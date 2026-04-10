import time

class RetryHandler:
    """Retry with exponential backoff."""
    
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self._delays = []  # Track delays for testing
    
    def execute(self, func, *args, **kwargs):
        """Execute func with retry logic."""
        self.attempt = 0
        self._delays = []
        last_error = None
        
        while self.attempt <= self.max_retries:
            try:
                result = func(*args, **kwargs)
                # BUG: resets attempt counter on partial success
                # This means if we get a partial result then fail,
                # backoff restarts from base_delay instead of continuing
                self.attempt = 0
                return result
            except PartialSuccess as e:
                # Partial success — should continue with CURRENT backoff, not reset
                self.attempt = 0  # BUG: should not reset
                last_error = e
            except Exception as e:
                last_error = e
            
            self.attempt += 1
            if self.attempt > self.max_retries:
                break
            
            delay = min(self.base_delay * (2 ** (self.attempt - 1)), self.max_delay)
            self._delays.append(delay)
            # In real code: time.sleep(delay)
        
        raise last_error


class PartialSuccess(Exception):
    """Raised when operation partially succeeds but needs retry."""
    pass
