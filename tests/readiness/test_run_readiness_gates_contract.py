from __future__ import annotations

import ast
import json
from pathlib import Path

from eval import run_readiness_gates
from eval import uat_scoreboard

ROOT = Path(__file__).resolve().parents[2]


def test_readiness_gate_orchestrator_runs_cold_start_trust_gate() -> None:
    source = (ROOT / "eval" / "run_readiness_gates.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]

    assert "cold_start_trust_gate" in constants
    assert "eval/cold_start_trust_gate.py" in constants


def _scoreboard_payload(*, synthetic: bool = True, real_100: bool = False) -> dict:
    return {
        "timestamp": "2026-05-26T00:00:00+00:00",
        "source": "test",
        "version": {"passed": True},
        "first_user_surface": {"passed": True},
        "security_surface": {"passed": True},
        "loads": {},
        "real_user_rollout": {
            "ready_for_10_controlled_beta": synthetic,
            "infrastructure_ready_for_100": synthetic,
            "ready_for_100_real_users": real_100,
            "max_recommended_real_users_now": 10 if synthetic else 0,
            "blockers": [] if real_100 else ["first-10 external-user evidence has not passed"],
        },
        "gate_run_snapshot": {},
        "gates": {},
        "ready_for_10": synthetic,
        "ready_for_100": synthetic,
        "ready_for_1000": synthetic,
        "synthetic_load_all_pass": synthetic,
        "real_user_100_all_pass": synthetic and real_100,
        "all_pass": synthetic and real_100,
    }


def test_uat_scoreboard_default_exit_code_follows_full_real_user_readiness(tmp_path, monkeypatch) -> None:
    (tmp_path / "eval").mkdir()
    monkeypatch.setattr(uat_scoreboard, "ROOT", tmp_path)
    monkeypatch.setattr(uat_scoreboard, "compile_scoreboard", lambda: _scoreboard_payload(synthetic=True, real_100=False))
    monkeypatch.setattr(uat_scoreboard, "_write_markdown", lambda snapshot: None)

    assert uat_scoreboard.main([]) == 1
    assert uat_scoreboard.main(["--synthetic-only"]) == 0


def test_run_readiness_gates_default_exit_code_does_not_treat_synthetic_pass_as_100_user_go(tmp_path, monkeypatch) -> None:
    (tmp_path / "eval").mkdir()
    monkeypatch.setattr(run_readiness_gates, "ROOT", tmp_path)
    monkeypatch.setattr(run_readiness_gates, "_write_decision", lambda snapshot: None)

    scoreboard_payload = _scoreboard_payload(synthetic=True, real_100=False)

    def fake_run(name: str, cmd: list[str], timeout: int = 900) -> dict:
        if name == "real_user_rollout_gate":
            return {
                "name": name,
                "cmd": cmd,
                "started": "2026-05-26T00:00:00+00:00",
                "rc": 1,
                "stdout": json.dumps(scoreboard_payload["real_user_rollout"]),
                "stderr": "",
            }
        if name in {"scoreboard_final", "scoreboard_after_decision"}:
            assert "--synthetic-only" in cmd
            (tmp_path / "eval" / "uat_scoreboard_snapshot.json").write_text(
                json.dumps(scoreboard_payload),
                encoding="utf-8",
            )
            return {"name": name, "cmd": cmd, "started": "2026-05-26T00:00:00+00:00", "rc": 0, "stdout": "", "stderr": ""}
        return {"name": name, "cmd": cmd, "started": "2026-05-26T00:00:00+00:00", "rc": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(run_readiness_gates, "_run", fake_run)

    assert run_readiness_gates.main([]) == 1
    assert run_readiness_gates.main(["--synthetic-only"]) == 0
