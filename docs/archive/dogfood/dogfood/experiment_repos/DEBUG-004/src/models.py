"""Models module - has import cycle with utils."""
from utils import format_timestamp


class User:
    """User model."""

    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email
        self.created_at = format_timestamp()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at,
        }
