"""Rate limiting middleware that enforces request limits.

BUG: This middleware raises an exception instead of returning an error response.
This causes the logging middleware's after-hook to be bypassed.
"""

from typing import Callable
from src.middleware import Request, Response


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


class RateLimitMiddleware:
    """Middleware that enforces rate limits per client.
    
    BUG: When rate limit is exceeded, this raises RateLimitExceeded
    instead of returning an error Response. This bypasses the
    logging middleware's after-hook.
    """
    
    def __init__(self, limits: dict = None):
        # limits: dict mapping client_id -> (count, window_seconds)
        # (count, window_seconds) tuple where count is the limit
        self.limits = limits or {}
        self.requests: dict = {}
    
    def process(self, request: Request, next_handler: Callable) -> Response:
        """Check rate limit, then proceed if under limit."""
        client_id = request.headers.get("X-Client-ID", "default")
        
        # Get or initialize request count - use provided limit from self.limits or default
        if client_id not in self.requests:
            # Use provided limit or default to 5
            limit_tuple = self.limits.get(client_id, (5, 60))
            self.requests[client_id] = {"count": 0, "limit": limit_tuple[0], "window": limit_tuple[1]}
        
        req_info = self.requests[client_id]
        limit = self.requests[client_id].get("limit") or self.limits.get(client_id, (5, 60))[0]
        count = req_info["count"]
        
        # Check if rate limit exceeded
        if count >= limit:
            # BUG: Should return Response(status_code=429, body="Rate Limit Exceeded")
            # Instead raises an exception which bypasses logging_after
            raise RateLimitExceeded(f"Rate limit exceeded for client {client_id}")
        
        # Increment count and proceed
        req_info["count"] += 1
        return next_handler()
    
    def reset(self, client_id: str = None) -> None:
        """Reset request count for a client."""
        if client_id:
            if client_id in self.requests:
                self.requests[client_id]["count"] = 0
        else:
            self.requests.clear()
