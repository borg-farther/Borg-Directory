"""Tests for the configuration system."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app import create_app, Application
from config import Config
from validator import validate_config, ConfigValidationError


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test that a valid config passes validation."""
        config = {
            "port": 8080,
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        validate_config(config)  # Should not raise

    def test_zero_string_in_config(self):
        """Test that string '0' values are treated as valid, not missing."""
        config = {
            "port": "0",  # String zero, should be valid
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        # This should NOT raise ConfigValidationError
        validate_config(config)

    def test_zero_string_port_in_app(self):
        """Test that app can be created with string '0' as port."""
        config = {
            "port": "0",
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        # This should NOT raise - the bug causes it to raise
        app = create_app(config)
        assert app.port == "0"

    def test_empty_string_host(self):
        """Test that empty string is properly rejected as host."""
        config = {
            "port": 8080,
            "host": "",  # Empty string should be rejected
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        with pytest.raises(ConfigValidationError):
            validate_config(config)

    def test_none_host(self):
        """Test that None is properly rejected as host."""
        config = {
            "port": 8080,
            "host": None,
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        with pytest.raises(ConfigValidationError):
            validate_config(config)

    def test_zero_max_connections(self):
        """Test that max_connections of 0 is valid (edge case)."""
        config = {
            "port": 8080,
            "host": "localhost",
            "debug": False,
            "max_connections": 0,
            "timeout": 30,
        }
        # 0 is technically invalid per validation (must be >= 1)
        # but it should not be treated as "missing"
        with pytest.raises(ConfigValidationError):
            validate_config(config)


class TestApplication:
    """Test application creation and running."""

    def test_app_creation_with_normal_config(self):
        """Test normal app creation."""
        config = {
            "port": 3000,
            "host": "0.0.0.0",
            "debug": True,
            "max_connections": 50,
            "timeout": 60,
        }
        app = create_app(config)
        assert app.port == 3000
        assert app.host == "0.0.0.0"
        assert app.debug is True

    def test_app_creation_with_string_zero_port(self):
        """Test app creation with string '0' as port value."""
        config = {
            "port": "0",
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        # This is the key test - should work but currently fails
        app = create_app(config)
        assert app.port == "0"
        assert app.host == "localhost"

    def test_app_run(self):
        """Test running the application."""
        config = {
            "port": 8080,
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }
        app = create_app(config)
        result = app.run()
        assert "localhost:8080" in result
