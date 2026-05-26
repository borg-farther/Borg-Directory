#!/usr/bin/env python3
"""Dry-run Borg rollback and communications drill.

This script never mutates PyPI, GitHub releases, served runtimes, or user data. It
proves that a public incident has a named pause/rollback/comms path and records a
machine-readable drill snapshot for readiness gates.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "rollback_comms_drill_snapshot.json"
REPORT = ROOT / "docs" / "ROLLBACK_AND_COMMS_RUNBOOK.md"

REQUIRED_RUNBOOK_PHRASES = [
    "pause first-10 invites",
    "yank",
    "pin previous version",
    "operator-supervised served MCP rollback",
    "bad guidance disable path",
    "public status update",
    "user notification template",
]

DRILL_STEPS = [
    ("pause_first_10_invites", "Mark controlled beta paused and stop inviting new testers until the incident owner clears the blocker."),
    ("pypi_bad_release_response", "If a release is harmful, yank the bad file on PyPI, pin the prior known-good version in docs, and publish a status note."),
    ("served_mcp_operator_rollback", "Do not kill the gateway from an agent session; operator runs fingerprint/canary and supervised rollback/reload."),
    ("bad_guidance_disable_path", "Record the bad guidance via bad-answer issue plus borg_record_failure; disable or narrow the matching path before more testers."),
    ("public_status_update", "Update docs/public/status.json and PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO with the incident state."),
    ("user_notification_template", "Send affected testers a concise notice: what happened, whether secrets were involved, current workaround, and next update time."),
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def run_drill() -> dict[str, Any]:
    text = _read(REPORT).lower()
    missing_phrases = [phrase for phrase in REQUIRED_RUNBOOK_PHRASES if phrase.lower() not in text]
    steps = []
    for name, description in DRILL_STEPS:
        steps.append({
            "name": name,
            "passed": not missing_phrases and REPORT.exists(),
            "dry_run_action": description,
            "no_mutation": True,
        })
    passed = REPORT.exists() and not missing_phrases and all(step["passed"] for step in steps)
    return {
        "schema_version": 1,
        "gate_type": "rollback_comms_drill",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "dry_run_only": True,
        "runbook": str(REPORT.relative_to(ROOT)),
        "steps": steps,
        "missing_runbook_phrases": missing_phrases,
        "operator_boundary": "Agents must not restart/kill/reload the Hermes gateway; served runtime rollback is operator-supervised.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Borg rollback/comms dry-run drill")
    parser.add_argument("--no-write", action="store_true", help="Do not write snapshot")
    args = parser.parse_args(argv)
    snapshot = run_drill()
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
