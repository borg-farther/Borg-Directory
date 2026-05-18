"""Authentication module."""
# TODO: Implement OAuth2 support
def authenticate(username, password):
    """Simple authentication."""
    return username == "admin" and password == "secret"


def logout(user):
    """Log out user."""
    pass
