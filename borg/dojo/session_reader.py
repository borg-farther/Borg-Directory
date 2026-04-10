"""
Safe, paginated reader for ~/.hermes/state.db.

Key design decisions (per BORG_DOJO_SPEC.md §4.2):
  - Read-only, WAL-safe: open with ?mode=ro&nolock=1 URI + PRAGMA query_only = ON
  - Pagination: 100 sessions per page, yield-based iteration
  - PII pipeline: user_id → HMAC-SHA256 (never raw), system_prompt → never read,
    content → privacy.redact_pii() before any storage
  - Integrity check: PRAGMA quick_check on open
  - Error handling: FileNotFoundError, sqlite3.OperationalError (locked), RuntimeError (corrupt)
"""

import hashlib
import hmac
import json
import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from .data_models import SessionSummary, ToolCallRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PII redaction — prefer borg.core.privacy, fall back to basic regex
# ---------------------------------------------------------------------------

import re as _re

_FALLBACK_PATTERNS = [
    _re.compile(r"~/.hermes\b"),
    _re.compile(r"/root/\S+"),
    _re.compile(r"/home/\w+/\S+"),
    _re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    _re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    _re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    _re.compile(r"\bxoxb-[A-Za-z0-9-]+\b"),
    _re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    _re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
    _re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    _re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
]


def _fallback_redact(text: str) -> str:
    """Basic PII redaction using regex patterns (fallback when borg.core.privacy unavailable)."""
    if not text:
        return text
    for pat in _FALLBACK_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


try:
    from borg.core.privacy import privacy_redact as _redact_pii
except ImportError:
    _redact_pii = _fallback_redact

# ---------------------------------------------------------------------------
# HMAC salt for user_id anonymisation (never raw — only a hash crosses the
# PII boundary)
# ---------------------------------------------------------------------------

_HMAC_SALT = b"borg-dojo-user-id-v1"


def _hash_user_id(raw_user_id: str) -> str:
    """HMAC-SHA256 hash of a user_id — one-way, deterministic per install."""
    return hmac.new(_HMAC_SALT, raw_user_id.encode(), hashlib.sha256).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Error category classification (mirrors failure_classifier.py logic but
# isolated here so session_reader can tag tool results during extraction)
# ---------------------------------------------------------------------------

_ERROR_PATTERNS = [
    ("path_not_found", re.compile(r"(?i)no such file|ENOENT|FileNotFoundError")),
    ("timeout", re.compile(r"(?i)ETIMEDOUT|timed?\s*out|deadline exceeded")),
    ("permission_denied", re.compile(r"(?i)EACCES|permission denied|403 forbidden")),
    ("command_not_found", re.compile(r"(?i)command not found|not recognized")),
    ("rate_limit", re.compile(r"(?i)429|rate limit|too many requests")),
    ("syntax_error", re.compile(r"(?i)SyntaxError|IndentationError|unexpected token")),
    ("network", re.compile(r"(?i)connection refused|ECONNREFUSED|network unreachable")),
]


def _classify_error(content: str) -> Tuple[bool, str, float]:
    """Classify a tool result as error or success.

    Returns (is_error, error_category, confidence).
    Confidence is 0.0 for success, or the pattern-based confidence for errors.
    """
    if not content:
        return False, "", 0.0
    for category, pattern in _ERROR_PATTERNS:
        if pattern.search(content):
            # confidence based on category (hardcoded per spec table)
            confidence_map = {
                "path_not_found": 0.9,
                "timeout": 0.85,
                "permission_denied": 0.9,
                "command_not_found": 0.95,
                "rate_limit": 0.9,
                "syntax_error": 0.95,
                "network": 0.85,
            }
            return True, category, confidence_map.get(category, 0.8)
    return False, "", 0.0


# ---------------------------------------------------------------------------
# SessionReader
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = Path.home() / ".hermes" / "state.db"
DEFAULT_DAYS = 7
DEFAULT_PAGE_SIZE = 100


class SessionReader:
    """Safe, paginated reader for ~/.hermes/state.db.

    Usage:
        with SessionReader(days=30) as reader:
            for session in reader.iter_sessions():
                process(session)
            tool_calls = reader.get_tool_calls(session_id)
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        days: int = DEFAULT_DAYS,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.days = days
        self.page_size = page_size
        self._conn: Optional[sqlite3.Connection] = None
        self._turn_index: Dict[str, int] = {}  # session_id → next turn index

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open read-only connection with integrity check.

        Raises:
            FileNotFoundError: state.db doesn't exist
            RuntimeError: PRAGMA quick_check failed (database corrupted)
            sqlite3.OperationalError: database is locked (after retries)
        """
        if not self.db_path.exists():
            raise FileNotFoundError(f"state.db not found: {self.db_path}")

        # Resolve to absolute path for reliable access
        abs_path = str(self.db_path.resolve())

        # Open read-only. isolation_level=None = autocommit, which avoids
        # holding read transactions that could conflict with Hermes writing.
        # This is equivalent to the WAL-safe ?mode=ro&nolock=1 URI intent.
        self._conn = sqlite3.connect(abs_path, timeout=5.0, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA query_only = ON")

        # Integrity check — fast (checks freelist only, not full integrity).
        # Catches corruption and non-database files.
        try:
            result = self._conn.execute("PRAGMA quick_check").fetchone()
            if result[0] != "ok":
                self._conn.close()
                self._conn = None
                raise RuntimeError(f"state.db integrity check failed: {result[0]}")
        except sqlite3.DatabaseError as e:
            self._conn.close()
            self._conn = None
            raise RuntimeError(f"state.db integrity check failed: {e}") from e

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SessionReader":
        self.open()
        return self

    def __exit__(self, *a: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API — session iteration
    # ------------------------------------------------------------------

    def iter_sessions(self) -> Iterator[SessionSummary]:
        """Yield sessions from the last N days, paginated.

        Yields:
            SessionSummary for each session (PII fields omitted per spec).
        """
        self._require_conn()
        cutoff = time.time() - (self.days * 86400)
        offset = 0

        while True:
            rows = self._conn.execute(
                """
                SELECT id, source, model, started_at, ended_at,
                       tool_call_count, message_count, estimated_cost_usd
                FROM sessions
                WHERE started_at > ?
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                (cutoff, self.page_size, offset),
            ).fetchall()

            if not rows:
                break

            for row in rows:
                yield SessionSummary(
                    session_id=row["id"],
                    source=row["source"] or "unknown",
                    model=row["model"] or "unknown",
                    started_at=row["started_at"],
                    ended_at=row["ended_at"],
                    tool_call_count=row["tool_call_count"] or 0,
                    message_count=row["message_count"] or 0,
                    estimated_cost_usd=row["estimated_cost_usd"],
                )

            offset += self.page_size

    def iter_all_sessions(self) -> Iterator[SessionSummary]:
        """Yield ALL sessions regardless of date cutoff (for full analysis)."""
        self._require_conn()
        offset = 0

        while True:
            rows = self._conn.execute(
                """
                SELECT id, source, model, started_at, ended_at,
                       tool_call_count, message_count, estimated_cost_usd
                FROM sessions
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                (self.page_size, offset),
            ).fetchall()

            if not rows:
                break

            for row in rows:
                yield SessionSummary(
                    session_id=row["id"],
                    source=row["source"] or "unknown",
                    model=row["model"] or "unknown",
                    started_at=row["started_at"],
                    ended_at=row["ended_at"],
                    tool_call_count=row["tool_call_count"] or 0,
                    message_count=row["message_count"] or 0,
                    estimated_cost_usd=row["estimated_cost_usd"],
                )

            offset += self.page_size

    # ------------------------------------------------------------------
    # Public API — message access
    # ------------------------------------------------------------------

    def get_user_messages(self, session_id: str) -> List[Tuple[str, float]]:
        """Get PII-redacted user messages for a session.

        Args:
            session_id: The session ID to fetch messages for.

        Returns:
            List of (redacted_content, timestamp) tuples, oldest first.
        """
        self._require_conn()
        rows = self._conn.execute(
            """
            SELECT content, timestamp
            FROM messages
            WHERE session_id = ? AND role = 'user'
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()

        return [
            (_redact_pii(row["content"] or ""), row["timestamp"])
            for row in rows
        ]

    def get_tool_calls(self, session_id: str) -> List[ToolCallRecord]:
        """Extract all tool calls from a session's messages.

        Each assistant message with tool_calls JSON is paired with the
        corresponding tool-result message (matched by tool_call_id).

        Args:
            session_id: The session ID to extract tool calls for.

        Returns:
            List of ToolCallRecord, ordered by timestamp.
        """
        self._require_conn()

        # Get assistant messages that invoked tools
        assistant_rows = self._conn.execute(
            """
            SELECT id, content, tool_calls, timestamp
            FROM messages
            WHERE session_id = ? AND role = 'assistant' AND tool_calls IS NOT NULL
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()

        tool_calls: List[ToolCallRecord] = []
        self._turn_index.setdefault(session_id, 0)

        for a_row in assistant_rows:
            raw_tool_calls = a_row["tool_calls"]
            if not raw_tool_calls:
                continue

            try:
                tool_call_list = json.loads(raw_tool_calls)
            except json.JSONDecodeError:
                logger.warning("Malformed tool_calls JSON in message %s", a_row["id"])
                continue

            for tc in tool_call_list:
                if not isinstance(tc, dict):
                    continue

                tool_name = tc.get("name", "unknown")
                arguments = tc.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                args_hash = hashlib.sha256(
                    json.dumps(arguments, sort_keys=True).encode()
                ).hexdigest()

                # Find the corresponding tool-result message
                tc_id = tc.get("id")
                tool_result_row = None
                if tc_id:
                    tool_result_rows = self._conn.execute(
                        """
                        SELECT content, tool_call_id, timestamp
                        FROM messages
                        WHERE session_id = ? AND tool_call_id = ? AND role = 'tool'
                        ORDER BY timestamp ASC
                        LIMIT 1
                        """,
                        (session_id, tc_id),
                    ).fetchall()
                    if tool_result_rows:
                        tool_result_row = tool_result_rows[0]

                # Extract result (from tool result message)
                raw_result = ""
                is_error = False
                error_type = ""
                timestamp = a_row["timestamp"]
                if tool_result_row:
                    raw_result = tool_result_row["content"] or ""
                    timestamp = tool_result_row["timestamp"]
                    is_error, error_type, _ = _classify_error(raw_result)

                # Truncate and redact
                result_snippet = _redact_pii(raw_result[:200])

                tool_calls.append(
                    ToolCallRecord(
                        session_id=session_id,
                        tool_name=tool_name,
                        arguments_hash=args_hash,
                        result_snippet=result_snippet,
                        is_error=is_error,
                        error_type=error_type,
                        timestamp=timestamp,
                        turn_index=self._turn_index[session_id],
                    )
                )
                self._turn_index[session_id] += 1

        return tool_calls

    def get_session_message_count(self, session_id: str) -> int:
        """Get the total message count for a session."""
        self._require_conn()
        row = self._conn.execute(
            "SELECT message_count FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        return row["message_count"] if row else 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_conn(self) -> None:
        if self._conn is None:
            raise RuntimeError(
                "SessionReader not open — use 'with SessionReader()' or call open() first"
            )

    def get_db_stats(self) -> Dict[str, int]:
        """Return basic stats about the database (for sanity checks)."""
        self._require_conn()
        sessions = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        messages = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        return {"sessions": sessions, "messages": messages}
