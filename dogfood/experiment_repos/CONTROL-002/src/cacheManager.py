"""Cache management system."""
from datetime import datetime, timedelta


class CacheManager:
    """Manage application cache."""

    def __init__(self, maxCacheSize):
        self.maxCacheSize = maxCacheSize
        self.cacheStore = {}
        self.lastCleanup = datetime.now()

    def cleanupExpired(self):
        """Remove expired cache entries."""
        self.lastCleanup = datetime.now()
