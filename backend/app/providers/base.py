from __future__ import annotations

from tikhub import AsyncTikHub


class ProviderError(Exception):
    def __init__(self, message='TikHub 请求失败，请稍后重试', *, permanent=False):
        super().__init__(message)
        self.permanent = permanent


def data(value):
    if hasattr(value, 'model_dump'):
        value = value.model_dump()
    if not isinstance(value, dict):
        raise ProviderError('TikHub 返回了无法识别的数据结构')
    code = value.get('code', 200)
    if str(code) not in ('0', '200'):
        messages = {'401': 'TikHub Key 无效，请在设置中更换', '402': 'TikHub 余额或额度不足', '403': 'TikHub 拒绝访问，请检查 Key 权限', '429': 'TikHub 请求限流，稍后会重试'}
        raise ProviderError(messages.get(str(code), 'TikHub 暂时未能返回有效数据'), permanent=str(code) in ('401', '402', '403'))
    for _ in range(4):
        if isinstance(value.get('data'), dict):
            value = value['data']
        else:
            break
    if value.get('status_code', 0) not in (0, '0', None):
        raise ProviderError('该账号或作品暂不可访问')
    return value


def url_from(value):
    if isinstance(value, str):
        return value if value.startswith('https://') else ''
    if isinstance(value, dict):
        urls = value.get('url_list') or value.get('urlList') or []
        return next((x for x in urls if isinstance(x, str) and x.startswith('https://')), '')
    return ''


class TikHubProvider:
    def __init__(self, key):
        self.client = AsyncTikHub(api_key=key, parse_response=False, timeout=25, max_retries=0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    async def call(self, method, **kwargs):
        try:
            return data(await method(**kwargs))
        except ProviderError:
            raise
        except Exception as error:
            status = getattr(error, 'status_code', None)
            message = {401: 'TikHub Key 无效，请在设置中更换', 402: 'TikHub 余额或额度不足', 403: 'TikHub 拒绝访问，请检查 Key 权限', 429: 'TikHub 请求限流，稍后会重试'}.get(status, 'TikHub 请求失败，请检查网络、Key 或接口状态')
            raise ProviderError(message, permanent=status in (401, 402, 403)) from None
