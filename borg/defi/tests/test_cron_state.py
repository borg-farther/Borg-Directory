"""
Tests for Cron State Module.

Tests CronState class for state persistence, previous value tracking,
and key-value operations.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from borg.defi.cron.state import CronState, DEFAULT_STATE_DIR, DEFAULT_STATE_FILE


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------

@pytest.fixture
def temp_state_file(tmp_path):
    """Create a temporary state file path."""
    return tmp_path / "test_cron_state.json"


@pytest.fixture
def cron_state(temp_state_file):
    """Create a CronState instance with temporary state file."""
    return CronState(state_file=temp_state_file, auto_save=False)


# -------------------------------------------------------------------------
# Initialization Tests
# -------------------------------------------------------------------------

class TestCronStateInit:
    """Tests for CronState initialization."""

    def test_default_state_file(self):
        """Default state file path is set correctly."""
        state = CronState(auto_save=False)
        assert state.state_file == DEFAULT_STATE_FILE

    def test_custom_state_file(self, temp_state_file):
        """Custom state file path is accepted."""
        state = CronState(state_file=temp_state_file, auto_save=False)
        assert state.state_file == temp_state_file

    def test_empty_state_on_init(self, cron_state):
        """State is empty on initialization."""
        assert len(cron_state) == 0
        assert cron_state.keys() == []

    def test_directory_created(self, temp_state_file):
        """Parent directory is created if it doesn't exist."""
        new_path = temp_state_file.parent / "nested" / "state.json"
        state = CronState(state_file=new_path, auto_save=False)
        assert new_path.parent.exists()


# -------------------------------------------------------------------------
# Get/Set Tests
# -------------------------------------------------------------------------

class TestCronStateGetSet:
    """Tests for CronState get/set operations."""

    def test_set_and_get_string(self, cron_state):
        """Set and get string value."""
        cron_state.set("key1", "value1")
        assert cron_state.get("key1") == "value1"

    def test_set_and_get_number(self, cron_state):
        """Set and get numeric value."""
        cron_state.set("counter", 42)
        assert cron_state.get("counter") == 42

    def test_set_and_get_list(self, cron_state):
        """Set and get list value."""
        cron_state.set("items", [1, 2, 3])
        assert cron_state.get("items") == [1, 2, 3]

    def test_set_and_get_dict(self, cron_state):
        """Set and get dict value."""
        cron_state.set("data", {"a": 1, "b": 2})
        assert cron_state.get("data") == {"a": 1, "b": 2}

    def test_get_default_missing_key(self, cron_state):
        """Get returns default for missing key."""
        result = cron_state.get("missing", "default")
        assert result == "default"

    def test_get_no_default_missing_key(self, cron_state):
        """Get returns None for missing key with no default."""
        result = cron_state.get("missing")
        assert result is None

    def test_overwrite_value(self, cron_state):
        """Overwriting a value updates it."""
        cron_state.set("key", "first")
        cron_state.set("key", "second")
        assert cron_state.get("key") == "second"


# -------------------------------------------------------------------------
# Previous Value Tests
# -------------------------------------------------------------------------

class TestCronStatePrevious:
    """Tests for CronState previous value tracking."""

    def test_get_previous_after_set(self, cron_state):
        """get_previous returns previous value after set."""
        cron_state.set("key", "first")
        cron_state.set("key", "second")
        assert cron_state.get_previous("key") == "first"

    def test_get_previous_no_previous(self, cron_state):
        """get_previous returns None for never-set key."""
        result = cron_state.get_previous("new_key")
        assert result is None

    def test_get_previous_default(self, cron_state):
        """get_previous returns default when no previous."""
        result = cron_state.get_previous("missing", "default")
        assert result == "default"

    def test_previous_tracks_multiple_sets(self, cron_state):
        """Previous value updates on each set."""
        cron_state.set("key", "v1")
        cron_state.set("key", "v2")
        cron_state.set("key", "v3")
        assert cron_state.get_previous("key") == "v2"

    def test_previous_none_for_new_key(self, cron_state):
        """Previous is None for newly created key."""
        cron_state.set("new_key", "value")
        assert cron_state.get_previous("new_key") is None


# -------------------------------------------------------------------------
# Save/Load Tests
# -------------------------------------------------------------------------

class TestCronStateSaveLoad:
    """Tests for CronState save/load operations."""

    def test_save_creates_file(self, cron_state, temp_state_file):
        """Save creates the state file."""
        cron_state.set("key", "value")
        cron_state.save()

        assert temp_state_file.exists()

    def test_save_writes_json(self, cron_state, temp_state_file):
        """Save writes valid JSON."""
        cron_state.set("key", "value")
        cron_state.set("number", 42)
        cron_state.save()

        with open(temp_state_file, "r") as f:
            data = json.load(f)

        assert data["key"] == "value"
        assert data["number"] == 42

    def test_load_reads_file(self, cron_state, temp_state_file):
        """Load reads state from file."""
        # Write some data directly
        with open(temp_state_file, "w") as f:
            json.dump({"loaded": "data"}, f)

        # Create new state and load
        state = CronState(state_file=temp_state_file, auto_save=False)
        state.load()

        assert state.get("loaded") == "data"

    def test_load_nonexistent_file(self, cron_state, temp_state_file):
        """Load handles nonexistent file gracefully."""
        # File doesn't exist
        state = CronState(state_file=temp_state_file, auto_save=False)
        state.load()

        assert len(state) == 0

    def test_corrupted_file_resets(self, cron_state, temp_state_file):
        """Corrupted JSON file causes reset."""
        # Write invalid JSON
        with open(temp_state_file, "w") as f:
            f.write("not valid json {")

        state = CronState(state_file=temp_state_file, auto_save=False)
        state.load()

        assert len(state) == 0


# -------------------------------------------------------------------------
# Auto-save Tests
# -------------------------------------------------------------------------

class TestCronStateAutoSave:
    """Tests for CronState auto_save behavior."""

    def test_auto_save_disabled(self, temp_state_file):
        """With auto_save=False, must call save manually."""
        state = CronState(state_file=temp_state_file, auto_save=False)
        state.set("key", "value")

        # File should not exist yet
        assert not temp_state_file.exists()

        # After save, file exists
        state.save()
        assert temp_state_file.exists()

    def test_auto_save_enabled(self, temp_state_file):
        """With auto_save=True, set() triggers save."""
        state = CronState(state_file=temp_state_file, auto_save=True)
        state.set("key", "value")

        # File should exist immediately after set
        assert temp_state_file.exists()

        # Verify content
        with open(temp_state_file, "r") as f:
            data = json.load(f)
        assert data["key"] == "value"


# -------------------------------------------------------------------------
# Clear and Utility Tests
# -------------------------------------------------------------------------

class TestCronStateUtilities:
    """Tests for CronState utility methods."""

    def test_clear(self, cron_state, temp_state_file):
        """Clear removes all data and deletes file."""
        cron_state.set("key1", "value1")
        cron_state.set("key2", "value2")
        cron_state.save()

        assert temp_state_file.exists()

        cron_state.clear()

        assert len(cron_state) == 0
        assert not temp_state_file.exists()

    def test_keys(self, cron_state):
        """keys() returns all state keys."""
        cron_state.set("a", 1)
        cron_state.set("b", 2)
        cron_state.set("c", 3)

        keys = cron_state.keys()
        assert set(keys) == {"a", "b", "c"}

    def test_contains(self, cron_state):
        """__contains__ works correctly."""
        cron_state.set("exists", "value")
        assert "exists" in cron_state
        assert "not_exists" not in cron_state

    def test_len(self, cron_state):
        """__len__ returns correct count."""
        assert len(cron_state) == 0
        cron_state.set("a", 1)
        assert len(cron_state) == 1
        cron_state.set("b", 2)
        assert len(cron_state) == 2


# -------------------------------------------------------------------------
# Integration Tests
# -------------------------------------------------------------------------

class TestCronStateIntegration:
    """Integration tests for CronState."""

    def test_full_workflow(self, temp_state_file):
        """Test typical usage: create, set, save, reload."""
        # Create state and add data
        state1 = CronState(state_file=temp_state_file, auto_save=False)
        state1.set("last_scan", 1234567890)
        state1.set("results", [1, 2, 3])
        state1.save()

        # Later, reload and check data
        state2 = CronState(state_file=temp_state_file, auto_save=False)
        state2.load()

        assert state2.get("last_scan") == 1234567890
        assert state2.get("results") == [1, 2, 3]

    def test_previous_value_tracking_across_save_load(self, temp_state_file):
        """Previous values persist across save/load cycle."""
        state1 = CronState(state_file=temp_state_file, auto_save=False)
        state1.set("value", "first")
        state1.set("value", "second")
        assert state1.get_previous("value") == "first"

        # Save and reload
        state1.save()

        state2 = CronState(state_file=temp_state_file, auto_save=False)
        state2.load()

        # Previous is NOT persisted (only in-memory tracking)
        assert state2.get_previous("value") is None
        # Current value is persisted
        assert state2.get("value") == "second"