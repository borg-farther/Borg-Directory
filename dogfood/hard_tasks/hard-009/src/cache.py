"""LRU Cache with TTL support."""

import time
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """
    LRU Cache with TTL support.
    
    The cache itself is working correctly - the bug is in how
    store.py uses it (bypasses invalidation on updates).
    """

    def __init__(self, max_size: int = 100, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check TTL
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        return value

    def put(self, key: str, value: Any) -> None:
        """Put value into cache."""
        # Remove if exists to update position
        if key in self._cache:
            del self._cache[key]
        
        # Add to end
        self._cache[key] = (value, time.time())
        
        # Evict oldest if over max size
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)
