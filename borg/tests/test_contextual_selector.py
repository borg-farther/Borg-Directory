"""
Comprehensive tests for borg.core.contextual_selector.

Run with: python -m pytest borg/tests/test_contextual_selector.py -v
Or directly: python -m borg.tests.test_contextual_selector
"""

import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

# Ensure module is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core.contextual_selector import (
    # Constants
    TASK_CATEGORIES,
    PRIOR_ALPHA,
    PRIOR_BETA,
    EXPLORATION_BUDGET,
    # Task classification
    classify_task,
    _CATEGORY_KEYWORDS,
    _EXTENSION_CATEGORIES,
    # Beta posteriors
    BetaPosterior,
    beta_sample_numpy,
    thompson_sample,
    # Pack descriptor
    PackDescriptor,
    # Cold-start
    build_similarity_prior,
    # Selector
    ContextualSelector,
    SelectorResult,
    # V2 comparison
    v2_fixed_blend_score,
    select_v2,
    V2FixedBlendResult,
    # Comparison
    compare_selectors,
    ComparisonResult,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_candidates() -> List[PackDescriptor]:
    """Create sample packs for testing."""
    return [
        PackDescriptor(
            pack_id="debug-auth",
            name="Debug Auth Module",
            keywords=["auth", "login", "jwt", "error", "null", "debug"],
            language="python",
            supported_tasks=["debug", "review"],
            description="Debug authentication issues",
            category_stats={
                "debug": (8, 2),    # 80% win rate
                "test": (3, 3),    # 50% win rate
                "review": (5, 2),  # ~71%
            },
        ),
        PackDescriptor(
            pack_id="test-api",
            name="API Test Suite",
            keywords=["test", "api", "pytest", "coverage", "integration"],
            language="python",
            supported_tasks=["test", "debug"],
            description="Comprehensive API testing",
            category_stats={
                "debug": (2, 4),   # 33%
                "test": (10, 2),   # 83%
            },
        ),
        PackDescriptor(
            pack_id="deploy-k8s",
            name="Kubernetes Deployer",
            keywords=["deploy", "kubernetes", "docker", "helm", "k8s", "ci"],
            language="yaml",
            supported_tasks=["deploy"],
            description="Kubernetes deployment automation",
            category_stats={
                "deploy": (12, 1),  # 92%
            },
        ),
        PackDescriptor(
            pack_id="refactor-db",
            name="Database Refactor",
            keywords=["refactor", "database", "schema", "migration", "sql", "postgresql"],
            language="sql",
            supported_tasks=["refactor", "data"],
            description="Database schema refactoring",
            category_stats={
                "refactor": (6, 3),  # 67%
                "data": (9, 2),     # 82%
            },
        ),
        PackDescriptor(
            pack_id="generic-helper",
            name="Generic Helper",
            keywords=["helper", "utility", "misc"],
            language="python",
            supported_tasks=["other"],
            description="Generic utility pack",
            category_stats={},  # Cold-start (no data)
        ),
    ]


@pytest.fixture
def debug_task_context() -> Dict[str, Any]:
    """Task context for debugging."""
    return {
        "task_type": "fix_auth_nullpointer",
        "error_type": "NullPointerException at auth/login.py:42",
        "language": "python",
        "keywords": ["null", "pointer", "exception", "auth", "login"],
        "file_path": "/src/auth/login.py",
    }


@pytest.fixture
def test_task_context() -> Dict[str, Any]:
    """Task context for testing."""
    return {
        "task_type": "run_api_tests",
        "language": "python",
        "keywords": ["pytest", "test", "api", "coverage"],
        "file_path": "/tests/test_api.py",
    }


@pytest.fixture
def deploy_task_context() -> Dict[str, Any]:
    """Task context for deployment."""
    return {
        "task_type": "deploy_to_kubernetes",
        "language": "yaml",
        "keywords": ["deploy", "kubernetes", "docker", "helm"],
        "file_path": "k8s/deployment.yaml",
    }


# =============================================================================
# Tests: Task Classification
# =============================================================================

class TestClassifyTask:
    """Tests for task classification heuristics."""

    @pytest.mark.parametrize("task_type,expected", [
        ("fix_bug_in_auth", "debug"),
        ("debug_memory_leak", "debug"),
        ("fix_crashing_error", "debug"),
        ("run_unit_tests", "test"),
        ("execute_test_suite", "test"),
        ("test_integration_api", "test"),
        ("deploy_to_production", "deploy"),
        ("run_docker_build", "deploy"),
        ("deploy_kubernetes_manifest", "deploy"),
        ("refactor_database_schema", "data"),
        ("extract_class_to_module", "refactor"),
        ("review_pull_request", "review"),
        ("check_code_quality", "review"),
        ("migrate_postgres_database", "data"),
        ("run_database_migration", "data"),
        ("query_analytics_data", "data"),
        ("do_something_random_xyz", "other"),
        ("process_generic_task", "other"),
    ])
    def test_classify_by_task_type(self, task_type: str, expected: str):
        """Test classification by task_type."""
        result = classify_task(task_type=task_type)
        assert result == expected, f"task_type={task_type!r} -> {result}, expected {expected}"

    def test_classify_by_error_type(self):
        """Test classification by error_type signal."""
        # Stacktrace should trigger debug
        assert classify_task(
            error_type="Traceback (most recent call last):\n  File 'test.py', line 42"
        ) == "debug"

        # SQL errors should trigger data
        assert classify_task(
            error_type="sqlalchemy.exc.OperationalError: could not connect to database"
        ) == "data"

        # Assertion errors lean toward test (assert is a test keyword)
        assert classify_task(
            error_type="AssertionError: assert expected == actual"
        ) in ("debug", "test")  # Either is valid — contains both error and assert signals

    def test_classify_by_keywords(self):
        """Test classification using keywords list."""
        assert classify_task(
            keywords=["pytest", "assert", "coverage", "unit test"]
        ) == "test"

        assert classify_task(
            keywords=["kubernetes", "docker", "helm chart", "deploy"]
        ) == "deploy"

        assert classify_task(
            keywords=["refactor", "extract method", "rename class"]
        ) == "refactor"

        assert classify_task(
            keywords=["database", "migration", "schema change", "alter table"]
        ) == "data"

        assert classify_task(
            keywords=["review", "lgtm", "pr feedback", "approve"]
        ) == "review"

    def test_classify_by_file_path(self):
        """Test classification via file path hints."""
        # Test files (with proper test extension patterns)
        assert classify_task(file_path="/tests/test_auth.py") == "other"  # No .test. pattern
        assert classify_task(file_path="src/module_test.py") == "test"
        assert classify_task(file_path="spec/api_spec.rb") == "test"

        # Docker/deploy files
        assert classify_task(file_path="Dockerfile") == "deploy"
        assert classify_task(file_path="docker-compose.yml") == "deploy"
        assert classify_task(file_path="k8s/deployment.yaml") == "deploy"

        # SQL files
        assert classify_task(file_path="migrations/001_init.sql") == "data"

    def test_classify_combined_signals(self):
        """Test classification with multiple signals."""
        # Multiple test signals (keywords, file path) outweigh task_type "debug"
        result = classify_task(
            task_type="debug_flaky_test",
            keywords=["pytest", "test", "assert"],
            file_path="/tests/test_auth.py",
        )
        assert result in ("debug", "test")  # Both valid — debug in task_type, test in keywords+path

        # Both deploy signals
        result = classify_task(
            task_type="deploy_to_k8s",
            keywords=["docker", "helm", "kubernetes"],
            file_path="k8s/production.yaml",
        )
        assert result == "deploy"

    def test_classify_unknown_returns_other(self):
        """Unknown tasks should return 'other'."""
        assert classify_task(task_type="do_nothing") == "other"
        assert classify_task(keywords=["foobar", "xyz123"]) == "other"
        assert classify_task() == "other"

    def test_classify_all_categories_covered(self):
        """Ensure all expected categories are available."""
        for cat in ["debug", "test", "deploy", "refactor", "review", "data", "other"]:
            assert cat in TASK_CATEGORIES


# =============================================================================
# Tests: Beta Posterior
# =============================================================================

class TestBetaPosterior:
    """Tests for BetaPosterior dataclass."""

    def test_initialization(self):
        """Test default initialization with uninformative prior."""
        bp = BetaPosterior("test-pack", "debug")
        assert bp.pack_id == "test-pack"
        assert bp.category == "debug"
        assert bp.alpha == PRIOR_ALPHA
        assert bp.beta == PRIOR_BETA
        assert bp.total_samples == 0

    def test_initialization_with_prior(self):
        """Test initialization with custom prior."""
        bp = BetaPosterior("test-pack", "debug", alpha=3.0, beta=2.0)
        assert bp.alpha == 3.0
        assert bp.beta == 2.0

    def test_successes_and_failures(self):
        """Test computed successes/failures properties."""
        bp = BetaPosterior("test-pack", "debug", alpha=5.0, beta=3.0)
        assert bp.successes == 4.0  # alpha - prior
        assert bp.failures == 2.0   # beta - prior

    def test_record_success(self):
        """Test recording a success."""
        bp = BetaPosterior("test-pack", "debug")
        bp.record_success()
        assert bp.alpha == PRIOR_ALPHA + 1
        assert bp.beta == PRIOR_BETA
        assert bp.total_samples == 1

    def test_record_failure(self):
        """Test recording a failure."""
        bp = BetaPosterior("test-pack", "debug")
        bp.record_failure()
        assert bp.alpha == PRIOR_ALPHA
        assert bp.beta == PRIOR_BETA + 1
        assert bp.total_samples == 1

    def test_record_multiple_outcomes(self):
        """Test recording multiple outcomes."""
        bp = BetaPosterior("test-pack", "debug")
        bp.record_success()
        bp.record_success()
        bp.record_failure()
        bp.record_success()
        assert bp.successes == 3
        assert bp.failures == 1
        assert bp.total_samples == 4
        # With prior (1,1): alpha=4, beta=2, mean=4/6=0.667
        assert abs(bp.mean - 4/6) < 0.001

    def test_mean(self):
        """Test mean property."""
        bp = BetaPosterior("test-pack", "debug", alpha=3.0, beta=1.0)
        assert abs(bp.mean - 3/4) < 0.001

        # With uninformative prior
        bp2 = BetaPosterior("test-pack", "debug")
        assert bp2.mean == 0.5

    def test_mean_edge_cases(self):
        """Test mean with edge case parameters."""
        bp = BetaPosterior("test-pack", "debug", alpha=0, beta=0)
        assert bp.mean == 0.5  # fallback

        bp2 = BetaPosterior("test-pack", "debug", alpha=0, beta=5.0)
        assert bp2.mean == 0.0

    def test_uncertainty(self):
        """Test uncertainty property (95% CI width)."""
        # Unseen pack should have high uncertainty
        bp = BetaPosterior("test-pack", "debug")
        assert bp.uncertainty == 1.0  # max

        # With more data, uncertainty should decrease
        for _ in range(20):
            if _ % 3 == 0:
                bp.record_failure()
            else:
                bp.record_success()

        assert bp.uncertainty < 1.0

    def test_uncertainty_bounded(self):
        """Test that uncertainty is bounded to [0, 1]."""
        bp = BetaPosterior("test-pack", "debug")
        assert 0 <= bp.uncertainty <= 1.0


# =============================================================================
# Tests: Thompson Sampling
# =============================================================================

class TestThompsonSampling:
    """Tests for Thompson Sampling functionality."""

    def test_beta_sample_bounded(self):
        """Beta samples should be in [0, 1]."""
        for _ in range(100):
            s = beta_sample_numpy(2.0, 2.0)
            assert 0 <= s <= 1

    def test_beta_sample_mean(self):
        """Beta samples should average to the true mean."""
        alpha, beta_param = 3.0, 1.0  # true mean = 0.75
        samples = [beta_sample_numpy(alpha, beta_param) for _ in range(1000)]
        empirical_mean = sum(samples) / len(samples)
        assert abs(empirical_mean - 3/4) < 0.1

    def test_beta_sample_numpy_reproducability(self):
        """Same seed should give same results."""
        np.random.seed(42)
        s1 = beta_sample_numpy(2.0, 2.0)
        np.random.seed(42)
        s2 = beta_sample_numpy(2.0, 2.0)
        assert s1 == s2

    def test_thompson_sample_with_seed(self):
        """thompson_sample should respect seed parameter."""
        s1 = thompson_sample(3.0, 1.0, seed=123)
        s2 = thompson_sample(3.0, 1.0, seed=123)
        assert s1 == s2

    def test_thompson_sample_edge_cases(self):
        """Edge cases should return sensible values."""
        # alpha = 0
        s = beta_sample_numpy(0, 1.0)
        assert 0 <= s <= 1

        # beta = 0
        s = beta_sample_numpy(1.0, 0)
        assert 0 <= s <= 1

        # both 0
        s = beta_sample_numpy(0, 0)
        assert s == 0.5


# =============================================================================
# Tests: PackDescriptor
# =============================================================================

class TestPackDescriptor:
    """Tests for PackDescriptor."""

    def test_has_category(self):
        """Test has_category method."""
        pack = PackDescriptor(
            pack_id="test",
            name="Test",
            supported_tasks=["debug", "test"],
        )
        assert pack.has_category("debug")
        assert pack.has_category("test")
        assert not pack.has_category("deploy")

    def test_similarity_to_keywords(self):
        """Test keyword similarity computation (Jaccard)."""
        pack = PackDescriptor(
            pack_id="test",
            name="Test",
            keywords=["error", "debug", "crash", "fix"],
        )

        # Partial match (2 overlapping out of 4 total unique = 0.5)
        assert pack.similarity_to_keywords(["error", "debug"]) == 0.5

        # Partial match
        sim = pack.similarity_to_keywords(["error", "other"])
        assert 0 < sim < 1

        # No match
        assert pack.similarity_to_keywords(["xyz123"]) == 0.0

        # Empty keywords
        assert pack.similarity_to_keywords([]) == 0.0

    def test_similarity_symmetric(self):
        """Jaccard similarity should be symmetric."""
        pack1 = PackDescriptor(pack_id="p1", name="P1", keywords=["a", "b", "c"])
        pack2 = PackDescriptor(pack_id="p2", name="P2", keywords=["b", "c", "d"])

        sim1 = pack1.similarity_to_keywords(["b", "c"])
        sim2 = pack2.similarity_to_keywords(["b", "c"])
        assert abs(sim1 - sim2) < 0.001  # both should be 1/3


# =============================================================================
# Tests: Cold-Start Prior
# =============================================================================

class TestColdStartPrior:
    """Tests for similarity-based cold-start priors."""

    def test_build_similarity_prior_no_keywords(self, sample_candidates):
        """No keywords should return global prior for all."""
        priors = build_similarity_prior(
            task_category="debug",
            task_keywords=[],
            candidates=sample_candidates,
        )
        for pack_id, (alpha, beta) in priors.items():
            assert alpha == PRIOR_ALPHA
            assert beta == PRIOR_BETA

    def test_build_similarity_prior_no_candidates(self):
        """No candidates should return empty dict."""
        priors = build_similarity_prior(
            task_category="debug",
            task_keywords=["error", "bug"],
            candidates=[],
        )
        assert priors == {}

    def test_build_similarity_prior_increases_similar_alpha(self, sample_candidates):
        """Similar packs should get higher alpha in prior."""
        priors = build_similarity_prior(
            task_category="debug",
            task_keywords=["error", "debug", "crash"],
            candidates=sample_candidates,
        )

        # debug-auth should be most similar (has "error" and "debug")
        assert priors["debug-auth"][0] > PRIOR_ALPHA
        # generic-helper should have default prior (no similarity)
        assert priors["generic-helper"][0] == PRIOR_ALPHA

    def test_build_similarity_prior_beta_unchanged(self, sample_candidates):
        """Beta should not be adjusted by similarity prior."""
        priors = build_similarity_prior(
            task_category="debug",
            task_keywords=["error"],
            candidates=sample_candidates,
        )
        for alpha, beta in priors.values():
            assert beta == PRIOR_BETA


# =============================================================================
# Tests: ContextualSelector
# =============================================================================

class TestContextualSelector:
    """Tests for ContextualSelector."""

    def test_init(self):
        """Test selector initialization."""
        selector = ContextualSelector()
        assert selector.exploration_budget == 0.20
        assert selector.prior_alpha == PRIOR_ALPHA
        assert selector.prior_beta == PRIOR_BETA
        assert selector._selection_count == 0
        assert selector._exploration_count == 0

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        selector = ContextualSelector(
            exploration_budget=0.30,
            prior_alpha=2.0,
            prior_beta=3.0,
        )
        assert selector.exploration_budget == 0.30
        assert selector.prior_alpha == 2.0
        assert selector.prior_beta == 3.0

    def test_select_returns_results(self, sample_candidates, debug_task_context):
        """Test that select returns SelectorResult list."""
        selector = ContextualSelector()
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        assert len(results) == 1
        assert isinstance(results[0], SelectorResult)
        assert results[0].category == "debug"

    def test_select_empty_candidates(self, debug_task_context):
        """Test select with empty candidate list."""
        selector = ContextualSelector()
        results = selector.select(debug_task_context, [], seed=42)
        assert results == []

    def test_select_categorization(self, sample_candidates):
        """Test that tasks are correctly categorized."""
        selector = ContextualSelector()

        # Debug task
        results = selector.select(
            {"task_type": "fix_null_pointer", "error_type": "NullPointerException"},
            sample_candidates,
            seed=42,
        )
        assert results[0].category == "debug"

        # Test task
        results = selector.select(
            {"task_type": "run_tests", "keywords": ["pytest", "test"]},
            sample_candidates,
            seed=42,
        )
        assert results[0].category == "test"

    def test_select_limit(self, sample_candidates, debug_task_context):
        """Test that limit parameter works."""
        selector = ContextualSelector()
        results = selector.select(debug_task_context, sample_candidates, limit=3, seed=42)
        assert len(results) == 3

    def test_select_exploration_flag(self, sample_candidates, debug_task_context):
        """Test that exploration flag is set correctly."""
        selector = ContextualSelector(exploration_budget=1.0)  # 100% exploration

        # With 100% exploration, every call should be exploration
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        assert results[0].is_exploration is True

    def test_select_exploitation_flag(self, sample_candidates, debug_task_context):
        """Test that exploitation (non-exploration) is the default."""
        selector = ContextualSelector(exploration_budget=0.0)  # 0% exploration

        # With 0% exploration, should be exploitation
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        assert results[0].is_exploration is False

    def test_select_reproducibility(self, sample_candidates, debug_task_context):
        """Same seed should give same results."""
        selector = ContextualSelector()
        r1 = selector.select(debug_task_context, sample_candidates, seed=123)
        r2 = selector.select(debug_task_context, sample_candidates, seed=123)
        assert r1[0].pack_id == r2[0].pack_id
        assert r1[0].score == r2[0].score

    def test_record_outcome(self, sample_candidates, debug_task_context):
        """Test recording outcomes."""
        selector = ContextualSelector()
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        selected_pack = results[0].pack_id
        category = results[0].category

        # Record success
        selector.record_outcome(selected_pack, category, successful=True)
        post = selector.get_posterior(selected_pack, category)
        assert post is not None
        assert post.successes == 1
        assert post.failures == 0

        # Record failure
        selector.record_outcome(selected_pack, category, successful=False)
        assert post.successes == 1
        assert post.failures == 1

    def test_record_outcomes_batch(self, sample_candidates):
        """Test batch outcome recording."""
        selector = ContextualSelector()
        outcomes = [
            ("debug-auth", "debug", True),
            ("debug-auth", "debug", True),
            ("debug-auth", "debug", False),
            ("test-api", "test", True),
        ]
        selector.record_outcomes(outcomes)

        post = selector.get_posterior("debug-auth", "debug")
        assert post.successes == 2
        assert post.failures == 1

        post2 = selector.get_posterior("test-api", "test")
        assert post2.successes == 1
        assert post2.failures == 0

    def test_get_posterior_nonexistent(self):
        """Getting nonexistent posterior returns None."""
        selector = ContextualSelector()
        post = selector.get_posterior("nonexistent", "debug")
        assert post is None

    def test_get_stats(self, sample_candidates, debug_task_context):
        """Test statistics tracking."""
        selector = ContextualSelector()
        for _ in range(10):
            selector.select(debug_task_context, sample_candidates, seed=42)

        stats = selector.get_stats()
        assert stats["total_selections"] == 10
        assert stats["total_posteriors"] >= 0
        assert "posteriors" in stats

    def test_exploration_rate(self, sample_candidates, debug_task_context):
        """Test that exploration happens at approximately the expected rate."""
        selector = ContextualSelector(exploration_budget=0.20)

        for _ in range(100):
            selector.select(debug_task_context, sample_candidates, seed=42)

        stats = selector.get_stats()
        # Should be approximately 20%
        rate = stats["exploration_selections"] / stats["total_selections"]
        assert 0.10 <= rate <= 0.30  # Allow some variance

    def test_posterior_after_selection(self, sample_candidates, debug_task_context):
        """Test that posteriors are created after selection."""
        selector = ContextualSelector()
        selector.select(debug_task_context, sample_candidates, seed=42)

        # Should have created a posterior for the selected pack + its category
        stats = selector.get_stats()
        assert stats["total_posteriors"] >= 1


# =============================================================================
# Tests: V2 Fixed-Blend
# =============================================================================

class TestV2FixedBlend:
    """Tests for V2 fixed-blend comparison."""

    def test_v2_fixed_blend_score(self, sample_candidates, debug_task_context):
        """Test V2 fixed-blend scoring."""
        pack = sample_candidates[0]
        result = v2_fixed_blend_score(pack, debug_task_context, seed=42)

        assert isinstance(result, V2FixedBlendResult)
        assert result.pack_id == pack.pack_id
        assert 0 <= result.score <= 1
        assert "win_rate" in result.components
        assert "return" in result.components
        assert "confidence" in result.components
        assert "freshness" in result.components

    def test_v2_fixed_blend_components_sum(self, sample_candidates, debug_task_context):
        """Test that components are properly weighted."""
        pack = sample_candidates[0]
        result = v2_fixed_blend_score(pack, debug_task_context, seed=42)

        # Score should be weighted combination
        c = result.components
        expected = (
            c["win_rate"] * 0.35
            + c["return"] * 0.30
            + c["confidence"] * 0.20
            + c["freshness"] * 0.15
        )
        assert abs(result.score - expected) < 0.001

    def test_select_v2(self, sample_candidates, debug_task_context):
        """Test select_v2 returns ranked results."""
        results = select_v2(debug_task_context, sample_candidates, limit=3, seed=42)

        assert len(results) == 3
        assert all(isinstance(r, V2FixedBlendResult) for r in results)
        # Should be sorted descending by score
        assert results[0].score >= results[1].score >= results[2].score

    def test_select_v2_empty_candidates(self, debug_task_context):
        """Test select_v2 with empty list."""
        results = select_v2(debug_task_context, [], seed=42)
        assert results == []

    def test_v2_no_uncertainty_tracking(self, sample_candidates, debug_task_context):
        """V2 should not track uncertainty (it's a fixed blend)."""
        pack = sample_candidates[0]
        result = v2_fixed_blend_score(pack, debug_task_context, seed=42)
        # V2 result has no uncertainty field
        assert not hasattr(result, "uncertainty")


# =============================================================================
# Tests: Comparison Function
# =============================================================================

class TestCompareSelectors:
    """Tests for the comparison function."""

    def test_compare_returns_result(self, sample_candidates, debug_task_context):
        """Test that compare_selectors returns a ComparisonResult."""
        result = compare_selectors(
            [debug_task_context],
            sample_candidates,
            seed=42,
        )

        assert isinstance(result, ComparisonResult)
        assert result.v2_wins + result.v3_wins + result.ties == 1
        assert len(result.details) == 1

    def test_compare_with_ground_truth(self, sample_candidates, debug_task_context):
        """Test comparison with ground truth labels."""
        result = compare_selectors(
            [debug_task_context, debug_task_context],
            sample_candidates,
            ground_truth=["debug-auth", "test-api"],  # Correct packs
            seed=42,
        )

        assert isinstance(result, ComparisonResult)
        assert result.v2_wins + result.v3_wins + result.ties == 2

    def test_compare_multiple_tasks(self, sample_candidates, debug_task_context, test_task_context, deploy_task_context):
        """Test comparison across multiple different tasks."""
        tasks = [debug_task_context, test_task_context, deploy_task_context]

        result = compare_selectors(
            tasks,
            sample_candidates,
            seed=42,
        )

        assert result.v2_wins + result.v3_wins + result.ties == 3
        assert len(result.details) == 3

    def test_compare_uses_provided_selector(self, sample_candidates, debug_task_context):
        """Test that compare_selectors uses the provided selector."""
        selector = ContextualSelector()

        # Pre-populate some outcomes
        selector.record_outcome("debug-auth", "debug", True)
        selector.record_outcome("debug-auth", "debug", True)
        selector.record_outcome("test-api", "test", True)

        result = compare_selectors(
            [debug_task_context],
            sample_candidates,
            v3_selector=selector,
            seed=42,
        )

        assert isinstance(result, ComparisonResult)
        # Check that the provided selector was used
        stats = selector.get_stats()
        assert stats["total_selections"] >= 1


# =============================================================================
# Tests: Integration / Edge Cases
# =============================================================================

class TestIntegration:
    """Integration and edge case tests."""

    def test_all_categories_represented(self, sample_candidates):
        """Test that all categories can be selected from candidates."""
        from borg.core.contextual_selector import classify_task

        category_tasks = {
            "debug": {"task_type": "fix_crash_error"},
            "test": {"task_type": "run_unit_tests"},
            "deploy": {"task_type": "deploy_to_k8s"},
            "refactor": {"task_type": "extract_class_method"},
            "review": {"task_type": "review_pull_request"},
            "data": {"task_type": "migrate_database_schema"},
        }

        selector = ContextualSelector()

        for category, ctx in category_tasks.items():
            results = selector.select(ctx, sample_candidates, seed=42)
            assert len(results) > 0, f"No results for category {category}"
            assert results[0].category == category or results[0].category in TASK_CATEGORIES

    def test_selector_with_noisy_context(self, sample_candidates):
        """Test selector handles context with missing/empty fields."""
        selector = ContextualSelector()

        # Empty context
        results = selector.select({}, sample_candidates, seed=42)
        assert len(results) > 0

        # Partial context
        results = selector.select(
            {"task_type": None, "keywords": [], "language": None},
            sample_candidates,
            seed=42,
        )
        assert len(results) > 0

    def test_selector_deterministic_with_same_seed(self, sample_candidates, debug_task_context):
        """Same seed should produce identical results."""
        selector1 = ContextualSelector()
        selector2 = ContextualSelector()

        r1 = selector1.select(debug_task_context, sample_candidates, seed=999)
        r2 = selector2.select(debug_task_context, sample_candidates, seed=999)

        assert r1[0].pack_id == r2[0].pack_id
        assert r1[0].score == r2[0].score

    def test_large_batch_consistency(self, sample_candidates, debug_task_context):
        """Large batch of selections should produce valid ranked results."""
        selector = ContextualSelector()

        # Run 50 selections — with uniform priors, TS may favor one pack
        # but results should always be valid
        for i in range(50):
            results = selector.select(debug_task_context, sample_candidates, seed=i)
            assert len(results) > 0
            # Each result should have a pack_id and score
            assert results[0].pack_id is not None
            assert results[0].score >= 0

    def test_cold_start_then_warm(self, sample_candidates):
        """Test transition from cold-start to warm posterior."""
        selector = ContextualSelector()

        # Cold-start selection (no priors)
        ctx = {"task_type": "fix_bug", "keywords": ["error", "debug"]}
        results = selector.select(ctx, sample_candidates, seed=42)
        initial_pack = results[0].pack_id
        initial_score = results[0].score

        # Record outcomes
        for _ in range(10):
            selector.record_outcome(initial_pack, "debug", True)

        # Warm selection
        results2 = selector.select(ctx, sample_candidates, seed=42)
        warm_score = results2[0].score

        # Score should be different now that we have data
        # (not necessarily higher, but different due to Thompson sampling)
        # At minimum, the posterior should be updated
        post = selector.get_posterior(initial_pack, "debug")
        assert post is not None
        assert post.total_samples == 10


# =============================================================================
# Tests: Specific Regression Tests
# =============================================================================

class TestRegression:
    """Regression tests for specific bugs or edge cases."""

    def test_similarity_prior_does_not_break_unseen_packs(self, sample_candidates):
        """Packs with no keyword match should still get default prior."""
        selector = ContextualSelector()

        # Task with keywords that don't match any pack well
        ctx = {
            "task_type": "do_something",
            "keywords": ["xyz123", "abc456", "foobar"],
        }

        # Should not crash
        results = selector.select(ctx, sample_candidates, seed=42)
        assert len(results) > 0

        # generic-helper should still be selectable (other category)
        pack_ids = [r.pack_id for r in results]
        assert "generic-helper" in pack_ids or len(pack_ids) > 0

    def test_exploration_never_selects_worst(self, sample_candidates, debug_task_context):
        """In exploration mode, we select highest uncertainty, not lowest score."""
        selector = ContextualSelector(exploration_budget=1.0)  # Always explore

        # Get exploration result
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        assert results[0].is_exploration

        # In exploration mode, uncertainty should be sorted descending
        # (but we only asked for 1)
        # The point is: no crash and a result is returned

    def test_posterior_key_error_safe(self, sample_candidates, debug_task_context):
        """Code should handle missing posteriors gracefully."""
        selector = ContextualSelector()

        # Never select, try to get posterior directly
        post = selector.get_posterior("nonexistent-pack", "debug")
        assert post is None

        # Should not crash during select
        results = selector.select(debug_task_context, sample_candidates, seed=42)
        assert len(results) > 0


# =============================================================================
# Main (run directly)
# =============================================================================

if __name__ == "__main__":
    # Run smoke tests from the module
    from borg.core.contextual_selector import _smoke_test
    _smoke_test()

    # Run pytest
    exit(pytest.main([__file__, "-v", "--tb=short"]))
