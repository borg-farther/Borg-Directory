"""
Opt-in anonymous telemetry for borg pack usage tracking.

Records structural events (search, pull, apply_start, apply_complete, apply_fail, feedback)
to BORG_DIR/telemetry.jsonl. No PII, no task content, no error messages — just usage patterns.

Opt-in via BORG_TELEMETRY=1 environment variable.
"""

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from borg.core.dirs import get_borg_dir

logger = logging.getLogger(__name__)

#: Opt-in flag — set BORG_TELEMETRY=1 to enable
TELEMETRY_ENABLED = os.environ.get("BORG_TELEMETRY", "0") == "1"

#: Anonymous session salt — regenerated on module load if not set
_SESSION_SALT = secrets.token_hex(16)

#: Valid event types
VALID_EVENT_TYPES = frozenset([
    "search",
    "pull",
    "apply_start",
    "apply_complete",
    "apply_fail",
    "feedback",
])


def _get_telemetry_path() -> Path:
    """Return the telemetry JSONL file path under BORG_DIR."""
    return get_borg_dir() / "telemetry.jsonl"


def _hash_session(session_id: str) -> str:
    """Create an opaque anonymous hash from a session_id.

    Uses a module-level salt so the same session_id produces different hashes
    across environments (making cross-environment correlation harder).
    """
    raw = f"{_SESSION_SALT}:{session_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def track_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Write a telemetry event to BORG_DIR/telemetry.jsonl.

    Events are only written when TELEMETRY_ENABLED is True.
    Failures are always silent — telemetry never crashes the main flow.

    Args:
        event_type: One of 'search', 'pull', 'apply_start', 'apply_complete',
                    'apply_fail', 'feedback'.
        data: Optional dict with additional event fields.
              Supported keys:
                  - pack_id (str): pack identifier
                  - session_id (str): execution session (hashed before storage)
                  - success (bool): whether the operation succeeded
                  - query_length (int): for search events
                  - result_count (int): for search events

    Event format (one JSON object per line):
        {
            "timestamp": "2026-03-28T10:00:00.000Z",
            "event_type": "search",
            "pack_id": null,
            "session_hash": "a1b2c3d4e5f6",
            "success": true,
            "query_length": 12,
            "result_count": 3
        }
    """
    if not TELEMETRY_ENABLED:
        return

    if event_type not in VALID_EVENT_TYPES:
        logger.debug("telemetry: unknown event type %r", event_type)
        return

    data = data or {}

    # Build event record — structural data only, no PII
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "pack_id": data.get("pack_id"),
        "session_hash": _hash_session(data["session_id"]) if data.get("session_id") else None,
        "success": data.get("success", True),
    }

    # Add optional structural fields (no task content, no error messages)
    if "query_length" in data:
        event["query_length"] = data["query_length"]
    if "result_count" in data:
        event["result_count"] = data["result_count"]

    try:
        telemetry_path = _get_telemetry_path()
        telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Graceful failure — never crash the main flow
        logger.debug("telemetry: failed to write event", exc_info=True)
