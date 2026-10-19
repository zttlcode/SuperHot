"""Compatibility exports for integrations using the original TikTok adapter."""
from .providers.base import ProviderError, data, url_from
from .providers.links import validate_link
from .providers.tiktok import TikTokProvider, author_from, post_from
