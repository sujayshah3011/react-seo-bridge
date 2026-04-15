"""Tests for cache.py"""

import pytest

from rsb.prerender.cache import SnapshotCache


@pytest.fixture
def cache(tmp_path):
    return SnapshotCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)


@pytest.mark.asyncio
async def test_cache_miss_on_empty(cache: SnapshotCache) -> None:
    assert await cache.get("https://example.com/about") is None


@pytest.mark.asyncio
async def test_set_and_get(cache: SnapshotCache) -> None:
    html = "<html><body>Hello</body></html>"
    await cache.set("https://example.com/about", html)
    assert await cache.get("https://example.com/about") == html


@pytest.mark.asyncio
async def test_query_params_ignored(cache: SnapshotCache) -> None:
    html = "<html><body>Hello</body></html>"
    await cache.set("https://example.com/about?utm_source=google", html)
    assert await cache.get("https://example.com/about") == html


@pytest.mark.asyncio
async def test_invalidate(cache: SnapshotCache) -> None:
    await cache.set("https://example.com/", "<html></html>")
    assert await cache.invalidate("https://example.com/") is True
    assert await cache.get("https://example.com/") is None


@pytest.mark.asyncio
async def test_invalidate_all(cache: SnapshotCache) -> None:
    await cache.set("https://example.com/", "<html>1</html>")
    await cache.set("https://example.com/about", "<html>2</html>")
    assert await cache.invalidate_all() == 2
    assert cache.stats()["total_entries"] == 0
