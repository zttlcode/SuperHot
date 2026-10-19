"""Cross-platform supervisor and constrained local SDK updater.

The web server only enqueues database jobs. Installation/restarts happen here.
"""
from __future__ import annotations
import concurrent.futures
import json
import os
import secrets
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
env_file = ROOT / '.env'
if not env_file.exists():
    try:
        with env_file.open('x', encoding='utf-8') as file:
            file.write('SUPERHOT_INVITE_CODE=' + secrets.token_urlsafe(18) + '\n')
        env_file.chmod(0o600)
    except FileExistsError:
        pass

from app.config import RUNTIME, ROOT, INVITE_CODE
from app.db import Session, engine
from app.models import Monitor, UpdateJob, WorkerStatus
from alembic import command
from alembic.config import Config
from sqlalchemy import select

if not INVITE_CODE:
    raise SystemExit('Set SUPERHOT_INVITE_CODE in your .env before starting.')
HOST = os.getenv('SUPERHOT_HOST', '127.0.0.1')
PORT = int(os.getenv('SUPERHOT_PORT', '8765'))
HEALTH_HOST = '127.0.0.1' if HOST in ('0.0.0.0', '::') else HOST
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
active_file = RUNTIME / 'active-python.txt'
previous_file = RUNTIME / 'previous-release.json'


def checked_python(value):
    path = Path(value).resolve()
    if path != Path(sys.executable).resolve() and RUNTIME not in path.parents:
        raise ValueError('Interpreter is outside the managed release directory')
    if not path.exists():
        raise ValueError('Interpreter no longer exists')
    return str(path)


def run_locked():
    handle = (RUNTIME / 'launcher.lock').open('a+b')
    handle.seek(0)
    handle.write(b'0')
    handle.flush()
    handle.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit('Another SuperHot launcher is already running.')
    return handle


def migrate():
    command.upgrade(Config(str(ROOT / 'backend' / 'alembic.ini')), 'head')


def child(python, module, *args):
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'backend')
    log = (RUNTIME / ('api.log' if module == 'uvicorn' else 'worker.log')).open('ab')
    return subprocess.Popen([python, '-m', module, *args], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=NO_WINDOW)


def start(python):
    return [child(python, 'uvicorn', 'app.main:app', '--host', HOST, '--port', str(PORT), '--no-access-log'), child(python, 'app.worker')]


def stop(children):
    for process in children:
        if process.poll() is None:
            process.terminate()
    for process in children:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def health(expected=None):
    for _ in range(30):
        try:
            with urllib.request.urlopen(f'http://{HEALTH_HOST}:{PORT}/api/health', timeout=2) as response:
                result = json.load(response)
            import hashlib
            with Session() as db:
                worker = db.get(WorkerStatus, 'monitor')
                worker_ready = worker and worker.sdk_version == result['sdk'] and time.time() - worker.heartbeat < 20
            if worker_ready and result['status'] == 'ok' and result.get('deployment_id') == hashlib.sha256(str(RUNTIME).encode()).hexdigest()[:16] and (expected is None or result['sdk'] == expected):
                return True
        except Exception:
            pass
        time.sleep(.5)
    return False


def mark(identifier, state, message):
    with Session() as db:
        job = db.get(UpdateJob, identifier)
        job.state, job.message = state, message
        if state in ('success', 'failed', 'rolled_back'):
            job.finished_at = time.time()
        db.commit()


def prepare(identifier, target):
    """All commands have fixed argv; target is a normalized verified version."""
    from packaging.version import Version
    import asyncio
    from app.updates import check_update
    target = str(Version(target))
    latest = asyncio.run(check_update(force=True))
    if not latest['can_update'] or latest['latest'] != target:
        raise RuntimeError('Candidate is no longer eligible for automatic update')
    release = RUNTIME / 'releases' / identifier
    release.mkdir(parents=True, exist_ok=False)
    requirements = (ROOT / 'backend' / 'requirements.in').read_text(encoding='utf-8')
    import re
    requirements = re.sub(r'^tikhub==[^\r\n]+', 'tikhub==' + target, requirements, flags=re.M)
    (release / 'requirements.in').write_text(requirements, encoding='utf-8')
    interpreter = release / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    with (release / 'build.log').open('wb') as log:
        def invoke(args):
            subprocess.run(args, cwd=ROOT, check=True, stdout=log, stderr=log, timeout=900, creationflags=NO_WINDOW)
        invoke([sys.executable, '-m', 'venv', str(release / 'venv')])
        invoke([str(interpreter), '-m', 'pip', 'install', '--index-url', 'https://pypi.org/simple', '--disable-pip-version-check', '-r', str(release / 'requirements.in')])
        invoke([str(interpreter), '-m', 'pip', 'check'])
        invoke([str(interpreter), str(ROOT / 'scripts' / 'sdk_probe.py'), target])
        frozen = subprocess.check_output([str(interpreter), '-m', 'pip', 'freeze'], cwd=ROOT, creationflags=NO_WINDOW).decode()
    (release / 'requirements.txt').write_text(frozen, encoding='utf-8')
    return {'python': str(interpreter), 'version': target, 'requirements.in': requirements, 'requirements.txt': frozen}


def snapshot(python, sdk):
    return {'python': python, 'version': sdk, **{name: (ROOT / 'backend' / name).read_text(encoding='utf-8') for name in ('requirements.in', 'requirements.txt')}}


def activate(release):
    python = checked_python(release['python'])
    for name in ('requirements.in', 'requirements.txt'):
        target = ROOT / 'backend' / name
        temporary = target.with_suffix(target.suffix + '.tmp')
        temporary.write_text(release[name], encoding='utf-8')
        temporary.replace(target)
    temporary = active_file.with_suffix('.tmp')
    temporary.write_text(python, encoding='utf-8')
    temporary.replace(active_file)


def switch_runtime(children, previous, candidate):
    """Keep the previous release authoritative until both processes are healthy."""
    stop(children)
    candidate_children = start(checked_python(candidate['python']))
    if not health(candidate['version']):
        stop(candidate_children)
        restored = start(previous['python'])
        if not health(previous['version']):
            stop(restored)
            raise RuntimeError('Previous runtime health check also failed')
        return restored, previous['python'], False
    try:
        activate(candidate)
        temporary = previous_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(previous), encoding='utf-8')
        temporary.replace(previous_file)
    except Exception:
        stop(candidate_children)
        activate(previous)
        restored = start(previous['python'])
        if not health(previous['version']):
            stop(restored)
            raise RuntimeError('Could not restore previous runtime')
        return restored, previous['python'], False
    return candidate_children, candidate['python'], True


def main():
    lock_handle = run_locked()
    if not (ROOT / 'frontend' / 'dist' / 'index.html').exists():
        raise SystemExit('Build the frontend first: cd frontend; npm ci; npm run build')
    migrate()
    python = checked_python(active_file.read_text().strip()) if active_file.exists() else sys.executable
    children = start(python)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future, updating = None, None
    try:
        if not health():
            raise SystemExit('Startup failed. See .runtime/api.log; check whether the port is already in use.')
        print(f'SuperHot: http://{HEALTH_HOST}:{PORT}', flush=True)
        print('Invitation code: run python scripts/admin.py invite in this environment.', flush=True)
        (RUNTIME / 'maintenance').unlink(missing_ok=True)
        (RUNTIME / 'stop.request').unlink(missing_ok=True)
        # A launcher interrupted during preparation must not leave an endless pending job.
        with Session() as db:
            for job in db.scalars(select(UpdateJob).where(UpdateJob.state.in_(['preparing', 'switching']))):
                job.state, job.message, job.finished_at = 'failed', '上次更新被中断，请检查实际版本后重新尝试', time.time()
            db.commit()
        while True:
            (RUNTIME / 'launcher.heartbeat').touch()
            if (RUNTIME / 'stop.request').exists():
                (RUNTIME / 'stop.request').unlink(missing_ok=True)
                break
            for index, process in enumerate(children):
                if process.poll() is not None:
                    print('Restarting API/worker after unexpected exit.', flush=True)
                    children[index] = child(python, 'uvicorn', 'app.main:app', '--host', HOST, '--port', str(PORT), '--no-access-log') if index == 0 else child(python, 'app.worker')
            if future and future.done():
                switched = False
                previous = None
                try:
                    candidate = future.result()
                    previous = snapshot(python, updating.previous)
                    mark(updating.id, 'switching', '离线验证通过，等待在途任务结束并切换；真实接口仍需观察')
                    (RUNTIME / 'maintenance').touch()
                    for _ in range(180):
                        (RUNTIME / 'launcher.heartbeat').touch()
                        with Session() as db:
                            busy = db.scalar(select(Monitor.id).where(Monitor.lease_until > time.time()).limit(1))
                        if not busy:
                            break
                        time.sleep(1)
                    else:
                        raise RuntimeError('Timed out waiting for active monitoring tasks')
                    switched = True
                    children, python, success = switch_runtime(children, previous, candidate)
                    if success:
                        mark(updating.id, 'success', '已切换并重启；离线兼容性通过，真实接口以运行结果为准')
                    else:
                        mark(updating.id, 'rolled_back', '候选版本验证或激活失败，已恢复上一版本')
                except Exception:
                    if switched and previous:
                        stop(children)
                        activate(previous)
                        children = start(previous['python'])
                        health(previous['version'])
                    mark(updating.id, 'failed', '更新未完成，保留原版本；请检查 .runtime/releases 下的构建日志')
                finally:
                    (RUNTIME / 'maintenance').unlink(missing_ok=True)
                    future, updating = None, None
            if future is None:
                with Session() as db:
                    updating = db.scalar(select(UpdateJob).where(UpdateJob.state.in_(['queued', 'rollback_queued'])).order_by(UpdateJob.created_at).limit(1))
                if updating:
                    reverting = updating.state == 'rollback_queued'
                    mark(updating.id, 'preparing', '正在隔离环境安装并执行离线兼容性检查')
                    future = pool.submit(lambda: json.loads(previous_file.read_text(encoding='utf-8'))) if reverting else pool.submit(prepare, updating.id, updating.target)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop(children)
        pool.shutdown(wait=False, cancel_futures=True)
        (RUNTIME / 'launcher.heartbeat').unlink(missing_ok=True)
        lock_handle.close()


if __name__ == '__main__':
    main()
