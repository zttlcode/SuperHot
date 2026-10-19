from .base import ProviderError
from .tiktok import TikTokProvider
from .twitter import TwitterProvider
from .douyin import DouyinProvider

PROVIDERS = {'tiktok': TikTokProvider, 'twitter': TwitterProvider, 'douyin': DouyinProvider}


def provider_for(platform, key):
    factory = PROVIDERS.get(platform)
    if factory is None:
        raise ProviderError('该平台暂不支持监控')
    return factory(key)
