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
            r'^(\w+)://([^\s/:]+)(:\d+)?(/.*)?$'
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
