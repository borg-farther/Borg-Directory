from __future__ import annotations

import json
import sys

from borg.cli import main
from borg.core import epistemic_guardrail


def no_memory(*args):
    return []


def run_cli(monkeypatch, argv: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["borg", *argv])
    return main()


def test_cli_deliberate_easy_task_stays_standard(capsys, monkeypatch) -> None:
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    code = run_cli(
        monkeypatch,
        ["deliberate", "rename", "a", "local", "variable", "--no-record", "--json"],
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["success"] is True
    assert payload["epistemic_packet"]["mode_selected"] == "standard"
    assert payload["epistemic_packet"]["outcome_capture"]["status"] == "not_recorded_by_request"


def test_cli_deliberate_high_risk_block_has_exit_two(capsys, monkeypatch) -> None:
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    code = run_cli(
        monkeypatch,
        [
            "deliberate",
            "approve",
            "production",
            "release",
            "--stage",
            "review",
            "--risk",
            "high",
            "--claims-json",
            '[{"id":"c1","text":"release is safe","material":true}]',
            "--no-record",
            "--json",
        ],
    )
    packet = json.loads(capsys.readouterr().out)["epistemic_packet"]
    assert code == 2
    assert packet["decision"] == "block_pending_verification"
    assert packet["unsupported_claims"] == ["c1"]


def test_cli_deliberate_rejects_non_array_json(capsys, monkeypatch) -> None:
    code = run_cli(
        monkeypatch,
        ["deliberate", "task", "--claims-json", '{"id":"not-an-array"}', "--json"],
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["success"] is False
    assert "JSON array" in payload["error"]


def test_cli_deliberate_records_local_intervention(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    code = run_cli(monkeypatch, ["deliberate", "debug", "parser", "--json"])
    packet = json.loads(capsys.readouterr().out)["epistemic_packet"]
    assert code == 0
    assert packet["outcome_capture"]["status"] == "recorded_local"
    assert packet["outcome_capture"]["intervention_id"].startswith("intervention-sha256:")


def test_cli_human_render_has_stop_verify_and_no_match(capsys, monkeypatch) -> None:
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    code = run_cli(monkeypatch, ["deliberate", "rename", "variable", "--no-record"])
    output = capsys.readouterr().out
    assert code == 0
    assert "DECISION:" in output
    assert "STOP:" in output
    assert "VERIFY:" in output
    assert "NO_CONFIDENT_MATCH" in output
