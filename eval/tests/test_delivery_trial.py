import json

from eval.run_delivery_trial import ARMS, summarize


def _rows(prefetch_calls=4, prefetch_tokens=80, prefetch_success=True):
    rows = []
    for task_id in ("a", "b"):
        values = {
            "T0_tool_empty": (True, 5, 120),
            "T1_tool_seeded": (True, 5, 100),
            "P0_prefetch_empty": (True, 4, 100),
            "P1_prefetch_seeded": (prefetch_success, prefetch_calls, prefetch_tokens),
        }
        for condition, (success, calls, tokens) in values.items():
            rows.append({
                "task_id": task_id,
                "condition": condition,
                "success": success,
                "valid": True,
                "api_calls": calls,
                "non_cache_tokens": tokens,
                "wall_seconds": float(calls),
                "total_tokens": tokens * 2,
                "cache_read_tokens": tokens,
                "retrieval_seconds": 0.01,
                "estimated_cost_usd": 0.0,
                "borg_invocations": 1,
            })
    return rows


def _prereg():
    return {
        "task_ids": ["a", "b"],
        "decision_rule": {"claim_boundary": "mechanism only"},
    }


def test_summary_applies_preregistered_directional_mechanism_rule():
    result = summarize(_rows(), _prereg(), {})

    assert result["trial_status"] == "completed"
    assert result["all_runs_valid"] is True
    assert result["verdict"] == "DIRECTIONAL_MECHANISM_IMPROVEMENT"
    primary = result["primary_seeded_prefetch_minus_tool"]
    assert primary["metrics"]["api_calls"]["median_paired_delta"] == -1
    assert primary["metrics"]["non_cache_tokens"]["median_paired_delta"] == -20
    assert not primary["negative_transfer_tasks"]


def test_summary_fails_rule_on_negative_transfer():
    result = summarize(_rows(prefetch_success=False), _prereg(), {})

    assert result["verdict"] == "MECHANISM_NOT_IMPROVED_UNDER_PREREGISTERED_RULE"
    assert result["primary_seeded_prefetch_minus_tool"]["negative_transfer_tasks"] == ["a", "b"]


def test_preregistration_names_exactly_the_four_arms():
    prereg = json.loads(
        ( __import__("pathlib").Path(__file__).resolve().parents[1] / "delivery_trial_preregistration.json")
        .read_text(encoding="utf-8")
    )

    assert set(prereg["conditions"]) == set(ARMS)
    assert prereg["status"] == "preregistered_before_first_delivery_trial_model_run"
