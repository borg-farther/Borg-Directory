from __future__ import annotations

from eval.public_gate_ci_policy import evaluate_expected_fail_closed_state


def _snapshot(*, blockers: list[object], controlled: bool = False, max_users: int = 0) -> dict[str, object]:
    return {
        "ready_for_public_self_serve_launch": False,
        "ready_for_controlled_first_10_beta": controlled,
        "max_recommended_real_users_now": max_users,
        "blockers": blockers,
    }


def test_accepts_current_package_source_and_runtime_fail_closed_state() -> None:
    result = evaluate_expected_fail_closed_state(
        _snapshot(
            blockers=[
                "package-impacting source/metadata changed after the immutable package reference tag",
                "served runtime borg_version '3.3.18' != source version '3.4.1'",
                "served runtime source_version '3.3.18' != source version '3.4.1'",
                "protocol: protocol status does not permit enrollment or completed evidence",
                "protocol: protocol artifact version is not locked",
                "protocol: protocol artifact wheel_sha256 is not locked",
                "first-10 external-user evidence has not passed: verified=0/10",
            ]
        )
    )

    assert result["passed"] is True
    assert result["unknown_blockers"] == []
    assert {row["kind"] for row in result["classified_blockers"]} == {
        "package_provenance",
        "release_controls",
        "first_10_evidence",
    }


def test_accepts_controlled_first_10_while_public_launch_stays_closed() -> None:
    result = evaluate_expected_fail_closed_state(
        _snapshot(
            blockers=["first-10 external-user evidence has not passed"],
            controlled=True,
            max_users=10,
        )
    )

    assert result["passed"] is True


def test_rejects_unknown_blocker_instead_of_weakening_watchdog() -> None:
    result = evaluate_expected_fail_closed_state(
        _snapshot(blockers=["core rescue engine crashed during readiness probe"])
    )

    assert result["passed"] is False
    assert result["unknown_blockers"] == ["core rescue engine crashed during readiness probe"]
    assert "unexpected blocker family present" in result["violations"]


def test_rejects_public_go_and_inconsistent_user_cap() -> None:
    data = _snapshot(
        blockers=["first-10 external-user evidence has not passed"],
        controlled=True,
        max_users=0,
    )
    data["ready_for_public_self_serve_launch"] = True

    result = evaluate_expected_fail_closed_state(data)

    assert result["passed"] is False
    assert "public self-serve must remain fail-closed" in result["violations"]
    assert any("inconsistent" in violation for violation in result["violations"])


def test_rejects_empty_or_non_string_blocker_list() -> None:
    empty = evaluate_expected_fail_closed_state(_snapshot(blockers=[]))
    non_string = evaluate_expected_fail_closed_state(_snapshot(blockers=[{"bad": "shape"}]))

    assert empty["passed"] is False
    assert "fail-closed public state must name at least one blocker" in empty["violations"]
    assert non_string["passed"] is False
    assert "all blockers must be strings" in non_string["violations"]
