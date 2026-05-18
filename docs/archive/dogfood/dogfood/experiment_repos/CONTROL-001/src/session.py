"""Session management."""
# TODO: Add session expiration
from datetime import datetime


class Session:
    """User session."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.created_at = datetime.now()
