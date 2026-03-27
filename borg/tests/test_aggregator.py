"""
Tests for PackAggregator — Borg self-improving aggregator.
"""

import json
import tempfile
from pathlib import Path

import pytest

from borg.core.aggregator import (
    PackAggregator,
    PROMOTION_MIN_EXECUTIONS,
    PROMOTION_MIN_SUCCESS_RATE,
)


# -----------------------------------------------------------------------
# Mock data helpers
# -----------------------------------------------------------------------

def make_execution_jsonl(
    session_id: str,
    phases: list[str],
    phase_results: list[str],  # "pass" or "fail"
    completed: bool = True,
) -> str:
    """Build a JSONL string for a single execution.

    Format matches session.log_event() output:
        execution_started, checkpoint_pass/checkpoint_fail,
        execution_completed.
    """
    lines = []

    # execution_started
    lines.append(
        json.dumps(
            {
                "type": "execution_started",
                "session_id": session_id,
                "phase_index": 0,
                "duration_s": 0.5,
            }
        )
    )

    for i, (phase_name, result) in enumerate(zip(phases, phase_results)):
        if result == "pass":
            lines.append(
                json.dumps(
                    {
                        "type": "checkpoint_pass",
                        "phase": phase_name,
                        "checkpoint": f"{phase_name}_checkpoint",
                        "checkpoint_result": "ok",
                        "duration_s": 1.0,
                    }
                )
            )
        else:
            lines.append(
                json.dumps(
                    {
                        "type": "checkpoint_fail",
                        "phase": phase_name,
                        "checkpoint": f"{phase_name}_checkpoint",
                        "checkpoint_result": "validation failed",
                        "error": f"Phase {phase_name} failed validation",
                        "duration_s": 1.0,
                    }
                )
            )

    if completed:
        lines.append(
            json.dumps(
                {
                    "type": "execution_completed",
                    "session_id": session_id,
                    "status": "completed" if all(r == "pass" for r in phase_results) else "failed",
                    "error": "",
                }
            )
        )

    return "\n".join(lines)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def make_exec_file(temp_dir: Path, session_id: str, phases, results, completed=True) -> Path:
    content = make_execution_jsonl(session_id, phases, results, completed)
    path = temp_dir / f"{session_id}.jsonl"
    path.write_text(content, encoding="utf-8")
    return path


# -----------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------

class TestIngestExecution:
    def test_ingest_success_execution(self, temp_dir):
        """Ingest a fully-successful execution log."""
        path = make_exec_file(
            temp_dir,
            "exec_001",
            ["Phase1", "Phase2", "Phase3"],
            ["pass", "pass", "pass"],
        )

        agg = PackAggregator("test-pack")
        summary = agg.ingest_execution(path)

        assert summary["session_id"] == "exec_001"
        assert summary["success"] is True
        assert len(summary["phases"]) == 3
        assert all(p["status"] == "passed" for p in summary["phases"])

    def test_ingest_partial_failure_execution(self, temp_dir):
        """Ingest an execution that fails at Phase 2."""
        path = make_exec_file(
            temp_dir,
            "exec_002",
            ["Phase1", "Phase2", "Phase3"],
            ["pass", "fail", "pass"],
        )

        agg = PackAggregator("test-pack")
        summary = agg.ingest_execution(path)

        assert summary["session_id"] == "exec_002"
        assert summary["success"] is False
        phase_names = [p["phase"] for p in summary["phases"]]
        assert "Phase2" in phase_names
        phase2 = next(p for p in summary["phases"] if p["phase"] == "Phase2")
        assert phase2["status"] == "failed"

    def test_ingest_multiple_executions(self, temp_dir):
        """Ingest 5 executions: 3 success, 2 partial failure at Phase 2."""
        phases = ["Phase1", "Phase2", "Phase3"]

        # 3 successes
        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_003", phases, ["pass", "pass", "pass"])

        # 2 failures at Phase 2
        make_exec_file(temp_dir, "exec_004", phases, ["pass", "fail", "pass"])
        make_exec_file(temp_dir, "exec_005", phases, ["pass", "fail", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            path = temp_dir / f"exec_00{i}.jsonl"
            agg.ingest_execution(path)

        assert len(agg._executions) == 5


class TestComputeMetrics:
    def test_success_rate_0_6(self, temp_dir):
        """5 executions, 3 success → success_rate = 0.6."""
        phases = ["Phase1", "Phase2", "Phase3"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_003", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_004", phases, ["pass", "fail", "pass"])
        make_exec_file(temp_dir, "exec_005", phases, ["pass", "fail", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            agg.ingest_execution(temp_dir / f"exec_00{i}.jsonl")

        metrics = agg.compute_metrics()

        assert metrics["total_executions"] == 5
        assert metrics["success_count"] == 3
        assert metrics["failure_count"] == 2
        assert metrics["success_rate"] == pytest.approx(0.6)
        assert metrics["avg_iterations"] > 0.0

    def test_common_failure_phase2(self, temp_dir):
        """Phase 2 is the only phase with failures → common_failures = ['Phase2']."""
        phases = ["Phase1", "Phase2", "Phase3"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_003", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_004", phases, ["pass", "fail", "pass"])
        make_exec_file(temp_dir, "exec_005", phases, ["pass", "fail", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            agg.ingest_execution(temp_dir / f"exec_00{i}.jsonl")

        metrics = agg.compute_metrics()

        assert "Phase2" in metrics["common_failures"]
        assert "Phase1" not in metrics["common_failures"]
        assert "Phase3" not in metrics["common_failures"]

    def test_empty_aggregator(self):
        """No executions → zero metrics."""
        agg = PackAggregator("empty-pack")
        metrics = agg.compute_metrics()

        assert metrics["total_executions"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["phase_metrics"] == {}
        assert metrics["common_failures"] == []


class TestSuggestImprovements:
    def test_suggests_anti_pattern_for_phase2(self, temp_dir):
        """Failure at Phase 2 should generate a suggestion to add anti-pattern."""
        phases = ["Phase1", "Phase2", "Phase3"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_003", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_004", phases, ["pass", "fail", "pass"])
        make_exec_file(temp_dir, "exec_005", phases, ["pass", "fail", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            agg.ingest_execution(temp_dir / f"exec_00{i}.jsonl")

        suggestions = agg.suggest_improvements()

        # Should have at least one suggestion mentioning Phase2
        phase2_suggestions = [s for s in suggestions if "Phase2" in s or "phase2" in s.lower()]
        assert len(phase2_suggestions) > 0
        # Suggestion should mention adding an anti-pattern or handling failures
        assert any("anti-pattern" in s.lower() or "common failure" in s.lower() or "address failure" in s.lower() for s in suggestions)

    def test_no_suggestions_when_all_pass(self, temp_dir):
        """All executions succeed → no improvements suggested."""
        phases = ["Phase1", "Phase2", "Phase3"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])

        agg = PackAggregator("test-pack")
        agg.ingest_execution(temp_dir / "exec_001.jsonl")
        agg.ingest_execution(temp_dir / "exec_002.jsonl")

        suggestions = agg.suggest_improvements()
        # No common failures → no structural anti-pattern suggestions
        assert all("anti-pattern" not in s.lower() for s in suggestions if s)


class TestConfidencePromotion:
    def test_no_promotion_below_min_executions(self, temp_dir):
        """Fewer than 10 executions → no promotion."""
        phases = ["Phase1", "Phase2", "Phase3"]

        # Only 5 executions, all successful
        for i in range(1, 6):
            make_exec_file(temp_dir, f"exec_00{i}", phases, ["pass", "pass", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            agg.ingest_execution(temp_dir / f"exec_00{i}.jsonl")

        result = agg.should_promote_confidence()
        assert result is None

    def test_no_promotion_below_success_rate(self, temp_dir):
        """10+ executions but success_rate < 0.70 → no promotion."""
        phases = ["Phase1", "Phase2", "Phase3"]

        # 10 executions with only 5 successes = 50% < 70%
        for i in range(1, 11):
            results = ["pass", "pass", "pass"] if i <= 5 else ["pass", "fail", "pass"]
            make_exec_file(temp_dir, f"exec_{i:03d}", phases, results)

        agg = PackAggregator("test-pack")
        for i in range(1, 11):
            agg.ingest_execution(temp_dir / f"exec_{i:03d}.jsonl")

        result = agg.should_promote_confidence()
        assert result is None

    def test_promotion_inferred_to_tested(self, temp_dir):
        """10+ executions with >70% success → promote inferred → tested."""
        phases = ["Phase1", "Phase2", "Phase3"]

        # 10 executions, 7 successes = 70%
        for i in range(1, 11):
            results = ["pass", "pass", "pass"] if i <= 7 else ["pass", "fail", "pass"]
            make_exec_file(temp_dir, f"exec_{i:03d}", phases, results)

        agg = PackAggregator("test-pack")
        for i in range(1, 11):
            agg.ingest_execution(temp_dir / f"exec_{i:03d}.jsonl")

        result = agg.should_promote_confidence()
        assert result == "tested"


class TestGenerateImprovedPack:
    def test_anti_pattern_added_to_phase2(self, temp_dir):
        """Improved pack has a new anti-pattern entry for Phase2."""
        phases = ["Phase1", "Phase2", "Phase3"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_003", phases, ["pass", "pass", "pass"])
        make_exec_file(temp_dir, "exec_004", phases, ["pass", "fail", "pass"])
        make_exec_file(temp_dir, "exec_005", phases, ["pass", "fail", "pass"])

        agg = PackAggregator("test-pack")
        for i in range(1, 6):
            agg.ingest_execution(temp_dir / f"exec_00{i}.jsonl")

        current_pack = {
            "type": "workflow_pack",
            "version": "1.0.0",
            "id": "test-pack",
            "problem_class": "testing",
            "mental_model": "test mental model",
            "required_inputs": ["task"],
            "phases": [
                {
                    "name": "Phase1",
                    "description": "Phase 1 desc",
                    "checkpoint": "Phase1_checkpoint",
                    "anti_patterns": [],
                    "prompts": [],
                },
                {
                    "name": "Phase2",
                    "description": "Phase 2 desc",
                    "checkpoint": "Phase2_checkpoint",
                    "anti_patterns": [],
                    "prompts": [],
                },
                {
                    "name": "Phase3",
                    "description": "Phase 3 desc",
                    "checkpoint": "Phase3_checkpoint",
                    "anti_patterns": [],
                    "prompts": [],
                },
            ],
            "escalation_rules": ["fallback to human"],
            "provenance": {
                "confidence": "inferred",
                "evidence": "initial pack",
                "failure_cases": [],
            },
        }

        improved = agg.generate_improved_pack(current_pack)

        # Phase2 should have a new anti-pattern
        phase2 = next(p for p in improved["phases"] if p["name"] == "Phase2")
        assert len(phase2["anti_patterns"]) > 0

        # Phase1 and Phase3 should be unchanged (no failures there)
        phase1 = next(p for p in improved["phases"] if p["name"] == "Phase1")
        assert phase1["anti_patterns"] == []

    def test_confidence_promotion_in_provenance(self, temp_dir):
        """Improved pack gets promoted confidence in provenance after 10+ successful runs."""
        phases = ["Phase1", "Phase2", "Phase3"]

        # 10 executions with 8 successes = 80% > 70%
        for i in range(1, 11):
            results = ["pass", "pass", "pass"] if i <= 8 else ["pass", "fail", "pass"]
            make_exec_file(temp_dir, f"exec_{i:03d}", phases, results)

        agg = PackAggregator("test-pack")
        for i in range(1, 11):
            agg.ingest_execution(temp_dir / f"exec_{i:03d}.jsonl")

        current_pack = {
            "type": "workflow_pack",
            "version": "1.0.0",
            "id": "test-pack",
            "problem_class": "testing",
            "mental_model": "test mental model",
            "required_inputs": ["task"],
            "phases": [
                {
                    "name": "Phase1",
                    "description": "desc",
                    "checkpoint": "chk",
                    "anti_patterns": [],
                    "prompts": [],
                },
            ],
            "escalation_rules": [],
            "provenance": {
                "confidence": "inferred",
                "evidence": "test evidence",
                "failure_cases": [],
            },
        }

        improved = agg.generate_improved_pack(current_pack)

        assert improved["provenance"]["confidence"] == "tested"
        assert improved["provenance"].get("promoted_from") == "inferred"

    def test_does_not_modify_original_pack(self, temp_dir):
        """generate_improved_pack returns a new dict; original is unchanged."""
        phases = ["Phase1", "Phase2"]

        make_exec_file(temp_dir, "exec_001", phases, ["pass", "fail"])
        make_exec_file(temp_dir, "exec_002", phases, ["pass", "fail"])

        agg = PackAggregator("test-pack")
        agg.ingest_execution(temp_dir / "exec_001.jsonl")
        agg.ingest_execution(temp_dir / "exec_002.jsonl")

        current_pack = {
            "type": "workflow_pack",
            "version": "1.0.0",
            "id": "test-pack",
            "problem_class": "testing",
            "mental_model": "model",
            "required_inputs": ["task"],
            "phases": [
                {
                    "name": "Phase1",
                    "description": "desc",
                    "checkpoint": "chk",
                    "anti_patterns": [],
                    "prompts": [],
                },
                {
                    "name": "Phase2",
                    "description": "desc",
                    "checkpoint": "chk",
                    "anti_patterns": [],
                    "prompts": [],
                },
            ],
            "escalation_rules": [],
            "provenance": {
                "confidence": "inferred",
                "evidence": "evidence",
                "failure_cases": [],
            },
        }
        original_anti_patterns = {p["name"]: list(p["anti_patterns"]) for p in current_pack["phases"]}

        improved = agg.generate_improved_pack(current_pack)

        # Original pack must not be mutated
        for p in current_pack["phases"]:
            assert p["anti_patterns"] == original_anti_patterns[p["name"]]
        assert current_pack["provenance"]["confidence"] == "inferred"

        # Improved pack should differ
        phase2 = next(p for p in improved["phases"] if p["name"] == "Phase2")
        assert len(phase2["anti_patterns"]) > 0
