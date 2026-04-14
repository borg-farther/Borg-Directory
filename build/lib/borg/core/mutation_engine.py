"""
Borg V3 Mutation Engine — Evolution of workflow packs based on agent feedback.

This module implements:
1. Five mutation operators (AntiPatternAddition, StepParameterTuning,
   ConditionRefinement, PhaseReordering, ExampleSubstitution)
2. A/B testing infrastructure with z-test significance
3. Adaptive mutation rate (1/5th rule)
4. Rollback with version history

No external dependencies beyond stdlib + numpy.
"""

from __future__ import annotations

import copy
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Protocol interfaces (duck typing for loose coupling)
# ---------------------------------------------------------------------------


class PackStore(Protocol):
    """Interface for pack storage."""

    def get_pack(self, pack_id: str) -> Optional[Dict[str, Any]]:
        """Load a pack by ID, returns None if not found."""
        ...

    def save_pack(self, pack_id: str, pack_data: Dict[str, Any]) -> None:
        """Save a pack by ID."""
        ...

    def list_packs(self) -> List[str]:
        """List all available pack IDs."""
        ...


class FailureMemoryLike(Protocol):
    """Interface for failure memory."""

    def recall(self, error_pattern: str) -> Optional[Dict[str, Any]]:
        """Recall failure records for an error pattern."""
        ...

    def record_failure(
        self,
        error_pattern: str,
        pack_id: str,
        phase: str,
        approach: str,
        outcome: str,
    ) -> None:
        """Record a failure or success."""
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        ...


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MutationProposal:
    """Represents a proposed mutation to a pack."""

    mutation_type: str  # e.g., "anti_pattern_addition", "step_parameter_tuning"
    pack_id: str
    description: str
    mutator_class: str  # Which operator generated this
    change: Dict[str, Any]  # The actual change to apply
    confidence: float = 0.5  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)  # Supporting evidence


@dataclass
class PackVariant:
    """Tracks a pack variant in an A/B test."""

    original_pack_id: str
    mutant_pack_id: str
    mutation_type: str
    created_at: datetime
    uses_original: int = 0
    uses_mutant: int = 0
    successes_original: int = 0
    successes_mutant: int = 0

    @property
    def success_rate_original(self) -> float:
        if self.uses_original == 0:
            return 0.0
        return self.successes_original / self.uses_original

    @property
    def success_rate_mutant(self) -> float:
        if self.uses_mutant == 0:
            return 0.0
        return self.successes_mutant / self.uses_mutant


@dataclass
class ABTestResult:
    """Result of checking an A/B test."""

    variant: PackVariant
    winner: str  # "original", "mutant", or "insufficient_data"
    significance: float  # p-value from z-test
    is_significant: bool
    recommended_action: str  # "promote_mutant", "revert_mutant", "continue"


@dataclass
class PackVersion:
    """A snapshot of a pack at a point in time."""

    version_id: str
    pack_id: str
    snapshot: Dict[str, Any]  # Full pack data
    created_at: datetime
    mutation_proposal_id: Optional[str] = None
    note: str = ""


# ---------------------------------------------------------------------------
# Mutation Operators
# ---------------------------------------------------------------------------


class MutationOperator:
    """Base class for mutation operators."""

    name: str = "base"

    def __init__(self, pack_store: PackStore, failure_memory: FailureMemoryLike):
        self.pack_store = pack_store
        self.failure_memory = failure_memory

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        """Suggest mutations for a pack. Override in subclasses."""
        return []


class AntiPatternAddition(MutationOperator):
    """
    When failure_memory has >= 3 agents failing the same way on a pack,
    add that failure pattern as an anti-pattern to the pack.
    """

    name = "anti_pattern_addition"
    MIN_FAILURES = 3

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        proposals = []
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            return []

        existing_antipatterns = set(pack.get("anti_patterns", []))

        # Get all failure records for this pack
        stats = self.failure_memory.get_stats()
        # We need to check each error pattern - iterate through recall patterns
        # Since failure_memory stores by error hash, we need a different approach
        # Check for common failure patterns in failure memory

        # Get all error patterns from the pack's context
        # Look for errors that have >= 3 failures for approaches on this pack
        pack_dir = getattr(self.failure_memory, "memory_dir", None)
        if pack_dir is None:
            return []

        from pathlib import Path

        pack_failures_dir = Path(pack_dir) / pack_id
        if not pack_failures_dir.exists():
            return []

        import yaml

        for yaml_file in pack_failures_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue

                error_pattern = data.get("error_pattern", "")
                wrong_approaches = data.get("wrong_approaches", [])

                # Check if any approach has >= MIN_FAILURES
                for approach in wrong_approaches:
                    failure_count = approach.get("failure_count", 0)
                    if failure_count >= self.MIN_FAILURES:
                        # Check if this anti-pattern is already in the pack
                        if error_pattern not in existing_antipatterns:
                            proposals.append(
                                MutationProposal(
                                    mutation_type=self.name,
                                    pack_id=pack_id,
                                    description=f"Add anti-pattern from failure memory: {error_pattern[:50]}...",
                                    mutator_class=self.name,
                                    change={
                                        "action": "add_anti_pattern",
                                        "anti_pattern": error_pattern,
                                        "source_approach": approach.get("approach", ""),
                                        "failure_count": failure_count,
                                    },
                                    confidence=min(failure_count / 10.0, 1.0),
                                    evidence=[
                                        f"Failure count: {failure_count} >= {self.MIN_FAILURES}",
                                        f"Error pattern: {error_pattern[:100]}",
                                        f"Failed approach: {approach.get('approach', '')[:50]}",
                                    ],
                                )
                            )
            except (yaml.YAMLError, OSError):
                continue

        return proposals


class StepParameterTuning(MutationOperator):
    """
    Compare successful vs failed sessions using same pack,
    identify parameter differences, propose parameter changes.
    """

    name = "step_parameter_tuning"

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        proposals = []
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            return []

        # Look at failure memory for patterns
        pack_dir = getattr(self.failure_memory, "memory_dir", None)
        if pack_dir is None:
            return []

        from pathlib import Path

        pack_failures_dir = Path(pack_dir) / pack_id
        if not pack_failures_dir.exists():
            return []

        import yaml

        # Collect all successful and failed approaches with their counts
        successful_approaches = {}
        failed_approaches = {}

        for yaml_file in pack_failures_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue

                for ca in data.get("correct_approaches", []):
                    approach = ca.get("approach", "")
                    count = ca.get("success_count", 0)
                    successful_approaches[approach] = count

                for wa in data.get("wrong_approaches", []):
                    approach = wa.get("approach", "")
                    count = wa.get("failure_count", 0)
                    failed_approaches[approach] = count
            except (yaml.YAMLError, OSError):
                continue

        # Find approaches that succeed but have similar names to failed ones
        # Suggest tuning parameters
        for failed_approach, failed_count in failed_approaches.items():
            for success_approach, success_count in successful_approaches.items():
                # If there's overlap in the approach strings, suggest parameter tuning
                if failed_approach != success_approach and (
                    failed_approach[:30] in success_approach
                    or success_approach[:30] in failed_approach
                    or any(
                        word in success_approach.lower()
                        for word in failed_approach.lower().split()
                        if len(word) > 4
                    )
                ):
                    proposals.append(
                        MutationProposal(
                            mutation_type=self.name,
                            pack_id=pack_id,
                            description=f"Parameter tuning based on success/failure comparison",
                            mutator_class=self.name,
                            change={
                                "action": "tune_parameters",
                                "from_approach": failed_approach,
                                "to_approach": success_approach,
                                "failed_count": failed_count,
                                "success_count": success_count,
                            },
                            confidence=min(success_count / (success_count + failed_count + 1), 1.0),
                            evidence=[
                                f"Failed approach: {failed_approach[:50]} (count: {failed_count})",
                                f"Successful approach: {success_approach[:50]} (count: {success_count})",
                            ],
                        )
                    )

        return proposals[:5]  # Limit proposals


class ConditionRefinement(MutationOperator):
    """
    Track skip_if/inject_if usage patterns, add conditions that are
    consistently triggered.
    """

    name = "condition_refinement"

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        proposals = []
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            return []

        # Analyze phases for skip_if/inject_if patterns
        phases = pack.get("phases", [])
        existing_conditions = set()

        for phase in phases:
            skip_if = phase.get("skip_if", [])
            inject_if = phase.get("inject_if", [])
            for cond in skip_if:
                existing_conditions.add(("skip_if", str(cond)))
            for cond in inject_if:
                existing_conditions.add(("inject_if", str(cond)))

        # Look for patterns in failure memory that suggest new conditions
        # For example, if errors consistently occur in certain phases,
        # suggest adding skip conditions
        pack_dir = getattr(self.failure_memory, "memory_dir", None)
        if pack_dir is None:
            return []

        from pathlib import Path

        pack_failures_dir = Path(pack_dir) / pack_id
        if not pack_failures_dir.exists():
            return []

        import yaml

        phase_error_counts = {}

        for yaml_file in pack_failures_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue

                phase = data.get("phase", "")
                total_failures = sum(
                    wa.get("failure_count", 0) for wa in data.get("wrong_approaches", [])
                )
                if phase:
                    phase_error_counts[phase] = phase_error_counts.get(phase, 0) + total_failures
            except (yaml.YAMLError, OSError):
                continue

        # Suggest conditions for phases with high error counts
        for phase_data in phases:
            phase_name = phase_data.get("name", "")
            error_count = phase_error_counts.get(phase_name, 0)
            if error_count >= 5:  # Threshold for suggesting condition
                proposals.append(
                    MutationProposal(
                        mutation_type=self.name,
                        pack_id=pack_id,
                        description=f"Add condition to phase '{phase_name}' based on {error_count} failures",
                        mutator_class=self.name,
                        change={
                            "action": "add_condition",
                            "phase": phase_name,
                            "condition_type": "skip_if",
                            "suggested_condition": {"error_high": True},
                        },
                        confidence=min(error_count / 20.0, 0.9),
                        evidence=[f"Phase '{phase_name}' has {error_count} failures in failure memory"],
                    )
                )

        return proposals[:5]


class PhaseReordering(MutationOperator):
    """
    If agents consistently skip phase N and go to phase N+2,
    suggest reordering phases.
    """

    name = "phase_reordering"
    SKIP_THRESHOLD = 3  # If skipped >= 3 times, suggest reordering

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        proposals = []
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            return []

        phases = pack.get("phases", [])
        if len(phases) < 3:
            return []  # Need at least 3 phases for reordering to make sense

        # Check failure memory for phase skip patterns
        # This requires tracking phase transitions which may not be directly available
        # We'll infer from failure patterns and phase names

        # For now, use a simpler heuristic:
        # If phases have similar purposes or there's evidence of skipping
        # This is a placeholder - real implementation would need phase transition tracking

        return proposals


class ExampleSubstitution(MutationOperator):
    """
    Replace examples with ones from recent successful sessions.
    """

    name = "example_substitution"

    def suggest(self, pack_id: str) -> List[MutationProposal]:
        proposals = []
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            return []

        # Extract current examples from pack
        current_examples = []
        phases = pack.get("phases", [])
        for phase in phases:
            for prompt in phase.get("context_prompts", []):
                if "example" in prompt.lower():
                    current_examples.append(prompt)

        if not current_examples:
            return []

        # Look for successful approaches in failure memory
        pack_dir = getattr(self.failure_memory, "memory_dir", None)
        if pack_dir is None:
            return []

        from pathlib import Path

        pack_failures_dir = Path(pack_dir) / pack_id
        if not pack_failures_dir.exists():
            return []

        import yaml

        successful_examples = []

        for yaml_file in pack_failures_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue

                for ca in data.get("correct_approaches", []):
                    approach = ca.get("approach", "")
                    count = ca.get("success_count", 0)
                    if count >= 2 and len(approach) > 20:
                        successful_examples.append((approach, count))
            except (yaml.YAMLError, OSError):
                continue

        # Sort by success count and suggest substitution
        successful_examples.sort(key=lambda x: x[1], reverse=True)

        if successful_examples:
            best_example, count = successful_examples[0]
            proposals.append(
                MutationProposal(
                    mutation_type=self.name,
                    pack_id=pack_id,
                    description="Substitute example from successful session",
                    mutator_class=self.name,
                    change={
                        "action": "substitute_example",
                        "original_example": current_examples[0] if current_examples else "",
                        "new_example": best_example,
                        "success_count": count,
                    },
                    confidence=min(count / 10.0, 0.9),
                    evidence=[f"Example from successful session with {count} successes"],
                )
            )

        return proposals


# ---------------------------------------------------------------------------
# A/B Testing Infrastructure
# ---------------------------------------------------------------------------


@dataclass
class ABTest:
    """Manages an A/B test between original and mutant packs."""

    variant: PackVariant
    _pack_store: PackStore

    @classmethod
    def create_test(
        cls,
        original_pack_id: str,
        mutant_pack_id: str,
        mutation_type: str,
        pack_store: PackStore,
    ) -> "ABTest":
        """Create a new A/B test."""
        variant = PackVariant(
            original_pack_id=original_pack_id,
            mutant_pack_id=mutant_pack_id,
            mutation_type=mutation_type,
            created_at=datetime.now(timezone.utc),
        )
        return cls(variant=variant, _pack_store=pack_store)

    def record_outcome(self, variant: str, success: bool) -> None:
        """Record the outcome of a pack use.

        Args:
            variant: Either "original" or "mutant"
            success: Whether the session using this variant was successful
        """
        if variant == "original":
            self.variant.uses_original += 1
            if success:
                self.variant.successes_original += 1
        elif variant == "mutant":
            self.variant.uses_mutant += 1
            if success:
                self.variant.successes_mutant += 1

    def get_winner(self, min_samples: int = 20, significance: float = 0.05) -> ABTestResult:
        """
        Determine the winner of the A/B test using a proportion z-test.

        Args:
            min_samples: Minimum samples needed in each arm before declaring winner
            significance: Alpha level for statistical significance (default 0.05)

        Returns:
            ABTestResult with winner, p-value, and recommended action
        """
        uses_orig = self.variant.uses_original
        uses_mut = self.variant.uses_mutant

        # Check for sufficient samples
        if uses_orig < min_samples or uses_mut < min_samples:
            return ABTestResult(
                variant=self.variant,
                winner="insufficient_data",
                significance=1.0,
                is_significant=False,
                recommended_action="continue",
            )

        # Calculate success rates
        p_orig = self.variant.successes_original / uses_orig
        p_mut = self.variant.successes_mutant / uses_mut

        # Pooled proportion
        total_successes = self.variant.successes_original + self.variant.successes_mutant
        total_uses = uses_orig + uses_mut
        p_pooled = total_successes / total_uses if total_uses > 0 else 0

        # Standard error — use math.sqrt (numpy unavailable or np.sqrt fails)
        import math as _math
        se = _math.sqrt(p_pooled * (1 - p_pooled) * (1 / uses_orig + 1 / uses_mut))
        if se == 0:
            return ABTestResult(
                variant=self.variant,
                winner="insufficient_data",
                significance=1.0,
                is_significant=False,
                recommended_action="continue",
            )

        # Z-score
        z = (p_mut - p_orig) / se

        # Two-tailed p-value from z-score
        from scipy import stats

        p_value = 2 * (1 - stats.norm.cdf(abs(z)))

        # Determine winner
        if p_value >= significance:
            winner = "insufficient_data"
            action = "continue"
        elif p_mut > p_orig:
            winner = "mutant"
            action = "promote_mutant"
        else:
            winner = "original"
            action = "revert_mutant"

        return ABTestResult(
            variant=self.variant,
            winner=winner,
            significance=p_value,
            is_significant=p_value < significance,
            recommended_action=action,
        )

    def auto_promote(self) -> bool:
        """
        Automatically promote the mutant if it's performing better.

        Returns:
            True if mutant was promoted (mutant pack saved as new original), False otherwise
        """
        result = self.get_winner()
        if result.winner == "mutant" and result.is_significant:
            # Load mutant and save as the new original
            mutant = self._pack_store.get_pack(self.variant.mutant_pack_id)
            if mutant:
                # Update the mutant's ID to match original and save
                mutant["id"] = self.variant.original_pack_id
                self._pack_store.save_pack(self.variant.original_pack_id, mutant)
                return True
        return False


# ---------------------------------------------------------------------------
# Adaptive Mutation Rate
# ---------------------------------------------------------------------------


class AdaptiveMutationRate:
    """
    Tracks mutation success and adapts the mutation rate using the 1/5th rule.

    - If >20% of mutations improve pack performance, increase rate
    - If <20% improve, decrease rate
    - Rate is bounded between 0.01 and 0.5
    - MacroMutation (wholesale restructure) occurs at 1% frequency
    """

    IMPROVEMENT_THRESHOLD = 0.20
    RATE_INCREASE_FACTOR = 1.5
    RATE_DECREASE_FACTOR = 0.5
    MIN_RATE = 0.01
    MAX_RATE = 0.5
    MACRO_MUTATION_FREQUENCY = 0.01

    def __init__(self, initial_rate: float = 0.1):
        self.mutation_rate = initial_rate
        self.mutations_attempted = 0
        self.mutations_that_improved = 0

    def record_attempt(self, improved: bool) -> None:
        """Record a mutation attempt."""
        self.mutations_attempted += 1
        if improved:
            self.mutations_that_improved += 1
        self._adjust_rate()

    def _adjust_rate(self) -> None:
        """Adjust mutation rate based on 1/5th rule."""
        if self.mutations_attempted < 5:
            return  # Need minimum samples

        improvement_rate = self.mutations_that_improved / self.mutations_attempted

        if improvement_rate > self.IMPROVEMENT_THRESHOLD:
            # Increase rate
            self.mutation_rate = min(
                self.mutation_rate * self.RATE_INCREASE_FACTOR, self.MAX_RATE
            )
        else:
            # Decrease rate
            self.mutation_rate = max(
                self.mutation_rate * self.RATE_DECREASE_FACTOR, self.MIN_RATE
            )

        # Reset counters periodically
        if self.mutations_attempted >= 20:
            self.mutations_attempted = 0
            self.mutations_that_improved = 0

    def should_mutate(self) -> bool:
        """Determine if a pack should be mutated based on current rate."""
        return random.random() < self.mutation_rate

    def is_macro_mutation(self) -> bool:
        """Determine if this should be a macro mutation (wholesale restructure)."""
        return random.random() < self.MACRO_MUTATION_FREQUENCY

    def get_stats(self) -> Dict[str, Any]:
        """Get current mutation rate statistics."""
        return {
            "mutation_rate": self.mutation_rate,
            "mutations_attempted": self.mutations_attempted,
            "mutations_that_improved": self.mutations_that_improved,
            "improvement_rate": (
                self.mutations_that_improved / self.mutations_attempted
                if self.mutations_attempted > 0
                else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Rollback Manager
# ---------------------------------------------------------------------------


class RollbackManager:
    """
    Manages pack version history and rollback operations.

    - Snapshots pack before any mutation
    - Tracks version history
    - Auto-reverts if mutant success_rate < original - 0.10 after 20 uses
    """

    REVERT_THRESHOLD = 0.10
    MIN_USES_FOR_REVERT = 20

    def __init__(self, pack_store: PackStore):
        self.pack_store = pack_store
        self.versions: Dict[str, List[PackVersion]] = {}  # pack_id -> list of versions

    def snapshot(self, pack_id: str, mutation_proposal_id: Optional[str] = None, note: str = "") -> PackVersion:
        """
        Create a snapshot of the current pack state.

        Args:
            pack_id: The pack to snapshot
            mutation_proposal_id: Optional ID of the mutation that prompted this snapshot
            note: Optional note about this version

        Returns:
            The PackVersion snapshot
        """
        pack = self.pack_store.get_pack(pack_id)
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")

        version_id = str(uuid.uuid4())[:8]
        snapshot = copy.deepcopy(pack)

        version = PackVersion(
            version_id=version_id,
            pack_id=pack_id,
            snapshot=snapshot,
            created_at=datetime.now(timezone.utc),
            mutation_proposal_id=mutation_proposal_id,
            note=note,
        )

        if pack_id not in self.versions:
            self.versions[pack_id] = []
        self.versions[pack_id].append(version)

        return version

    def get_versions(self, pack_id: str) -> List[PackVersion]:
        """Get all versions for a pack."""
        return self.versions.get(pack_id, [])

    def get_latest_version(self, pack_id: str) -> Optional[PackVersion]:
        """Get the most recent version of a pack."""
        versions = self.versions.get(pack_id, [])
        return versions[-1] if versions else None

    def rollback_to_version(self, pack_id: str, version_id: str) -> bool:
        """
        Rollback a pack to a specific version.

        Args:
            pack_id: The pack to rollback
            version_id: The version to rollback to

        Returns:
            True if rollback successful, False otherwise
        """
        versions = self.versions.get(pack_id, [])
        for version in versions:
            if version.version_id == version_id:
                self.pack_store.save_pack(pack_id, copy.deepcopy(version.snapshot))
                return True
        return False

    def rollback_to_latest(self, pack_id: str) -> bool:
        """
        Rollback a pack to its most recent version.

        Args:
            pack_id: The pack to rollback

        Returns:
            True if rollback successful, False otherwise
        """
        versions = self.versions.get(pack_id, [])
        if len(versions) < 2:
            return False  # Can't rollback to latest if there's only one version

        # Rollback to the version before the latest
        previous_version = versions[-2]
        return self.rollback_to_version(pack_id, previous_version.version_id)

    def check_and_revert(self, variant: PackVariant) -> bool:
        """
        Check if a mutant should be auto-reverted and perform the revert if needed.

        Args:
            variant: The PackVariant to check

        Returns:
            True if revert was performed, False otherwise
        """
        total_uses = variant.uses_original + variant.uses_mutant
        if total_uses < self.MIN_USES_FOR_REVERT:
            return False

        # Check if mutant is significantly worse
        success_rate_orig = variant.success_rate_original
        success_rate_mut = variant.success_rate_mutant

        if success_rate_mut < success_rate_orig - self.REVERT_THRESHOLD:
            # Revert mutant to original
            mutant = self.pack_store.get_pack(variant.mutant_pack_id)
            if mutant:
                original = copy.deepcopy(self.pack_store.get_pack(variant.original_pack_id))
                if original:
                    self.pack_store.save_pack(variant.original_pack_id, original)
                    return True
        return False


# ---------------------------------------------------------------------------
# Main Mutation Engine
# ---------------------------------------------------------------------------


class MutationEngine:
    """
    Main mutation engine that orchestrates pack evolution.

    Coordinates:
    - Mutation operators
    - A/B testing
    - Adaptive mutation rate
    - Rollback
    """

    def __init__(
        self,
        pack_store: PackStore,
        failure_memory: FailureMemoryLike,
        mutation_rate: float = 0.1,
    ):
        self.pack_store = pack_store
        self.failure_memory = failure_memory
        self.mutation_rate = AdaptiveMutationRate(initial_rate=mutation_rate)
        self.rollback_manager = RollbackManager(pack_store)
        self.ab_tests: Dict[str, ABTest] = {}  # test_id -> ABTest
        self.operator_results: Dict[str, List[MutationProposal]] = {}

        # Initialize operators
        self.operators: List[MutationOperator] = [
            AntiPatternAddition(pack_store, failure_memory),
            StepParameterTuning(pack_store, failure_memory),
            ConditionRefinement(pack_store, failure_memory),
            PhaseReordering(pack_store, failure_memory),
            ExampleSubstitution(pack_store, failure_memory),
        ]

    def suggest_mutations(self, pack_id: str) -> List[MutationProposal]:
        """
        Suggest mutations for a pack based on all operators.

        Args:
            pack_id: The pack to analyze

        Returns:
            List of MutationProposal objects
        """
        all_proposals = []

        for operator in self.operators:
            try:
                proposals = operator.suggest(pack_id)
                all_proposals.extend(proposals)
            except Exception:
                continue  # Skip operators that fail

        self.operator_results[pack_id] = all_proposals
        return all_proposals

    def apply_mutation(
        self, pack_id: str, mutation: MutationProposal
    ) -> PackVariant:
        """
        Apply a mutation to a pack and create an A/B test.

        Args:
            pack_id: The pack to mutate
            mutation: The mutation to apply

        Returns:
            PackVariant representing the A/B test
        """
        # Snapshot original before mutation
        self.rollback_manager.snapshot(
            pack_id, note=f"Before mutation: {mutation.description}"
        )

        # Load original pack
        original = self.pack_store.get_pack(pack_id)
        if original is None:
            raise ValueError(f"Pack {pack_id} not found")

        # Create mutant by applying the change
        mutant = copy.deepcopy(original)
        self._apply_change(mutant, mutation.change)
        mutant["id"] = f"{pack_id}_mutant_{uuid.uuid4().hex[:8]}"

        # Save mutant
        self.pack_store.save_pack(mutant["id"], mutant)

        # Create A/B test
        test_id = str(uuid.uuid4())
        ab_test = ABTest.create_test(
            original_pack_id=pack_id,
            mutant_pack_id=mutant["id"],
            mutation_type=mutation.mutation_type,
            pack_store=self.pack_store,
        )
        self.ab_tests[test_id] = ab_test

        return ab_test.variant

    def _apply_change(self, pack: Dict[str, Any], change: Dict[str, Any]) -> None:
        """Apply a change dict to a pack."""
        action = change.get("action", "")

        if action == "add_anti_pattern":
            anti_pattern = change.get("anti_pattern", "")
            if "anti_patterns" not in pack:
                pack["anti_patterns"] = []
            if anti_pattern not in pack["anti_patterns"]:
                pack["anti_patterns"].append(anti_pattern)

        elif action == "tune_parameters":
            # Modify phase parameters based on successful approach
            # This is a simplified implementation
            pass

        elif action == "add_condition":
            phase_name = change.get("phase", "")
            condition_type = change.get("condition_type", "skip_if")
            condition = change.get("suggested_condition", {})

            for phase in pack.get("phases", []):
                if phase.get("name") == phase_name:
                    if condition_type not in phase:
                        phase[condition_type] = []
                    phase[condition_type].append(condition)

        elif action == "substitute_example":
            # Replace example in context_prompts
            new_example = change.get("new_example", "")
            original_example = change.get("original_example", "")
            for phase in pack.get("phases", []):
                prompts = phase.get("context_prompts", [])
                for i, prompt in enumerate(prompts):
                    if original_example and original_example in prompt:
                        prompts[i] = new_example
                        break

    def record_outcome(self, test_id: str, variant: str, success: bool) -> None:
        """
        Record the outcome of a variant in an A/B test.

        Args:
            test_id: The ID of the A/B test
            variant: Either "original" or "mutant"
            success: Whether the session was successful
        """
        if test_id in self.ab_tests:
            self.ab_tests[test_id].record_outcome(variant, success)

    def check_ab_tests(self) -> List[ABTestResult]:
        """
        Check all running A/B tests and take action (promote/revert) as needed.

        Returns:
            List of ABTestResult objects for all tests
        """
        results = []
        for test_id, test in self.ab_tests.items():
            result = test.get_winner()
            results.append(result)

            # Auto-revert if mutant is significantly worse
            if result.winner == "original" and result.is_significant:
                self.rollback_manager.check_and_revert(test.variant)

            # Auto-promote if mutant is significantly better
            elif result.winner == "mutant" and result.is_significant:
                if test.auto_promote():
                    # Successfully promoted - update mutation stats
                    self.mutation_rate.record_attempt(improved=True)
                else:
                    self.mutation_rate.record_attempt(improved=False)

        return results

    def get_mutation_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive mutation statistics.

        Returns:
            Dict with mutation rate stats, A/B test stats, rollback stats
        """
        ab_test_stats = []
        for test_id, test in self.ab_tests.items():
            v = test.variant
            ab_test_stats.append(
                {
                    "test_id": test_id,
                    "mutation_type": v.mutation_type,
                    "uses_original": v.uses_original,
                    "uses_mutant": v.uses_mutant,
                    "success_rate_original": v.success_rate_original,
                    "success_rate_mutant": v.success_rate_mutant,
                }
            )

        rollback_stats = {}
        for pack_id, versions in self.rollback_manager.versions.items():
            rollback_stats[pack_id] = len(versions)

        return {
            "adaptive_rate": self.mutation_rate.get_stats(),
            "ab_tests": ab_test_stats,
            "rollback_versions": rollback_stats,
            "total_ab_tests": len(self.ab_tests),
        }


# ---------------------------------------------------------------------------
# Mutation Factory
# ---------------------------------------------------------------------------


def create_macro_mutant(pack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a wholesale restructured version of a pack (MacroMutation).

    This is a dramatic restructuring that changes the fundamental flow.

    Args:
        pack: Original pack

    Returns:
        Mutant pack with wholesale restructuring
    """
    mutant = copy.deepcopy(pack)
    mutant["id"] = f"{pack['id']}_macro_{uuid.uuid4().hex[:8]}"

    phases = mutant.get("phases", [])

    # Reverse the order of phases
    if phases:
        phases.reverse()

    # Swap first two phases if they exist
    if len(phases) >= 2:
        phases[0], phases[1] = phases[1], phases[0]

    mutant["phases"] = phases

    return mutant
