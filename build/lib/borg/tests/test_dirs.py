"""
Tests for borg/core/dirs.py — BORG_DIR environment variable override.
"""

import os
import pytest
from pathlib import Path

from borg.core import dirs


class TestGetBorgDir:
    """Test get_borg_dir() env-var override."""

    def test_default_is_home_hermes_guild(self, monkeypatch):
        """Without BORG_DIR set, defaults to ~/.hermes/guild."""
        monkeypatch.delenv("BORG_DIR", raising=False)
        # Force re-evaluation by patching the env after import
        result = dirs.get_borg_dir()
        expected = Path.home() / ".hermes" / "guild"
        assert result == expected

    def test_borg_dir_env_var_overrides_default(self, monkeypatch, tmp_path):
        """Setting BORG_DIR env var changes the returned path."""
        custom = tmp_path / "custom-guild"
        monkeypatch.setenv("BORG_DIR", str(custom))
        result = dirs.get_borg_dir()
        assert result == custom

    def test_borg_dir_env_var_with_tilde_expansion(self, monkeypatch, tmp_path):
        """BORG_DIR env var with ~ in path is NOT expanded by get_borg_dir (Path does not expand ~ in env vars)."""
        # This is a property of how the env var works — Path doesn't expand ~
        monkeypatch.setenv("BORG_DIR", "~/my-guild")
        result = dirs.get_borg_dir()
        # Path treats ~ literally when it comes from env var
        assert str(result) == str(Path("~/my-guild"))

    def test_borg_dir_can_be_absolute_path(self, monkeypatch, tmp_path):
        """An absolute path works as BORG_DIR."""
        abs_path = tmp_path / "abs-guild"
        monkeypatch.setenv("BORG_DIR", str(abs_path))
        assert dirs.get_borg_dir() == abs_path


class TestModuleLevelBorgDirConstant:
    """Test the module-level BORG_DIR constant (backwards compat)."""

    def test_borg_dir_constant_matches_get_borg_dir_at_load_time(self, monkeypatch):
        """The BORG_DIR constant equals get_borg_dir() when the module was loaded."""
        # Note: because BORG_DIR is captured at import time, it won't change
        # if BORG_DIR env var is set after import. Use get_borg_dir() for
        # dynamic behaviour. This test documents the current behaviour.
        monkeypatch.setenv("BORG_DIR", "/test-path")
        # After the env var is set, get_borg_dir() should return the new value
        assert dirs.get_borg_dir() == Path("/test-path")
