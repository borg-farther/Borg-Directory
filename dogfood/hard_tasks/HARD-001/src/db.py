"""Database query layer - simulates fetching user data from a database."""

# Mock database - in real scenario this would be an actual DB query
USERS_DB = {
    1: {
        "user_id": 1,
        "user_name": "Alice Smith",
        "email_addr": "alice@example.com",
        "signup_date": "2024-01-15T10:30:00Z"
    },
    2: {
        "user_id": 2,
        "user_name": "Bob Jones",
        "email_addr": "bob@example.com",
        "signup_date": "2024-02-20T14:45:00Z"
    }
}

def get_user_by_id(user_id):
    """Fetch user record from database by ID."""
    return USERS_DB.get(user_id)

def get_user_email(user_id):
    """Fetch only the email field for a user."""
    user = USERS_DB.get(user_id)
    if user:
        return user.get("email_addr")
    return None
