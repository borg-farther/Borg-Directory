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
    assert data["go_no_go"]["global_federated_learning_claim"].startswith("NO_GO")
    assert len(data["controls"]) >= 10

    ids = {control["id"] for control in data["controls"]}
    assert ids == {f"CLC-{idx:03d}" for idx in range(1, 11)}

    p0_controls = [control for control in data["controls"] if control["priority"] == "P0"]
    assert len(p0_controls) >= 9
    assert {"implemented_local", "implemented_policy_gate", "blocked_next_build"}.issubset(
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
    assert "**File rev:** 20260526-1302 rev A" in doc
    assert "global/federated learning remains blocked" in doc
    assert "eval/collective_learning_loop_controls.json" in doc
    assert "66 passed" in doc
    assert "87 passed" in doc
