#!/bin/bash
# TASK-024: Incorrect hash table - resize doesn't rehash existing keys
mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-024

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-024/hash_table.py << 'EOF'
"""Hash table implementation with resize."""
from typing import Any, Optional, List, Tuple


class HashTable:
    """A hash table with chaining for collision resolution."""
    
    def __init__(self, initial_capacity: int = 4):
        self.capacity = initial_capacity
        self.size = 0
        self.buckets: List[List[Tuple[str, Any]]] = [[] for _ in range(self.capacity)]
    
    def _hash(self, key: str) -> int:
        """Hash function."""
        return hash(key) % self.capacity
    
    def _resize(self, new_capacity: int) -> None:
        """Resize the hash table to new_capacity."""
        old_buckets = self.buckets
        self.capacity = new_capacity
        # BUG: We create new buckets but we DON'T rehash the old entries!
        # The old entries are lost! This is a critical bug.
        self.buckets = [[] for _ in range(self.capacity)]
        # Missing: rehash all keys from old_buckets into self.buckets
    
    def put(self, key: str, value: Any) -> None:
        """Put a key-value pair in the hash table."""
        # Resize if load factor exceeds 0.75
        if self.size / self.capacity > 0.75:
            self._resize(self.capacity * 2)
        
        index = self._hash(key)
        bucket = self.buckets[index]
        
        # Check if key already exists
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        
        # Add new entry
        bucket.append((key, value))
        self.size += 1
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        index = self._hash(key)
        bucket = self.buckets[index]
        
        for k, v in bucket:
            if k == key:
                return v
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from the hash table."""
        index = self._hash(key)
        bucket = self.buckets[index]
        
        for i, (k, v) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self.size -= 1
                return True
        return False
    
    def contains(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None
    
    def get_size(self) -> int:
        """Get the number of entries."""
        return self.size
    
    def get_capacity(self) -> int:
        """Get the current capacity."""
        return self.capacity


def test_hashtable():
    """Test basic hash table operations."""
    ht = HashTable()
    
    ht.put("apple", 1)
    ht.put("banana", 2)
    ht.put("cherry", 3)
    
    assert ht.get("apple") == 1
    assert ht.get("banana") == 2
    assert ht.get("cherry") == 3
    assert ht.get_size() == 3
    
    print("test_hashtable PASSED")


def test_resize_rehash():
    """Test that resize properly rehashes existing keys."""
    ht = HashTable(initial_capacity=2)
    
    # Add entries that will cause resize
    # With capacity=2 and load factor 0.75, resize happens at size=2
    ht.put("a", 1)
    ht.put("b", 2)  # This should trigger resize to capacity 4
    
    # After resize, all keys should still be accessible
    assert ht.get("a") == 1, f"Expected 1 but got {ht.get('a')}"
    assert ht.get("b") == 2, f"Expected 2 but got {ht.get('b')}"
    
    print("test_resize_rehash PASSED")


def test_many_resizes():
    """Test that data survives multiple resizes."""
    ht = HashTable(initial_capacity=2)
    
    # Add many entries to trigger multiple resizes
    for i in range(20):
        ht.put(f"key{i}", i * 10)
    
    # All entries should be accessible
    for i in range(20):
        assert ht.get(f"key{i}") == i * 10, f"key{i} not found or wrong value"
    
    assert ht.get_size() == 20
    print("test_many_resizes PASSED")


def test_resize_with_collisions():
    """Test resizing when there are hash collisions."""
    ht = HashTable(initial_capacity=2)
    
    # These might collide depending on hash function
    # But our implementation handles this with chaining
    ht.put("aa", 1)
    ht.put("bb", 2)
    ht.put("cc", 3)
    
    assert ht.get("aa") == 1
    assert ht.get("bb") == 2
    assert ht.get("cc") == 3
    
    # Trigger resize
    ht.put("dd", 4)
    
    # All should still be accessible
    assert ht.get("aa") == 1
    assert ht.get("bb") == 2
    assert ht.get("cc") == 3
    assert ht.get("dd") == 4
    
    print("test_resize_with_collisions PASSED")


if __name__ == "__main__":
    test_hashtable()
    test_resize_rehash()
    test_many_resizes()
    test_resize_with_collisions()
    print("\nAll tests passed!")
EOF