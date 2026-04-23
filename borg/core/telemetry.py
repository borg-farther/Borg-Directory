"""Borg telemetry helpers.

This module supports two telemetry streams:
1) Generic product telemetry via ``track_event`` (opt-in via BORG_TELEMETRY=1)
2) Recall/usage telemetry via ``log_recall`` / ``log_usage`` (legacy helpers)

All telemetry is best-effort and must never crash callers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

BORG_DIR = Path(os.getenv("BORG_DIR", os.path.expanduser("~/.borg")))
TELEMETRY_FILE = BORG_DIR / "telemetry.jsonl"
TELEMETRY_ENABLED = os.getenv("BORG_TELEMETRY", "0") == "1"

VALID_EVENT_TYPES = {
    "search",
    "pull",
    "apply_start",
    "apply_complete",
    "apply_fail",
    "feedback",
}

_session_recalls = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_session_id(session_id: str | None) -> str | None:
    if not session_id:
        return None
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:16]


def _strip_pii_query(t: str | None) -> str | None:
    if not t:
        return t
    t = re.sub(r"(/[\w./-]{3,})", "<path>", t)
    t = re.sub(r"([A-Z]:\\[\w\\.-]+)", "<path>", t)
    t = re.sub(r"(sk-[a-zA-Z0-9]{10,})", "<key>", t)
    t = re.sub(r"(ghp_[a-zA-Z0-9]{10,})", "<token>", t)
    t = re.sub(r"(Bearer\s+[a-zA-Z0-9._-]{10,})", "<bearer>", t)
    t = re.sub(r"\b(?!127\.0\.0\.1)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", "<ip>", t)
    t = re.sub(r"[\w.-]+@[\w.-]+\.\w+", "<email>", t)
    t = re.sub(r"(arn:aws:[a-zA-Z0-9:/_-]+)", "<arn>", t)
    t = re.sub(r"(postgresql|mysql|mongodb)://[^\s]+", "<dburl>", t)
    return t


def _append_jsonl(entry: Dict[str, Any]) -> None:
    TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def track_event(event_type: str, data: Dict[str, Any] | None = None) -> None:
    """Record a sanitized telemetry event.

    - no-op when telemetry is disabled
    - silently drops unknown event types
    - never raises
    """
    try:
        if not TELEMETRY_ENABLED:
            return

        if event_type not in VALID_EVENT_TYPES:
            return

        payload = data or {}

        entry: Dict[str, Any] = {
            "timestamp": _utc_now(),
            "event_type": event_type,
            "pack_id": payload.get("pack_id"),
            "session_hash": _hash_session_id(payload.get("session_id")),
            "success": payload.get("success"),
        }

        # Allowlist of non-PII analytic fields
        if "query_length" in payload:
            entry["query_length"] = payload.get("query_length")
        if "result_count" in payload:
            entry["result_count"] = payload.get("result_count")

        _append_jsonl(entry)
    except Exception:
        # Telemetry must never impact product behavior
        return


def log_recall(query, results, source="borg_observe"):
    safe_query = _strip_pii_query(query)
    entry = {
        "ts": _utc_now(),
        "event": "recall",
        "source": source,
        "query": (safe_query or "")[:100],
        "result_count": len(results),
        "result_ids": [r.get("trace_id", "") for r in results[:5] if isinstance(r, dict)],
    }
    _session_recalls.append(entry)
    try:
        _append_jsonl(entry)
    except Exception:
        return


def log_usage(trace_id, action="referenced"):
    entry = {"ts": _utc_now(), "event": "usage", "trace_id": trace_id, "action": action}
    try:
        _append_jsonl(entry)
    except Exception:
        return


def get_usage_rate(last_n=50):
    if not TELEMETRY_FILE.exists():
        return 0.0
    lines = TELEMETRY_FILE.read_text(encoding="utf-8").strip().split("\n")[-last_n:]
    recalled, used = set(), set()
    for l in lines:
        try:
            e = json.loads(l)
            if e.get("event") == "recall":
                recalled.update(e.get("result_ids", []))
            elif e.get("event") == "usage":
                used.add(e.get("trace_id", ""))
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError, KeyError):
            pass
    recalled.discard("")
    used.discard("")
    return len(used & recalled) / max(len(recalled), 1)
