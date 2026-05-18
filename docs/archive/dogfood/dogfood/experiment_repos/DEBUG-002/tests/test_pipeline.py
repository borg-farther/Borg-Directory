"""Tests for data pipeline."""
import pytest
from pipeline import get_user_data, process_users, generate_report


def test_get_existing_user():
    """Existing user returns dict."""
    result = get_user_data(1)
    assert result == {"name": "Alice", "email": "alice@example.com"}


def test_get_missing_user_returns_empty_dict():
    """Missing user should return empty dict, not None."""
    result = get_user_data(999)
    assert result == {}


def test_process_users_with_mixed_valid_and_missing():
    """Pipeline should handle mix of existing and missing user IDs."""
    # User 1 exists, user 999 does not
    result = process_users([1, 999])
    # Should return only the valid user, not crash
    assert len(result) == 1
    assert result[0]["name"] == "ALICE"


def test_process_users_all_missing():
    """Pipeline should handle all missing users gracefully."""
    result = process_users([999, 888])
    assert result == []


def test_generate_report_with_missing_users():
    """Report generation should not crash on missing users."""
    report = generate_report([1, 999, 2])
    assert "ALICE" in report
    assert "BOB" in report
