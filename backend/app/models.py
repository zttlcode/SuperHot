from __future__ import annotations

import time
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def uid():
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='member')
    encrypted_key: Mapped[str | None] = mapped_column(Text)
    key_hint: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str] = mapped_column(String(80), default='Asia/Shanghai')
    language: Mapped[str] = mapped_column(String(8), default='zh')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class Resolution(Base):
    __tablename__ = 'resolutions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    author: Mapped[dict] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Monitor(Base):
    __tablename__ = 'monitors'
    __table_args__ = (UniqueConstraint('owner_id', 'platform', 'author_id', name='uq_monitors_owner_platform_author'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    author_id: Mapped[str] = mapped_column(String(160))
    platform: Mapped[str] = mapped_column(String(20), default='tiktok', server_default='tiktok')
    provider_data: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    sec_uid: Mapped[str | None] = mapped_column(String(256))
    username: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(160))
    avatar: Mapped[str] = mapped_column(Text, default='')
    source_url: Mapped[str] = mapped_column(Text)
    interval_hours: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_check_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    last_attempt_at: Mapped[float | None] = mapped_column(Float)
    last_success_at: Mapped[float | None] = mapped_column(Float)
    baseline_at: Mapped[float | None] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(24), default='pending')
    last_error: Mapped[str | None] = mapped_column(Text)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    lease_token: Mapped[str | None] = mapped_column(String(32))
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    manual: Mapped[bool] = mapped_column(Boolean, default=False)
    backfill_cursor: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (UniqueConstraint('monitor_id', 'platform_id'),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    monitor_id: Mapped[str] = mapped_column(ForeignKey('monitors.id', ondelete='CASCADE'), index=True)
    platform_id: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text, default='')
    kind: Mapped[str] = mapped_column(String(20))
    post_type: Mapped[str] = mapped_column(String(20), default='original', server_default='original')
    references: Mapped[list] = mapped_column(JSON, default=list, server_default='[]')
    assets: Mapped[list] = mapped_column(JSON)
    cover: Mapped[str] = mapped_column(Text, default='')
    share_url: Mapped[str] = mapped_column(Text, default='')
    published_at: Mapped[float] = mapped_column(Float)
    found_at: Mapped[float] = mapped_column(Float, default=time.time)
    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    read: Mapped[bool] = mapped_column(Boolean, default=True)


class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    monitor_id: Mapped[str] = mapped_column(ForeignKey('monitors.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(24))
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[float] = mapped_column(Float)
    finished_at: Mapped[float] = mapped_column(Float, default=time.time)


class WorkerStatus(Base):
    __tablename__ = 'worker_status'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default='monitor')
    heartbeat: Mapped[float] = mapped_column(Float)
    sdk_version: Mapped[str] = mapped_column(String(40))


class UpdateJob(Base):
    __tablename__ = 'sdk_updates'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    target: Mapped[str] = mapped_column(String(40))
    previous: Mapped[str] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(32), default='queued')
    message: Mapped[str] = mapped_column(Text, default='等待本机启动器处理')
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    finished_at: Mapped[float | None] = mapped_column(Float)
