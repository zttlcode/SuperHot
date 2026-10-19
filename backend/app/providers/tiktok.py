from __future__ import annotations

import re
from urllib.parse import urlparse
from .base import ProviderError, TikHubProvider, data, url_from
from .links import validate_link
from .assets import normalize_assets


def author_from(value):
    value = data(value)
    for _ in range(4):
        nested = next((value[name] for name in ('user', 'user_info', 'userInfo', 'author') if isinstance(value.get(name), dict)), None)
        if nested is None:
            break
        value = nested
    uid = str(value.get('uid') or value.get('id') or value.get('user_id') or '')
    sec = value.get('sec_uid') or value.get('secUid') or value.get('sec_user_id') or ''
    username = value.get('unique_id') or value.get('uniqueId') or value.get('username') or ''
    if not uid or not sec:
        raise ProviderError('未取得作者的稳定标识，请尝试完整主页链接')
    return {'platform': 'tiktok', 'author_id': uid, 'sec_uid': sec, 'provider_data': {'sec_uid': sec}, 'username': username, 'nickname': value.get('nickname') or username or uid, 'avatar': url_from(value.get('avatar_thumb') or value.get('avatarLarger') or value.get('avatar_medium'))}


def post_from(raw):
    identifier = str(raw.get('aweme_id') or raw.get('id') or '')
    if not identifier:
        raise ProviderError('作品数据缺少 ID，请更新适配器后重试')
    images = (raw.get('image_post_info') or {}).get('images') or (raw.get('imagePost') or {}).get('images') or raw.get('images') or []
    assets = []
    for image in images:
        url = url_from(image.get('display_image') or image.get('displayImage') or image)
        if url:
            assets.append({'url': url, 'kind': 'image'})
    video = raw.get('video') or {}
    if not assets:
        video_url = url_from(video.get('play_addr') or video.get('playAddr') or video.get('download_addr'))
        if video_url:
            assets.append({'url': video_url, 'kind': 'video'})
    created = raw.get('create_time') or raw.get('createTime') or 0
    try:
        created = float(created)
    except (TypeError, ValueError):
        created = 0
    return {'platform_id': identifier, 'text': raw.get('desc') or raw.get('description') or '', 'published_at': created, 'kind': 'images' if images else 'video', 'assets': normalize_assets(assets), 'cover': url_from(video.get('cover') or video.get('origin_cover')) or (assets[0]['url'] if images and assets else ''), 'share_url': raw.get('share_url') or (raw.get('share_info') or {}).get('share_url') or ''}


class TikTokProvider(TikHubProvider):
    async def list_posts(self, author_id, provider_data, cursor=None):
        return await self.posts(provider_data['sec_uid'], cursor or '0')

    async def resolve(self, link):
        link = validate_link(link)
        match = re.search(r'/@([^/?#]+)', urlparse(link).path)
        if match:
            return author_from(await self.call(self.client.tiktok_app_v3.handler_user_profile, unique_id=match.group(1)))
        result = await self.call(self.client.tiktok_app_v3.fetch_one_video_by_share_url, share_url=link)
        raw = result.get('aweme_detail') or result.get('aweme_details') or result
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        author = raw.get('author') or {}
        sec = author.get('sec_uid') or author.get('secUid')
        uid = author.get('uid') or author.get('id')
        if not sec and not uid:
            raise ProviderError('分享链接未返回作者，请尝试完整主页链接')
        return author_from(await self.call(self.client.tiktok_app_v3.handler_user_profile, sec_user_id=sec, user_id=str(uid) if uid else None))

    async def posts(self, sec_uid, cursor='0'):
        result = await self.call(self.client.tiktok_app_v3.fetch_user_post_videos, sec_user_id=sec_uid, max_cursor=int(cursor), count=20, sort_type=0)
        raw = result.get('aweme_list')
        if raw is None:
            raw = result.get('itemList')
        if raw is None or not isinstance(raw, list):
            raise ProviderError('作品列表结构不匹配，未将其当作空列表处理')
        return [post_from(x) for x in raw], str(result.get('max_cursor', result.get('cursor', '0'))), bool(result.get('has_more', result.get('hasMore', False)))

    async def detail(self, identifier):
        result = await self.call(self.client.tiktok_app_v3.fetch_one_video, aweme_id=identifier)
        raw = result.get('aweme_detail') or result.get('aweme_details') or result
        if isinstance(raw, list):
            raw = raw[0] if raw else {}
        return post_from(raw)
