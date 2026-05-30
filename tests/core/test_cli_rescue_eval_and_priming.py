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


def test_agent_priming_cli_install_dry_run_and_uninstall_json(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"

    code, out, err = capture_main([
        "agent-priming",
        "claude-code",
        "--install",
        "--dry-run",
        "--target-file",
        str(target),
        "--json",
    ])
    data = json.loads(out)
    assert code == 0
    assert data["dry_run"] is True
    assert data["changed"] is True
    assert not target.exists()
    assert "DRY_RUN_NO_WRITE" in {state["code"] for state in data["fallback_states"]}
    assert err == ""

    code, out, err = capture_main([
        "agent-priming",
        "claude-code",
        "--install",
        "--target-file",
        str(target),
        "--json",
    ])
    install = json.loads(out)
    assert code == 0
    assert install["changed"] is True
    assert target.exists()

    wrong = tmp_path / "wrong.md"
    code, out, err = capture_main([
        "agent-priming",
        "claude-code",
        "--uninstall",
        "--target-file",
        str(wrong),
        "--json",
    ])
    failure = json.loads(out)
    assert code == 1
    assert "target file mismatch" in failure["error"]
    assert target.exists()

    code, out, err = capture_main(["agent-priming", "claude-code", "--uninstall", "--target-file", str(target), "--json"])
    uninstall = json.loads(out)
    assert code == 0
    assert uninstall["operation"] == "uninstall"
    assert uninstall["changed"] is True
    assert not target.exists()
    assert err == ""


def test_status_cli_json_exposes_data_notice_and_fallbacks(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))

    code, out, err = capture_main(["status", "--json"])

    data = json.loads(out)
    assert code == 0
    assert data["success"] is True
    assert data["data_notice"]["raw_trace_export_default"] == "off"
    states_by_code = {state["code"]: state for state in data["fallback_states"]}
    codes = set(states_by_code)
    assert "MCP_UNAVAILABLE_USE_CLI" in codes
    assert "SEMANTIC_SEARCH_LEXICAL_FALLBACK" in codes
    assert "OUTCOME_NOT_RECORDED" in codes
    assert "borg_record_outcome" in states_by_code["OUTCOME_NOT_RECORDED"]["next"]
    assert "feedback-v3" not in states_by_code["OUTCOME_NOT_RECORDED"]["next"]
    assert err == ""


def test_status_cli_json_does_not_create_storage_on_clean_home(tmp_path, monkeypatch):
    borg_home = tmp_path / "clean-borg-home"
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.delenv("BORG_DIR", raising=False)

    code, out, err = capture_main(["status", "--json"])

    data = json.loads(out)
    assert code == 0
    assert data["pack_count"] == 0
    assert data["agent_count"] == 0
    assert not borg_home.exists()
    assert err == ""


def test_status_cli_text_does_not_create_storage_on_clean_home(tmp_path, monkeypatch):
    borg_home = tmp_path / "clean-borg-home"
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.delenv("BORG_DIR", raising=False)

    code, out, err = capture_main(["status"])

    assert code == 0
    assert "Borg System Status" in out
    assert "SEMANTIC_SEARCH_LEXICAL_FALLBACK" in out
    assert "OUTCOME_NOT_RECORDED" in out
    assert not borg_home.exists()
    assert err == ""


def test_search_cli_text_no_match_prints_visible_fallback_notice(monkeypatch):
    payload = {
        "success": True,
        "matches": [],
        "query": "qxz impossible",
        "total": 0,
        "mode": "text",
        "fallback_states": [
            {
                "code": "NO_CONFIDENT_MATCH",
                "message": "Borg search found no matching pack, trace, or seed result.",
                "next": "run ordinary debugging without attributing the fix to Borg",
            }
        ],
    }
    monkeypatch.setattr("borg.core.search.borg_search", lambda *args, **kwargs: json.dumps(payload))

    code, out, err = capture_main(["search", "qxz impossible"])

    assert code == 0
    assert "No packs found." in out
    assert "NO_CONFIDENT_MATCH" in out
    assert "next: run ordinary debugging" in out
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
