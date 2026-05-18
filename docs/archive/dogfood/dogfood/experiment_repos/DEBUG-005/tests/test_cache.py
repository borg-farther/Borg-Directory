"""Tests for bounded cache."""
import pytest
from cache import Cache


def test_cache_basic_operations():
    """Cache should support basic get/set."""
    cache = Cache()
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.get("nonexistent") is None
    assert cache.get("nonexistent", "default") == "default"


def test_cache_respects_max_size():
    """Cache should not exceed max_size after many inserts."""
    cache = Cache(max_size=100)

    # Insert 1000 items
    for i in range(1000):
        cache.set(f"key_{i}", f"value_{i}")

    # Cache should not exceed max_size
    assert cache.size() <= 100, f"Cache size {cache.size()} exceeds max_size 100"


def test_cache_lru_eviction():
    """Least recently used items should be evicted."""
    cache = Cache(max_size=3)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # 'a' is LRU, should be evicted when we add 'd'
    cache.set("d", 4)

    # 'a' should be gone
    assert cache.get("a") is None
    # 'b', 'c', 'd' should still be there
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert cache.get("d") == 4


def test_cache_access_updates_lru():
    """Accessing an item should update its LRU status."""
    cache = Cache(max_size=3)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    # Access 'a', making it most recently used
    cache.get("a")

    # Add 'd', 'b' should be evicted (it was accessed after 'a' was set but...)
    # Actually 'a' was set first, then 'b', then 'c'. Accessing 'a' doesn't change
    # that 'b' was set after 'a'. So after accessing 'a', order is: b, c, a
    # Adding 'd' should evict 'b' (LRU)

    cache.set("d", 4)

    # 'b' should be evicted
    assert cache.get("b") is None
    # 'a', 'c', 'd' should still be there
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("d") == 4
