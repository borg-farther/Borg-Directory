from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from scripts import build_borg_proof_dashboard as dashboard

ROOT = Path(__file__).resolve().parents[2]


def test_borg_proof_dashboard_artifacts_exist_and_are_honest(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    eval_dir = tmp_path / "eval"
    public = docs / "public" / "proof-dashboard"
    monkeypatch.setattr(dashboard, "DOCS", docs)
    monkeypatch.setattr(dashboard, "EVAL", eval_dir)
    monkeypatch.setattr(dashboard, "PUBLIC", public)
    monkeypatch.setattr(dashboard, "JSON_OUT", eval_dir / "borg_proof_dashboard.json")
    monkeypatch.setattr(dashboard, "MD_OUT", docs / "BORG_PROOF_DASHBOARD.md")
    monkeypatch.setattr(dashboard, "HTML_OUT", docs / "BORG_PROOF_DASHBOARD.html")
    monkeypatch.setattr(dashboard, "PUBLIC_OUT", public / "index.html")
    monkeypatch.setattr(dashboard, "PUBLIC_STATUS_OUT", docs / "public" / "status.json")
    monkeypatch.setattr(dashboard, "PUBLIC_VALUE_OUT", docs / "public" / "value.json")
    monkeypatch.setattr(dashboard, "PUBLIC_IMPACT_OUT", docs / "public" / "impact" / "impact.json")

    assert dashboard.main() == 0

    json_path = dashboard.JSON_OUT
    md_path = dashboard.MD_OUT
    html_path = dashboard.HTML_OUT
    public_path = dashboard.PUBLIC_OUT
    status_path = dashboard.PUBLIC_STATUS_OUT
    value_path = dashboard.PUBLIC_VALUE_OUT
    impact_path = dashboard.PUBLIC_IMPACT_OUT
    for path in [json_path, md_path, html_path, public_path, status_path, value_path, impact_path]:
        assert path.exists(), path
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["repo"] == "https://github.com/borg-farther/Borg-Directory"
    assert re.fullmatch(r"[0-9a-f]{40}(?:\+dirty)?", data["source_revision"])
    if data["metrics"]["pypi_package_current_gate"]["value"] == "PASS":
        assert data["metrics"]["pypi_package_current_gate"]["honesty_label"] == "PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE"
        release_and_ops_green = all(
            data["metrics"][name]["value"] == "PASS"
            for name in [
                "served_runtime_freshness_gate",
                "release_governance_gate",
                "self_service_ops_gate",
                "ops_readiness_watchdog",
                "rollback_comms_drill",
            ]
        )
        if release_and_ops_green:
            assert data["controlled_first_10_beta"]["answer"] == "CONDITIONAL GO"
            assert data["top_verdict"]["controlled_first_10_beta"]["verdict"] == "CONDITIONAL"
            assert "served-runtime freshness, release governance, and ops guardrails are green" in data["top_verdict"]["controlled_first_10_beta"]["why"]
        else:
            assert data["controlled_first_10_beta"]["answer"] == "NO-GO"
            assert data["top_verdict"]["controlled_first_10_beta"]["verdict"] == "NO-GO"
            why = data["top_verdict"]["controlled_first_10_beta"]["why"]
            expected_missing_terms = []
            if data["metrics"]["served_runtime_freshness_gate"]["value"] != "PASS":
                expected_missing_terms.append("served-runtime freshness")
            if data["metrics"]["release_governance_gate"]["value"] != "PASS":
                expected_missing_terms.append("release governance")
            if data["metrics"]["self_service_ops_gate"]["value"] != "PASS":
                expected_missing_terms.append("self-service ops gate")
            if data["metrics"]["ops_readiness_watchdog"]["value"] != "PASS":
                expected_missing_terms.append("ops watchdog")
            if data["metrics"]["rollback_comms_drill"]["value"] != "PASS":
                expected_missing_terms.append("rollback/comms drill")
            assert expected_missing_terms
            for term in expected_missing_terms:
                assert term in why
    else:
        assert data["controlled_first_10_beta"]["answer"] == "NO-GO"
        assert data["top_verdict"]["controlled_first_10_beta"]["verdict"] == "NO-GO"
        assert "PyPI latest" in data["top_verdict"]["controlled_first_10_beta"]["why"]
    assert data["metrics"]["verified_external_users"]["value"] == 0
    assert data["metrics"]["cold_start_trust_hardening_gate"]["honesty_label"] == "FIRST_ANSWER_TRUST_GATE"
    assert data["metrics"]["self_service_ops_gate"]["honesty_label"] == "SELF_SERVICE_OPS_GATE"
    assert data["metrics"]["first_10_privacy_security_incidents"]["value"] == 0
    assert data["metrics"]["first_10_privacy_security_incidents"]["honesty_label"] == "ROW_DERIVED_EXTERNAL_USER_RISK"
    assert data["metrics"]["ops_readiness_watchdog"]["honesty_label"] == "OPS_PROOF_FRESHNESS_GATE"
    assert data["metrics"]["rollback_comms_drill"]["honesty_label"] == "DRY_RUN_ROLLBACK_COMMS_DRILL"
    assert data["metrics"]["host_runtime_split_brain"]["value"] == data["metrics"]["served_runtime_freshness_gate"]["value"]
    assert data["metrics"]["host_runtime_split_brain"]["honesty_label"] == "SERVED_RUNTIME_EVIDENCE"
    assert "eval/served_runtime_fingerprint_snapshot.json" in data["metrics"]["host_runtime_split_brain"]["provenance"]
    assert data["top_verdict"]["broad_public_launch"]["verdict"] == "NO-GO"
    assert data["top_verdict"]["unattended_git_onboarding"]["verdict"] == "NO-GO"
    assert data["anti_hype"]["simulated_users_are_not_real_users"] is True
    assert "Simulated/logical users are not real users" in data["anti_hype"]["text"]
    status = json.loads(status_path.read_text(encoding="utf-8"))
    value = json.loads(value_path.read_text(encoding="utf-8"))
    impact = json.loads(impact_path.read_text(encoding="utf-8"))
    assert status["updated_at"] == data["generated_at_utc"]
    assert value["updated_at"] == data["generated_at_utc"]
    assert impact["updated_at"] == data["generated_at_utc"]
    assert status["source_revision"] == data["source_revision"]
    assert status["controlled_first_10_beta"] == data["top_verdict"]["controlled_first_10_beta"]
    assert status["broad_public_launch"] == data["top_verdict"]["broad_public_launch"]
    assert status["repo"] == "https://github.com/borg-farther/Borg-Directory"
    assert status["state"].startswith("NO-GO public self-serve")
    assert status["cold_start_trust_hardening_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["served_runtime_freshness_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["release_governance_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["release_controls_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["self_service_ops_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["ops_readiness_watchdog"] in {"PASS", "FAIL", "UNKNOWN"}
    assert "eval/cold_start_trust_gate_snapshot.json" in status["evidence"]
    assert "eval/served_runtime_fingerprint_snapshot.json" in status["evidence"]
    assert "eval/release_governance_snapshot.json" in status["evidence"]
    assert "eval/self_service_ops_gate_snapshot.json" in status["evidence"]
    assert status["controlled_first_10_beta"]["verdict"] in {"NO-GO", "CONDITIONAL"}
    if status["controlled_first_10_beta"]["verdict"] == "CONDITIONAL":
        assert "controlled first-10 beta CONDITIONAL GO while gates remain green" in status["state"]
        assert "source/local release-candidate only" not in status["state"]
        assert "served-runtime, release-governance, and ops guardrails are green" in value["detail"]
    else:
        assert status["state"] in {
            "NO-GO public self-serve; source/local release-candidate only",
            "NO-GO public self-serve; public package proof green, release controls blocked",
            "NO-GO public self-serve; PyPI runtime canary green, package metadata stale",
        }
        if data["metrics"]["pypi_package_current_gate"]["value"] == "PASS":
            assert "public package proof green" in status["state"]
        else:
            assert (
                "source/local release-candidate only" in status["state"]
                or "PyPI runtime canary green, package metadata stale" in status["state"]
            )
    assert "ACTION / STOP / VERIFY" in value["headline"]
    assert "measured_savings" in value
    assert value["measured_savings"]["rows_with_measured_value"] == 0
    assert value["measured_savings"]["net_minutes_saved"] == 0.0
    assert value["measured_savings"]["net_tokens_saved"] == 0
    assert value["value_honesty_label"] == "ROW_DERIVED_EXTERNAL_USER_SAVINGS_REQUIRED"
    assert impact["primary_impact"] == "NO-GO public self-serve"
    assert data["first_10_user_scoreboard_template"]["columns"] == [
        "user id/pseudonym",
        "install success",
        "time to first rescue",
        "rescue useful yes/no",
        "MCP setup success",
        "blocker",
        "outcome recorded",
        "baseline minutes without Borg",
        "actual minutes with Borg",
        "net minutes saved",
        "baseline tokens without Borg",
        "actual tokens with Borg",
        "net tokens saved",
        "savings counterfactual basis",
        "dead end avoided confirmed",
        "user confirmed value",
    ]
    assert len(data["first_10_user_scoreboard_template"]["rows"]) >= 10
    for row in data["evidence"]:
        assert row["path"]
        assert row["path"] not in {"PROJECT_STATUS.md", "GO_NO_GO_DECISION.md", "UAT_RESULTS.md", "ROADMAP.md"}
        assert "exists" in row
        assert row["claim_derived"]
        if row["exists"]:
            assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
            source_path = ROOT / row["path"]
            assert source_path.exists(), row["path"]
            expected = hashlib.sha256(source_path.read_bytes()).hexdigest()
            assert row["sha256"] == expected, row["path"]


def test_borg_proof_dashboard_markdown_required_sections():
    md = (ROOT / "docs" / "BORG_PROOF_DASHBOARD.md").read_text(encoding="utf-8")
    for heading in [
        "## Big top verdict",
        "## Metrics with provenance and honesty labels",
        "## Evidence table",
        "## Blockers",
        "## First-10-user scoreboard template",
        "## Anti-hype section",
        "## Next action queue before controlled first-10 beta testers",
    ]:
        assert heading in md
    assert "Controlled first-10 beta only?" in md
    assert "Supervised source checkout only?" not in md
    assert "Next action queue before supervised first user" not in md
    assert "Repo: `/root/" not in md


def test_public_payload_does_not_call_package_green_when_pypi_latest_alignment_fails():
    model = {
        "generated_at_utc": "2026-05-31T11:40:00Z",
        "repo": "https://github.com/borg-farther/Borg-Directory",
        "source_revision": "abcdef1234567890abcdef1234567890abcdef12",
        "top_verdict": {
            "controlled_first_10_beta": {"verdict": "NO-GO", "why": "package gate failed"},
            "broad_public_launch": {"verdict": "NO-GO", "why": "package gate failed"},
            "local_release_candidate": {"verdict": "CONDITIONAL", "why": "local source is green"},
        },
        "blockers": {},
        "metrics": {
            "pypi_fresh_install_canary": {"value": "PASS"},
            "pypi_package_current_gate": {"value": "FAIL"},
            "max_recommended_real_users_now": {"value": 0},
            "verified_external_users": {"value": 0},
            "measured_savings": {"value": {}},
        },
    }

    status, value, _impact = dashboard.build_public_payloads(model)

    assert status["state"] == "NO-GO public self-serve; PyPI runtime canary green, package metadata stale"
    assert "public package proof green" not in status["state"]
    assert "fresh PyPI install/runtime canary passes" in value["detail"]
    assert "metadata/source alignment is not current proof" in value["detail"]


def _minimal_dashboard_files(pypi_snapshot: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        "eval/first_user_release_gate_snapshot.json": {"all_pass": True},
        "eval/uat_scoreboard_snapshot.json": {"synthetic_load_all_pass": True},
        "eval/gate_run_snapshot.json": {"synthetic_load_all_pass": True},
        "eval/real_user_rollout_gate_snapshot.json": {
            "ready_for_100_real_users": False,
            "blockers": [],
            "release_controls_gate": {"passed": False},
        },
        "eval/public_self_serve_launch_gate_snapshot.json": {
            "ready_for_public_self_serve_launch": False,
            "gates": {"pypi_latest": {"passed": True}},
        },
        "eval/cold_start_trust_gate_snapshot.json": {"passed": True},
        "eval/self_service_ops_gate_snapshot.json": {"passed": True, "blockers": []},
        "eval/ops_readiness_watchdog_snapshot.json": {"passed": True},
        "eval/rollback_comms_drill_snapshot.json": {"passed": True},
        "eval/pypi_fresh_install_snapshot.json": pypi_snapshot,
    }


def test_dashboard_requires_mcp_stdio_canary_for_pypi_package_current(monkeypatch):
    from eval import self_service_ops_gate

    files = _minimal_dashboard_files({
        "success": True,
        "version": "9.9.9",
        "generated_at_utc": "fresh",
        "mcp_stdio_canary": {"passed": False},
    })
    monkeypatch.setattr(dashboard, "load_json", lambda rel: files.get(rel))
    monkeypatch.setattr(dashboard, "pyproject_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "init_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "current_commit", lambda: "a" * 40)
    monkeypatch.setattr(dashboard, "pack_count", lambda: 1)
    monkeypatch.setattr(dashboard, "age_hours", lambda value: 1.0)
    monkeypatch.setattr(self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})

    model = dashboard.build_model()

    assert model["metrics"]["pypi_fresh_install_canary"]["value"] == "FAIL"
    assert model["metrics"]["pypi_package_current_gate"]["value"] == "FAIL"
    first_action = model["next_action_queue_before_sharing_git_with_first_user"][0]
    assert "rerun or fix the fresh-install + stdio MCP canary for immutable `agent-borg==9.9.9`" in first_action
    assert "publish immutable `agent-borg==9.9.9`" not in first_action


def test_dashboard_rejects_future_pypi_canary_timestamp_for_package_current(monkeypatch):
    from eval import self_service_ops_gate

    files = _minimal_dashboard_files({
        "success": True,
        "version": "9.9.9",
        "generated_at_utc": "future",
        "mcp_stdio_canary": {"passed": True},
    })
    monkeypatch.setattr(dashboard, "load_json", lambda rel: files.get(rel))
    monkeypatch.setattr(dashboard, "pyproject_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "init_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "current_commit", lambda: "a" * 40)
    monkeypatch.setattr(dashboard, "pack_count", lambda: 1)
    monkeypatch.setattr(dashboard, "age_hours", lambda value: -1.0)
    monkeypatch.setattr(self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})

    model = dashboard.build_model()

    assert model["metrics"]["pypi_fresh_install_canary"]["value"] == "FAIL"
    assert model["metrics"]["pypi_package_current_gate"]["value"] == "FAIL"


def test_dashboard_requires_fresh_pypi_canary_for_pypi_package_current(monkeypatch):
    from eval import self_service_ops_gate

    files = _minimal_dashboard_files({
        "success": True,
        "version": "9.9.9",
        "generated_at_utc": "stale",
        "mcp_stdio_canary": {"passed": True},
    })
    monkeypatch.setattr(dashboard, "load_json", lambda rel: files.get(rel))
    monkeypatch.setattr(dashboard, "pyproject_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "init_version", lambda: "9.9.9")
    monkeypatch.setattr(dashboard, "current_commit", lambda: "a" * 40)
    monkeypatch.setattr(dashboard, "pack_count", lambda: 1)
    monkeypatch.setattr(dashboard, "age_hours", lambda value: 48.0)
    monkeypatch.setattr(self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": []})

    model = dashboard.build_model()

    assert model["metrics"]["pypi_fresh_install_canary"]["value"] == "FAIL"
    assert model["metrics"]["pypi_package_current_gate"]["value"] == "FAIL"
