"""Service - uses transformed configuration."""

from .config_loader import load_config
from .transformer import transform_config

_config = None

def get_config():
    """Get the transformed configuration (lazy loaded)."""
    global _config
    if _config is None:
        raw_config = load_config()
        _config = transform_config(raw_config)
    return _config

def reset_config():
    """Reset config cache (for testing)."""
    global _config
    _config = None

def start_service():
    """Start the service with current configuration."""
    config = get_config()
    return {
        "status": "started",
        "port": config["port"],
        "timeout": config["timeout"],
        "debug": config["debug"]
    }
