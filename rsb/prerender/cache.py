"""
cache.py - Disk-based HTML snapshot cache for the prerender server.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse


DEFAULT_TTL_SECONDS = 60 * 60 * 24
DEFAULT_CACHE_DIR = Path("/tmp/rsb-cache")


class SnapshotCache:
    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}

    def _cache_key(self, url: str) -> str:
        parsed = urlparse(url)
        normalised = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return hashlib.sha256(normalised.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.html"

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def get(self, url: str) -> str | None:
        key = self._cache_key(url)
        path = self._cache_path(key)

        if not path.exists():
            return None

        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            return None

        if age > self.ttl:
            return None

        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    async def set(self, url: str, html: str) -> None:
        key = self._cache_key(url)
        path = self._cache_path(key)
        tmp_path = path.with_suffix(".tmp")

        async with self._get_lock(key):
            try:
                tmp_path.write_text(html, encoding="utf-8")
                tmp_path.replace(path)
            except OSError:
                return

    async def invalidate(self, url: str) -> bool:
        key = self._cache_key(url)
        path = self._cache_path(key)
        if path.exists():
            async with self._get_lock(key):
                path.unlink(missing_ok=True)
            return True
        return False

    async def invalidate_all(self) -> int:
        deleted = 0
        for html_file in self.cache_dir.glob("*.html"):
            html_file.unlink(missing_ok=True)
            deleted += 1
        return deleted

    def stats(self) -> dict[str, str | int]:
        files = list(self.cache_dir.glob("*.html"))
        current_time = time.time()
        fresh_entries = sum(1 for file_path in files if current_time - file_path.stat().st_mtime < self.ttl)
        return {
            "total_entries": len(files),
            "fresh_entries": fresh_entries,
            "stale_entries": len(files) - fresh_entries,
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl,
        }
