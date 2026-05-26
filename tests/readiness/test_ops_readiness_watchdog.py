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
        "blockers": ["first-10 external-user evidence has not passed"],
    }


def test_watchdog_allows_only_first_10_external_evidence_as_public_blocker() -> None:
    assert watchdog._public_blockers_are_allowed(["first-10 external-user evidence has not passed"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["verified=0/10"], "first_10_external_evidence") is True
    assert watchdog._public_blockers_are_allowed(["self-service ops readiness gate is missing"], "first_10_external_evidence") is False


def test_ops_watchdog_compiles_consistent_green_ops_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True: _public_snapshot())
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda: {
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
    files = {
        "eval/public_self_serve_launch_gate_snapshot.json": _public_snapshot() | {"generated_at_utc": now},
        "docs/public/status.json": {
            "state": "NO-GO public self-serve; controlled first-10 beta GO",
            "controlled_first_10_beta": {"verdict": "CONDITIONAL"},
            "max_recommended_real_users_now": 10,
            "verified_external_users": 0,
            "source_revision": "a" * 40,
        },
        "eval/borg_proof_dashboard.json": {"generated_at_utc": now, "source_revision": "a" * 40},
        "eval/pypi_fresh_install_snapshot.json": {"success": True, "version": "9.9.9", "generated_at_utc": now, "mcp_stdio_canary": {"passed": True}},
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "generated_at_utc": now},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True, "dry_run_only": True, "generated_at_utc": now},
    }

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
    assert snapshot["blockers"] == []


def test_ops_watchdog_blocks_stale_or_non_evidence_public_blockers(monkeypatch) -> None:
    bad_public = _public_snapshot() | {"blockers": ["self-service ops readiness gate is missing"]}
    monkeypatch.setattr(watchdog.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(watchdog.public_gate, "compile_gate", lambda fetch_network=True: bad_public)
    monkeypatch.setattr(watchdog.real_user_rollout_gate, "compile_rollout_gate", lambda: {
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
