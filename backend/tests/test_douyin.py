import copy
import json
import time
from pathlib import Path
import httpx
import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import select
from app import media, worker
from app.db import Session
from app.main import app
from app.models import Monitor, Post, Run
from app.providers import base, share_links
from app.providers.base import ProviderError
from app.providers.douyin import DouyinProvider, detail_from, douyin_author, douyin_page, douyin_post
from app.providers.links import detect_link, douyin_target

SAMPLE = json.loads((Path(__file__).parent / 'fixtures/douyin_app_v3.json').read_text(encoding='utf-8'))
SEC = 'MS4wLjABAAAAsample_douyin_sec_uid'


@pytest.mark.parametrize('url,kind', [
    (f'https://www.douyin.com/user/{SEC}', 'sec_uid'),
    ('https://www.iesdouyin.com/share/user/9001/', 'uid'),
    ('https://www.douyin.com/video/123456', 'post'),
    ('https://www.douyin.com/note/123456', 'post'),
    ('https://www.iesdouyin.com/share/video/123456/', 'post'),
    (f'https://www.douyin.com/user/{SEC}?modal_id=123456', 'post'),
    ('https://v.douyin.com/Sample123/', 'short'),
])
def test_douyin_official_profiles_posts_and_pasted_share_messages(url, kind):
    platform, link = detect_link('长按复制此条消息，打开抖音搜索。 ' + url)
    assert platform == 'douyin' and douyin_target(link)[0] == kind


@pytest.mark.parametrize('url', [
    'https://douyin.com.evil.test/user/name', 'https://user@www.douyin.com/video/123',
    'http://v.douyin.com/sample/', 'https://v.douyin.com:8080/sample/',
    'https://www.douyin.com/search/test', 'https://www.douyin.com/',
    'https://www.douyin.com/video/not-an-id', 'https://v.douyin.com/a/b/',
    'https://www.douyin.com/?modal_id=1&modal_id=2',
])
def test_douyin_invalid_links_rejected_before_paid_requests(url):
    with pytest.raises(ProviderError):
        detect_link(url)


@pytest.mark.asyncio
async def test_short_link_expansion_uses_bounded_public_https_and_no_credentials(monkeypatch):
    real_client = httpx.AsyncClient
    requests = []
    async def redirect(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(302, headers={'Location': '/second/'})
        return httpx.Response(302, headers={'Location': f'https://www.douyin.com/user/{SEC}'})
    monkeypatch.setattr(share_links.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('1.1.1.1', 443))])
    monkeypatch.setattr(share_links.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(redirect), **kw))
    assert await share_links.expand_douyin_link('https://v.douyin.com/first/') == f'https://www.douyin.com/user/{SEC}'
    assert len(requests) == 2
    assert all('authorization' not in request.headers and 'cookie' not in request.headers for request in requests)
    async def malicious(request):
        return httpx.Response(302, headers={'Location': 'https://127.0.0.1/private'})
    monkeypatch.setattr(share_links.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(malicious), **kw))
    with pytest.raises(ProviderError):
        await share_links.expand_douyin_link('https://v.douyin.com/first/')
    monkeypatch.setattr(share_links.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(ProviderError):
        await share_links.expand_douyin_link('https://v.douyin.com/first/')


@pytest.mark.asyncio
async def test_short_link_redirect_limit_and_non_redirect_failure(monkeypatch):
    real_client = httpx.AsyncClient
    calls = []
    async def loop(request):
        calls.append(request)
        return httpx.Response(302, headers={'Location': '/loop/'})
    monkeypatch.setattr(share_links.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('1.1.1.1', 443))])
    monkeypatch.setattr(share_links.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(loop), **kw))
    with pytest.raises(ProviderError):
        await share_links.expand_douyin_link('https://v.douyin.com/first/')
    assert len(calls) == 5
    monkeypatch.setattr(share_links.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(lambda req: httpx.Response(403)), **kw))
    with pytest.raises(ProviderError):
        await share_links.expand_douyin_link('https://v.douyin.com/first/')


def test_native_video_gallery_and_stable_image_identity():
    author = douyin_author(SAMPLE['profile'])
    assert author['platform'] == 'douyin' and author['author_id'] == '9001'
    items, cursor, more = douyin_page(SAMPLE['posts'])
    assert len(items) == 2 and cursor == '1792404000000' and more
    video, gallery = map(douyin_post, items)
    assert video['kind'] == 'video' and video['assets'][0]['id'] == 'video'
    assert gallery['kind'] == 'images' and len(gallery['assets']) == 2
    assert all(asset['kind'] == 'image' for asset in gallery['assets'])
    assert gallery['share_url'].startswith('https://www.douyin.com/note/')
    # Gallery posts also have a video object; it must not become a video asset.
    reordered = copy.deepcopy(items[1])
    reordered['images'].reverse()
    reordered['images'][1]['url_list'] = ['https://p26-sign.douyinpic.com/changed-preview.jpg?new-signature=yes']
    assert douyin_post(reordered)['assets'][1]['id'] == gallery['assets'][0]['id']
    # With no native URI, different signed hosts/resize suffixes still refer to
    # the same image path and must resolve to the same asset ID.
    no_uri = copy.deepcopy(items[1])
    no_uri['images'][0].pop('uri')
    before = douyin_post(no_uri)['assets'][0]['id']
    no_uri['images'][0]['url_list'] = ['https://p26-sign.douyinpic.com/tos-cn-i-0813/sample-photo-1~tplv-resized.webp?other=signature']
    assert douyin_post(no_uri)['assets'][0]['id'] == before
    assert douyin_post(detail_from(SAMPLE['detail_video'], items[0]['aweme_id']))['kind'] == 'video'
    assert douyin_post(detail_from(SAMPLE['detail_gallery'], items[1]['aweme_id']))['kind'] == 'images'


@pytest.mark.parametrize('payload', [
    {'data': None}, {'aweme_list': None}, {'aweme_list': []},
    {'aweme_list': [], 'has_more': 'false'}, {'aweme_list': [], 'has_more': 0.0},
    {'aweme_list': [], 'has_more': 1, 'max_cursor': 0},
    {'aweme_list': [], 'has_more': 1, 'max_cursor': 'opaque'},
])
def test_invalid_douyin_paging_is_not_fake_empty_success(payload):
    with pytest.raises(ProviderError):
        douyin_page(payload)
    assert douyin_page({'aweme_list': [], 'has_more': '0', 'max_cursor': 0}) == ([], '0', False)


def test_invalid_media_time_and_empty_detail_are_reported():
    raw = copy.deepcopy(SAMPLE['posts']['data']['aweme_list'][0])
    raw['create_time'] = 0
    with pytest.raises(ProviderError):
        douyin_post(raw)
    with pytest.raises(ProviderError):
        detail_from({'aweme_details': [], 'filter_list': [{'reason': 5}]}, '123')
    raw = copy.deepcopy(SAMPLE['posts']['data']['aweme_list'][1])
    raw['images'] = {'unexpected': 'shape'}
    with pytest.raises(ProviderError):
        douyin_post(raw)


@pytest.fixture
def douyin_sdk(monkeypatch):
    real_sdk = base.AsyncTikHub
    requests, responses = [], copy.deepcopy(SAMPLE)
    async def upstream(request):
        requests.append(request)
        endpoint = request.url.path.rsplit('/', 1)[1]
        if endpoint in ('handler_user_profile', 'fetch_user_profile_by_uid'):
            payload = responses['profile']
        elif endpoint == 'fetch_one_video_v2':
            payload = responses['detail_gallery'] if request.url.params['aweme_id'].endswith('301') else responses['detail_video']
        elif endpoint == 'fetch_user_post_videos':
            assert request.url.params['sec_user_id'] == SEC
            assert request.url.params['count'] == '20' and request.url.params['sort_type'] == '0'
            assert request.url.params['channel'] == 'lite'
            payload = responses.get('next_page', responses['posts']) if request.url.params['max_cursor'] != '0' else responses['posts']
        else:
            raise AssertionError('Unexpected SDK endpoint')
        return httpx.Response(200, json=payload)
    monkeypatch.setattr(base, 'AsyncTikHub', lambda **kw: real_sdk(**kw, transport=httpx.MockTransport(upstream)))
    return requests, responses


@pytest.mark.asyncio
async def test_sdk_resolves_numeric_profiles_and_actual_post_author(douyin_sdk):
    requests, _ = douyin_sdk
    async with DouyinProvider('offline-douyin-key') as provider:
        assert (await provider.resolve('https://www.iesdouyin.com/share/user/9001/'))['author_id'] == '9001'
        assert requests[-1].url.path.endswith('fetch_user_profile_by_uid')
        assert (await provider.resolve('https://www.douyin.com/video/1900000000000000300'))['author_id'] == '9001'
        assert requests[-1].url.path.endswith('fetch_one_video_v2')
        assert (await provider.resolve('https://www.douyin.com/note/1900000000000000301'))['platform'] == 'douyin'
        before = len(requests)
        with pytest.raises(ProviderError):
            await provider.list_posts('9001', {'sec_uid': SEC}, 'bad-cursor')
        assert len(requests) == before


@pytest.mark.asyncio
async def test_douyin_api_worker_incremental_downloads_and_privacy(client, register, douyin_sdk, monkeypatch):
    requests, responses = douyin_sdk
    owner = register(client)
    client.put('/api/settings', json={'api_key': 'offline-douyin-owner-key'})
    async def expand(link):
        return f'https://www.douyin.com/user/{SEC}'
    monkeypatch.setattr('app.providers.douyin.expand_douyin_link', expand)
    resolution = client.post('/api/monitors/resolve', json={'url': '长按复制分享消息 https://v.douyin.com/sample/'})
    assert resolution.status_code == 200, resolution.text
    assert resolution.json()['author']['platform'] == 'douyin'
    result = client.post('/api/monitors', json={'resolution_id': resolution.json()['resolution_id'], 'interval_hours': 3})
    assert result.status_code == 201, result.text
    monitor_id = result.json()['id']
    await worker.process(monitor_id, worker.claim(monitor_id))
    with Session() as db:
        assert db.get(Monitor, monitor_id).state == 'idle'
        assert db.get(Monitor, monitor_id).next_check_at > time.time() + 10700
        assert db.scalar(select(Run)).status == 'success'
        # Same author ID on three platforms is legitimate and stays separate.
        for platform in ('tiktok', 'twitter'):
            db.add(Monitor(owner_id=owner['id'], platform=platform, author_id='9001', sec_uid='other-sec', username='other', nickname='Other', source_url='https://example.test'))
        db.commit()
    assert len(client.get('/api/monitors').json()) == 3
    assert len(client.get('/api/monitors?platform=douyin').json()) == 1
    payload = client.get('/api/posts?platform=douyin').json()
    assert payload['total'] == 2
    assert all(post['read'] and post['platform'] == 'douyin' for post in payload['items'])
    assert client.get('/api/posts?platform=tiktok').json()['total'] == 0
    gallery = next(post for post in payload['items'] if post['kind'] == 'images')
    assert '/note/' in gallery['share_url']
    assert all('url' not in asset for asset in gallery['assets'])
    refreshed = responses['detail_gallery']['data']['aweme_details'][0]
    refreshed['images'].reverse()
    refreshed['images'][1]['url_list'] = ['https://p26-sign.douyinpic.com/refreshed-image.jpg']
    downloads = []
    async def stream(url, filename, platform):
        downloads.append((url, filename, platform))
        return Response(b'image', media_type='image/jpeg')
    monkeypatch.setattr(media, 'stream_media', stream)
    asset_id = gallery['assets'][0]['id']
    assert client.get(f"/api/posts/{gallery['id']}/assets/{asset_id}/download").status_code == 200
    assert downloads[0][0].endswith('refreshed-image.jpg') and downloads[0][2] == 'douyin'
    assert downloads[0][1].startswith('douyin-')
    # Incremental polling follows numeric cursors and deduplicates overlaps.
    new = copy.deepcopy(responses['posts']['data']['aweme_list'][0])
    new.update(aweme_id='1900000000000000302', create_time=time.time() + 1)
    responses['posts']['data']['aweme_list'].append(new)
    responses['posts']['data']['max_cursor'] = 321
    responses['next_page'] = {'code': 200, 'data': {'aweme_list': [new], 'has_more': 0, 'max_cursor': 0}}
    with Session() as db:
        db.get(Monitor, monitor_id).next_check_at = time.time() - 1
        db.commit()
    await worker.process(monitor_id, worker.claim(monitor_id))
    assert client.get('/api/posts?platform=douyin').json()['total'] == 3
    assert client.get('/api/overview').json()['unread'] == 1
    assert any(request.url.params.get('max_cursor') == '321' for request in requests)
    assert all(request.headers['authorization'] == 'Bearer offline-douyin-owner-key' for request in requests)
    with TestClient(app) as other:
        register(other, 'other-douyin@example.test')
        assert other.get('/api/monitors?platform=douyin').json() == []
        assert other.get('/api/posts?platform=douyin').json()['items'] == []
        assert other.get(f"/api/posts/{gallery['id']}/assets/{asset_id}/download").status_code == 404
        assert other.post(f'/api/monitors/{monitor_id}/check').status_code == 404


@pytest.mark.asyncio
async def test_douyin_cdn_redirects_mime_and_platform_isolation(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(media.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('1.1.1.1', 443))])
    for url in ('https://api-play.amemv.com/play', 'https://v3-dy-o.zjcdn.com/video', 'https://p3-sign.douyinpic.com/image'):
        await media.validate_media_url(url, 'douyin')
        with pytest.raises(HTTPException):
            await media.validate_media_url(url, 'twitter')
    for url in ('https://douyinpic.com.evil.test/image', 'https://amemv.com/play', 'https://api-play.amemv.com:bad/play', 'https://127.0.0.1/private'):
        with pytest.raises(HTTPException):
            await media.validate_media_url(url, 'douyin')
    requests = []
    async def upstream(request):
        requests.append(request)
        if request.url.host == 'api-play.amemv.com':
            return httpx.Response(302, headers={'Location': 'https://v3-dy-o.zjcdn.com/asset.mp4'})
        return httpx.Response(200, headers={'Content-Type': 'video/mp4'}, content=b'offline-mp4')
    monkeypatch.setattr(media.httpx, 'AsyncClient', lambda **kw: real_client(transport=httpx.MockTransport(upstream), **kw))
    response = await media.stream_media('https://api-play.amemv.com/play', 'douyin-123-1.mp4', 'douyin')
    assert b''.join([part async for part in response.body_iterator]) == b'offline-mp4'
    assert len(requests) == 2 and all('authorization' not in request.headers for request in requests)
    assert response.headers['content-disposition'].endswith('.mp4"')
