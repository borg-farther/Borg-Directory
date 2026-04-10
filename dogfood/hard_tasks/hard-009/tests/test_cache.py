"""Tests for cache invalidation bug."""

import pytest
from src.cache import LRUCache
from src.store import DataStore
from src.service import UserService


def test_cache_basic_operations():
    """Test that cache itself works correctly."""
    cache = LRUCache(max_size=10, ttl=60)
    
    cache.put("key1", "value1")
    assert cache.get("key1") == "value1"
    
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_write_and_read():
    """Test write populates cache correctly."""
    cache = LRUCache()
    store = DataStore(cache)
    
    store.write("user1", {"name": "Alice", "age": 30})
    
    # Should be in cache and store
    assert store.read("user1") == {"name": "Alice", "age": 30}
    assert cache.get("user1") == {"name": "Alice", "age": 30}


def test_update_should_refresh_cache():
    """
    Test that demonstrates the cache invalidation bug.
    
    After update(), the cache should be invalidated and the new
    value should be returned. But due to the bug, stale data is returned.
    """
    cache = LRUCache()
    store = DataStore(cache)
    
    # Create user
    store.write("user1", {"name": "Alice", "age": 30})
    
    # Read to populate cache
    assert store.read("user1") == {"name": "Alice", "age": 30}
    assert cache.get("user1") == {"name": "Alice", "age": 30}
    
    # Update user - BUG: this bypasses cache invalidation
    store.update("user1", {"name": "Alice", "age": 31})
    
    # Store has new value
    assert store._data["user1"] == {"name": "Alice", "age": 31}
    
    # But cache still has old value! BUG!
    cached_value = cache.get("user1")
    assert cached_value == {"name": "Alice", "age": 30}, f"Expected age 30 from cache but got {cached_value}"
    
    # Read returns stale data from cache
    result = store.read("user1")
    assert result == {"name": "Alice", "age": 30}, f"Expected age 30 but got {result}"


def test_service_update_returns_stale_data():
    """
    Test the full bug scenario through the service layer.
    """
    cache = LRUCache()
    store = DataStore(cache)
    service = UserService(cache, store)
    
    # Create and read user
    service.create_user("user1", {"name": "Bob", "score": 100})
    assert service.get_user("user1") == {"name": "Bob", "score": 100}
    
    # Update via service - should invalidate cache
    service.update_user("user1", {"name": "Bob", "score": 150})
    
    # BUG: Service read returns stale cache data
    user = service.get_user("user1")
    assert user["score"] == 150, f"Expected score 150 but got {user['score']}"


def test_batch_update_leaves_stale_cache():
    """
    Test that batch updates leave stale data in cache.
    """
    cache = LRUCache()
    store = DataStore(cache)
    
    # Create users
    store.write("user1", {"name": "User1", "value": 10})
    store.write("user2", {"name": "User2", "value": 20})
    
    # Populate cache
    store.read("user1")
    store.read("user2")
    
    # Batch update - BUG: doesn't invalidate cache
    store.update_batch({
        "user1": {"name": "User1", "value": 100},
        "user2": {"name": "User2", "value": 200}
    })
    
    # Store has new values
    assert store._data["user1"]["value"] == 100
    assert store._data["user2"]["value"] == 200
    
    # But cache has stale values
    assert cache.get("user1")["value"] == 10
    assert cache.get("user2")["value"] == 20
