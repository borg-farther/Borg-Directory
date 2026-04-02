"""Simple in-memory database implementation."""
from typing import Any, Dict, Optional, List


class Database:
    def __init__(self):
        self._data: Dict[str, Dict] = {}

    def put(self, key: str, value: Dict) -> None:
        """Store a record in the database."""
        self._data[key] = value

    def get(self, key: str) -> Optional[Dict]:
        """Retrieve a record by key."""
        # BUG: Returns a reference to the internal dict, not a copy!
        # This causes mutations to corrupt the stored data
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete a record by key."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return key in self._data

    def get_all(self) -> List[Dict]:
        """Get all records as a list."""
        return list(self._data.values())

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()

    def count(self) -> int:
        """Return the number of records."""
        return len(self._data)


# Global database instance
_db = Database()


def get_db() -> Database:
    """Get the global database instance."""
    return _db
