"""Durable, privacy-safe, LOCAL record of when Borg fired and whether it matched
— the value-legibility surface (PART 10 gate #10) and the substrate for the
operator-side counterfactual measurement (scripts/counterfactual_replay.py).

A blind runtime-integrator cold eval found that after several successful rescues
nothing on disk proved Borg ever helped. This module fixes that and goes
further: each receipt carries enough *consented, redacted* context to later
replay the case against a frontier model and ask "would the agent have failed
here without Borg?" — the counterfactual that actually justifies the product.

Schema v2 adds, per receipt:
  * ``trigger`` / ``trigger_n`` — task_start | after_n_failures(n) | manual |
    unknown. The after_n_failures signal comes from the suggest/failure path
    (failure_count >= 2); it identifies the high-value "caught the agent after it
    was stuck" cases that `borg status` headlines.
  * ``coverage_class`` — a coarse bucket (python_dependency / django_db /
    permission / ...) so coverage breadth is measurable.
  * ``replay_context`` — a small JSON blob: POST-REDACTION error text, an
    env fingerprint (OS/python/borg version, no PII), the matched id, the fix
    Borg surfaced, and the outcome (unknown until a record_outcome closes it).

Honesty rules (unchanged): receipts never store raw secrets/PII (error text is
redacted before storage); no time/token savings are ever claimed; receipts are
local-only and never leave the device.
"""

from __future__ import annotations

import json
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from borg.core.dirs import get_borg_home

SCHEMA_VERSION = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rescue_receipts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT NOT NULL,
    status         TEXT NOT NULL,
    problem_class  TEXT NOT NULL DEFAULT 'unknown',
    confidence     TEXT NOT NULL DEFAULT 'unknown',
    provenance     TEXT NOT NULL DEFAULT 'unknown',
    matched        INTEGER NOT NULL DEFAULT 0,
    source         TEXT NOT NULL DEFAULT 'cli',
    session_id     TEXT NOT NULL DEFAULT '',
    trigger        TEXT NOT NULL DEFAULT 'unknown',
    trigger_n      INTEGER NOT NULL DEFAULT 0,
    coverage_class TEXT NOT NULL DEFAULT 'unknown',
    replay_context TEXT NOT NULL DEFAULT '{}',
    client         TEXT NOT NULL DEFAULT 'unknown'
);
"""

# Columns added after the original 9. ADD COLUMN is a cheap migration in SQLite,
# so existing receipts are preserved with sensible defaults.
#   v1 -> v2: trigger / trigger_n / coverage_class / replay_context
#   v2 -> v3: client (the MCP client that fired the rescue — claude-code | cursor
#             | ... — so per-client firing visibility is measurable separately
#             from counterfactual_rate; see docs/PILOT_DECISION_PROTOCOL.md).
_ADDED_COLUMNS = {
    "trigger": "TEXT NOT NULL DEFAULT 'unknown'",
    "trigger_n": "INTEGER NOT NULL DEFAULT 0",
    "coverage_class": "TEXT NOT NULL DEFAULT 'unknown'",
    "replay_context": "TEXT NOT NULL DEFAULT '{}'",
    "client": "TEXT NOT NULL DEFAULT 'unknown'",
}

VALID_TRIGGERS = {"task_start", "after_n_failures", "manual", "unknown"}

_SAVINGS_NOTE = (
    "Counts only. Time/token savings are not claimed here — they require a recorded "
    "outcome, and net value requires the operator counterfactual replay. Seed-corpus "
    "matches are cold-start knowledge, not verified collective proof."
)

# problem_class -> coarse coverage bucket (breadth measurement).
_COVERAGE_BUCKETS = {
    "missing_dependency": "python_dependency",
    "import_cycle": "python_dependency",
    "circular_dependency": "python_dependency",
    "type_mismatch": "python_type",
    "null_pointer_chain": "python_type",
    "migration_state_desync": "django_db",
    "schema_drift": "django_db",
    "missing_foreign_key": "django_db",
    "configuration_error": "config",
    "permission_denied": "permission",
    "timeout_hang": "concurrency",
    "race_condition": "concurrency",
}


def _db_path(borg_home: Optional[Path | str] = None) -> Path:
    home = Path(borg_home) if borg_home is not None else get_borg_home()
    return home / "value_receipts.db"


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(rescue_receipts)")}
    for col, decl in _ADDED_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE rescue_receipts ADD COLUMN {col} {decl}")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _connect(borg_home: Optional[Path | str] = None) -> sqlite3.Connection:
    path = _db_path(borg_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    _migrate(conn)
    return conn


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_fingerprint() -> str:
    try:
        from borg import __version__ as _bv
    except Exception:
        _bv = "?"
    return f"{platform.system() or '?'}/py{platform.python_version()}/borg{_bv}"


def _redact(text: str) -> str:
    """Redact secrets/PII from free text before it is persisted.

    Fail-closed: if the redactor is unavailable the text is DROPPED, never
    stored raw — losing one replay context beats persisting a secret.
    """
    if not text:
        return ""
    try:
        from borg.core.privacy import privacy_scan_structured

        return privacy_scan_structured(str(text)).sanitized[:1200]
    except Exception:
        return "[redaction-unavailable: error text dropped]"


def _provenance_of(result: Dict[str, Any]) -> str:
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
        "pack_suggestion": "pack_suggestion",
        "none": "none",
    }.get(source, source)


def _coverage_class(problem_class: str, matched: bool) -> str:
    if not matched:
        return "uncovered"
    pc = (problem_class or "").lower()
    return _COVERAGE_BUCKETS.get(pc, pc or "unknown")


def _first_action(data: Dict[str, Any]) -> str:
    action = data.get("action")
    if isinstance(action, list) and action:
        return _redact(str(action[0]))
    return ""


def normalize_client(name: str) -> str:
    """Normalize an MCP client name to a stable slug for per-client tallies.

    "Claude Code" -> "claude-code", "Cursor" -> "cursor", "" -> "unknown".
    Kept liberal: an unrecognized client keeps its slug rather than being lost.
    """
    slug = "-".join((name or "").strip().lower().split())
    return slug or "unknown"


def _normalize_trigger(trigger: str, trigger_n: int) -> Tuple[str, int]:
    t = (trigger or "unknown").strip().lower()
    if t not in VALID_TRIGGERS:
        t = "unknown"
    n = int(trigger_n or 0)
    if n >= 2 and t in ("unknown", "after_n_failures"):
        t = "after_n_failures"
    if t == "after_n_failures" and n < 2:
        n = 2
    return t, (n if t == "after_n_failures" else 0)


def record_rescue_receipt(
    result: Any,
    *,
    source: str = "cli",
    session_id: str = "",
    trigger: str = "unknown",
    trigger_n: int = 0,
    error_text: str = "",
    outcome: str = "unknown",
    client: str = "unknown",
    borg_home: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Append a privacy-safe receipt for one rescue/suggestion (schema v3).

    Accepts a ``RescueResult`` or a plain dict. Best-effort: never raises into the
    rescue path. ``error_text`` is redacted before it is stored in replay_context.
    ``client`` is the MCP client that fired the rescue (claude-code | cursor | …),
    captured from the MCP initialize handshake, for per-client firing visibility.
    """
    try:
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    except Exception:
        return {}
    status = str(data.get("status") or "unknown")
    matched = status == "matched"
    problem_class = str(data.get("problem_class") or "unknown")
    trig, trig_n = _normalize_trigger(trigger, trigger_n)
    replay_context = {
        "error_redacted": _redact(error_text),
        "env_fingerprint": _env_fingerprint(),
        "matched_id": problem_class if matched else "",
        "fix_surfaced": _first_action(data),
        "outcome": str(outcome or "unknown"),
    }
    row = {
        "created_at": _utc_now(),
        "status": status,
        "problem_class": problem_class,
        "confidence": str(data.get("confidence") or "unknown"),
        "provenance": _provenance_of(data),
        "matched": 1 if matched else 0,
        "source": str(source or "cli"),
        "session_id": str(session_id or ""),
        "trigger": trig,
        "trigger_n": trig_n,
        "coverage_class": _coverage_class(problem_class, matched),
        "replay_context": json.dumps(replay_context, sort_keys=True),
        "client": normalize_client(client),
    }
    try:
        with _connect(borg_home) as conn:
            conn.execute(
                "INSERT INTO rescue_receipts "
                "(created_at, status, problem_class, confidence, provenance, matched, source, "
                " session_id, trigger, trigger_n, coverage_class, replay_context, client) "
                "VALUES (:created_at, :status, :problem_class, :confidence, :provenance, :matched, "
                ":source, :session_id, :trigger, :trigger_n, :coverage_class, :replay_context, :client)",
                row,
            )
            conn.commit()
    except Exception:
        return {}
    return row


def value_summary(*, borg_home: Optional[Path | str] = None) -> Dict[str, Any]:
    """Aggregate the local rescue receipts into an honest value tally (v2)."""
    empty = {
        "schema_version": SCHEMA_VERSION,
        "rescues_fired": 0,
        "rescues_matched": 0,
        "no_confident_match": 0,
        "caught_after_stuck": 0,
        # Hit-rate / miss-rate are the pilot's separable activity signal: a low
        # hit_rate (few matches per fire) is a recall problem, not a value
        # verdict — the day-15 reading must diagnose this BEFORE concluding
        # anything from activation/retention (docs/PILOT_DECISION_PROTOCOL.md §2a).
        "hit_rate": None,
        "miss_rate": None,
        "matched_by_confidence": {},
        "matched_by_provenance": {},
        "matched_by_coverage_class": {},
        "by_trigger": {},
        # Per-client firing visibility: fires and matches grouped by the MCP
        # client that produced them (claude-code | cursor | …). Lets the operator
        # see whether a client (e.g. Cursor) under-fires or under-surfaces,
        # separately from whether Borg's catches are valuable.
        "fires_by_client": {},
        "matched_by_client": {},
        "distinct_problem_classes": 0,
        "replayable_receipts": 0,
        "first_rescue_at": None,
        "last_rescue_at": None,
        "savings_note": _SAVINGS_NOTE,
    }
    if not _db_path(borg_home).exists():  # read-only: never create the store
        return empty
    try:
        with _connect(borg_home) as conn:
            total = conn.execute("SELECT COUNT(*) FROM rescue_receipts").fetchone()[0] or 0
            matched = conn.execute("SELECT COUNT(*) FROM rescue_receipts WHERE matched = 1").fetchone()[0] or 0
            caught = conn.execute(
                "SELECT COUNT(*) FROM rescue_receipts WHERE matched = 1 AND trigger = 'after_n_failures'"
            ).fetchone()[0] or 0
            replayable = conn.execute(
                "SELECT COUNT(*) FROM rescue_receipts WHERE matched = 1 "
                "AND replay_context IS NOT NULL AND replay_context != '{}'"
            ).fetchone()[0] or 0
            by_conf = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT confidence AS k, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY confidence")}
            by_prov = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT provenance AS k, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY provenance")}
            by_cov = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT coverage_class AS k, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY coverage_class")}
            by_trig = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT trigger AS k, COUNT(*) AS n FROM rescue_receipts GROUP BY trigger")}
            fires_by_client = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT client AS k, COUNT(*) AS n FROM rescue_receipts GROUP BY client")}
            matched_by_client = {str(r["k"]): int(r["n"]) for r in conn.execute(
                "SELECT client AS k, COUNT(*) AS n FROM rescue_receipts WHERE matched = 1 GROUP BY client")}
            distinct = conn.execute(
                "SELECT COUNT(DISTINCT problem_class) FROM rescue_receipts "
                "WHERE matched = 1 AND problem_class != 'unknown'").fetchone()[0] or 0
            span = conn.execute("SELECT MIN(created_at) AS f, MAX(created_at) AS l FROM rescue_receipts").fetchone()
    except Exception:
        return empty
    total_i, matched_i = int(total), int(matched)
    hit_rate = round(matched_i / total_i, 4) if total_i else None
    miss_rate = round((total_i - matched_i) / total_i, 4) if total_i else None
    return {
        "schema_version": SCHEMA_VERSION,
        "rescues_fired": total_i,
        "rescues_matched": matched_i,
        "no_confident_match": total_i - matched_i,
        "caught_after_stuck": int(caught),
        "hit_rate": hit_rate,
        "miss_rate": miss_rate,
        "matched_by_confidence": by_conf,
        "matched_by_provenance": by_prov,
        "matched_by_coverage_class": by_cov,
        "by_trigger": by_trig,
        "fires_by_client": fires_by_client,
        "matched_by_client": matched_by_client,
        "distinct_problem_classes": int(distinct),
        "replayable_receipts": int(replayable),
        "first_rescue_at": span["f"] if span else None,
        "last_rescue_at": span["l"] if span else None,
        "savings_note": _SAVINGS_NOTE,
    }


def replayable_receipts(
    limit: int = 1000, *, matched_only: bool = True, borg_home: Optional[Path | str] = None
) -> List[Dict[str, Any]]:
    """Return receipts with parsed replay_context, for the counterfactual replay tool."""
    if not _db_path(borg_home).exists():
        return []
    try:
        with _connect(borg_home) as conn:
            where = "WHERE matched = 1" if matched_only else ""
            rows = conn.execute(
                f"SELECT id, created_at, problem_class, confidence, provenance, trigger, trigger_n, "
                f"coverage_class, replay_context FROM rescue_receipts {where} ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100000)),),
            ).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        rec = dict(r)
        try:
            rec["replay_context"] = json.loads(rec.get("replay_context") or "{}")
        except Exception:
            rec["replay_context"] = {}
        out.append(rec)
    return out


def recent_receipts(limit: int = 10, *, borg_home: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    if not _db_path(borg_home).exists():  # read-only: do not create storage
        return []
    try:
        with _connect(borg_home) as conn:
            rows = conn.execute(
                "SELECT created_at, status, problem_class, confidence, provenance, source, trigger "
                "FROM rescue_receipts ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ------------------------------------------------------------- user data rights

EXPORT_SCHEMA = "borg-receipts-export/1"
VALID_OUTCOMES = {"worked", "did_not_work", "unknown"}


def export_receipts(
    *, matched_only: bool = False, limit: int = 100000, borg_home: Optional[Path | str] = None
) -> Dict[str, Any]:
    """Build the user-run, consent-time export of redacted receipts.

    The output shape is exactly what scripts/counterfactual_replay.py consumes
    via --receipts-file ({"receipts": [...]}). Receipts were redacted at write
    time; export adds nothing and removes nothing — what the user sees here is
    byte-for-byte what the operator receives.
    """
    return {
        "schema": EXPORT_SCHEMA,
        "exported_at": _utc_now(),
        "note": (
            "Redacted local rescue receipts, exported by the user for consented "
            "offline counterfactual replay (docs/PILOT_CONSENT_FORM.md). Contains "
            "no raw error text, secrets, code, or PII — only post-redaction text "
            "and class labels. Deletable on request."
        ),
        "receipts": replayable_receipts(limit, matched_only=matched_only, borg_home=borg_home),
    }


def delete_receipts(
    *, ids: Optional[List[int]] = None, delete_all: bool = False, borg_home: Optional[Path | str] = None
) -> int:
    """Delete receipts by id or all of them. Returns the number deleted."""
    if not delete_all and not ids:
        return 0
    if not _db_path(borg_home).exists():
        return 0
    try:
        with _connect(borg_home) as conn:
            if delete_all:
                cursor = conn.execute("DELETE FROM rescue_receipts")
            else:
                marks = ",".join("?" for _ in ids)
                cursor = conn.execute(
                    f"DELETE FROM rescue_receipts WHERE id IN ({marks})",
                    [int(i) for i in ids],
                )
            conn.commit()
            return int(cursor.rowcount or 0)
    except Exception:
        return 0


def record_receipt_outcome(
    receipt_id: int, outcome: str, *, borg_home: Optional[Path | str] = None
) -> bool:
    """Set a receipt's replay_context.outcome (worked / did_not_work / unknown).

    This is the CLI/Python counterpart of the MCP outcome-recording path: it
    closes the loop on a rescue so the counterfactual replay can distinguish
    fixes that actually worked from ones merely surfaced.
    """
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(VALID_OUTCOMES)}, got {outcome!r}")
    if not _db_path(borg_home).exists():
        return False
    try:
        with _connect(borg_home) as conn:
            row = conn.execute(
                "SELECT replay_context FROM rescue_receipts WHERE id = ?", (int(receipt_id),)
            ).fetchone()
            if row is None:
                return False
            try:
                context = json.loads(row["replay_context"] or "{}")
            except json.JSONDecodeError:
                context = {}
            context["outcome"] = outcome
            conn.execute(
                "UPDATE rescue_receipts SET replay_context = ? WHERE id = ?",
                (json.dumps(context, sort_keys=True), int(receipt_id)),
            )
            conn.commit()
            return True
    except Exception:
        return False


def record_latest_receipt_outcome(
    outcome: str, *, borg_home: Optional[Path | str] = None
) -> Optional[int]:
    """Set the outcome on the most recent matched receipt still 'unknown'.

    Best-effort bridge for agent flows (MCP record-outcome) where no receipt id
    is in hand: the rescue that just happened is the latest unknown one.
    Returns the receipt id updated, or None.
    """
    if outcome not in VALID_OUTCOMES:
        return None
    if not _db_path(borg_home).exists():
        return None
    try:
        with _connect(borg_home) as conn:
            rows = conn.execute(
                "SELECT id, replay_context FROM rescue_receipts "
                "WHERE matched = 1 ORDER BY id DESC LIMIT 20"
            ).fetchall()
    except Exception:
        return None
    for row in rows:
        try:
            context = json.loads(row["replay_context"] or "{}")
        except json.JSONDecodeError:
            continue
        if context.get("outcome", "unknown") == "unknown":
            return int(row["id"]) if record_receipt_outcome(row["id"], outcome, borg_home=borg_home) else None
    return None
