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
