"""Input validators."""
# TODO: Add more validation rules


def validate_username(username):
    """Validate username."""
    return len(username) >= 3


def validate_password(password):
    """Validate password strength."""
    return len(password) >= 8
