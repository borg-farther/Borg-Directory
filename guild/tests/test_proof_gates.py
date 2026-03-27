"""
Tests for guild/core/proof_gates.py — validate_proof_gates, compute_pack_tier,
compute_pack_tier_from_index, check_confidence_decay.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from guild.core.proof_gates import (
    CONFIDENCE_TTL_DAYS,
    _CONFIDENCE_DOWNGRADE,
    _REQUIRED_PACK_FIELDS,
    VALID_CONFIDENCE,
    check_confidence_decay,
    compute_pack_tier,
    compute_pack_tier_from_index,
    validate_proof_gates,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def base_pack(overrides: dict = None) -> dict:
    """Minimal valid workflow_pack with all required top-level fields."""
    pack = {
        "type": "workflow_pack",
        "version": "1.0",
        "id": "test-pack",
        "problem_class": "classification",
        "mental_model": "fast-thinker",
        "phases": [
            {
                "description": "Read the input",
                "checkpoint": "read_done",
                "prompts": ["Read {input}"],
                "anti_patterns": [],
            },
        ],
        "provenance": {
            "author": "test-agent",
            "created": "2025-01-01T00:00:00Z",
            "confidence": "guessed",
            "failure_cases": ["edge-case-input"],
        },
    }
    if overrides:
        pack.update(overrides)
    return pack


def base_feedback(overrides: dict = None) -> dict:
    fb = {
        "type": "feedback",
        "parent_artifact": "test-pack",
        "execution_log_hash": "abc123",
        "provenance": {
            "confidence": "guessed",
        },
    }
    if overrides:
        fb.update(overrides)
    return fb


# ---------------------------------------------------------------------------
# validate_proof_gates — workflow_pack
# ---------------------------------------------------------------------------

class TestValidateProofGatesPack:
    """workflow_pack proof-gate validation."""

    def test_minimal_guessed_pack_passes(self):
        """guessed: core fields + failure_cases >= 1 — no extra requirements."""
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "guessed", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert errors == [], f"unexpected errors: {errors}"

    def test_guessed_missing_author(self):
        pack = base_pack({"provenance": {"created": "2025-01-01", "confidence": "guessed", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("author" in e for e in errors)

    def test_guessed_missing_created(self):
        pack = base_pack({"provenance": {"author": "a", "confidence": "guessed", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("created" in e for e in errors)

    def test_guessed_missing_confidence(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("confidence" in e for e in errors)

    def test_guessed_missing_failure_cases(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "guessed"}})
        errors = validate_proof_gates(pack)
        assert any("failure_cases" in e for e in errors)

    def test_guessed_empty_failure_cases(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "guessed", "failure_cases": []}})
        errors = validate_proof_gates(pack)
        assert any("failure_cases" in e for e in errors)

    def test_guessed_invalid_confidence_value(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "random", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("Invalid" in e and "random" in e for e in errors)

    def test_inferred_missing_evidence(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "inferred", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("evidence" in e for e in errors)

    def test_inferred_with_evidence_passes(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "inferred", "evidence": "some rationale", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert errors == [], f"unexpected errors: {errors}"

    def test_tested_missing_examples(self):
        pack = base_pack({"provenance": {"author": "a", "created": "2025-01-01", "confidence": "tested", "evidence": "tested evidence", "failure_cases": ["x"]}})
        errors = validate_proof_gates(pack)
        assert any("examples" in e for e in errors)

    def test_tested_example_missing_fields(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "tested", "evidence": "tested evidence", "failure_cases": ["x"]},
            "feedback_agent": "agent://other",
            "examples": [{"problem": "p"}],  # missing solution and outcome
        })
        errors = validate_proof_gates(pack)
        assert any("solution" in e and "tested" in e for e in errors)
        assert any("outcome" in e and "tested" in e for e in errors)

    def test_tested_missing_feedback_agent(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "tested", "evidence": "tested evidence", "failure_cases": ["x"]},
            "examples": [{"problem": "p", "solution": "s", "outcome": "o"}],
        })
        errors = validate_proof_gates(pack)
        assert any("feedback_agent" in e for e in errors)

    def test_tested_minimal_passes(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "tested", "evidence": "tested evidence", "failure_cases": ["x"]},
            "feedback_agent": "agent://other",
            "examples": [{"problem": "p", "solution": "s", "outcome": "o"}],
        })
        errors = validate_proof_gates(pack)
        assert errors == [], f"unexpected errors: {errors}"

    def test_validated_missing_evaluator_rubric(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "validated", "evidence": "validated evidence", "failure_cases": ["x"]},
            "operators": ["op1", "op2", "op3"],
            "examples": [
                {"problem": "p", "solution": "s", "outcome": "o", "agent": "agent://hermes"},
                {"problem": "p2", "solution": "s2", "outcome": "o2", "agent": "agent://other"},
            ],
        })
        errors = validate_proof_gates(pack)
        assert any("evaluator_rubric" in e for e in errors)

    def test_validated_too_few_examples(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "validated", "evidence": "validated evidence", "failure_cases": ["x"]},
            "evaluator_rubric": "rubric content",
            "operators": ["op1", "op2", "op3"],
            "examples": [{"problem": "p", "solution": "s", "outcome": "o", "agent": "agent://hermes"}],  # only 1
        })
        errors = validate_proof_gates(pack)
        assert any("examples" in e and "2" in e for e in errors)

    def test_validated_same_agent_examples(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "validated", "evidence": "validated evidence", "failure_cases": ["x"]},
            "evaluator_rubric": "rubric content",
            "operators": ["op1", "op2", "op3"],
            "examples": [
                {"problem": "p", "solution": "s", "outcome": "o", "agent": "agent://hermes"},
                {"problem": "p2", "solution": "s2", "outcome": "o2", "agent": "agent://hermes"},  # same agent
            ],
        })
        errors = validate_proof_gates(pack)
        assert any("independent agents" in e for e in errors)

    def test_validated_too_few_operators(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "validated", "evidence": "validated evidence", "failure_cases": ["x"]},
            "evaluator_rubric": "rubric content",
            "operators": ["op1", "op2"],  # only 2, need 3+
            "examples": [
                {"problem": "p", "solution": "s", "outcome": "o", "agent": "agent://hermes"},
                {"problem": "p2", "solution": "s2", "outcome": "o2", "agent": "agent://other"},
            ],
        })
        errors = validate_proof_gates(pack)
        assert any("operators" in e and "3" in e for e in errors)

    def test_validated_minimal_passes(self):
        pack = base_pack({
            "provenance": {"author": "a", "created": "2025-01-01", "confidence": "validated", "evidence": "validated evidence", "failure_cases": ["x"]},
            "evaluator_rubric": "rubric content",
            "operators": ["op1", "op2", "op3"],
            "examples": [
                {"problem": "p", "solution": "s", "outcome": "o", "agent": "agent://hermes"},
                {"problem": "p2", "solution": "s2", "outcome": "o2", "agent": "agent://other"},
            ],
        })
        errors = validate_proof_gates(pack)
        assert errors == [], f"unexpected errors: {errors}"

    def test_unknown_artifact_type(self):
        errors = validate_proof_gates({"type": "unknown"})
        assert any("Unknown artifact type" in e for e in errors)

    def test_missing_required_top_level_fields(self):
        pack = base_pack()
        del pack["problem_class"]
        errors = validate_proof_gates(pack)
        assert any("problem_class" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_proof_gates — feedback
# ---------------------------------------------------------------------------

class TestValidateProofGatesFeedback:
    def test_minimal_feedback_passes(self):
        fb = base_feedback()
        errors = validate_proof_gates(fb)
        assert errors == [], f"unexpected errors: {errors}"

    def test_feedback_missing_parent_artifact(self):
        fb = base_feedback()
        del fb["parent_artifact"]
        errors = validate_proof_gates(fb)
        assert any("parent_artifact" in e for e in errors)

    def test_feedback_missing_execution_log_hash(self):
        fb = base_feedback()
        del fb["execution_log_hash"]
        errors = validate_proof_gates(fb)
        assert any("execution_log_hash" in e for e in errors)

    def test_feedback_missing_confidence(self):
        fb = base_feedback()
        fb["provenance"] = {}
        errors = validate_proof_gates(fb)
        assert any("confidence" in e for e in errors)


# ---------------------------------------------------------------------------
# compute_pack_tier
# ---------------------------------------------------------------------------

class TestComputePackTier:
    def test_core_tier_full(self):
        pack = {
            "provenance": {
                "confidence": "validated",
                "author_agent": "agent://hermes/core",
                "evidence": "multiple successful runs",
                "failure_cases": ["case1", "case2", "case3"],
            },
            "examples": [{"problem": "p", "solution": "s", "outcome": "o"}],
        }
        assert compute_pack_tier(pack) == "CORE"

    def test_core_tier_no_examples_field(self):
        """CORE is allowed when examples field is absent entirely."""
        pack = {
            "provenance": {
                "confidence": "validated",
                "author_agent": "agent://hermes/core",
                "evidence": "runs",
                "failure_cases": ["a", "b", "c"],
            },
        }
        assert compute_pack_tier(pack) == "CORE"

    def test_core_tier_empty_examples_fails(self):
        """CORE requires examples to be absent OR non-empty."""
        pack = {
            "provenance": {
                "confidence": "validated",
                "author_agent": "agent://hermes/core",
                "evidence": "runs",
                "failure_cases": ["a", "b", "c"],
            },
            "examples": [],
        }
        assert compute_pack_tier(pack) == "VALIDATED"

    def test_validated_tier_tested_confidence(self):
        pack = {
            "provenance": {
                "confidence": "tested",
                "evidence": "some evidence",
                "failure_cases": ["a"],
            },
        }
        assert compute_pack_tier(pack) == "VALIDATED"

    def test_validated_tier_validated_confidence(self):
        pack = {
            "provenance": {
                "confidence": "validated",
                "evidence": "evidence",
                "failure_cases": ["a"],
            },
        }
        assert compute_pack_tier(pack) == "VALIDATED"

    def test_validated_needs_evidence(self):
        pack = {
            "provenance": {
                "confidence": "tested",
                # no evidence
                "failure_cases": ["a"],
            },
        }
        assert compute_pack_tier(pack) == "COMMUNITY"

    def test_validated_needs_failure_cases(self):
        pack = {
            "provenance": {
                "confidence": "tested",
                "evidence": "evidence",
                # no failure_cases
            },
        }
        assert compute_pack_tier(pack) == "COMMUNITY"

    def test_community_falls_through(self):
        pack = {
            "provenance": {
                "confidence": "guessed",
                "evidence": "",
                "failure_cases": [],
            },
        }
        assert compute_pack_tier(pack) == "COMMUNITY"

    def test_hermes_agent_must_start_with_agent_hermes(self):
        pack = {
            "provenance": {
                "confidence": "validated",
                "author_agent": "agent://other/pack",
                "evidence": "e",
                "failure_cases": ["a", "b", "c"],
            },
        }
        assert compute_pack_tier(pack) == "VALIDATED"


# ---------------------------------------------------------------------------
# compute_pack_tier_from_index
# ---------------------------------------------------------------------------

class TestComputePackTierFromIndex:
    def test_core_from_index(self):
        entry = {
            "name": "my-pack",
            "confidence": "validated",
            "author_agent": "agent://hermes/core",
            "evidence": "evidence",
            "failure_cases": ["a", "b", "c"],
            "examples": [{"problem": "p", "solution": "s", "outcome": "o"}],
        }
        assert compute_pack_tier_from_index(entry) == "CORE"

    def test_validated_from_index(self):
        entry = {
            "name": "my-pack",
            "confidence": "tested",
            "evidence": "evidence",
            "failure_cases": ["a"],
        }
        assert compute_pack_tier_from_index(entry) == "VALIDATED"

    def test_community_from_index(self):
        entry = {
            "name": "my-pack",
            "confidence": "guessed",
            "evidence": "",
            "failure_cases": [],
        }
        assert compute_pack_tier_from_index(entry) == "COMMUNITY"


# ---------------------------------------------------------------------------
# check_confidence_decay
# ---------------------------------------------------------------------------

class TestCheckConfidenceDecay:
    def _make_pack(self, confidence: str, created_days_ago: int = None):
        """Build a pack dict with a created timestamp."""
        if created_days_ago is None:
            created = datetime.now(timezone.utc).isoformat()
        else:
            created = (datetime.now(timezone.utc) - timedelta(days=created_days_ago)).isoformat()
        return {
            "provenance": {
                "confidence": confidence,
                "created": created,
            },
        }

    def test_no_created_timestamp(self):
        pack = {"provenance": {"confidence": "validated"}}
        result = check_confidence_decay(pack)
        assert result["decayed"] is False
        assert result["age_days"] == -1
        assert "No created timestamp" in result["warning"]

    def test_invalid_timestamp(self):
        pack = {"provenance": {"confidence": "validated", "created": "not-a-date"}}
        result = check_confidence_decay(pack)
        assert result["decayed"] is False
        assert result["age_days"] == -1
        assert "Invalid created timestamp" in result["warning"]

    def test_validated_within_ttl(self):
        pack = self._make_pack("validated", created_days_ago=100)
        result = check_confidence_decay(pack)
        assert result["confidence"] == "validated"
        assert result["decayed"] is False
        assert result["age_days"] == 100

    def test_validated_expired(self):
        pack = self._make_pack("validated", created_days_ago=400)
        result = check_confidence_decay(pack)
        assert result["decayed"] is True
        assert result["confidence"] == "tested"
        assert result["original_confidence"] == "validated"
        assert "decayed from validated to tested" in result["warning"]

    def test_tested_expired(self):
        pack = self._make_pack("tested", created_days_ago=200)
        result = check_confidence_decay(pack)
        assert result["decayed"] is True
        assert result["confidence"] == "inferred"
        assert "decayed from tested to inferred" in result["warning"]

    def test_inferred_expired(self):
        pack = self._make_pack("inferred", created_days_ago=100)
        result = check_confidence_decay(pack)
        assert result["decayed"] is True
        assert result["confidence"] == "guessed"

    def test_guessed_expired(self):
        pack = self._make_pack("guessed", created_days_ago=40)
        result = check_confidence_decay(pack)
        assert result["decayed"] is True
        assert result["confidence"] == "expired"

    def test_exact_ttl_boundary_does_not_decay(self):
        """At exactly the TTL boundary, decay should NOT trigger."""
        ttl = CONFIDENCE_TTL_DAYS["guessed"]
        pack = self._make_pack("guessed", created_days_ago=ttl)
        result = check_confidence_decay(pack)
        assert result["decayed"] is False
        assert result["confidence"] == "guessed"

    def test_one_day_past_ttl_decays(self):
        ttl = CONFIDENCE_TTL_DAYS["guessed"]
        pack = self._make_pack("guessed", created_days_ago=ttl + 1)
        result = check_confidence_decay(pack)
        assert result["decayed"] is True
        assert result["confidence"] == "expired"

    def test_unknown_confidence_no_decay(self):
        pack = self._make_pack("unknown-tier", created_days_ago=1000)
        result = check_confidence_decay(pack)
        assert result["decayed"] is False
        assert result["confidence"] == "unknown-tier"

    def test_warning_message_contains_age(self):
        pack = self._make_pack("validated", created_days_ago=400)
        result = check_confidence_decay(pack)
        assert "400 days ago" in result["warning"]
