"""User authentication and authorization."""
# TODO: Add OAuth2 support


class UserAuth:
    """Handle user authentication."""

    def __init__(self, userId, userName):
        self.userId = userId
        self.userName = userName

    def authenticate(self, password):
        """Authenticate user with password."""
        return password == "secret"
