import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = [
    "eval/security_hardening_baseline.json",
    "docs/SECURITY_HARDENING_BASELINE.md",
    ".github/workflows/security-gates.yml",
    "scripts/security_gate_check.py",
]
REQUIRED_CI_GATES = {
    "secret_scan",
    "dependency_vuln_scan",
    "static_security_scan",
    "policy_enforcement",
}
PLACEHOLDER_TOKENS = ("todo", "tbd", "placeholder", "fixme", "lorem")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_security_hardening_baseline_files_exist():
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).exists()]
    assert missing == []


def test_security_hardening_baseline_json_contract_is_complete():
    baseline = json.loads(_read("eval/security_hardening_baseline.json"))

    threat_model = baseline.get("threat_model") or {}
    assert len(threat_model.get("assets") or []) >= 4
    assert len(threat_model.get("attack_paths") or []) >= 4

    controls = baseline.get("controls") or {}
    for key in ("privacy", "prompt_injection", "trust", "lifecycle"):
        assert key in controls
        assert len(controls[key]) >= 2

    assert REQUIRED_CI_GATES.issubset(set(baseline.get("ci_gates") or []))
    assert len(baseline.get("release_blockers") or []) >= 4


def test_security_hardening_baseline_has_no_placeholder_language():
    combined = "\n".join(_read(rel).lower() for rel in REQUIRED_FILES)
    assert not any(token in combined for token in PLACEHOLDER_TOKENS)


def test_security_workflow_contains_required_jobs_and_tools():
    workflow = _read(".github/workflows/security-gates.yml")
    for needle in (
        "gitleaks/gitleaks-action",
        "pip-audit",
        "bandit",
        "python scripts/security_gate_check.py",
    ):
        assert needle in workflow


def test_docs_index_links_machine_and_human_security_sources():
    docs_index = _read("docs/README.md")
    assert "SECURITY_HARDENING_BASELINE.md" in docs_index
    assert "security_hardening_baseline.json" in docs_index
