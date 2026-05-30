"""Executable rescue-packet evaluation harness for Borg.

This module evaluates the *user-visible* rescue contract, not model weights.  It
keeps the SkillOpt discipline Borg wants: frozen tasksets, explicit splits,
NO_CONFIDENT_MATCH as a positive behavior, and no first-10/public-lift claims.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any, Sequence

from borg.core.rescue import RescueResult, rescue

_UNSAFE_RE = re.compile(r"(?i)(\bsudo\s+pip\b|\brm\s+-rf\b|curl\s+[^|]+\|\s*(?:sh|bash)|chmod\s+777)")
_ALLOWED_SPLITS = {"train", "selection", "hidden"}


@dataclass(frozen=True)
class RescueEvalCase:
    case_id: str
    split: str
    input: str
    expected_status: str
    expected_problem_class: str
    expected_action_contains: tuple[str, ...] = ()
    expected_stop_contains: tuple[str, ...] = ()
    expected_verify_contains: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RescueEvalCase":
        if not isinstance(data, dict):
            raise ValueError("rescue eval case must be an object")
        case_id = str(data.get("case_id") or "").strip()
        split = str(data.get("split") or "selection").strip().lower()
        input_text = str(data.get("input") or "")
        expected_status = str(data.get("expected_status") or "").strip()
        expected_problem_class = str(data.get("expected_problem_class") or "").strip()
        if not case_id:
            raise ValueError("rescue eval case missing case_id")
        if split not in _ALLOWED_SPLITS:
            raise ValueError(f"rescue eval case {case_id} has invalid split: {split}")
        if not input_text:
            raise ValueError(f"rescue eval case {case_id} missing input")
        if expected_status not in {"matched", "no_confident_match", "empty_input"}:
            raise ValueError(f"rescue eval case {case_id} has invalid expected_status")
        if not expected_problem_class:
            raise ValueError(f"rescue eval case {case_id} missing expected_problem_class")
        return cls(
            case_id=case_id,
            split=split,
            input=input_text,
            expected_status=expected_status,
            expected_problem_class=expected_problem_class,
            expected_action_contains=tuple(str(x) for x in data.get("expected_action_contains", []) if str(x).strip()),
            expected_stop_contains=tuple(str(x) for x in data.get("expected_stop_contains", []) if str(x).strip()),
            expected_verify_contains=tuple(str(x) for x in data.get("expected_verify_contains", []) if str(x).strip()),
        )


@dataclass(frozen=True)
class RescueEvalTaskset:
    taskset_id: str
    cases: tuple[RescueEvalCase, ...]


def load_rescue_eval_taskset(path: str | Path) -> RescueEvalTaskset:
    """Load and validate a rescue-packet eval taskset JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("rescue eval taskset must be a JSON object")
    if data.get("schema_version") != "1.0":
        raise ValueError("rescue eval taskset schema_version must be '1.0'")
    taskset_id = str(data.get("taskset_id") or "").strip()
    if not taskset_id:
        raise ValueError("rescue eval taskset missing taskset_id")
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("rescue eval taskset requires non-empty cases")
    cases = tuple(RescueEvalCase.from_dict(item) for item in raw_cases)
    if not any(case.split == "selection" for case in cases):
        raise ValueError("rescue eval taskset requires at least one selection case")
    return RescueEvalTaskset(taskset_id=taskset_id, cases=cases)


def _contains_all(haystack: Sequence[str], needles: Sequence[str]) -> bool:
    text = "\n".join(str(item or "") for item in haystack).lower()
    return all(str(needle).lower() in text for needle in needles)


def _outcome_capture_present(result: RescueResult) -> bool:
    if result.status == "no_confident_match":
        instruction = f"{result.agent_instruction}\n{result.human_receipt}".lower()
        return "do not attribute" in instruction or "no_match" in instruction
    text = f"{result.next_command}\n{result.agent_instruction}\n{result.value_receipt}".lower()
    return "feedback" in text or "record_outcome" in text or "outcome" in text


def _case_eval(case: RescueEvalCase) -> dict[str, Any]:
    result = rescue(case.input, source="rescue-packet-eval", show_guidance=False)
    payload = result.to_dict()
    action_ok = _contains_all(result.action, case.expected_action_contains)
    stop_ok = _contains_all(result.stop, case.expected_stop_contains)
    verify_ok = _contains_all(result.verify, case.expected_verify_contains)
    status_ok = result.status == case.expected_status
    problem_ok = result.problem_class == case.expected_problem_class
    presence_ok = bool(result.action and result.stop and result.verify and (("ACTION" in result.agent_instruction and "STOP" in result.agent_instruction and "VERIFY" in result.agent_instruction) or (case.expected_status == "no_confident_match" and "NO_MATCH" in result.agent_instruction)))
    unsafe = bool(_UNSAFE_RE.search(json.dumps(payload, ensure_ascii=False)))
    no_match_expected = case.expected_status == "no_confident_match"
    no_match_ok = (result.status == "no_confident_match" and result.problem_class == "unknown") if no_match_expected else True
    return {
        "case_id": case.case_id,
        "split": case.split,
        "expected_status": case.expected_status,
        "status": result.status,
        "problem_class": result.problem_class,
        "status_ok": status_ok,
        "problem_class_ok": problem_ok,
        "action_contains_ok": action_ok,
        "stop_contains_ok": stop_ok,
        "verify_contains_ok": verify_ok,
        "action_stop_verify_presence_ok": presence_ok,
        "no_confident_match_ok": no_match_ok,
        "unsafe_guidance": unsafe,
        "outcome_capture_prompt_ok": _outcome_capture_present(result),
        "human_visible_no_match": ("NO_MATCH" in result.agent_instruction or "no prior memory" in result.human_receipt.lower()) if no_match_expected else True,
    }


def _avg(values: Sequence[bool]) -> float:
    if not values:
        return 1.0
    return round(sum(1 for value in values if value) / len(values), 6)


def _split_summary(case_results: list[dict[str, Any]], split: str) -> dict[str, Any]:
    rows = [row for row in case_results if row["split"] == split]
    no_match_rows = [row for row in rows if row.get("expected_status") == "no_confident_match"]
    metrics = {
        "status_accuracy": _avg([row["status_ok"] for row in rows]),
        "problem_class_accuracy": _avg([row["problem_class_ok"] for row in rows]),
        "action_stop_verify_presence": _avg([row["action_stop_verify_presence_ok"] for row in rows]),
        "expected_content_match": _avg([row["action_contains_ok"] and row["stop_contains_ok"] and row["verify_contains_ok"] for row in rows]),
        "no_confident_match_precision": _avg([row["no_confident_match_ok"] for row in no_match_rows]),
        "unsafe_guidance_rate": round(sum(1 for row in rows if row["unsafe_guidance"]) / max(1, len(rows)), 6),
        "outcome_capture_prompt_rate": _avg([row["outcome_capture_prompt_ok"] for row in rows]),
        "human_visible_no_match_rate": _avg([row["human_visible_no_match"] for row in rows]),
    }
    hard_failures: list[str] = []
    if rows and min(metrics["status_accuracy"], metrics["problem_class_accuracy"], metrics["action_stop_verify_presence"]) < 1.0:
        hard_failures.append(f"{split}_core_contract_regression")
    if metrics["unsafe_guidance_rate"] > 0:
        hard_failures.append(f"{split}_unsafe_guidance")
    if metrics["outcome_capture_prompt_rate"] < 1.0:
        hard_failures.append(f"{split}_outcome_capture_missing")
    return {
        "case_count": len(rows),
        "used_for_candidate": split == "selection",
        "used_for_candidate_generation": split == "train",
        "used_for_selection_gate": split == "selection",
        "holdout_only": split == "hidden",
        "metrics": metrics,
        "hard_failures": hard_failures,
        "cases": rows,
    }


def evaluate_rescue_cases(cases: Sequence[RescueEvalCase], *, taskset_id: str = "adhoc-rescue-eval") -> dict[str, Any]:
    """Execute a rescue eval taskset and return source-reviewable metrics."""
    if not cases:
        raise ValueError("rescue eval requires at least one case")
    case_results = [_case_eval(case) for case in cases]
    selection = _split_summary(case_results, "selection")
    train = _split_summary(case_results, "train")
    hidden = _split_summary(case_results, "hidden")
    hard_failures = list(selection["hard_failures"])
    hidden_holdout_passed = not bool(hidden["hard_failures"])
    success = not hard_failures and selection["case_count"] > 0
    return {
        "schema_version": "1.0",
        "taskset_id": taskset_id,
        "success": bool(success),
        "recommendation": "rescue_packet_candidate_eligible_for_review" if success else "rescue_packet_candidate_blocked",
        "train": train,
        "selection": selection,
        "hidden": hidden,
        "hidden_holdout_passed": hidden_holdout_passed,
        "diagnostic_failures": {
            "train": list(train["hard_failures"]),
            "hidden": list(hidden["hard_failures"]),
        },
        "hard_failures": hard_failures,
        "first_10_claim": False,
        "global_promotion_allowed": False,
    }
