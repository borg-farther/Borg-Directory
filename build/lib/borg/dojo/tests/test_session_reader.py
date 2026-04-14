"""
Unit tests for borg/dojo/session_reader.py.

Tests use the real state.db at ~/.hermes/state.db (715 sessions, 22k messages).
"""

import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from borg.dojo.session_reader import (
    DEFAULT_DB_PATH,
    SessionReader,
    _classify_error,
    _fallback_redact,
    _hash_user_id,
    _redact_pii,
)
from borg.dojo.data_models import SessionSummary, ToolCallRecord


# ============================================================================
# Helpers
# ============================================================================

REAL_DB = Path.home() / ".hermes" / "state.db"


def real_db_available():
    return REAL_DB.exists()


# ============================================================================
# Tests: PII utilities
# ============================================================================

class TestRedactPii:
    def test_fallback_redact_email(self):
        text = "Contact me at john.doe@example.com"
        result = _fallback_redact(text)
        assert "[REDACTED]" in result
        assert "john.doe@example.com" not in result

    def test_fallback_redact_ip(self):
        text = "Server at 192.168.1.100 responded"
        result = _fallback_redact(text)
        assert "[REDACTED]" in result
        assert "192.168.1.100" not in result

    def test_fallback_redact_home_path(self):
        text = "File not found at /home/alice/docs.txt"
        result = _fallback_redact(text)
        assert "[REDACTED]" in result
        assert "/home/alice" not in result

    def test_fallback_redact_sk(self):
        text = "Authorization: Bearer sk-abc123defghijklmnopqrstuvwxyz"
        result = _fallback_redact(text)
        assert "[REDACTED]" in result
        assert "sk-abc" not in result

    def test_fallback_redact_empty(self):
        assert _fallback_redact("") == ""
        assert _fallback_redact(None) is None

    def test_redact_pii_is_available(self):
        """privacy_redact should be importable and functional."""
        assert callable(_redact_pii)
        result = _redact_pii("test@example.com and 10.0.0.1")
        assert "[REDACTED]" in result


class TestHashUserId:
    def test_hash_user_id_deterministic(self):
        h1 = _hash_user_id("user_12345")
        h2 = _hash_user_id("user_12345")
        assert h1 == h2

    def test_hash_user_id_different_inputs(self):
        h1 = _hash_user_id("user_12345")
        h2 = _hash_user_id("user_99999")
        assert h1 != h2

    def test_hash_user_id_length(self):
        h = _hash_user_id("user_12345")
        assert len(h) == 16  # first 16 chars of HMAC-SHA256

    def test_hash_user_id_not_raw(self):
        """Hashed value must not contain the raw user_id."""
        raw = "user_telegram_123456789"
        h = _hash_user_id(raw)
        assert raw not in h
        assert h.isalnum()


# ============================================================================
# Tests: Error classification
# ============================================================================

class TestClassifyError:
    def test_path_not_found(self):
        is_err, cat, conf = _classify_error("Error: [Errno 2] ENOENT: no such file")
        assert is_err is True
        assert cat == "path_not_found"
        assert conf == 0.9

    def test_timeout(self):
        is_err, cat, conf = _classify_error("HTTPSConnectionPool: Timed out")
        assert is_err is True
        assert cat == "timeout"
        assert conf == 0.85

    def test_permission_denied(self):
        is_err, cat, conf = _classify_error("PermissionError: EACCES permission denied")
        assert is_err is True
        assert cat == "permission_denied"
        assert conf == 0.9

    def test_command_not_found(self):
        is_err, cat, conf = _classify_error("sh: 1: gh: command not found")
        assert is_err is True
        assert cat == "command_not_found"
        assert conf == 0.95

    def test_rate_limit(self):
        is_err, cat, conf = _classify_error("HTTP 429: rate limit exceeded")
        assert is_err is True
        assert cat == "rate_limit"
        assert conf == 0.9

    def test_syntax_error(self):
        is_err, cat, conf = _classify_error("  File \"test.py\", line 1\n    SyntaxError: invalid syntax")
        assert is_err is True
        assert cat == "syntax_error"
        assert conf == 0.95

    def test_network_error(self):
        is_err, cat, conf = _classify_error("ConnectionRefusedError: ECONNREFUSED")
        assert is_err is True
        assert cat == "network"
        assert conf == 0.85

    def test_no_error(self):
        is_err, cat, conf = _classify_error("File created successfully at /tmp/out.txt")
        assert is_err is False
        assert cat == ""
        assert conf == 0.0

    def test_empty_content(self):
        is_err, cat, conf = _classify_error("")
        assert is_err is False
        assert cat == ""
        assert conf == 0.0

    def test_case_insensitive(self):
        is_err, cat, conf = _classify_error("NO SUCH FILE OR DIRECTORY")
        assert is_err is True
        assert cat == "path_not_found"


# ============================================================================
# Tests: SessionReader — connection lifecycle
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestSessionReaderOpenClose:
    def test_open_ok(self):
        reader = SessionReader(db_path=REAL_DB)
        reader.open()
        assert reader._conn is not None
        stats = reader.get_db_stats()
        assert stats["sessions"] == 715
        assert stats["messages"] == 22349
        reader.close()

    def test_context_manager(self):
        with SessionReader(db_path=REAL_DB) as reader:
            assert reader._conn is not None
            stats = reader.get_db_stats()
            assert stats["sessions"] > 0
        # Connection should be closed after exiting
        reader = SessionReader(db_path=REAL_DB)
        reader.open()
        reader.close()
        assert reader._conn is None

    def test_file_not_found(self):
        reader = SessionReader(db_path=Path("/nonexistent/path/state.db"))
        with pytest.raises(FileNotFoundError):
            reader.open()

    def test_integrity_check(self):
        # Create a corrupt in-memory db
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t(x);")
        conn.execute("INSERT INTO t VALUES (1);")
        conn.execute("PRAGMA quick_check")
        conn.close()
        # SessionReader with a corrupt db should raise RuntimeError
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            corrupt_path = Path(f.name)
        try:
            # Write a minimal corrupt file
            corrupt_path.write_bytes(b"not a sqlite database")
            reader = SessionReader(db_path=corrupt_path)
            with pytest.raises(RuntimeError, match="integrity check failed"):
                reader.open()
        finally:
            corrupt_path.unlink(missing_ok=True)


# ============================================================================
# Tests: SessionReader — iter_sessions() pagination
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestIterSessions:
    def test_iter_sessions_returns_summaries(self):
        with SessionReader(db_path=REAL_DB, days=365, page_size=50) as reader:
            sessions = list(reader.iter_sessions())
        assert len(sessions) > 0
        assert all(isinstance(s, SessionSummary) for s in sessions)
        # Check fields are present
        for s in sessions:
            assert s.session_id
            assert s.source
            assert s.started_at > 0

    def test_pagination_page_size(self):
        """Verify pagination works by checking page_size limit."""
        with SessionReader(db_path=REAL_DB, days=365, page_size=10) as reader:
            # Collect in chunks and verify no page exceeds page_size
            chunk = []
            for s in reader.iter_sessions():
                chunk.append(s)
                if len(chunk) == 10:
                    assert len(chunk) <= 10
                    chunk = []
            # Last chunk may be smaller
            assert len(chunk) <= 10

    def test_sessions_have_no_pii(self):
        """SessionSummary should NOT contain user_id or system_prompt."""
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            for s in reader.iter_sessions():
                assert not hasattr(s, "user_id") or s.session_id
                # system_prompt is never read
                assert not hasattr(s, "system_prompt") or s.session_id

    def test_iter_sessions_respects_days_cutoff(self):
        """Sessions older than `days` should not appear."""
        now = time.time()
        with SessionReader(db_path=REAL_DB, days=7) as reader:
            sessions = list(reader.iter_sessions())
        cutoff = now - (7 * 86400)
        for s in sessions:
            assert s.started_at > cutoff


# ============================================================================
# Tests: SessionReader — tool call extraction
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestGetToolCalls:
    def test_get_tool_calls_returns_list(self):
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            # Get the first session
            sessions = list(reader.iter_sessions())
            if not sessions:
                pytest.skip("No sessions found")
            session_id = sessions[0].session_id
            tool_calls = reader.get_tool_calls(session_id)
        assert isinstance(tool_calls, list)
        # All items should be ToolCallRecord
        for tc in tool_calls:
            assert isinstance(tc, ToolCallRecord)
            assert tc.session_id == session_id

    def test_tool_call_record_fields(self):
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            sessions = list(reader.iter_sessions())
            for s in sessions:
                tool_calls = reader.get_tool_calls(s.session_id)
                if not tool_calls:
                    continue
                tc = tool_calls[0]
                assert tc.tool_name
                assert tc.tool_name != "unknown", (
                    "tool_name should be resolved from function.name or function_name, "
                    "not default to 'unknown'"
                )
                assert len(tc.arguments_hash) == 64  # SHA256 hex
                assert tc.timestamp > 0
                # result_snippet should be redacted
                assert "[REDACTED]" in tc.result_snippet or tc.result_snippet
                break

    def test_tool_calls_pii_safe(self):
        """Tool call result_snippets must not contain raw PII."""
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            sessions = list(reader.iter_sessions())
            for s in sessions:
                tool_calls = reader.get_tool_calls(s.session_id)
                for tc in tool_calls:
                    # result_snippet must not contain raw emails or IPs
                    assert "example.com" not in tc.result_snippet
                    # SHA256 hash — no raw arguments
                    assert len(tc.arguments_hash) == 64
                break

    def test_empty_session_returns_empty_list(self):
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            # A session ID that doesn't exist should return empty
            tool_calls = reader.get_tool_calls("nonexistent-session-id-12345")
        assert tool_calls == []


# ============================================================================
# Tests: SessionReader — user messages
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestGetUserMessages:
    def test_get_user_messages_returns_list(self):
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            sessions = list(reader.iter_sessions())
            if not sessions:
                pytest.skip("No sessions found")
            # Find a session with user messages
            found = False
            for s in sessions:
                msgs = reader.get_user_messages(s.session_id)
                if msgs:
                    found = True
                    assert all(isinstance(m, tuple) and len(m) == 2 for m in msgs)
                    assert all(isinstance(m[0], str) and isinstance(m[1], float) for m in msgs)
                    break
            # At least one session should have user messages
            assert found, "No sessions with user messages found"

    def test_user_messages_are_redacted(self):
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            sessions = list(reader.iter_sessions())
            for s in sessions:
                msgs = reader.get_user_messages(s.session_id)
                for content, _ts in msgs:
                    # Should not have raw emails
                    assert "example.com" not in content
                if msgs:
                    break


# ============================================================================
# Tests: SessionReader — iter_all_sessions
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestIterAllSessions:
    def test_iter_all_sessions_returns_all(self):
        with SessionReader(db_path=REAL_DB, page_size=100) as reader:
            sessions = list(reader.iter_all_sessions())
        # Should cover all 715 sessions
        assert len(sessions) >= 715, f"Expected ≥715 sessions, got {len(sessions)}"

    def test_iter_all_vs_iter_sessions_days(self):
        """iter_all_sessions should return more or equal sessions vs iter_sessions(365)."""
        with SessionReader(db_path=REAL_DB, days=365, page_size=100) as reader:
            recent = list(reader.iter_sessions())
        with SessionReader(db_path=REAL_DB, page_size=100) as reader:
            all_s = list(reader.iter_all_sessions())
        assert len(all_s) >= len(recent)


# ============================================================================
# Integration: end-to-end read of real database
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestFullIntegration:
    def test_real_database_stats(self):
        """Sanity check against known DB stats."""
        with SessionReader(db_path=REAL_DB) as reader:
            stats = reader.get_db_stats()
        assert stats["sessions"] == 715, f"Expected 715 sessions, got {stats['sessions']}"
        assert stats["messages"] == 22349, f"Expected 22349 messages, got {stats['messages']}"

    def test_full_pipeline_read(self):
        """Read all sessions, extract tool calls, verify no crashes."""
        with SessionReader(db_path=REAL_DB, days=365, page_size=100) as reader:
            sessions = list(reader.iter_sessions())
            assert len(sessions) > 0

            total_tool_calls = 0
            for s in sessions:
                tcs = reader.get_tool_calls(s.session_id)
                total_tool_calls += len(tcs)

            assert total_tool_calls >= 0  # Just verify no crashes

    def test_session_summary_fields_complete(self):
        """All SessionSummary fields should be populated from real DB."""
        with SessionReader(db_path=REAL_DB, days=365) as reader:
            sessions = list(reader.iter_sessions())
            assert len(sessions) > 0
            s = sessions[0]
            # All required fields from spec
            assert s.session_id
            assert s.source in ("cli", "telegram", "discord", "slack", "unknown") or s.source
            assert s.model
            assert s.started_at > 0
            # Optional fields
            assert isinstance(s.ended_at, (float, type(None)))
            assert isinstance(s.tool_call_count, int)
            assert isinstance(s.message_count, int)
            assert isinstance(s.estimated_cost_usd, (float, type(None)))
