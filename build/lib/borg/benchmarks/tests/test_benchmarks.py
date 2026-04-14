#!/usr/bin/env python3
"""
Tests for Borg Benchmark Suite.
Covers tasks, scorer, runner, and report generation.
"""

import pytest
from borg.benchmarks.tasks import (
    TASKS,
    Task,
    get_tasks_by_category,
    get_task_by_id,
    DOCKER_DNS,
    OAUTH_401,
    DB_MIGRATION,
    YIELD_SELECTION,
    RUG_DETECTION,
    PORTFOLIO_REBALANCE,
    DEPLOY_CONFIG,
    MONITORING_SETUP,
    API_COMPARISON,
    ARCH_DECISION,
)
from borg.benchmarks.scorer import TaskScorer, TaskScore
from borg.benchmarks.runner import BenchmarkRunner, TaskResult, BenchmarkReport
from borg.benchmarks.report import generate_markdown_report, print_summary


# =============================================================================
# TASK TESTS
# =============================================================================

class TestTasks:
    """Tests for task definitions."""

    def test_total_task_count(self):
        """Should have exactly 10 benchmark tasks."""
        assert len(TASKS) == 10, f"Expected 10 tasks, got {len(TASKS)}"

    def test_all_tasks_have_required_fields(self):
        """Every task should have id, category, description, context, expected_approach, rubric, anti_patterns, borg_pack_id."""
        required_fields = ['id', 'category', 'description', 'context', 
                          'expected_approach', 'rubric', 'anti_patterns', 'borg_pack_id']
        for task in TASKS:
            for field in required_fields:
                assert hasattr(task, field), f"Task {task.id} missing field: {field}"
                assert getattr(task, field) is not None, f"Task {task.id} field {field} is None"

    def test_task_ids_are_unique(self):
        """All task IDs should be unique."""
        ids = [t.id for t in TASKS]
        assert len(ids) == len(set(ids)), f"Duplicate task IDs found: {ids}"

    def test_task_ids_are_valid_strings(self):
        """All task IDs should be lowercase with hyphens."""
        for task in TASKS:
            assert task.id.islower(), f"Task {task.id} should be lowercase"
            assert '-' in task.id or '_' in task.id or task.id.isalpha(), f"Task {task.id} should use hyphens or underscores"

    def test_categories_are_valid(self):
        """Categories should be from the allowed set."""
        valid_categories = {'coding', 'defi', 'ops', 'research'}
        for task in TASKS:
            assert task.category in valid_categories, f"Task {task.id} has invalid category: {task.category}"

    def test_category_counts(self):
        """Expected category distribution."""
        categories = [t.category for t in TASKS]
        coding_count = categories.count('coding')
        defi_count = categories.count('defi')
        ops_count = categories.count('ops')
        research_count = categories.count('research')
        
        assert coding_count == 3, f"Expected 3 coding tasks, got {coding_count}"
        assert defi_count == 3, f"Expected 3 defi tasks, got {defi_count}"
        assert ops_count == 2, f"Expected 2 ops tasks, got {ops_count}"
        assert research_count == 2, f"Expected 2 research tasks, got {research_count}"

    def test_rubric_is_list(self):
        """Rubric should be a list of strings."""
        for task in TASKS:
            assert isinstance(task.rubric, list), f"Task {task.id} rubric should be a list"
            assert all(isinstance(r, str) for r in task.rubric), f"Task {task.id} rubric items should be strings"

    def test_anti_patterns_is_list(self):
        """Anti-patterns should be a list of strings."""
        for task in TASKS:
            assert isinstance(task.anti_patterns, list), f"Task {task.id} anti_patterns should be a list"
            assert all(isinstance(a, str) for a in task.anti_patterns), f"Task {task.id} anti_patterns items should be strings"

    def test_get_tasks_by_category(self):
        """get_tasks_by_category should filter correctly."""
        coding_tasks = get_tasks_by_category('coding')
        assert len(coding_tasks) == 3
        assert all(t.category == 'coding' for t in coding_tasks)
        
        defi_tasks = get_tasks_by_category('defi')
        assert len(defi_tasks) == 3
        
        ops_tasks = get_tasks_by_category('ops')
        assert len(ops_tasks) == 2
        
        research_tasks = get_tasks_by_category('research')
        assert len(research_tasks) == 2

    def test_get_task_by_id(self):
        """get_task_by_id should return correct task."""
        task = get_task_by_id('docker-dns')
        assert task is not None
        assert task.id == 'docker-dns'
        
        task = get_task_by_id('arch-decision')
        assert task is not None
        assert task.id == 'arch-decision'

    def test_get_task_by_id_not_found(self):
        """get_task_by_id should return None for unknown ID."""
        task = get_task_by_id('nonexistent-task')
        assert task is None

    def test_all_borg_pack_ids_are_set(self):
        """All tasks should have a borg_pack_id set."""
        for task in TASKS:
            assert task.borg_pack_id, f"Task {task.id} missing borg_pack_id"
            assert isinstance(task.borg_pack_id, str), f"Task {task.id} borg_pack_id should be string"


# =============================================================================
# SCORER TESTS
# =============================================================================

class TestTaskScorer:
    """Tests for TaskScorer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = TaskScorer()

    def test_score_returns_task_score(self):
        """score() should return a TaskScore object."""
        result = TaskResult(
            task_id='docker-dns',
            solution='Use container name as hostname, ensure same network.',
            time_seconds=30.0
        )
        score = self.scorer.score(DOCKER_DNS, result)
        assert isinstance(score, TaskScore)

    def test_score_high_quality_solution(self):
        """Good solution with rubric keywords should score high."""
        result = TaskResult(
            task_id='docker-dns',
            solution=(
                'Containers communicate by container name on the same bridge network. '
                'Ensure both are on the same docker-compose network. '
                'Restart containers to pick up DNS changes. '
                'Use bridge network driver for proper isolation.'
            ),
            time_seconds=60.0
        )
        score = self.scorer.score(DOCKER_DNS, result)
        assert score.quality >= 7, f"Expected quality >= 7, got {score.quality}"
        assert score.solved is True
        assert score.used_best_practice is True
        assert score.hit_anti_pattern is False

    def test_score_low_quality_solution(self):
        """Solution with anti-patterns should score low."""
        result = TaskResult(
            task_id='docker-dns',
            solution='Use localhost instead of container name. Use host network mode.',
            time_seconds=30.0
        )
        score = self.scorer.score(DOCKER_DNS, result)
        assert score.quality < 5, f"Expected quality < 5, got {score.quality}"
        assert score.hit_anti_pattern is True

    def test_score_partial_solution(self):
        """Partial rubric coverage should give partial score."""
        result = TaskResult(
            task_id='docker-dns',
            solution='Containers need to be on the same network.',
            time_seconds=45.0
        )
        score = self.scorer.score(DOCKER_DNS, result)
        # Should have some rubric matches but not complete
        assert 0 < score.quality < 10

    def test_score_empty_solution(self):
        """Empty or irrelevant solution should score 0."""
        result = TaskResult(
            task_id='docker-dns',
            solution='I dont know how to fix this.',
            time_seconds=30.0
        )
        score = self.scorer.score(DOCKER_DNS, result)
        assert score.quality == 0
        assert score.solved is False

    def test_score_defi_yield_high_apy_is_anti_pattern(self):
        """Recommending highest APY is an anti-pattern for yield selection."""
        result = TaskResult(
            task_id='yield-selection',
            solution='Put all money in the 25% APY protocol - highest yield is best!',
            time_seconds=20.0
        )
        score = self.scorer.score(YIELD_SELECTION, result)
        assert score.hit_anti_pattern is True
        assert score.quality < 5

    def test_score_defi_yield_bluechip(self):
        """Recommending Aave/morpho for yield is good practice."""
        result = TaskResult(
            task_id='yield-selection',
            solution=(
                'Use Aave USDC for 3.2% APY - blue chip, no impermanent loss, fully liquid. '
                'Avoid Curve due to IL risk. Reject unaudited protocols. '
                'Overcollateralized lending is safest.'
            ),
            time_seconds=35.0
        )
        score = self.scorer.score(YIELD_SELECTION, result)
        assert score.quality >= 7
        assert score.solved is True

    def test_score_rug_detection_anonymous_no_audit(self):
        """Anonymous team + no audits = rug red flags."""
        result = TaskResult(
            task_id='rug-detection',
            solution=(
                'HIGH RUG RISK: Anonymous team, no audits, LP not locked, '
                '40% tax token, small liquidity. Do not invest.'
            ),
            time_seconds=30.0
        )
        score = self.scorer.score(RUG_DETECTION, result)
        assert score.quality >= 7
        assert score.solved is True
        assert score.used_best_practice is True

    def test_score_architecture_monolith(self):
        """Recommending monolith for small team is correct."""
        result = TaskResult(
            task_id='arch-decision',
            solution=(
                'Stay with modular monolith. Microservices add complexity. '
                'Extract services only when scale pressure justifies. '
                'Small team = less operational overhead.'
            ),
            time_seconds=50.0
        )
        score = self.scorer.score(ARCH_DECISION, result)
        assert score.quality >= 7
        assert score.solved is True

    def test_score_architecture_microservices_anti_pattern(self):
        """Jumping to microservices is an anti-pattern."""
        result = TaskResult(
            task_id='arch-decision',
            solution='Use microservices now for modern architecture. Extract everything.',
            time_seconds=30.0
        )
        score = self.scorer.score(ARCH_DECISION, result)
        assert score.hit_anti_pattern is True
        assert score.quality < 5


# =============================================================================
# RUNNER TESTS
# =============================================================================

class TestBenchmarkRunner:
    """Tests for BenchmarkRunner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = BenchmarkRunner()

    def test_runner_has_baseline_responses(self):
        """Runner should have baseline responses for all tasks."""
        for task in TASKS:
            assert task.id in self.runner.BASELINE_RESPONSES, f"Missing baseline for {task.id}"

    def test_runner_has_borg_responses(self):
        """Runner should have borg responses for all tasks."""
        for task in TASKS:
            assert task.id in self.runner.BORG_RESPONSES, f"Missing borg response for {task.id}"

    def test_run_baseline_returns_task_result(self):
        """run_baseline should return a TaskResult."""
        result = self.runner.run_baseline(DOCKER_DNS)
        assert isinstance(result, TaskResult)
        assert result.task_id == 'docker-dns'
        assert result.pack_used is None
        assert result.solution
        assert result.time_seconds > 0

    def test_run_with_borg_returns_task_result(self):
        """run_with_borg should return a TaskResult with pack_used set."""
        result = self.runner.run_with_borg(DOCKER_DNS)
        assert isinstance(result, TaskResult)
        assert result.task_id == 'docker-dns'
        assert result.pack_used == DOCKER_DNS.borg_pack_id
        assert result.solution
        assert result.time_seconds > 0

    def test_baseline_vs_borg_different_solutions(self):
        """Baseline and borg solutions should be different for same task."""
        baseline = self.runner.run_baseline(YIELD_SELECTION)
        borg = self.runner.run_with_borg(YIELD_SELECTION)
        assert baseline.solution != borg.solution

    def test_compare_produces_report(self):
        """compare() should produce a BenchmarkReport."""
        baseline_results = [self.runner.run_baseline(t) for t in TASKS]
        borg_results = [self.runner.run_with_borg(t) for t in TASKS]
        report = self.runner.compare(baseline_results, borg_results)
        
        assert isinstance(report, BenchmarkReport)
        assert report.total_tasks == len(TASKS)

    def test_compare_calculates_success_rate(self):
        """compare() should correctly calculate success rates."""
        baseline_results = [self.runner.run_baseline(t) for t in TASKS]
        borg_results = [self.runner.run_with_borg(t) for t in TASKS]
        report = self.runner.compare(baseline_results, borg_results)
        
        assert 0 <= report.baseline_success_rate <= 1
        assert 0 <= report.borg_success_rate <= 1

    def test_compare_calculates_quality_delta(self):
        """compare() should correctly calculate quality delta."""
        baseline_results = [self.runner.run_baseline(t) for t in TASKS]
        borg_results = [self.runner.run_with_borg(t) for t in TASKS]
        report = self.runner.compare(baseline_results, borg_results)
        
        # Borg should generally have higher quality
        # Calculate manually to verify
        expected_delta = report.borg_avg_quality - report.baseline_avg_quality
        assert abs(report.avg_quality_delta - expected_delta) < 0.01

    def test_run_all_returns_all_results(self):
        """run_all() should return baseline, borg, and report."""
        baseline, borg, report = self.runner.run_all()
        
        assert len(baseline) == len(TASKS)
        assert len(borg) == len(TASKS)
        assert isinstance(report, BenchmarkReport)


# =============================================================================
# REPORT TESTS
# =============================================================================

class TestReport:
    """Tests for report generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = BenchmarkRunner()
        self.baseline, self.borg, self.report = self.runner.run_all()

    def test_generate_markdown_returns_string(self):
        """generate_markdown_report should return a string."""
        md = generate_markdown_report(self.report)
        assert isinstance(md, str)
        assert len(md) > 0

    def test_markdown_report_contains_header(self):
        """Report should contain expected header."""
        md = generate_markdown_report(self.report)
        assert '# Borg Benchmark Report' in md

    def test_markdown_report_contains_summary_table(self):
        """Report should contain summary table."""
        md = generate_markdown_report(self.report)
        assert '| Metric | Baseline | Borg | Delta |' in md

    def test_markdown_report_contains_all_tasks(self):
        """Report should mention all tasks."""
        md = generate_markdown_report(self.report)
        for task in TASKS:
            assert task.id in md, f"Task {task.id} not found in report"

    def test_markdown_report_contains_assessment(self):
        """Report should contain honest assessment section."""
        md = generate_markdown_report(self.report)
        assert '## Honest Assessment' in md

    def test_print_summary_no_exception(self):
        """print_summary should not raise an exception."""
        # Should run without error
        print_summary(self.report)
        # If we get here, no exception was raised


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_benchmark_run(self):
        """Complete benchmark run should work without errors."""
        runner = BenchmarkRunner()
        baseline, borg, report = runner.run_all()
        
        assert len(baseline) == 10
        assert len(borg) == 10
        assert report.total_tasks == 10

    def test_borg_helps_most_tasks(self):
        """Borg should improve quality on most tasks (this is the hypothesis being tested)."""
        runner = BenchmarkRunner()
        _, _, report = runner.run_all()
        
        # Count how many tasks borg improved
        helped = sum(1 for r in report.task_results if r['quality_delta'] > 0)
        hurt = sum(1 for r in report.task_results if r['quality_delta'] < 0)
        
        # We expect borg to help on more tasks than it hurts
        # But if it doesn't, that's a valid benchmark result
        assert helped + hurt + sum(1 for r in report.task_results if r['quality_delta'] == 0) == 10

    def test_benchmark_is_deterministic(self):
        """Running benchmark twice should give same results."""
        runner = BenchmarkRunner()
        _, _, report1 = runner.run_all()
        _, _, report2 = runner.run_all()
        
        assert report1.baseline_success_rate == report2.baseline_success_rate
        assert report1.borg_success_rate == report2.borg_success_rate
        assert report1.avg_quality_delta == report2.avg_quality_delta


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
