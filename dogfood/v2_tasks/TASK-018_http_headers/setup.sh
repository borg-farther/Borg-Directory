#!/bin/bash
# TASK-018: HTTP header parsing with case-sensitive key lookup

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-018_http_headers

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-018_http_headers/http_parser.py << 'EOF'
"""HTTP header parsing with a subtle case-sensitivity bug."""

from typing import Dict, List, Optional, Tuple


class HTTPRequest:
    """
    Represents an HTTP request with headers.
    
    Headers are stored as key-value pairs.
    """
    
    def __init__(self):
        self.method = "GET"
        self.path = "/"
        self.version = "HTTP/1.1"
        self.headers: Dict[str, str] = {}
    
    def set_header(self, name: str, value: str):
        """Set a header value."""
        # BUG: We store headers with the exact case provided,
        # but HTTP headers are case-insensitive!
        # RFC 7230 says header field names are case-insensitive.
        # But our implementation does case-sensitive lookups.
        self.headers[name] = value
    
    def get_header(self, name: str) -> Optional[str]:
        """
        Get a header value by name.
        
        Returns None if header is not found.
        """
        # BUG: Direct dictionary lookup is case-sensitive!
        # "Content-Type" != "content-type" != "CONTENT-TYPE"
        return self.headers.get(name)
    
    def has_header(self, name: str) -> bool:
        """Check if a header exists."""
        return name in self.headers
    
    def get_all_headers(self) -> List[Tuple[str, str]]:
        """Get all headers as list of (name, value) tuples."""
        return list(self.headers.items())
    
    @classmethod
    def parse(cls, raw_request: str) -> 'HTTPRequest':
        """
        Parse a raw HTTP request string.
        
        Format:
        METHOD PATH HTTP/VERSION\r\n
        Header-Name: Header-Value\r\n
        ...
        \r\n
        Body...
        """
        request = cls()
        lines = raw_request.split('\r\n')
        
        if not lines:
            return request
        
        # Parse request line
        request_line = lines[0]
        parts = request_line.split(' ')
        if len(parts) >= 3:
            request.method = parts[0]
            request.path = parts[1]
            request.version = parts[2]
        
        # Parse headers
        for line in lines[1:]:
            if not line:
                break
            
            if ':' in line:
                name, value = line.split(':', 1)
                name = name.strip()
                value = value.strip()
                request.set_header(name, value)
        
        return request


class HTTPServer:
    """
    Simple HTTP server that processes requests.
    """
    
    def __init__(self):
        self.requests_received = []
    
    def process_request(self, raw_request: str) -> Dict:
        """
        Process an HTTP request and return response info.
        """
        request = HTTPRequest.parse(raw_request)
        self.requests_received.append(request)
        
        # Build response
        response = {
            'status': 200,
            'reason': 'OK',
            'headers': {},
            'body': ''
        }
        
        # Check for required headers
        content_type = request.get_header('Content-Type')
        if content_type:
            response['headers']['Content-Type'] = content_type
        
        content_length = request.get_header('Content-Length')
        if content_length:
            response['headers']['Content-Length'] = content_length
        
        return response
    
    def check_header(self, request: HTTPRequest, header_name: str) -> bool:
        """
        Check if a specific header exists in the request.
        
        Uses case-insensitive comparison as per HTTP spec.
        """
        # BUG: This is supposed to be case-insensitive per HTTP spec,
        # but the underlying get_header() does case-sensitive lookup!
        value = request.get_header(header_name)
        return value is not None


def main():
    """Demonstrate the case-sensitivity bug."""
    
    server = HTTPServer()
    
    # Raw HTTP request with mixed-case headers
    raw_request = """GET /test HTTP/1.1\r
Host: localhost\r
content-type: application/json\r
Content-Length: 123\r
X-Custom-Header: value\r
\r
"""
    
    print("=== HTTP Request ===")
    print(raw_request)
    
    # Parse and process
    request = HTTPRequest.parse(raw_request)
    
    print("=== Parsed Headers ===")
    for name, value in request.get_all_headers():
        print(f"  {name}: {value}")
    
    print("\n=== Header Lookups ===")
    print(f"get_header('Content-Type'): {request.get_header('Content-Type')}")
    print(f"get_header('content-type'): {request.get_header('content-type')}")
    print(f"get_header('CONTENT-TYPE'): {request.get_header('CONTENT-TYPE')}")
    
    print("\n=== The Bug ===")
    print("HTTP headers should be case-insensitive per RFC 7230.")
    print("But our implementation does case-SENSITIVE lookups!")
    print("'Content-Type' != 'content-type' in our lookup.")


if __name__ == "__main__":
    main()
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-018_http_headers/test_http_parser.py << 'EOF'
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
EOF
