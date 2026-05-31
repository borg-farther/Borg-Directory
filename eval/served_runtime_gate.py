#!/usr/bin/env python3
"""Validate a captured served Borg MCP runtime fingerprint.

This gate is deliberately read-only: it never restarts or patches a live server.
Operators capture `borg_runtime_fingerprint` from the served MCP endpoint and
feed the JSON here. Public/served-runtime readiness requires the loaded runtime
to match the repository/package version and pass Borg's behavior canaries.
"""
from __future__ import annotations

import argparse
import json
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "eval" / "served_runtime_fingerprint_snapshot.json"


def source_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _read_payload(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"served runtime fingerprint snapshot missing: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"served runtime fingerprint snapshot unreadable: {exc}"
    if isinstance(payload, dict) and isinstance(payload.get("result"), str):
        try:
            nested = json.loads(payload["result"])
            if isinstance(nested, dict):
                payload = nested
        except json.JSONDecodeError:
            pass
    if not isinstance(payload, dict):
        return None, "served runtime fingerprint snapshot must be a JSON object"
    return payload, None


def evaluate_snapshot(payload: dict[str, Any] | None, *, expected_version: str) -> dict[str, Any]:
    blockers: list[str] = []
    if payload is None:
        blockers.append("served runtime fingerprint snapshot not provided")
        payload = {}

    confidence = payload.get("confidence_gate_canary") or {}
    observe = payload.get("observe_behavior_canary") or {}
    if payload.get("success") is not True:
        blockers.append("runtime fingerprint did not report success=true")
    if payload.get("borg_version") != expected_version:
        blockers.append(
            f"served runtime borg_version {payload.get('borg_version')!r} != source version {expected_version!r}"
        )
    if payload.get("source_version") not in (expected_version, None):
        blockers.append(
            f"served runtime source_version {payload.get('source_version')!r} != source version {expected_version!r}"
        )
    if payload.get("version_matches_source") is not True:
        blockers.append("served runtime version_matches_source is not true")
    if payload.get("reload_status") != "loaded_code_matches_source_behavior":
        blockers.append(
            "served runtime reload_status is not loaded_code_matches_source_behavior"
        )
    if confidence.get("passed") is not True:
        blockers.append("served runtime confidence_gate_canary did not pass")
    if observe.get("passed") is not True or observe.get("meta_prompt_failed_closed") is not True:
        blockers.append("served runtime observe_behavior_canary did not pass")

    return {
        "schema_version": 1,
        "passed": not blockers,
        "expected_version": expected_version,
        "blockers": blockers,
        "summary": {
            "borg_version": payload.get("borg_version"),
            "source_version": payload.get("source_version"),
            "version_matches_source": payload.get("version_matches_source"),
            "reload_status": payload.get("reload_status"),
            "confidence_gate_canary_passed": confidence.get("passed"),
            "observe_behavior_canary_passed": observe.get("passed"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a served Borg MCP runtime fingerprint snapshot")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="Path to captured borg_runtime_fingerprint JSON")
    parser.add_argument("--expected-version", default=source_version(), help="Expected Borg source/package version")
    args = parser.parse_args(argv)

    payload, read_error = _read_payload(Path(args.snapshot))
    result = evaluate_snapshot(payload, expected_version=args.expected_version)
    if read_error:
        result["blockers"].insert(0, read_error)
        result["passed"] = False
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
