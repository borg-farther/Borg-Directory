"""Unbounded cache with memory leak bug."""
from datetime import datetime, timedelta


class Cache:
    """A simple in-memory cache that grows unbounded."""

    def __init__(self):
        self._store = {}

    def set(self, key, value):
        """Store a value with no eviction."""
        self._store[key] = value

    def get(self, key, default=None):
        """Retrieve a value from cache."""
        return self._store.get(key, default)

    def size(self):
        """Return number of items in cache."""
        return len(self._store)

    def clear(self):
        """Clear all items from cache."""
        self._store.clear()


# Example usage showing the memory leak
def process_requests():
    """Process requests and cache results - memory grows forever."""
    cache = Cache()
    results = []

    for i in range(10000):
        # Each request adds to cache without eviction
        cache.set(f"request_{i}", {"id": i, "data": "x" * 100})

    return cache.size()
