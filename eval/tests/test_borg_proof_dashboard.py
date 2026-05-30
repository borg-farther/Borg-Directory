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
    if data["metrics"]["pypi_fresh_install_canary"]["value"] == "PASS":
        assert data["metrics"]["pypi_fresh_install_canary"]["honesty_label"] == "PYPI_FRESH_INSTALL_CURRENT_VERSION"
        assert data["controlled_first_10_beta"]["answer"] == "CONDITIONAL GO"
        assert data["top_verdict"]["controlled_first_10_beta"]["verdict"] == "CONDITIONAL"
        assert "infrastructure and ops guardrails are green" in data["top_verdict"]["controlled_first_10_beta"]["why"]
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
    assert data["metrics"]["host_runtime_split_brain"]["value"] == "NOT_EVALUATED_BY_THIS_BUILD"
    assert "live cutover proof" in data["metrics"]["host_runtime_split_brain"]["provenance"]
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
    assert status["self_service_ops_gate"] in {"PASS", "FAIL", "UNKNOWN"}
    assert status["ops_readiness_watchdog"] in {"PASS", "FAIL", "UNKNOWN"}
    assert "eval/cold_start_trust_gate_snapshot.json" in status["evidence"]
    assert "eval/self_service_ops_gate_snapshot.json" in status["evidence"]
    assert status["controlled_first_10_beta"]["verdict"] in {"NO-GO", "CONDITIONAL"}
    if status["controlled_first_10_beta"]["verdict"] == "CONDITIONAL":
        assert "controlled first-10 beta CONDITIONAL GO while gates remain green" in status["state"]
        assert "source/local release-candidate only" not in status["state"]
        assert "infrastructure and ops guardrails are green" in value["detail"]
    else:
        assert "source/local release-candidate only" in status["state"]
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
