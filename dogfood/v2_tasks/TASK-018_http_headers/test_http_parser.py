"""Test cases for HTTP header parsing."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-018_http_headers')

from http_parser import HTTPRequest, HTTPServer


def test_basic_request_parsing():
    """Test parsing a simple HTTP request."""
    raw = "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    request = HTTPRequest.parse(raw)
    
    assert request.method == "GET"
    assert request.path == "/"
    assert request.version == "HTTP/1.1"
    print("test_basic_request_parsing: PASS")


def test_header_storage():
    """Test that headers are stored correctly."""
    request = HTTPRequest()
    request.set_header("Content-Type", "application/json")
    
    assert request.headers.get("Content-Type") == "application/json"
    print("test_header_storage: PASS")


def test_case_insensitive_get():
    """
    Test that get_header is case-insensitive.
    
    BUG: The current implementation is case-sensitive,
    so this test fails!
    """
    request = HTTPRequest()
    request.set_header("Content-Type", "application/json")
    
    # All these should return the same value
    assert request.get_header("Content-Type") == "application/json"
    assert request.get_header("content-type") == "application/json", \
        "get_header should be case-insensitive"
    assert request.get_header("CONTENT-TYPE") == "application/json", \
        "get_header should be case-insensitive"
    
    print("test_case_insensitive_get: PASS")


def test_case_insensitive_has():
    """Test that has_header is case-insensitive."""
    request = HTTPRequest()
    request.set_header("X-Custom-Header", "value")
    
    assert request.has_header("X-Custom-Header")
    assert request.has_header("x-custom-header"), \
        "has_header should be case-insensitive"
    assert request.has_header("X-CUSTOM-HEADER"), \
        "has_header should be case-insensitive"
    
    print("test_case_insensitive_has: PASS")


def test_parse_mixed_case_headers():
    """Test parsing request with mixed-case header names."""
    raw = "GET /test HTTP/1.1\r\nHost: localhost\r\ncontent-type: text/html\r\n\r\n"
    request = HTTPRequest.parse(raw)
    
    # Should be able to retrieve with different case
    assert request.get_header("Content-Type") == "text/html"
    assert request.get_header("content-type") == "text/html"
    assert request.get_header("CONTENT-TYPE") == "text/html"
    
    print("test_parse_mixed_case_headers: PASS")


def test_server_process_request():
    """Test server processing with case-insensitive headers."""
    server = HTTPServer()
    
    raw = "POST /api HTTP/1.1\r\nHost: localhost\r\ncontent-type: application/json\r\nContent-Length: 50\r\n\r\n"
    
    response = server.process_request(raw)
    
    # Server should correctly identify Content-Type regardless of case
    assert response['headers'].get('Content-Type') == 'application/json', \
        f"Server should handle case-insensitive Content-Type, got {response['headers']}"
    
    print("test_server_process_request: PASS")


def test_standard_http_headers():
    """Test that standard HTTP headers work case-insensitively."""
    request = HTTPRequest()
    
    # These are common HTTP headers that should be case-insensitive
    standard_headers = {
        'Content-Type': 'text/html',
        'Content-Length': '123',
        'Host': 'example.com',
        'User-Agent': 'TestClient/1.0',
        'Accept': '*/*',
    }
    
    for name, value in standard_headers.items():
        request.set_header(name, value)
    
    # Check all variations
    for name in standard_headers.keys():
        lower = name.lower()
        upper = name.upper()
        
        assert request.get_header(lower) == standard_headers[name], \
            f"get_header('{lower}') should return '{standard_headers[name]}'"
        assert request.get_header(upper) == standard_headers[name], \
            f"get_header('{upper}') should return '{standard_headers[name]}'"


def test_header_not_found():
    """Test get_header returns None for missing headers."""
    request = HTTPRequest()
    request.set_header("Content-Type", "text/plain")
    
    assert request.get_header("Non-Existent") is None
    assert request.get_header("content-type") == "text/plain"  # case insensitive
    
    print("test_header_not_found: PASS")


if __name__ == "__main__":
    test_basic_request_parsing()
    test_header_storage()
    test_case_insensitive_get()
    test_case_insensitive_has()
    test_parse_mixed_case_headers()
    test_server_process_request()
    test_standard_http_headers()
    test_header_not_found()
    print("\nAll tests passed!")
