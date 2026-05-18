"""Validation schemas."""


def validate_email(email):
    """Validate email format."""
    return "@" in email
