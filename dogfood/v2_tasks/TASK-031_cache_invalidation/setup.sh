#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/cache.py << 'PYEOF'
import time

class TTLCache:
    """Cache with time-to-live expiration."""
    
    def __init__(self, default_ttl=60):
        self.default_ttl = default_ttl
        self._store = {}  # key -> (value, expire_time)
    
    def set(self, key, value, ttl=None):
        """Set a value with optional custom TTL."""
        if ttl is None:
            ttl = self.default_ttl
        expire = time.time() + ttl
        self._store[key] = (value, expire)
    
    def get(self, key, now=None):
        """Get a value. Returns None if expired or missing."""
        if key not in self._store:
            return None
        
        value, expire = self._store[key]
        if now is None:
            now = time.time()
        
        if now >= expire:
            # BUG: doesn't delete expired entry
            return None
        
        return value
    
    def delete(self, key):
        """Delete a key."""
        if key in self._store:
            del self._store[key]
    
    def cleanup(self, now=None):
        """Remove all expired entries."""
        if now is None:
            now = time.time()
        # BUG: modifying dict during iteration
        for key in self._store:
            value, expire = self._store[key]
            if now >= expire:
                del self._store[key]
    
    def size(self):
        """Return number of entries (including expired ones — bug)."""
        return len(self._store)
PYEOF

cat > repo/test_cache.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from cache import TTLCache

def test_expired_removed():
    """Getting an expired key should remove it from storage."""
    c = TTLCache(default_ttl=10)
    c.set("k1", "v1")
    
    # Access after expiry
    result = c.get("k1", now=time.time() + 20)
    assert result is None, "Should return None for expired"
    assert c.size() == 0, f"Expired entry should be removed, size={c.size()}"

def test_cleanup_safe():
    """Cleanup should not crash when removing entries."""
    c = TTLCache(default_ttl=10)
    now = 1000.0
    c._store = {
        "k1": ("v1", now + 5),   # Not expired
        "k2": ("v2", now - 1),   # Expired
        "k3": ("v3", now - 2),   # Expired
        "k4": ("v4", now + 10),  # Not expired
    }
    
    c.cleanup(now=now)
    assert c.size() == 2, f"Expected 2 remaining, got {c.size()}"
    assert c.get("k1", now=now) == "v1"
    assert c.get("k4", now=now) == "v4"

def test_size_excludes_expired():
    """size() should not count expired entries."""
    c = TTLCache(default_ttl=10)
    now = 1000.0
    c.set("k1", "v1")
    c.set("k2", "v2")
    
    # After both expire, size should reflect cleanup
    c.get("k1", now=now + 20)  # Trigger cleanup of k1
    c.get("k2", now=now + 20)  # Trigger cleanup of k2
    assert c.size() == 0, f"Expected 0, got {c.size()}"

import time

if __name__ == "__main__":
    tests = [test_expired_removed, test_cleanup_safe, test_size_excludes_expired]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
