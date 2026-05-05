#!/usr/bin/env python3
"""Compile Borg production readiness gates, including 1000-user scale."""
from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _version_consistent() -> dict[str, Any]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = pyproject["project"]["version"]
    init_text = (ROOT / "borg" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    runtime_version = match.group(1) if match else ""
    return {
        "project_version": project_version,
        "runtime_version": runtime_version,
        "passed": bool(project_version and project_version == runtime_version),
    }


def _first_user_surface() -> dict[str, Any]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    urls = pyproject.get("project", {}).get("urls", {})
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    license_exists = (ROOT / "LICENSE").exists()
    checks = {
        "readme_has_pip_install": "pip install agent-borg" in readme,
        "readme_has_setup_claude_verify_fix": "borg setup-claude --scope user --verify --fix" in readme,
        "urls_complete": all(k in urls and str(urls[k]).startswith("https://github.com/borg-farther/Borg-Directory") for k in ["Homepage", "Repository", "Documentation", "Issues"]),
        "license_exists": license_exists,
    }
    return {"checks": checks, "passed": all(checks.values())}


def _security_surface() -> dict[str, Any]:
    required = [
        "docs/SECURITY_HARDENING_BASELINE.md",
        "docs/LEARNING_ATOM_SCHEMA.md",
        "docs/PRIVACY_MODEL.md",
        "docs/PROMPT_INJECTION_THREAT_MODEL.md",
        "docs/TRUST_AND_PROMOTION.md",
        "docs/REVOCATION_AND_DELETION.md",
        "scripts/security_gate_check.py",
        "scripts/run_atom_fixture_corpus.py",
        ".github/workflows/security-gates.yml",
        "borg/core/learning_atoms.py",
        "borg/core/atom_policy.py",
        "borg/core/atom_store.py",
        "borg/core/atom_retrieval.py",
        "borg/core/prompt_injection.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    return {"required_files": required, "missing": missing, "passed": not missing}


def _load_gate(users: int) -> dict[str, Any]:
    snap = _read_json(ROOT / "eval" / f"load_{users}_snapshot.json")
    if not snap:
        return {"exists": False, "passed": False, "error": "missing snapshot"}
    return {
        "exists": True,
        "passed": bool(snap.get("passed")),
        "success_rate": snap.get("success_rate"),
        "p95_ms": (snap.get("latency_ms") or {}).get("p95"),
        "p99_ms": (snap.get("latency_ms") or {}).get("p99"),
        "total_requests": snap.get("total_requests"),
        "timestamp": snap.get("timestamp"),
    }


def compile_scoreboard() -> dict[str, Any]:
    version = _version_consistent()
    first_user = _first_user_surface()
    security = _security_surface()
    load_10 = _load_gate(10)
    load_100 = _load_gate(100)
    load_1000 = _load_gate(1000)
    gate_run = _read_json(ROOT / "eval" / "gate_run_snapshot.json") or {}

    gates = {
        "version_consistency": version["passed"],
        "first_user_surface": first_user["passed"],
        "security_surface": security["passed"],
        "load_10": load_10["passed"],
        "load_100": load_100["passed"],
        "load_1000": load_1000["passed"],
    }
    ready_for_10 = all(gates[k] for k in ["version_consistency", "first_user_surface", "security_surface", "load_10"])
    ready_for_100 = ready_for_10 and gates["load_100"]
    ready_for_1000 = ready_for_100 and gates["load_1000"]
    all_pass = ready_for_1000
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "eval/uat_scoreboard.py",
        "version": version,
        "first_user_surface": first_user,
        "security_surface": security,
        "loads": {"10": load_10, "100": load_100, "1000": load_1000},
        "gate_run_snapshot": {
            "exists": bool(gate_run),
            "timestamp": gate_run.get("timestamp"),
            "ready_for_10": gate_run.get("ready_for_10"),
            "ready_for_100": gate_run.get("ready_for_100"),
            "ready_for_1000": gate_run.get("ready_for_1000"),
        },
        "gates": gates,
        "ready_for_10": ready_for_10,
        "ready_for_100": ready_for_100,
        "ready_for_1000": ready_for_1000,
        "all_pass": all_pass,
    }


def _write_markdown(snapshot: dict[str, Any]) -> None:
    lines = [
        "# Borg Project Status",
        "",
        f"Updated: `{snapshot['timestamp']}`",
        "",
        "## Rollout decision",
        "",
        f"- Ready for 10 users: {'GO' if snapshot['ready_for_10'] else 'NO-GO'}",
        f"- Ready for 100 users: {'GO' if snapshot['ready_for_100'] else 'NO-GO'}",
        f"- Ready for 1000 users: {'GO' if snapshot['ready_for_1000'] else 'NO-GO'}",
        f"- Overall: {'GO' if snapshot['all_pass'] else 'NO-GO'}",
        "",
        "## Hard gates",
        "",
    ]
    for name, passed in snapshot["gates"].items():
        lines.append(f"- {name}: {'PASS' if passed else 'FAIL'}")
    lines.extend([
        "",
        "## Load gates",
        "",
    ])
    for users, gate in snapshot["loads"].items():
        lines.append(f"- {users} users: passed={gate.get('passed')} total_requests={gate.get('total_requests')} p95_ms={gate.get('p95_ms')} p99_ms={gate.get('p99_ms')}")
    lines.extend([
        "",
        "Canonical machine snapshot: `eval/uat_scoreboard_snapshot.json`",
        "",
    ])
    (ROOT / "PROJECT_STATUS.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    snapshot = compile_scoreboard()
    out = ROOT / "eval" / "uat_scoreboard_snapshot.json"
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(snapshot)
    print(ROOT / "PROJECT_STATUS.md")
    print(out)
    return 0 if snapshot["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
