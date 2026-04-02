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
