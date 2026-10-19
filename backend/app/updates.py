import platform
import time
from importlib.metadata import version
import httpx
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from fastapi import HTTPException

cache = None


async def check_update(force=False):
    global cache
    if cache and time.time() - cache['checked_at'] < 3600 and not force:
        return {**cache, 'current': version('tikhub')}
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        try:
            response = await client.get('https://api.github.com/repos/TikHub/TikHub-API-Python-SDK/releases/latest', headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'SuperHot/0.1'})
            response.raise_for_status()
            release = response.json()
            target = Version(release['tag_name'].removeprefix('v'))
            if target.is_prerelease or target.is_devrelease or release.get('prerelease') or release.get('draft'):
                raise ValueError()
            package = await client.get(f'https://pypi.org/pypi/tikhub/{target}/json')
            available = package.status_code == 200
            compatible = False
            if available:
                metadata = package.json()
                files = [item for item in metadata.get('urls', []) if not item.get('yanked')]
                compatible = bool(files) and Version(platform.python_version()) in SpecifierSet(metadata['info'].get('requires_python') or '')
            current = Version(version('tikhub'))
            breaking = target.major != current.major
            cache = {'current': str(current), 'latest': str(target), 'notes': (release.get('body') or '')[:20000], 'url': release.get('html_url', 'https://github.com/TikHub/TikHub-API-Python-SDK/releases'), 'checked_at': time.time(), 'available': available, 'can_update': target > current and compatible and not breaking, 'blocked': '主版本升级需要先人工适配' if breaking else '等待 PyPI 软件包发布或 Python 兼容性确认' if target > current and not compatible else None}
            return cache
        except (httpx.HTTPError, KeyError, ValueError, InvalidVersion):
            raise HTTPException(502, '版本检查失败，请稍后重试；未将其视为已是最新') from None
