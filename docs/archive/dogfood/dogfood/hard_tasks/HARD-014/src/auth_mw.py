"""Authentication middleware that validates credentials."""

from typing import Callable
from src.middleware import Request, Response


class AuthMiddleware:
    """Middleware that authenticates requests.
    
    Returns error response for unauthenticated requests.
    """
    
    def __init__(self, valid_tokens: dict = None):
        self.valid_tokens = valid_tokens or {}
    
    def process(self, request: Request, next_handler: Callable) -> Response:
        """Authenticate request, then proceed if valid."""
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if token and token in self.valid_tokens:
            # Authenticated - proceed to next handler
            return next_handler()
        elif not token:
            # No token - return error response (not exception)
            return Response(status_code=401, body="Unauthorized: No token")
        else:
            # Invalid token - return error response (not exception)
            return Response(status_code=401, body="Unauthorized: Invalid token")
