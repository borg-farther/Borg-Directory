from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_borg_proof_dashboard_artifacts_exist_and_are_honest():
    json_path = ROOT / "eval" / "borg_proof_dashboard.json"
    md_path = ROOT / "docs" / "BORG_PROOF_DASHBOARD.md"
    html_path = ROOT / "docs" / "BORG_PROOF_DASHBOARD.html"
    public_path = ROOT / "docs" / "public" / "proof-dashboard" / "index.html"
    for path in [json_path, md_path, html_path, public_path]:
        assert path.exists(), path
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["metrics"]["verified_external_users"]["value"] == 0
    assert data["top_verdict"]["broad_public_launch"]["verdict"] == "NO-GO"
    assert data["top_verdict"]["unattended_git_onboarding"]["verdict"] == "NO-GO"
    assert data["anti_hype"]["simulated_users_are_not_real_users"] is True
    assert "Simulated/logical users are not real users" in data["anti_hype"]["text"]
    assert data["first_10_user_scoreboard_template"]["columns"] == [
        "user id/pseudonym",
        "install success",
        "time to first rescue",
        "rescue useful yes/no",
        "MCP setup success",
        "blocker",
        "outcome recorded",
    ]
    assert len(data["first_10_user_scoreboard_template"]["rows"]) >= 10
    for row in data["evidence"]:
        assert row["path"]
        assert "exists" in row
        assert row["claim_derived"]
        if row["exists"]:
            assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])


def test_borg_proof_dashboard_markdown_required_sections():
    md = (ROOT / "docs" / "BORG_PROOF_DASHBOARD.md").read_text(encoding="utf-8")
    for heading in [
        "## Big top verdict",
        "## Metrics with provenance and honesty labels",
        "## Evidence table",
        "## Blockers",
        "## First-10-user scoreboard template",
        "## Anti-hype section",
        "## Next action queue before sharing Git with first user",
    ]:
        assert heading in md
