"""HTTP client tests - missing edge cases."""
import pytest
import requests_mock
from client import APIClient


def test_get_success(requests_mock):
    """Basic GET request returns 200."""
    requests_mock.get("http://api.example.com/users", json=[{"id": 1}])
    client = APIClient("http://api.example.com")
    response = client.get("/users")
    assert response.status_code == 200
    assert response.json() == [{"id": 1}]


def test_post_success(requests_mock):
    """Basic POST request returns 201."""
    requests_mock.post("http://api.example.com/users", json={"id": 1}, status_code=201)
    client = APIClient("http://api.example.com")
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 201
    assert response.json() == {"id": 1}


# Edge cases that need to be added:
# - test_get_timeout
# - test_post_rate_limited (429)
# - test_get_empty_response
# - test_post_malformed_json
# - test_connection_error
# - test_get_404
# - test_server_error_500_retries
