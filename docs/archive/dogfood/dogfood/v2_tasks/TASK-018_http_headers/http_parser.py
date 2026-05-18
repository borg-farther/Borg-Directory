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
        # Store with original case as provided.
        self.headers[name] = value
    
    def get_header(self, name: str) -> Optional[str]:
        """
        Get a header value by name.
        
        Returns None if header is not found.
        """
        # HTTP header names are case-insensitive per RFC 7230.
        name_lower = name.lower()
        for k, v in self.headers.items():
            if k.lower() == name_lower:
                return v
        return None
    
    def has_header(self, name: str) -> bool:
        """Check if a header exists."""
        # HTTP header names are case-insensitive per RFC 7230.
        name_lower = name.lower()
        return any(k.lower() == name_lower for k in self.headers)
    
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
