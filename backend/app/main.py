from __future__ import annotations

import hmac
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from importlib.metadata import version
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal
from urllib.parse import quote
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from . import config
from .db import Session, session
from .models import LoginSession, Monitor, Post, Resolution, Run, UpdateJob, User, WorkerStatus
from .providers.base import ProviderError
from .providers.links import detect_link
from .providers.registry import PROVIDERS, provider_for
from .providers.assets import asset_summaries, normalize_assets
from .security import DUMMY_HASH, admin, cipher, current_user, digest, key_for, passwords, throttle
from .updates import check_update

register_lock = threading.Lock()


@asynccontextmanager
async def lifespan(_):
    # Schema migrations are performed by the launcher, not by every web process.
    yield


app = FastAPI(title='SuperHot API', version='0.1.0', lifespan=lifespan, docs_url='/api/docs', openapi_url='/api/openapi.json')


@app.middleware('http')
async def origin_guard(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('origin') and request.headers['origin'] not in config.ALLOWED_ORIGINS:
        return JSONResponse({'detail': '不允许的请求来源'}, status_code=403)
    result = await call_next(request)
    result.headers['X-Content-Type-Options'] = 'nosniff'
    result.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    result.headers['X-Frame-Options'] = 'DENY'
    if request.url.path.startswith('/api/'):
        result.headers['Cache-Control'] = 'no-store'
    return result


@app.exception_handler(ProviderError)
async def provider_error(_, error):
    return JSONResponse({'detail': str(error)}, status_code=502)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class LoginBody(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RegisterBody(LoginBody):
    name: str = Field(min_length=1, max_length=80)
    invite_code: str = Field(min_length=1, max_length=200)


class SettingsBody(StrictModel):
    api_key: str | None = Field(default=None, max_length=4096)
    timezone: str | None = Field(default=None, max_length=80)
    language: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)


class PasswordBody(StrictModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class ResolveBody(StrictModel):
    url: str = Field(min_length=8, max_length=3000)


class CreateMonitor(StrictModel):
    resolution_id: str
    interval_hours: int = Field(default=1, ge=1, le=168)


class PatchMonitor(StrictModel):
    enabled: bool | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)


def public_user(user):
    return {key: getattr(user, key) for key in ('id', 'email', 'name', 'role', 'key_hint', 'timezone', 'language')} | {'has_key': bool(user.encrypted_key)}


def login_response(db, response, user):
    token, csrf = secrets.token_urlsafe(48), secrets.token_hex(24)
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, csrf=csrf, expires_at=time.time() + config.SESSION_SECONDS))
    db.execute(delete(LoginSession).where(LoginSession.expires_at < time.time()))
    db.commit()
    response.set_cookie(config.COOKIE, token, max_age=config.SESSION_SECONDS, httponly=True, samesite='strict', secure=config.SECURE_COOKIE, path='/')
    return {'user': public_user(user), 'csrf_token': csrf}


def owned(db, model, identifier, owner):
    row = db.get(model, identifier)
    if not row or row.owner_id != owner.id:
        raise HTTPException(404, '记录不存在')
    return row


def monitor_json(row):
    return {key: getattr(row, key) for key in ('id', 'platform', 'author_id', 'username', 'nickname', 'avatar', 'source_url', 'interval_hours', 'enabled', 'next_check_at', 'last_attempt_at', 'last_success_at', 'baseline_at', 'state', 'last_error', 'created_at')}


def post_url(row, monitor):
    username, identifier = quote(monitor.username, safe=''), quote(row.platform_id, safe='')
    if monitor.platform == 'twitter':
        return f'https://x.com/{username}/status/{identifier}'
    if monitor.platform == 'douyin':
        return f'https://www.douyin.com/{"note" if row.kind == "images" else "video"}/{identifier}'
    category = 'photo' if row.kind == 'images' else 'video'
    return f'https://www.tiktok.com/@{username}/{category}/{identifier}'


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '0.1.0', 'sdk': version('tikhub'), 'platforms': list(PROVIDERS), 'deployment_id': digest(str(config.RUNTIME))[:16]}


@app.post('/api/auth/register', status_code=201)
def register(body: RegisterBody, request: Request, response: Response, db=Depends(session)):
    throttle(request)
    if not config.INVITE_CODE or not hmac.compare_digest(body.invite_code.encode(), config.INVITE_CODE.encode()):
        raise HTTPException(400, '邀请码无效，请联系部署管理员')
    email = body.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(body.password) < 10 or not body.name.strip():
        raise HTTPException(400, '请填写有效邮箱、昵称和至少 10 位密码')
    hashed = passwords.hash(body.password)
    with register_lock:
        first = not db.scalar(select(User.id).limit(1))
        user = User(email=email, name=body.name.strip(), password_hash=hashed, role='admin' if first else 'member')
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, '该邮箱已注册') from None
    return login_response(db, response, user)


@app.post('/api/auth/login')
def login(body: LoginBody, request: Request, response: Response, db=Depends(session)):
    throttle(request)
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    valid = passwords.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, '邮箱或密码不正确')
    return login_response(db, response, user)


@app.get('/api/auth/me')
def me(request: Request, user=Depends(current_user)):
    return {'user': public_user(user), 'csrf_token': request.state.login_session.csrf}


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(session)):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == request.state.login_session.token_hash))
    db.commit()
    response.delete_cookie(config.COOKIE, path='/')
    return {'ok': True}


@app.put('/api/settings')
def settings(body: SettingsBody, user=Depends(current_user), db=Depends(session)):
    if body.timezone is not None:
        try:
            ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(400, '无效的 IANA 时区') from None
        user.timezone = body.timezone
    if body.language is not None:
        if body.language not in ('zh', 'en'):
            raise HTTPException(400, '不支持的语言')
        user.language = body.language
    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(400, '昵称不能为空')
        user.name = body.name.strip()
    if body.api_key is not None:
        key = body.api_key.strip()
        if key and (len(key) < 10 or any(x.isspace() for x in key)):
            raise HTTPException(400, 'Key 格式无效，请粘贴完整 Key')
        user.encrypted_key = cipher.encrypt(key.encode()).decode() if key else None
        user.key_hint = ('•••• ' + key[-4:]) if key else None
        # A corrected credential should not remain blocked by a long failure backoff.
        db.execute(update(Monitor).where(Monitor.owner_id == user.id, Monitor.enabled.is_(True)).values(next_check_at=time.time()))
    db.add(user)
    db.commit()
    return public_user(user)


@app.put('/api/settings/password')
def change_password(body: PasswordBody, request: Request, user=Depends(current_user), db=Depends(session)):
    if not passwords.verify(body.current_password, user.password_hash):
        raise HTTPException(400, '当前密码不正确')
    user.password_hash = passwords.hash(body.new_password)
    db.add(user)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id, LoginSession.token_hash != request.state.login_session.token_hash))
    db.commit()
    return {'ok': True}


@app.get('/api/overview')
def overview(user=Depends(current_user), db=Depends(session)):
    count = lambda model, *conditions: db.scalar(select(func.count()).select_from(model).where(model.owner_id == user.id, *conditions))
    status = db.get(WorkerStatus, 'monitor')
    return {'monitors': count(Monitor), 'active': count(Monitor, Monitor.enabled.is_(True)), 'errors': count(Monitor, Monitor.state == 'error'), 'posts': count(Post), 'unread': count(Post, Post.read.is_(False)), 'worker_online': bool(status and time.time() - status.heartbeat < 40), 'worker_sdk': status.sdk_version if status else None}


@app.post('/api/monitors/resolve')
async def resolve(body: ResolveBody, user=Depends(current_user), db=Depends(session)):
    platform, link = detect_link(body.url)
    async with provider_for(platform, key_for(user)) as provider:
        author = await provider.resolve(link)
    author['platform'] = platform
    record = Resolution(owner_id=user.id, author=author, source_url=link)
    db.execute(delete(Resolution).where(Resolution.created_at < time.time() - 1800))
    db.add(record)
    db.commit()
    return {'resolution_id': record.id, 'author': author}


@app.post('/api/monitors', status_code=201)
def create_monitor(body: CreateMonitor, user=Depends(current_user), db=Depends(session)):
    key_for(user)
    record = owned(db, Resolution, body.resolution_id, user)
    if record.created_at < time.time() - 1800:
        raise HTTPException(400, '作者确认已过期，请重新识别')
    row = Monitor(owner_id=user.id, **record.author, source_url=record.source_url, interval_hours=body.interval_hours)
    db.add(row)
    db.delete(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '你已监控该作者') from None
    return monitor_json(row)


@app.get('/api/monitors')
def monitors(q: str = '', platform: Literal['', 'tiktok', 'twitter', 'douyin'] = '', user=Depends(current_user), db=Depends(session)):
    statement = select(Monitor).where(Monitor.owner_id == user.id)
    if platform:
        statement = statement.where(Monitor.platform == platform)
    if q:
        statement = statement.where(Monitor.nickname.icontains(q[:100]) | Monitor.username.icontains(q[:100]))
    return [monitor_json(row) for row in db.scalars(statement.order_by(Monitor.created_at.desc()))]


@app.patch('/api/monitors/{identifier}')
def patch_monitor(identifier: str, body: PatchMonitor, user=Depends(current_user), db=Depends(session)):
    row = owned(db, Monitor, identifier, user)
    if body.enabled is not None:
        row.enabled = body.enabled
        if body.enabled:
            row.next_check_at = time.time()
    if body.interval_hours is not None:
        row.interval_hours = body.interval_hours
        if row.state != 'running':
            row.next_check_at = time.time() + body.interval_hours * 3600
    db.commit()
    return monitor_json(row)


@app.post('/api/monitors/{identifier}/check')
def manual_check(identifier: str, user=Depends(current_user), db=Depends(session)):
    row = owned(db, Monitor, identifier, user)
    key_for(user)
    row.manual = True
    row.next_check_at = time.time()
    db.commit()
    return {'ok': True}


@app.delete('/api/monitors/{identifier}')
def remove_monitor(identifier: str, user=Depends(current_user), db=Depends(session)):
    db.delete(owned(db, Monitor, identifier, user))
    db.commit()
    return {'ok': True}


@app.get('/api/posts')
def posts(page: int = 1, q: str = '', scope: str = 'all', author: str = '', platform: Literal['', 'tiktok', 'twitter', 'douyin'] = '', user=Depends(current_user), db=Depends(session)):
    conditions = [Post.owner_id == user.id]
    if platform:
        conditions.append(Post.monitor_id.in_(select(Monitor.id).where(Monitor.platform == platform)))
    if q:
        conditions.append(Post.text.icontains(q[:100]))
    if scope == 'unread':
        conditions.append(Post.read.is_(False))
    if author:
        conditions.append(Post.monitor_id == author)
    total = db.scalar(select(func.count()).select_from(Post).where(*conditions))
    rows = db.scalars(select(Post).where(*conditions).order_by(Post.published_at.desc(), Post.found_at.desc()).offset((max(1, page) - 1) * 24).limit(24))
    result = []
    for row in rows:
        monitor = db.get(Monitor, row.monitor_id)
        result.append({key: getattr(row, key) for key in ('id', 'platform_id', 'text', 'kind', 'post_type', 'references', 'cover', 'published_at', 'found_at', 'is_new', 'read', 'monitor_id')} | {'platform': monitor.platform, 'share_url': post_url(row, monitor), 'assets': asset_summaries(row.assets), 'asset_count': len(row.assets), 'author': monitor.nickname, 'username': monitor.username})
    return {'items': result, 'total': total, 'page': max(1, page)}


@app.post('/api/posts/read-all')
def read_all(user=Depends(current_user), db=Depends(session)):
    db.execute(update(Post).where(Post.owner_id == user.id).values(read=True))
    db.commit()
    return {'ok': True}


@app.post('/api/posts/{identifier}/read')
def read_post(identifier: str, user=Depends(current_user), db=Depends(session)):
    row = owned(db, Post, identifier, user)
    row.read = True
    db.commit()
    return {'ok': True}


@app.get('/api/posts/{identifier}/download/{index}')
async def download(identifier: str, index: int, user=Depends(current_user), db=Depends(session)):
    row = owned(db, Post, identifier, user)
    assets = normalize_assets(row.assets)
    if index < 0 or index >= len(assets):
        raise HTTPException(404, '素材不存在')
    return await download_asset(identifier, assets[index]['id'], user, db)


@app.get('/api/posts/{identifier}/assets/{asset_id}/download')
async def download_asset(identifier: str, asset_id: str, user=Depends(current_user), db=Depends(session)):
    from .media import stream_media
    row = owned(db, Post, identifier, user)
    # Reject unknown asset IDs before spending the owner's TikHub quota.
    if not any(asset['id'] == asset_id for asset in normalize_assets(row.assets)):
        raise HTTPException(404, '素材不存在')
    monitor = db.get(Monitor, row.monitor_id)
    async with provider_for(monitor.platform, key_for(user)) as provider:
        fresh = await provider.detail(row.platform_id)
    assets = normalize_assets(fresh['assets'])
    match = next(((index, asset) for index, asset in enumerate(assets) if asset['id'] == asset_id), None)
    if match is None:
        raise HTTPException(404, '该素材已变化或不可访问，请刷新内容列表')
    index, asset = match
    if not asset.get('url'):
        raise HTTPException(422, '该素材未返回可下载直链，首版暂不支持 HLS 分片合并')
    row.assets, row.cover = assets, fresh['cover']
    db.commit()
    suffix = 'jpg' if asset['kind'] == 'image' else 'mp4'
    return await stream_media(asset['url'], f'{monitor.platform}-{row.platform_id}-{index + 1}.{suffix}', platform=monitor.platform)


@app.get('/api/runs')
def runs(user=Depends(current_user), db=Depends(session)):
    rows = db.scalars(select(Run).where(Run.owner_id == user.id).order_by(Run.started_at.desc()).limit(50))
    return [{key: getattr(row, key) for key in ('id', 'monitor_id', 'status', 'new_count', 'pages', 'message', 'started_at', 'finished_at')} for row in rows]


@app.get('/api/admin/users')
def users(user=Depends(admin), db=Depends(session)):
    return [{key: getattr(row, key) for key in ('id', 'email', 'name', 'role', 'created_at')} for row in db.scalars(select(User).order_by(User.created_at))]


@app.get('/api/admin/sdk')
async def sdk(force: bool = False, user=Depends(admin)):
    return await check_update(force)


@app.get('/api/admin/updates')
def update_jobs(user=Depends(admin), db=Depends(session)):
    jobs = list(db.scalars(select(UpdateJob).order_by(UpdateJob.created_at.desc()).limit(20)))
    return {'current': version('tikhub'), 'can_rollback': (config.RUNTIME / 'previous-release.json').exists(), 'launcher_online': (config.RUNTIME / 'launcher.heartbeat').exists() and time.time() - (config.RUNTIME / 'launcher.heartbeat').stat().st_mtime < 20, 'jobs': [{key: getattr(row, key) for key in ('id', 'target', 'previous', 'state', 'message', 'created_at', 'finished_at')} for row in jobs]}


class UpgradeBody(StrictModel):
    target: str = Field(max_length=40)


@app.post('/api/admin/updates', status_code=202)
async def upgrade(body: UpgradeBody, user=Depends(admin), db=Depends(session)):
    status = await check_update(force=True)
    if not status['can_update'] or body.target != status['latest']:
        raise HTTPException(400, '该版本尚未通过发布来源与兼容性预检')
    heartbeat = config.RUNTIME / 'launcher.heartbeat'
    if not heartbeat.exists() or time.time() - heartbeat.stat().st_mtime > 20:
        raise HTTPException(409, '请通过 start.ps1/start.sh 启动系统后再更新')
    if db.scalar(select(UpdateJob.id).where(UpdateJob.state.in_(['queued', 'rollback_queued', 'preparing', 'switching']))):
        raise HTTPException(409, '已有更新正在执行')
    job = UpdateJob(owner_id=user.id, target=body.target, previous=version('tikhub'))
    db.add(job)
    db.commit()
    return {'id': job.id}


@app.post('/api/admin/updates/rollback', status_code=202)
def rollback(user=Depends(admin), db=Depends(session)):
    import json
    record = config.RUNTIME / 'previous-release.json'
    heartbeat = config.RUNTIME / 'launcher.heartbeat'
    if not record.exists() or not heartbeat.exists() or time.time() - heartbeat.stat().st_mtime > 20:
        raise HTTPException(409, '没有可用的上一版环境，或启动器未运行')
    if db.scalar(select(UpdateJob.id).where(UpdateJob.state.in_(['queued', 'rollback_queued', 'preparing', 'switching']))):
        raise HTTPException(409, '已有更新正在执行')
    previous = json.loads(record.read_text(encoding='utf-8'))
    job = UpdateJob(owner_id=user.id, target=previous['version'], previous=version('tikhub'), state='rollback_queued', message='等待回退到上一版本')
    db.add(job)
    db.commit()
    return {'id': job.id}


# The built frontend uses the same origin and HttpOnly session cookies.
DIST = config.ROOT / 'frontend' / 'dist'
if (DIST / 'assets').exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/{path:path}', include_in_schema=False)
def frontend(path: str):
    if path.startswith('api/'):
        raise HTTPException(404, '接口不存在')
    if (DIST / 'index.html').exists():
        return FileResponse(DIST / 'index.html')
    return JSONResponse({'message': 'Frontend not built. Run npm ci && npm run build in frontend.'}, status_code=503)
