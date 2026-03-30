"""
Cron State Persistence — State management for DeFi cron scans.

Provides CronState class that persists key-value state to disk,
enabling cooldowns, change detection, and signal caching across runs.

Storage: ~/.hermes/borg/defi/cron_state.json

Usage:
    state = CronState()

    # Basic get/set
    state.set("last_whale_scan", time.time())
    last = state.get("last_whale_scan")

    # Previous value tracking
    state.set("previous_pools", pool_data)
    previous = state.get_previous("previous_pools")

    # Explicit save/load
    state.save()
    state.load()
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default storage location
DEFAULT_STATE_DIR = Path.home() / ".hermes" / "borg" / "defi"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "cron_state.json"


class CronState:
    """
    Persistent state manager for cron scans.

    Stores key-value pairs in a JSON file, with support for:
    - Previous value tracking (for change detection)
    - Automatic save/load on set/get operations
    - Default values when keys don't exist

    Attributes:
        state_file: Path to the JSON state file.
        _data: In-memory copy of the state dictionary.
        _previous: Dictionary of previous values (before last set).
    """

    def __init__(
        self,
        state_file: Optional[Path] = None,
        auto_save: bool = True,
    ) -> None:
        """
        Initialize CronState.

        Args:
            state_file: Path to state file. Defaults to ~/.hermes/borg/defi/cron_state.json
            auto_save: If True, automatically save to disk after each set(). Default True.
        """
        self.state_file = state_file or DEFAULT_STATE_FILE
        self.auto_save = auto_save
        self._data: Dict[str, Any] = {}
        self._previous: Dict[str, Any] = {}

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state if available
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from state.

        Args:
            key: The key to retrieve.
            default: Default value if key doesn't exist.

        Returns:
            The stored value or default.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in state.

        Stores the previous value before overwriting, so get_previous()
        can retrieve it.

        Args:
            key: The key to set.
            value: The value to store.
        """
        # Track previous value before overwriting
        if key in self._data:
            self._previous[key] = self._data[key]
        else:
            self._previous[key] = None

        self._data[key] = value

        if self.auto_save:
            self.save()

    def get_previous(self, key: str, default: Any = None) -> Any:
        """
        Get the previous value before the last set().

        Useful for change detection - compare current vs previous.

        Args:
            key: The key to retrieve previous value for.
            default: Default if no previous value exists.

        Returns:
            The previous value or default.
        """
        return self._previous.get(key, default)

    def save(self) -> None:
        """
        Persist current state to disk.

        Writes all key-value pairs to the JSON state file.
        """
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Cron state saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save cron state: {e}")

    def load(self) -> None:
        """
        Load state from disk.

        Reads the JSON state file into memory. If the file doesn't exist,
        no error is raised - just an empty state.
        """
        if not self.state_file.exists():
            logger.debug(f"Cron state file not found at {self.state_file}, starting fresh")
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.debug(f"Cron state loaded from {self.state_file}")
        except json.JSONDecodeError as e:
            logger.warning(f"Cron state file corrupted, resetting: {e}")
            self._data = {}
        except Exception as e:
            logger.error(f"Failed to load cron state: {e}")
            self._data = {}

    def clear(self) -> None:
        """Clear all state and delete the state file."""
        self._data = {}
        self._previous = {}
        if self.state_file.exists():
            try:
                self.state_file.unlink()
                logger.debug(f"Cron state file deleted: {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to delete cron state file: {e}")

    def keys(self) -> list:
        """Return list of all keys in state."""
        return list(self._data.keys())

    def __len__(self) -> int:
        """Return number of keys in state."""
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in state."""
        return key in self._data