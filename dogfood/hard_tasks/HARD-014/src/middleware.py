"""Middleware chain processor for request handling."""

from typing import List, Callable, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Request:
    """Simple request object passed through middleware chain."""
    path: str
    method: str
    headers: Dict[str, str] = None
    body: Any = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class Response:
    """Simple response object returned from middleware."""
    status_code: int
    body: Any = None
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class MiddlewareChain:
    """Processes a chain of middleware in order.
    
    Each middleware can either:
    - Call next(request) to pass to the next middleware
    - Return a response early (short-circuit)
    - Raise an exception (which may bypass after-hooks)
    """
    
    def __init__(self):
        self.middlewares: List[Dict[str, Any]] = []
        self.log: List[str] = []
    
    def use(self, middleware: Callable) -> None:
        """Register a middleware."""
        self.middlewares.append({
            "handler": middleware,
            "name": middleware.__name__
        })
    
    def execute(self, request: Request) -> Response:
        """Execute the middleware chain on a request."""
        self.log = []
        return self._process(0, request)
    
    def _process(self, index: int, request: Request) -> Response:
        """Recursively process middleware at given index."""
        if index >= len(self.middlewares):
            return Response(status_code=404, body="Not Found")
        
        middleware = self.middlewares[index]
        mw_handler = middleware["handler"]
        mw_name = middleware["name"]
        
        # Execute before hook
        self.log.append(f"{mw_name}_before")
        
        # Create the next handler
        def next_handler():
            return self._process(index + 1, request)
        
        try:
            result = mw_handler(request, next_handler)
            
            # Execute after hook (only if no exception)
            self.log.append(f"{mw_name}_after")
            
            return result
        except Exception as e:
            # Log exception but don't execute after hook
            self.log.append(f"{mw_name}_exception:{type(e).__name__}")
            raise
    
    def get_log(self) -> List[str]:
        """Return the execution log."""
        return self.log


def default_handler(request: Request, next_handler: Callable) -> Response:
    """Default handler when no middleware short-circuits."""
    return Response(status_code=200, body="OK")
