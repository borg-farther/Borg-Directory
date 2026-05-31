from __future__ import annotations

from pathlib import Path

from eval import ops_readiness_watchdog as watchdog


def _public_snapshot() -> dict[str, object]:
    return {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": True,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 10,
        "blockers": ["first-10 external-user evidence has not passed"],
    }


def _pre_package_public_snapshot() -> dict[str, object]:
    return {
        "source_version": "9.9.9",
        "ready_for_controlled_first_10_beta": False,
        "ready_for_public_self_serve_launch": False,
        "max_recommended_real_users_now": 0,
        "blockers": [
            "PyPI latest metadata does not match source version or required project URLs",
            "PyPI fresh-install + MCP stdio canary snapshot is missing or failing",
            "first-10 external-user evidence has not passed: verified=0/10",
        ],
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


def test_watchdog_allows_only_first_10_external_evidence_as_public_blocker() -> None:
    assert watchdog._public_blockers_are_allowed(["first-10 external-user evidence has not passed"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["verified=0/10"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "first_10_external_evidence") is False
    assert watchdog._public_blockers_are_allowed(
        [
            "PyPI latest metadata does not match source version",
            "PyPI fresh-install + MCP stdio canary snapshot is missing",
            "first-10 external-user evidence has not passed",
        ],
        "package_or_first_10_evidence",
    ) is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "package_or_first_10_evidence") is False
    assert watchdog._public_blockers_are_allowed(
        [
            "served runtime borg_version '3.3.14' != source version '3.3.15'",
            "main branch is not protected",
            "first-10 external-user evidence has not passed",
        ],
        "release_controls_or_first_10_evidence",
    ) is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "release_controls_or_first_10_evidence") is False


def test_source_revision_honesty_accepts_dirty_ancestor_in_clean_pr_checkout(monkeypatch) -> None:
    base = "a" * 40
    head = "b" * 40
    monkeypatch.setattr(watchdog, "_git_is_ancestor", lambda candidate, current: candidate == base and current == head)

    assert watchdog._source_revision_is_honest(f"{base}+dirty", head, clean=True) is True
    assert watchdog._source_revision_is_honest(f"{'c' * 40}+dirty", head, clean=True) is False
    assert watchdog._source_revision_is_honest(f"{head}+dirty", head, clean=True) is True
    assert watchdog._source_revision_is_honest(head, head, clean=True) is True


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
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev)

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
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _pre_package_public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _pre_package_dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.8", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _pre_package_public_json_files(now, rev)

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="package_or_first_10_evidence")

    assert snapshot["passed"] is True
    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["checks"]["pypi_fresh_current"]["pre_package_release_stage"] is True
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
    }

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    assert snapshot["passed"] is True
    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is True
    assert snapshot["checks"]["public_status_consistency"]["release_control_blocked_status_ok"] is True


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
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _pre_package_public_json_files(now, rev)

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
    }

    monkeypatch.setattr(watchdog, "_read_json", lambda path: files.get(str(path.relative_to(watchdog.ROOT)), {}))
    monkeypatch.setattr(watchdog, "_age_hours", lambda value: 1.0)

    snapshot = watchdog.compile_watchdog(max_snapshot_age_hours=24, allow_public_blocker="release_controls_or_first_10_evidence")

    assert snapshot["passed"] is False
    assert snapshot["checks"]["real_user_rollout_consistency"]["release_control_blocked_stage"] is False


def test_workflow_public_gate_guard_requires_each_blocker_to_be_allowed() -> None:
    text = (watchdog.ROOT / ".github" / "workflows" / "self-service-watchdog.yml").read_text(encoding="utf-8")
    assert "allowed_public_blockers = all(" in text
    assert "assert (controlled_package or pre_publish or release_controls_blocked) and allowed_public_blockers" in text


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
    rev = "a" * 40
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "eval/borg_proof_dashboard.json": _dashboard(now, rev),
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    } | _public_json_files(now, rev)
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
