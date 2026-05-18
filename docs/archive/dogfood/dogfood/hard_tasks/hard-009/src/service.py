"""Service layer with cache-through reads."""

from typing import Any, Optional

from .cache import LRUCache
from .store import DataStore


class UserService:
    """
    User service that uses cache-through pattern.
    
    Relies on store.update() to properly invalidate cache,
    but store.py has a bug where it doesn't invalidate.
    """

    def __init__(self, cache: LRUCache, store: DataStore):
        self._cache = cache
        self._store = store

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID - reads from cache or store."""
        return self._store.read(user_id)

    def create_user(self, user_id: str, user_data: dict) -> None:
        """Create new user."""
        self._store.write(user_id, user_data)

    def update_user(self, user_id: str, user_data: dict) -> None:
        """
        Update user.
        
        Calls store.update() which has the bug - doesn't invalidate cache.
        """
        self._store.update(user_id, user_data)

    def update_user_field(self, user_id: str, field: str, value: Any) -> None:
        """
        Update a specific field in user data.
        
        BUG: This method reads from cache, modifies, then writes back.
        But store.update() doesn't invalidate, so next read gets stale cache.
        """
        # Get current user (from cache or store)
        user = self.get_user(user_id)
        if user is None:
            return
        
        # Update field
        user[field] = value
        
        # Write back via update (which has the bug)
        self._store.update(user_id, user)

    def batch_update_users(self, updates: dict) -> None:
        """Batch update users."""
        self._store.update_batch(updates)
