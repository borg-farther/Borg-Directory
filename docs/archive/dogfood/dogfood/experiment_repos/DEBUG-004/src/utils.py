"""Utils module - imports from models creating cycle."""
from models import User


def format_timestamp():
    """Format current time as ISO string."""
    from datetime import datetime
    return datetime.now().isoformat()


def create_user(id, name, email):
    """Factory function to create User instance."""
    return User(id, name, email)


def validate_user(user):
    """Validate a user object."""
    if not isinstance(user, User):
        return False
    return bool(user.name and user.email)
