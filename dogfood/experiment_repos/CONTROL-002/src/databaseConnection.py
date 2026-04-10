"""Database connection management."""
import sqlite3


class DatabaseConnection:
    """Manage database connections."""

    def __init__(self, connectionString):
        self.connectionString = connectionString
        self.connection = None

    def connect(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.connectionString)
