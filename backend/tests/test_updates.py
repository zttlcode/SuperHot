import time
import httpx
import pytest
from fastapi import HTTPException
from app import updates
from app.config import RUNTIME


@pytest.fixture
def release_api(monkeypatch):
    class Client:
        tag = 'v2.3.0'
        package_status = 200
        yanked = False
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        def __init__(self, **kwargs):
            pass
        async def get(self, url, **kwargs):
            if 'api.github.com' in url:
                return httpx.Response(200, request=httpx.Request('GET', url), json={'tag_name': self.tag, 'body': 'Release notes', 'html_url': 'https://github.com/TikHub/TikHub-API-Python-SDK/releases/tag/' + self.tag})
            return httpx.Response(self.package_status, request=httpx.Request('GET', url), json={'info': {'requires_python': '>=3.9'}, 'urls': [{'yanked': self.yanked}]})
    monkeypatch.setattr(updates.httpx, 'AsyncClient', Client)
    monkeypatch.setattr(updates, 'cache', None)
    return Client


@pytest.mark.asyncio
async def test_release_needs_matching_installable_package(release_api):
    status = await updates.check_update(True)
    assert status['can_update'] is True
    release_api.package_status = 404
    status = await updates.check_update(True)
    assert status['available'] is False
    assert status['can_update'] is False


@pytest.mark.asyncio
async def test_yanked_prerelease_major_and_invalid_versions_are_blocked(release_api):
    release_api.yanked = True
    assert (await updates.check_update(True))['can_update'] is False
    release_api.yanked = False
    release_api.tag = 'v3.0.0'
    assert (await updates.check_update(True))['can_update'] is False
    for tag in ['v2.3.0rc1', '--index-url malicious', 'not-a-version']:
        release_api.tag = tag
        with pytest.raises(HTTPException):
            await updates.check_update(True)


def test_update_requires_launcher_verified_version_and_serial_execution(client, register, monkeypatch):
    register(client)
    async def check(force=False):
        return {'can_update': True, 'latest': '2.3.0'}
    monkeypatch.setattr('app.main.check_update', check)
    heartbeat = RUNTIME / 'launcher.heartbeat'
    heartbeat.unlink(missing_ok=True)
    assert client.post('/api/admin/updates', json={'target': '2.3.0'}).status_code == 409
    heartbeat.touch()
    try:
        assert client.post('/api/admin/updates', json={'target': '2.3.0; malicious'}).status_code == 400
        assert client.post('/api/admin/updates', json={'target': '2.3.0'}).status_code == 202
        assert client.post('/api/admin/updates', json={'target': '2.3.0'}).status_code == 409
        assert client.post('/api/admin/updates/rollback').status_code == 409
    finally:
        heartbeat.unlink(missing_ok=True)
