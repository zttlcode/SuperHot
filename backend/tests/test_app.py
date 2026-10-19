import asyncio
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import Session
from app.main import app
from app.models import Monitor, Post, Resolution, Run, User
from app.provider import ProviderError, author_from, post_from, validate_link
from app.security import cipher
from app import worker


def item(identifier, timestamp):
    return {'platform_id': identifier, 'text': 'A caption', 'published_at': timestamp, 'kind': 'video', 'assets': [{'url': 'https://v.tiktokcdn.com/movie.mp4', 'kind': 'video'}], 'cover': '', 'share_url': ''}


def test_registration_requires_invite_and_uses_private_http_only_session(client, register):
    invalid = client.post('/api/auth/register', json={'email': 'one@example.com', 'password': 'a-secure-password', 'name': 'One', 'invite_code': 'wrong'})
    assert invalid.status_code == 400
    unicode_invite = client.post('/api/auth/register', json={'email': 'one@example.com', 'password': 'a-secure-password', 'name': 'One', 'invite_code': '错误的邀请码'})
    assert unicode_invite.status_code == 400
    owner = register(client)
    assert owner['role'] == 'admin'
    assert 'HttpOnly' in client.cookies.jar._cookies['testserver.local']['/']['superhot_session']._rest
    response = client.get('/api/auth/me')
    assert response.json()['user']['email'] == 'one@example.com'
    assert 'password_hash' not in response.text
    assert client.post('/api/auth/logout', headers={'X-CSRF-Token': ''}).status_code == 403
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/auth/me').status_code == 401


def test_credentials_encrypted_and_never_returned(client, register):
    owner = register(client)
    key = 'my-own-tikhub-secret'
    result = client.put('/api/settings', json={'api_key': key})
    assert result.status_code == 200
    assert key not in result.text
    with Session() as db:
        encrypted = db.get(User, owner['id']).encrypted_key
        assert key not in encrypted
        assert cipher.decrypt(encrypted.encode()).decode() == key
    assert client.put('/api/settings', json={'timezone': 'Invalid/Zone'}).status_code == 400
    assert client.put('/api/settings', json={'api_key': ''}).json()['has_key'] is False


def test_cross_user_resources_and_admin_are_isolated(client, monitor, register):
    row, _ = monitor
    with Session() as db:
        post = Post(owner_id=row_owner(db, row['id']), monitor_id=row['id'], **item('123', time.time()))
        db.add(post)
        db.commit()
        post_id = post.id
    with TestClient(app) as other:
        user = register(other, 'two@example.com')
        assert user['role'] == 'member'
        assert other.get('/api/monitors').json() == []
        assert other.get('/api/posts').json()['items'] == []
        assert other.patch('/api/monitors/' + row['id'], json={'enabled': False}).status_code == 404
        assert other.delete('/api/monitors/' + row['id']).status_code == 404
        assert other.get(f'/api/posts/{post_id}/download/0').status_code == 404
        assert other.post(f'/api/posts/{post_id}/read').status_code == 404
        assert other.get('/api/admin/users').status_code == 403


def row_owner(db, identifier):
    return db.get(Monitor, identifier).owner_id


def test_expired_resolution_and_duplicate_monitor(client, monitor, provider):
    row, _ = monitor
    resolution = client.post('/api/monitors/resolve', json={'url': 'https://www.tiktok.com/@creator'}).json()
    assert client.post('/api/monitors', json={'resolution_id': resolution['resolution_id'], 'interval_hours': 2}).status_code == 409
    with Session() as db:
        record = db.get(Resolution, resolution['resolution_id'])
        record.created_at = time.time() - 1900
        db.commit()
    assert client.post('/api/monitors', json={'resolution_id': resolution['resolution_id'], 'interval_hours': 2}).status_code == 400


@pytest.mark.asyncio
async def test_baseline_incremental_dedup_and_exclusive_lease(client, monitor, provider):
    row, owner = monitor
    provider.pages = {'0': ([item('old', time.time() - 86400)], '0', False)}
    token = worker.claim(row['id'])
    assert token
    assert worker.claim(row['id']) is None
    await worker.process(row['id'], token)
    with Session() as db:
        baseline = db.get(Monitor, row['id']).baseline_at
        assert baseline
        assert db.scalar(select(Post)).read is True
        db.get(Monitor, row['id']).next_check_at = time.time() - 1
        db.commit()
    provider.pages['0'] = ([item('new', time.time() + 1), item('old', time.time() - 86400)], '0', False)
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        posts = list(db.scalars(select(Post)))
        assert len(posts) == 2
        assert sum(not post.read for post in posts) == 1
        assert db.get(Monitor, row['id']).next_check_at > time.time() + 7000
        db.get(Monitor, row['id']).next_check_at = time.time() - 1
        db.commit()
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        assert len(list(db.scalars(select(Post)))) == 2
    assert all(call[1] == 'test-key-for-one' for call in provider.calls)
    assert client.get('/api/overview').json()['unread'] == 1
    assert client.post('/api/posts/read-all').status_code == 200
    assert client.get('/api/overview').json()['unread'] == 0


@pytest.mark.asyncio
async def test_pause_manual_check_and_failed_key_backoff(client, monitor, provider):
    row, owner = monitor
    assert client.patch('/api/monitors/' + row['id'], json={'enabled': False}).status_code == 200
    assert worker.claim(row['id']) is None
    assert client.post('/api/monitors/' + row['id'] + '/check').status_code == 200
    provider.failure = ProviderError('TikHub Key 无效', permanent=True)
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        saved = db.get(Monitor, row['id'])
        assert saved.enabled is False
        assert saved.state == 'error'
        assert saved.lease_until == 0
        assert saved.next_check_at > time.time() + 21000
        assert 'Key' in saved.last_error


@pytest.mark.asyncio
async def test_expired_lease_is_recoverable_and_deleted_jobs_do_not_write(client, monitor, provider):
    row, _ = monitor
    with Session() as db:
        saved = db.get(Monitor, row['id'])
        saved.lease_token = 'crashed-worker'
        saved.lease_until = time.time() - 1
        db.commit()
    token = worker.claim(row['id'])
    assert token and token != 'crashed-worker'
    assert client.delete('/api/monitors/' + row['id']).status_code == 200
    await worker.process(row['id'], token)
    with Session() as db:
        assert list(db.scalars(select(Post))) == []
        assert list(db.scalars(select(Run))) == []


@pytest.mark.asyncio
async def test_paginated_backfill_is_capped_without_losing_continuation(client, monitor, provider):
    row, _ = monitor
    with Session() as db:
        saved = db.get(Monitor, row['id'])
        saved.baseline_at = time.time() - 500
        db.commit()
    provider.pages = {str(i): ([item(str(i), time.time())], str(i + 1), True) for i in range(7)}
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        saved = db.get(Monitor, row['id'])
        assert saved.state == 'backfill'
        assert saved.backfill_cursor == '5'
        assert len(list(db.scalars(select(Post)))) == 5


@pytest.mark.asyncio
async def test_download_rejects_private_or_untrusted_sources(client, monitor, provider):
    row, _ = monitor
    with Session() as db:
        post = Post(owner_id=row_owner(db, row['id']), monitor_id=row['id'], **item('123', time.time()))
        db.add(post)
        db.commit()
        identifier = post.id
    response = client.get(f'/api/posts/{identifier}/download/0')
    assert response.status_code == 400
    assert 'test-key' not in response.text
    from app.media import validate_media_url
    from fastapi import HTTPException
    for url in ['http://127.0.0.1/secret', 'https://evil.example/movie', 'https://tiktokcdn.com.evil.example/movie']:
        with pytest.raises(HTTPException):
            await validate_media_url(url)


def test_password_change_revokes_other_sessions(client, register):
    register(client)
    with TestClient(app) as second:
        result = second.post('/api/auth/login', json={'email': 'one@example.com', 'password': 'a-secure-password'})
        second.headers['X-CSRF-Token'] = result.json()['csrf_token']
        assert client.put('/api/settings/password', json={'current_password': 'a-secure-password', 'new_password': 'another-secure-password'}).status_code == 200
        assert second.get('/api/auth/me').status_code == 401
        assert client.get('/api/auth/me').status_code == 200


def test_upstream_normalization_and_no_fake_empty_success():
    author = author_from({'data': {'user': {'uid': '123', 'sec_uid': 'SEC', 'unique_id': 'creator'}}})
    assert author['author_id'] == '123'
    photo = post_from({'aweme_id': '456', 'image_post_info': {'images': [{'display_image': {'url_list': ['https://p.tiktokcdn.com/photo.webp']}}]}})
    assert photo['kind'] == 'images'
    assert len(photo['assets']) == 1
    with pytest.raises(ProviderError):
        author_from({'data': {}})
    for url in ['https://tiktok.com.evil.example/@name', 'http://tiktok.com/@name', 'https://user@tiktok.com/@name']:
        with pytest.raises(ProviderError):
            validate_link(url)


def test_origin_and_login_throttling(client):
    assert client.post('/api/auth/login', json={'email': 'a@b.com', 'password': 'invalid'}, headers={'Origin': 'https://evil.example'}).status_code == 403
    for _ in range(20):
        assert client.post('/api/auth/login', json={'email': 'a@b.com', 'password': 'invalid'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'a@b.com', 'password': 'invalid'}).status_code == 429
