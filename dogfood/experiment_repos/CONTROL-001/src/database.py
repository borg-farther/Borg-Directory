"""Database connection handling."""
# TODO: Add connection pooling
import sqlite3


def get_connection():
    """Get database connection."""
    return sqlite3.connect(":memory:")
