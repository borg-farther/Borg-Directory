"""Machine-readable gates for the optimal safe collective learning loop."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTROL_PATH = ROOT / "eval" / "collective_learning_loop_controls.json"
DOC_PATH = ROOT / "docs" / "20260526-1302_OPTIMAL_SAFE_COLLECTIVE_LEARNING_LOOP.md"


def _load_controls():
    return json.loads(CONTROL_PATH.read_text(encoding="utf-8"))


def test_collective_learning_loop_control_contract_exists_and_is_complete():
    data = _load_controls()

    assert data["schema_version"] == "1.0"
    assert data["rev"] == "20260526-1302"
    assert data["go_no_go"]["global_federated_learning_claim"] == "GO_REMOTE_SIGNED_PROTOCOL_ONLY"
    assert data["go_no_go"]["google_god_tier_learning_optimality"] == "NO_GO_VALUE_LOOP_NOT_PROVEN"
    assert data["go_no_go"]["public_self_serve_launch"].startswith("NO_GO")
    assert len(data["controls"]) >= 10

    ids = {control["id"] for control in data["controls"]}
    assert ids == {f"CLC-{idx:03d}" for idx in range(1, 11)}

    p0_controls = [control for control in data["controls"] if control["priority"] == "P0"]
    assert len(p0_controls) >= 9
    assert {"implemented_local", "implemented_policy_gate", "implemented_remote_protocol", "implemented_runtime_gate"}.issubset(
        {control["status"] for control in data["controls"]}
    )


def test_collective_learning_loop_controls_have_verifiable_files_or_blocked_status():
    data = _load_controls()

    for control in data["controls"]:
        assert control["id"].startswith("CLC-")
        assert control["category"]
        assert control["invariant"]
        assert "todo" not in control["invariant"].lower()
        if control["status"].startswith("implemented"):
            assert control["implementation_files"]
            assert control["tests"]
        for relative_path in control["implementation_files"] + control["tests"]:
            assert (ROOT / relative_path).exists(), relative_path


def test_collective_learning_loop_required_docs_exist_and_link_current_contract():
    data = _load_controls()

    for relative_path in data["required_docs"]:
        assert (ROOT / relative_path).exists(), relative_path

    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "**File rev:** 20260526-1302 rev B" in doc
    assert "remote/global/federated protocol is GO" in doc
    assert "docs/20260526-2046_REMOTE_FEDERATED_LEARNING_GO_PROOF.md" in doc
    assert "docs/20260526-2115_FEDERATED_LEARNING_OPTIMALITY_AUDIT.md" in doc
    assert "NO-GO for optimality today" in doc
    assert "eval/collective_learning_loop_controls.json" in doc
    assert "66 passed" in doc
    assert "97 passed" in doc


def test_learning_atom_schema_partial_example_is_honest():
    schema_doc = (ROOT / "docs" / "LEARNING_ATOM_SCHEMA.md").read_text(encoding="utf-8")
    assert "## Partial example safe payload" in schema_doc
    assert "A validating payload must also include `atom_id`, `evidence`, `privacy`, `safety`, `trust`, and `lifecycle`" in schema_doc
