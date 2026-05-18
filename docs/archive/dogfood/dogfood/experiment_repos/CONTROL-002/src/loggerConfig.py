"""Logging configuration."""
import logging


class LoggerConfig:
    """Configure application logging."""

    def __init__(self, logLevel, logFilePath):
        self.logLevel = logLevel
        self.logFilePath = logFilePath

    def setup(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=self.logLevel,
            filename=self.logFilePath
        )
