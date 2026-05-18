"""Authentication implementation."""
from typing import Dict, Optional, Any


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class Authenticator:
    """Handles user authentication."""

    def __init__(self):
        # In-memory user store: user_id -> {username, password_hash, ...}
        self._users: Dict[str, Dict] = {}
        self._sessions: Dict[str, str] = {}  # session_token -> user_id

    def register_user(self, user_id: str, username: str, password: str, **extra_fields) -> Dict:
        """Register a new user."""
        # In real system, password would be hashed
        user_data = {
            "id": user_id,
            "username": username,
            "password_hash": password,  # Simplified - should be hashed
            **extra_fields
        }
        self._users[user_id] = user_data
        return user_data

    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user by username and password.

        Returns user data if authentication succeeds, None otherwise.
        """
        # Find user by username
        for user_id, user_data in self._users.items():
            if user_data["username"] == username:
                # Check password (simplified)
                if user_data["password_hash"] == password:
                    return user_data
                return None  # Wrong password
        return None  # User not found

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user data by user ID."""
        return self._users.get(user_id)

    def create_session(self, user_id: str) -> str:
        """Create a new session for a user. Returns session token."""
        # Simplified session token
        session_token = f"session_{user_id}_token"
        self._sessions[session_token] = user_id
        return session_token

    def get_user_from_session(self, session_token: str) -> Optional[Dict]:
        """Get user from session token."""
        user_id = self._sessions.get(session_token)
        if user_id:
            return self._users.get(user_id)
        return None


# Global authenticator instance
_auth = Authenticator()


def get_authenticator() -> Authenticator:
    """Get the global authenticator instance."""
    return _auth
