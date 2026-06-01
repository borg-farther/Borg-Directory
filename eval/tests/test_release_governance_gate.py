from __future__ import annotations

import json

from eval import release_governance_gate


def _hard_protection_payload(*, checks: list[str] | None = None) -> dict:
    checks = checks or list(release_governance_gate.DEFAULT_REQUIRED_CHECKS)
    return {
        "protected": True,
        "protection": {
            "required_status_checks": {
                "strict": True,
                "checks": [{"context": context} for context in checks],
            },
            "required_pull_request_reviews": {
                "require_code_owner_reviews": True,
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_last_push_approval": True,
            },
            "enforce_admins": {"enabled": True},
            "required_conversation_resolution": True,
            "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
        },
    }


def test_release_governance_gate_fails_unprotected_main() -> None:
    result = release_governance_gate.evaluate_branch_payload({"protected": False})

    assert result["passed"] is False
    assert "main branch is not protected" in result["blockers"]


def test_release_governance_gate_fails_closed_when_protection_details_missing() -> None:
    result = release_governance_gate.evaluate_branch_payload({"protected": True})

    assert result["passed"] is False
    joined = "\n".join(result["blockers"])
    assert "details are missing" in joined
    assert "missing required checks" in joined
    assert "CODEOWNERS" in joined


def test_release_governance_gate_passes_protected_branch_with_exact_checks_reviews_and_codeowners() -> None:
    result = release_governance_gate.evaluate_branch_payload(
        _hard_protection_payload(),
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["required_checks_observed"] == sorted(release_governance_gate.DEFAULT_REQUIRED_CHECKS)
    assert result["codeowners_errors_checked"] is True


def test_release_governance_gate_accepts_github_enabled_object_shapes() -> None:
    payload = _hard_protection_payload()
    payload["protection"]["required_conversation_resolution"] = {"enabled": True}

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is True
    assert result["required_conversation_resolution"] is True


def test_release_governance_gate_rejects_unexpected_extra_required_checks() -> None:
    payload = _hard_protection_payload(checks=list(release_governance_gate.DEFAULT_REQUIRED_CHECKS) + ["CI"])

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    assert "branch protection has unexpected required checks: CI" in result["blockers"]


def test_release_governance_gate_rejects_bypass_allowances() -> None:
    payload = _hard_protection_payload()
    payload["protection"]["required_pull_request_reviews"]["bypass_pull_request_allowances"] = {
        "users": [{"login": "borg-farther"}],
        "teams": [],
        "apps": [],
    }

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    assert result["bypass_allowances"] == ["pull_request_review_bypass_allowances"]
    assert any("bypass allowances" in blocker for blocker in result["blockers"])


def test_release_governance_gate_rejects_broad_workflow_names_as_required_check_decoys() -> None:
    payload = _hard_protection_payload(
        checks=[
            "CI",
            "Borg Security Gates",
            "Self-service readiness watchdog",
            "Account Reference Firewall",
        ]
    )

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    joined = "\n".join(result["blockers"])
    assert "branch protection missing required checks" in joined
    assert "test (3.10)" in joined
    assert "ops-readiness-watchdog" in joined


def test_release_governance_gate_rejects_substring_check_decoys() -> None:
    payload = _hard_protection_payload(
        checks=[f"fake-{context}-bypass" for context in release_governance_gate.DEFAULT_REQUIRED_CHECKS]
    )

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    assert "branch protection missing required checks" in "\n".join(result["blockers"])


def test_release_governance_gate_fails_missing_hardening_switches() -> None:
    payload = _hard_protection_payload()
    protection = payload["protection"]
    protection["required_status_checks"]["strict"] = False
    protection["required_pull_request_reviews"]["require_code_owner_reviews"] = False
    protection["required_pull_request_reviews"]["required_approving_review_count"] = 0
    protection["required_pull_request_reviews"]["dismiss_stale_reviews"] = False
    protection["required_pull_request_reviews"]["require_last_push_approval"] = False
    protection["enforce_admins"] = {"enabled": False}
    protection["required_conversation_resolution"] = False
    protection["allow_force_pushes"] = {"enabled": True}
    protection["allow_deletions"] = {"enabled": True}

    result = release_governance_gate.evaluate_branch_payload(
        payload,
        codeowners_errors=[],
        require_codeowners_validation=True,
    )

    joined = "\n".join(result["blockers"])
    assert result["passed"] is False
    for expected in [
        "not strict",
        "does not require CODEOWNERS review",
        "fewer than 1 approving review",
        "does not dismiss stale reviews",
        "does not require last-push approval",
        "does not enforce rules for admins",
        "does not require conversation resolution",
        "allows force pushes",
        "allows branch deletion",
    ]:
        assert expected in joined


def test_release_governance_gate_fails_codeowners_errors() -> None:
    result = release_governance_gate.evaluate_branch_payload(
        _hard_protection_payload(),
        codeowners_errors=[{"path": ".github/CODEOWNERS", "line": 1, "kind": "Unknown owner", "message": "bad owner"}],
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    assert result["codeowners_error_count"] == 1
    assert "CODEOWNERS validation has errors: 1" in result["blockers"]


def test_release_governance_gate_requires_codeowners_validation_when_requested() -> None:
    result = release_governance_gate.evaluate_branch_payload(
        _hard_protection_payload(),
        require_codeowners_validation=True,
    )

    assert result["passed"] is False
    assert "CODEOWNERS validation errors were not checked" in result["blockers"]


def test_release_governance_gate_cli_writes_evaluated_snapshot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    snapshot_input = tmp_path / "raw_branch.json"
    snapshot_output = tmp_path / "evaluated_release_governance.json"
    payload = _hard_protection_payload()
    payload["codeowners_errors"] = []

    snapshot_input.write_text(json.dumps(payload), encoding="utf-8")

    rc = release_governance_gate.main(["--snapshot", str(snapshot_input), "--output", str(snapshot_output)])

    assert rc == 0
    evaluated = json.loads(snapshot_output.read_text(encoding="utf-8"))
    assert evaluated["passed"] is True
    assert evaluated["source"] == "snapshot"
    assert evaluated["generated_at_utc"]


def test_release_governance_gate_cli_snapshot_requires_codeowners_validation_proof(tmp_path) -> None:  # type: ignore[no-untyped-def]
    snapshot_input = tmp_path / "raw_branch.json"
    snapshot_output = tmp_path / "evaluated_release_governance.json"
    snapshot_input.write_text(json.dumps(_hard_protection_payload()), encoding="utf-8")

    rc = release_governance_gate.main(["--snapshot", str(snapshot_input), "--output", str(snapshot_output)])

    assert rc == 1
    evaluated = json.loads(snapshot_output.read_text(encoding="utf-8"))
    assert evaluated["passed"] is False
    assert "CODEOWNERS validation errors were not checked" in evaluated["blockers"]


def test_release_governance_gate_cli_writes_fail_closed_snapshot_on_fetch_error(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    snapshot_output = tmp_path / "evaluated_release_governance.json"
    monkeypatch.setattr(release_governance_gate, "fetch_live_branch_payload", lambda repo, branch: (_ for _ in ()).throw(RuntimeError("network down")))

    rc = release_governance_gate.main(["--repo", "borg-farther/Borg-Directory", "--branch", "main", "--output", str(snapshot_output)])

    assert rc == 1
    evaluated = json.loads(snapshot_output.read_text(encoding="utf-8"))
    assert evaluated["passed"] is False
    assert evaluated["source"] == "github_api"
    assert evaluated["generated_at_utc"]
    assert evaluated["required_checks_expected"] == release_governance_gate.DEFAULT_REQUIRED_CHECKS
    assert any("release governance evidence unavailable" in blocker for blocker in evaluated["blockers"])
