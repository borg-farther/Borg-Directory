"""Custom exceptions."""


class AppError(Exception):
    """Base application error."""
    pass


class ValidationError(AppError):
    """Validation failed."""
    pass
