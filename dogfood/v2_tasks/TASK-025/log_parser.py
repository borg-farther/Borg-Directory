"""Log parser that handles multiline log entries."""
import re
from typing import List, Dict, Any
from datetime import datetime


class LogParser:
    """Parser for multiline log entries."""
    
    # Log format: TIMESTAMP [LEVEL] Message
    # Multiline messages start with whitespace after the closing bracket
    LOG_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.*)$', re.MULTILINE)
    
    @staticmethod
    def parse_logs(log_text: str) -> List[Dict[str, Any]]:
        """Parse log text into structured entries."""
        entries = []
        
        # Find all log line starts
        matches = LogParser.LOG_PATTERN.finditer(log_text)
        
        for match in matches:
            timestamp_str = match.group(1)
            level = match.group(2)
            message = match.group(3)
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
            
            entry = {
                'timestamp': timestamp,
                'level': level,
                'message': message
            }
            entries.append(entry)
        
        # BUG: The above correctly identifies log line starts,
        # but doesn't handle continuation lines (lines that start with whitespace
        # after a log line). These should be appended to the previous entry's message.
        # 
        # The fix would be to track the end position of each match and
        # check if the text between matches starts with whitespace.
        # Currently, continuation lines are simply ignored.
        
        return entries
    
    @staticmethod
    def parse_logs_with_continuation(log_text: str) -> List[Dict[str, Any]]:
        """Parse log text, joining continuation lines to their parent entry."""
        entries = []
        
        matches = list(LogParser.LOG_PATTERN.finditer(log_text))
        
        for i, match in enumerate(matches):
            timestamp_str = match.group(1)
            level = match.group(2)
            message = match.group(3)
            
            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
            
            # Get the text between this match and the next
            if i < len(matches) - 1:
                next_start = matches[i + 1].start()
            else:
                next_start = len(log_text)
            
            # The text between current match end and next match start
            # might contain continuation lines (starting with whitespace)
            continuation_text = log_text[match.end():next_start]
            
            # If continuation exists and starts with whitespace, it's a continuation
            if continuation_text:
                # Check if it's a continuation by looking at lines after newlines
                lines = continuation_text.split('\n')
                for i, line in enumerate(lines):
                    if i == 0:
                        # First line - check if it's empty or starts with whitespace
                        if line.strip():
                            if not line.startswith((' ', '\t')):
                                # Not a continuation line, skip it
                                pass
                    elif line.strip():
                        # Subsequent lines - if starts with whitespace, it's continuation
                        if line.startswith((' ', '\t')):
                            message += '\n' + line
            
            entry = {
                'timestamp': timestamp,
                'level': level,
                'message': message
            }
            entries.append(entry)
        
        return entries


def test_single_line_logs():
    """Test parsing single-line log entries."""
    log_text = """
2024-01-15 10:30:00 [INFO] Application started
2024-01-15 10:30:01 [DEBUG] Loading configuration
2024-01-15 10:30:02 [ERROR] Failed to connect to database
    """.strip()
    
    entries = LogParser.parse_logs(log_text)
    
    assert len(entries) == 3, f"Expected 3 entries but got {len(entries)}"
    assert entries[0]['level'] == 'INFO'
    assert entries[1]['level'] == 'DEBUG'
    assert entries[2]['level'] == 'ERROR'
    
    print("test_single_line_logs PASSED")


def test_multiline_logs():
    """Test parsing multiline log entries."""
    log_text = """2024-01-15 10:30:00 [INFO] Application started
2024-01-15 10:30:01 [ERROR] Connection failed:
    could not connect to host
    retrying in 5 seconds
2024-01-15 10:30:02 [INFO] Retry successful"""
    
    entries = LogParser.parse_logs_with_continuation(log_text)
    
    assert len(entries) == 3, f"Expected 3 entries but got {len(entries)}"
    
    # First entry should be single line
    assert entries[0]['message'] == 'Application started'
    
    # Second entry should have continuation lines
    assert 'Connection failed' in entries[1]['message']
    assert 'could not connect to host' in entries[1]['message']
    assert 'retrying in 5 seconds' in entries[1]['message']
    
    # Third entry should be single line
    assert entries[2]['message'] == 'Retry successful'
    
    print("test_multiline_logs PASSED")


def test_stack_trace_parsing():
    """Test parsing logs with stack traces."""
    log_text = """2024-01-15 10:30:00 [ERROR] Exception occurred:
    Traceback (most recent call last):
      File "app.py", line 10, in main
        raise ValueError("test error")
    ValueError: test error
2024-01-15 10:30:01 [INFO] Continuing after error"""
    
    entries = LogParser.parse_logs_with_continuation(log_text)
    
    assert len(entries) == 2, f"Expected 2 entries but got {len(entries)}"
    
    # First entry should contain the full stack trace
    assert 'Traceback' in entries[0]['message']
    assert 'ValueError: test error' in entries[0]['message']
    
    print("test_stack_trace_parsing PASSED")


if __name__ == "__main__":
    test_single_line_logs()
    test_multiline_logs()
    test_stack_trace_parsing()
    print("\nAll tests passed!")
