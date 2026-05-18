"""Tests for auth - tests pass but don't catch security issues."""
import pytest
import os
import sqlite3
from src.auth import authenticate_user, create_user, get_user_profile


def setup_function():
    """Setup test database."""
    if os.path.exists('users.db'):
        os.remove('users.db')


def teardown_function():
    """Cleanup."""
    if os.path.exists('users.db'):
        os.remove('users.db')


def test_create_and_authenticate():
    """Basic test - works but doesn't catch security issues."""
    create_user('testuser', 'testpass')
    user = authenticate_user('testuser', 'testpass')
    assert user is not None
    assert user['username'] == 'testuser'


def test_authenticate_invalid_user():
    """Test invalid credentials."""
    user = authenticate_user('nonexistent', 'wrongpass')
    assert user is None


def test_get_user_profile():
    """Test getting user profile."""
    create_user('testuser', 'testpass')
    profile = get_user_profile(1)
    assert profile is not None
    assert profile['username'] == 'testuser'
