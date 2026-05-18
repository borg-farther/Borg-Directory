"""Middleware chain implementation with error handling."""
from typing import Callable, Any, List, Optional
import traceback


class MiddlewareChain:
    """A chain of middleware functions that process requests/responses."""
    
    def __init__(self):
        self.middlewares: List[Callable] = []
    
    def use(self, middleware: Callable) -> None:
        """Add a middleware to the chain."""
        self.middlewares.append(middleware)
    
    def execute(self, request: dict) -> dict:
        """Execute the middleware chain with a request."""
        context = {"request": request, "response": None, "error": None}
        
        def next_handler(middleware_index: int = 0):
            """Recursively execute middleware starting at given index."""
            if middleware_index >= len(self.middlewares):
                return
            
            middleware = self.middlewares[middleware_index]
            
            try:
                # Call middleware with request and next
                def next():
                    next_handler(middleware_index + 1)
                
                result = middleware(context["request"], next)
                context["response"] = result
            except Exception as e:
                context["error"] = e
                # When an error occurs, we log it and store it in context
                # Error handlers will be called after all middleware completes
                # Error handlers can decide whether to propagate the error or continue
                print(f"Error in middleware {middleware_index}: {e}")
        
        next_handler(0)
        
        if context["error"]:
            # Try error handlers (if any were registered)
            for middleware in self.middlewares:
                try:
                    if hasattr(middleware, '_is_error_handler') and middleware._is_error_handler:
                        middleware(context["error"], context)
                except Exception:
                    pass  # Ignore errors in error handlers
        
        return context["response"]


def logging_middleware(req: dict, next_fn: Callable) -> dict:
    """Middleware that logs requests."""
    print(f"LOG: Processing request {req.get('id', 'unknown')}")
    result = next_fn()
    print(f"LOG: Finished request {req.get('id', 'unknown')}")
    return result


def validation_middleware(req: dict, next_fn: Callable) -> dict:
    """Middleware that validates requests."""
    if req.get("required_field") is None:
        raise ValueError("required_field is missing")
    return next_fn()


def transform_middleware(req: dict, next_fn: Callable) -> dict:
    """Middleware that transforms requests."""
    req["transformed"] = True
    return next_fn()


def error_handler_middleware(error: Exception, context: dict) -> None:
    """Error handler middleware - marks error as handled."""
    print(f"ERROR_HANDLER: Handling error: {error}")
    error._handled = True


# Decorator to mark error handlers
def error_handler(fn):
    fn._is_error_handler = True
    return fn
