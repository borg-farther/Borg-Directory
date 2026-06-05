from __future__ import annotations

import json
from pathlib import Path

from eval import ops_readiness_watchdog as watchdog


def _public_snapshot() -> dict[str, object]:
    return {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": True,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 10,
        "gates": {"pypi_latest": {"passed": True}},
        "blockers": ["first-10 external-user evidence has not passed"],
    }


def _pre_package_public_snapshot() -> dict[str, object]:
    return {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "gates": {"pypi_latest": {"passed": False}},
        "blockers": [
            "PyPI latest metadata does not match source version or required project URLs",
            "PyPI fresh-install + MCP stdio canary snapshot is missing or failing",
            "first-10 external-user evidence has not passed: verified=0/10",
        ],
    }


def _github_source_snapshot(now: str, *, version: str = "9.9.9", passed: bool = True) -> dict[str, object]:
    required_results = [
        "fresh_venv_create",
        "pip_install_git_source",
        "pip_show_agent_borg",
        "borg_version",
        "borg_help",
        "borg_rescue_json",
        "borg_doctor_json",
        "borg_generate_systematic_debugging_rules",
        "borg_convert_openclaw_registry",
        "python_api_check",
    ]
    return {
        "success": passed,
        "version": version,
        "install_source": "github_source",
        "install_target": "git+https://github.com/borg-farther/Borg-Directory.git@main",
        "generated_at_utc": now,
        "results": [{"name": name, "passed": passed} for name in required_results],
        "mcp_stdio_canary": {
            "passed": passed,
            "server_info": {"name": "borg-mcp-server", "version": version},
            "required_tools_present": ["borg_observe", "borg_rescue", "borg_runtime_fingerprint", "error_lookup"],
            "alias_value_signal": passed,
            "fingerprint_signal": passed,
        },
        "checkout_import_leakage": {
            "passed": passed,
            "installed_file": "/tmp/borg-source-venv/lib/python3.12/site-packages/borg/__init__.py",
        },
    }


def _github_source_gate(now: str, *, version: str = "9.9.9", passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "exists": True,
        "path": "eval/github_source_install_snapshot.json",
        "success": passed,
        "version": version,
        "install_source": "github_source",
        "install_target": "git+https://github.com/borg-farther/Borg-Directory.git@main",
        "canonical_install_target": True,
        "missing_required_results": [],
        "missing_mcp_tools": [],
        "mcp_stdio_canary_passed": passed,
        "checkout_import_leakage_passed": passed,
        "freshness": {"passed": passed, "age_hours": 1.0, "generated_at_utc": now},
    }


def _measured_savings() -> dict[str, object]:
    return {
        "rows_with_measured_value": 0,
        "dead_ends_avoided_confirmed": 0,
        "net_minutes_saved": 0.0,
        "positive_minutes_saved": 0.0,
        "negative_minutes_cost": 0.0,
        "net_tokens_saved": 0,
        "positive_tokens_saved": 0,
        "negative_tokens_cost": 0,
        "counterfactual_basis_counts": {},
    }


def _dashboard(now: str, rev: str) -> dict[str, object]:
    return {
        "generated_at_utc": now,
        "source_revision": rev,
        "top_verdict": {
            "controlled_first_10_beta": {"verdict": "CONDITIONAL"},
            "broad_public_launch": {"verdict": "NO-GO"},
        },
        "metrics": {
            "max_recommended_real_users_now": {"value": 10},
            "verified_external_users": {"value": 0},
            "measured_savings": {"value": _measured_savings()},
        },
    }


def _pre_package_dashboard(now: str, rev: str) -> dict[str, object]:
    return {
        "generated_at_utc": now,
        "source_revision": rev,
        "top_verdict": {
            "controlled_first_10_beta": {"verdict": "NO-GO"},
            "broad_public_launch": {"verdict": "NO-GO"},
        },
        "metrics": {
            "max_recommended_real_users_now": {"value": 0},
            "verified_external_users": {"value": 0},
            "measured_savings": {"value": _measured_savings()},
        },
    }


def _public_json_files(now: str, rev: str) -> dict[str, dict[str, object]]:
    return {
        "docs/public/status.json": {
            "updated_at": now,
            "state": "NO-GO public self-serve; controlled first-10 beta CONDITIONAL GO while gates remain green",
            "controlled_first_10_beta": {"verdict": "CONDITIONAL"},
            "broad_public_launch": {"verdict": "NO-GO"},
            "max_recommended_real_users_now": 10,
            "verified_external_users": 0,
            "source_revision": rev,
        },
        "docs/public/value.json": {
            "updated_at": now,
            "measured_savings": _measured_savings(),
        },
        "docs/public/impact/impact.json": {
            "updated_at": now,
            "measured_savings": _measured_savings(),
        },
    }


def _pre_package_public_json_files(now: str, rev: str) -> dict[str, dict[str, object]]:
    return {
        "docs/public/status.json": {
            "updated_at": now,
            "state": "NO-GO public self-serve; source/local release-candidate only",
            "controlled_first_10_beta": {"verdict": "NO-GO"},
            "broad_public_launch": {"verdict": "NO-GO"},
            "max_recommended_real_users_now": 0,
            "verified_external_users": 0,
            "source_revision": rev,
        },
        "docs/public/value.json": {
            "updated_at": now,
            "measured_savings": _measured_savings(),
        },
        "docs/public/impact/impact.json": {
            "updated_at": now,
            "measured_savings": _measured_savings(),
        },
    }


def _fresh_aux_snapshots(now: str) -> dict[str, dict[str, object]]:
    return {
        "eval/real_user_rollout_gate_snapshot.json": {"passed": False, "generated_at_utc": now},
        "eval/release_governance_snapshot.json": {
            "passed": False,
            "generated_at_utc": now,
            "repo": "borg-farther/Borg-Directory",
            "branch": "main",
            "required_checks_expected": [],
            "required_checks_observed": [],
            "codeowners_errors_checked": True,
            "blockers": ["main branch is not protected"],
        },
    }


def test_watchdog_allows_only_first_10_external_evidence_as_public_blocker() -> None:
    assert watchdog._public_blockers_are_allowed(["first-10 external-user evidence has not passed"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["verified=0/10"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "first_10_external_evidence") is False
    assert watchdog._public_blockers_are_allowed(
        [
            "PyPI latest metadata does not match source version",
            "PyPI fresh-install + MCP stdio canary snapshot is missing",
            "package-impacting source/metadata changed after the immutable package reference tag",
            "first-10 external-user evidence has not passed",
        ],
        "package_or_first_10_evidence",
    ) is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "package_or_first_10_evidence") is False
    assert watchdog._public_blockers_are_allowed(
        [
            "package-impacting source/metadata changed after the immutable package reference tag",
            "served runtime borg_version '3.3.14' != source version '3.3.15'",
            "main branch is not protected",
            "CODEOWNERS validation has errors: 11",
            "first-10 external-user evidence has not passed",
        ],
        "release_controls_or_first_10_evidence",
    ) is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "release_controls_or_first_10_evidence") is False
    for unsafe in [
        "security incident: MCP stdio token exfiltration detected",
        "privacy blocker: package source includes customer trace data",
    ]:
        assert watchdog._is_package_release_blocker(unsafe) is False
        assert watchdog._public_blockers_are_allowed([unsafe], "release_controls_or_first_10_evidence") is False


def test_source_revision_honesty_accepts_dirty_ancestor_in_clean_pr_checkout(monkeypatch) -> None:
    base = "a" * 40
    head = "b" * 40
    monkeypatch.setattr(watchdog, "_git_is_ancestor", lambda candidate, current: candidate == base and current == head)
    monkeypatch.setattr(watchdog, "_changes_since_source_are_generated_artifacts", lambda candidate, current: candidate == base and current == head)

    assert watchdog._source_revision_is_honest(f"{base}+dirty", head, clean=True) is True
    assert watchdog._source_revision_is_honest(f"{'c' * 40}+dirty", head, clean=True) is False
    assert watchdog._source_revision_is_honest(f"{head}+dirty", head, clean=True) is True
    assert watchdog._source_revision_is_honest(head, head, clean=True) is True
    assert watchdog._source_revision_is_honest(head, head, clean=False) is False


def test_source_revision_honesty_rejects_dirty_ancestor_when_non_generated_files_changed(monkeypatch) -> None:
    base = "a" * 40
    head = "b" * 40
    monkeypatch.setattr(watchdog, "_git_is_ancestor", lambda candidate, current: True)
    monkeypatch.setattr(watchdog, "_changes_since_source_are_generated_artifacts", lambda candidate, current: False)

    assert watchdog._source_revision_is_honest(f"{base}+dirty", head, clean=True) is False


def test_source_revision_honesty_rejects_head_dirty_with_non_generated_worktree(monkeypatch) -> None:
    head = "b" * 40
    monkeypatch.setattr(watchdog, "_git_dirty_paths", lambda: ["eval/borg_proof_dashboard.json", "borg/cli.py"])

    assert watchdog._source_revision_is_honest(f"{head}+dirty", head, clean=False) is False


def test_source_revision_honesty_accepts_head_dirty_with_only_generated_worktree(monkeypatch) -> None:
    head = "b" * 40
    monkeypatch.setattr(watchdog, "_git_dirty_paths", lambda: ["eval/borg_proof_dashboard.json", "docs/status.json"])

    assert watchdog._source_revision_is_honest(f"{head}+dirty", head, clean=False) is True


def test_generated_artifact_change_filter_rejects_source_or_docs_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        watchdog,
        "_git_changed_paths",
        lambda base, head: [
            "eval/borg_proof_dashboard.json",
            "docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md",
            "eval/production_inventory_board_snapshot.json",
            "docs/20260531_BORG_PRODUCTION_INVENTORY_BOARD.md",
            "docs/status.json",
        ],
    )
    assert watchdog._changes_since_source_are_generated_artifacts("a" * 40, "b" * 40) is True

    monkeypatch.setattr(watchdog, "_git_changed_paths", lambda base, head: [])
    assert watchdog._changes_since_source_are_generated_artifacts("a" * 40, "b" * 40) is True

    monkeypatch.setattr(watchdog, "_git_changed_paths", lambda base, head: ["eval/borg_proof_dashboard.json", "README.md"])
    assert watchdog._changes_since_source_are_generated_artifacts("a" * 40, "b" * 40) is False


def test_workflow_command_text_ignores_comments_and_echoed_commands() -> None:
    text = """
name: fake
on:
  schedule:
    - cron: '0 * * * *'
jobs:
  test:
    steps:
      - run: |
          # python eval/run_pypi_fresh_install_canary.py
          echo python eval/cold_start_trust_gate.py
          printf 'python eval/public_self_serve_launch_gate.py'
      - run: python eval/run_pypi_fresh_install_canary.py
"""

    commands = watchdog._workflow_command_text(text)

    assert "python eval/run_pypi_fresh_install_canary.py" in commands
    assert "python eval/cold_start_trust_gate.py" not in commands
    assert "python eval/public_self_serve_launch_gate.py" not in commands


def test_ops_watchdog_compiles_consistent_green_ops_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: _public_snapshot())
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": True,
        "infrastructure_ready_for_100": True,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 10,
        "blockers": ["first-10 external-user evidence has not passed"],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev) | _fresh_aux_snapshots(now)

    def fake_read_json(path: Path) -> dict[str, object]:
        return files.get(str(path.relative_to(watchdog.ROOT)), {})

    monkeypatch.setattr(watchdog, "_read_json", fake_read_json)
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24)

    assert snapshot["passed"] is True
    assert snapshot["ready_for_controlled_first_10_beta"] is True
    assert snapshot["ready_for_public_self_serve_launch"] is False
    assert snapshot["checks"]["snapshot_freshness"]["items"]["self_service_ops_gate_snapshot"]["passed"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["rollback_comms_drill_snapshot"]["passed"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["public_status_json"]["passed"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["public_value_json"]["passed"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["public_impact_json"]["passed"] is True
    assert snapshot["checks"]["public_json_dashboard_consistency"]["passed"] is True
    assert snapshot["blockers"] == []


def test_ops_watchdog_rejects_stale_public_snapshot_blockers(monkeypatch) -> None:
    live_public = _public_snapshot()
    stale_public = live_public | {
        "blockers": [
            "first-10 external-user evidence has not passed",
            "stale prior watchdog blocker that is no longer live",
        ]
    }
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: live_public)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": True,
        "infrastructure_ready_for_100": True,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 10,
        "blockers": ["first-10 external-user evidence has not passed"],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": stale_public | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev) | _fresh_aux_snapshots(now)
    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24)

    assert snapshot["passed"] is False
    assert snapshot["checks"]["public_gate_live_matches_snapshot"]["passed"] is False
    assert any("public_gate_live_matches_snapshot" in blocker for blocker in snapshot["blockers"])


def test_ops_watchdog_accepts_pre_package_release_no_go_stage(monkeypatch) -> None:
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: _pre_package_public_snapshot())
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": False,
        "infrastructure_ready_for_100": False,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 0,
        "blockers": [
            "PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version",
            "PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green",
            "first-10 external-user evidence has not passed: verified=0/10",
        ],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    stale_pypi = "2026-05-23T00:00:00+00:00"
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _pre_package_public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _pre_package_dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.8", "generated_at_utc": stale_pypi, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _pre_package_public_json_files(now, rev) | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 48.0 if value == stale_pypi else 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="package_or_first_10_evidence")

    assert snapshot["passed"] is True
    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["checks"]["pypi_fresh_current"]["pre_package_release_stage"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["pypi_fresh_install_snapshot"]["passed"] is True
    assert snapshot["checks"]["snapshot_freshness"]["items"]["pypi_fresh_install_snapshot"]["raw_freshness_passed"] is False
    assert snapshot["checks"]["snapshot_freshness"]["items"]["pypi_fresh_install_snapshot"]["allowed_stale_reason"] == "pre_package_release_stage_package_proof_already_red"
    assert snapshot["checks"]["real_user_rollout_consistency"]["pre_package_release_stage"] is True
    assert snapshot["checks"]["public_status_consistency"]["pre_package_status_ok"] is True


def test_ops_watchdog_accepts_release_control_blocked_no_go_stage(monkeypatch) -> None:
    blockers = [
        "served runtime borg_version '3.3.14' != source version '3.3.15'",
        "served runtime version_matches_source is not true",
        "main branch is not protected",
        "first-10 external-user evidence has not passed: verified=0/10",
    ]
    public_snapshot = {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "gates": {"pypi_latest": {"passed": True}},
        "blockers": blockers,
    }
    real_snapshot = {
        "ready_for_10_controlled_beta": False,
        "infrastructure_ready_for_100": False,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 0,
        "blockers": blockers,
    }
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: public_snapshot)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: real_snapshot)
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    rev = "a" * 40
    dashboard = _pre_package_dashboard(now, rev)
    metrics = dashboard["metrics"]
    assert isinstance(metrics, dict)
    metrics["served_runtime_freshness_gate"] = {"value": "FAIL"}
    metrics["release_governance_gate"] = {"value": "FAIL"}
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": public_snapshot | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": dashboard,
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
        "docs/public/status.json": {
            "updated_at": now,
            "state": "NO-GO public self-serve; public package proof green, release controls blocked",
            "controlled_first_10_beta": {"verdict": "NO-GO"},
            "broad_public_launch": {"verdict": "NO-GO"},
            "max_recommended_real_users_now": 0,
            "verified_external_users": 0,
            "served_runtime_freshness_gate": "FAIL",
            "release_governance_gate": "FAIL",
            "source_revision": rev,
        },
        "docs/public/value.json": {"updated_at": now, "measured_savings": _measured_savings()},
        "docs/public/impact/impact.json": {"updated_at": now, "measured_savings": _measured_savings()},
    } | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    assert snapshot["passed"] is True
    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is True
    assert snapshot["checks"]["public_status_consistency"]["release_control_blocked_status_ok"] is True


def test_source_revision_honesty_rejects_unrelated_dirty_source_revision(monkeypatch) -> None:
    monkeypatch.setattr(watchdog, "_git_dirty_paths", lambda: ["eval/borg_proof_dashboard.json"])
    assert watchdog._source_revision_is_honest("a" * 40 + "+dirty", "a" * 40, clean=False) is True
    monkeypatch.setattr(watchdog, "_git_dirty_paths", lambda: ["borg/cli.py"])
    assert watchdog._source_revision_is_honest("a" * 40 + "+dirty", "a" * 40, clean=False) is False
    assert watchdog._source_revision_is_honest("c" * 40 + "+dirty", "a" * 40, clean=False) is False


def test_freshness_passed_rejects_future_timestamps() -> None:
    assert watchdog._freshness_passed(1.0, 24.0) is True
    assert watchdog._freshness_passed(24.1, 24.0) is False
    assert watchdog._freshness_passed(-1.0, 24.0) is False
    assert watchdog._freshness_passed(None, 24.0) is False


def test_ops_watchdog_blocks_stale_pypi_snapshot_when_package_gate_is_green(monkeypatch) -> None:
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: _public_snapshot())
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": True,
        "infrastructure_ready_for_100": True,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 10,
        "blockers": ["first-10 external-user evidence has not passed"],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    stale_pypi = "2026-05-23T00:00:00+00:00"
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": stale_pypi, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev) | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 48.0 if value == stale_pypi else 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24)

    pypi_freshness = snapshot["checks"]["snapshot_freshness"]["items"]["pypi_fresh_install_snapshot"]
    assert snapshot["passed"] is False
    assert pypi_freshness["passed"] is False
    assert pypi_freshness["raw_freshness_passed"] is False
    assert pypi_freshness["allowed_stale_reason"] is None
    assert any("snapshot_freshness" in blocker for blocker in snapshot["blockers"])


def test_ops_watchdog_blocks_stale_pypi_snapshot_when_release_controls_are_only_blockers(monkeypatch) -> None:
    blockers = [
        "served runtime borg_version '3.3.14' != source version '3.3.15'",
        "served runtime version_matches_source is not true",
        "main branch is not protected",
        "first-10 external-user evidence has not passed: verified=0/10",
    ]
    public_snapshot = {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "gates": {"pypi_latest": {"passed": True}},
        "blockers": blockers,
    }
    real_snapshot = {
        "ready_for_10_controlled_beta": False,
        "infrastructure_ready_for_100": False,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 0,
        "blockers": blockers,
    }
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: public_snapshot)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: real_snapshot)
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    stale_pypi = "2026-05-23T00:00:00+00:00"
    rev = "a" * 40
    dashboard = _pre_package_dashboard(now, rev)
    metrics = dashboard["metrics"]
    assert isinstance(metrics, dict)
    metrics["served_runtime_freshness_gate"] = {"value": "FAIL"}
    metrics["release_governance_gate"] = {"value": "FAIL"}
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": public_snapshot | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": dashboard,
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": stale_pypi, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
        "docs/public/status.json": {
            "updated_at": now,
            "state": "NO-GO public self-serve; public package proof green, release controls blocked",
            "controlled_first_10_beta": {"verdict": "NO-GO"},
            "broad_public_launch": {"verdict": "NO-GO"},
            "max_recommended_real_users_now": 0,
            "verified_external_users": 0,
            "served_runtime_freshness_gate": "FAIL",
            "release_governance_gate": "FAIL",
            "source_revision": rev,
        },
        "docs/public/value.json": {"updated_at": now, "measured_savings": _measured_savings()},
        "docs/public/impact/impact.json": {"updated_at": now, "measured_savings": _measured_savings()},
    } | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 48.0 if value == stale_pypi else 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    pypi_freshness = snapshot["checks"]["snapshot_freshness"]["items"]["pypi_fresh_install_snapshot"]
    assert snapshot["passed"] is False
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is True
    assert pypi_freshness["passed"] is False
    assert pypi_freshness["allowed_stale_reason"] is None
    assert any("snapshot_freshness" in blocker for blocker in snapshot["blockers"])


def test_ops_watchdog_rejects_release_control_stage_with_stale_pre_package_status(monkeypatch) -> None:
    blockers = [
        "served runtime borg_version '3.3.14' != source version '3.3.15'",
        "main branch is not protected",
        "first-10 external-user evidence has not passed: verified=0/10",
    ]
    public_snapshot = {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "gates": {"pypi_latest": {"passed": True}},
        "blockers": blockers,
    }
    real_snapshot = {
        "ready_for_10_controlled_beta": False,
        "infrastructure_ready_for_100": False,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 0,
        "blockers": blockers,
    }
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: public_snapshot)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: real_snapshot)
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    rev = "a" * 40
    dashboard = _pre_package_dashboard(now, rev)
    metrics = dashboard["metrics"]
    assert isinstance(metrics, dict)
    metrics["served_runtime_freshness_gate"] = {"value": "FAIL"}
    metrics["release_governance_gate"] = {"value": "FAIL"}
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": public_snapshot | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": dashboard,
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _pre_package_public_json_files(now, rev) | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    assert snapshot["passed"] is False
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is True
    assert snapshot["checks"]["public_status_consistency"]["pre_package_status_ok"] is True
    assert snapshot["checks"]["public_status_consistency"]["passed"] is False


def test_ops_watchdog_rejects_release_control_stage_with_unrelated_real_rollout_blocker(monkeypatch) -> None:
    public_blockers = [
        "served runtime borg_version '3.3.14' != source version '3.3.15'",
        "main branch is not protected",
        "first-10 external-user evidence has not passed: verified=0/10",
    ]
    real_blockers = public_blockers + ["10-user load gate is not green"]
    public_snapshot = {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "gates": {"pypi_latest": {"passed": True}},
        "blockers": public_blockers,
    }
    real_snapshot = {
        "ready_for_10_controlled_beta": False,
        "infrastructure_ready_for_100": False,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 0,
        "blockers": real_blockers,
    }
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: public_snapshot)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: real_snapshot)
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    rev = "a" * 40
    dashboard = _pre_package_dashboard(now, rev)
    metrics = dashboard["metrics"]
    assert isinstance(metrics, dict)
    metrics["served_runtime_freshness_gate"] = {"value": "FAIL"}
    metrics["release_governance_gate"] = {"value": "FAIL"}
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": public_snapshot | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": dashboard,
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
        "docs/public/status.json": {
            "updated_at": now,
            "state": "NO-GO public self-serve; public package proof green, release controls blocked",
            "controlled_first_10_beta": {"verdict": "NO-GO"},
            "broad_public_launch": {"verdict": "NO-GO"},
            "max_recommended_real_users_now": 0,
            "verified_external_users": 0,
            "served_runtime_freshness_gate": "FAIL",
            "release_governance_gate": "FAIL",
            "source_revision": rev,
        },
        "docs/public/value.json": {"updated_at": now, "measured_savings": _measured_savings()},
        "docs/public/impact/impact.json": {"updated_at": now, "measured_savings": _measured_savings()},
    } | _fresh_aux_snapshots(now)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    assert snapshot["passed"] is False
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is False


def test_workflow_public_gate_guard_requires_each_blocker_to_be_allowed() -> None:
    text = (watchdog.ROOT / ".github" / "workflows" / "self-service-watchdog.yml").read_text(encoding="utf-8")
    assert "python eval/run_pypi_fresh_install_canary.py" in text
    assert "continuing so public/readiness gates can fail closed with the fresh snapshot" in text
    assert "allowed_public_blockers = all(" in text
    assert "from eval.ops_readiness_watchdog import" in text
    assert "_is_package_release_blocker" in text
    assert "_has_package_release_gap" in text
    assert "_has_release_control_gap" in text
    assert "_has_first_10_gap" in text
    assert "controlled_blocked_by_known_gates" in text
    assert "assert (controlled_package or controlled_blocked_by_known_gates) and allowed_public_blockers" in text
    assert "python scripts/build_borg_proof_dashboard.py" in text
    assert "python scripts/borg_proof_dashboard_lint.py" in text


def test_workflow_regenerates_mutable_evidence_before_dashboard_lint() -> None:
    workflow = watchdog._workflow_has_schedule()
    assert workflow["passed"] is True
    assert workflow["missing"] == []
    assert workflow["order_ok"] is True
    positions = workflow["order_positions"]
    assert positions["python eval/run_pypi_fresh_install_canary.py"] < positions["python eval/public_self_serve_launch_gate.py"]
    assert positions["python eval/run_pypi_fresh_install_canary.py"] < positions["python eval/cold_start_trust_gate.py"]
    assert positions["python eval/cold_start_trust_gate.py"] < positions["python eval/release_governance_gate.py --output eval/release_governance_snapshot.json"]
    assert positions["python eval/release_governance_gate.py --output eval/release_governance_snapshot.json"] < positions["python eval/public_self_serve_launch_gate.py"]
    assert positions["python eval/public_self_serve_launch_gate.py"] < positions["python eval/real_user_rollout_gate.py"]
    assert positions["python eval/real_user_rollout_gate.py"] < positions["python scripts/build_borg_proof_dashboard.py"]
    assert positions["python scripts/build_borg_proof_dashboard.py"] < positions["python eval/ops_readiness_watchdog.py"]
    assert positions["python eval/ops_readiness_watchdog.py"] < positions["python eval/ops_readiness_watchdog.py --mode pr --json --no-write --output eval/ops_readiness_watchdog_post_dashboard_check.json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule"]
    assert positions["python eval/ops_readiness_watchdog.py --mode pr --json --no-write --output eval/ops_readiness_watchdog_post_dashboard_check.json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule"] < positions["python scripts/borg_proof_dashboard_lint.py"]
    assert workflow["sequence_ok"] is True


def test_ops_watchdog_no_write_can_persist_explicit_post_dashboard_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(watchdog, "compile_watchdog", lambda **kwargs: {"passed": True, "blockers": [], "checks": {}})
    output = tmp_path / "post_dashboard.json"

    assert watchdog.main(["--json", "--no-write", "--output", str(output)]) == 0

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True


def test_ops_watchdog_blocks_stale_public_json_even_when_snapshots_are_fresh(monkeypatch) -> None:
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: _public_snapshot())
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": True,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 10,
        "blockers": ["first-10 external-user evidence has not passed"],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)

    now = "2026-05-25T00:00:00+00:00"
    monkeypatch.setattr(watchdog.public_gate, "github_source_install_check", lambda path, expected_version, max_snapshot_age_hours=24.0: _github_source_gate(now, version=expected_version))
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/github_source_install_snapshot.json": _github_source_snapshot(now),
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev) | _fresh_aux_snapshots(now)
    files["docs/public/status.json"] = files["docs/public/status.json"] | {"updated_at": "2020-01-01T00:00:00Z"}

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24)

    assert snapshot["passed"] is False
    assert any("public_json_dashboard_consistency" in blocker for blocker in snapshot["blockers"])


def test_ops_watchdog_blocks_stale_or_non_evidence_public_blockers(monkeypatch) -> None:
    bad_public = _public_snapshot() | {"blockers": ["self-service ops readiness gate is missing"]}
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True, require_ops_watchdog=True: bad_public)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda require_ops_watchdog=True: {
        "ready_for_10_controlled_beta": True,
        "ready_for_100_real_users": False,
        "max_recommended_real_users_now": 10,
        "blockers": [],
    })
    monkeypatch.setattr(watchdog.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(watchdog, "_workflow_has_schedule", lambda: {"passed": True, "exists": True, "missing": []})
    monkeypatch.setattr(watchdog, "_git_head", lambda: "b" * 40)
    monkeypatch.setattr(watchdog, "_git_clean", lambda: True)
    monkeypatch.setattr(watchdog, "_read_json", lambda path: {})

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24)

    assert snapshot["passed"] is False
    assert any("public_blockers_allowed" in blocker for blocker in snapshot["blockers"])
    assert any("snapshot_freshness" in blocker for blocker in snapshot["blockers"])
