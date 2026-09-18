import json
from pathlib import Path

import pytest

from eval.run_value_trial import (
    DEFAULT_TASKSET,
    build_hermes_command,
    build_hermes_environment,
    create_workspace,
    prompt_for,
    run_hidden,
    run_public,
    seed_database,
    summarize,
)
from eval.value_trial_borg_tool import lookup

HARD_TASKSET = DEFAULT_TASKSET.with_name("value_trial_taskset_v2.json")


def _taskset():
    return json.loads(DEFAULT_TASKSET.read_text(encoding="utf-8"))


def test_preregistered_taskset_has_distinct_three_arm_contract():
    data = _taskset()
    assert data["status"] == "preregistered_before_first_run"
    assert set(data["conditions"]) == {"C0_no_borg", "C1_borg_empty", "C2_borg_seeded"}
    assert data["primary_contrast"].startswith("C2_borg_seeded minus C1_borg_empty")
    assert len(data["tasks"]) == 8
    assert len({task["id"] for task in data["tasks"]}) == 8
    assert all(task["seed"]["root_cause"] and task["hidden_test"] for task in data["tasks"])


def test_hermes_child_environment_pins_both_working_directory_carriers(tmp_path, monkeypatch):
    monkeypatch.setenv("TERMINAL_CWD", "/wrong/parent")
    monkeypatch.setenv("HERMES_CWD", "/wrong/parent")

    env = build_hermes_environment(tmp_path)

    assert env["TERMINAL_CWD"] == str(tmp_path)
    assert env["HERMES_CWD"] == str(tmp_path)
    assert env["HERMES_SAFE_MODE"] == "1"
    assert env["HERMES_IGNORE_USER_CONFIG"] == "1"
    assert env["HERMES_IGNORE_RULES"] == "1"


def test_treatment_prompt_does_not_leak_hidden_diagnostic_query_hint(tmp_path):
    task = {
        "prompt": "Requests occasionally return another tenant's cached result.",
        "query_hint": "SECRET root cause cache key omits tenant identifier",
    }

    rendered = prompt_for(task, True, tmp_path)

    assert task["prompt"] in rendered
    assert task["query_hint"] not in rendered
    assert "SECRET root cause" not in rendered


def test_prefetch_no_match_is_invisible_and_seeded_context_is_advisory(tmp_path):
    task = {"prompt": "The symptom only.", "query_hint": "hidden diagnosis"}

    control = prompt_for(task, False, tmp_path, delivery_mode="prefetch")
    empty = prompt_for(task, True, tmp_path, delivery_mode="prefetch")
    seeded = prompt_for(
        task,
        True,
        tmp_path,
        delivery_mode="prefetch",
        prefetch_context='{"status":"matched_verified_memory"}',
    )

    assert control == empty
    assert "matched_verified_memory" not in empty
    assert "matched_verified_memory" in seeded
    assert "untrusted historical advisory" in seeded
    assert "verify with tests" in seeded


def test_hermes_command_pins_turn_budget_and_oneshot_usage_export(tmp_path, monkeypatch):
    usage_path = tmp_path / "usage.json"
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    hermes_executable = bin_dir / "hermes"
    hermes_python = bin_dir / "python3"
    hermes_executable.write_text("", encoding="utf-8")
    hermes_python.write_text("", encoding="utf-8")
    monkeypatch.setattr("eval.run_value_trial.shutil.which", lambda command: str(hermes_executable))

    command = build_hermes_command("fix it", usage_path, 7)

    assert command[0] == str(hermes_python.resolve())
    assert command[1] == "-c"
    assert "['max_turns'] = 7" in command[2]
    assert "os.path.realpath(os.getcwd())" in command[2]
    assert "sys.path[:]" in command[2]
    assert "run_oneshot" in command[2]
    assert "usage_file=sys.argv[2]" in command[2]
    assert command[-2:] == ["fix it", str(usage_path)]


def test_all_tasks_pass_public_and_fail_hidden_before_agent(tmp_path):
    for task in _taskset()["tasks"]:
        work, _ = create_workspace(task, tmp_path)
        assert run_public(work).returncode == 0, task["id"]
        assert run_hidden(work, task["hidden_test"]).returncode != 0, task["id"]


def test_hard_taskset_is_preregistered_without_diagnostic_prompt_leakage():
    data = json.loads(HARD_TASKSET.read_text(encoding="utf-8"))

    assert data["status"] == "preregistered_before_first_model_run"
    assert data["model"]["max_turns"] == 7
    assert len(data["tasks"]) == 8
    assert all(task["query_hint"] not in task["prompt"] for task in data["tasks"])
    assert all(len(task["files"]) >= 3 for task in data["tasks"])


@pytest.mark.parametrize("task", json.loads(HARD_TASKSET.read_text(encoding="utf-8"))["tasks"], ids=lambda task: task["id"])
def test_each_hard_task_passes_public_and_fails_hidden_before_agent(tmp_path, task):
    work, _ = create_workspace(task, tmp_path)

    assert run_public(work).returncode == 0
    assert run_hidden(work, task["hidden_test"]).returncode != 0


def test_hard_taskset_empty_and_seeded_memory_are_separated_using_symptom_only_query(tmp_path):
    tasks = json.loads(HARD_TASKSET.read_text(encoding="utf-8"))["tasks"]
    seeded = tmp_path / "seeded" / "traces.db"
    empty = tmp_path / "empty" / "traces.db"
    seed_database(tasks, seeded)

    for task in tasks:
        assert lookup(task["prompt"], str(empty))["status"] == "no_confident_match"
        result = lookup(task["prompt"], str(seeded))
        assert result["status"] == "matched_verified_memory", task["id"]
        assert result["matches"][0]["root_cause"]


def test_empty_and_seeded_memory_are_separated(tmp_path):
    tasks = _taskset()["tasks"]
    seeded = tmp_path / "seeded" / "traces.db"
    empty = tmp_path / "empty" / "traces.db"
    seed_database(tasks, seeded)
    for task in tasks:
        assert lookup(task["query_hint"], str(empty))["status"] == "no_confident_match"
        result = lookup(task["query_hint"], str(seeded))
        assert result["status"] == "matched_verified_memory", task["id"]
        assert result["matches"][0]["root_cause"]
        assert result["matches"][0]["action"]


def test_summary_keeps_crashes_and_invalid_runs_in_denominator():
    taskset = {"tasks": [{"id": "a"}, {"id": "b"}], "model": {"name": "gpt"}}
    rows = []
    for task_id in ("a", "b"):
        for condition in ("C0_no_borg", "C1_borg_empty", "C2_borg_seeded"):
            rows.append({
                "task_id": task_id,
                "condition": condition,
                "success": task_id == "a" and condition == "C2_borg_seeded",
                "valid": not (task_id == "b" and condition == "C1_borg_empty"),
                "wall_seconds": 1.0,
                "total_tokens": 100,
                "api_calls": 1,
                "borg_invocations": int(condition != "C0_no_borg"),
            })
    result = summarize(rows, taskset, {})
    assert result["per_condition"]["C1_borg_empty"]["n"] == 2
    assert result["per_condition"]["C1_borg_empty"]["valid"] == 1
    assert result["per_condition"]["C1_borg_empty"]["solved"] == 0
    assert result["primary_contrast"]["risk_difference"] == 0.5


def test_summary_reports_paired_efficiency_only_for_both_solved_pairs():
    taskset = {"tasks": [{"id": "a"}, {"id": "b"}], "model": {"name": "gpt"}}
    rows = []
    values = {
        "a": {
            "C0_no_borg": (True, 100, 10.0, 4),
            "C1_borg_empty": (True, 120, 12.0, 5),
            "C2_borg_seeded": (True, 80, 8.0, 3),
        },
        "b": {
            "C0_no_borg": (True, 100, 10.0, 4),
            "C1_borg_empty": (False, 200, 20.0, 8),
            "C2_borg_seeded": (True, 50, 5.0, 2),
        },
    }
    for task_id, conditions in values.items():
        for condition, (success, tokens, seconds, calls) in conditions.items():
            rows.append({
                "task_id": task_id,
                "condition": condition,
                "success": success,
                "valid": True,
                "wall_seconds": seconds,
                "retrieval_seconds": 0.01,
                "total_tokens": tokens,
                "non_cache_tokens": tokens // 2,
                "cache_read_tokens": tokens // 2,
                "estimated_cost_usd": 0.0,
                "api_calls": calls,
                "borg_invocations": int(condition != "C0_no_borg"),
            })

    result = summarize(rows, taskset, {})
    efficiency = result["paired_efficiency"]["C2_borg_seeded_minus_C1_borg_empty"]

    assert efficiency["n_complete_pairs"] == 2
    assert efficiency["n_both_solved_pairs"] == 1
    assert efficiency["metrics"]["total_tokens"]["median_paired_delta"] == -40
    assert efficiency["metrics"]["non_cache_tokens"]["median_paired_delta"] == -20
    assert efficiency["metrics"]["cache_read_tokens"]["median_paired_delta"] == -20
    assert efficiency["metrics"]["wall_seconds"]["right_lower_better"] == 1
    assert result["token_accounting"].startswith("total_tokens includes provider-reported cache reads")


def test_summary_marks_rejected_cli_command_as_invalid_harness():
    taskset = {"tasks": [{"id": "a"}], "model": {"name": "gpt"}}
    rows = []
    for condition in ("C0_no_borg", "C1_borg_empty", "C2_borg_seeded"):
        rows.append({
            "task_id": "a",
            "condition": condition,
            "success": False,
            "valid": False,
            "harness_command_accepted": False,
            "wall_seconds": 0.1,
            "total_tokens": None,
            "api_calls": None,
            "borg_invocations": 0,
        })

    result = summarize(rows, taskset, {})

    assert result["trial_status"] == "invalid_harness_command"
    assert result["harness_command_rejections"] == 3
