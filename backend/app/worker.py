from __future__ import annotations

import asyncio
import logging
import time
import uuid
from importlib.metadata import version
from sqlalchemy import or_, select, update
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .db import Session
from .models import Monitor, Post, Run, User, WorkerStatus
from .providers.base import ProviderError
from .providers.registry import provider_for
from .security import cipher

log = logging.getLogger('superhot.worker')
active = set()
owner_locks = {}
CAPACITY = 4


def claim(identifier):
    now, token = time.time(), uuid.uuid4().hex
    with Session() as db:
        result = db.execute(update(Monitor).where(Monitor.id == identifier, Monitor.lease_until < now, Monitor.next_check_at <= now, or_(Monitor.enabled.is_(True), Monitor.manual.is_(True))).values(lease_token=token, lease_until=now + 600, last_attempt_at=now, state='running', manual=False))
        db.commit()
        return token if result.rowcount else None


async def process(identifier, token):
    start, pages, new_count = time.time(), 0, 0
    with Session() as db:
        monitor = db.get(Monitor, identifier)
        if not monitor or monitor.lease_token != token:
            return
        owner = db.get(User, monitor.owner_id)
        owner_id = monitor.owner_id
    lock = owner_locks.setdefault(owner_id, asyncio.Lock())
    try:
        async with lock:
            # Re-read after waiting: a deleted monitor or changed key must not use a stale credential.
            with Session() as db:
                monitor = db.get(Monitor, identifier)
                owner = db.get(User, owner_id)
                if not monitor or monitor.lease_token != token:
                    return
                if not owner or not owner.encrypted_key:
                    raise ProviderError('请先在设置中填写 TikHub API Key', permanent=True)
                key = cipher.decrypt(owner.encrypted_key.encode()).decode()
                baseline = monitor.baseline_at
                platform, author_id = monitor.platform, monitor.author_id
                provider_data = dict(monitor.provider_data or {})
                if platform in ('tiktok', 'douyin'):
                    provider_data.setdefault('sec_uid', monitor.sec_uid)
                continuation = monitor.backfill_cursor
                known = set(db.scalars(select(Post.platform_id).where(Post.monitor_id == identifier)))
            batch, next_cursor, incomplete = [], None, False
            async with provider_for(platform, key) as provider:
                # Always inspect the newest page, even while an older backfill is in progress.
                cursor = None
                visited = set()
                for page_index in range(5):
                    if cursor in visited:
                        raise ProviderError('接口返回了重复分页游标，已停止本轮检查')
                    visited.add(cursor)
                    items, next_value, more = await provider.list_posts(author_id, provider_data, cursor)
                    pages += 1
                    batch.extend(items)
                    if baseline is None or not more:
                        break
                    if not next_value or next_value == cursor:
                        raise ProviderError('接口返回了无效分页游标，已停止本轮检查')
                    # A known item alone cannot prove coverage because posts may be pinned.
                    old = [x for x in items if x['published_at'] and x['published_at'] < (monitor.last_success_at or baseline) - 86400]
                    if not continuation and len(old) >= 3 and any(x['platform_id'] in known for x in old):
                        break
                    cursor = continuation if page_index == 0 and continuation else next_value
                    if page_index == 4:
                        next_cursor, incomplete = cursor, True
            with Session() as db:
                monitor = db.get(Monitor, identifier)
                if not monitor or monitor.lease_token != token:
                    return
                existing = set(db.scalars(select(Post.platform_id).where(Post.monitor_id == identifier)))
                for item in batch:
                    if item['platform_id'] in existing:
                        continue
                    existing.add(item['platform_id'])
                    is_new = baseline is not None and (item['published_at'] == 0 or item['published_at'] > baseline)
                    new_count += int(is_new)
                    db.add(Post(owner_id=owner_id, monitor_id=identifier, **item, is_new=is_new, read=not is_new))
                now = time.time()
                monitor.baseline_at = baseline or start
                monitor.last_success_at = now
                monitor.failure_count = 0
                monitor.last_error = None
                monitor.backfill_cursor = next_cursor
                monitor.state = 'backfill' if incomplete else 'idle'
                # Preserve a manual request that arrived during this run.
                monitor.next_check_at = now if monitor.manual else now + (60 if incomplete else monitor.interval_hours * 3600)
                monitor.lease_token, monitor.lease_until = None, 0
                db.add(Run(owner_id=owner_id, monitor_id=identifier, status='partial' if incomplete else 'success', new_count=new_count, pages=pages, started_at=start))
                db.commit()
    except Exception as error:
        message = str(error) if isinstance(error, ProviderError) else '后台检查异常，稍后会重试；请查看服务状态'
        with Session() as db:
            monitor = db.get(Monitor, identifier)
            if monitor and monitor.lease_token == token:
                monitor.failure_count += 1
                permanent = isinstance(error, ProviderError) and error.permanent
                monitor.state = 'error'
                monitor.last_error = message
                monitor.next_check_at = time.time() + (21600 if permanent else min(3600, 60 * 2 ** min(monitor.failure_count, 6)))
                monitor.lease_token, monitor.lease_until = None, 0
                db.add(Run(owner_id=owner_id, monitor_id=identifier, status='error', pages=pages, message=message, started_at=start))
                db.commit()


async def scan():
    from .config import RUNTIME
    with Session() as db:
        row = db.get(WorkerStatus, 'monitor') or WorkerStatus(id='monitor', heartbeat=time.time(), sdk_version=version('tikhub'))
        row.heartbeat = time.time()
        row.sdk_version = version('tikhub')
        db.add(row)
        db.commit()
        if (RUNTIME / 'maintenance').exists():
            return
        ids = list(db.scalars(select(Monitor.id).where(Monitor.next_check_at <= time.time(), Monitor.lease_until < time.time(), or_(Monitor.enabled.is_(True), Monitor.manual.is_(True))).order_by(Monitor.next_check_at).limit(max(0, CAPACITY - len(active)))))
    for identifier in ids:
        token = claim(identifier)
        if token:
            task = asyncio.create_task(process(identifier, token))
            active.add(task)
            task.add_done_callback(active.discard)


async def main():
    # The first version intentionally has one worker per deployment. An OS lock
    # proves that a crashed predecessor no longer owns any database leases.
    from .config import RUNTIME
    handle = (RUNTIME / 'worker.lock').open('a+b')
    handle.seek(0)
    handle.write(b'0')
    handle.flush()
    handle.seek(0)
    try:
        if __import__('os').name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit('A monitor worker is already running for this deployment.')
    with Session() as db:
        db.execute(update(Monitor).where(Monitor.lease_token.is_not(None)).values(lease_token=None, lease_until=0, state='pending'))
        db.commit()
    scheduler = AsyncIOScheduler(timezone='UTC')
    scheduler.add_job(scan, 'interval', seconds=10, id='due-monitors', max_instances=1, coalesce=True)
    scheduler.start()
    await scan()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        handle.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
