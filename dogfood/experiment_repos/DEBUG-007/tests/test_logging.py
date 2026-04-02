"""Tests for logging configuration."""
import os
import logging
import pytest
from src.app import setup_logger, process_data, LOG_FILE


def setup_function():
    """Clean up before each test."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


def teardown_function():
    """Clean up after each test."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


def test_warning_messages_appear():
    """Test that WARNING messages appear in log file."""
    logger = setup_logger()
    # BUG: level is ERROR so WARNING is filtered - this test SHOULD fail
    process_data("hi")  # Should log WARNING about short data

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # With correct WARNING level, "short" should appear in the log
    # With buggy ERROR level, nothing appears (except maybe errors)
    assert 'short' in content.lower() or 'WARNING' in content, \
        f"WARNING message should appear in log when level is WARNING. Log content: {repr(content)}"


def test_debug_messages_dont_appear():
    """Test that DEBUG messages do NOT appear in log at WARNING level."""
    logger = setup_logger()
    # Even if DEBUG is emitted internally, with WARNING level it should be filtered

    # Pass a list - will trigger DEBUG for conversion
    # With ERROR level: DEBUG filtered, nothing logged
    # With WARNING level: DEBUG filtered, nothing logged
    result = process_data([1, 2, 3])

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # With WARNING level, no DEBUG should appear
    assert 'DEBUG' not in content, \
        f"DEBUG message should NOT appear when level is WARNING. Log content: {repr(content)}"


def test_error_messages_appear():
    """Test that ERROR messages appear in log."""
    logger = setup_logger()
    process_data("")  # Should log ERROR about no data

    with open(LOG_FILE, 'r') as f:
        content = f.read()

    # ERROR messages should always appear
    assert 'no data' in content.lower() or 'error' in content.lower(), \
        f"ERROR message should appear in log. Log content: {repr(content)}"
