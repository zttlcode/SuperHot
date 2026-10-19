"""Stable media identity shared by the API, legacy records and adapters."""
import hashlib
from urllib.parse import urlparse


def media_id(asset, index):
    if asset.get('id'):
        return str(asset['id'])
    # Legacy TikTok records did not store IDs. Keep their existing ordering.
    return 'video' if asset.get('kind') == 'video' and index == 0 else f"image-{index + 1}"


def stable_url_id(url):
    parsed = urlparse(url)
    return hashlib.sha256(((parsed.hostname or '') + parsed.path).encode()).hexdigest()[:24]


def normalize_assets(assets):
    return [dict(asset, id=media_id(asset, index), order=index,
                 downloadable=bool(asset.get('url')),
                 preview=asset.get('preview') or (asset.get('url', '') if asset.get('kind') == 'image' else ''))
            for index, asset in enumerate(assets)]


def asset_summaries(assets):
    # Do not expose download URLs or upstream video variants to clients.
    return [{key: asset.get(key) for key in ('id', 'kind', 'mime_type', 'order', 'preview', 'downloadable')}
            for asset in normalize_assets(assets)]
