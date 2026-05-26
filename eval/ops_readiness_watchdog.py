#!/usr/bin/env python3
"""Read-only watchdog for Borg self-service production proof.

The watchdog catches stale proof snapshots, missing scheduled automation, broken
ops readiness, and contradiction between live gates and committed public status.
It intentionally allows public self-serve to remain NO-GO when the only blocker
is first-10 external evidence.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval import public_self_serve_launch_gate as public_gate
from eval import real_user_rollout_gate
from eval import self_service_ops_gate

SNAPSHOT = ROOT / "eval" / "ops_readiness_watchdog_snapshot.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_hours(value: str | None) -> float | None:
    dt = _parse_dt(value)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600


def _git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def _git_clean() -> bool:
    try:
        return not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    except Exception:
        return False


def _git_is_ancestor(candidate: str, head: str | None) -> bool:
    if not candidate or not head:
        return False
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", candidate, head],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _source_revision_is_honest(source_rev: Any, head: str | None, clean: bool) -> bool:
    if not source_rev or not head:
        return False
    source = str(source_rev)
    if source == head or source == f"{head}+dirty":
        return True
    if source.endswith("+dirty"):
        base = source.removesuffix("+dirty")
        return (not clean) or _git_is_ancestor(base, head)
    return False


def _workflow_has_schedule() -> dict[str, Any]:
    path = ROOT / ".github" / "workflows" / "self-service-watchdog.yml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    required = ["schedule:", "workflow_dispatch:", "python eval/ops_readiness_watchdog.py", "python eval/self_service_ops_gate.py"]
    missing = [item for item in required if item not in text]
    return {"path": str(path.relative_to(ROOT)), "exists": path.exists(), "passed": path.exists() and not missing, "missing": missing}


def _public_blockers_are_allowed(blockers: list[Any], allowed_key: str) -> bool:
    if not blockers:
        return True
    joined = "\n".join(str(b).lower() for b in blockers)
    if allowed_key == "first_10_external_evidence":
        return all(("first-10" in str(b).lower() or "verified=" in str(b).lower() or "external-user evidence" in str(b).lower()) for b in blockers)
    return allowed_key.lower() in joined


def compile_watchdog(*, max_snapshot_age_hours: float = 24.0, allow_public_blocker: str = "first_10_external_evidence") -> dict[str, Any]:
    version = public_gate.source_version()
    public_snapshot = _read_json(ROOT / "eval" / "public_self_serve_launch_gate_snapshot.json")
    status = _read_json(ROOT / "docs" / "public" / "status.json")
    dashboard = _read_json(ROOT / "eval" / "borg_proof_dashboard.json")
    pypi = _read_json(ROOT / "eval" / "pypi_fresh_install_snapshot.json")
    cold = _read_json(ROOT / "eval" / "cold_start_trust_gate_snapshot.json")

    live_public = public_gate.compile_gate(fetch_network=True)
    live_real = real_user_rollout_gate.compile_rollout_gate()
    ops = self_service_ops_gate.compile_gate()
    workflow = _workflow_has_schedule()

    checks: dict[str, dict[str, Any]] = {}
    checks["self_service_ops_gate"] = {"passed": ops.get("passed") is True, "blockers": ops.get("blockers", [])}
    checks["watchdog_workflow"] = workflow
    checks["pypi_fresh_current"] = {
        "passed": pypi.get("success") is True and pypi.get("version") == version and bool((pypi.get("mcp_stdio_canary") or {}).get("passed")),
        "version": pypi.get("version"),
        "expected_version": version,
        "generated_at_utc": pypi.get("generated_at_utc"),
    }
    checks["cold_start_trust_current"] = {
        "passed": cold.get("passed") is True,
        "generated_at_utc": cold.get("generated_at_utc"),
    }
    checks["snapshot_freshness"] = {"passed": True, "items": {}}
    for name, data in {
        "public_self_serve_launch_gate_snapshot": public_snapshot,
        "pypi_fresh_install_snapshot": pypi,
        "cold_start_trust_gate_snapshot": cold,
        "borg_proof_dashboard": dashboard,
        "self_service_ops_gate_snapshot": _read_json(ROOT / "eval" / "self_service_ops_gate_snapshot.json"),
        "rollback_comms_drill_snapshot": _read_json(ROOT / "eval" / "rollback_comms_drill_snapshot.json"),
    }.items():
        age = _age_hours(data.get("generated_at_utc") or data.get("updated_at"))
        ok = age is not None and age <= max_snapshot_age_hours
        checks["snapshot_freshness"]["items"][name] = {"age_hours": age, "passed": ok}
        if not ok:
            checks["snapshot_freshness"]["passed"] = False

    checks["public_gate_live_matches_snapshot"] = {
        "passed": bool(
            public_snapshot.get("source_version") == live_public.get("source_version")
            and public_snapshot.get("ready_for_controlled_first_10_beta") == live_public.get("ready_for_controlled_first_10_beta")
            and public_snapshot.get("ready_for_public_self_serve_launch") == live_public.get("ready_for_public_self_serve_launch")
            and public_snapshot.get("max_recommended_real_users_now") == live_public.get("max_recommended_real_users_now")
        ),
        "snapshot": {k: public_snapshot.get(k) for k in ["source_version", "ready_for_controlled_first_10_beta", "ready_for_public_self_serve_launch", "max_recommended_real_users_now"]},
        "live": {k: live_public.get(k) for k in ["source_version", "ready_for_controlled_first_10_beta", "ready_for_public_self_serve_launch", "max_recommended_real_users_now"]},
    }
    checks["real_user_rollout_consistency"] = {
        "passed": bool(live_real.get("ready_for_10_controlled_beta") and live_real.get("max_recommended_real_users_now") == 10 and not live_real.get("ready_for_100_real_users")),
        "live": {k: live_real.get(k) for k in ["ready_for_10_controlled_beta", "infrastructure_ready_for_100", "ready_for_100_real_users", "max_recommended_real_users_now", "blockers"]},
    }
    checks["public_blockers_allowed"] = {
        "passed": _public_blockers_are_allowed(live_public.get("blockers") or [], allow_public_blocker),
        "allow_public_blocker": allow_public_blocker,
        "blockers": live_public.get("blockers") or [],
    }
    checks["public_status_consistency"] = {
        "passed": bool(
            status.get("state") == "NO-GO public self-serve; controlled first-10 beta GO"
            and (status.get("controlled_first_10_beta") or {}).get("verdict") == "CONDITIONAL"
            and status.get("max_recommended_real_users_now") == 10
            and status.get("verified_external_users") == 0
        ),
        "status_state": status.get("state"),
        "controlled_verdict": (status.get("controlled_first_10_beta") or {}).get("verdict"),
        "max_recommended_real_users_now": status.get("max_recommended_real_users_now"),
        "verified_external_users": status.get("verified_external_users"),
    }
    head = _git_head()
    clean = _git_clean()
    source_rev = dashboard.get("source_revision") or status.get("source_revision")
    checks["source_revision_honesty"] = {
        "passed": _source_revision_is_honest(source_rev, head, clean),
        "head": head,
        "git_clean": clean,
        "source_revision": source_rev,
        "policy": "Committed dashboards may be generated from a dirty tree and must mark +dirty; clean-tree status endpoints should match HEAD or a dirty ancestor used to generate committed proof artifacts.",
    }

    blockers: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            blockers.append(f"{name} failed: {check}")
    passed = not blockers
    return {
        "schema_version": 1,
        "gate_type": "ops_readiness_watchdog",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "source_version": version,
        "ready_for_controlled_first_10_beta": live_public.get("ready_for_controlled_first_10_beta"),
        "ready_for_public_self_serve_launch": live_public.get("ready_for_public_self_serve_launch"),
        "max_recommended_real_users_now": live_public.get("max_recommended_real_users_now"),
        "checks": checks,
        "blockers": blockers,
        "truth_policy": "Watchdog passing means controlled first-10 ops proof is fresh and internally consistent. Broad public self-serve still requires row-derived first-10 external-user evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Borg ops readiness watchdog")
    parser.add_argument("--mode", choices=["pr", "scheduled"], default="pr")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--max-snapshot-age-hours", type=float, default=24.0)
    parser.add_argument("--allow-public-blocker", default="first_10_external_evidence")
    parser.add_argument("--require-ci-schedule", action="store_true", help="Kept for CI contract compatibility; schedule is always checked")
    args = parser.parse_args(argv)
    snapshot = compile_watchdog(max_snapshot_age_hours=args.max_snapshot_age_hours, allow_public_blocker=args.allow_public_blocker)
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot if args.json else {"passed": snapshot["passed"], "blockers": snapshot["blockers"], "snapshot": str(SNAPSHOT.relative_to(ROOT))}, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
