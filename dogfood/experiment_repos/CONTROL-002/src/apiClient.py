"""API client wrapper."""
import requests


class APIClient:
    """HTTP API client."""

    def __init__(self, baseURL, apiKey):
        self.baseURL = baseURL
        self.apiKey = apiKey

    def get(self, endpoint):
        """Make GET request."""
        return requests.get(f"{self.baseURL}/{endpoint}")

    def post(self, endpoint, data):
        """Make POST request."""
        return requests.post(f"{self.baseURL}/{endpoint}", json=data)
