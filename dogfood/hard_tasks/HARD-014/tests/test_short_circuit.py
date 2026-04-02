"""Tests for HARD-014: Middleware Chain Short-Circuit Bug.

These tests verify that the logging middleware's after-hook is always called,
even when other middleware raises exceptions. They should FAIL due to the bug.
"""

import pytest
from src.middleware import Request, Response, MiddlewareChain
from src.logging_mw import LoggingMiddleware
from src.auth_mw import AuthMiddleware
from src.rate_limit_mw import RateLimitMiddleware, RateLimitExceeded


class TestMiddlewareChainShortCircuit:
    """Tests for middleware chain short-circuit behavior."""
    
    def test_logging_middleware_after_hook_called_on_success(self):
        """Test that logging after-hook is called on successful request."""
        chain = MiddlewareChain()
        logging_mw = LoggingMiddleware(chain)
        
        chain.use(logging_mw.process)
        chain.use(lambda req, next: Response(status_code=200))
        
        request = Request(path="/test", method="GET")
        response = chain.execute(request)
        
        log = chain.get_log()
        
        assert response.status_code == 200
        assert "logging_before:/test" in log
        assert "logging_after:/test" in log
    
    def test_logging_middleware_after_hook_called_on_auth_failure(self):
        """Test that logging after-hook is called when auth returns error response."""
        chain = MiddlewareChain()
        logging_mw = LoggingMiddleware(chain)
        auth_mw = AuthMiddleware({"valid_token": "user1"})
        
        chain.use(logging_mw.process)
        chain.use(auth_mw.process)
        
        request = Request(path="/test", method="GET", headers={})
        response = chain.execute(request)
        
        log = chain.get_log()
        
        assert response.status_code == 401
        # After hook should be called because auth returns Response, not exception
        assert "logging_after:/test" in log, "After hook should be called on auth failure"
    
    def test_logging_middleware_after_hook_bypassed_on_rate_limit(self):
        """Test that logging after-hook is bypassed when rate limit raises exception.
        
        This test should FAIL because rate_limit_mw raises an exception
        instead of returning an error response, which bypasses logging_after.
        """
        chain = MiddlewareChain()
        logging_mw = LoggingMiddleware(chain)
        rate_limit_mw = RateLimitMiddleware({"client1": (0, 60)})  # Limit of 0
        
        chain.use(logging_mw.process)
        chain.use(rate_limit_mw.process)
        chain.use(lambda req, next: Response(status_code=200))
        
        # First request should immediately trigger rate limit (limit is 0)
        request1 = Request(path="/test", method="GET", headers={"X-Client-ID": "client1"})
        
        # This will raise RateLimitExceeded, bypassing logging_after
        with pytest.raises(RateLimitExceeded):
            chain.execute(request1)
        
        log1 = chain.get_log()
        
        # BUG: logging_after is NOT in log1 because rate_limit_mw raises exception
        assert "logging_after:/test" in log1, "BUG: After hook should be called even on rate limit"
    

    
    def test_full_chain_logging_completeness(self):
        """Test that all middleware hooks are logged in correct order."""
        chain = MiddlewareChain()
        logging_mw = LoggingMiddleware(chain)
        auth_mw = AuthMiddleware({"valid_token": "user1"})
        rate_limit_mw = RateLimitMiddleware({"client1": (10, 60)})
        
        chain.use(logging_mw.process)
        chain.use(auth_mw.process)
        chain.use(rate_limit_mw.process)
        chain.use(lambda req, next: Response(status_code=200))
        
        request = Request(
            path="/api/test",
            method="GET",
            headers={"Authorization": "Bearer valid_token", "X-Client-ID": "client1"}
        )
        
        response = chain.execute(request)
        log = chain.get_log()
        
        assert response.status_code == 200
        
        # Check all hooks are logged
        expected = [
            "logging_before:/api/test",
            "logging_after:/api/test"
        ]
        
        for entry in expected:
            assert entry in log, f"Missing: {entry} in log: {log}"
