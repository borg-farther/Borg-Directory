"""LRU Cache implementation with a subtle eviction bug."""

from collections import OrderedDict


class LRUCache:
    """
    A simple LRU (Least Recently Used) cache with a fixed capacity.
    
    The cache stores key-value pairs and evicts the least recently used
    item when capacity is exceeded.
    """
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key):
        """
        Retrieve a value from the cache.
        Returns None if key is not found.
        """
        if key not in self.cache:
            return None
        
        # Move to end to mark as recently used
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key, value):
        """
        Insert or update a key-value pair in the cache.
        Evicts least recently used item if capacity would be exceeded.
        """
        if key in self.cache:
            # Update existing key and move to end
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Check capacity BEFORE adding new item
            if len(self.cache) >= self.capacity:
                # Evict LRU item (first item in OrderedDict)
                evicted_key = next(iter(self.cache))
                del self.cache[evicted_key]
            
            self.cache[key] = value
    
    def size(self):
        return len(self.cache)


def main():
    """Demonstrate the LRU cache behavior."""
    cache = LRUCache(3)
    
    # Fill cache to capacity
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    
    print(f"Initial cache size: {cache.size()}")
    print(f"Cache contents: {list(cache.cache.keys())}")
    
    # Access "a" to make it recently used
    print(f"get('a') = {cache.get('a')}")
    print(f"After access, order: {list(cache.cache.keys())}")
    
    # Add new item - should evict "b" (least recently used)
    cache.put("d", 4)
    print(f"After adding 'd', cache size: {cache.size()}")
    print(f"Cache contents: {list(cache.cache.keys())}")
    
    # Expected: a, c, d (b was evicted)
    # But with the bug, 'a' stays at beginning and gets evicted instead of 'b'!
    
    print(f"\nExpected: ['c', 'a', 'd']")
    print(f"Actual:   {list(cache.cache.keys())}")
    
    if list(cache.cache.keys()) == ['c', 'a', 'd']:
        print("PASS: Cache correctly evicted LRU item")
    else:
        print("FAIL: Cache did not evict correctly")


if __name__ == "__main__":
    main()
