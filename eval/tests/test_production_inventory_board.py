from __future__ import annotations

import json
from pathlib import Path

from eval.production_inventory_board import REPORT, SNAPSHOT, compile_inventory, render_markdown


ROOT = Path(__file__).resolve().parents[2]


def _by_id(data: dict, component_id: str) -> dict:
    return next(component for component in data["components"] if component["id"] == component_id)


def test_production_inventory_preserves_split_verdicts() -> None:
    data = compile_inventory()
    verdict = data["top_verdict"]

    assert verdict["published_package_local_stdio"] == "NO_GO"
    if data["source"]["git"]["dirty"]:
        assert verdict["source_package_local_stdio"] == "NO_GO"
        assert verdict["current_source_hardening_branch"] == "IN_PROGRESS"
    else:
        assert verdict["source_package_local_stdio"] == "NO_GO"
        assert verdict["current_source_hardening_branch"] == "CONDITIONAL_GO"
    assert verdict["global_federated_learning_protocol"] == "GO_PROTOCOL_ONLY"
    assert verdict["recursive_collective_learning_mechanism"] == "GO_INTERNAL_ONLY"
    assert verdict["recursive_pack_optimizer"] == "GO_INTERNAL_MANUAL_ONLY"

    assert verdict["controlled_first_10_beta"] == "NO_GO"
    assert verdict["public_self_serve"] == "NO_GO"
    assert verdict["hundred_real_users"] == "NO_GO"
    assert verdict["served_runtime_freshness"] == "NO_GO"
    assert verdict["remote_mcp_distribution"] == "NO_GO"
    assert verdict["served_remote_mcp"] == "NO_GO"
    assert verdict["google_tier_external_lift"] == "NO_GO"

    counts = data["evidence_summary"]["first_10_counts"]
    assert counts["verified_external_users"] == 0
    assert counts["real_users"] == 0
    assert counts["install_successes"] == 0
    assert counts["useful_rescue_moments"] == 0


def test_inventory_surfaces_current_release_control_blockers() -> None:
    data = compile_inventory()

    served = _by_id(data, "served_runtime")
    assert served["status"] == "NO_GO"
    assert any("3.3.14" in blocker and "3.3.15" in blocker for blocker in served["blockers"])
    assert any("reload_status" in blocker for blocker in served["blockers"])

    governance = _by_id(data, "release_governance")
    assert governance["status"] == "NO_GO"
    assert "main branch is not protected" in governance["blockers"]

    controlled = _by_id(data, "controlled_first_10_beta")
    assert controlled["status"] == "NO_GO"
    blocker_text = "\n".join(controlled["blockers"])
    assert "main branch is not protected" in blocker_text
    assert "served runtime" in blocker_text
    ops = _by_id(data, "self_service_ops_watchdog")
    if ops["status"] == "NO_GO":
        assert any(("watchdog" in blocker or "rollback/comms" in blocker or "self-service" in blocker) for blocker in controlled["blockers"])


def test_inventory_keeps_federated_protocol_separate_from_production_ops() -> None:
    data = compile_inventory()

    federated = _by_id(data, "remote_global_federated_protocol")
    assert federated["status"] == "GO_PROTOCOL_ONLY"
    assert any("production hosted registry ops" in item for item in federated["outstanding"])
    assert "Protocol GO is not hosted-registry production ops" in federated["assumption_challenge"]

    loop = _by_id(data, "collective_recursive_learning_loop")
    assert loop["status"] == "GO_INTERNAL_ONLY"
    assert any("prove real external lift" in item for item in loop["outstanding"])

    optimality = _by_id(data, "google_tier_measured_lift")
    assert optimality["status"] == "NO_GO"
    assert any("first-10 external" in blocker or "external outcome" in blocker for blocker in optimality["blockers"])


def test_inventory_markdown_names_the_promised_outstanding_features() -> None:
    data = compile_inventory()
    markdown = render_markdown(data)

    required_phrases = [
        "served/Hermes MCP runtime freshness",
        "GitHub release governance and main-branch protection",
        "first-10 consented external-user evidence",
        "remote/global/federated learning protocol",
        "outcome-grounded collective/recursive learning mechanism",
        "recursive/local pack optimizer",
        "production hosted registry",
        "no Borg vs empty Borg vs seeded Borg",
        "transparency-log anchoring",
        "Protocol GO is not hosted-registry production ops",
    ]
    for phrase in required_phrases:
        assert phrase in markdown


def test_inventory_artifacts_are_machine_readable_and_report_is_honest() -> None:
    # The generator writes these artifacts; this test asserts the checked-in/current
    # artifacts retain the same hard boundaries as compile_inventory().
    assert SNAPSHOT.exists()
    assert REPORT.exists()

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    assert snapshot["board_name"] == "borg_production_inventory_board"
    assert snapshot["top_verdict"]["public_self_serve"] == "NO_GO"
    assert snapshot["top_verdict"]["google_tier_external_lift"] == "NO_GO"
    assert "broad public self-serve: `NO_GO`" in report
    assert "current source/hardening branch: `" in report
    assert "published package/local stdio: `NO_GO`" in report
    assert "served runtime freshness: `NO_GO`" in report
    assert "remote MCP/marketplace distribution: `NO_GO`" in report
    assert "global/federated learning protocol: `GO_PROTOCOL_ONLY`" in report
    assert "Google/God-tier measured external lift: `NO_GO`" in report
