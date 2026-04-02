"""Tests for validators - only has 3 hardcoded tests."""
import pytest
from src.validator import validate_email, validate_phone, validate_url


def test_valid_email():
    """Test valid email."""
    assert validate_email('test@example.com') is True


def test_valid_phone():
    """Test valid phone."""
    assert validate_phone('123-456-7890') is True


def test_valid_url():
    """Test valid URL."""
    assert validate_url('https://example.com') is True
