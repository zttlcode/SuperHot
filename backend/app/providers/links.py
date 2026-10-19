"""Parse official links locally; never resolve arbitrary user-supplied URLs."""
import re
from urllib.parse import parse_qs, urlparse, urlunparse
from .base import ProviderError

DOUYIN_HOSTS = frozenset(('douyin.com', 'www.douyin.com', 'm.douyin.com', 'v.douyin.com', 'iesdouyin.com', 'www.iesdouyin.com'))


def douyin_target(link):
    parsed = urlparse(link)
    if parsed.hostname not in DOUYIN_HOSTS:
        raise ProviderError('请使用抖音官方主页或作品链接')
    path = parsed.path.rstrip('/')
    if parsed.hostname == 'v.douyin.com':
        if re.fullmatch(r'/[A-Za-z0-9_-]{1,100}', path):
            return 'short', ''
        raise ProviderError('抖音分享链接格式无效')
    modal = parse_qs(parsed.query).get('modal_id')
    if modal:
        if len(modal) == 1 and modal[0].isdigit():
            return 'post', modal[0]
        raise ProviderError('抖音作品 ID 格式无效')
    post = re.fullmatch(r'/(?:share/)?(?:video|note)/(\d+)', path)
    if post:
        return 'post', post.group(1)
    profile = re.fullmatch(r'/(?:share/)?user/([A-Za-z0-9_.=-]{1,256})', path)
    if profile:
        identifier = profile.group(1)
        return ('uid' if identifier.isdigit() else 'sec_uid'), identifier
    raise ProviderError('请使用抖音作者主页或具体作品链接')


def detect_link(value):
    found = re.search(r'https://[^\s<>"\u3002]+', value.strip())
    if not found:
        raise ProviderError('请粘贴 HTTPS TikTok、Twitter/X 或抖音主页、作品链接')
    parsed = urlparse(found.group(0).rstrip('.,，)）'))
    host = (parsed.hostname or '').lower()
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
    if parsed.username or parsed.password or not valid_port:
        raise ProviderError('平台链接格式无效')
    if host == 'tiktok.com' or host.endswith('.tiktok.com'):
        return 'tiktok', urlunparse(parsed)
    if host in DOUYIN_HOSTS:
        douyin_target(urlunparse(parsed))
        return 'douyin', urlunparse(parsed._replace(scheme='https', netloc=host, fragment=''))
    if host in ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com', 'mobile.twitter.com'):
        path = parsed.path.rstrip('/')
        status = re.fullmatch(r'/(?:[A-Za-z0-9_]{1,15}|i/web|i)/status/(\d+)(?:/(?:photo|video)/\d+)?', path)
        username = path.lstrip('/')
        reserved = {'home', 'explore', 'search', 'settings', 'notifications', 'messages', 'i', 'intent', 'compose', 'login', 'signup', 'share'}
        if not status and (not re.fullmatch(r'[A-Za-z0-9_]{1,15}', username) or username.lower() in reserved):
            raise ProviderError('请使用 Twitter/X 作者主页或具体帖子链接')
        return 'twitter', 'https://x.com' + path
    raise ProviderError('仅支持 TikTok、Twitter/X 或抖音官方 HTTPS 链接')


def validate_link(value):
    platform, link = detect_link(value)
    if platform != 'tiktok':
        raise ProviderError('请使用 TikTok 主页或作品链接')
    return link
