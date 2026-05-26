#!/usr/bin/env python3
"""Compile Borg synthetic/load and real-user rollout readiness gates."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
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


def _real_user_rollout_gate() -> dict[str, Any]:
    snap = _read_json(ROOT / "eval" / "real_user_rollout_gate_snapshot.json") or {}
    return {
        "exists": bool(snap),
        "ready_for_10_controlled_beta": bool(snap.get("ready_for_10_controlled_beta")),
        "infrastructure_ready_for_100": bool(snap.get("infrastructure_ready_for_100")),
        "ready_for_100_real_users": bool(snap.get("ready_for_100_real_users")),
        "max_recommended_real_users_now": snap.get("max_recommended_real_users_now", 0),
        "blockers": snap.get("blockers") or ["real-user rollout gate snapshot missing"],
        "generated_at_utc": snap.get("generated_at_utc"),
    }


def compile_scoreboard() -> dict[str, Any]:
    version = _version_consistent()
    first_user = _first_user_surface()
    security = _security_surface()
    load_10 = _load_gate(10)
    load_100 = _load_gate(100)
    load_1000 = _load_gate(1000)
    gate_run = _read_json(ROOT / "eval" / "gate_run_snapshot.json") or {}
    real_user = _real_user_rollout_gate()

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
    synthetic_load_all_pass = ready_for_1000
    real_user_100_all_pass = synthetic_load_all_pass and real_user["ready_for_100_real_users"]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "eval/uat_scoreboard.py",
        "version": version,
        "first_user_surface": first_user,
        "security_surface": security,
        "loads": {"10": load_10, "100": load_100, "1000": load_1000},
        "real_user_rollout": real_user,
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
        "synthetic_load_all_pass": synthetic_load_all_pass,
        "real_user_100_all_pass": real_user_100_all_pass,
        "all_pass": real_user_100_all_pass,
    }


def _write_markdown(snapshot: dict[str, Any]) -> None:
    lines = [
        "# Borg Project Status",
        "",
        f"Updated: `{snapshot['timestamp']}`",
        "",
        "## Synthetic/load rollout decision",
        "",
        "These flags are for logical load gates only. They do not authorize 100 real external users.",
        "",
        f"- Ready for 10 logical load users: {'GO' if snapshot['ready_for_10'] else 'NO-GO'}",
        f"- Ready for 100 logical load users: {'GO' if snapshot['ready_for_100'] else 'NO-GO'}",
        f"- Ready for 1000 logical load users: {'GO' if snapshot['ready_for_1000'] else 'NO-GO'}",
        f"- Synthetic/load overall: {'GO' if snapshot['synthetic_load_all_pass'] else 'NO-GO'}",
        "",
        "Real external-user rollout is gated separately by `eval/real_user_rollout_gate_snapshot.json`.",
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
        lines.append(f"- {users} logical users: passed={gate.get('passed')} total_requests={gate.get('total_requests')} p95_ms={gate.get('p95_ms')} p99_ms={gate.get('p99_ms')}")
    lines.extend([
        "",
        "## Real external-user rollout decision",
        "",
        f"- Ready for 10 controlled real users: {'GO' if snapshot['real_user_rollout'].get('ready_for_10_controlled_beta') else 'NO-GO'}",
        f"- Ready for 100 real external users: {'GO' if snapshot['real_user_rollout'].get('ready_for_100_real_users') else 'NO-GO'}",
        f"- Max recommended real users now: {snapshot['real_user_rollout'].get('max_recommended_real_users_now')}",
        "- Source: `eval/real_user_rollout_gate_snapshot.json`",
        "",
        "## Real-user blockers",
        "",
    ])
    blockers = snapshot["real_user_rollout"].get("blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("None.")
    lines.extend([
        "",
        "Canonical machine snapshot: `eval/uat_scoreboard_snapshot.json`",
        "",
    ])
    (ROOT / "PROJECT_STATUS.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Borg synthetic/load and real-user rollout readiness gates")
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Exit 0 when synthetic/logical load gates pass even if 100-real-user rollout is still blocked. Default exits nonzero unless all real-user gates pass.",
    )
    args = parser.parse_args(argv)
    snapshot = compile_scoreboard()
    out = ROOT / "eval" / "uat_scoreboard_snapshot.json"
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(snapshot)
    print(ROOT / "PROJECT_STATUS.md")
    print(out)
    return 0 if (snapshot["synthetic_load_all_pass"] if args.synthetic_only else snapshot["all_pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
