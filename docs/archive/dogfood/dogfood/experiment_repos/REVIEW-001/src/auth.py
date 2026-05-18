"""Authentication module with security vulnerabilities."""
import sqlite3
import hashlib


def authenticate_user(username, password):
    """
    Authenticate user - VULNERABLE: SQL injection and plaintext passwords.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILITY 1: SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)

    result = cursor.fetchone()
    conn.close()

    if result:
        return {'username': result[1], 'id': result[0]}
    return None


def create_user(username, password):
    """
    Create new user - VULNERABLE: stores plaintext password.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT
        )
    ''')

    # VULNERABILITY 2: Plaintext password storage
    query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
    cursor.execute(query)
    conn.commit()
    conn.close()

    return True


def get_user_profile(user_id):
    """
    Get user profile - VULNERABLE: SQL injection in user_id.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILITY 3: SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)

    result = cursor.fetchone()
    conn.close()

    if result:
        return {'id': result[0], 'username': result[1]}
    return None


def hash_password_sha256(password):
    """Simple hash - not really helping since we don't use it in auth."""
    return hashlib.sha256(password.encode()).hexdigest()
