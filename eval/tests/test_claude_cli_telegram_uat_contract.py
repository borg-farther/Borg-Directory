import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "eval" / "claude_cli_telegram_uat_contract.json"
RUNBOOK_PATH = REPO_ROOT / "docs" / "CLAUDE_CLI_TELEGRAM_UAT.md"


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_file_exists_and_parses():
    assert CONTRACT_PATH.exists(), f"missing contract: {CONTRACT_PATH}"
    data = _load_contract()
    assert isinstance(data, dict)


def test_contract_has_required_top_level_fields():
    data = _load_contract()
    required = {
        "artifact_version",
        "scope",
        "channel",
        "entrypoint",
        "acceptance_gates",
        "test_plan",
        "release_blockers",
        "go_no_go_policy",
    }
    missing = required - set(data.keys())
    assert not missing, f"missing keys: {sorted(missing)}"


def test_acceptance_gates_are_binary_and_nonempty():
    data = _load_contract()
    gates = data["acceptance_gates"]
    assert isinstance(gates, list) and len(gates) >= 8
    for gate in gates:
        assert gate.get("id")
        assert gate.get("name")
        assert gate.get("pass_criteria")
        assert gate.get("fail_criteria")


def test_test_plan_covers_installation_mcp_and_channel_delivery():
    data = _load_contract()
    plan = data["test_plan"]
    step_names = {step.get("name", "").lower() for step in plan}
    assert any("install" in s for s in step_names)
    assert any("mcp" in s or "claude" in s for s in step_names)
    assert any("telegram" in s or "channel" in s for s in step_names)


def test_runbook_exists_and_has_execution_sections():
    assert RUNBOOK_PATH.exists(), f"missing runbook: {RUNBOOK_PATH}"
    body = RUNBOOK_PATH.read_text(encoding="utf-8").lower()
    required_headings = [
        "# claude cli telegram uat runbook",
        "## scope",
        "## preflight",
        "## execution",
        "## pass/fail rubric",
        "## rollback",
    ]
    for heading in required_headings:
        assert heading in body, f"missing heading in runbook: {heading}"


def test_no_placeholder_values_left_in_contract_or_runbook():
    bad_tokens = ["tbd", "todo", "lorem ipsum", "xxx"]
    texts = []
    if CONTRACT_PATH.exists():
        texts.append(CONTRACT_PATH.read_text(encoding="utf-8").lower())
    if RUNBOOK_PATH.exists():
        texts.append(RUNBOOK_PATH.read_text(encoding="utf-8").lower())
    whole = "\n".join(texts)
    for token in bad_tokens:
        assert token not in whole, f"placeholder token found: {token}"
