"""Durable, privacy-safe, LOCAL record of when Borg fired and whether it matched
— the value-legibility surface (PART 10 gate #10).

A blind runtime-integrator cold eval found that after several successful rescues
nothing on disk proved Borg ever helped (`collective summary` stayed at zero and
no receipt was persisted). This module fixes that: every interactive rescue
appends a small receipt so `borg status` can show an honest running tally —
"Borg matched N of M failures you hit, here's the provenance" — across restarts.

Honesty rules (matching ``borg.core.rescue._value_receipt``):
  * Receipts contain NO raw error text — only the class label (``problem_class``),
    the confidence tier, and the provenance (seed corpus / your own traces /
    the federated collective). Nothing identifying, nothing shareable.
  * No time/token savings are ever claimed here. Savings require a recorded
    first-10 outcome row; seed-corpus matches are cold-start knowledge, not
    verified collective proof. The summary says so explicitly.
  * Receipts are local-only and never leave the device.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from borg.core.dirs import get_borg_home

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rescue_receipts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    status        TEXT NOT NULL,
    problem_class TEXT NOT NULL DEFAULT 'unknown',
    confidence    TEXT NOT NULL DEFAULT 'unknown',
    provenance    TEXT NOT NULL DEFAULT 'unknown',
    matched       INTEGER NOT NULL DEFAULT 0,
    source        TEXT NOT NULL DEFAULT 'cli',
    session_id    TEXT NOT NULL DEFAULT ''
);
"""

_SAVINGS_NOTE = (
    "Counts only. Time/token savings are not claimed here — they require a recorded "
    "outcome. Seed-corpus matches are cold-start knowledge, not verified collective proof."
)


def _db_path(borg_home: Optional[Path | str] = None) -> Path:
    home = Path(borg_home) if borg_home is not None else get_borg_home()
    return home / "value_receipts.db"


def _connect(borg_home: Optional[Path | str] = None) -> sqlite3.Connection:
    path = _db_path(borg_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _provenance_of(result: Dict[str, Any]) -> str:
    """Map a rescue's evidence source to a human-legible provenance label."""
    evidence = result.get("evidence") or {}
    source = str(evidence.get("source") or "none")
    return {
        "seed_pack": "seed_corpus",
        "trace": "your_traces",
        "local_trace": "your_traces",
        "local_trace_db": "your_traces",
        "collective": "collective",
        "federated": "collective",
        "atom": "collective",
        "none": "none",
    }.get(source, source)


def record_rescue_receipt(
    result: Any,
    *,
    source: str = "cli",
    session_id: str = "",
    borg_home: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Append a privacy-safe receipt for one rescue.

    Accepts a ``RescueResult`` or a plain dict. Best-effort: it must never raise
    into the rescue path, so all errors are swallowed and an empty dict returned.
    """
    try:
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    except Exception:
        return {}
    status = str(data.get("status") or "unknown")
    row = {
        "created_at": _utc_now(),
        "status": status,
        "problem_class": str(data.get("problem_class") or "unknown"),
        "confidence": str(data.get("confidence") or "unknown"),
        "provenance": _provenance_of(data),
        "matched": 1 if status == "matched" else 0,
        "source": str(source or "cli"),
        "session_id": str(session_id or ""),
    }
    try:
        with _connect(borg_home) as conn:
            conn.execute(
                "INSERT INTO rescue_receipts "
                "(created_at, status, problem_class, confidence, provenance, matched, source, session_id) "
                "VALUES (:created_at, :status, :problem_class, :confidence, :provenance, :matched, :source, :session_id)",
                row,
            )
            conn.commit()
    except Exception:
        return {}
    return row


def value_summary(*, borg_home: Optional[Path | str] = None) -> Dict[str, Any]:
    """Aggregate the local rescue receipts into an honest value tally."""
    empty = {
        "rescues_fired": 0,
        "rescues_matched": 0,
        "no_confident_match": 0,
        "matched_by_confidence": {},
        "matched_by_provenance": {},
        "distinct_problem_classes": 0,
        "first_rescue_at": None,
        "last_rescue_at": None,
        "savings_note": _SAVINGS_NOTE,
    }
    # Read-only: never create the store just to display a tally (keeps
    # `borg status` from writing to a clean home).
    if not _db_path(borg_home).exists():
        return empty
    try:
        with _connect(borg_home) as conn:
            total = conn.execute("SELECT COUNT(*) FROM rescue_receipts").fetchone()[0] or 0
            matched = conn.execute("SELECT COUNT(*) FROM rescue_receipts WHERE matched = 1").fetchone()[0] or 0
            by_conf = {
                str(r["confidence"]): int(r["n"])
                for r in conn.execute(
                    "SELECT confidence, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY confidence"
                )
            }
            by_prov = {
                str(r["provenance"]): int(r["n"])
                for r in conn.execute(
                    "SELECT provenance, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY provenance"
                )
            }
            distinct = conn.execute(
                "SELECT COUNT(DISTINCT problem_class) FROM rescue_receipts "
                "WHERE matched = 1 AND problem_class != 'unknown'"
            ).fetchone()[0] or 0
            span = conn.execute("SELECT MIN(created_at) AS f, MAX(created_at) AS l FROM rescue_receipts").fetchone()
    except Exception:
        return empty
    return {
        "rescues_fired": int(total),
        "rescues_matched": int(matched),
        "no_confident_match": int(total) - int(matched),
        "matched_by_confidence": by_conf,
        "matched_by_provenance": by_prov,
        "distinct_problem_classes": int(distinct),
        "first_rescue_at": span["f"] if span else None,
        "last_rescue_at": span["l"] if span else None,
        "savings_note": _SAVINGS_NOTE,
    }


def recent_receipts(limit: int = 10, *, borg_home: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    if not _db_path(borg_home).exists():  # read-only: do not create storage
        return []
    try:
        with _connect(borg_home) as conn:
            rows = conn.execute(
                "SELECT created_at, status, problem_class, confidence, provenance, source "
                "FROM rescue_receipts ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
