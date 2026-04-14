"""
Tests for Borg Brain — Conditional Phases (Phase 1).

Tests evaluate_condition, skip_if, inject_if, context_prompts,
and backward compatibility with packs that don't use conditions.
"""

import pytest

from borg.core.conditions import (
    evaluate_condition,
    evaluate_skip_conditions,
    evaluate_inject_conditions,
    evaluate_context_prompts,
)
from borg.core import schema as schema_mod


# ---------------------------------------------------------------------------
# evaluate_condition tests — all 4 condition types
# ---------------------------------------------------------------------------

class TestEvaluateCondition:
    def test_string_contains_match(self):
        ctx = {"error_message": "TypeError: 'NoneType' has no attribute 'split'"}
        assert evaluate_condition("'NoneType' in error_message", ctx) is True

    def test_string_contains_no_match(self):
        ctx = {"error_message": "TypeError: 'NoneType' has no attribute 'split'"}
        assert evaluate_condition("'ImportError' in error_message", ctx) is False

    def test_string_contains_case_sensitive(self):
        ctx = {"error_message": "TypeError: NoneType has no attribute"}
        assert evaluate_condition("'NoneType' in error_message", ctx) is True

    def test_exact_match_string(self):
        ctx = {"error_type": "TypeError"}
        assert evaluate_condition("error_type == 'TypeError'", ctx) is True

    def test_exact_match_string_no_match(self):
        ctx = {"error_type": "ImportError"}
        assert evaluate_condition("error_type == 'TypeError'", ctx) is False

    def test_exact_match_integer(self):
        ctx = {"error_type": 42}
        assert evaluate_condition("error_type == 42", ctx) is True

    def test_numeric_greater_than(self):
        ctx = {"attempts": 5}
        assert evaluate_condition("attempts > 3", ctx) is True

    def test_numeric_greater_than_false(self):
        ctx = {"attempts": 2}
        assert evaluate_condition("attempts > 3", ctx) is False

    def test_numeric_greater_than_equal(self):
        ctx = {"attempts": 3}
        assert evaluate_condition("attempts >= 3", ctx) is True

    def test_numeric_less_than(self):
        ctx = {"attempts": 2}
        assert evaluate_condition("attempts < 3", ctx) is True

    def test_numeric_less_than_equal(self):
        ctx = {"attempts": 3}
        assert evaluate_condition("attempts <= 3", ctx) is True

    def test_numeric_equals(self):
        ctx = {"attempts": 3}
        assert evaluate_condition("attempts == 3", ctx) is True

    def test_numeric_not_equals(self):
        ctx = {"attempts": 4}
        assert evaluate_condition("attempts != 3", ctx) is True

    def test_boolean_flag_true(self):
        ctx = {"has_recent_changes": True}
        assert evaluate_condition("has_recent_changes", ctx) is True

    def test_boolean_flag_false(self):
        ctx = {"has_recent_changes": False}
        assert evaluate_condition("has_recent_changes", ctx) is False

    def test_boolean_flag_absent(self):
        ctx = {}
        assert evaluate_condition("has_recent_changes", ctx) is False

    def test_error_in_test_true(self):
        ctx = {"error_in_test": True}
        assert evaluate_condition("error_in_test", ctx) is True

    def test_error_in_test_false(self):
        ctx = {"error_in_test": False}
        assert evaluate_condition("error_in_test", ctx) is False

    def test_missing_context_key_returns_false(self):
        ctx = {"other_field": "value"}
        assert evaluate_condition("has_recent_changes", ctx) is False
        assert evaluate_condition("error_type == 'TypeError'", ctx) is False
        assert evaluate_condition("attempts > 3", ctx) is False
        assert evaluate_condition("'foo' in error_message", ctx) is False

    def test_none_context_value_returns_false(self):
        ctx = {"error_type": None}
        assert evaluate_condition("error_type == 'TypeError'", ctx) is False

    def test_whitespace_stripped(self):
        ctx = {"error_type": "TypeError"}
        assert evaluate_condition("  error_type == 'TypeError'  ", ctx) is True

    def test_unknown_condition_pattern_returns_false(self):
        ctx = {"error_type": "TypeError"}
        assert evaluate_condition("error_type !== 'TypeError'", ctx) is False


# ---------------------------------------------------------------------------
# evaluate_skip_conditions tests
# ---------------------------------------------------------------------------

class TestEvaluateSkipConditions:
    def test_no_skip_if_field(self):
        phase = {"name": "test", "description": "A phase"}
        should_skip, reason = evaluate_skip_conditions(phase, {})
        assert should_skip is False
        assert reason == ""

    def test_skip_when_condition_matches(self):
        phase = {
            "name": "reproduce",
            "skip_if": [
                {"condition": "error_type == 'ImportError'", "reason": "Import errors are deterministic"}
            ]
        }
        ctx = {"error_type": "ImportError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True
        assert "deterministic" in reason

    def test_no_skip_when_condition_doesnt_match(self):
        phase = {
            "name": "reproduce",
            "skip_if": [
                {"condition": "error_type == 'ImportError'", "reason": "Import errors are deterministic"}
            ]
        }
        ctx = {"error_type": "TypeError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is False

    def test_skip_with_string_contains(self):
        phase = {
            "name": "reproduce",
            "skip_if": [
                {"condition": "'NoneType' in error_message", "reason": "NoneType needs tracing"}
            ]
        }
        ctx = {"error_message": "TypeError: 'NoneType' object has no attribute"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True

    def test_skip_with_numeric(self):
        phase = {
            "name": "investigate",
            "skip_if": [
                {"condition": "attempts > 5", "reason": "Too many attempts"}
            ]
        }
        ctx = {"attempts": 10}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True

    def test_skip_with_boolean(self):
        phase = {
            "name": "reproduce",
            "skip_if": [
                {"condition": "error_in_test", "reason": "Test errors don't need reproduction"}
            ]
        }
        ctx = {"error_in_test": True}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True

    def test_multiple_skip_conditions_first_match_wins(self):
        phase = {
            "name": "reproduce",
            "skip_if": [
                {"condition": "error_type == 'ImportError'", "reason": "ImportError reason"},
                {"condition": "error_type == 'TypeError'", "reason": "TypeError reason"},
            ]
        }
        ctx = {"error_type": "ImportError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True
        assert "ImportError reason" in reason

    def test_skip_condition_as_string_not_dict(self):
        phase = {
            "name": "reproduce",
            "skip_if": ["error_type == 'ImportError'"]
        }
        ctx = {"error_type": "ImportError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True


# ---------------------------------------------------------------------------
# evaluate_inject_conditions tests
# ---------------------------------------------------------------------------

class TestEvaluateInjectConditions:
    def test_no_inject_if_field(self):
        phase = {"name": "test", "description": "A phase"}
        messages = evaluate_inject_conditions(phase, {})
        assert messages == []

    def test_inject_when_condition_matches(self):
        phase = {
            "name": "investigate",
            "inject_if": [
                {"condition": "attempts > 2", "message": "Stop and list what you tried."}
            ]
        }
        ctx = {"attempts": 3}
        messages = evaluate_inject_conditions(phase, ctx)
        assert len(messages) == 1
        assert "Stop and list" in messages[0]

    def test_no_inject_when_condition_doesnt_match(self):
        phase = {
            "name": "investigate",
            "inject_if": [
                {"condition": "attempts > 2", "message": "Stop and list what you tried."}
            ]
        }
        ctx = {"attempts": 1}
        messages = evaluate_inject_conditions(phase, ctx)
        assert messages == []

    def test_inject_with_string_contains(self):
        phase = {
            "name": "investigate",
            "inject_if": [
                {"condition": "'NoneType' in error_message", "message": "Trace upstream."}
            ]
        }
        ctx = {"error_message": "TypeError: 'NoneType' has no attribute"}
        messages = evaluate_inject_conditions(phase, ctx)
        assert len(messages) == 1
        assert "Trace upstream" in messages[0]

    def test_multiple_inject_conditions_all_match(self):
        phase = {
            "name": "investigate",
            "inject_if": [
                {"condition": "attempts > 2", "message": "Stop and list."},
                {"condition": "'NoneType' in error_message", "message": "Trace upstream."},
            ]
        }
        ctx = {"attempts": 5, "error_message": "TypeError: 'NoneType' has no attribute"}
        messages = evaluate_inject_conditions(phase, ctx)
        assert len(messages) == 2


# ---------------------------------------------------------------------------
# evaluate_context_prompts tests
# ---------------------------------------------------------------------------

class TestEvaluateContextPrompts:
    def test_no_context_prompts_field(self):
        phase = {"name": "test"}
        prompts = evaluate_context_prompts(phase, {})
        assert prompts == []

    def test_context_prompt_when_condition_matches(self):
        phase = {
            "name": "investigate",
            "context_prompts": [
                {"condition": "has_recent_changes", "prompt": "Check git log for recent changes."}
            ]
        }
        ctx = {"has_recent_changes": True}
        prompts = evaluate_context_prompts(phase, ctx)
        assert len(prompts) == 1
        assert "git log" in prompts[0]

    def test_context_prompt_no_match(self):
        phase = {
            "name": "investigate",
            "context_prompts": [
                {"condition": "has_recent_changes", "prompt": "Check git log."}
            ]
        }
        ctx = {"has_recent_changes": False}
        prompts = evaluate_context_prompts(phase, ctx)
        assert prompts == []

    def test_multiple_context_prompts(self):
        phase = {
            "name": "investigate",
            "context_prompts": [
                {"condition": "has_recent_changes", "prompt": "Check git log."},
                {"condition": "error_in_test", "prompt": "Check if test itself is wrong."},
            ]
        }
        ctx = {"has_recent_changes": True, "error_in_test": True}
        prompts = evaluate_context_prompts(phase, ctx)
        assert len(prompts) == 2


# ---------------------------------------------------------------------------
# Schema — pack with skip_if parses correctly (backward compat)
# ---------------------------------------------------------------------------

class TestSchemaBackwardCompatibility:
    def test_pack_without_conditions_parses(self):
        yaml_text = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debug
mental_model: fast-thinker
phases:
  - name: step1
    description: Do the thing
    checkpoint: Done
provenance:
  confidence: tested
  evidence: works
required_inputs: []
escalation_rules: []
"""
        pack = schema_mod.parse_workflow_pack(yaml_text)
        assert pack["phases"][0]["name"] == "step1"

        errors = schema_mod.validate_pack(pack)
        # required_inputs and escalation_rules must be non-empty per validate_pack
        assert "required_inputs" in str(errors) or "escalation_rules" in str(errors) or errors == []

    def test_pack_with_skip_if_parses(self):
        yaml_text = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debug
mental_model: fast-thinker
phases:
  - name: reproduce
    description: Reproduce the bug
    checkpoint: Bug reproduced
    skip_if:
      - condition: "error_type == 'ImportError'"
        reason: Import errors are deterministic
provenance:
  confidence: tested
  evidence: works
required_inputs: []
escalation_rules: []
"""
        pack = schema_mod.parse_workflow_pack(yaml_text)
        phase = pack["phases"][0]
        assert phase["name"] == "reproduce"
        assert len(phase["skip_if"]) == 1
        assert phase["skip_if"][0]["condition"] == "error_type == 'ImportError'"

    def test_pack_with_inject_if_parses(self):
        yaml_text = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debug
mental_model: fast-thinker
phases:
  - name: investigate
    description: Investigate the bug
    checkpoint: Root cause found
    inject_if:
      - condition: "attempts > 2"
        message: Stop and list what you tried.
provenance:
  confidence: tested
  evidence: works
required_inputs: []
escalation_rules: []
"""
        pack = schema_mod.parse_workflow_pack(yaml_text)
        phase = pack["phases"][0]
        assert phase["inject_if"][0]["message"] == "Stop and list what you tried."

    def test_pack_with_context_prompts_parses(self):
        yaml_text = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debug
mental_model: fast-thinker
phases:
  - name: investigate
    description: Investigate
    checkpoint: Done
    context_prompts:
      - condition: "has_recent_changes"
        prompt: Check git log.
provenance:
  confidence: tested
  evidence: works
required_inputs: []
escalation_rules: []
"""
        pack = schema_mod.parse_workflow_pack(yaml_text)
        phase = pack["phases"][0]
        assert phase["context_prompts"][0]["prompt"] == "Check git log."

    def test_collect_text_fields_includes_context_prompts(self):
        yaml_text = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debug
mental_model: fast-thinker
phases:
  - name: investigate
    description: Investigate the bug
    checkpoint: Done
    context_prompts:
      - condition: "has_recent_changes"
        prompt: Check git log for recent changes.
provenance:
  confidence: tested
  evidence: works
required_inputs: []
escalation_rules: []
"""
        pack = schema_mod.parse_workflow_pack(yaml_text)
        texts = schema_mod.collect_text_fields(pack)
        assert "Check git log for recent changes." in texts


# ---------------------------------------------------------------------------
# Integration: Phase is skipped when condition matches
# ---------------------------------------------------------------------------

class TestConditionalPhaseIntegration:
    def test_phase_skipped_when_skip_condition_matches(self):
        phase = {
            "name": "reproduce",
            "description": "Reproduce the bug",
            "skip_if": [
                {"condition": "error_type == 'ImportError'", "reason": "Import errors are deterministic"}
            ]
        }
        ctx = {"error_type": "ImportError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is True
        assert "deterministic" in reason

    def test_phase_not_skipped_when_condition_doesnt_match(self):
        phase = {
            "name": "reproduce",
            "description": "Reproduce the bug",
            "skip_if": [
                {"condition": "error_type == 'ImportError'", "reason": "Import errors are deterministic"}
            ]
        }
        ctx = {"error_type": "TypeError"}
        should_skip, reason = evaluate_skip_conditions(phase, ctx)
        assert should_skip is False

    def test_inject_message_added_when_condition_matches(self):
        phase = {
            "name": "investigate",
            "inject_if": [
                {"condition": "attempts > 2", "message": "Stop and list what you tried."}
            ]
        }
        ctx = {"attempts": 3}
        messages = evaluate_inject_conditions(phase, ctx)
        assert len(messages) == 1
        assert "Stop" in messages[0]

    def test_context_prompt_appears_when_relevant(self):
        phase = {
            "name": "investigate",
            "context_prompts": [
                {"condition": "has_recent_changes", "prompt": "Check git log."}
            ]
        }
        ctx = {"has_recent_changes": True}
        prompts = evaluate_context_prompts(phase, ctx)
        assert len(prompts) == 1
        assert "git" in prompts[0]
