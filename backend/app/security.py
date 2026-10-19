import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from . import config
from .db import session
from .models import LoginSession, User

passwords = PasswordHash.recommended()
cipher = Fernet(config.encryption_key())
attempts = defaultdict(deque)
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(20))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def throttle(request: Request):
    address = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    queue = attempts[address]
    while queue and queue[0] < now - 900:
        queue.popleft()
    if len(queue) >= 20:
        raise HTTPException(429, '尝试次数过多，请 15 分钟后再试')
    queue.append(now)


def current_user(request: Request, db=Depends(session)) -> User:
    token = request.cookies.get(config.COOKIE, '')
    record = db.get(LoginSession, digest(token)) if token else None
    if not record or record.expires_at < time.time():
        raise HTTPException(401, '请先登录')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and not hmac.compare_digest(request.headers.get('X-CSRF-Token', '').encode(), record.csrf.encode()):
        raise HTTPException(403, '请求校验失败，请刷新页面')
    request.state.login_session = record
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(401, '请先登录')
    return user


def admin(user=Depends(current_user)):
    if user.role != 'admin':
        raise HTTPException(403, '仅系统管理员可操作')
    return user


def key_for(user: User):
    if not user.encrypted_key:
        raise HTTPException(400, '请先在个人设置中填写 TikHub API Key')
    return cipher.decrypt(user.encrypted_key.encode()).decode()
