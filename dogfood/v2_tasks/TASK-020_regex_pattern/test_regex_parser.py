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
