"""Permission checking with caching."""
from typing import Dict, Set, Optional


class PermissionDeniedError(Exception):
    """Raised when a permission check fails."""
    pass


class PermissionCache:
    """Handles permission checking with caching for performance."""

    # Role-based permissions
    ROLE_PERMISSIONS = {
        "admin": {"read", "write", "delete", "admin"},
        "user": {"read", "write"},
        "guest": {"read"},
    }

    def __init__(self):
        self._user_roles: Dict[str, str] = {}  # user_id -> role
        self._cache: Dict[str, bool] = {}  # (user_id, permission) -> bool

    def set_user_role(self, user_id: str, role: str) -> None:
        """Set a user's role."""
        self._user_roles[user_id] = role

    def get_user_role(self, user_id: str) -> Optional[str]:
        """Get a user's current role."""
        return self._user_roles.get(user_id)

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission.

        Uses caching for performance - results are cached by user_id:permission
        """
        cache_key = f"{user_id}:{permission}"

        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get user's role
        role = self._user_roles.get(user_id)

        # If user has no role, deny by default
        if role is None:
            self._cache[cache_key] = False
            return False

        # Check if role has the permission
        role_permissions = self.ROLE_PERMISSIONS.get(role, set())
        has_permission = permission in role_permissions

        # Cache the result
        self._cache[cache_key] = has_permission
        return has_permission

    def update_user_role(self, user_id: str, new_role: str) -> None:
        """Update a user's role."""
        self._user_roles[user_id] = new_role
        # BUG: We update the role but don't invalidate the cache!
        # This means old cached permission results will still be used
        # even though the user's role has changed

    def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cached permissions for a user."""
        keys_to_delete = [k for k in self._cache if k.startswith(f"{user_id}:")]
        for key in keys_to_delete:
            del self._cache[key]

    def clear_cache(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()

    def clear_all(self) -> None:
        """Clear all roles and cache."""
        self._user_roles.clear()
        self._cache.clear()


# Global permissions instance
_perms = PermissionCache()


def get_permissions() -> PermissionCache:
    """Get the global permissions instance."""
    return _perms
