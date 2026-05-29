from __future__ import annotations

import json
from pathlib import Path

from borg.core.rescue_packet_eval import RescueEvalCase, evaluate_rescue_cases, load_rescue_eval_taskset


def test_rescue_packet_eval_executes_selection_and_reports_hidden_holdout(tmp_path):
    taskset_path = tmp_path / "rescue-taskset.json"
    taskset_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskset_id": "rescue-packet-smoke",
                "cases": [
                    {
                        "case_id": "sel-missing-dep",
                        "split": "selection",
                        "input": "ModuleNotFoundError: No module named flask",
                        "expected_status": "matched",
                        "expected_problem_class": "missing_dependency",
                        "expected_action_contains": ["pip install flask"],
                        "expected_verify_contains": ["rerun"],
                    },
                    {
                        "case_id": "sel-no-match-rust",
                        "split": "selection",
                        "input": "error[E0382]: borrow of moved value: `x`",
                        "expected_status": "no_confident_match",
                        "expected_problem_class": "unknown",
                        "expected_stop_contains": ["do not force"],
                    },
                    {
                        "case_id": "hidden-type-mismatch",
                        "split": "hidden",
                        "input": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
                        "expected_status": "matched",
                        "expected_problem_class": "type_mismatch",
                        "expected_action_contains": ["type"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    taskset = load_rescue_eval_taskset(taskset_path)
    result = evaluate_rescue_cases(taskset.cases, taskset_id=taskset.taskset_id)

    assert result["schema_version"] == "1.0"
    assert result["taskset_id"] == "rescue-packet-smoke"
    assert result["success"] is True
    assert result["selection"]["used_for_candidate"] is True
    assert result["hidden"]["used_for_candidate"] is False
    assert result["hidden"]["holdout_only"] is True
    assert result["selection"]["metrics"]["problem_class_accuracy"] == 1.0
    assert result["selection"]["metrics"]["no_confident_match_precision"] == 1.0
    assert result["selection"]["metrics"]["action_stop_verify_presence"] == 1.0
    assert result["selection"]["metrics"]["outcome_capture_prompt_rate"] == 1.0
    assert result["hidden"]["metrics"]["problem_class_accuracy"] == 1.0
    assert result["hidden_holdout_passed"] is True
    assert result["recommendation"] == "rescue_packet_candidate_eligible_for_review"


def test_rescue_packet_eval_rewards_correct_no_match_and_penalizes_unsafe_or_missing_outcome_prompt():
    case = RescueEvalCase(
        case_id="unknown",
        split="selection",
        input="some impossible proprietary service said blorple blargle",
        expected_status="no_confident_match",
        expected_problem_class="unknown",
    )

    result = evaluate_rescue_cases([case], taskset_id="single-no-match")

    assert result["selection"]["metrics"]["no_confident_match_precision"] == 1.0
    assert result["selection"]["metrics"]["unsafe_guidance_rate"] == 0.0
    assert result["selection"]["metrics"]["outcome_capture_prompt_rate"] == 1.0
    assert result["first_10_claim"] is False
    assert result["global_promotion_allowed"] is False


def test_rescue_packet_eval_reports_hidden_failures_without_using_them_for_candidate_selection():
    cases = [
        RescueEvalCase(
            case_id="selection-good",
            split="selection",
            input="ModuleNotFoundError: No module named flask",
            expected_status="matched",
            expected_problem_class="missing_dependency",
        ),
        RescueEvalCase(
            case_id="hidden-intentionally-wrong",
            split="hidden",
            input="ModuleNotFoundError: No module named flask",
            expected_status="no_confident_match",
            expected_problem_class="unknown",
        ),
    ]

    result = evaluate_rescue_cases(cases, taskset_id="hidden-diagnostic")

    assert result["success"] is True
    assert result["recommendation"] == "rescue_packet_candidate_eligible_for_review"
    assert result["hidden_holdout_passed"] is False
    assert result["hidden"]["used_for_candidate"] is False
    assert result["hidden"]["hard_failures"]
    assert result["hard_failures"] == []


def test_rescue_packet_eval_train_cases_are_report_only_for_selection_gate():
    cases = [
        RescueEvalCase(
            case_id="selection-good",
            split="selection",
            input="ModuleNotFoundError: No module named flask",
            expected_status="matched",
            expected_problem_class="missing_dependency",
        ),
        RescueEvalCase(
            case_id="train-intentionally-wrong",
            split="train",
            input="ModuleNotFoundError: No module named flask",
            expected_status="no_confident_match",
            expected_problem_class="unknown",
        ),
    ]

    result = evaluate_rescue_cases(cases, taskset_id="train-diagnostic")

    assert result["success"] is True
    assert result["train"]["used_for_candidate"] is False
    assert result["train"]["used_for_candidate_generation"] is True
    assert result["train"]["hard_failures"]
    assert result["hard_failures"] == []
