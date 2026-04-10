"""Caching layer."""
# TODO: Implement LRU eviction
from datetime import datetime, timedelta


class Cache:
    """Simple in-memory cache."""

    def __init__(self):
        self._store = {}

    def set(self, key, value):
        """Set cache value."""
        self._store[key] = value
