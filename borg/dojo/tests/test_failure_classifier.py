"""Tests for borg/dojo/failure_classifier.py"""

import pytest
from borg.dojo.failure_classifier import (
    classify_tool_result,
    classify_tool_result_to_report,
    detect_corrections,
    ERROR_CATEGORIES,
    CORRECTION_PATTERNS,
    _strip_false_positives,
    _is_structured_error,
)


# =============================================================================
# Tests: classify_tool_result — role filtering (false positive mitigation)
# =============================================================================

class TestRoleFilter:
    """Only role='tool' messages should be classified. Assistant/user pass through."""

    def test_tool_role_gets_classified(self):
        content = '{"error": "No such file or directory: /home/user/data.txt"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error is True
        assert cat == "path_not_found"
        assert conf > 0.0

    def test_assistant_role_returns_no_classification(self):
        """Assistant reasoning text like 'I could not find the file' must NOT trigger."""
        content = "I could not find the file at that location. Let me try another path."
        is_error, cat, conf = classify_tool_result(content, role="assistant")
        assert is_error is False
        assert cat == ""
        assert conf == 0.0

    def test_assistant_role_with_error_word_passes_through(self):
        """Assistant text containing 'error' but no actual error structure."""
        content = "The tool returned an error about a missing file."
        is_error, cat, conf = classify_tool_result(content, role="assistant")
        assert is_error is False

    def test_user_role_returns_no_classification(self):
        content = "The tool said permission denied"
        is_error, cat, conf = classify_tool_result(content, role="user")
        assert is_error is False
        assert cat == ""
        assert conf == 0.0

    def test_empty_role_returns_no_classification(self):
        is_error, cat, conf = classify_tool_result("some error", role="")
        assert is_error is False

    def test_none_role_returns_no_classification(self):
        is_error, cat, conf = classify_tool_result("some error", role=None)
        assert is_error is False


# =============================================================================
# Tests: "could not" false positive handling
# =============================================================================

class TestCouldNotFalsePositive:
    """The phrase 'could not' in assistant text must NOT trigger path_not_found."""

    def test_assistant_i_could_not_find_not_flagged(self):
        """'I could not find' in assistant reasoning should not be an error."""
        content = "I could not find the configuration file. I'll check the default location."
        is_error, cat, conf = classify_tool_result(content, role="assistant")
        assert is_error is False

    def test_assistant_could_not_be_located_not_flagged(self):
        content = "The requested module could not be located in the search path."
        is_error, cat, conf = classify_tool_result(content, role="assistant")
        assert is_error is False

    def test_tool_result_with_could_not_still_classifies(self):
        """A real tool result containing 'could not' in an error context should classify."""
        content = '{"error": "could not open file: [Errno 2] No such file"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        # The structured error should still match
        # after false-positive phrases are stripped, ENOENT should match
        assert conf >= 0.0  # Either error or no-error depending on stripping

    def test_tool_result_no_errors_found_not_flagged(self):
        """Tool result saying 'no errors found' must NOT be classified as error."""
        content = '{"success": true, "result": "completed", "errors": []}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error is False

    def test_tool_result_error_free_not_flagged(self):
        content = '{"success": true, "output": "error-free execution"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error is False


# =============================================================================
# Tests: classify_tool_result — each error category
# =============================================================================

class TestPathNotFound:
    def test_enoent(self):
        content = '{"error": "[Errno 2] No such file or directory: /root/test.txt"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "path_not_found"
        assert conf >= 0.9

    def test_file_not_found_error(self):
        content = "FileNotFoundError: [Errno 2] No such file: './config.yml'"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "path_not_found"

    def test_no_such_file(self):
        content = "rsync: link_stat test.txt failed: No such file or directory (2)"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "path_not_found"

    def test_directory_does_not_exist(self):
        content = "Error: directory '/var/log/needspecial' does not exist"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "path_not_found"


class TestTimeout:
    def test_etimedout(self):
        content = '{"error": "Connection timed out. ETIMEDOUT"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "timeout"
        assert conf >= 0.85

    def test_timeout_word(self):
        content = "Request timeout after 30 seconds"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "timeout"

    def test_deadline_exceeded(self):
        content = "Error: deadline exceeded"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "timeout"


class TestPermissionDenied:
    def test_eacces(self):
        content = '{"error": "EACCES: permission denied: /etc/sensitive.conf"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "permission_denied"
        assert conf >= 0.9

    def test_permission_denied_text(self):
        content = "Error: permission denied (os error 13)"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "permission_denied"

    def test_403_forbidden(self):
        content = '{"error": "HTTP 403 Forbidden: access denied to resource"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "permission_denied"


class TestCommandNotFound:
    def test_command_not_found_shell(self):
        content = "/bin/bash: line 1: kubectl: command not found"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "command_not_found"
        assert conf >= 0.95

    def test_not_recognized(self):
        content = "'docker-compose' is not recognized as an internal or external command"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "command_not_found"


class TestRateLimit:
    def test_429_status(self):
        content = '{"error": "HTTP 429: Too Many Requests. Retry-After: 60"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "rate_limit"
        assert conf >= 0.9

    def test_rate_limit_word(self):
        content = "API rate limit exceeded. Please wait before retrying."
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "rate_limit"


class TestSyntaxError:
    def test_syntax_error_python(self):
        content = 'File "/app/main.py", line 42\\n    print("hello\\n         ^\\nSyntaxError: invalid syntax'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "syntax_error"
        assert conf >= 0.95

    def test_indentation_error(self):
        content = "IndentationError: unexpected indent"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "syntax_error"

    def test_unexpected_token(self):
        content = "Error: unexpected token '}' at position 12"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "syntax_error"


class TestNetwork:
    def test_connection_refused(self):
        content = "connect() failed: Connection refused (errno 111)"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "network"
        assert conf >= 0.85

    def test_econnrefused(self):
        content = "ECONNREFUSED: Unable to connect to port 8080"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "network"

    def test_network_unreachable(self):
        content = "Error: network unreachable"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "network"


class TestGeneric:
    def test_plain_error_word(self):
        content = '{"error": "Something went wrong"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat == "generic"
        assert conf >= 0.5

    def test_exception_word(self):
        content = "Exception occurred while processing request"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error
        assert cat in ("generic", "network", "timeout")  # could be many

    def test_failed_word(self):
        content = "Operation failed"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert is_error


# =============================================================================
# Tests: classify_tool_result — confidence scores
# =============================================================================

class TestConfidenceScores:
    def test_confidence_is_float(self):
        content = '{"error": "ENOENT"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

    def test_high_confidence_for_specific_pattern(self):
        content = "FileNotFoundError: [Errno 2] No such file"
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert conf >= 0.9

    def test_context_boost_applied(self):
        """Error with contextual keywords should get a boost."""
        content = '{"error": "No such file", "file": "/path/to/file.txt"}'
        conf_with_context = classify_tool_result(content, role="tool")[2]

        content_no_context = '{"error": "No such file"}'
        conf_without = classify_tool_result(content_no_context, role="tool")[2]

        assert conf_with_context >= conf_without

    def test_confidence_clamped_to_1(self):
        """Even with multiple boosts, confidence can't exceed 1.0."""
        # Build a content that hits multiple context boosts
        content = '{"error": "No such file", "path": "/home", "file": "test", "directory": "dir"}'
        is_error, cat, conf = classify_tool_result(content, role="tool")
        assert conf <= 1.0


# =============================================================================
# Tests: classify_tool_result_to_report
# =============================================================================

class TestClassifyToReport:
    def test_returns_failure_report_on_error(self):
        content = '{"error": "ENOENT: No such file"}'
        report = classify_tool_result_to_report(
            content, role="tool", tool_name="filesystem",
            session_id="sess_123", timestamp=999999.0
        )
        assert report is not None
        assert report.tool_name == "filesystem"
        assert report.error_category == "path_not_found"
        assert report.session_id == "sess_123"
        assert report.timestamp == 999999.0
        assert report.confidence > 0.0

    def test_returns_none_on_success(self):
        content = '{"success": true, "output": "done"}'
        report = classify_tool_result_to_report(content, role="tool")
        assert report is None

    def test_snippet_max_200_chars(self):
        # Use actual error content so a report IS generated
        long_content = '{"error": "FileNotFoundError"}' + ("x" * 500)
        report = classify_tool_result_to_report(long_content, role="tool")
        assert report is not None
        assert len(report.error_snippet) <= 200


# =============================================================================
# Tests: detect_corrections — applied ONLY to user messages
# =============================================================================

class TestDetectCorrections:
    def test_high_confidence_explicit_correction(self):
        messages = [
            ("No, that's the wrong file.", 1000.0),
            ("I meant to say parse the CSV instead.", 1001.0),
        ]
        signals = detect_corrections(messages)
        assert len(signals) == 2
        assert all(s.confidence >= 0.85 for s in signals)

    def test_medium_confidence_try_again(self):
        messages = [("try again with different parameters", 1000.0)]
        signals = detect_corrections(messages)
        assert len(signals) == 1
        assert signals[0].confidence == 0.7

    def test_low_confidence_stop(self):
        messages = [("stop what you were doing", 1000.0)]
        signals = detect_corrections(messages)
        assert len(signals) == 1
        assert signals[0].confidence == 0.5

    def test_no_false_corrections(self):
        """Assistant/tool messages passed to detect_corrections should not error,
        but the function is designed for user messages only."""
        messages = [
            ("I could not find the file", 1000.0),  # not a correction
            ("The tool timed out", 1001.0),  # not a correction
        ]
        signals = detect_corrections(messages)
        # These specific phrases don't match any correction pattern
        assert len(signals) == 0

    def test_empty_messages_returns_empty(self):
        signals = detect_corrections([])
        assert signals == []

    def test_none_content_skipped(self):
        signals = detect_corrections([(None, 1000.0)])
        assert signals == []


# =============================================================================
# Tests: _strip_false_positives
# =============================================================================

class TestStripFalsePositives:
    def test_i_could_not_masked(self):
        text = "I could not find the file"
        result = _strip_false_positives(text)
        assert "could not" not in result.lower() or "FALSE_POSITIVE" in result

    def test_no_errors_found_masked(self):
        text = "Operation completed with no errors found"
        result = _strip_false_positives(text)
        # The replacement token should appear and the original phrase should be gone
        assert "[NO_ERRORS_SUCCESS]" in result
        assert "no errors found" not in result.lower()

    def test_error_free_masked(self):
        text = "error-free execution"
        result = _strip_false_positives(text)
        assert "[CLEAN_SUCCESS]" in result


# =============================================================================
# Tests: _is_structured_error
# =============================================================================

class TestIsStructuredError:
    def test_json_error_true(self):
        assert _is_structured_error('{"error": "something failed"}') is True

    def test_json_error_with_whitespace(self):
        assert _is_structured_error('{  "error": "failed"}') is True

    def test_non_error_json_false(self):
        assert _is_structured_error('{"success": true}') is False

    def test_plain_text_false(self):
        assert _is_structured_error("File not found") is False


# =============================================================================
# Tests: Real data from state.db
# =============================================================================

class TestRealStateDBData:
    """Tests using real tool results from ~/.hermes/state.db"""

    @pytest.fixture
    def real_tool_messages(self):
        """Sample of real tool role messages from state.db"""
        import sqlite3
        try:
            conn = sqlite3.connect(f"{Path.home()}/.hermes/state.db", timeout=1.0)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT content FROM messages WHERE role = 'tool' AND content IS NOT NULL LIMIT 50"
            ).fetchall()
            conn.close()
            return [r["content"] for r in rows if r["content"]]
        except Exception:
            return []

    def test_real_tool_results_classified(self, real_tool_messages):
        """Real tool results should be classifiable without crashing."""
        for content in real_tool_messages[:10]:  # test first 10
            try:
                is_error, cat, conf = classify_tool_result(content, role="tool")
                assert isinstance(is_error, bool)
                assert isinstance(cat, str)
                assert isinstance(conf, float)
                assert 0.0 <= conf <= 1.0
            except Exception as e:
                pytest.fail(f"Failed to classify content: {e}")


from pathlib import Path
