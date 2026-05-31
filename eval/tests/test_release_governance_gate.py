from __future__ import annotations

from eval import release_governance_gate


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


def test_release_governance_gate_passes_protected_branch_with_reviews_and_checks() -> None:
    payload = {
        "protected": True,
        "protection": {
            "required_status_checks": {
                "checks": [
                    {"context": "CI / test (3.11)"},
                    {"context": "Borg Security Gates"},
                    {"context": "Self-service readiness watchdog"},
                    {"context": "Account Reference Firewall"},
                ]
            },
            "required_pull_request_reviews": {"require_code_owner_reviews": True},
        },
    }

    result = release_governance_gate.evaluate_branch_payload(payload)

    assert result["passed"] is True
    assert result["blockers"] == []


def test_release_governance_gate_fails_missing_required_checks_and_codeowners() -> None:
    payload = {
        "protected": True,
        "protection": {
            "required_status_checks": {"contexts": ["CI"]},
            "required_pull_request_reviews": {"require_code_owner_reviews": False},
        },
    }

    result = release_governance_gate.evaluate_branch_payload(payload)

    assert result["passed"] is False
    joined = "\n".join(result["blockers"])
    assert "missing required checks" in joined
    assert "CODEOWNERS" in joined
