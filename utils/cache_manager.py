"""
Cache Manager for F1 Agent
Simple in-memory cache with statistics tracking
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger("CacheManager")


class CacheManager:
    """Simple cache manager with TTL and statistics"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str, ttl_seconds: int = 300) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            
            if (datetime.now() - timestamp).total_seconds() < ttl_seconds:
                self.hits += 1
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        self.misses += 1
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any):
        """Store value in cache with current timestamp"""
        self._cache[key] = (value, datetime.now())
        logger.debug(f"Cache SET: {key}")
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        total_size_bytes = sum(len(str(v)) for v, _ in self._cache.values())
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        return {
            'total_entries': len(self._cache),
            'total_size_mb': total_size_mb,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'categories': list(self._cache.keys())[:10]
        }


# Singleton instance
_cache_instance = None


def get_cache() -> CacheManager:
    """Get singleton cache manager instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance
