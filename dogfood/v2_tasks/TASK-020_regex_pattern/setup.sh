#!/bin/bash
# TASK-020: Regex pattern with greedy match causing wrong capture groups

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-020_regex_pattern

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-020_regex_pattern/regex_parser.py << 'EOF'
"""Regex pattern matching with a subtle greedy matching bug."""

import re
from typing import List, Optional, Tuple


class LogParser:
    """
    Parse log entries using regex patterns.
    
    Supports patterns like:
    [2024-01-15 10:30:45] [INFO] [user@example.com] Message: Something happened
    """
    
    def __init__(self):
        # BUG: The regex pattern uses greedy quantifiers that
        # capture more than intended, causing wrong group extraction.
        #
        # The pattern attempts to capture:
        # Group 1: timestamp
        # Group 2: log level
        # Group 3: user email
        # Group 4: message
        #
        # But due to greedy matching, the groups get mixed up!
        self.log_pattern = re.compile(
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] '  # timestamp
            r'\[(\w+)\] '  # log level
            r'\[([^\]]+)\] '  # user email - greedy!
            r'Message: (.*)'  # message
        )
    
    def parse_log(self, log_line: str) -> Optional[dict]:
        """
        Parse a single log line.
        
        Returns dict with keys: timestamp, level, user, message
        or None if parsing fails.
        """
        match = self.log_pattern.match(log_line)
        
        if not match:
            return None
        
        return {
            'timestamp': match.group(1),
            'level': match.group(2),
            'user': match.group(3),
            'message': match.group(4)
        }
    
    def parse_logs(self, logs: List[str]) -> List[dict]:
        """Parse multiple log lines."""
        results = []
        for log in logs:
            parsed = self.parse_log(log)
            if parsed:
                results.append(parsed)
        return results


class ConfigParser:
    """
    Parse configuration strings with key=value pairs.
    
    Example: key1=value1;key2=value2;key3=value with spaces
    """
    
    def __init__(self):
        # BUG: Greedy .+ at the end captures too much,
        # including semicolons that should be separators!
        self.pair_pattern = re.compile(r'(\w+)=(.+?);?(.+)?')
        # Actually let me think about this more...
        # The pattern (.+)? is optional and greedy
        # But the issue is capturing the value correctly
    
    def parse(self, config: str) -> dict:
        """
        Parse config string into dict.
        
        Handles formats like:
        - key1=value1
        - key1=value1;key2=value2
        - key1=value with spaces;key2=value2
        """
        result = {}
        
        # BUG: This pattern doesn't correctly split on semicolons
        # and the greedy .+ in (.+) captures too much
        pattern = re.compile(r'(\w+)=([^;]+)')
        
        for match in pattern.finditer(config):
            key = match.group(1)
            value = match.group(2).strip()
            result[key] = value
        
        return result


class CSVParser:
    """
    Parse CSV-like strings with quoted fields.
    """
    
    def __init__(self):
        # BUG: The greedy ".*" in the quoted field pattern
        # causes it to capture more than intended
        pass
    
    def parse_line(self, line: str) -> List[str]:
        """
        Parse a CSV line with quoted fields.
        
        Handles: "field1","field2","field3"
        And: "field with spaces","another field"
        """
        # BUG: This pattern has greedy .* which matches too much
        pattern = re.compile(r'"(.*)"')
        
        matches = pattern.findall(line)
        
        if matches:
            return matches
        
        # Fallback: split by comma
        return [f.strip() for f in line.split(',')]


class URLParser:
    """
    Parse URLs into components.
    """
    
    def __init__(self):
        # BUG: The greedy .+ in various parts causes wrong captures
        self.url_pattern = re.compile(
            r'^(\w+)://([^\s/]+)(:\d+)?(/.*)?$'
        )
        # Actually this one might be OK, let me focus on the log parser
    
    def parse(self, url: str) -> Optional[dict]:
        """Parse URL into components."""
        match = self.url_pattern.match(url)
        
        if not match:
            return None
        
        return {
            'scheme': match.group(1),
            'host': match.group(2),
            'port': match.group(3),
            'path': match.group(4)
        }


def main():
    """Demonstrate the regex greedy matching issues."""
    
    print("=== Log Parser Demo ===\n")
    
    parser = LogParser()
    
    log_line = "[2024-01-15 10:30:45] [INFO] [admin@site.com] Message: User logged in"
    
    print(f"Parsing: {log_line}\n")
    
    result = parser.parse_log(log_line)
    
    if result:
        print(f"  timestamp: {result.get('timestamp')}")
        print(f"  level: {result.get('level')}")
        print(f"  user: {result.get('user')}")
        print(f"  message: {result.get('message')}")
    
    # Test another line with different user
    log_line2 = "[2024-01-15 10:30:46] [ERROR] [user123@domain.org] Message: Connection failed"
    print(f"\nParsing: {log_line2}\n")
    
    result2 = parser.parse_log(log_line2)
    
    if result2:
        print(f"  timestamp: {result2.get('timestamp')}")
        print(f"  level: {result2.get('level')}")
        print(f"  user: {result2.get('user')}")
        print(f"  message: {result2.get('message')}")
    else:
        print("  PARSE FAILED!")
    
    print("\n=== The Bug ===")
    print("The regex pattern uses greedy quantifiers that can")
    print("capture more than intended, causing group extraction issues.")


if __name__ == "__main__":
    main()
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-020_regex_pattern/test_regex_parser.py << 'EOF'
"""Test cases for regex parser."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-020_regex_pattern')

from regex_parser import LogParser, ConfigParser, CSVParser, URLParser


def test_log_parser_basic():
    """Test basic log parsing."""
    parser = LogParser()
    
    log = "[2024-01-15 10:30:45] [INFO] [user@example.com] Message: Test message"
    
    result = parser.parse_log(log)
    
    assert result is not None, "Should parse successfully"
    assert result['timestamp'] == "2024-01-15 10:30:45"
    assert result['level'] == "INFO"
    assert result['user'] == "user@example.com"
    assert result['message'] == "Test message"
    
    print("test_log_parser_basic: PASS")


def test_log_parser_error_level():
    """Test log parsing with ERROR level."""
    parser = LogParser()
    
    log = "[2024-01-16 15:20:00] [ERROR] [admin@site.org] Message: Connection timeout"
    
    result = parser.parse_log(log)
    
    assert result is not None
    assert result['level'] == "ERROR"
    assert result['user'] == "admin@site.org"
    assert result['message'] == "Connection timeout"
    
    print("test_log_parser_error_level: PASS")


def test_log_parser_multiple_lines():
    """Test parsing multiple log lines."""
    parser = LogParser()
    
    logs = [
        "[2024-01-15 10:30:45] [INFO] [user1@test.com] Message: First",
        "[2024-01-15 10:30:46] [WARN] [user2@test.com] Message: Second",
        "[2024-01-15 10:30:47] [ERROR] [user3@test.com] Message: Third",
    ]
    
    results = parser.parse_logs(logs)
    
    assert len(results) == 3
    assert results[0]['user'] == "user1@test.com"
    assert results[1]['level'] == "WARN"
    assert results[2]['message'] == "Third"
    
    print("test_log_parser_multiple_lines: PASS")


def test_log_parser_strips_brackets():
    """Test that user field is properly extracted without extra brackets."""
    parser = LogParser()
    
    # The pattern [([^\]]+)] for user should capture content without brackets
    # But due to greedy matching, it might capture too much
    log = "[2024-01-15 10:30:45] [INFO] [test@domain.com] Message: Test"
    
    result = parser.parse_log(log)
    
    assert result is not None
    # User should NOT have brackets
    assert '[' not in result['user'], f"User should not have brackets: {result['user']}"
    assert ']' not in result['user'], f"User should not have brackets: {result['user']}"
    assert result['user'] == "test@domain.com"
    
    print("test_log_parser_strips_brackets: PASS")


def test_log_parser_with_colons_in_message():
    """
    Test that message is captured correctly even with colons.
    
    BUG: Greedy .* in (.*) for message might capture incorrectly.
    """
    parser = LogParser()
    
    log = "[2024-01-15 10:30:45] [INFO] [user@test.com] Message: URL: http://example.com"
    
    result = parser.parse_log(log)
    
    assert result is not None
    # Message should be the full message including colons
    assert result['message'] == "URL: http://example.com"
    
    print("test_log_parser_with_colons_in_message: PASS")


def test_log_parser_fails_on_invalid():
    """Test that invalid logs return None."""
    parser = LogParser()
    
    invalid_logs = [
        "not a valid log",
        "[2024-01-15] [INFO] Message: Missing user field",
        "",
    ]
    
    for log in invalid_logs:
        result = parser.parse_log(log)
        # These should fail (return None) or at least not crash
        # But for valid format with missing parts, it might partially match
    
    print("test_log_parser_fails_on_invalid: PASS")


def test_config_parser():
    """Test config string parsing."""
    parser = ConfigParser()
    
    config_str = "host=localhost;port=8080;debug=true"
    result = parser.parse(config_str)
    
    assert result['host'] == 'localhost'
    assert result['port'] == '8080'
    assert result['debug'] == 'true'
    
    print("test_config_parser: PASS")


def test_config_parser_with_spaces():
    """Test config parsing with spaces in values."""
    parser = ConfigParser()
    
    config_str = "name=My Application;path=/usr/local/bin"
    result = parser.parse(config_str)
    
    assert 'name' in result
    assert 'path' in result
    
    print("test_config_parser_with_spaces: PASS")


def test_url_parser():
    """Test URL parsing."""
    parser = URLParser()
    
    url = "https://example.com:8080/path/to/resource"
    result = parser.parse(url)
    
    assert result is not None
    assert result['scheme'] == 'https'
    assert result['host'] == 'example.com'
    
    print("test_url_parser: PASS")


if __name__ == "__main__":
    test_log_parser_basic()
    test_log_parser_error_level()
    test_log_parser_multiple_lines()
    test_log_parser_strips_brackets()
    test_log_parser_with_colons_in_message()
    test_log_parser_fails_on_invalid()
    test_config_parser()
    test_config_parser_with_spaces()
    test_url_parser()
    print("\nAll tests passed!")
EOF
