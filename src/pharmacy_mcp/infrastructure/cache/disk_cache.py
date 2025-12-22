"""Disk-based cache service."""

import json
from pathlib import Path
from typing import Any

from diskcache import Cache

from pharmacy_mcp.config import settings


class CacheService:
    """Disk-based cache service using diskcache."""
    
    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = Path(cache_dir or settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self.cache_dir))
        self.default_ttl = settings.cache_ttl_seconds
    
    def get(self, key: str) -> Any | None:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        value = self._cache.get(key)
        if value is not None and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        ttl = ttl or self.default_ttl
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        return self._cache.set(key, value, expire=ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key existed
        """
        return self._cache.delete(key)
    
    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
    
    def get_or_set(
        self,
        key: str,
        default_factory: callable,
        ttl: int | None = None
    ) -> Any:
        """
        Get from cache or set with default factory.
        
        Args:
            key: Cache key
            default_factory: Callable to generate value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or newly set value
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = default_factory()
        self.set(key, value, ttl)
        return value
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache
    
    def close(self) -> None:
        """Close cache connection."""
        self._cache.close()
