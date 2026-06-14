from __future__ import annotations

import json
from pathlib import Path

from eval import rollback_comms_drill
from eval import self_service_ops_gate as gate

ROOT = Path(__file__).resolve().parents[2]


def _use_fresh_drill_snapshot(monkeypatch, tmp_path) -> None:
    """Regenerate the time-sensitive rollback-drill snapshot fresh and point the
    gate at it, so the gate's <=24h freshness check is HERMETIC rather than
    dependent on the wall-clock age of the committed snapshot.

    Without this, these tests fail on any branch whose committed
    rollback_comms_drill_snapshot.json is >24h old — the documented footgun in
    OPERATOR_ACTIONS.md ("committed drill/ops-gate snapshots age out after 24h,
    so ANY PR branch older than a day fails the test matrix"). run_drill() is
    offline and side-effect-free, so this is the prescribed "regenerate in CI"
    fix applied at test time.
    """
    snap = rollback_comms_drill.run_drill()
    fresh = tmp_path / "rollback_comms_drill_snapshot.json"
    fresh.write_text(json.dumps(snap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = dict(gate.REQUIRED_STATIC_FILES)
    files["rollback_drill_snapshot"] = fresh  # absolute path overrides ROOT / value
    monkeypatch.setattr(gate, "REQUIRED_STATIC_FILES", files)


def test_self_service_ops_gate_script_and_artifacts_are_present(monkeypatch, tmp_path) -> None:
    _use_fresh_drill_snapshot(monkeypatch, tmp_path)
    snapshot = gate.compile_gate()

    assert snapshot["gate_type"] == "self_service_ops_readiness"
    assert snapshot["passed"] is True
    assert "broad public self-serve" in snapshot["rollout_policy"]
    assert "necessary but not sufficient" in snapshot["rollout_policy"]
    assert "served-runtime freshness" in snapshot["rollout_policy"]
    assert snapshot["checks"]["issue_templates"]["bad_answer"]["passed"] is True
    assert snapshot["checks"]["issue_templates"]["first_10_evidence"]["passed"] is True
    assert snapshot["checks"]["static_files"]["codeowners"]["passed"] is True
    assert snapshot["checks"]["static_files"]["codeowners"]["contains_banned_owner"] is False
    assert snapshot["checks"]["static_files"]["watchdog_workflow"]["passed"] is True
    workflow_text = (ROOT / ".github" / "workflows" / "self-service-watchdog.yml").read_text(encoding="utf-8")
    assert "--max-snapshot-age-hours 24" in workflow_text
    assert "--max-snapshot-age-hours 168" not in workflow_text
    assert "python eval/run_pypi_fresh_install_canary.py" in workflow_text
    assert "python eval/cold_start_trust_gate.py" in workflow_text
    assert "python eval/release_governance_gate.py --output eval/release_governance_snapshot.json" in workflow_text
    assert "python eval/real_user_rollout_gate.py" in workflow_text
    assert "python scripts/build_borg_proof_dashboard.py" in workflow_text
    assert workflow_text.index("python eval/run_pypi_fresh_install_canary.py") < workflow_text.index("python eval/cold_start_trust_gate.py")
    assert workflow_text.index("python eval/cold_start_trust_gate.py") < workflow_text.index("python eval/release_governance_gate.py --output eval/release_governance_snapshot.json")
    assert workflow_text.index("python eval/release_governance_gate.py --output eval/release_governance_snapshot.json") < workflow_text.index("python eval/public_self_serve_launch_gate.py")
    post_dashboard_check = "python eval/ops_readiness_watchdog.py --mode pr --json --no-write --output eval/ops_readiness_watchdog_post_dashboard_check.json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule"
    assert post_dashboard_check in workflow_text
    first_dashboard_build = workflow_text.index("python scripts/build_borg_proof_dashboard.py")
    first_watchdog = workflow_text.index("python eval/ops_readiness_watchdog.py")
    final_dashboard_build = workflow_text.rindex("python scripts/build_borg_proof_dashboard.py")
    assert workflow_text.index("python eval/real_user_rollout_gate.py") < first_dashboard_build
    assert first_dashboard_build < first_watchdog
    assert first_watchdog < final_dashboard_build
    assert final_dashboard_build < workflow_text.index(post_dashboard_check)
    assert workflow_text.index(post_dashboard_check) < workflow_text.index("python scripts/borg_proof_dashboard_lint.py")
    assert snapshot["checks"]["bad_answer_feedback_path"]["feedback_path"]["passed"] is True


def test_codeowners_static_check_parses_exact_owner_tokens(tmp_path: Path) -> None:
    codeowners = tmp_path / "CODEOWNERS"
    codeowners.write_text(
        "# * @borg-farther/maintainers is invalid but this comment must not count\n"
        "* @borg-farther\n",
        encoding="utf-8",
    )

    result = gate._codeowners_file_check(codeowners)

    assert result["passed"] is True
    assert result["contains_required_owner"] is True
    assert result["contains_banned_owner"] is False
    assert result["invalid_owner_tokens"] == []


def test_codeowners_static_check_rejects_partial_or_teamlike_borg_farther_tokens(tmp_path: Path) -> None:
    codeowners = tmp_path / "CODEOWNERS"
    codeowners.write_text("* @borg-farther @borg-farther/maintainers @borg-fartherly\n", encoding="utf-8")

    result = gate._codeowners_file_check(codeowners)

    assert result["passed"] is False
    assert result["contains_banned_owner"] is True
    assert result["invalid_owner_tokens"] == ["@borg-farther/maintainers", "@borg-fartherly"]


def test_bad_answer_feedback_path_uses_shipped_paths_not_borg_rate() -> None:
    feedback = gate.compile_gate()["checks"]["bad_answer_feedback_path"]["feedback_path"]

    assert feedback["passed"] is True
    assert feedback["banned_hits"] == []
    assert feedback["missing_required_tokens"] == []
    combined = "\n".join((ROOT / rel).read_text(encoding="utf-8", errors="replace") for rel in [
        "docs/COLD_START_TRUST_HARDENING.md",
        "eval/cold_start_trust_gate_snapshot.json",
        ".github/ISSUE_TEMPLATE/bad-answer.yml",
        "docs/SELF_SERVICE_OPS_READINESS.md",
    ])
    assert "borg_record_failure" in combined
    assert "bad-answer.yml" in combined
    assert "borg_rate" not in combined


def test_issue_templates_capture_recovery_critical_fields() -> None:
    snapshot = gate.compile_gate()
    templates = snapshot["checks"]["issue_templates"]

    assert templates["bad_answer"]["missing_fields"] == []
    assert templates["bad_answer"]["has_secret_redaction_warning"] is True
    assert templates["first_10_evidence"]["missing_fields"] == []
    assert templates["install_mcp_support"]["missing_fields"] == []


def test_self_service_ops_gate_cli_writes_machine_snapshot(tmp_path, monkeypatch, capsys) -> None:
    _use_fresh_drill_snapshot(monkeypatch, tmp_path)
    snapshot_path = tmp_path / "self_service_ops_gate_snapshot.json"
    report_path = tmp_path / "SELF_SERVICE_OPS_READINESS_REPORT.md"
    monkeypatch.setattr(gate, "SNAPSHOT", snapshot_path)
    monkeypatch.setattr(gate, "REPORT", report_path)

    assert gate.main([]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["passed"] is True
    assert snapshot_path.exists()
    assert report_path.exists()
    saved = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert saved["passed"] is True
    assert saved["checks"]["static_files"]["rollback_drill_snapshot"]["passed"] is True
