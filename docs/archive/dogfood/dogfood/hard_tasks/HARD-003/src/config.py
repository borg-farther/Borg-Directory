"""Configuration loader with defaults."""
import json
from typing import Any, Dict, Optional


class Config:
    def __init__(self, config_file: Optional[str] = None):
        self._config: Dict[str, Any] = self._get_defaults()
        if config_file:
            self._load_from_file(config_file)

    def _get_defaults(self) -> Dict[str, Any]:
        return {
            "port": 8080,
            "host": "localhost",
            "debug": False,
            "max_connections": 100,
            "timeout": 30,
        }

    def _load_from_file(self, config_file: str) -> None:
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                self._config.update(user_config)
        except FileNotFoundError:
            pass  # Use defaults if file not found

    def get(self, key: str) -> Any:
        return self._config.get(key)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()
