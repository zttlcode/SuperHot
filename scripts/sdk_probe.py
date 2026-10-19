"""Offline compatibility gate; never calls a paid TikHub endpoint."""
import asyncio
import inspect
import json
import sys
from importlib.metadata import version
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from tikhub import AsyncTikHub
from app.provider import author_from, post_from
from app.main import app
from app.providers.twitter import twitter_page, twitter_post, twitter_post_type
from app.providers.douyin import douyin_author, douyin_page, douyin_post, detail_from


async def main():
    async with AsyncTikHub(api_key='offline-compatibility-probe', max_retries=0) as client:
        resource = client.tiktok_app_v3
        for method, parameters in [('handler_user_profile', ['unique_id', 'sec_user_id']), ('fetch_user_post_videos', ['sec_user_id', 'max_cursor', 'count', 'sort_type']), ('fetch_one_video_by_share_url', ['share_url']), ('fetch_one_video', ['aweme_id'])]:
            signature = inspect.signature(getattr(resource, method))
            assert all(name in signature.parameters for name in parameters), method
        for method, parameters in [('fetch_user_profile', ['screen_name', 'rest_id']), ('fetch_user_post_tweet', ['rest_id', 'cursor']), ('fetch_tweet_detail', ['tweet_id'])]:
            signature = inspect.signature(getattr(client.twitter_web, method))
            assert all(name in signature.parameters for name in parameters), method
        for method, parameters in [('handler_user_profile', ['sec_user_id']), ('fetch_user_post_videos', ['sec_user_id', 'max_cursor', 'count', 'sort_type', 'channel']), ('fetch_one_video_v2', ['aweme_id'])]:
            signature = inspect.signature(getattr(client.douyin_app_v3, method))
            assert all(name in signature.parameters for name in parameters), method
        assert 'uid' in inspect.signature(client.douyin_web.fetch_user_profile_by_uid).parameters
    assert author_from({'data': {'user': {'uid': '1', 'sec_uid': 'sec', 'unique_id': 'sample'}}})['author_id'] == '1'
    assert post_from({'aweme_id': '1', 'desc': 'sample', 'create_time': 1, 'video': {'play_addr': {'url_list': ['https://example.com/video']}}})['assets'][0]['kind'] == 'video'
    assert app.openapi()['info']['title'] == 'SuperHot API'
    sample = json.loads((Path(__file__).resolve().parents[1] / 'backend/tests/fixtures/twitter_timeline.json').read_text(encoding='utf-8'))
    tweets, cursor, more = twitter_page(sample)
    assert len(tweets) == 2 and cursor == 'opaque-cursor/+=do-not-convert' and more
    assert twitter_post(tweets[0])['kind'] == 'text'
    mixed = twitter_post(tweets[1])
    assert mixed['kind'] == 'mixed' and mixed['assets'][1]['url'].endswith('sample-high.mp4')
    compact = json.loads((Path(__file__).resolve().parents[1] / 'backend/tests/fixtures/twitter_compact_timeline.json').read_text(encoding='utf-8'))
    tweets, cursor, more = twitter_page(compact)
    assert len(tweets) == 5 and more and cursor == 'opaque-sanitized-next_cursor/+='
    compact_posts = [twitter_post(tweet) for tweet in tweets if twitter_post_type(tweet) in ('original', 'quote')]
    assert len(compact_posts) == 3 and compact_posts[0]['assets'][0]['kind'] == 'video'
    assert compact_posts[2]['post_type'] == 'quote' and compact_posts[2]['assets'] == []
    douyin = json.loads((Path(__file__).resolve().parents[1] / 'backend/tests/fixtures/douyin_app_v3.json').read_text(encoding='utf-8'))
    assert douyin_author(douyin['profile'])['platform'] == 'douyin'
    videos, cursor, more = douyin_page(douyin['posts'])
    assert len(videos) == 2 and cursor == '1792404000000' and more
    assert douyin_post(videos[1])['kind'] == 'images' and len(douyin_post(videos[1])['assets']) == 2
    assert douyin_post(detail_from(douyin['detail_video'], videos[0]['aweme_id']))['assets'][0]['id'] == 'video'
    if len(sys.argv) > 1:
        assert version('tikhub') == sys.argv[1]
    print('Offline SDK compatibility checks passed. This check does not call live upstream endpoints.')


asyncio.run(main())
