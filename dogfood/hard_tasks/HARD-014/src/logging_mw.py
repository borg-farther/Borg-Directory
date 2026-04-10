"""Logging middleware that records request/response lifecycle."""

from typing import Callable
from src.middleware import Request, Response, MiddlewareChain


class LoggingMiddleware:
    """Middleware that logs before and after hook execution.
    
    The bug is that when another middleware raises an exception,
    this middleware's after-hook is never called, resulting in
    incomplete logs.
    """
    
    def __init__(self, chain: MiddlewareChain):
        self.chain = chain
    
    def process(self, request: Request, next_handler: Callable) -> Response:
        """Log before processing, call next, then log after."""
        self.chain.log.append(f"logging_before:{request.path}")
        
        try:
            response = next_handler()
            self.chain.log.append(f"logging_after:{request.path}")
            return response
        except Exception as e:
            # The after-hook is NOT logged when exception is raised
            # This is the symptom of the bug in rate_limit_mw
            self.chain.log.append(f"logging_error:{type(e).__name__}")
            raise
