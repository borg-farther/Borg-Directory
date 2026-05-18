"""Flask app with logging misconfiguration."""
import logging
import os

LOG_FILE = '/tmp/app.log'


def setup_logger():
    """Setup logger - THIS IS THE PROBLEM."""
    # Clear log file
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    logger = logging.getLogger('app')
    logger.setLevel(logging.ERROR)  # Too high - misses WARNING

    handler = logging.FileHandler(LOG_FILE)
    handler.setLevel(logging.DEBUG)  # Handler level doesn't matter if logger is ERROR

    # Missing formatter - log messages won't have proper format
    logger.addHandler(handler)

    return logger


def process_data(data):
    """Process data with various log levels."""
    logger = logging.getLogger('app')

    if not data:
        logger.error("No data provided")
        return None

    if len(data) < 5:
        logger.warning("Data is too short")

    if not isinstance(data, str):
        logger.debug("Converting data to string")
        data = str(data)

    logger.info("Data processed successfully")
    return data.upper()
