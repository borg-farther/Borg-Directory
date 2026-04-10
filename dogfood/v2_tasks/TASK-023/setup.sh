#!/bin/bash
# TASK-023: Broken middleware chain - error handler skips remaining middleware
mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-023

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-023/middleware.py << 'EOF'
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
                # BUG: When an error occurs, we should handle it and potentially
                # continue to remaining middleware, but instead we just re-raise
                # after logging, preventing remaining middleware from running.
                # This is incorrect - error handlers should be able to decide
                # whether to continue or propagate.
                print(f"Error in middleware {middleware_index}: {e}")
                raise  # BUG: Should not re-raise, should continue to error handlers
        
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
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-023/test_middleware.py << 'EOF'
"""Tests for middleware chain."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-023')

from middleware import MiddlewareChain, logging_middleware, validation_middleware, transform_middleware, error_handler_middleware, error_handler


def test_normal_flow():
    """Test that middleware chain executes in order without errors."""
    chain = MiddlewareChain()
    chain.use(logging_middleware)
    chain.use(transform_middleware)
    
    request = {"id": "test1", "data": "hello"}
    response = chain.execute(request)
    
    assert response["transformed"] == True
    assert response["id"] == "test1"
    print("test_normal_flow PASSED")


def test_error_in_middleware():
    """Test that error handler runs when middleware throws."""
    chain = MiddlewareChain()
    chain.use(logging_middleware)
    chain.use(validation_middleware)  # This will raise
    chain.use(transform_middleware)  # Should still run after error handling
    
    @error_handler
    def handle_error(err, ctx):
        print(f"Caught error: {err}")
        ctx["error_caught"] = True
        # Error is handled, should continue
    
    chain.use(handle_error)
    
    request = {"id": "test2"}  # Missing required_field
    response = chain.execute(request)
    
    # The error handler should have caught the error
    # And the chain should continue to remaining middleware
    assert response is None or response.get("error_caught") == True
    print("test_error_in_middleware PASSED")


def test_validation_error_blocks_chain():
    """Test that validation errors are properly caught."""
    chain = MiddlewareChain()
    
    call_order = []
    
    def mw1(req, next_fn):
        call_order.append("mw1_start")
        result = next_fn()
        call_order.append("mw1_end")
        return result
    
    def mw2(req, next_fn):
        call_order.append("mw2_start")
        raise ValueError("Test error")
    
    def mw3(req, next_fn):
        call_order.append("mw3_start")
        return {"done": True}
    
    @error_handler
    def error_handler_mw(err, ctx):
        call_order.append("error_handler")
        ctx["error"] = err
    
    chain.use(mw1)
    chain.use(mw2)
    chain.use(mw3)
    chain.use(error_handler_mw)
    
    request = {"id": "test3"}
    chain.execute(request)
    
    # After error, mw3 should NOT run, but error handler should
    # The chain should stop at the error
    assert "mw3_start" not in call_order, f"mw3 should not have run but call_order was {call_order}"
    assert "error_handler" in call_order, f"error_handler should have run but call_order was {call_order}"
    print("test_validation_error_blocks_chain PASSED")


def test_error_recovery():
    """Test that middleware chain can recover from errors."""
    chain = MiddlewareChain()
    
    call_order = []
    
    def problematic(req, next_fn):
        call_order.append("problematic")
        raise RuntimeError("Problematic middleware")
    
    def recovery(req, next_fn):
        call_order.append("recovery")
        return {"recovered": True}
    
    @error_handler
    def handler(err, ctx):
        call_order.append("handler")
        # Mark as handled so chain can continue
        ctx["error"] = None
    
    chain.use(problematic)
    chain.use(recovery)
    chain.use(handler)
    
    request = {"id": "test4"}
    result = chain.execute(request)
    
    # Both should have been called since error handler continues
    assert "problematic" in call_order
    assert "recovery" in call_order
    print("test_error_recovery PASSED")


if __name__ == "__main__":
    test_normal_flow()
    test_error_in_middleware()
    test_validation_error_blocks_chain()
    test_error_recovery()
    print("\nAll tests passed!")
EOF