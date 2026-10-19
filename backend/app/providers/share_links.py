"""Bounded, credential-free expansion of official Douyin share links."""
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse
import httpx
from .base import ProviderError
from .links import detect_link, douyin_target


async def expand_douyin_link(link):
    async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
        for request_index in range(6):
            platform, link = detect_link(link)
            if platform != 'douyin':
                raise ProviderError('抖音分享链接跳转到了不支持的地址')
            kind, _ = douyin_target(link)
            if kind != 'short':
                return link
            if request_index == 5:
                break
            host = urlparse(link).hostname
            try:
                addresses = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
                if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                    raise ProviderError('抖音分享地址无法安全解析')
                response = await client.send(client.build_request('GET', link, headers={'User-Agent': 'Mozilla/5.0'}), stream=True)
            except (OSError, httpx.RequestError):
                raise ProviderError('抖音分享链接暂时无法打开，请尝试完整主页或作品链接') from None
            try:
                if not response.is_redirect or not response.headers.get('location'):
                    raise ProviderError('抖音分享链接未返回有效跳转，请尝试完整主页或作品链接')
                link = urljoin(link, response.headers['location'])
            finally:
                await response.aclose()
        raise ProviderError('抖音分享链接跳转次数过多，请尝试完整主页或作品链接')
