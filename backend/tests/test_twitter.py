import copy
import json
import time
from pathlib import Path
import httpx
import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import Session
from app.models import Monitor, Post, Run
from app.providers.base import ProviderError
from app.providers.links import detect_link
from app.providers.registry import PROVIDERS
from app.providers.twitter import TwitterProvider, tweet_author, twitter_author, twitter_page, twitter_post, twitter_post_type
from app import worker, media

SAMPLE = json.loads((Path(__file__).parent / 'fixtures/twitter_timeline.json').read_text(encoding='utf-8'))
COMPACT_SAMPLE = json.loads((Path(__file__).parent / 'fixtures/twitter_compact_timeline.json').read_text(encoding='utf-8'))


def tweet(identifier='1900000000000000100', **fields):
    return {'rest_id': identifier, 'core': {'user_results': {'result': {'rest_id': '9001', 'legacy': {'screen_name': 'sample_creator', 'name': 'Creator'}}}},
            'legacy': {'full_text': 'Original text', 'created_at': time.time(), **fields}}


def test_graphql_timeline_text_mixed_mp4_and_opaque_cursor():
    items, cursor, more = twitter_page(SAMPLE)
    assert len(items) == 2 and more and cursor == 'opaque-cursor/+=do-not-convert'
    text, mixed = map(twitter_post, items)
    assert text['kind'] == 'text' and text['assets'] == []
    assert text['share_url'].startswith('https://x.com/sample_creator/status/')
    assert mixed['kind'] == 'mixed'
    assert [item['id'] for item in mixed['assets']] == ['media-photo', 'media-video']
    assert mixed['assets'][1]['url'] == 'https://video.twimg.com/sample-high.mp4'
    assert mixed['assets'][1]['preview'].startswith('https://pbs.twimg.com/')


@pytest.mark.parametrize('payload', [None, {'data': None}, {'unknown': []}, {'tweets': None},
                                    {'tweets': [], 'has_more': True}, {'tweets': [], 'next_cursor': 123},
                                    {'timeline': None}, {'timeline': [], 'status': 'error'},
                                    {'timeline': [], 'pinned': ['unexpected']},
                                    {'instructions': [{'type': 'ChangedUpstreamFormat', 'entries': []}]}])
def test_invalid_payload_is_not_a_successful_empty_timeline(payload):
    with pytest.raises(ProviderError):
        twitter_page(payload)


@pytest.mark.parametrize('url', ['https://x.com/creator', 'https://twitter.com/creator?lang=en',
                                 'https://mobile.twitter.com/creator/status/123/photo/1', 'https://x.com/i/web/status/123'])
def test_official_twitter_links(url):
    platform, canonical = detect_link('分享：' + url)
    assert platform == 'twitter' and canonical.startswith('https://x.com/') and '?' not in canonical


@pytest.mark.parametrize('url', ['https://x.com.evil.test/creator', 'https://x.com@evil.test/creator',
                                 'https://user@x.com/creator', 'http://x.com/creator', 'https://x.com:8080/creator',
                                 'https://x.com/search?q=test', 'https://x.com/home', 'https://t.co/abc'])
def test_untrusted_and_non_author_twitter_links(url):
    with pytest.raises(ProviderError):
        detect_link(url)


def test_long_text_quotes_do_not_absorb_quoted_author_media():
    raw = tweet(quoted_status_id_str='123')
    raw['note_tweet'] = {'note_tweet_results': {'result': {'text': 'Full long post\n第二段'}}}
    quoted = tweet('123', full_text='Quoted author text', extended_entities={'media': [{'id_str': 'quoted-only', 'type': 'photo', 'media_url_https': 'https://pbs.twimg.com/media/quoted.jpg'}]})
    quoted['core']['user_results']['result']['legacy']['screen_name'] = 'other_author'
    raw['quoted_status_result'] = {'result': quoted}
    post = twitter_post(raw)
    assert post['text'] == 'Full long post\n第二段'
    assert post['post_type'] == 'quote' and post['assets'] == []
    assert post['references'][0]['username'] == 'other_author'


def test_animation_mp4_and_hls_only_are_not_confused_with_thumbnail():
    animated = tweet(extended_entities={'media': [{'id_str': 'gif-1', 'type': 'animated_gif', 'media_url_https': 'https://pbs.twimg.com/thumb.jpg', 'video_info': {'variants': [{'content_type': 'video/mp4', 'url': 'https://video.twimg.com/animation.mp4'}]}}]})
    asset = twitter_post(animated)['assets'][0]
    assert asset['kind'] == 'animated_gif' and asset['url'].endswith('.mp4') and asset['downloadable']
    animated['legacy']['extended_entities']['media'][0]['video_info']['variants'][0] = {'content_type': 'application/x-mpegURL', 'url': 'https://video.twimg.com/animation.m3u8'}
    asset = twitter_post(animated)['assets'][0]
    assert asset['preview'].endswith('thumb.jpg') and not asset['downloadable'] and asset['url'] == ''


def test_empty_timeline_and_unavailable_quote_are_distinct_from_invalid_payload():
    assert twitter_page({'tweets': [], 'has_more': False}) == ([], None, False)
    assert twitter_page({'instructions': [{'type': 'TimelineTerminateTimeline'}]}) == ([], None, False)
    raw = tweet(quoted_status_id_str='123', is_quote_status=True)
    raw['quoted_status_result'] = {'result': {'__typename': 'TweetUnavailable'}}
    post = twitter_post(raw)
    assert post['post_type'] == 'quote' and post['assets'] == []


def test_captured_compact_shape_pinned_partial_authors_and_grouped_video():
    items, cursor, more = twitter_page(COMPACT_SAMPLE)
    assert len(items) == 5 and more and cursor == 'opaque-sanitized-next_cursor/+='
    assert items[0]['tweet_id'] == COMPACT_SAMPLE['data']['pinned']['tweet_id']
    assert tweet_author(items[0])['author_id'] == '9001'
    assert tweet_author(items[0])['username'] == ''
    posts = [twitter_post(item) for item in items]
    assert [post['post_type'] for post in posts] == ['original', 'original', 'quote', 'reply', 'repost']
    assert posts[0]['kind'] == 'video' and posts[0]['assets'][0]['downloadable']
    assert posts[0]['assets'][0]['kind'] == 'video'
    assert posts[0]['assets'][0]['url'].endswith('.mp4')
    assert posts[2]['kind'] == 'text' and posts[2]['assets'] == []
    assert posts[2]['references'][0]['id'] == items[2]['quoted']['tweet_id']
    assert posts[2]['references'][0]['text'] == items[2]['quoted']['text']
    # No username is required for timeline identity, but author confirmation
    # must still retrieve an actual profile before creating a new monitor.
    with pytest.raises(ProviderError):
        twitter_author(items[0]['author'])
    assert twitter_page({'status': 'ok', 'timeline': [], 'pinned': None, 'next_cursor': ''}) == ([], None, False)


def test_grouped_photos_animation_and_entity_list_do_not_hide_media():
    raw = copy.deepcopy(COMPACT_SAMPLE['data']['timeline'][0])
    raw['entities'] = []
    raw['media'] = {
        'photo': [{'id': 'photo-1', 'media_url_https': 'https://pbs.twimg.com/media/photo.jpg'}],
        'animated_gif': [{'id': 'gif-1', 'media_url_https': 'https://pbs.twimg.com/media/preview.jpg', 'variants': [
            {'content_type': 'video/mp4', 'url': 'https://video.twimg.com/animation.mp4'}]}],
    }
    post = twitter_post(raw)
    assert post['kind'] == 'mixed'
    assert [asset['kind'] for asset in post['assets']] == ['image', 'animated_gif']
    raw['media'] = {'unknown': [{}]}
    with pytest.raises(ProviderError):
        twitter_post(raw)


@pytest.mark.asyncio
async def test_compact_response_runs_through_real_sdk_worker_and_profile_fallback(client, register, monkeypatch):
    from app.providers import base
    real_sdk = base.AsyncTikHub
    requests = []
    source = copy.deepcopy(COMPACT_SAMPLE)
    # Upstream can repeat the pinned post in its normal timeline.
    source['data']['timeline'].append(copy.deepcopy(source['data']['pinned']))
    async def upstream(request):
        requests.append(request)
        if request.url.path.endswith('fetch_user_profile'):
            return httpx.Response(200, json={'code': 200, 'data': {'user': {'rest_id': '9001', 'screen_name': 'sample_author'}}})
        if request.url.path.endswith('fetch_tweet_detail'):
            return httpx.Response(200, json={'code': 200, 'data': source['data']['pinned']})
        assert request.url.path.endswith('fetch_user_post_tweet')
        assert request.url.params['rest_id'] == '9001'
        return httpx.Response(200, json=source)
    monkeypatch.setattr(base, 'AsyncTikHub', lambda **kwargs: real_sdk(**kwargs, transport=httpx.MockTransport(upstream)))
    register(client)
    client.put('/api/settings', json={'api_key': 'offline-compact-owner-key'})
    tweet_id = source['data']['pinned']['tweet_id']
    resolution = client.post('/api/monitors/resolve', json={'url': f'https://x.com/untrusted_name/status/{tweet_id}'})
    assert resolution.status_code == 200, resolution.text
    assert requests[-1].url.params['rest_id'] == '9001'
    assert resolution.json()['author']['username'] == 'sample_author'
    response = client.post('/api/monitors', json={'resolution_id': resolution.json()['resolution_id']})
    assert response.status_code == 201, response.text
    identifier = response.json()['id']
    await worker.process(identifier, worker.claim(identifier))
    result = client.get('/api/posts?platform=twitter').json()
    assert result['total'] == 3
    assert {post['post_type'] for post in result['items']} == {'original', 'quote'}
    assert all(post['read'] and not post['is_new'] for post in result['items'])
    with Session() as db:
        assert db.get(Monitor, identifier).state == 'idle'
        assert db.scalar(select(Run)).status == 'success'
    # In subsequent pages partial author IDs must still prevent attributing a
    # different author's post to this monitored account.
    source['data']['timeline'][0]['author']['rest_id'] = '9999'
    source['data']['timeline'] = [source['data']['timeline'][0]]
    source['data']['pinned'] = None
    async with TwitterProvider('offline-compact-owner-key') as provider:
        posts, cursor, more = await provider.list_posts('9001', {}, 'opaque-cursor')
        assert posts == [] and more
        assert requests[-1].url.params['cursor'] == 'opaque-cursor'
    assert all(request.headers['authorization'] == 'Bearer offline-compact-owner-key' for request in requests)


@pytest.mark.asyncio
async def test_full_api_worker_and_real_sdk_http_contract_without_network(client, register, monkeypatch):
    from app.providers import base
    real_sdk = base.AsyncTikHub
    requests = []
    async def upstream(request):
        requests.append(request)
        if request.url.path.endswith('fetch_user_profile'):
            payload = {'user': {'result': {'rest_id': '9001', 'legacy': {'screen_name': 'sample_creator', 'name': 'Creator'}}}}
        elif request.url.path.endswith('fetch_user_post_tweet'):
            assert request.url.params['rest_id'] == '9001'
            payload = SAMPLE['data']
        elif request.url.path.endswith('fetch_tweet_detail'):
            payload = {'tweetResult': {'result': twitter_page(SAMPLE)[0][1]}}
        else:
            raise AssertionError('Unexpected endpoint ' + request.url.path)
        return httpx.Response(200, json={'code': 200, 'data': payload})
    monkeypatch.setattr(base, 'AsyncTikHub', lambda **kwargs: real_sdk(**kwargs, transport=httpx.MockTransport(upstream)))
    register(client)
    client.put('/api/settings', json={'api_key': 'offline-sdk-owner-key'})
    resolution = client.post('/api/monitors/resolve', json={'url': 'https://x.com/sample_creator'}).json()
    response = client.post('/api/monitors', json={'resolution_id': resolution['resolution_id']})
    assert response.status_code == 201, response.text
    identifier = response.json()['id']
    await worker.process(identifier, worker.claim(identifier))
    result = client.get('/api/posts?platform=twitter').json()
    assert result['total'] == 2
    mixed = next(item for item in result['items'] if item['kind'] == 'mixed')
    assert mixed['assets'][1]['id'] == 'media-video'
    async def stream(url, filename, platform):
        assert url.endswith('sample-high.mp4') and platform == 'twitter'
        return Response(b'offline-video', media_type='video/mp4')
    monkeypatch.setattr(media, 'stream_media', stream)
    assert client.get(f"/api/posts/{mixed['id']}/assets/media-video/download").status_code == 200
    assert len(requests) == 3
    assert all(request.headers['authorization'] == 'Bearer offline-sdk-owner-key' for request in requests)
    assert 'offline-sdk-owner-key' not in json.dumps(result)


@pytest.mark.asyncio
async def test_sdk_arguments_profile_post_author_and_scope(monkeypatch):
    provider = TwitterProvider('offline-fake-key')
    calls = []
    replies = [tweet(), tweet('1900000000000000101', in_reply_to_status_id_str='42'),
               tweet('1900000000000000102', retweeted_status={'id_str': '99'}), tweet('1900000000000000103', quoted_status_id_str='99')]
    async def fake_call(method, **kwargs):
        calls.append((method.__name__, kwargs))
        if method.__name__ == 'fetch_user_profile':
            return {'user': {'result': replies[0]['core']['user_results']['result']}}
        if method.__name__ == 'fetch_tweet_detail':
            return {'tweetResult': {'result': replies[0]}}
        return {'tweets': replies, 'next_cursor': 'a/+=opaque'}
    monkeypatch.setattr(provider, 'call', fake_call)
    async with provider:
        author = await provider.resolve('https://twitter.com/sample_creator')
        assert author['author_id'] == '9001'
        actual = await provider.resolve('https://x.com/wrong_name/status/1900000000000000100')
        assert actual['username'] == 'sample_creator'
        posts, cursor, more = await provider.list_posts('9001', {}, 'a/+=opaque')
        assert len(posts) == 2 and [post['post_type'] for post in posts] == ['original', 'quote']
        assert more and cursor == 'a/+=opaque'
        assert calls[-1][1] == {'rest_id': 9001, 'cursor': 'a/+=opaque'}
        assert (await provider.detail('1900000000000000100'))['kind'] == 'text'


@pytest.fixture
def twitter_provider(monkeypatch, provider):
    class FakeTwitter(provider):
        calls = []
        pages = {None: ([], None, False)}
        fresh = twitter_post(twitter_page(SAMPLE)[0][1])

        async def resolve(self, link):
            self.calls.append(('resolve', self.key))
            return twitter_author({'rest_id': '9001', 'legacy': {'screen_name': 'sample_creator', 'name': 'Twitter Creator'}})

        async def list_posts(self, author_id, provider_data, cursor=None):
            self.calls.append(('posts', self.key, cursor))
            return self.pages[cursor]

        async def detail(self, identifier):
            self.calls.append(('detail', self.key, identifier))
            return self.fresh
    monkeypatch.setitem(PROVIDERS, 'twitter', FakeTwitter)
    return FakeTwitter


@pytest.fixture
def twitter_monitor(client, register, twitter_provider):
    owner = register(client)
    client.put('/api/settings', json={'api_key': 'twitter-owner-private-key'})
    resolution = client.post('/api/monitors/resolve', json={'url': 'https://x.com/sample_creator'})
    assert resolution.status_code == 200, resolution.text
    result = client.post('/api/monitors', json={'resolution_id': resolution.json()['resolution_id']})
    assert result.status_code == 201, result.text
    return result.json(), owner


def test_platform_identity_filtering_and_private_content(client, twitter_monitor, register):
    row, owner = twitter_monitor
    assert row['platform'] == 'twitter'
    with Session() as db:
        tiktok = Monitor(owner_id=owner['id'], author_id='9001', sec_uid='tiktok-sec', username='other', nickname='TikTok Creator', source_url='https://www.tiktok.com/@other')
        db.add(tiktok)
        post = Post(owner_id=owner['id'], monitor_id=row['id'], **twitter_post(tweet()))
        db.add(post)
        db.commit()
        identifier = post.id
    assert len(client.get('/api/monitors').json()) == 2
    assert len(client.get('/api/monitors?platform=twitter').json()) == 1
    assert client.get('/api/posts?platform=tiktok').json()['total'] == 0
    payload = client.get('/api/posts?platform=twitter').json()['items'][0]
    assert payload['kind'] == 'text' and payload['assets'] == [] and payload['platform'] == 'twitter'
    assert payload['share_url'].startswith('https://x.com/')
    assert client.get('/api/posts?platform=unknown').status_code == 422
    with TestClient(app) as other:
        register(other, 'other@example.com')
        assert other.get('/api/posts?platform=twitter').json()['items'] == []
        assert other.get(f'/api/posts/{identifier}/assets/arbitrary/download').status_code == 404


@pytest.mark.asyncio
async def test_twitter_worker_baseline_pagination_dedup_and_owner_key(client, twitter_monitor, twitter_provider):
    row, _ = twitter_monitor
    old = twitter_post(tweet('1900000000000000200', created_at=time.time() - 86400))
    twitter_provider.pages = {None: ([old], 'opaque/+=', True)}
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        assert db.scalar(select(Post)).read is True
        db.get(Monitor, row['id']).next_check_at = time.time() - 1
        db.commit()
    new = twitter_post(tweet('1900000000000000201', created_at=time.time() + 1))
    twitter_provider.pages = {None: ([old, new], 'opaque/+=', True), 'opaque/+=': ([old, new], None, False)}
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        assert len(list(db.scalars(select(Post)))) == 2
        assert sum(not post.read for post in db.scalars(select(Post))) == 1
        assert db.get(Monitor, row['id']).state == 'idle'
    assert all(call[1] == 'twitter-owner-private-key' for call in twitter_provider.calls)
    assert ('posts', 'twitter-owner-private-key', 'opaque/+=') in twitter_provider.calls


@pytest.mark.asyncio
async def test_repeated_twitter_cursor_fails_without_partial_database_write(client, twitter_monitor, twitter_provider):
    row, _ = twitter_monitor
    with Session() as db:
        db.get(Monitor, row['id']).baseline_at = time.time() - 1
        db.commit()
    twitter_provider.pages = {None: ([], 'repeat', True), 'repeat': ([], 'repeat', True)}
    await worker.process(row['id'], worker.claim(row['id']))
    with Session() as db:
        assert db.get(Monitor, row['id']).state == 'error'
        assert db.scalar(select(Run)).status == 'error'


def test_download_uses_stable_media_id_and_owner_key_after_reordering(client, twitter_monitor, twitter_provider, monkeypatch):
    row, owner = twitter_monitor
    original = twitter_post(twitter_page(SAMPLE)[0][1])
    with Session() as db:
        post = Post(owner_id=owner['id'], monitor_id=row['id'], **original)
        db.add(post)
        db.commit()
        identifier = post.id
    twitter_provider.fresh = copy.deepcopy(original)
    twitter_provider.fresh['assets'].reverse()
    calls = []
    async def stream(url, filename, platform):
        calls.append((url, filename, platform))
        return Response(b'image-bytes', media_type='image/jpeg')
    monkeypatch.setattr(media, 'stream_media', stream)
    response = client.get(f'/api/posts/{identifier}/assets/media-photo/download')
    assert response.status_code == 200
    assert calls[0][0] == 'https://pbs.twimg.com/media/sample.jpg' and calls[0][2] == 'twitter'
    assert twitter_provider.calls[-1][1] == 'twitter-owner-private-key'
    before = len(twitter_provider.calls)
    assert client.get(f'/api/posts/{identifier}/assets/not-owned/download').status_code == 404
    assert len(twitter_provider.calls) == before
    payload = client.get('/api/posts').json()['items'][0]
    assert all('url' not in asset for asset in payload['assets'])


@pytest.mark.asyncio
async def test_twitter_cdn_redirect_policy_and_real_mime_extension(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(media.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('1.1.1.1', 443))])
    for url in ('https://pbs.twimg.com.evil.test/image', 'https://evil.twimg.com/image', 'https://x.com/image', 'https://video.twimg.com:bad/file'):
        with pytest.raises(HTTPException):
            await media.validate_media_url(url, 'twitter')
    async def serve(request):
        return httpx.Response(200, headers={'Content-Type': 'image/png'}, content=b'png-bytes')
    monkeypatch.setattr(media.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(serve), **kwargs))
    response = await media.stream_media('https://pbs.twimg.com/media/asset', 'twitter-123-1.jpg', 'twitter')
    assert response.headers['content-disposition'].endswith('twitter-123-1.png"')
    assert b''.join([chunk async for chunk in response.body_iterator]) == b'png-bytes'
    async def redirect(request):
        return httpx.Response(302, headers={'Location': 'https://127.0.0.1/private'})
    monkeypatch.setattr(media.httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(redirect), **kwargs))
    with pytest.raises(HTTPException) as error:
        await media.stream_media('https://video.twimg.com/file', 'video.mp4', 'twitter')
    assert error.value.status_code == 400
