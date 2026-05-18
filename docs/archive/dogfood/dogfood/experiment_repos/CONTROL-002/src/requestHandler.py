"""HTTP request handler."""
from urllib.parse import urlparse


class RequestHandler:
    """Handle incoming HTTP requests."""

    def __init__(self, requestURL, requestMethod):
        self.requestURL = requestURL
        self.requestMethod = requestMethod
        self.queryParams = {}

    def parseURL(self):
        """Parse the request URL."""
        parsed = urlparse(self.requestURL)
        return parsed.path
