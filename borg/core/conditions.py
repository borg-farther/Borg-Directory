"""
Condition Evaluator for Borg Brain — Conditional Phases.

Supports simple pattern-matching condition evaluation without using eval().

Supported condition patterns:
  - "'substring' in error_message"  — string containment
  - "error_type == 'TypeError'"     — exact match
  - "attempts > 3"                  — numeric comparison
  - "has_recent_changes"            — boolean flag lookup
  - "error_in_test"                — boolean flag lookup
"""

from __future__ import annotations

import re
from typing import Any, Dict


def evaluate_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a single condition string against a context dict.

    Args:
        condition: A condition pattern string (e.g. "error_type == 'TypeError'").
        context: A dict with runtime values (error_message, error_type, attempts, etc).

    Returns:
        True if the condition matches, False otherwise.
        Returns False if the context key is missing (not an error).
    """
    condition = condition.strip()

    # Boolean flag lookup: "has_recent_changes" or "error_in_test"
    if _is_boolean_lookup(condition):
        return _eval_boolean(condition, context)

    # String containment: "'substring' in error_message"
    if _is_string_contains(condition):
        return _eval_string_contains(condition, context)

    # Exact match: "error_type == 'TypeError'"
    if _is_exact_match(condition):
        return _eval_exact_match(condition, context)

    # Numeric comparison: "attempts > 3"
    if _is_numeric_comparison(condition):
        return _eval_numeric(condition, context)

    # Unknown pattern — treat as non-matching
    return False


def _is_boolean_lookup(condition: str) -> bool:
    """Check if condition is a simple boolean flag lookup (no operators)."""
    return (
        " in " not in condition
        and " == " not in condition
        and " != " not in condition
        and " > " not in condition
        and " < " not in condition
        and " >= " not in condition
        and " <= " not in condition
        and condition.startswith("'") is False
        and condition.startswith('"') is False
    )


def _is_string_contains(condition: str) -> bool:
    """Check if condition is a string containment check."""
    return " in " in condition and ("'" in condition or '"' in condition)


def _is_exact_match(condition: str) -> bool:
    """Check if condition is an exact match comparison."""
    return " == " in condition and ("'" in condition or '"' in condition)


def _is_numeric_comparison(condition: str) -> bool:
    """Check if condition is a numeric comparison."""
    return bool(re.search(r"\s*(>|<|>=|<=|==|!=)\s*\d+\.?\d*$", condition))


def _eval_boolean(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate a boolean flag lookup like 'has_recent_changes'."""
    key = condition.strip()
    val = context.get(key)
    if val is None:
        return False
    return bool(val)


def _eval_string_contains(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate "'substring' in error_message" style conditions."""
    # Pattern: "'<text>' in <key>"
    match = re.match(r"\s*['\"](.+?)['\"]\s+in\s+(\w+)", condition)
    if not match:
        return False
    substring = match.group(1)
    key = match.group(2)
    val = context.get(key, "")
    if val is None:
        return False
    return substring in str(val)


def _eval_exact_match(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate "error_type == 'TypeError'" style conditions."""
    # Pattern: <key> == '<value>'
    match = re.match(r"\s*(\w+)\s*==\s*['\"](.+?)['\"]", condition)
    if not match:
        return False
    key = match.group(1)
    expected = match.group(2)
    actual = context.get(key, "")
    return str(actual) == expected


def _eval_numeric(condition: str, context: Dict[str, Any]) -> bool:
    """Evaluate 'attempts > 3' style numeric comparisons."""
    # Pattern: <key> <op> <number>
    match = re.match(r"\s*(\w+)\s*(>=?|<=?|==|!=)\s*(\d+\.?\d*)\s*$", condition)
    if not match:
        return False
    key = match.group(1)
    op = match.group(2)
    threshold = float(match.group(3))

    val = context.get(key)
    if val is None:
        return False

    try:
        actual = float(val)
    except (TypeError, ValueError):
        return False

    if op == ">":
        return actual > threshold
    elif op == ">=":
        return actual >= threshold
    elif op == "<":
        return actual < threshold
    elif op == "<=":
        return actual <= threshold
    elif op == "==":
        return actual == threshold
    elif op == "!=":
        return actual != threshold

    return False


# ---------------------------------------------------------------------------
# Phase-level condition helpers
# ---------------------------------------------------------------------------


def evaluate_skip_conditions(
    phase: Dict[str, Any],
    context: Dict[str, Any],
) -> tuple[bool, str]:
    """Evaluate skip_if conditions on a phase.

    Args:
        phase: A phase dict which may have a 'skip_if' list.
        context: Runtime context dict.

    Returns:
        A tuple of (should_skip: bool, reason: str).
        If skip_if is absent or no conditions match, returns (False, "").
    """
    skip_conditions = phase.get("skip_if", [])
    if not skip_conditions:
        return False, ""

    for item in skip_conditions:
        if isinstance(item, dict):
            condition = item.get("condition", "")
            reason = item.get("reason", "")
        else:
            condition = str(item)
            reason = ""

        if evaluate_condition(condition, context):
            return True, reason

    return False, ""


def evaluate_inject_conditions(
    phase: Dict[str, Any],
    context: Dict[str, Any],
) -> list[str]:
    """Evaluate inject_if conditions on a phase and return matching messages.

    Args:
        phase: A phase dict which may have an 'inject_if' list.
        context: Runtime context dict.

    Returns:
        List of message strings from conditions that matched.
    """
    inject_conditions = phase.get("inject_if", [])
    if not inject_conditions:
        return []

    messages = []
    for item in inject_conditions:
        if isinstance(item, dict):
            condition = item.get("condition", "")
            message = item.get("message", "")
        else:
            condition = str(item)
            message = ""

        if evaluate_condition(condition, context) and message:
            messages.append(message)

    return messages


def evaluate_context_prompts(
    phase: Dict[str, Any],
    context: Dict[str, Any],
) -> list[str]:
    """Evaluate context_prompts conditions on a phase and return matching prompts.

    Args:
        phase: A phase dict which may have a 'context_prompts' list.
        context: Runtime context dict.

    Returns:
        List of prompt strings from conditions that matched.
    """
    context_prompts = phase.get("context_prompts", [])
    if not context_prompts:
        return []

    prompts = []
    for item in context_prompts:
        if isinstance(item, dict):
            condition = item.get("condition", "")
            prompt = item.get("prompt", "")
        else:
            condition = str(item)
            prompt = ""

        if evaluate_condition(condition, context) and prompt:
            prompts.append(prompt)

    return prompts
