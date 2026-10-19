"""Douyin App V3 adapter, independent from TikTok's response contract."""
from __future__ import annotations

import hashlib
from urllib.parse import urlparse
from .assets import normalize_assets
from .base import ProviderError, TikHubProvider, data, url_from
from .links import detect_link, douyin_target
from .share_links import expand_douyin_link
from .tiktok import author_from


def douyin_author(value):
    author = author_from(value)
    if not author['author_id'].isdigit():
        raise ProviderError('抖音作者缺少有效用户 ID')
    author['platform'] = 'douyin'
    author['provider_data'] = {'sec_uid': author['sec_uid'], 'channel': 'lite'}
    # Some accounts have no public unique_id. Identity remains uid/sec_uid.
    author['username'] = author['username'] or author['author_id']
    return author


def image_asset(image, index):
    if not isinstance(image, dict):
        raise ProviderError('抖音图片结构无法识别')
    body = image.get('display_image') or image.get('displayImage') or image
    if not isinstance(body, dict):
        raise ProviderError('抖音图片地址结构无法识别')
    url = url_from({'url_list': body.get('download_url_list') or []}) or url_from(body)
    uri = image.get('image_id') or image.get('uri') or body.get('uri')
    if not uri and url:
        # CDN hosts/signatures and resize suffixes can change between list and
        # detail. The underlying image path remains the stable media identity.
        uri = urlparse(url).path.split('~', 1)[0].split('@', 1)[0]
    identifier = 'image-' + hashlib.sha256(str(uri).encode()).hexdigest()[:24] if uri else f'image-{index + 1}'
    return {'id': identifier, 'kind': 'image', 'url': url, 'preview': url,
            'mime_type': '', 'width': body.get('width'), 'height': body.get('height')}


def douyin_post(raw):
    if not isinstance(raw, dict):
        raise ProviderError('抖音作品结构无法识别')
    identifier = str(raw.get('aweme_id') or raw.get('id') or '')
    if not identifier.isdigit():
        raise ProviderError('抖音作品缺少有效 ID')
    try:
        timestamp = float(raw.get('create_time') or raw.get('createTime') or 0)
        if not 0 < timestamp < 1e11:
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        raise ProviderError('抖音作品发布时间无法识别，未将其当作新作品处理') from None
    images = raw.get('images')
    if images is None:
        info = raw.get('image_post_info') or raw.get('imagePost') or {}
        if not isinstance(info, dict):
            raise ProviderError('抖音图文结构无法识别')
        images = info.get('images') or []
    if not isinstance(images, list):
        raise ProviderError('抖音图片列表结构无法识别')
    gallery = bool(images) or str(raw.get('aweme_type')) in ('68', '150')
    video = raw.get('video') or {}
    if not isinstance(video, dict):
        raise ProviderError('抖音视频结构无法识别')
    if gallery:
        assets = [image_asset(image, index) for index, image in enumerate(images)]
    else:
        url = url_from(video.get('play_addr')) or url_from(video.get('play_addr_h264')) or url_from(video.get('download_addr'))
        # Keep a non-downloadable video entry if access to its media is limited.
        assets = [{'id': 'video', 'kind': 'video', 'url': url, 'mime_type': 'video/mp4',
                   'preview': url_from(video.get('cover') or video.get('origin_cover'))}]
    assets = normalize_assets(assets)
    if len({asset['id'] for asset in assets}) != len(assets):
        raise ProviderError('抖音素材标识重复，无法安全匹配下载内容')
    text = raw.get('desc') or raw.get('description') or ''
    if not isinstance(text, str):
        raise ProviderError('抖音文案结构无法识别')
    kind = 'images' if gallery else 'video'
    cover = (assets[0]['preview'] if gallery and assets else '') or url_from(video.get('cover') or video.get('origin_cover'))
    return {'platform_id': identifier, 'text': text, 'published_at': timestamp, 'kind': kind,
            'assets': assets, 'cover': cover, 'share_url': f'https://www.douyin.com/{"note" if gallery else "video"}/{identifier}'}


def douyin_page(value):
    value = data(value)
    items = value.get('aweme_list')
    if not isinstance(items, list):
        raise ProviderError('抖音作品列表结构不匹配，未将其当作空列表处理')
    more = value.get('has_more')
    if type(more) not in (bool, int, str) or more not in (False, True, 0, 1, '0', '1'):
        raise ProviderError('抖音分页状态无法识别')
    more = more in (True, 1, '1')
    cursor = value.get('max_cursor')
    if cursor is not None and (isinstance(cursor, bool) or not str(cursor).isdigit()):
        raise ProviderError('抖音分页游标无法识别')
    if more and (cursor is None or int(cursor) == 0):
        raise ProviderError('抖音分页缺少下一页游标')
    return items, str(cursor) if cursor is not None else None, more


def detail_from(value, identifier):
    value = data(value)
    raw = value.get('aweme_detail')
    if raw is None:
        raw = value.get('aweme_details')
    if raw is None:
        raw = value.get('aweme_list')
    if raw is None and value.get('aweme_id'):
        raw = value
    candidates = raw if isinstance(raw, list) else [raw]
    for item in candidates:
        if isinstance(item, dict) and str(item.get('aweme_id') or item.get('id') or '') == identifier:
            return item
    raise ProviderError('抖音作品暂不可访问、已删除或未返回详情')


class DouyinProvider(TikHubProvider):
    async def resolve(self, link):
        platform, link = detect_link(link)
        if platform != 'douyin':
            raise ProviderError('请使用抖音主页或作品链接')
        kind, identifier = douyin_target(await expand_douyin_link(link))
        if kind == 'post':
            raw = await self.raw_detail(identifier)
            author = raw.get('author')
            if not isinstance(author, dict):
                raise ProviderError('抖音作品未返回作者资料，请尝试主页链接')
            return douyin_author(author)
        if kind == 'uid':
            result = await self.call(self.client.douyin_web.fetch_user_profile_by_uid, uid=identifier)
        else:
            result = await self.call(self.client.douyin_app_v3.handler_user_profile, sec_user_id=identifier)
        return douyin_author(result)

    async def list_posts(self, author_id, provider_data, cursor=None):
        sec_uid = provider_data.get('sec_uid')
        channel = provider_data.get('channel', 'lite')
        if not sec_uid or channel not in ('normal', 'lite') or (cursor is not None and not str(cursor).isdigit()):
            raise ProviderError('抖音作者标识或分页游标无效，请重新识别作者')
        result = await self.call(self.client.douyin_app_v3.fetch_user_post_videos, sec_user_id=sec_uid,
                                 max_cursor=int(cursor or 0), count=20, sort_type=0, channel=channel)
        items, next_cursor, more = douyin_page(result)
        posts = []
        for raw in items:
            if not isinstance(raw, dict):
                raise ProviderError('抖音作品条目结构无法识别')
            author = raw.get('author') or {}
            if not isinstance(author, dict):
                raise ProviderError('抖音作品作者结构无法识别')
            if author.get('uid') and str(author['uid']) != author_id:
                continue
            posts.append(douyin_post(raw))
        return posts, next_cursor, more

    async def raw_detail(self, identifier):
        result = await self.call(self.client.douyin_app_v3.fetch_one_video_v2, aweme_id=identifier)
        return detail_from(result, identifier)

    async def detail(self, identifier):
        return douyin_post(await self.raw_detail(identifier))
