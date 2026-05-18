"""Data validation utilities."""


class DataValidator:
    """Validate input data."""

    @staticmethod
    def validateEmail(emailAddress):
        """Validate email address format."""
        return "@" in emailAddress

    @staticmethod
    def validatePassword(passwordString):
        """Validate password strength."""
        return len(passwordString) >= 8
