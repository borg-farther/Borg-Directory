"""
Borg Failure Memory — Phase 3 of Borg Brain spec.

Collective failure intelligence: records what approaches failed for each error pattern,
and what approaches succeeded, so future agents get shortcuts.

Storage: YAML files at ~/.hermes/borg/failures/<pack_id>/<error_hash>.yaml
Error hash: first 16 chars of sha256 of normalized error pattern.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_error(error_message: str) -> str:
    """Normalize an error message for consistent hashing."""
    if not error_message:
        return ""
    # Collapse whitespace, strip trailing periods
    normalized = " ".join(error_message.split())
    if normalized.endswith("."):
        normalized = normalized[:-1]
    return normalized


def _error_hash(error_pattern: str) -> str:
    """Compute the error hash (first 16 chars of sha256 of normalized pattern)."""
    normalized = _normalize_error(error_pattern)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# FailureMemory
# ---------------------------------------------------------------------------

class FailureMemory:
    """Records and recalls failure/success patterns for errors encountered by agents."""

    DEFAULT_MEMORY_DIR = Path.home() / ".hermes" / "borg" / "failures"

    def __init__(self, memory_dir: Optional[Path] = None) -> None:
        """
        Initialize FailureMemory.

        Args:
            memory_dir: Directory to store failure YAML files.
                        Defaults to ~/.hermes/borg/failures/
        """
        self.memory_dir = Path(memory_dir) if memory_dir else self.DEFAULT_MEMORY_DIR

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
    ) -> None:
        """
        Record a failure or success for an error pattern.

        Args:
            error_pattern: The error message or pattern (e.g. "NoneType has no attribute 'split'").
            pack_id: The borg pack being used (e.g. "systematic-debugging").
            phase: The phase being executed when the error occurred (e.g. "investigate_root_cause").
            approach: What the agent tried (e.g. "Added if val is not None check in the method").
            outcome: Either 'success' or 'failure'.
        """
        if outcome not in ("success", "failure"):
            raise ValueError(f"outcome must be 'success' or 'failure', got {outcome!r}")

        normalized_pattern = _normalize_error(error_pattern)
        eh = _error_hash(error_pattern)

        # Ensure directory exists
        pack_dir = self.memory_dir / pack_id
        pack_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = pack_dir / f"{eh}.yaml"

        # Load existing data or start fresh
        if yaml_path.exists():
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = self._empty_record(normalized_pattern, pack_id, phase)
            except (yaml.YAMLError, OSError):
                data = self._empty_record(normalized_pattern, pack_id, phase)
        else:
            data = self._empty_record(normalized_pattern, pack_id, phase)

        # Ensure we have the right error_pattern normalized
        data["error_pattern"] = normalized_pattern
        data["pack_id"] = pack_id
        data["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Update wrong_approaches or correct_approaches
        if outcome == "failure":
            # Find or create entry in wrong_approaches
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
                    "why_fails": "",  # We don't capture why_fails in this simplified version
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

        # Write back
        yaml_path.write_text(
            yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    # ---------------------------------------------------------------------------
    # Recall
    # ---------------------------------------------------------------------------

    def recall(self, error_message: str) -> Optional[Dict[str, Any]]:
        """
        Search failure memory for an error and return what approaches failed/succeeded.

        Args:
            error_message: The error message to search for.

        Returns:
            Dict with error_pattern, wrong_approaches (sorted by failure_count desc),
            correct_approaches (sorted by success_count desc), and total_sessions.
            Returns None if no matching error pattern is found.
        """
        if not error_message:
            return None

        # Search all pack dirs for matching error patterns
        if not self.memory_dir.exists():
            return None

        normalized = _normalize_error(error_message)
        eh = _error_hash(error_message)

        # Direct lookup by error hash
        for pack_dir in self.memory_dir.iterdir():
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
                        # Hash collision or different normalization — search by pattern
                        continue
                    return self._format_recall(data)
                except (yaml.YAMLError, OSError):
                    continue

        # Fallback: search by substring match across all files
        for pack_dir in self.memory_dir.iterdir():
            if not pack_dir.is_dir():
                continue
            for yaml_file in pack_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    stored_pattern = data.get("error_pattern", "")
                    # Check if the error message contains the stored pattern or vice versa
                    if (normalized and stored_pattern and (
                        stored_pattern in normalized or normalized in stored_pattern
                    )):
                        return self._format_recall(data)
                except (yaml.YAMLError, OSError):
                    continue

        return None

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all failure memory.

        Returns:
            Dict with total_failures, total_patterns, total_successes.
        """
        total_failures = 0
        total_patterns = 0
        total_successes = 0

        if self.memory_dir.exists():
            for pack_dir in self.memory_dir.iterdir():
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
    def _empty_record(error_pattern: str, pack_id: str, phase: str) -> Dict[str, Any]:
        """Return an empty failure record skeleton."""
        return {
            "error_pattern": error_pattern,
            "pack_id": pack_id,
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
            "wrong_approaches": wrong_sorted,
            "correct_approaches": correct_sorted,
            "total_sessions": data.get("total_sessions", 0),
        }
