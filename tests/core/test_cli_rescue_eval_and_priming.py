from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import borg.cli as cli_module


def capture_main(args: list[str]) -> tuple[int, str, str]:
    sys.argv = ["borg"] + args
    captured_out = ""
    captured_err = ""

    def fake_stdout_write(s):
        nonlocal captured_out
        captured_out += str(s)

    def fake_stderr_write(s):
        nonlocal captured_err
        captured_err += str(s)

    try:
        with patch.object(sys, "stdout", MagicMock(wraps=sys.stdout, write=fake_stdout_write)), patch.object(
            sys, "stderr", MagicMock(wraps=sys.stderr, write=fake_stderr_write)
        ):
            code = cli_module.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1

    return code, captured_out, captured_err


def test_agent_priming_cli_outputs_host_candidate_json():
    code, out, err = capture_main(["agent-priming", "claude-code", "--json"])

    data = json.loads(out)
    assert code == 0
    assert data["host"] == "claude-code"
    assert data["recommendation"] == "eligible_for_host_rules_review"
    assert "borg_record_outcome" in data["prompt"]
    assert err == ""


def test_rescue_eval_cli_executes_taskset_json(tmp_path):
    taskset = tmp_path / "rescue-taskset.json"
    taskset.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskset_id": "cli-rescue-smoke",
                "cases": [
                    {
                        "case_id": "missing-dep",
                        "split": "selection",
                        "input": "ModuleNotFoundError: No module named flask",
                        "expected_status": "matched",
                        "expected_problem_class": "missing_dependency",
                        "expected_action_contains": ["pip install flask"],
                    },
                    {
                        "case_id": "rust-no-match",
                        "split": "hidden",
                        "input": "error[E0382]: borrow of moved value: `x`",
                        "expected_status": "no_confident_match",
                        "expected_problem_class": "unknown",
                    },
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    code, out, err = capture_main(["rescue-eval", str(taskset), "--json"])

    data = json.loads(out)
    assert code == 0
    assert data["taskset_id"] == "cli-rescue-smoke"
    assert data["success"] is True
    assert data["hidden"]["used_for_candidate"] is False
    assert data["first_10_claim"] is False
    assert err == ""
