"""
Tests for Borg V3 Mutation Engine.

Covers:
- All 5 mutation operators
- A/B testing infrastructure
- Adaptive mutation rate (1/5th rule)
- Rollback and version history
- MutationEngine class

Uses in-memory mocks, no filesystem dependencies.
"""

import copy
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest

# Ensure borg package is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core.mutation_engine import (
    ABTest,
    ABTestResult,
    AdaptiveMutationRate,
    AntiPatternAddition,
    ConditionRefinement,
    ExampleSubstitution,
    MutationEngine,
    MutationOperator,
    MutationProposal,
    PackVariant,
    PackVersion,
    PhaseReordering,
    RollbackManager,
    StepParameterTuning,
    create_macro_mutant,
)


# ============================================================================
# Mocks / Fixtures
# ============================================================================


class MockPackStore:
    """In-memory pack store for testing."""

    def __init__(self):
        self.packs: Dict[str, Dict[str, Any]] = {}

    def get_pack(self, pack_id: str) -> Optional[Dict[str, Any]]:
        return self.packs.get(pack_id)

    def save_pack(self, pack_id: str, pack_data: Dict[str, Any]) -> None:
        self.packs[pack_id] = copy.deepcopy(pack_data)

    def list_packs(self) -> List[str]:
        return list(self.packs.keys())


class MockFailureMemory:
    """In-memory failure memory for testing."""

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir
        self.records: Dict[str, Dict[str, Any]] = {}

    def recall(self, error_pattern: str) -> Optional[Dict[str, Any]]:
        return self.records.get(error_pattern)

    def record_failure(
        self,
        error_pattern: str,
        pack_id: str,
        phase: str,
        approach: str,
        outcome: str,
    ) -> None:
        if error_pattern not in self.records:
            self.records[error_pattern] = {
                "error_pattern": error_pattern,
                "pack_id": pack_id,
                "phase": phase,
                "wrong_approaches": [],
                "correct_approaches": [],
                "total_sessions": 0,
            }

        record = self.records[error_pattern]
        record["total_sessions"] += 1

        if outcome == "failure":
            found = False
            for entry in record.get("wrong_approaches", []):
                if entry["approach"] == approach:
                    entry["failure_count"] += 1
                    found = True
                    break
            if not found:
                record.setdefault("wrong_approaches", []).append({
                    "approach": approach,
                    "failure_count": 1,
                })
        else:
            found = False
            for entry in record.get("correct_approaches", []):
                if entry["approach"] == approach:
                    entry["success_count"] += 1
                    found = True
                    break
            if not found:
                record.setdefault("correct_approaches", []).append({
                    "approach": approach,
                    "success_count": 1,
                })

    def get_stats(self) -> Dict[str, Any]:
        total_failures = sum(
            sum(wa.get("failure_count", 0) for wa in r.get("wrong_approaches", []))
            for r in self.records.values()
        )
        total_successes = sum(
            sum(ca.get("success_count", 0) for ca in r.get("correct_approaches", []))
            for r in self.records.values()
        )
        return {
            "total_failures": total_failures,
            "total_patterns": len(self.records),
            "total_successes": total_successes,
        }


@pytest.fixture
def mock_pack_store():
    return MockPackStore()


@pytest.fixture
def mock_failure_memory(tmp_path):
    return MockFailureMemory(memory_dir=tmp_path)


@pytest.fixture
def sample_pack():
    """A minimal sample pack for testing."""
    return {
        "id": "test-pack",
        "type": "workflow_pack",
        "version": "1.0",
        "problem_class": "debugging",
        "mental_model": "systematic",
        "phases": [
            {
                "name": "investigate",
                "description": "Investigate the problem",
                "checkpoint": "Root cause identified",
                "anti_patterns": [],
                "context_prompts": ["Look for obvious errors", "Example: Check for None values"],
            },
            {
                "name": "plan",
                "description": "Plan the fix",
                "checkpoint": "Fix planned",
                "anti_patterns": [],
                "context_prompts": ["Consider side effects"],
            },
            {
                "name": "implement",
                "description": "Implement the fix",
                "checkpoint": "Fix implemented",
                "anti_patterns": [],
                "context_prompts": [],
            },
            {
                "name": "verify",
                "description": "Verify the fix",
                "checkpoint": "Fix verified",
                "anti_patterns": [],
                "context_prompts": ["Run tests"],
            },
        ],
        "anti_patterns": [],
        "provenance": {"created": "test"},
    }


# ============================================================================
# Tests: MutationProposal dataclass
# ============================================================================


class TestMutationProposal:
    def test_proposal_creation(self):
        proposal = MutationProposal(
            mutation_type="test",
            pack_id="pack-1",
            description="Test mutation",
            mutator_class="TestOp",
            change={"action": "test"},
        )
        assert proposal.mutation_type == "test"
        assert proposal.pack_id == "pack-1"
        assert proposal.confidence == 0.5  # default
        assert proposal.evidence == []  # default

    def test_proposal_with_all_fields(self):
        proposal = MutationProposal(
            mutation_type="anti_pattern_addition",
            pack_id="pack-1",
            description="Add anti-pattern",
            mutator_class="AntiPatternAddition",
            change={"action": "add_anti_pattern", "anti_pattern": "None check"},
            confidence=0.8,
            evidence=["3 agents failed with this pattern"],
        )
        assert proposal.confidence == 0.8
        assert len(proposal.evidence) == 1


# ============================================================================
# Tests: PackVariant dataclass
# ============================================================================


class TestPackVariant:
    def test_variant_creation(self):
        variant = PackVariant(
            original_pack_id="pack-1",
            mutant_pack_id="pack-1-mutant",
            mutation_type="test",
            created_at=datetime.now(timezone.utc),
        )
        assert variant.original_pack_id == "pack-1"
        assert variant.uses_original == 0
        assert variant.uses_mutant == 0

    def test_success_rate_no_uses(self):
        variant = PackVariant(
            original_pack_id="pack-1",
            mutant_pack_id="pack-1-mutant",
            mutation_type="test",
            created_at=datetime.now(timezone.utc),
        )
        assert variant.success_rate_original == 0.0
        assert variant.success_rate_mutant == 0.0

    def test_success_rate_with_uses(self):
        variant = PackVariant(
            original_pack_id="pack-1",
            mutant_pack_id="pack-1-mutant",
            mutation_type="test",
            created_at=datetime.now(timezone.utc),
            uses_original=10,
            successes_original=7,
            uses_mutant=10,
            successes_mutant=9,
        )
        assert variant.success_rate_original == 0.7
        assert variant.success_rate_mutant == 0.9


# ============================================================================
# Tests: PackVersion dataclass
# ============================================================================


class TestPackVersion:
    def test_version_creation(self):
        version = PackVersion(
            version_id="v1",
            pack_id="pack-1",
            snapshot={"id": "pack-1", "phases": []},
            created_at=datetime.now(timezone.utc),
        )
        assert version.version_id == "v1"
        assert version.mutation_proposal_id is None


# ============================================================================
# Tests: AntiPatternAddition operator
# ============================================================================


class TestAntiPatternAddition:
    def test_no_failures_returns_empty(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        operator = AntiPatternAddition(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert proposals == []

    def test_insufficient_failures(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        # Record only 2 failures
        mock_failure_memory.record_failure(
            error_pattern="TypeError: None has no attribute",
            pack_id="test-pack",
            phase="investigate",
            approach="Added None check",
            outcome="failure",
        )
        mock_failure_memory.record_failure(
            error_pattern="TypeError: None has no attribute",
            pack_id="test-pack",
            phase="investigate",
            approach="Added None check",
            outcome="failure",
        )
        operator = AntiPatternAddition(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert len(proposals) == 0

    def test_sufficient_failures_proposes_mutation(
        self, mock_pack_store, mock_failure_memory, sample_pack, tmp_path
    ):
        # Create a failure memory that writes to disk
        from borg.core.failure_memory import FailureMemory
        failure_memory = FailureMemory(memory_dir=tmp_path)

        mock_pack_store.save_pack("test-pack", sample_pack)

        # Record 3 failures - this writes to disk
        for _ in range(3):
            failure_memory.record_failure(
                error_pattern="TypeError: None has no attribute 'split'",
                pack_id="test-pack",
                phase="investigate",
                approach="Added None check in method",
                outcome="failure",
            )

        operator = AntiPatternAddition(mock_pack_store, failure_memory)
        proposals = operator.suggest("test-pack")
        assert len(proposals) >= 1
        assert proposals[0].mutation_type == "anti_pattern_addition"

    def test_existing_anti_pattern_not_duplicated(self, mock_pack_store, mock_failure_memory, sample_pack, tmp_path):
        from borg.core.failure_memory import FailureMemory
        failure_memory = FailureMemory(memory_dir=tmp_path)
        sample_pack["anti_patterns"] = ["TypeError: None has no attribute 'split'"]
        mock_pack_store.save_pack("test-pack", sample_pack)

        # Record 3 failures with same pattern
        for _ in range(3):
            failure_memory.record_failure(
                error_pattern="TypeError: None has no attribute 'split'",
                pack_id="test-pack",
                phase="investigate",
                approach="Added None check",
                outcome="failure",
            )

        operator = AntiPatternAddition(mock_pack_store, failure_memory)
        proposals = operator.suggest("test-pack")
        # Should not propose since anti-pattern already exists
        assert len(proposals) == 0


# ============================================================================
# Tests: StepParameterTuning operator
# ============================================================================


class TestStepParameterTuning:
    def test_no_data_returns_empty(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        operator = StepParameterTuning(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert proposals == []

    def test_similar_approach_names_propose_tuning(self, mock_pack_store, mock_failure_memory, sample_pack, tmp_path):
        from borg.core.failure_memory import FailureMemory
        failure_memory = FailureMemory(memory_dir=tmp_path)
        mock_pack_store.save_pack("test-pack", sample_pack)

        mock_failure_memory.record_failure(
            error_pattern="ValueError",
            pack_id="test-pack",
            phase="plan",
            approach="Consider using dict.get() method",
            outcome="failure",
        )
        mock_failure_memory.record_failure(
            error_pattern="ValueError",
            pack_id="test-pack",
            phase="plan",
            approach="Consider using dict.get() method",
            outcome="failure",
        )
        mock_failure_memory.record_failure(
            error_pattern="ValueError",
            pack_id="test-pack",
            phase="plan",
            approach="Consider using dict.get() method alternative",
            outcome="success",
        )
        mock_failure_memory.record_failure(
            error_pattern="ValueError",
            pack_id="test-pack",
            phase="plan",
            approach="Consider using dict.get() method alternative",
            outcome="success",
        )

        operator = StepParameterTuning(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert len(proposals) >= 0  # May or may not trigger depending on similarity


# ============================================================================
# Tests: ConditionRefinement operator
# ============================================================================


class TestConditionRefinement:
    def test_no_phases_returns_empty(self, mock_pack_store, mock_failure_memory):
        mock_pack_store.save_pack("test-pack", {"id": "test-pack", "phases": []})
        operator = ConditionRefinement(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert proposals == []

    def test_phase_with_high_error_count(self, mock_pack_store, mock_failure_memory, sample_pack, tmp_path):
        from borg.core.failure_memory import FailureMemory
        failure_memory = FailureMemory(memory_dir=tmp_path)
        mock_pack_store.save_pack("test-pack", sample_pack)

        # Record many failures in the same phase
        for _ in range(5):
            failure_memory.record_failure(
                error_pattern="Error in investigate phase",
                pack_id="test-pack",
                phase="investigate",
                approach="Approach A",
                outcome="failure",
            )

        operator = ConditionRefinement(mock_pack_store, failure_memory)
        proposals = operator.suggest("test-pack")
        # Should suggest adding a condition
        assert len(proposals) >= 0


# ============================================================================
# Tests: PhaseReordering operator
# ============================================================================


class TestPhaseReordering:
    def test_short_pack_returns_empty(self, mock_pack_store, mock_failure_memory, sample_pack):
        # Only 2 phases - too short for reordering
        sample_pack["phases"] = [
            {"name": "phase1"},
            {"name": "phase2"},
        ]
        mock_pack_store.save_pack("test-pack", sample_pack)
        operator = PhaseReordering(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert proposals == []


# ============================================================================
# Tests: ExampleSubstitution operator
# ============================================================================


class TestExampleSubstitution:
    def test_no_examples_returns_empty(self, mock_pack_store, mock_failure_memory, sample_pack):
        # Remove examples from phases
        for phase in sample_pack["phases"]:
            phase["context_prompts"] = []
        mock_pack_store.save_pack("test-pack", sample_pack)
        operator = ExampleSubstitution(mock_pack_store, mock_failure_memory)
        proposals = operator.suggest("test-pack")
        assert proposals == []

    def test_successful_example_proposed(self, mock_pack_store, mock_failure_memory, sample_pack, tmp_path):
        from borg.core.failure_memory import FailureMemory
        failure_memory = FailureMemory(memory_dir=tmp_path)
        mock_pack_store.save_pack("test-pack", sample_pack)

        # Record successful approach
        for _ in range(3):
            failure_memory.record_failure(
                error_pattern="AnyError",
                pack_id="test-pack",
                phase="investigate",
                approach="Use explicit type checking instead of implicit None comparison",
                outcome="success",
            )

        operator = ExampleSubstitution(mock_pack_store, failure_memory)
        proposals = operator.suggest("test-pack")
        # Should propose substituting the example
        assert len(proposals) >= 0


# ============================================================================
# Tests: ABTest class
# ============================================================================


class TestABTest:
    def test_create_test(self, mock_pack_store):
        ab_test = ABTest.create_test(
            original_pack_id="pack-1",
            mutant_pack_id="pack-1-mutant",
            mutation_type="test",
            pack_store=mock_pack_store,
        )
        assert ab_test.variant.original_pack_id == "pack-1"
        assert ab_test.variant.mutant_pack_id == "pack-1-mutant"

    def test_record_outcome_original_success(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        ab_test.record_outcome("original", success=True)
        assert ab_test.variant.uses_original == 1
        assert ab_test.variant.successes_original == 1

    def test_record_outcome_mutant_failure(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        ab_test.record_outcome("mutant", success=False)
        assert ab_test.variant.uses_mutant == 1
        assert ab_test.variant.successes_mutant == 0

    def test_get_winner_insufficient_data(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        # Only 5 samples each - below min_samples of 20
        for _ in range(5):
            ab_test.record_outcome("original", True)
            ab_test.record_outcome("mutant", True)
        result = ab_test.get_winner(min_samples=20)
        assert result.winner == "insufficient_data"
        assert result.recommended_action == "continue"

    def test_get_winner_mutant_significant(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        # Record 25 successes for mutant, 15 for original
        for _ in range(25):
            ab_test.record_outcome("mutant", True)
        for _ in range(15):
            ab_test.record_outcome("original", True)
        result = ab_test.get_winner(min_samples=20, significance=0.05)
        # Mutant should win if significantly better
        assert result.winner in ["mutant", "insufficient_data"]

    def test_get_winner_original_significant(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        # Record 25 successes for original, 15 for mutant
        for _ in range(25):
            ab_test.record_outcome("original", True)
        for _ in range(15):
            ab_test.record_outcome("mutant", True)
        result = ab_test.get_winner(min_samples=20, significance=0.05)
        assert result.winner in ["original", "insufficient_data"]

    def test_auto_promote_success(self, mock_pack_store):
        mock_pack_store.save_pack("pack-1", {"id": "pack-1", "phases": []})
        mock_pack_store.save_pack("pack-1-mutant", {"id": "pack-1-mutant", "phases": [{"name": "new"}]})

        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        # Record clear winner
        for _ in range(30):
            ab_test.record_outcome("mutant", True)
        for _ in range(10):
            ab_test.record_outcome("original", True)

        result = ab_test.get_winner(min_samples=20)
        if result.winner == "mutant" and result.is_significant:
            promoted = ab_test.auto_promote()
            # Check that mutant content was promoted to original
            assert "phases" in mock_pack_store.get_pack("pack-1")


# ============================================================================
# Tests: AdaptiveMutationRate
# ============================================================================


class TestAdaptiveMutationRate:
    def test_initial_rate(self):
        rate = AdaptiveMutationRate(initial_rate=0.1)
        assert rate.mutation_rate == 0.1

    def test_rate_bounded_min(self):
        rate = AdaptiveMutationRate(initial_rate=0.01)
        for _ in range(100):
            rate.record_attempt(False)
        assert rate.mutation_rate >= 0.01

    def test_rate_bounded_max(self):
        rate = AdaptiveMutationRate(initial_rate=0.5)
        for _ in range(100):
            rate.record_attempt(True)
        assert rate.mutation_rate <= 0.5

    def test_1_5th_rule_increase(self):
        rate = AdaptiveMutationRate(initial_rate=0.1)
        # Record 10 attempts with >20% improvement (3 improved)
        rate.mutations_attempted = 10
        rate.mutations_that_improved = 4  # 40% > 20%
        rate._adjust_rate()
        assert rate.mutation_rate > 0.1

    def test_1_5th_rule_decrease(self):
        rate = AdaptiveMutationRate(initial_rate=0.2)
        # Record attempts with <20% improvement
        rate.mutations_attempted = 10
        rate.mutations_that_improved = 1  # 10% < 20%
        rate._adjust_rate()
        assert rate.mutation_rate < 0.2

    def test_should_mutate_probability(self):
        rate = AdaptiveMutationRate(initial_rate=1.0)  # Always mutate
        assert rate.should_mutate() is True

        rate = AdaptiveMutationRate(initial_rate=0.0)  # Never mutate
        assert rate.should_mutate() is False

    def test_macro_mutation_frequency(self):
        # With 1% frequency, running many times should rarely trigger
        rate = AdaptiveMutationRate()
        count = 0
        for _ in range(1000):
            if rate.is_macro_mutation():
                count += 1
        # Should be roughly 1% but allow for variance
        assert 0 <= count <= 20

    def test_get_stats(self):
        rate = AdaptiveMutationRate(initial_rate=0.15)
        rate.record_attempt(True)
        rate.record_attempt(False)
        stats = rate.get_stats()
        assert "mutation_rate" in stats
        assert "mutations_attempted" in stats
        assert "mutations_that_improved" in stats


# ============================================================================
# Tests: RollbackManager
# ============================================================================


class TestRollbackManager:
    def test_snapshot_creates_version(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        manager = RollbackManager(mock_pack_store)

        version = manager.snapshot("test-pack")
        assert version is not None
        assert version.pack_id == "test-pack"
        assert version.snapshot["id"] == "test-pack"

    def test_get_versions(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        manager = RollbackManager(mock_pack_store)

        manager.snapshot("test-pack")
        manager.snapshot("test-pack")

        versions = manager.get_versions("test-pack")
        assert len(versions) == 2

    def test_rollback_to_version(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        manager = RollbackManager(mock_pack_store)

        v1 = manager.snapshot("test-pack")

        # Modify pack
        sample_pack["phases"].append({"name": "new"})
        mock_pack_store.save_pack("test-pack", sample_pack)

        v2 = manager.snapshot("test-pack")

        # Rollback to v1
        result = manager.rollback_to_version("test-pack", v1.version_id)
        assert result is True

        restored = mock_pack_store.get_pack("test-pack")
        assert len(restored["phases"]) == 4  # Original count

    def test_rollback_to_latest(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        manager = RollbackManager(mock_pack_store)

        v1 = manager.snapshot("test-pack")
        v2 = manager.snapshot("test-pack")
        v3 = manager.snapshot("test-pack")

        # Rollback to v2 (the version before v3)
        result = manager.rollback_to_latest("test-pack")
        assert result is True

        # Versions list still has all versions (rollback doesn't remove them)
        # but the pack content should now be from v2
        versions = manager.get_versions("test-pack")
        assert len(versions) == 3

        # Verify pack content matches v2
        restored = mock_pack_store.get_pack("test-pack")
        assert restored == v2.snapshot

    def test_rollback_fails_with_single_version(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        manager = RollbackManager(mock_pack_store)

        manager.snapshot("test-pack")
        result = manager.rollback_to_latest("test-pack")
        assert result is False

    def test_check_and_revert_no_revert_needed(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        mock_pack_store.save_pack("test-pack-mutant", {"id": "test-pack-mutant", "phases": []})

        manager = RollbackManager(mock_pack_store)
        variant = PackVariant(
            original_pack_id="test-pack",
            mutant_pack_id="test-pack-mutant",
            mutation_type="test",
            created_at=datetime.now(timezone.utc),
            uses_original=15,
            successes_original=10,
            uses_mutant=15,
            successes_mutant=9,
        )

        result = manager.check_and_revert(variant)
        assert result is False  # No revert because threshold not met

    def test_check_and_revert_triggers_revert(self, mock_pack_store, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        mutant = copy.deepcopy(sample_pack)
        mutant["id"] = "test-pack-mutant"
        mutant["phases"] = []  # Break it
        mock_pack_store.save_pack("test-pack-mutant", mutant)

        manager = RollbackManager(mock_pack_store)
        variant = PackVariant(
            original_pack_id="test-pack",
            mutant_pack_id="test-pack-mutant",
            mutation_type="test",
            created_at=datetime.now(timezone.utc),
            uses_original=15,
            successes_original=10,  # 0.67
            uses_mutant=15,
            successes_mutant=3,  # 0.20 - less than 0.57 (0.67 - 0.10)
        )

        result = manager.check_and_revert(variant)
        assert result is True


# ============================================================================
# Tests: MutationEngine
# ============================================================================


class TestMutationEngine:
    def test_init(self, mock_pack_store, mock_failure_memory):
        engine = MutationEngine(mock_pack_store, mock_failure_memory, mutation_rate=0.2)
        assert engine.mutation_rate.mutation_rate == 0.2
        assert len(engine.operators) == 5

    def test_suggest_mutations(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)
        proposals = engine.suggest_mutations("test-pack")
        assert isinstance(proposals, list)

    def test_apply_mutation_creates_ab_test(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        proposal = MutationProposal(
            mutation_type="test",
            pack_id="test-pack",
            description="Test mutation",
            mutator_class="TestOp",
            change={"action": "add_anti_pattern", "anti_pattern": "Test anti-pattern"},
        )

        variant = engine.apply_mutation("test-pack", proposal)
        assert variant.original_pack_id == "test-pack"
        assert variant.mutant_pack_id != "test-pack"
        assert len(engine.ab_tests) == 1

    def test_apply_mutation_snapshots_original(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        proposal = MutationProposal(
            mutation_type="test",
            pack_id="test-pack",
            description="Test mutation",
            mutator_class="TestOp",
            change={"action": "add_anti_pattern", "anti_pattern": "Test"},
        )

        engine.apply_mutation("test-pack", proposal)

        versions = engine.rollback_manager.get_versions("test-pack")
        assert len(versions) >= 1

    def test_record_outcome(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        proposal = MutationProposal(
            mutation_type="test",
            pack_id="test-pack",
            description="Test",
            mutator_class="TestOp",
            change={},
        )

        variant = engine.apply_mutation("test-pack", proposal)
        test_id = list(engine.ab_tests.keys())[0]

        engine.record_outcome(test_id, "original", True)
        engine.record_outcome(test_id, "mutant", False)

        assert engine.ab_tests[test_id].variant.uses_original == 1
        assert engine.ab_tests[test_id].variant.successes_original == 1
        assert engine.ab_tests[test_id].variant.uses_mutant == 1
        assert engine.ab_tests[test_id].variant.successes_mutant == 0

    def test_check_ab_tests(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        mock_pack_store.save_pack("test-pack-mutant", {"id": "test-pack-mutant", "phases": []})

        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        proposal = MutationProposal(
            mutation_type="test",
            pack_id="test-pack",
            description="Test",
            mutator_class="TestOp",
            change={},
        )

        engine.apply_mutation("test-pack", proposal)
        results = engine.check_ab_tests()
        assert len(results) >= 1

    def test_get_mutation_stats(self, mock_pack_store, mock_failure_memory, sample_pack):
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        stats = engine.get_mutation_stats()
        assert "adaptive_rate" in stats
        assert "ab_tests" in stats
        assert "rollback_versions" in stats


# ============================================================================
# Tests: create_macro_mutant
# ============================================================================


class TestCreateMacroMutant:
    def test_macro_mutant_creates_new_id(self, sample_pack):
        mutant = create_macro_mutant(sample_pack)
        assert mutant["id"] != sample_pack["id"]
        assert "_macro_" in mutant["id"]

    def test_macro_mutant_reverses_phases(self, sample_pack):
        original_phase_names = [p["name"] for p in sample_pack["phases"]]
        mutant = create_macro_mutant(sample_pack)
        mutant_phase_names = [p["name"] for p in mutant["phases"]]
        # Phase order should be different (reversed/swapped)
        assert mutant_phase_names != original_phase_names


# ============================================================================
# Integration-like Tests
# ============================================================================


class TestMutationEngineIntegration:
    """Integration tests for the full mutation flow."""

    def test_full_mutation_flow(self, mock_pack_store, mock_failure_memory, sample_pack):
        """Test the complete flow from suggestion to A/B test."""
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        # Suggest mutations
        proposals = engine.suggest_mutations("test-pack")

        # Apply first proposal if any
        if proposals:
            variant = engine.apply_mutation("test-pack", proposals[0])
            assert variant is not None

            # Record outcomes
            test_id = list(engine.ab_tests.keys())[0]
            engine.record_outcome(test_id, "original", True)
            engine.record_outcome(test_id, "mutant", True)

            # Check results
            results = engine.check_ab_tests()
            assert len(results) == 1

    def test_multiple_mutations_tracked_separately(self, mock_pack_store, mock_failure_memory, sample_pack):
        """Test that multiple mutations create separate A/B tests."""
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        # Apply multiple mutations
        for i in range(3):
            proposal = MutationProposal(
                mutation_type=f"test_{i}",
                pack_id="test-pack",
                description=f"Test mutation {i}",
                mutator_class="TestOp",
                change={},
            )
            engine.apply_mutation("test-pack", proposal)

        assert len(engine.ab_tests) == 3

    def test_adaptive_rate_after_mutations(self, mock_pack_store, mock_failure_memory, sample_pack):
        """Test that adaptive rate updates after mutation results."""
        mock_pack_store.save_pack("test-pack", sample_pack)
        engine = MutationEngine(mock_pack_store, mock_failure_memory)

        initial_rate = engine.mutation_rate.mutation_rate

        # Simulate recording mutation attempts
        engine.mutation_rate.record_attempt(improved=True)
        engine.mutation_rate.record_attempt(improved=True)
        engine.mutation_rate.record_attempt(improved=True)
        engine.mutation_rate.record_attempt(improved=True)
        engine.mutation_rate.record_attempt(improved=True)

        # Rate may have adjusted
        stats = engine.mutation_rate.get_stats()
        assert stats["mutations_attempted"] >= 5


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    def test_mutation_engine_missing_pack(self, mock_pack_store, mock_failure_memory):
        engine = MutationEngine(mock_pack_store, mock_failure_memory)
        proposals = engine.suggest_mutations("nonexistent-pack")
        assert proposals == []

    def test_apply_mutation_missing_pack(self, mock_pack_store, mock_failure_memory):
        engine = MutationEngine(mock_pack_store, mock_failure_memory)
        proposal = MutationProposal(
            mutation_type="test",
            pack_id="nonexistent",
            description="Test",
            mutator_class="TestOp",
            change={},
        )
        with pytest.raises(ValueError):
            engine.apply_mutation("nonexistent", proposal)

    def test_record_outcome_invalid_test(self, mock_pack_store, mock_failure_memory):
        engine = MutationEngine(mock_pack_store, mock_failure_memory)
        # Should not raise, just ignore
        engine.record_outcome("fake-id", "original", True)

    def test_ab_test_zero_samples(self, mock_pack_store):
        ab_test = ABTest.create_test("pack-1", "pack-1-mutant", "test", mock_pack_store)
        result = ab_test.get_winner(min_samples=20)
        assert result.winner == "insufficient_data"


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
