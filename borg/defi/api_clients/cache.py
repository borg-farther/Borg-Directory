"""
TTL Cache for DeFi API responses.

In-memory cache with timestamp-based expiration and LRU eviction.
Thread-safe for typical async usage.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TTLCache:
    """
    In-memory cache with TTL and LRU eviction.

    Features:
    - Timestamp-based expiration
    - LRU eviction when max_size exceeded
    - Thread-safe for async operations
    - Cache key: (url, params) tuple

    Usage:
        cache = TTLCache(ttl=300, max_size=1000)  # 5 min TTL, 1000 max entries
        key = ("https://api.example.com/endpoint", ("param", "value"))
        cache.set(key, {"data": "value"})
        result = cache.get(key)
    """

    DEFAULT_TTL = 300  # 5 minutes
    DEFAULT_MAX_SIZE = 1000

    def __init__(self, ttl: int = DEFAULT_TTL, max_size: int = DEFAULT_MAX_SIZE):
        """
        Initialize TTLCache.

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
            max_size: Maximum number of entries (default: 1000)
        """
        self._ttl = ttl
        self._max_size = max_size
        self._cache: OrderedDict[Tuple[str, Any], Tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> int:
        """Get the TTL in seconds."""
        return self._ttl

    @property
    def max_size(self) -> int:
        """Get the maximum cache size."""
        return self._max_size

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def _make_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> Tuple[str, Any]:
        """
        Create a cache key from URL and params.

        Args:
            url: The request URL
            params: Optional query parameters dict

        Returns:
            Tuple key for caching
        """
        # Sort params for consistent key generation
        if params:
            sorted_params = tuple(sorted(params.items()))
        else:
            sorted_params = ()
        return (url, sorted_params)

    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cached entry has expired."""
        return time.time() - timestamp > self._ttl

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get cached value if exists and not expired.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(url, params)

        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]

        if self._is_expired(timestamp):
            # Expired - remove and return None
            del self._cache[key]
            logger.debug(f"Cache expired for {url}")
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        logger.debug(f"Cache hit for {url}")
        return value

    def set(self, url: str, value: Any, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Store value in cache with current timestamp.

        Args:
            url: The request URL
            value: The value to cache
            params: Optional query parameters
        """
        key = self._make_key(url, params)

        # If key exists, remove it first (will be re-added at end)
        if key in self._cache:
            del self._cache[key]

        # Evict oldest entries if at capacity
        while len(self._cache) >= self._max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Cache evicted oldest entry: {evicted_key[0]}")

        # Add new entry
        self._cache[key] = (value, time.time())
        logger.debug(f"Cache set for {url}")

    async def get_async(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Async version of get - thread-safe.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            return self.get(url, params)

    async def set_async(self, url: str, value: Any, params: Optional[Dict[str, Any]] = None) -> None:
        """
        Async version of set - thread-safe.

        Args:
            url: The request URL
            value: The value to cache
            params: Optional query parameters
        """
        async with self._lock:
            self.set(url, value, params)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def clear_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if self._is_expired(timestamp)
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def invalidate(self, url: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            url: The request URL
            params: Optional query parameters

        Returns:
            True if entry was found and removed, False otherwise
        """
        key = self._make_key(url, params)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated for {url}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        total_entries = len(self._cache)
        expired_entries = sum(
            1 for _, timestamp in self._cache.values()
            if self._is_expired(timestamp)
        )

        return {
            "size": total_entries,
            "max_size": self._max_size,
            "ttl": self._ttl,
            "expired_entries": expired_entries,
            "valid_entries": total_entries - expired_entries,
        }


def cached_request(ttl: int = TTLCache.DEFAULT_TTL, max_size: int = TTLCache.DEFAULT_MAX_SIZE):
    """
    Decorator to cache async API responses.

    Works on methods of classes that have a _cache attribute or will receive one.

    The decorated method must be an async instance method that takes
    (self, url, **kwargs) and returns the response dict.

    Cache key is (url, sorted kwargs.items()).

    Args:
        ttl: Time-to-live in seconds (default: 300)
        max_size: Maximum cache entries (default: 1000)

    Usage:
        class MyClient:
            def __init__(self):
                self._cache = TTLCache(ttl=300)

            @cached_request()
            async def get(self, url, **kwargs):
                # actual HTTP request
                return await self._fetch(url, **kwargs)
    """
    def decorator(func):
        async def wrapper(self, url, **kwargs):
            # Get or create cache on instance
            if not hasattr(self, '_cache') or self._cache is None:
                self._cache = TTLCache(ttl=ttl, max_size=max_size)

            # Check if caching is disabled (ttl=0)
            cache: TTLCache = self._cache
            if cache.ttl == 0:
                return await func(self, url, **kwargs)

            # Try to get from cache
            cached_value = cache.get(url, kwargs)
            if cached_value is not None:
                return cached_value

            # Make the actual request
            result = await func(self, url, **kwargs)

            # Cache the result (even if None - helps avoid repeated failed requests)
            if result is not None:
                cache.set(url, result, kwargs)

            return result

        return wrapper
    return decorator
