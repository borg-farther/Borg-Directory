"""Application entry point."""
from typing import Dict, Any
from config import Config
from validator import validate_config, ConfigValidationError


class Application:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Validate config - this is where the error manifests
        validate_config(self.config)
        self._initialize()

    def _initialize(self) -> None:
        """Initialize application with validated config."""
        self.port = self.config["port"]
        self.host = self.config["host"]
        self.debug = self.config["debug"]
        self.max_connections = self.config["max_connections"]
        self.timeout = self.config["timeout"]

    def run(self) -> str:
        """Run the application."""
        return f"Application running on {self.host}:{self.port} (debug={self.debug})"


def create_app(config_dict: Dict[str, Any]) -> Application:
    """Create and return a new application instance."""
    return Application(config_dict)
