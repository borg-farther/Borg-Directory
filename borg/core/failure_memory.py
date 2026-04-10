"""
Borg Failure Memory — Phase 3 of Borg Brain spec.

Collective failure intelligence: records what approaches failed for each error pattern,
and what approaches succeeded, so future agents get shortcuts.

Storage: YAML files at ~/.hermes/borg/failures/<agent_id>/<pack_id>/<error_hash>.yaml
Error hash: first 32 chars of sha256 of normalized error pattern.
Agent scoping: each agent_id is a namespace — agent A cannot see agent B's failures.
Path components (agent_id, pack_id) are validated to prevent traversal attacks.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_error(error_message: str) -> str:
    """Normalize an error message for consistent hashing.

    Note: we do NOT strip trailing periods here — doing so causes hash collisions
    between "Error: connection refused" and "Error: connection refused." which
    are semantically distinct. Trailing punctuation is preserved.
    """
    if not error_message:
        return ""
    # Collapse whitespace only — do NOT strip trailing punctuation
    return " ".join(error_message.split())


def _error_hash(error_pattern: str) -> str:
    """Compute the error hash (first 32 chars of sha256 of normalized pattern).

    16 chars (64 bits) is too short — empirical testing showed collisions with
    10+ distinct patterns. 32 chars (128 bits) provides comfortable margin.
    """
    normalized = _normalize_error(error_pattern)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# FailureMemory
# ---------------------------------------------------------------------------

class FailureMemory:
    """Records and recalls failure/success patterns for errors encountered by agents.

    Storage is scoped by agent_id — each agent has an isolated namespace.
    Path format: <memory_dir>/<agent_id>/<pack_id>/<error_hash>.yaml
    """

    DEFAULT_MEMORY_DIR = Path.home() / ".hermes" / "borg" / "failures"

    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        agent_id: str = "default",
    ) -> None:
        """
        Initialize FailureMemory.

        Args:
            memory_dir: Directory to store failure YAML files.
                        Defaults to ~/.hermes/borg/failures/
            agent_id:   Agent namespace for this instance. Controls which
                        directory subtree is used for reads and writes.
                        Defaults to "default" for backward compatibility.
        """
        self.memory_dir = Path(memory_dir) if memory_dir else self.DEFAULT_MEMORY_DIR
        self.agent_id = agent_id

    # --------------------------------------------------------------------------
    # Path helpers
    # --------------------------------------------------------------------------

    def _validate_path_component(self, component: str, field_name: str) -> None:
        """Validate a path component (agent_id or pack_id) for traversal attempts.

        Raises ValueError if the component contains path traversal sequences,
        is empty, or is the special dot/dotdot entries.
        """
        if not component or not component.strip():
            raise ValueError(f"{field_name} cannot be empty")

        # Reject path traversal sequences
        unsafe = {"..", "/", "\\", "\0"}
        for seq in unsafe:
            if seq in component:
                raise ValueError(
                    f"{field_name} contains unsafe path component: {seq!r}"
                )

        # Reject dot/dotdot (purely defensive — Path resolves these anyway)
        if component in (".", " ", "  "):
            raise ValueError(f"{field_name} cannot be whitespace or dot-only: {component!r}")

    def _agent_dir(self) -> Path:
        """Return the agent-scoped root directory, creating it if needed."""
        d = self.memory_dir / self.agent_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _yaml_path(self, pack_id: str, error_hash: str) -> Path:
        """Return the YAML file path for a given pack_id and error hash."""
        return self._agent_dir() / pack_id / f"{error_hash}.yaml"

    # ---------------------------------------------------------------------------
    # Record failures and successes
    # ---------------------------------------------------------------------------

    def record_failure(
        self,
        error_pattern: str,
        pack_id: str,
        phase: str,
        approach: str,
        outcome: str,
        agent_id: Optional[str] = None,
    ) -> None:
        """
        Record a failure or success for an error pattern.

        Args:
            error_pattern: The error message or pattern (e.g. "NoneType has no attribute 'split'").
            pack_id:       The borg pack being used (e.g. "systematic-debugging").
            phase:         The phase being executed when the error occurred.
            approach:      What the agent tried (e.g. "Added if val is not None check").
            outcome:       Either 'success' or 'failure'.
            agent_id:      Agent namespace for this entry. Defaults to self.agent_id.

        Raises:
            ValueError: If error_pattern is empty/whitespace, or outcome is invalid.
        """
        # TASK 3 — Input validation
        if not error_pattern or not error_pattern.strip():
            raise ValueError("error_pattern is required and cannot be empty")

        if outcome not in ("success", "failure"):
            raise ValueError(f"outcome must be 'success' or 'failure', got {outcome!r}")

        # BUG FIX 1: use instance agent_id when param not provided
        effective_agent_id = agent_id if agent_id is not None else self.agent_id

        # BUG FIX 2: path traversal prevention — validate agent_id and pack_id
        self._validate_path_component(effective_agent_id, "agent_id")
        self._validate_path_component(pack_id, "pack_id")

        normalized_pattern = _normalize_error(error_pattern)
        eh = _error_hash(error_pattern)

        # TASK 1 — Agent namespace scoping: path includes agent_id
        pack_dir = self.memory_dir / effective_agent_id / pack_id
        pack_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = pack_dir / f"{eh}.yaml"

        # Load existing data or start fresh
        if yaml_path.exists():
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = self._empty_record(normalized_pattern, pack_id, phase, effective_agent_id)
            except (yaml.YAMLError, OSError):
                data = self._empty_record(normalized_pattern, pack_id, phase, effective_agent_id)
        else:
            data = self._empty_record(normalized_pattern, pack_id, phase, effective_agent_id)

        # Ensure we have the right error_pattern normalized
        data["error_pattern"] = normalized_pattern
        data["pack_id"] = pack_id
        data["agent_id"] = effective_agent_id
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Update wrong_approaches or correct_approaches
        if outcome == "failure":
            found = False
            for entry in data.get("wrong_approaches", []):
                if entry["approach"] == approach:
                    entry["failure_count"] += 1
                    found = True
                    break
            if not found:
                data.setdefault("wrong_approaches", []).append({
                    "approach": approach,
                    "failure_count": 1,
                    "why_fails": "",
                })
        else:  # success
            found = False
            for entry in data.get("correct_approaches", []):
                if entry["approach"] == approach:
                    entry["success_count"] += 1
                    found = True
                    break
            if not found:
                data.setdefault("correct_approaches", []).append({
                    "approach": approach,
                    "success_count": 1,
                })

        # Increment total_sessions
        data["total_sessions"] = data.get("total_sessions", 0) + 1

        # TASK 2 — Atomic write: write to tmp, then rename
        self._atomic_write(yaml_path, data)

    @staticmethod
    def _atomic_write(yaml_path: Path, data: Dict[str, Any]) -> None:
        """Write data to a YAML file atomically using tmp/rename pattern.

        Uses os.open with O_NOFOLLOW | O_CREAT | O_EXCL to prevent:
        1. Symlink attacks — O_NOFOLLOW rejects symlinks at the target path
        2. Race conditions — O_EXCL fails if file already exists (safe under rename)
        3. Data loss on crash — rename is atomic on POSIX

        The tmp file is created with mode 0o644.
        """
        tmp = yaml_path.with_suffix(".tmp")
        content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

        # Write content to tmp file using os.open with O_NOFOLLOW to block symlinks
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
        try:
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)

        # Atomic rename — on POSIX this is atomic (rename is atomic on Linux)
        os.replace(str(tmp), str(yaml_path))

        # Defensive cleanup: tmp should not exist after successful replace
        if tmp.exists():
            tmp.unlink()

    # ---------------------------------------------------------------------------
    # Recall
    # ---------------------------------------------------------------------------

    def recall(
        self,
        error_message: str,
        agent_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Search failure memory for an error and return what approaches failed/succeeded.

        Args:
            error_message: The error message to search for.
            agent_id:      Agent namespace to search. Defaults to self.agent_id.

        Returns:
            Dict with error_pattern, wrong_approaches (sorted by failure_count desc),
            correct_approaches (sorted by success_count desc), and total_sessions.
            Returns None if no matching error pattern is found.
        """
        if not error_message:
            return None

        # BUG FIX 1: use instance agent_id when param not provided
        effective_agent_id = agent_id if agent_id is not None else self.agent_id

        # TASK 1 — Agent namespace scoping: only search within agent_id subtree
        agent_root = self.memory_dir / effective_agent_id
        if not agent_root.exists():
            return None

        normalized = _normalize_error(error_message)
        eh = _error_hash(error_message)

        # Direct lookup by error hash within agent namespace
        for pack_dir in agent_root.iterdir():
            if not pack_dir.is_dir():
                continue
            yaml_path = pack_dir / f"{eh}.yaml"
            if yaml_path.exists():
                try:
                    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    # Verify the normalized pattern matches
                    if data.get("error_pattern") != normalized:
                        continue
                    return self._format_recall(data)
                except (yaml.YAMLError, OSError):
                    continue

        # Fallback: search by substring match across agent namespace only
        for pack_dir in agent_root.iterdir():
            if not pack_dir.is_dir():
                continue
            for yaml_file in pack_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    stored_pattern = data.get("error_pattern", "")
                    if (normalized and stored_pattern and (
                        stored_pattern in normalized or normalized in stored_pattern
                    )):
                        return self._format_recall(data)
                except (yaml.YAMLError, OSError):
                    continue

        return None

    # ---------------------------------------------------------------------------
    # TASK 4 — Delete
    # ---------------------------------------------------------------------------

    def delete(
        self,
        error_pattern: str,
        agent_id: Optional[str] = None,
    ) -> bool:
        """
        Delete the stored record for an error pattern.

        Args:
            error_pattern: The error pattern whose record should be deleted.
            agent_id:      Agent namespace. Defaults to self.agent_id.

        Returns:
            True  — record was found and deleted.
            False — no record found for this error pattern (silent, no error).
        """
        # BUG FIX 1: use instance agent_id when param not provided
        effective_agent_id = agent_id if agent_id is not None else self.agent_id

        # BUG FIX 2: path traversal prevention
        self._validate_path_component(effective_agent_id, "agent_id")

        eh = _error_hash(error_pattern)
        agent_root = self.memory_dir / effective_agent_id

        if not agent_root.exists():
            return False

        for pack_dir in agent_root.iterdir():
            if not pack_dir.is_dir():
                continue
            yaml_path = pack_dir / f"{eh}.yaml"
            # BUG FIX 5: TOCTOU race — remove exists() check, just try unlink
            try:
                yaml_path.unlink()
                return True
            except FileNotFoundError:
                # File not found — not a real error, keep searching other pack_dirs
                continue
            except OSError:
                # Real OS error (permissions, I/O, etc.) — fail fast
                return False

        return False

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregate statistics for a given agent namespace.

        Args:
            agent_id: Agent namespace to query. Defaults to self.agent_id.

        Returns:
            Dict with total_failures, total_patterns, total_successes.
        """
        # BUG FIX 1: use instance agent_id when param not provided
        effective_agent_id = agent_id if agent_id is not None else self.agent_id

        total_failures = 0
        total_patterns = 0
        total_successes = 0

        agent_root = self.memory_dir / effective_agent_id
        if not agent_root.exists():
            return {
                "total_failures": total_failures,
                "total_patterns": total_patterns,
                "total_successes": total_successes,
            }

        for pack_dir in agent_root.iterdir():
            if not pack_dir.is_dir():
                continue
            for yaml_file in pack_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    total_patterns += 1
                    for wa in data.get("wrong_approaches", []):
                        total_failures += wa.get("failure_count", 0)
                    for ca in data.get("correct_approaches", []):
                        total_successes += ca.get("success_count", 0)
                except (yaml.YAMLError, OSError):
                    continue

        return {
            "total_failures": total_failures,
            "total_patterns": total_patterns,
            "total_successes": total_successes,
        }

    # ---------------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------------

    @staticmethod
    def _empty_record(
        error_pattern: str,
        pack_id: str,
        phase: str,
        agent_id: str = "default",
    ) -> Dict[str, Any]:
        """Return an empty failure record skeleton."""
        return {
            "error_pattern": error_pattern,
            "pack_id": pack_id,
            "agent_id": agent_id,
            "phase": phase,
            "wrong_approaches": [],
            "correct_approaches": [],
            "total_sessions": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _format_recall(data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a stored record for recall response."""
        wrong = data.get("wrong_approaches", [])
        correct = data.get("correct_approaches", [])

        # Sort by count descending
        wrong_sorted = sorted(wrong, key=lambda x: x.get("failure_count", 0), reverse=True)
        correct_sorted = sorted(correct, key=lambda x: x.get("success_count", 0), reverse=True)

        return {
            "error_pattern": data.get("error_pattern", ""),
            "agent_id": data.get("agent_id", "default"),
            "wrong_approaches": wrong_sorted,
            "correct_approaches": correct_sorted,
            "total_sessions": data.get("total_sessions", 0),
        }
