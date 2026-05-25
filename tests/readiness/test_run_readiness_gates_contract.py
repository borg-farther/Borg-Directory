from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readiness_gate_orchestrator_runs_cold_start_trust_gate() -> None:
    source = (ROOT / "eval" / "run_readiness_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]

    assert "cold_start_trust_gate" in constants
    assert "eval/cold_start_trust_gate.py" in constants
