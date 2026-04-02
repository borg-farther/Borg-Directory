"""Combines auth and permissions in request pipeline."""
from typing import Dict, Optional, Any
from auth import Authenticator, get_authenticator
from permissions import PermissionCache, get_permissions


class Middleware:
    """Middleware that combines authentication and authorization."""

    def __init__(self, auth: Authenticator = None, permissions: PermissionCache = None):
        self.auth = auth or get_authenticator()
        self.permissions = permissions or get_permissions()

    def process_request(self, request: Dict[str, Any]) -> Dict:
        """Process a request through auth and permissions.

        Returns a response dict. If there's an error, returns {"error": ...}
        If successful, returns {"user": user_data, "data": ...}
        """
        user_id = request.get("user_id")
        username = request.get("username")
        password = request.get("password")
        action = request.get("action", "read")

        # BUG: We check permissions BEFORE authenticating!
        # This is wrong because we don't even know who the user is yet
        if user_id:
            # Even without authentication, we check permissions
            # This is wrong - we should authenticate first
            if not self.permissions.check_permission(user_id, action):
                return {"error": "Permission denied"}

        # Only then do we authenticate
        if username and password:
            user = self.auth.authenticate(username, password)
            if user is None:
                return {"error": "Authentication failed"}

            # Use authenticated user's ID
            user_id = user["id"]

            # Check permissions again for authenticated user
            if not self.permissions.check_permission(user_id, action):
                return {"error": "Permission denied"}

            return {"user": user, "data": {"message": "Success"}}

        # If no credentials provided
        return {"error": "Authentication required"}

    def require_auth(self, request: Dict[str, Any], required_permission: str) -> Optional[Dict]:
        """Check if a request has the required permission.

        Returns error dict if check fails, None if successful.
        """
        user_id = request.get("user_id")
        username = request.get("username")
        password = request.get("password")

        # BUG: Same issue - checking permissions before auth
        if user_id:
            if not self.permissions.check_permission(user_id, required_permission):
                return {"error": "Permission denied"}

        if username and password:
            user = self.auth.authenticate(username, password)
            if user is None:
                return {"error": "Authentication failed"}

            # Check permission after authentication
            if not self.permissions.check_permission(user["id"], required_permission):
                return {"error": "Permission denied"}

        return None  # All checks passed


class Request:
    """Simple request object."""

    def __init__(self, data: Dict[str, Any] = None):
        self.data = data or {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


def create_middleware(auth: Authenticator = None, permissions: PermissionCache = None) -> Middleware:
    """Create a new middleware instance."""
    return Middleware(auth, permissions)
