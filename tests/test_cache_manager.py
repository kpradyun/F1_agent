"""
Smoke tests for CacheManager (disk-backed via diskcache).
"""
import pytest
import tempfile
import os
from unittest.mock import patch


def make_cache(tmp_dir):
    """Create a CacheManager backed by a temp directory."""
    import diskcache
    from utils.cache_manager import CacheManager
    with patch("utils.cache_manager.CACHE_DIR", tmp_dir):
        c = CacheManager()
    return c


@pytest.fixture
def cache(tmp_path):
    c = make_cache(str(tmp_path))
    yield c
    c.close()


def test_set_and_get(cache):
    cache.set("key1", "value1", ttl_seconds=60)
    result = cache.get("key1")
    assert result == "value1"


def test_miss_returns_none(cache):
    result = cache.get("nonexistent")
    assert result is None


def test_stats_keys(cache):
    stats = cache.get_stats()
    assert "total_entries" in stats
    assert "total_size_mb" in stats
    assert "hit_rate" in stats
    assert "hits" in stats
    assert "misses" in stats


def test_clear(cache):
    cache.set("k", "v")
    cache.clear()
    assert cache.get("k") is None


def test_hit_rate_tracking(cache):
    cache.set("x", 42)
    cache.get("x")   # hit
    cache.get("y")   # miss
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == pytest.approx(50.0)
