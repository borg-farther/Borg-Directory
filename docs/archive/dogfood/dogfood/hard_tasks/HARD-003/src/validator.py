"""Configuration validator."""
from typing import Any, Dict, List, Optional


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_keys = ["port", "host", "debug", "max_connections", "timeout"]

    def validate(self) -> None:
        """Validate all configuration values."""
        self._validate_required_keys()
        self._validate_port()
        self._validate_host()
        self._validate_debug()
        self._validate_max_connections()
        self._validate_timeout()

    def _validate_required_keys(self) -> None:
        for key in self.required_keys:
            value = self.config.get(key)
            # BUG: This treats string '0' as falsy
            if not value:
                raise ConfigValidationError(f"Missing required configuration: {key}")

    def _validate_port(self) -> None:
        port = self.config.get("port")
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise ConfigValidationError("Port must be an integer between 1 and 65535")

    def _validate_host(self) -> None:
        host = self.config.get("host")
        if host is not None:
            if not isinstance(host, str) or len(host) == 0:
                raise ConfigValidationError("Host must be a non-empty string")

    def _validate_debug(self) -> None:
        debug = self.config.get("debug")
        if debug is not None:
            if not isinstance(debug, bool):
                raise ConfigValidationError("Debug must be a boolean")

    def _validate_max_connections(self) -> None:
        max_conn = self.config.get("max_connections")
        if max_conn is not None:
            if not isinstance(max_conn, int) or max_conn < 1:
                raise ConfigValidationError("Max connections must be a positive integer")

    def _validate_timeout(self) -> None:
        timeout = self.config.get("timeout")
        if timeout is not None:
            if not isinstance(timeout, (int, float)) or timeout < 0:
                raise ConfigValidationError("Timeout must be a non-negative number")


def validate_config(config: Dict[str, Any]) -> None:
    """Validate a configuration dictionary."""
    validator = ConfigValidator(config)
    validator.validate()
