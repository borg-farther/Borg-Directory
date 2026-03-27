"""
Guild Session Management (T1.7).

Session persistence: {BORG_DIR}/sessions/{session_id}.json
Execution logs:      {BORG_DIR}/executions/{session_id}.jsonl

All paths are configurable via constructor or environment variable
HERMES_HOME.  Defaults to ~/.hermes/guild/.

Session dict schema (keys required by this module):
    session_id, pack_name, task, phase_index, status, created_at,
    phases, execution_log_path

Phase dict schema (within phases list):
    index, name, description, checkpoint, anti_patterns, prompts, status
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths — can be overridden via HERMES_HOME env var
# ---------------------------------------------------------------------------

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
BORG_DIR = HERMES_HOME / "guild"
EXECUTIONS_DIR = BORG_DIR / "executions"

# Size limits (PRD §4.3)
MAX_PHASES = 20
MAX_PACK_SIZE_BYTES = 500 * 1024  # 500 KB
MAX_FIELD_SIZE_BYTES = 10 * 1024   # 10 KB

# ---------------------------------------------------------------------------
# In-memory session store (keyed by session_id)
# ---------------------------------------------------------------------------

_active_sessions: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Session file helpers
# ---------------------------------------------------------------------------

def session_file(session_id: str, *, agent_dir: Optional[Path] = None) -> Path:
    """Return the path to a session's JSON persistence file."""
    base = agent_dir if agent_dir is not None else BORG_DIR
    return base / "sessions" / f"{session_id}.json"


def _ensure_dirs(agent_dir: Optional[Path] = None) -> Path:
    base = agent_dir if agent_dir is not None else BORG_DIR
    sessions_dir = base / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    EXECUTIONS_DIR_if = base / "executions"
    EXECUTIONS_DIR_if.mkdir(parents=True, exist_ok=True)
    return base


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _session_to_serializable(session: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a flat, JSON-serializable dict from a session object."""
    log_path = session.get("execution_log_path") or session.get("log_path", "")
    return {
        "session_id": session["session_id"],
        "pack_id": session.get("pack_id", ""),
        "pack_version": session.get("pack_version", "unknown"),
        "pack_name": session.get("pack_name", ""),
        "task": session.get("task", ""),
        "problem_class": session.get("problem_class", ""),
        "phase_index": session.get("phase_index", 0),
        "status": session.get("status", "pending"),
        "created_at": session.get("created_at", ""),
        "execution_log_path": str(log_path),
        "phase_results": session.get("phase_results", []),
        "retries": session.get("retries", {}),
        "phase_status": {
            p["name"]: p.get("status", "pending")
            for p in session.get("phases", [])
            if isinstance(p, dict)
        },
    }


# ---------------------------------------------------------------------------
# Persistence operations
# ---------------------------------------------------------------------------

def save_session(session: Dict[str, Any], *, agent_dir: Optional[Path] = None) -> None:
    """Persist session metadata to disk as JSON."""
    try:
        base = _ensure_dirs(agent_dir)
        path = session_file(session["session_id"], agent_dir=base)
        path.write_text(
            json.dumps(_session_to_serializable(session), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("Failed to persist session %s: %s", session["session_id"], e)


def load_session(session_id: str, *, agent_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load a session from disk and register it in the active store.

    Returns the session dict if found, or None.
    """
    path = session_file(session_id, agent_dir=agent_dir)
    if not path.exists():
        return None

    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Failed to load session file %s: %s", session_id, e)
        return None

    # Rebuild full session from metadata
    base = agent_dir if agent_dir is not None else BORG_DIR
    log_path_str = meta.get("execution_log_path", "")
    log_path = Path(log_path_str) if log_path_str else Path(base) / "executions" / f"{session_id}.jsonl"

    # Rebuild events from JSONL log
    events: List[Dict[str, Any]] = []
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

    # Rebuild phase plan from stored phase_status
    phase_status = meta.get("phase_status", {})
    phases_raw = meta.get("phases", [])
    phase_plan: List[Dict[str, Any]] = []
    for i, phase in enumerate(phases_raw if isinstance(phases_raw, list) else []):
        if not isinstance(phase, dict):
            continue
        name = phase.get("name", f"phase_{i}")
        phase_plan.append({
            "index": i,
            "name": name,
            "description": phase.get("description", ""),
            "checkpoint": phase.get("checkpoint", ""),
            "anti_patterns": phase.get("anti_patterns", []),
            "prompts": phase.get("prompts", []),
            "status": phase_status.get(name, "pending"),
        })

    # If phases weren't serialized, derive from phase_status keys
    if not phase_plan:
        for name, status in phase_status.items():
            phase_plan.append({
                "index": len(phase_plan),
                "name": name,
                "description": "",
                "checkpoint": "",
                "anti_patterns": [],
                "prompts": [],
                "status": status,
            })

    session: Dict[str, Any] = {
        "session_id": meta["session_id"],
        "pack_id": meta.get("pack_id", ""),
        "pack_version": meta.get("pack_version", "unknown"),
        "pack_name": meta.get("pack_name", ""),
        "task": meta.get("task", ""),
        "problem_class": meta.get("problem_class", ""),
        "phases": phase_plan,
        "phase_index": meta.get("phase_index", 0),
        "status": meta.get("status", "pending"),
        "created_at": meta.get("created_at", ""),
        "log_path": log_path,
        "execution_log_path": log_path,
        "events": events,
        "phase_results": meta.get("phase_results", []),
        "retries": meta.get("retries", {}),
        "approved": meta.get("approved", False),
    }
    _active_sessions[session["session_id"]] = session
    return session


def delete_session(session_id: str, *, agent_dir: Optional[Path] = None) -> None:
    """Remove a session's persistence file and in-memory entry (session is done)."""
    # Remove from in-memory store
    _active_sessions.pop(session_id, None)
    # Remove from disk
    try:
        path = session_file(session_id, agent_dir=agent_dir)
        if path.exists():
            path.unlink()
    except OSError as e:
        logger.warning("Failed to delete session file %s: %s", session_id, e)


def clear_test_sessions() -> None:
    """Remove all sessions from the in-memory store. For test use only."""
    _active_sessions.clear()


# ---------------------------------------------------------------------------
# Execution log (JSONL)
# ---------------------------------------------------------------------------

def log_event(session_id: str, event: Dict[str, Any], *, agent_dir: Optional[Path] = None) -> None:
    """Append an event to the session's JSONL execution log.

    Adds a ``ts`` timestamp (UTC ISO format) to the event before writing.
    """
    event = dict(event)  # shallow copy so caller dict is not mutated
    event["ts"] = datetime.now(timezone.utc).isoformat()
    session = _active_sessions.get(session_id)
    if session:
        session["events"].append(event)
        log_path: Any = session.get("execution_log_path") or session.get("log_path")
    else:
        # Try to construct log path from agent_dir
        base = agent_dir if agent_dir is not None else BORG_DIR
        log_path = base / "executions" / f"{session_id}.jsonl"

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Failed to write event for session %s: %s", session_id, e)


def compute_log_hash(log_path: Path) -> str:
    """Compute SHA-256 hash of the execution log file.

    Returns ``sha256:<hex>`` on success, or ``""`` if the file does not exist
    or is empty.
    """
    if not log_path.exists():
        return ""
    if log_path.stat().st_size == 0:
        return ""
    h = hashlib.sha256()
    h.update(log_path.read_bytes())
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# YAML / pack size-limit checks
# ---------------------------------------------------------------------------

def check_pack_size_limits(pack: Dict[str, Any], pack_file: Path) -> List[str]:
    """Validate pack against size limits.

    Checks:
    - Total pack file size ≤ MAX_PACK_SIZE_BYTES (500 KB)
    - Phase count ≤ MAX_PHASES (20)
    - No individual string field value exceeds MAX_FIELD_SIZE_BYTES (10 KB)

    Returns a list of human-readable violation messages; empty list means pass.
    """
    violations: List[str] = []

    # Total file size
    try:
        file_size = pack_file.stat().st_size
        if file_size > MAX_PACK_SIZE_BYTES:
            violations.append(
                f"Pack file exceeds 500KB limit: {file_size} bytes"
            )
    except OSError:
        pass

    # Phase count
    phases = pack.get("phases", [])
    if len(phases) > MAX_PHASES:
        violations.append(
            f"Pack has {len(phases)} phases, exceeds limit of {MAX_PHASES}"
        )

    # Per-field size check (recursive walk)
    def _check_fields(obj: Any, path: str = "") -> None:
        if isinstance(obj, str):
            encoded = obj.encode("utf-8")
            if len(encoded) > MAX_FIELD_SIZE_BYTES:
                violations.append(
                    f"Field '{path}' exceeds 10KB limit: {len(encoded)} bytes"
                )
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check_fields(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_fields(item, f"{path}[{i}]")

    _check_fields(pack)
    return violations


# ---------------------------------------------------------------------------
# Active-session access (for use by other core modules)
# ---------------------------------------------------------------------------

def get_active_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Return the in-memory session object, or None."""
    return _active_sessions.get(session_id)


def register_session(session: Dict[str, Any]) -> None:
    """Register a session in the in-memory store."""
    _active_sessions[session["session_id"]] = session
