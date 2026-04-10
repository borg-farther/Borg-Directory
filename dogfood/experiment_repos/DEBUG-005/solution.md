# Solution for DEBUG-005

## Bug Description
The `Cache` class is unbounded - it grows forever as items are added with no eviction policy. This is a memory leak.

## Fix

Replace the simple dict-based cache with an LRU cache using `collections.OrderedDict` or `functools.lru_cache`:

```python
from collections import OrderedDict


class Cache:
    """A cache with LRU eviction policy."""

    def __init__(self, max_size=100):
        self._store = OrderedDict()
        self._max_size = max_size

    def set(self, key, value):
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self._max_size:
            self._store.popitem(last=False)  # Remove oldest (first) item
        self._store[key] = value

    def get(self, key, default=None):
        if key in self._store:
            # Move to end (most recently used)
            self._store.move_to_end(key)
            return self._store[key]
        return default

    def size(self):
        return len(self._store)

    def clear(self):
        self._store.clear()
```

Or use Python's built-in `functools.lru_cache` decorator which provides thread-safe LRU caching.
