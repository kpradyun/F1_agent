"""
Cache Manager for F1 Agent
Persistent disk-backed cache using diskcache.
"""
from __future__ import annotations
import logging
from typing import Any, Optional

import diskcache

from config.settings import CACHE_DIR

logger = logging.getLogger("CacheManager")

__all__ = ["CacheManager", "get_cache"]


class CacheManager:
    """Disk-backed cache with TTL and statistics tracking."""

    def __init__(self) -> None:
        self._cache: diskcache.Cache = diskcache.Cache(CACHE_DIR)
        self.hits: int = 0
        self.misses: int = 0

    def get(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        value = self._cache.get(key, default=None)
        if value is None:
            self.misses += 1
            logger.debug(f"Cache MISS: {key}")
        else:
            self.hits += 1
            logger.debug(f"Cache HIT: {key}")
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store value in cache with TTL expiry."""
        self._cache.set(key, value, expire=ttl_seconds)
        logger.debug(f"Cache SET: {key}")

    def clear(self) -> None:
        """Evict all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Return cache statistics dict."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            "total_entries": len(self._cache),
            "total_size_mb": self._cache.volume() / (1024 * 1024),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }

    def close(self) -> None:
        """Close the underlying disk cache."""
        self._cache.close()


_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Return singleton CacheManager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
