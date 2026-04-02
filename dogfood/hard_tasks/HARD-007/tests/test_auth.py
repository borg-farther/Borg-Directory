"""Tests for the auth system."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from auth import Authenticator, get_authenticator
from permissions import PermissionCache, get_permissions
from middleware import Middleware, create_middleware


class TestAuthenticator:
    """Test the authenticator."""

    def setup_method(self):
        """Reset authenticator before each test."""
        self.auth = Authenticator()

    def test_register_and_authenticate(self):
        """Test registering a user and authenticating."""
        self.auth.register_user("user1", "alice", "password123", age=30)

        user = self.auth.authenticate("alice", "password123")
        assert user is not None
        assert user["username"] == "alice"
        assert user["id"] == "user1"

    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        self.auth.register_user("user1", "alice", "password123")

        user = self.auth.authenticate("alice", "wrongpassword")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        """Test authentication with nonexistent user."""
        user = self.auth.authenticate("nonexistent", "password")
        assert user is None


class TestPermissionCache:
    """Test the permission cache."""

    def setup_method(self):
        """Reset permissions before each test."""
        self.perms = PermissionCache()

    def test_set_user_role(self):
        """Test setting a user role."""
        self.perms.set_user_role("user1", "admin")
        assert self.perms.get_user_role("user1") == "admin"

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        self.perms.set_user_role("admin1", "admin")

        assert self.perms.check_permission("admin1", "read") is True
        assert self.perms.check_permission("admin1", "write") is True
        assert self.perms.check_permission("admin1", "delete") is True
        assert self.perms.check_permission("admin1", "admin") is True

    def test_user_has_limited_permissions(self):
        """Test that user role has limited permissions."""
        self.perms.set_user_role("user1", "user")

        assert self.perms.check_permission("user1", "read") is True
        assert self.perms.check_permission("user1", "write") is True
        assert self.perms.check_permission("user1", "delete") is False

    def test_guest_has_minimal_permissions(self):
        """Test that guest role has minimal permissions."""
        self.perms.set_user_role("guest1", "guest")

        assert self.perms.check_permission("guest1", "read") is True
        assert self.perms.check_permission("guest1", "write") is False

    def test_unknown_user_denied(self):
        """Test that users without roles are denied."""
        assert self.perms.check_permission("unknown_user", "read") is False


class TestPermissionCacheUpdate:
    """Test permission cache updates when roles change."""

    def setup_method(self):
        """Reset permissions before each test."""
        self.perms = PermissionCache()

    def test_role_update_invalidates_cache(self):
        """Test that updating a user's role invalidates the cache.

        This is the key test for the stale cache bug.
        """
        # User starts as guest with only read permission
        self.perms.set_user_role("user1", "guest")
        assert self.perms.check_permission("user1", "read") is True
        assert self.perms.check_permission("user1", "write") is False

        # Check read to cache it
        result = self.perms.check_permission("user1", "read")
        assert result is True

        # Now upgrade user to admin
        self.perms.update_user_role("user1", "admin")

        # BUG: Without cache invalidation, this still returns cached False!
        # After fix, should return True because user is now admin
        assert self.perms.check_permission("user1", "write") is True, \
            "Permission check returned stale cached result after role update"

    def test_cache_invalidation_method(self):
        """Test that explicit cache invalidation works."""
        self.perms.set_user_role("user1", "guest")
        self.perms.check_permission("user1", "write")  # Caches False

        # Explicitly invalidate cache
        self.perms.invalidate_user_cache("user1")

        # Now update role
        self.perms.update_user_role("user1", "admin")

        # Should now return True
        assert self.perms.check_permission("user1", "write") is True


class TestMiddleware:
    """Test the middleware combining auth and permissions."""

    def setup_method(self):
        """Reset state before each test."""
        self.auth = Authenticator()
        self.perms = PermissionCache()
        self.middleware = Middleware(self.auth, self.perms)

        # Register and set up test users
        self.auth.register_user("alice", "alice", "password123", role="admin")
        self.auth.register_user("bob", "bob", "password123", role="user")
        self.auth.register_user("charlie", "charlie", "password123", role="guest")

        self.perms.set_user_role("alice", "admin")
        self.perms.set_user_role("bob", "user")
        self.perms.set_user_role("charlie", "guest")

    def test_successful_admin_auth(self):
        """Test successful authentication and authorization for admin."""
        request = {
            "username": "alice",
            "password": "password123",
            "action": "delete"
        }

        response = self.middleware.process_request(request)
        assert "error" not in response
        assert response["user"]["username"] == "alice"

    def test_successful_user_auth(self):
        """Test successful authentication for user with valid permission."""
        request = {
            "username": "bob",
            "password": "password123",
            "action": "read"
        }

        response = self.middleware.process_request(request)
        assert "error" not in response
        assert response["user"]["username"] == "bob"

    def test_user_denied_delete_permission(self):
        """Test that user is denied delete permission."""
        request = {
            "username": "bob",
            "password": "password123",
            "action": "delete"
        }

        response = self.middleware.process_request(request)
        assert "error" in response
        assert response["error"] == "Permission denied"

    def test_guest_denied_write_permission(self):
        """Test that guest is denied write permission."""
        request = {
            "username": "charlie",
            "password": "password123",
            "action": "write"
        }

        response = self.middleware.process_request(request)
        assert "error" in response
        assert response["error"] == "Permission denied"

    def test_wrong_password(self):
        """Test authentication with wrong password."""
        request = {
            "username": "alice",
            "password": "wrongpassword",
            "action": "read"
        }

        response = self.middleware.process_request(request)
        assert "error" in response
        assert response["error"] == "Authentication failed"

    def test_permission_check_order(self):
        """Test that authentication happens before permission check.

        This test exposes the bug where permissions are checked BEFORE auth.
        """
        # Make a request without credentials but with a user_id
        # BUG: The middleware checks permissions for user_id before checking credentials
        request = {
            "user_id": "alice",  # Has admin permissions
            "username": "bob",    # Different user
            "password": "wrongpassword",
            "action": "delete"    # Alice has this permission, Bob doesn't
        }

        response = self.middleware.process_request(request)

        # With the bug, permission is checked for bob (who doesn't have delete)
        # before alice's credentials are even verified
        # After fix: auth happens first, so bob's permissions are checked correctly
        assert "error" in response  # Should still fail because bob doesn't have delete

    def test_role_change_takes_effect(self):
        """Test that when a user's role changes, permissions update correctly."""
        # Charlie starts as guest with only read
        request = {
            "username": "charlie",
            "password": "password123",
            "action": "write"
        }

        response = self.middleware.process_request(request)
        assert response["error"] == "Permission denied"

        # Now upgrade charlie to admin
        self.perms.update_user_role("charlie", "admin")

        # Should now work
        request["action"] = "admin"  # Admin-only action
        response = self.middleware.process_request(request)
        # BUG: This might still fail due to stale cache
        assert "error" not in response, f"Expected success but got: {response}"
