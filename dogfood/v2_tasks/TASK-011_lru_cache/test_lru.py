"""Test cases for LRU cache to verify correct behavior."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-011_lru_cache')

from lru_cache import LRUCache


def test_basic_get():
    """Test basic get operation."""
    cache = LRUCache(2)
    cache.put("x", 10)
    assert cache.get("x") == 10, "get() should return stored value"
    print("test_basic_get: PASS")


def test_miss():
    """Test cache miss."""
    cache = LRUCache(2)
    assert cache.get("nonexistent") is None, "get() should return None for missing key"
    print("test_miss: PASS")


def test_eviction_order():
    """
    Test that eviction happens for least recently used item.
    
    Scenario: capacity=3
    1. Put a, b, c (order: a, b, c)
    2. Get a (order should update: b, c, a - a is now most recent)
    3. Put d (should evict b, which is LRU)
    4. Cache should contain: c, a, d
    """
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    
    # Access 'a' to make it most recently used
    cache.get("a")
    
    # Add new item - should evict 'b' (the LRU item)
    cache.put("d", 4)
    
    # Verify cache contents
    assert cache.size() == 3, f"Cache should have 3 items, has {cache.size()}"
    
    # 'b' should be evicted
    assert cache.get("b") is None, "'b' should have been evicted"
    
    # 'a', 'c', 'd' should remain
    assert cache.get("a") == 1, "'a' should still be present"
    assert cache.get("c") == 3, "'c' should still be present"
    assert cache.get("d") == 4, "'d' should be present"
    
    # Verify order is c, a, d (most recent at end)
    keys = list(cache.cache.keys())
    assert keys == ['c', 'a', 'd'], f"Expected ['c', 'a', 'd'], got {keys}"
    
    print("test_eviction_order: PASS")


def test_update_existing():
    """Test updating an existing key doesn't cause spurious eviction."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    
    # Update 'a' - should not cause eviction
    cache.put("a", 100)
    
    assert cache.size() == 2, "Cache should still have 2 items"
    assert cache.get("a") == 100, "'a' should have updated value"
    assert cache.get("b") == 2, "'b' should still be present"
    
    print("test_update_existing: PASS")


def test_full_capacity_then_access():
    """
    Test LRU behavior when accessing items before adding new ones.
    
    After get() is called, the accessed item should become the MOST
    recently used, not the least.
    """
    cache = LRUCache(3)
    cache.put("x", 1)
    cache.put("y", 2)
    cache.put("z", 3)
    
    # Access 'x' - it becomes most recent (LRU is now 'y')
    cache.get("x")
    
    # 'y' should be evicted when we add new item
    cache.put("w", 4)
    
    assert cache.get("y") is None, "'y' should have been evicted"
    assert cache.get("x") == 1, "'x' should still be present"
    assert cache.get("z") == 3, "'z' should still be present"
    assert cache.get("w") == 4, "'w' should be present"
    
    print("test_full_capacity_then_access: PASS")


if __name__ == "__main__":
    test_basic_get()
    test_miss()
    test_eviction_order()
    test_update_existing()
    test_full_capacity_then_access()
    print("\nAll tests passed!")
