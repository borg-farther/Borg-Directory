"""Logging utilities."""
import logging

logger = logging.getLogger(__name__)


def log_request(request):
    """Log incoming request."""
    logger.info(f"Request: {request}")
