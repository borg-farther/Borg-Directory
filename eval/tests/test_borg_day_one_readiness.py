"""Regression tests for the Borg day-one first-user readiness compiler."""

from __future__ import annotations

from eval.borg_day_one_readiness import compile_snapshot, render_report


def test_day_one_readiness_snapshot_has_truthful_split_verdicts():
    snapshot = compile_snapshot()

    assert snapshot["verdict"]["controlled_first_users"] in {"GO", "NO_GO"}
    assert snapshot["verdict"]["broad_public_production"] == "NO_GO"
    assert "external outcome lift remains unproven" in snapshot["verdict"]["why"] or snapshot["missing_evidence"]


def test_day_one_readiness_requires_rescue_security_and_first_user_evidence():
    snapshot = compile_snapshot()

    for key in [
        "gate_run",
        "uat_scoreboard",
        "security_baseline",
        "readme",
        "rescue_engine",
        "rescue_tests",
        "privacy_scanner",
        "prompt_injection_scanner",
        "privacy_tests",
        "prompt_injection_tests",
    ]:
        assert key in snapshot["evidence_files"]
    assert snapshot["security"]["status"] in {"GREEN_FOR_CONTROLLED_FIRST_USERS", "NO_GO"}
    assert snapshot["value"]["north_star_metric"].startswith("percent of first sessions")


def test_day_one_readiness_report_does_not_overclaim_security_or_utility():
    snapshot = compile_snapshot()
    report = render_report(snapshot).lower()

    assert "controlled first users" in report
    assert "broad public production" in report
    assert "not ready to claim statistically proven external uplift" in report
    assert "zero risk" not in report
    assert "guaranteed secure" not in report
    assert "fully safe" not in report


def test_day_one_readiness_report_surfaces_human_value_path():
    snapshot = compile_snapshot()
    report = render_report(snapshot)

    assert "borg rescue" in report
    assert "ACTION/STOP/VERIFY" in report
    assert "human receipt" in report
