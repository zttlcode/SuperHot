import os
import sys
import tempfile
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
(ROOT / '.runtime').mkdir(exist_ok=True)
directory = tempfile.TemporaryDirectory(prefix='test-', dir=ROOT / '.runtime')
os.environ['SUPERHOT_RUNTIME'] = directory.name
os.environ['DATABASE_URL'] = 'sqlite:///' + Path(directory.name, 'tests.db').as_posix()
os.environ['SUPERHOT_INVITE_CODE'] = 'test-invitation'
sys.path.insert(0, str(ROOT / 'backend'))
from app.db import Base, engine, Session
from app import models
from app.main import app
from app.security import attempts
from app import worker
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    attempts.clear()
    worker.owner_locks.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def register():
    def create(client, email='one@example.com'):
        response = client.post('/api/auth/register', json={'email': email, 'password': 'a-secure-password', 'name': email.split('@')[0], 'invite_code': 'test-invitation'})
        assert response.status_code == 201, response.text
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        return response.json()['user']
    return create


@pytest.fixture
def provider(monkeypatch):
    class FakeProvider:
        calls = []
        pages = {'0': ([], '0', False)}
        failure = None

        def __init__(self, key):
            self.key = key

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def resolve(self, link):
            self.calls.append(('resolve', self.key))
            return {'author_id': 'author-1', 'sec_uid': 'sec-author-1', 'username': 'creator', 'nickname': 'Test Creator', 'avatar': ''}

        async def posts(self, sec, cursor='0'):
            self.calls.append(('posts', self.key, cursor))
            if self.failure:
                raise self.failure
            return self.pages[cursor]

        async def list_posts(self, author_id, provider_data, cursor=None):
            return await self.posts(provider_data.get('sec_uid'), cursor or '0')

        async def detail(self, identifier):
            return {'assets': [{'url': 'http://127.0.0.1/private', 'kind': 'video'}], 'cover': ''}
    monkeypatch.setitem(__import__('app.providers.registry', fromlist=['PROVIDERS']).PROVIDERS, 'tiktok', FakeProvider)
    return FakeProvider


@pytest.fixture
def monitor(client, register, provider):
    owner = register(client)
    assert client.put('/api/settings', json={'api_key': 'test-key-for-one'}).status_code == 200
    resolution = client.post('/api/monitors/resolve', json={'url': 'https://www.tiktok.com/@creator'}).json()
    response = client.post('/api/monitors', json={'resolution_id': resolution['resolution_id'], 'interval_hours': 2})
    assert response.status_code == 201, response.text
    return response.json(), owner


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    directory.cleanup()
