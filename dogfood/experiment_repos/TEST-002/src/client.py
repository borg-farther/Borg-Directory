"""HTTP client wrapper with retry logic."""
import time
import requests


class APIClient:
    """HTTP client with retry logic."""

    def __init__(self, base_url, max_retries=3, timeout=5):
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout = timeout

    def _request(self, method, path, **kwargs):
        """Make HTTP request with retries."""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))

        return None

    def get(self, path, **kwargs):
        """GET request."""
        return self._request("GET", path, **kwargs)

    def post(self, path, data=None, json=None, **kwargs):
        """POST request."""
        return self._request("POST", path, data=data, json=json, **kwargs)

    def put(self, path, data=None, json=None, **kwargs):
        """PUT request."""
        return self._request("PUT", path, data=data, json=json, **kwargs)

    def delete(self, path, **kwargs):
        """DELETE request."""
        return self._request("DELETE", path, **kwargs)
