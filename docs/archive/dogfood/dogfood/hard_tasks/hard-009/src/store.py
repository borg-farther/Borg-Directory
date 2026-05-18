"""Data store that uses cache for reads."""

from typing import Any, Dict, Optional

from .cache import LRUCache


class DataStore:
    """
    Data store with cache-through reads.
    
    BUG: The update methods bypass cache invalidation!
    When data is updated directly via update/update_batch,
    the cache is not invalidated, so service.py reads stale data.
    """

    def __init__(self, cache: LRUCache):
        self._data: Dict[str, Any] = {}
        self._cache = cache

    def read(self, key: str) -> Optional[Any]:
        """
        Read from cache first, then store.
        Cache is checked and populated here - but updates bypass it.
        """
        # Try cache first
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        
        # Fallback to store
        if key in self._data:
            value = self._data[key]
            # Populate cache
            self._cache.put(key, value)
            return value
        
        return None

    def write(self, key: str, value: Any) -> None:
        """Write to store and update cache."""
        self._data[key] = value
        self._cache.put(key, value)

    def update(self, key: str, value: Any) -> None:
        """
        Update existing value.
        
        BUG: This updates the store but does NOT invalidate the cache!
        The cache still holds the old value.
        """
        if key in self._data:
            self._data[key] = value
            # BUG: Missing cache invalidation here!
            # Should call self._cache.invalidate(key) but doesn't

    def update_batch(self, updates: Dict[str, Any]) -> None:
        """
        Batch update.
        
        BUG: Same issue - updates store but not cache.
        """
        for key, value in updates.items():
            if key in self._data:
                self._data[key] = value
                # BUG: Missing cache invalidation!
