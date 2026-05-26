from __future__ import annotations

import json
from pathlib import Path

from eval import real_user_rollout_gate as rollout_gate

ROOT = Path(__file__).resolve().parents[2]


def test_real_user_rollout_gate_script_exists_and_mentions_no_fake_users() -> None:
    path = ROOT / "eval" / "real_user_rollout_gate.py"
    text = path.read_text(encoding="utf-8")
    assert "real_user_rollout" in text
    assert "no_fake_user_policy" in text
    assert "first-10 external-user evidence" in text


def test_real_user_rollout_gate_blocks_100_when_first_10_scoreboard_empty(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(rollout_gate, "SNAPSHOT", tmp_path / "real_user_rollout_gate_snapshot.json")
    monkeypatch.setattr(rollout_gate, "REPORT", tmp_path / "20260517_BORG_100_REAL_USER_READINESS.md")

    monkeypatch.setattr(rollout_gate, "_ops_ready", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    assert rollout_gate.main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_for_100_real_users"] is False
    assert payload["max_recommended_real_users_now"] in {0, 10}
    assert any("first-10 external-user evidence" in b for b in payload["blockers"])

    package_blocked = any("PyPI latest/fresh-install package evidence" in b for b in payload["blockers"])
    if package_blocked:
        assert payload["ready_for_10_controlled_beta"] is False
        assert payload["infrastructure_ready_for_100"] is False
        assert payload["max_recommended_real_users_now"] == 0
    else:
        assert payload["ready_for_10_controlled_beta"] is True
        assert payload["infrastructure_ready_for_100"] is True
        assert payload["max_recommended_real_users_now"] == 10


def test_real_user_rollout_gate_snapshot_is_machine_readable() -> None:
    path = ROOT / "eval" / "real_user_rollout_gate_snapshot.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["gate_type"] == "real_user_rollout"
    assert data["important_distinction"].startswith("load/readiness snapshots are synthetic")
    assert data["max_recommended_real_users_now"] in {0, 10, 100}
    assert data["no_fake_user_policy"].startswith("Do not mark first-10 complete")


def test_real_user_rollout_gate_blocks_controlled_beta_when_public_package_path_fails(monkeypatch) -> None:
    monkeypatch.setattr(rollout_gate, "_version_consistent", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_security_ready", lambda: {"passed": True, "missing": []})
    monkeypatch.setattr(rollout_gate, "_first_user_release_ready", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_load_ready", lambda users: {"passed": True, "users": users})
    monkeypatch.setattr(rollout_gate, "_first_10_evidence", lambda: {
        "passed": False,
        "verified_external_users": 0,
        "real_users": 0,
        "install_successes": 0,
        "useful_rescue_moments": 0,
        "critical_privacy_security_failures": 0,
        "required_total_real_users": 10,
        "required_install_successes": 8,
        "required_useful_rescue_moments": 6,
        "max_critical_privacy_security_failures": 0,
        "row_level_blockers": [],
    })
    monkeypatch.setattr(rollout_gate, "_public_package_ready", lambda: {
        "passed": False,
        "blockers": ["PyPI latest/fresh-install package evidence is not green"],
    })
    monkeypatch.setattr(rollout_gate, "_ops_ready", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})

    snapshot = rollout_gate.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is False
    assert snapshot["infrastructure_ready_for_100"] is False
    assert snapshot["ready_for_100_real_users"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert "PyPI latest/fresh-install package evidence is not green" in snapshot["blockers"]


def test_real_user_rollout_gate_blocks_controlled_beta_when_ops_readiness_fails(monkeypatch) -> None:
    monkeypatch.setattr(rollout_gate, "_version_consistent", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_security_ready", lambda: {"passed": True, "missing": []})
    monkeypatch.setattr(rollout_gate, "_first_user_release_ready", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_load_ready", lambda users: {"passed": True, "users": users})
    monkeypatch.setattr(rollout_gate, "_public_package_ready", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(rollout_gate, "_ops_ready", lambda: {"passed": False, "blockers": ["support SLA missing"], "rollout_policy": "test"})
    monkeypatch.setattr(rollout_gate, "_first_10_evidence", lambda: {
        "passed": False,
        "verified_external_users": 0,
        "real_users": 0,
        "install_successes": 0,
        "useful_rescue_moments": 0,
        "critical_privacy_security_failures": 0,
        "required_total_real_users": 10,
        "required_install_successes": 8,
        "required_useful_rescue_moments": 6,
        "max_critical_privacy_security_failures": 0,
        "row_level_blockers": [],
    })

    snapshot = rollout_gate.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["self_service_ops_gate"]["passed"] is False
    assert "support SLA missing" in snapshot["blockers"]


def test_real_user_rollout_gate_pauses_controlled_beta_when_first_10_privacy_incident_reported(monkeypatch) -> None:
    monkeypatch.setattr(rollout_gate, "_version_consistent", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_security_ready", lambda: {"passed": True, "missing": []})
    monkeypatch.setattr(rollout_gate, "_first_user_release_ready", lambda: {"passed": True})
    monkeypatch.setattr(rollout_gate, "_load_ready", lambda users: {"passed": True, "users": users})
    monkeypatch.setattr(rollout_gate, "_public_package_ready", lambda: {"passed": True, "blockers": []})
    monkeypatch.setattr(rollout_gate, "_ops_ready", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    monkeypatch.setattr(rollout_gate, "_first_10_evidence", lambda: {
        "passed": False,
        "verified_external_users": 1,
        "real_users": 1,
        "install_successes": 1,
        "useful_rescue_moments": 1,
        "critical_privacy_security_failures": 1,
        "required_total_real_users": 10,
        "required_install_successes": 8,
        "required_useful_rescue_moments": 6,
        "max_critical_privacy_security_failures": 0,
        "row_level_blockers": [],
    })

    snapshot = rollout_gate.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is False
    assert snapshot["first_10_privacy_security_incident_pause_clear"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert any("privacy/security incident" in blocker for blocker in snapshot["blockers"])


def test_first_10_evidence_is_derived_from_rows_not_aggregate_counts(monkeypatch) -> None:
    fake_scoreboard = {
        "truth_policy": {"verified_external_users": 10},
        "thresholds": {
            "min_install_successes_for_public_self_serve": 8,
            "min_useful_rescue_moments_for_public_self_serve": 6,
            "max_critical_privacy_security_failures": 0,
            "required_total_real_users": 10,
        },
        "rows": [],
        "current_counts": {
            "real_users": 10,
            "install_successes": 10,
            "useful_rescue_moments": 10,
            "critical_privacy_security_failures": 0,
            "repeat_use_within_7_days": 10,
        },
        "current_verdict": {"first_10_complete": True, "public_self_serve_launch_gate": "READY"},
    }

    monkeypatch.setattr(rollout_gate, "_read_json", lambda path: fake_scoreboard)

    result = rollout_gate._first_10_evidence()

    assert result["passed"] is False
    assert result["verified_external_users"] == 0
    assert result["real_users"] == 0
    assert result["stored_consistency"]["passed"] is False
