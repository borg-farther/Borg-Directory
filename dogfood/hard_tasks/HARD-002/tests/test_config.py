"""Tests for configuration management."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Reset config cache before each test
from src.service import reset_config, get_config

def test_default_port_is_3000():
    """Default port should be 3000, not 8080."""
    reset_config()
    # Clear any env vars that might interfere
    for key in ["PORT", "TIMEOUT", "DEBUG"]:
        os.environ.pop(key, None)
    
    config = get_config()
    assert config["port"] == 3000, f"Expected port=3000, got {config['port']}"

def test_default_timeout_is_5():
    """Default timeout should be 5 seconds, not 30."""
    reset_config()
    for key in ["PORT", "TIMEOUT", "DEBUG"]:
        os.environ.pop(key, None)
    
    config = get_config()
    assert config["timeout"] == 5, f"Expected timeout=5, got {config['timeout']}"

def test_env_override_port():
    """Environment variable should override default port."""
    reset_config()
    os.environ["PORT"] = "9000"
    os.environ.pop("TIMEOUT", None)
    os.environ.pop("DEBUG", None)
    
    config = get_config()
    assert config["port"] == 9000, f"Expected port=9000, got {config['port']}"
    os.environ.pop("PORT", None)

def test_env_override_timeout():
    """Environment variable should override default timeout."""
    reset_config()
    os.environ["TIMEOUT"] = "15"
    os.environ.pop("PORT", None)
    os.environ.pop("DEBUG", None)
    
    config = get_config()
    assert config["timeout"] == 15, f"Expected timeout=15, got {config['timeout']}"
    os.environ.pop("TIMEOUT", None)
