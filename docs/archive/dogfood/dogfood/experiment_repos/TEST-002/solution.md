# Solution for TEST-002

## Task
Add edge case tests to `tests/test_client.py`. There are already 2 basic tests, you need to add more to cover edge cases.

## Required Edge Cases
- `test_get_timeout` - Request times out
- `test_post_rate_limited` - Server returns 429 Too Many Requests
- `test_get_empty_response` - Server returns empty body
- `test_post_malformed_json` - Server returns invalid JSON
- `test_connection_error` - Connection refused/failed
- `test_get_404` - Resource not found
- `test_server_error_500_retries` - Server returns 500, should retry
- `test_delete_success` - DELETE request works

## Example Tests

```python
def test_get_timeout(requests_mock):
    """GET request that times out should raise exception after retries."""
    requests_mock.get("http://api.example.com/users", exc=requests.exceptions.Timeout)
    client = APIClient("http://api.example.com", max_retries=2)
    with pytest.raises(requests.exceptions.Timeout):
        client.get("/users")


def test_post_rate_limited(requests_mock):
    """429 should be returned to caller (not retried automatically)."""
    requests_mock.post("http://api.example.com/users", status_code=429)
    client = APIClient("http://api.example.com")
    response = client.post("/users", json={"name": "Alice"})
    assert response.status_code == 429


def test_get_empty_response(requests_mock):
    """Empty response should be handled gracefully."""
    requests_mock.get("http://api.example.com/empty", text="")
    client = APIClient("http://api.example.com")
    response = client.get("/empty")
    assert response.text == ""


def test_connection_error(requests_mock):
    """Connection error should raise after retries."""
    requests_mock.get("http://api.example.com/users", exc=requests.exceptions.ConnectionError)
    client = APIClient("http://api.example.com", max_retries=2)
    with pytest.raises(requests.exceptions.ConnectionError):
        client.get("/users")


def test_server_error_retries(requests_mock):
    """500 errors should be retried."""
    requests_mock.get("http://api.example.com/users", [
        {"status_code": 500},
        {"status_code": 500},
        {"status_code": 200, "json": [{"id": 1}]}
    ])
    client = APIClient("http://api.example.com", max_retries=3)
    response = client.get("/users")
    assert response.status_code == 200
```
