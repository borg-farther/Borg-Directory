"""Tests for import cycle."""
import pytest
import sys


def test_import_models():
    """Importing models should work without cycle error."""
    # Clear any cached imports
    mods_to_remove = [k for k in sys.modules.keys() if k in ('models', 'utils')]
    for mod in mods_to_remove:
        del sys.modules[mod]

    # This should not raise ImportError
    from models import User
    assert User is not None


def test_import_utils():
    """Importing utils should work without cycle error."""
    mods_to_remove = [k for k in sys.modules.keys() if k in ('models', 'utils')]
    for mod in mods_to_remove:
        del sys.modules[mod]

    from utils import format_timestamp
    assert format_timestamp is not None


def test_user_creation():
    """User creation should work."""
    mods_to_remove = [k for k in sys.modules.keys() if k in ('models', 'utils')]
    for mod in mods_to_remove:
        del sys.modules[mod]

    from models import User
    user = User(1, "Alice", "alice@example.com")
    assert user.name == "Alice"
    assert user.to_dict()["email"] == "alice@example.com"
