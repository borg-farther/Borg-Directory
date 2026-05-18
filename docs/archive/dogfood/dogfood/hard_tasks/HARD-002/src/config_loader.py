"""Configuration loader - reads config from environment with defaults."""

import os

DEFAULT_CONFIG = {
    "port": 3000,
    "timeout": 5,
    "debug": False,
    "workers": 4
}

def load_config():
    """Load configuration from environment variables with defaults.
    
    Environment variables override defaults:
    - PORT: defaults to 3000
    - TIMEOUT: defaults to 5
    - DEBUG: defaults to False
    """
    config = DEFAULT_CONFIG.copy()
    
    # RED HERRING: The env var names look correct
    # but there's a subtle bug in how they're applied
    if "PORT" in os.environ:
        config["port"] = int(os.environ["PORT"])
    
    if "TIMEOUT" in os.environ:
        config["timeout"] = int(os.environ["TIMEOUT"])
    
    if "DEBUG" in os.environ:
        config["debug"] = os.environ["DEBUG"].lower() in ("true", "1", "yes")
    
    return config
