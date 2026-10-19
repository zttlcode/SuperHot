"""Twitter Web API adapter. Keep upstream payloads out of the shared worker."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from .base import ProviderError, TikHubProvider, data, url_from
from .assets import normalize_assets, stable_url_id
from .links import detect_link


def unwrap(value):
    for _ in range(8):
        if not isinstance(value, dict):
            break
        if value.get('rest_id') or value.get('id_str') or value.get('id') or value.get('tweet_id'):
            break
        child = next((value[key] for key in ('result', 'tweet', 'user', 'tweetResult', 'tweet_results', 'user_results')
                      if isinstance(value.get(key), dict)), None)
        if child is None:
            break
        value = child
    return value if isinstance(value, dict) else {}


def twitter_author(value, *, allow_partial=False):
    value = unwrap(value)
    legacy = value.get('legacy') or value
    core = value.get('core') or {}
    identifier = str(value.get('rest_id') or value.get('id_str') or value.get('id') or value.get('user_id') or '')
    username = legacy.get('screen_name') or core.get('screen_name') or value.get('username') or ''
    if not identifier.isdigit() or (not re.fullmatch(r'[A-Za-z0-9_]{1,15}', username) and not (allow_partial and not username)):
        raise ProviderError('未取得 Twitter 作者的稳定标识，请尝试完整主页链接')
    return {'platform': 'twitter', 'author_id': identifier, 'sec_uid': None, 'provider_data': {},
            'username': username, 'nickname': legacy.get('name') or core.get('name') or username or identifier,
            'avatar': url_from(legacy.get('profile_image_url_https') or (value.get('avatar') or {}).get('image_url'))}


def tweet_author(raw):
    core = raw.get('core') or {}
    user = core.get('user_results') or raw.get('user') or raw.get('author')
    # Timeline author objects can have a stable ID but null names/avatars.
    # Keep the ID for ownership filtering; profile resolution still needs a name.
    return twitter_author(user, allow_partial=True) if isinstance(user, dict) else None


def published(value):
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            stamp = float(value)
            stamp = stamp / 1000 if stamp > 1e12 else stamp
        else:
            try:
                moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                moment = parsedate_to_datetime(value)
            stamp = moment.replace(tzinfo=timezone.utc).timestamp() if moment.tzinfo is None else moment.timestamp()
        if not 0 < stamp < 1e11:
            raise ValueError()
        return stamp
    except (TypeError, ValueError, AttributeError, OverflowError):
        raise ProviderError('Twitter 帖子发布时间无法识别，未将其当作新作品处理') from None


def canonical(identifier, username=''):
    return f'https://x.com/{username}/status/{identifier}' if username else f'https://x.com/i/web/status/{identifier}'


def twitter_asset(raw):
    kind = raw.get('type') or raw.get('kind')
    kind = {'photo': 'image', 'gif': 'animated_gif'}.get(kind, kind)
    if kind not in ('image', 'video', 'animated_gif'):
        raise ProviderError('Twitter 返回了尚未支持的媒体类型')
    preview = url_from(raw.get('media_url_https') or raw.get('preview_image_url') or raw.get('thumbnail_url'))
    variants = (raw.get('video_info') or {}).get('variants') or raw.get('variants') or []
    if not isinstance(variants, list):
        raise ProviderError('Twitter 视频变体结构无法识别')
    candidates = [item for item in variants if isinstance(item, dict) and item.get('content_type') == 'video/mp4' and url_from(item.get('url'))]
    def bitrate(item):
        try:
            return int(item.get('bitrate') or item.get('bit_rate') or 0)
        except (TypeError, ValueError):
            return 0
    if kind == 'image':
        url = url_from(raw.get('media_url_https') or raw.get('url'))
        preview = preview or url
        mime = raw.get('content_type') or ''
    else:
        variant = max(candidates, key=bitrate) if candidates else {}
        url = url_from(variant.get('url'))
        # Some compact responses provide an MP4 directly rather than variants.
        direct = url_from(raw.get('video_url') or raw.get('url'))
        if not url and direct and urlparse(direct).path.lower().endswith('.mp4'):
            url = direct
        mime = 'video/mp4' if url else ''
    identifier = str(raw.get('media_key') or raw.get('id_str') or raw.get('id') or '')
    if not identifier:
        identity_url = preview or url
        if not identity_url:
            raise ProviderError('Twitter 素材缺少稳定标识和预览地址')
        identifier = stable_url_id(identity_url)
    return {'id': identifier, 'kind': kind, 'url': url, 'preview': preview, 'mime_type': mime,
            'width': (raw.get('original_info') or {}).get('width') or raw.get('width'),
            'height': (raw.get('original_info') or {}).get('height') or raw.get('height')}


def media_items(raw, legacy):
    extended = legacy.get('extended_entities') or {}
    if not isinstance(extended, dict):
        raise ProviderError('Twitter 媒体扩展结构无法识别')
    media = extended.get('media')
    if media is None and 'media' in raw:
        media = raw['media']
    if media is None:
        entities = legacy.get('entities') or {}
        if not isinstance(entities, dict):
            raise ProviderError('Twitter 实体结构无法识别')
        media = entities.get('media', [])
    # Twitter Web's compact response groups media instead of putting type on
    # each item: media.video / media.photo / media.animated_gif.
    if isinstance(media, dict):
        aliases = {'photo': 'photo', 'photos': 'photo', 'image': 'photo', 'images': 'photo',
                   'video': 'video', 'videos': 'video', 'animated_gif': 'animated_gif',
                   'gif': 'animated_gif', 'gifs': 'animated_gif'}
        grouped = []
        for group, values in media.items():
            if group not in aliases or not isinstance(values, list):
                raise ProviderError('Twitter 媒体分组结构无法识别')
            for item in values:
                if not isinstance(item, dict):
                    raise ProviderError('Twitter 媒体条目结构无法识别')
                grouped.append(dict(item, type=item.get('type') or item.get('kind') or aliases[group]))
        media = grouped
    if not isinstance(media, list) or any(not isinstance(item, dict) for item in media):
        raise ProviderError('Twitter 媒体列表结构无法识别')
    return media


def twitter_post_type(raw):
    legacy = raw.get('legacy') or raw
    if (raw.get('retweeted') or raw.get('retweeted_tweet') or raw.get('retweeted_status_result')
            or legacy.get('retweeted_status_result') or legacy.get('retweeted_status') or raw.get('is_retweet')):
        return 'repost'
    if (raw.get('reply_to') or legacy.get('in_reply_to_status_id_str')
            or legacy.get('in_reply_to_status_id') or raw.get('is_reply')):
        return 'reply'
    if (raw.get('quoted') or raw.get('quoted_status_result') or legacy.get('quoted_status_result')
            or legacy.get('quoted_status') or legacy.get('quoted_status_id_str')
            or legacy.get('quoted_status_id') or raw.get('quoted_tweet_id') or legacy.get('is_quote_status')):
        return 'quote'
    return 'original'


def twitter_post(value):
    raw = unwrap(value)
    legacy = raw.get('legacy') or raw
    identifier = str(raw.get('rest_id') or raw.get('id_str') or raw.get('id') or raw.get('tweet_id') or '')
    if not identifier.isdigit():
        raise ProviderError('Twitter 帖子缺少有效 ID，未将其当作空内容处理')
    author = tweet_author(raw)
    note = (((raw.get('note_tweet') or {}).get('note_tweet_results') or {}).get('result') or {}).get('text')
    text = note if note is not None else legacy.get('full_text', legacy.get('text', ''))
    if not isinstance(text, str):
        raise ProviderError('Twitter 正文结构无法识别')
    media = media_items(raw, legacy)
    assets = normalize_assets([twitter_asset(item) for item in media])
    if len({asset['id'] for asset in assets}) != len(assets):
        raise ProviderError('Twitter 素材标识重复，无法安全下载')
    kinds = {item['kind'] for item in assets}
    kind = 'text' if not kinds else 'images' if kinds == {'image'} else 'video' if kinds <= {'video', 'animated_gif'} else 'mixed'
    quoted = raw.get('quoted') or raw.get('quoted_status_result') or legacy.get('quoted_status_result') or legacy.get('quoted_status')
    quote_id = legacy.get('quoted_status_id_str') or legacy.get('quoted_status_id') or raw.get('quoted_tweet_id')
    references = []
    if quoted:
        quoted = unwrap(quoted)
        quote_id = quoted.get('rest_id') or quoted.get('id_str') or quoted.get('id') or quoted.get('tweet_id') or quote_id
        try:
            quoted_author = tweet_author(quoted)
        except ProviderError:
            # A quoted author can be unavailable while the quoting post is public.
            quoted_author = None
        quote_legacy = quoted.get('legacy') or quoted
        if quote_id:
            references.append({'kind': 'quote', 'id': str(quote_id), 'username': quoted_author['username'] if quoted_author else '',
                               'text': quote_legacy.get('full_text') or quote_legacy.get('text') or '',
                               'url': canonical(str(quote_id), quoted_author['username'] if quoted_author else '')})
    elif quote_id:
        references.append({'kind': 'quote', 'id': str(quote_id), 'username': '', 'text': '', 'url': canonical(str(quote_id))})
    return {'platform_id': identifier, 'text': text, 'published_at': published(legacy.get('created_at') or raw.get('published_at')),
            'kind': kind, 'post_type': twitter_post_type(raw),
            'references': references, 'assets': assets, 'cover': next((item['preview'] for item in assets if item['preview']), ''),
            'share_url': canonical(identifier, author['username'] if author else '')}


def instructions_in(value):
    """Find the timeline container, never walk into quoted/reposted content."""
    if not isinstance(value, dict):
        return None
    if isinstance(value.get('instructions'), list):
        return value['instructions']
    for key in ('data', 'user', 'result', 'timeline', 'timeline_v2', 'threaded_conversation_with_injections_v2'):
        found = instructions_in(value.get(key))
        if found is not None:
            return found
    return None


def timeline_items(instructions):
    items, cursor = [], None
    for instruction in instructions:
        if not isinstance(instruction, dict):
            raise ProviderError('Twitter 时间线指令结构无法识别')
        if instruction.get('type') not in ('TimelineAddEntries', 'TimelinePinEntry', 'TimelineReplaceEntry', 'TimelineAddToModule', 'TimelineTerminateTimeline', 'TimelineClearCache', 'TimelineShowAlert'):
            raise ProviderError('Twitter 时间线指令已变化，请更新平台适配器')
        entries = instruction.get('entries') or ([instruction['entry']] if isinstance(instruction.get('entry'), dict) else [])
        if instruction.get('type') == 'TimelineAddToModule':
            entries = [{'content': {'items': instruction.get('moduleItems', [])}}]
        for entry in entries:
            content = entry.get('content') or {}
            if content.get('cursorType', '').lower() == 'bottom':
                cursor = content.get('value')
                continue
            subitems = [content.get('itemContent') or content]
            subitems.extend((part.get('item') or part).get('itemContent') or {} for part in content.get('items', []))
            for item in subitems:
                if item.get('promotedMetadata'):
                    continue
                tweet = item.get('tweet_results') or item.get('tweetResult')
                if tweet is not None:
                    result = unwrap(tweet)
                    if result.get('__typename') not in ('TweetTombstone', 'TweetUnavailable'):
                        items.append(result)
    if cursor is not None and not isinstance(cursor, str):
        raise ProviderError('Twitter 分页游标结构无法识别')
    return items, cursor or None


def twitter_page(value):
    value = data(value)
    instructions = instructions_in(value)
    if instructions is not None:
        items, cursor = timeline_items(instructions)
        return items, cursor, bool(cursor)
    for key in ('timeline', 'tweets', 'posts'):
        if key in value:
            if not isinstance(value[key], list):
                break
            if value.get('status') not in (None, 'ok', 'success'):
                raise ProviderError('Twitter 暂未返回有效时间线，请稍后重试')
            cursor = value.get('next_cursor') or value.get('cursor') or None
            if cursor is not None and not isinstance(cursor, str):
                break
            more = bool(value.get('has_more', bool(cursor)))
            if more and not cursor:
                break
            items = list(value[key])
            pinned = value.get('pinned')
            if pinned:
                if not isinstance(pinned, dict):
                    raise ProviderError('Twitter 置顶帖子结构无法识别')
                items.insert(0, pinned)
            return items, cursor, more
    raise ProviderError('Twitter 帖子列表结构不匹配，未将其当作空列表处理')


class TwitterProvider(TikHubProvider):
    async def resolve(self, link):
        platform, link = detect_link(link)
        if platform != 'twitter':
            raise ProviderError('请使用 Twitter/X 主页或帖子链接')
        match = re.search(r'/status/(\d+)', urlparse(link).path)
        if match:
            raw = await self.raw_detail(match.group(1))
            author = tweet_author(raw)
            if author is None:
                raise ProviderError('帖子未返回作者资料，请尝试完整主页链接')
            if not author['username']:
                result = await self.call(self.client.twitter_web.fetch_user_profile, rest_id=int(author['author_id']))
                return twitter_author(result)
            return author
        result = await self.call(self.client.twitter_web.fetch_user_profile, screen_name=urlparse(link).path.strip('/'))
        return twitter_author(result)

    async def list_posts(self, author_id, provider_data, cursor=None):
        result = await self.call(self.client.twitter_web.fetch_user_post_tweet, rest_id=int(author_id), cursor=cursor)
        raw_items, next_cursor, more = twitter_page(result)
        items = []
        for raw in raw_items:
            raw = unwrap(raw)
            if twitter_post_type(raw) not in ('original', 'quote'):
                continue
            author = tweet_author(raw)
            post = twitter_post(raw)
            if (author is None or author['author_id'] == author_id) and post['post_type'] in ('original', 'quote'):
                items.append(post)
        return items, next_cursor, more

    async def raw_detail(self, identifier):
        value = await self.call(self.client.twitter_web.fetch_tweet_detail, tweet_id=identifier)
        instructions = instructions_in(value)
        candidates = timeline_items(instructions)[0] if instructions is not None else [unwrap(value)]
        for raw in candidates:
            if str(raw.get('rest_id') or raw.get('id_str') or raw.get('id') or raw.get('tweet_id') or '') == identifier:
                return raw
        raise ProviderError('未找到该推文，可能已删除或暂不可访问')

    async def detail(self, identifier):
        return twitter_post(await self.raw_detail(identifier))
