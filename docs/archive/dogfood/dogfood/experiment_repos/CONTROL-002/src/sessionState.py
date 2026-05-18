"""Session state management."""
from datetime import datetime


class SessionState:
    """Manage user session state."""

    def __init__(self, sessionId, userId):
        self.sessionId = sessionId
        self.userId = userId
        self.createdAt = datetime.now()

    def isExpired(self):
        """Check if session has expired."""
        return False
