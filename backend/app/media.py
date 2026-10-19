import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

SUFFIXES = ('tiktokcdn.com', 'tiktokcdn-us.com', 'tiktokcdn-eu.com', 'tiktok.com', 'byteoversea.com', 'ibytedtos.com', 'byteimg.com', 'muscdn.com', 'musical.ly', 'bytegecko.com', 'tiktokv.com')
TWITTER_HOSTS = ('pbs.twimg.com', 'video.twimg.com')
DOUYIN_SUFFIXES = ('douyinpic.com', 'douyinvod.com', 'douyincdn.com', 'zjcdn.com', 'byteimg.com', 'ibytedtos.com')
DOUYIN_HOSTS = ('api-play.amemv.com', 'aweme.snssdk.com')


async def validate_media_url(url, platform='tiktok'):
    parsed = urlparse(url)
    host = parsed.hostname or ''
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError:
        valid_port = False
    allowed = host in TWITTER_HOSTS if platform == 'twitter' else platform == 'tiktok' and any(host == suffix or host.endswith('.' + suffix) for suffix in SUFFIXES)
    if platform == 'douyin':
        allowed = host in DOUYIN_HOSTS or any(host == suffix or host.endswith('.' + suffix) for suffix in DOUYIN_SUFFIXES)
    if parsed.scheme != 'https' or parsed.username or parsed.password or not valid_port or not allowed:
        raise HTTPException(400, '媒体来源不在该平台已验证的 CDN 域名中')
    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise ValueError()
    except (OSError, ValueError):
        raise HTTPException(400, '媒体地址无法安全解析') from None


async def stream_media(url, filename, platform='tiktok'):
    client = httpx.AsyncClient(timeout=httpx.Timeout(30, read=60), follow_redirects=False, trust_env=False)
    upstream = None
    try:
        for _ in range(5):
            await validate_media_url(url, platform)
            upstream = await client.send(client.build_request('GET', url, headers={'User-Agent': 'Mozilla/5.0'}), stream=True)
            if upstream.is_redirect:
                target = upstream.headers.get('location', '')
                await upstream.aclose()
                if not target.startswith('https://'):
                    raise HTTPException(502, '媒体重定向不可用')
                url = target
                continue
            break
        if upstream is None or upstream.status_code != 200:
            raise HTTPException(502, '媒体暂时无法下载，可能已过期或受到平台限制')
        content_type = upstream.headers.get('content-type', '').split(';')[0]
        if not (content_type.startswith('image/') or content_type.startswith('video/') or content_type == 'application/octet-stream'):
            raise HTTPException(502, '平台返回的内容不是图片或视频')
        if int(upstream.headers.get('content-length', '0')) > 256 * 1024 * 1024:
            raise HTTPException(413, '本地首版暂支持 256 MB 以内的单个素材')
    except Exception as error:
        if upstream:
            await upstream.aclose()
        await client.aclose()
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(502, '连接媒体服务器失败，请稍后再试') from None

    async def chunks():
        try:
            total = 0
            async for chunk in upstream.aiter_bytes(65536):
                total += len(chunk)
                if total > 256 * 1024 * 1024:
                    raise RuntimeError('Media exceeded the configured download size limit')
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()
    extensions = {'image/webp': 'webp', 'image/png': 'png', 'image/gif': 'gif', 'image/avif': 'avif', 'image/jpeg': 'jpg', 'video/webm': 'webm', 'video/mp4': 'mp4'}
    if content_type in extensions:
        filename = filename.rsplit('.', 1)[0] + '.' + extensions[content_type]
    return StreamingResponse(chunks(), media_type=content_type, headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
