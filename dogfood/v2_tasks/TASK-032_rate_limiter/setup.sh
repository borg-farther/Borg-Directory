#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/limiter.py << 'PYEOF'
import time

class RateLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []  # list of timestamps
    
    def allow(self, now=None):
        """Check if request is allowed. Returns True if within rate limit."""
        if now is None:
            now = time.time()
        
        # Clean old requests outside window
        # BUG: cleans requests BEFORE checking, but uses >= instead of >
        # This means requests exactly at the window boundary are kept
        # AND the cleanup condition is wrong: keeps too many old requests
        cutoff = now - self.window_seconds
        self.requests = [t for t in self.requests if t >= cutoff]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False
    
    def remaining(self, now=None):
        """How many requests remain in current window."""
        if now is None:
            now = time.time()
        cutoff = now - self.window_seconds
        # BUG: doesn't clean before counting
        current = len([t for t in self.requests if t >= cutoff])
        return max(0, self.max_requests - current)
    
    def reset_time(self, now=None):
        """Seconds until the oldest request in window expires."""
        if now is None:
            now = time.time()
        cutoff = now - self.window_seconds
        active = [t for t in self.requests if t >= cutoff]
        if not active:
            return 0
        # BUG: returns time until newest expires, not oldest
        oldest = min(active)
        return max(0, (oldest + self.window_seconds) - now)
PYEOF

cat > repo/test_limiter.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from limiter import RateLimiter

def test_basic_limiting():
    """Should allow max_requests then deny."""
    limiter = RateLimiter(max_requests=3, window_seconds=10)
    
    assert limiter.allow(now=100) == True
    assert limiter.allow(now=101) == True
    assert limiter.allow(now=102) == True
    assert limiter.allow(now=103) == False  # 4th request denied

def test_window_slides():
    """After window passes, should allow again."""
    limiter = RateLimiter(max_requests=2, window_seconds=10)
    
    assert limiter.allow(now=100) == True
    assert limiter.allow(now=101) == True
    assert limiter.allow(now=105) == False  # Still in window
    
    # Window should have slid: request at 100 expires at 110
    assert limiter.allow(now=111) == True  # First request expired

def test_remaining():
    limiter = RateLimiter(max_requests=3, window_seconds=10)
    assert limiter.remaining(now=100) == 3
    limiter.allow(now=100)
    assert limiter.remaining(now=101) == 2
    limiter.allow(now=101)
    limiter.allow(now=102)
    assert limiter.remaining(now=103) == 0

def test_reset_time():
    """reset_time should return when the oldest request expires."""
    limiter = RateLimiter(max_requests=2, window_seconds=10)
    limiter.allow(now=100)
    limiter.allow(now=105)
    
    # Oldest is at 100, expires at 110
    # At time 107, reset_time should be 3 seconds
    rt = limiter.reset_time(now=107)
    assert rt == 3, f"Expected 3, got {rt}"

def test_boundary_exact():
    """Request exactly at window boundary should be expired."""
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    limiter.allow(now=100)
    # At time 110, the request at 100 is exactly 10 seconds old — should be expired
    assert limiter.allow(now=110) == True, "Request at exact boundary should be expired"

if __name__ == "__main__":
    tests = [test_basic_limiting, test_window_slides, test_remaining, test_reset_time, test_boundary_exact]
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
