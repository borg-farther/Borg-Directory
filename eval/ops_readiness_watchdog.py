#!/usr/bin/env python3
"""Read-only watchdog for Borg self-service production proof.

The watchdog catches stale proof snapshots, missing scheduled automation, broken
ops readiness, and contradiction between live gates and committed public status.
It intentionally allows public self-serve to remain NO-GO when blockers are the
expected current release-stage blockers: package/PyPI canary not live yet,
served-runtime/release-governance controls not cut over yet, and/or row-derived
first-10 external evidence not collected yet.
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


def _freshness_passed(age: float | None, max_snapshot_age_hours: float) -> bool:
    return age is not None and 0 <= age <= max_snapshot_age_hours


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
    if source == head:
        # Exact HEAD is honest only when the verifying checkout is clean. A
        # dirty working tree must be recorded as <base>+dirty so generated
        # proof artifacts cannot masquerade as clean-source output.
        return clean
    if source == f"{head}+dirty":
        return True
    if source.endswith("+dirty"):
        base = source.removesuffix("+dirty")
        return base == head or (_git_is_ancestor(base, head) and _changes_since_source_are_generated_artifacts(base, head))
    return False


def _git_changed_paths(base: str, head: str) -> list[str]:
    try:
        output = subprocess.check_output(["git", "diff", "--name-only", f"{base}..{head}"], cwd=ROOT, text=True)
    except Exception:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _is_generated_proof_artifact(path: str) -> bool:
    exact = {
        "eval/borg_proof_dashboard.json",
        "eval/ops_readiness_watchdog_snapshot.json",
        "eval/ops_readiness_watchdog_post_dashboard_check.json",
        "eval/public_self_serve_launch_gate_snapshot.json",
        "eval/real_user_rollout_gate_snapshot.json",
        "eval/pypi_fresh_install_snapshot.json",
        "eval/cold_start_trust_gate_snapshot.json",
        "eval/release_governance_snapshot.json",
        "eval/self_service_ops_gate_snapshot.json",
        "eval/rollback_comms_drill_snapshot.json",
        "docs/BORG_PROOF_DASHBOARD.md",
        "docs/BORG_PROOF_DASHBOARD.html",
        "docs/public/status.json",
        "docs/public/value.json",
        "docs/public/impact/impact.json",
        "docs/public/proof-dashboard/index.html",
    }
    return path in exact


def _changes_since_source_are_generated_artifacts(base: str, head: str) -> bool:
    changed = _git_changed_paths(base, head)
    return bool(changed) and all(_is_generated_proof_artifact(path) for path in changed)


def _workflow_command_text(text: str) -> str:
    commands: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        run_directive = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if run_directive.startswith("run:"):
            indent = len(raw) - len(raw.lstrip())
            after = run_directive[len("run:"):].strip()
            if after and after not in {"|", ">", "|-", ">-"}:
                candidate = after.strip('"\'')
                if candidate and not candidate.startswith("#") and not candidate.startswith(("echo ", "printf ")):
                    commands.append(candidate)
            else:
                index += 1
                while index < len(lines):
                    block_raw = lines[index]
                    block_indent = len(block_raw) - len(block_raw.lstrip())
                    block_stripped = block_raw.strip()
                    if block_stripped and block_indent <= indent:
                        index -= 1
                        break
                    if block_stripped and not block_stripped.startswith("#") and not block_stripped.startswith(("echo ", "printf ")):
                        commands.append(block_stripped)
                    index += 1
        index += 1
    return "\n".join(commands)


def _workflow_has_schedule() -> dict[str, Any]:
    path = ROOT / ".github" / "workflows" / "self-service-watchdog.yml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    command_text = _workflow_command_text(text)
    post_dashboard_check = "python eval/ops_readiness_watchdog.py --mode pr --json --no-write --output eval/ops_readiness_watchdog_post_dashboard_check.json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule"
    required_triggers = [
        "schedule:",
        "workflow_dispatch:",
    ]
    required_commands = [
        "python eval/run_pypi_fresh_install_canary.py",
        "python eval/cold_start_trust_gate.py",
        "python eval/release_governance_gate.py --output eval/release_governance_snapshot.json",
        "python eval/rollback_comms_drill.py",
        "python eval/self_service_ops_gate.py",
        "python eval/public_self_serve_launch_gate.py",
        "python eval/real_user_rollout_gate.py",
        "python eval/ops_readiness_watchdog.py",
        "python scripts/build_borg_proof_dashboard.py",
        post_dashboard_check,
        "python scripts/borg_proof_dashboard_lint.py",
    ]
    missing_triggers = [item for item in required_triggers if item not in text]
    missing_commands = [item for item in required_commands if item not in command_text]
    missing = missing_triggers + missing_commands
    ordered = [
        "python eval/run_pypi_fresh_install_canary.py",
        "python eval/cold_start_trust_gate.py",
        "python eval/release_governance_gate.py --output eval/release_governance_snapshot.json",
        "python eval/public_self_serve_launch_gate.py",
        "python eval/real_user_rollout_gate.py",
        "python eval/ops_readiness_watchdog.py",
        "python scripts/build_borg_proof_dashboard.py",
        post_dashboard_check,
        "python scripts/borg_proof_dashboard_lint.py",
    ]
    positions = {item: command_text.find(item) for item in ordered}
    order_missing = [item for item, position in positions.items() if position < 0]
    order_ok = not order_missing and all(positions[left] < positions[right] for left, right in zip(ordered, ordered[1:]))
    ordered_sequence = [
        "python eval/run_pypi_fresh_install_canary.py",
        "python eval/cold_start_trust_gate.py",
        "python eval/release_governance_gate.py --output eval/release_governance_snapshot.json",
        "python eval/rollback_comms_drill.py",
        "python eval/self_service_ops_gate.py",
        "python eval/public_self_serve_launch_gate.py",
        "python eval/real_user_rollout_gate.py",
        "python eval/ops_readiness_watchdog.py --mode pr --json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule",
        "python eval/public_self_serve_launch_gate.py",
        "python eval/real_user_rollout_gate.py",
        "python eval/ops_readiness_watchdog.py --mode pr --json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule",
        "python scripts/build_borg_proof_dashboard.py",
        post_dashboard_check,
        "python scripts/borg_proof_dashboard_lint.py",
    ]
    sequence_positions: list[dict[str, Any]] = []
    cursor = 0
    sequence_ok = True
    for index, item in enumerate(ordered_sequence):
        position = command_text.find(item, cursor)
        sequence_positions.append({"index": index, "snippet": item, "position": position})
        if position < 0:
            sequence_ok = False
        else:
            cursor = position + len(item)
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "passed": path.exists() and not missing and order_ok and sequence_ok,
        "missing": missing,
        "missing_triggers": missing_triggers,
        "missing_commands": missing_commands,
        "required_order": ordered,
        "order_positions": positions,
        "order_missing": order_missing,
        "order_ok": order_ok,
        "required_sequence": ordered_sequence,
        "sequence_positions": sequence_positions,
        "sequence_ok": sequence_ok,
    }


def _public_blockers_are_allowed(blockers: list[Any], allowed_key: str) -> bool:
    if not blockers:
        return True
    joined = "\n".join(str(b).lower() for b in blockers)
    if allowed_key == "first_10_external_evidence":
        return all(("first-10" in str(b).lower() or "verified=" in str(b).lower() or "external-user evidence" in str(b).lower()) for b in blockers)
    if allowed_key == "package_or_first_10_evidence":
        return all(
            _is_first_10_blocker(str(b)) or _is_package_release_blocker(str(b))
            for b in blockers
        )
    if allowed_key == "release_controls_or_first_10_evidence":
        return all(
            _is_first_10_blocker(str(b)) or _is_package_release_blocker(str(b)) or _is_release_control_blocker(str(b))
            for b in blockers
        )
    return allowed_key.lower() in joined


def _is_first_10_blocker(blocker: str) -> bool:
    lower = blocker.lower()
    return "first-10" in lower or "verified=" in lower or "external-user evidence" in lower


def _is_package_release_blocker(blocker: str) -> bool:
    lower = blocker.lower()
    return (
        "pypi latest" in lower
        or "latest metadata" in lower
        or "fresh-install" in lower
        or "fresh install" in lower
        or "mcp stdio" in lower
    )


def _is_release_control_blocker(blocker: str) -> bool:
    lower = blocker.lower()
    return (
        "served runtime" in lower
        or "version_matches_source" in lower
        or "reload_status" in lower
        or "release governance" in lower
        or "branch protection" in lower
        or "main branch is not protected" in lower
    )


def _has_package_release_gap(blockers: list[Any]) -> bool:
    return any(_is_package_release_blocker(str(blocker)) for blocker in blockers)


def _has_release_control_gap(blockers: list[Any]) -> bool:
    return any(_is_release_control_blocker(str(blocker)) for blocker in blockers)


def _has_first_10_gap(blockers: list[Any]) -> bool:
    return any(_is_first_10_blocker(str(blocker)) for blocker in blockers)


def _is_pre_package_release_stage(live_public: dict[str, Any], live_real: dict[str, Any], pypi_current: bool) -> bool:
    public_blockers = live_public.get("blockers") or []
    real_blockers = live_real.get("blockers") or []
    return bool(
        not pypi_current
        and live_public.get("ready_for_controlled_first_10_beta") is False
        and live_public.get("ready_for_public_self_serve_launch") is False
        and live_public.get("max_recommended_real_users_now") == 0
        and live_real.get("ready_for_10_controlled_beta") is False
        and live_real.get("ready_for_100_real_users") is False
        and live_real.get("max_recommended_real_users_now") == 0
        and _has_package_release_gap(public_blockers)
        and _has_package_release_gap(real_blockers)
        and _has_first_10_gap(public_blockers)
        and _has_first_10_gap(real_blockers)
        and _public_blockers_are_allowed(public_blockers, "release_controls_or_first_10_evidence")
        and _public_blockers_are_allowed(real_blockers, "release_controls_or_first_10_evidence")
    )


def _is_release_control_blocked_stage(live_public: dict[str, Any], live_real: dict[str, Any], pypi_current: bool) -> bool:
    public_blockers = live_public.get("blockers") or []
    real_blockers = live_real.get("blockers") or []
    return bool(
        pypi_current
        and live_public.get("ready_for_controlled_first_10_beta") is False
        and live_public.get("ready_for_public_self_serve_launch") is False
        and live_public.get("max_recommended_real_users_now") == 0
        and live_real.get("ready_for_10_controlled_beta") is False
        and live_real.get("ready_for_100_real_users") is False
        and live_real.get("max_recommended_real_users_now") == 0
        and _has_release_control_gap(public_blockers)
        and _has_release_control_gap(real_blockers)
        and _has_first_10_gap(public_blockers)
        and _has_first_10_gap(real_blockers)
        and _public_blockers_are_allowed(public_blockers, "release_controls_or_first_10_evidence")
        and _public_blockers_are_allowed(real_blockers, "release_controls_or_first_10_evidence")
    )


def compile_watchdog(*, max_snapshot_age_hours: float = 24.0, allow_public_blocker: str = "first_10_external_evidence") -> dict[str, Any]:
    version = public_gate.source_version()
    public_snapshot = _read_json(ROOT / "eval" / "public_self_serve_launch_gate_snapshot.json")
    status = _read_json(ROOT / "docs" / "public" / "status.json")
    value = _read_json(ROOT / "docs" / "public" / "value.json")
    impact = _read_json(ROOT / "docs" / "public" / "impact" / "impact.json")
    dashboard = _read_json(ROOT / "eval" / "borg_proof_dashboard.json")
    pypi = _read_json(ROOT / "eval" / "pypi_fresh_install_snapshot.json")
    cold = _read_json(ROOT / "eval" / "cold_start_trust_gate_snapshot.json")

    live_public = public_gate.compile_gate(fetch_network=True, require_ops_watchdog=False)
    live_real = real_user_rollout_gate.compile_rollout_gate(require_ops_watchdog=False)
    ops = self_service_ops_gate.compile_gate()
    workflow = _workflow_has_schedule()

    live_pypi_latest = ((live_public.get("gates") or {}).get("pypi_latest") or {})
    pypi_current = bool(
        pypi.get("success") is True
        and pypi.get("version") == version
        and bool((pypi.get("mcp_stdio_canary") or {}).get("passed"))
        and live_pypi_latest.get("passed") is True
    )
    pre_package_release_stage = _is_pre_package_release_stage(live_public, live_real, pypi_current)
    release_control_blocked_stage = _is_release_control_blocked_stage(live_public, live_real, pypi_current)
    controlled_package_stage = bool(
        live_public.get("ready_for_controlled_first_10_beta")
        and live_public.get("max_recommended_real_users_now") == 10
        and not live_public.get("ready_for_public_self_serve_launch")
        and live_real.get("ready_for_10_controlled_beta")
        and live_real.get("max_recommended_real_users_now") == 10
        and not live_real.get("ready_for_100_real_users")
    )

    checks: dict[str, dict[str, Any]] = {}
    checks["self_service_ops_gate"] = {"passed": ops.get("passed") is True, "blockers": ops.get("blockers", [])}
    checks["watchdog_workflow"] = workflow
    checks["pypi_fresh_current"] = {
        "passed": pypi_current or pre_package_release_stage,
        "version": pypi.get("version"),
        "expected_version": version,
        "generated_at_utc": pypi.get("generated_at_utc"),
        "pypi_current": pypi_current,
        "pre_package_release_stage": pre_package_release_stage,
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
        "public_status_json": status,
        "public_value_json": value,
        "public_impact_json": impact,
        "real_user_rollout_gate_snapshot": _read_json(ROOT / "eval" / "real_user_rollout_gate_snapshot.json"),
        "release_governance_snapshot": _read_json(ROOT / "eval" / "release_governance_snapshot.json"),
        "self_service_ops_gate_snapshot": _read_json(ROOT / "eval" / "self_service_ops_gate_snapshot.json"),
        "rollback_comms_drill_snapshot": _read_json(ROOT / "eval" / "rollback_comms_drill_snapshot.json"),
    }.items():
        timestamp = data.get("generated_at_utc") or data.get("updated_at")
        age = _age_hours(timestamp)
        raw_ok = _freshness_passed(age, max_snapshot_age_hours)
        allowed_stale_reason = None
        if name == "pypi_fresh_install_snapshot" and age is not None and age > max_snapshot_age_hours and pre_package_release_stage:
            # During the explicit pre-package-release NO-GO state, live PyPI metadata
            # already fails closed (same-version artifact drift / missing immutable
            # release) and caps real users at 0. An aged fresh-install canary should
            # not make the scheduled ops watchdog red for the wrong reason. Once
            # package proof is claimed green, or release controls are the only
            # blockers, this exemption disappears and stale PyPI canaries fail hard.
            allowed_stale_reason = "pre_package_release_stage_package_proof_already_red"
        ok = raw_ok or allowed_stale_reason is not None
        checks["snapshot_freshness"]["items"][name] = {
            "age_hours": age,
            "passed": ok,
            "raw_freshness_passed": raw_ok,
            "allowed_stale_reason": allowed_stale_reason,
        }
        if not ok:
            checks["snapshot_freshness"]["passed"] = False

    checks["public_gate_live_matches_snapshot"] = {
        "passed": bool(
            public_snapshot.get("source_version") == live_public.get("source_version")
            and public_snapshot.get("ready_for_controlled_first_10_beta") == live_public.get("ready_for_controlled_first_10_beta")
            and public_snapshot.get("ready_for_public_self_serve_launch") == live_public.get("ready_for_public_self_serve_launch")
            and public_snapshot.get("max_recommended_real_users_now") == live_public.get("max_recommended_real_users_now")
            and public_snapshot.get("blockers") == live_public.get("blockers")
        ),
        "snapshot": {k: public_snapshot.get(k) for k in ["source_version", "ready_for_controlled_first_10_beta", "ready_for_public_self_serve_launch", "max_recommended_real_users_now", "blockers"]},
        "live": {k: live_public.get(k) for k in ["source_version", "ready_for_controlled_first_10_beta", "ready_for_public_self_serve_launch", "max_recommended_real_users_now", "blockers"]},
    }
    checks["real_user_rollout_consistency"] = {
        "passed": controlled_package_stage or pre_package_release_stage or release_control_blocked_stage,
        "live": {k: live_real.get(k) for k in ["ready_for_10_controlled_beta", "infrastructure_ready_for_100", "ready_for_100_real_users", "max_recommended_real_users_now", "blockers"]},
        "controlled_package_stage": controlled_package_stage,
        "pre_package_release_stage": pre_package_release_stage,
        "release_control_blocked_stage": release_control_blocked_stage,
    }
    checks["public_blockers_allowed"] = {
        "passed": _public_blockers_are_allowed(live_public.get("blockers") or [], allow_public_blocker),
        "allow_public_blocker": allow_public_blocker,
        "blockers": live_public.get("blockers") or [],
    }
    controlled_status_ok = bool(
            status.get("state") == "NO-GO public self-serve; controlled first-10 beta CONDITIONAL GO while gates remain green"
            and (status.get("controlled_first_10_beta") or {}).get("verdict") == "CONDITIONAL"
            and status.get("max_recommended_real_users_now") == 10
            and status.get("verified_external_users") == 0
    )
    pre_package_status_ok = bool(
        status.get("state") == "NO-GO public self-serve; source/local release-candidate only"
        and (status.get("controlled_first_10_beta") or {}).get("verdict") == "NO-GO"
        and status.get("max_recommended_real_users_now") == 0
        and status.get("verified_external_users") == 0
    )
    release_control_blocked_status_ok = bool(
        status.get("state") == "NO-GO public self-serve; public package proof green, release controls blocked"
        and (status.get("controlled_first_10_beta") or {}).get("verdict") == "NO-GO"
        and status.get("max_recommended_real_users_now") == 0
        and status.get("verified_external_users") == 0
        and status.get("served_runtime_freshness_gate") == "FAIL"
        and status.get("release_governance_gate") == "FAIL"
    )
    checks["public_status_consistency"] = {
        "passed": bool(
            (controlled_status_ok and controlled_package_stage)
            or (pre_package_status_ok and pre_package_release_stage)
            or (release_control_blocked_status_ok and release_control_blocked_stage)
        ),
        "status_state": status.get("state"),
        "controlled_verdict": (status.get("controlled_first_10_beta") or {}).get("verdict"),
        "max_recommended_real_users_now": status.get("max_recommended_real_users_now"),
        "verified_external_users": status.get("verified_external_users"),
        "controlled_status_ok": controlled_status_ok,
        "pre_package_status_ok": pre_package_status_ok,
        "release_control_blocked_status_ok": release_control_blocked_status_ok,
    }
    metrics = dashboard.get("metrics") or {}
    measured = ((metrics.get("measured_savings") or {}).get("value") or {}) if isinstance(metrics, dict) else {}
    normalized_measured = {
        "rows_with_measured_value": int(measured.get("rows_with_measured_value") or 0),
        "dead_ends_avoided_confirmed": int(measured.get("dead_ends_avoided_confirmed") or 0),
        "net_minutes_saved": float(measured.get("net_minutes_saved") or 0.0),
        "positive_minutes_saved": float(measured.get("positive_minutes_saved") or 0.0),
        "negative_minutes_cost": float(measured.get("negative_minutes_cost") or 0.0),
        "net_tokens_saved": int(measured.get("net_tokens_saved") or 0),
        "positive_tokens_saved": int(measured.get("positive_tokens_saved") or 0),
        "negative_tokens_cost": int(measured.get("negative_tokens_cost") or 0),
        "counterfactual_basis_counts": measured.get("counterfactual_basis_counts") or {},
    }
    checks["public_json_dashboard_consistency"] = {
        "passed": bool(
            status.get("updated_at") == dashboard.get("generated_at_utc")
            and value.get("updated_at") == dashboard.get("generated_at_utc")
            and impact.get("updated_at") == dashboard.get("generated_at_utc")
            and status.get("source_revision") == dashboard.get("source_revision")
            and status.get("controlled_first_10_beta") == (dashboard.get("top_verdict") or {}).get("controlled_first_10_beta")
            and status.get("broad_public_launch") == (dashboard.get("top_verdict") or {}).get("broad_public_launch")
            and status.get("max_recommended_real_users_now") == (metrics.get("max_recommended_real_users_now") or {}).get("value", 0)
            and status.get("verified_external_users") == (metrics.get("verified_external_users") or {}).get("value", 0)
            and value.get("measured_savings") == normalized_measured
            and impact.get("measured_savings") == value.get("measured_savings")
        ),
        "status_updated_at": status.get("updated_at"),
        "dashboard_generated_at_utc": dashboard.get("generated_at_utc"),
        "status_source_revision": status.get("source_revision"),
        "dashboard_source_revision": dashboard.get("source_revision"),
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
    parser.add_argument("--output", help="Write the watchdog result to this explicit path; works with --no-write for post-dashboard proof artifacts")
    parser.add_argument("--max-snapshot-age-hours", type=float, default=24.0)
    parser.add_argument("--allow-public-blocker", default="first_10_external_evidence")
    parser.add_argument("--require-ci-schedule", action="store_true", help="Kept for CI contract compatibility; schedule is always checked")
    args = parser.parse_args(argv)
    snapshot = compile_watchdog(max_snapshot_age_hours=args.max_snapshot_age_hours, allow_public_blocker=args.allow_public_blocker)
    output_path = Path(args.output) if args.output else (None if args.no_write else SNAPSHOT)
    if output_path is not None:
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reported_snapshot = output_path or SNAPSHOT
    reported_path = str(reported_snapshot.relative_to(ROOT)) if reported_snapshot.is_relative_to(ROOT) else str(reported_snapshot)
    print(json.dumps(snapshot if args.json else {"passed": snapshot["passed"], "blockers": snapshot["blockers"], "snapshot": reported_path}, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
