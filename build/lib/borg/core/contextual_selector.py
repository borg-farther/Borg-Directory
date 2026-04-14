"""
Borg V3 — Hierarchical Contextual Thompson Sampling Selector.

Task classification -> Beta posteriors per category -> Thompson Sampling with
20% exploration budget -> cold-start via similarity-based priors.

No new dependencies beyond numpy (already present).
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False


# ----------------------------------------------------------------------
# Task Categories
# ----------------------------------------------------------------------

TASK_CATEGORIES = frozenset([
    "debug", "test", "deploy", "refactor", "review", "data", "other"
])

# Uninformative prior for Beta-Binomial
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0

# Exploration budget
EXPLORATION_BUDGET = 0.20


# ----------------------------------------------------------------------
# Task Classification via Heuristics
# ----------------------------------------------------------------------

# Keyword sets per category (lowercase)
_CATEGORY_KEYWORDS = {
    "debug": {
        "error", "bug", "crash", "exception", "fail", "failed", "failure",
        "fix", "issue", "problem", "broken", "debug", "traceback", "stack",
        "panic", "assertion", "assert failed", "no such file", "undefined",
        "null", "none", "timeout", "refused", "denied", "segmentation",
    },
    "test": {
        "test", "spec", "specs", "pytest", "unittest", "jest", "mocha",
        "coverage", "integration test", "unit test", "e2e", "end-to-end",
        "assert", "expect", "should", "it(", "describe(", "test_", "_test.",
        ".test.", ".spec.", "testing", "testable",
    },
    "deploy": {
        "deploy", "deployment", "kubernetes", "k8s", "docker", "container",
        "ci/cd", "pipeline", "production", "release", "rollback", "ingress",
        "helm", "terraform", "ansible", "provision", "serverless", "lambda",
        "azure", "aws", "gcp", "cloud", "devops", "nginx", "apache",
    },
    "refactor": {
        "refactor", "restructure", "rename", "extract", "move", "inline",
        "replace", "simplify", "cleanup", "technical debt", "improve",
        "rewrite", "consolidate", "abstract", "interface", "decouple",
        "modular", "split", "merge", "combine",
    },
    "review": {
        "review", "pull request", "pull-request", "approve", "check", "审核", "检查",
        "critique", "feedback", "suggestion", "comment", "lgtm", "ship it",
        "needs work", "looks good", "approved",
    },
    "data": {
        "migration", "migrate", "database", "db", "sql", "nosql", "schema",
        "dataset", "analytics", "pipeline", "etl", "warehouse", "bigquery",
        "postgres", "mysql", "mongodb", "redis", "elasticsearch", "index",
        "query", "crud", "aggregate",
    },
}

# File extension hints (keys must be quoted where they start with .)
_EXTENSION_CATEGORIES = {
    ".test.": "test", "_test.": "test", ".spec.": "test", "_spec.": "test",
    ".debug.": "debug",
    ".deploy.": "deploy",
    "Dockerfile": "deploy",
    "docker-compose": "deploy",
    ".yaml": "deploy",  # kubernetes configs
    ".yml": "deploy",
    "deployment": "deploy",
    ".sql": "data",
    "migration": "data",
}


def classify_task(
    task_type: Optional[str] = None,
    error_type: Optional[str] = None,
    language: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    file_path: Optional[str] = None,
) -> str:
    """Classify a task into a category using heuristics.

    Combines multiple signals: explicit task_type, error_type, language,
    keywords list, and file_path to determine the task category.

    Args:
        task_type: Explicit task type hint (e.g. "fix_bug", "run_tests")
        error_type: Error classification (e.g. "stacktrace", "assertion_error")
        language: Programming language (e.g. "python", "typescript")
        keywords: List of keyword strings from task description
        file_path: File path being operated on

    Returns:
        Category string: one of debug, test, deploy, refactor, review, data, other
    """
    scores: Dict[str, float] = {cat: 0.0 for cat in TASK_CATEGORIES}

    # 1. task_type signal (highest priority if informative)
    if task_type:
        task_lower = task_type.lower()
        for cat, kws in _CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in task_lower:
                    scores[cat] += 3.0  # task_type matches count triple

    # 2. error_type signal
    if error_type:
        err_lower = error_type.lower()
        # Check domain-specific error patterns first
        for cat, kws in _CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in err_lower:
                    scores[cat] += 1.5
        # Stacktraces and errors get a debug boost — but only if no stronger domain signal
        if any(sig in err_lower for sig in ("traceback", "exception", "panic:", "segfault")):
            scores["debug"] += 5.0

    # 3. keywords list signal
    if keywords:
        for kw in keywords:
            kw_lower = kw.lower() if isinstance(kw, str) else str(kw).lower()
            for cat, kws in _CATEGORY_KEYWORDS.items():
                if kw_lower in kws:
                    scores[cat] += 1.0

    # 4. file_path extension hints
    if file_path:
        path_lower = file_path.lower()
        # Check extension-based rules first
        for pattern, cat in _EXTENSION_CATEGORIES.items():
            if pattern.lower() in path_lower:
                scores[cat] += 1.5
        # Language extension hints
        lang_ext_map = {
            "python": ".py",
            "typescript": ".ts",
            "javascript": ".js",
            "rust": ".rs",
            "go": ".go",
            "java": ".java",
            "sql": ".sql",
            "shell": ".sh",
        }
        if language:
            ext = lang_ext_map.get(language.lower(), f".{language.lower()}")
            if path_lower.endswith(ext):
                scores["data" if language.lower() == "sql" else "other"] += 0.5

    # 5. Language-based scoring
    if language:
        lang_lower = language.lower()
        if lang_lower in {"python", "ruby", "perl", "php"}:
            scores["debug"] += 0.3  # dynamically typed languages often debug
        if lang_lower in {"sql", "postgresql", "mysql"}:
            scores["data"] += 0.5

    # Find highest scoring category (other is fallback)
    # Only consider categories with positive scores (matched at least one keyword)
    best_cat = "other"
    best_score = 0.0  # Only match if score > 0
    for cat in TASK_CATEGORIES:
        if cat != "other" and scores[cat] > best_score:
            best_score = scores[cat]
            best_cat = cat

    return best_cat


# ----------------------------------------------------------------------
# Beta Posteriors
# ----------------------------------------------------------------------

@dataclass
class BetaPosterior:
    """Beta-Binomial posterior for a (pack, category) pair."""
    pack_id: str
    category: str
    alpha: float = PRIOR_ALPHA  # wins + prior
    beta: float = PRIOR_BETA    # losses + prior
    total_samples: int = 0

    @property
    def successes(self) -> float:
        """Wins = alpha - prior."""
        return max(0.0, self.alpha - PRIOR_ALPHA)

    @property
    def failures(self) -> float:
        """Losses = beta - prior."""
        return max(0.0, self.beta - PRIOR_BETA)

    @property
    def mean(self) -> float:
        """Posterior mean."""
        total = self.alpha + self.beta
        return self.alpha / total if total > 0 else 0.5

    @property
    def uncertainty(self) -> float:
        """Uncertainty = width of 95% CI (higher = more exploration needed)."""
        if self.alpha <= 0 or self.beta <= 0:
            return 1.0  # max uncertainty
        # Normal approximation for Beta
        mean = self.alpha / (self.alpha + self.beta)
        var = (self.alpha * self.beta) / (
            (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        )
        std = math.sqrt(var)
        # 95% CI width
        return min(1.0, 4.0 * std)

    def record_success(self) -> None:
        """Record a successful outcome."""
        self.alpha += 1.0
        self.total_samples += 1

    def record_failure(self) -> None:
        """Record a failed outcome."""
        self.beta += 1.0
        self.total_samples += 1


# ----------------------------------------------------------------------
# Pack Descriptor (minimal interface for contextual selector)
# ----------------------------------------------------------------------

@dataclass
class PackDescriptor:
    """Minimal pack description for the contextual selector.

    This is a lightweight alternative to DeFiStrategyPack for general
    (non-DeFi) pack selection. Packs in borg/core/ pack system can provide
    this minimal interface.
    """
    pack_id: str
    name: str
    keywords: List[str] = field(default_factory=list)  # domain/skill keywords
    language: Optional[str] = None
    supported_tasks: List[str] = field(default_factory=list)  # e.g. ["debug", "test"]
    description: str = ""
    # Historical performance per category (if available)
    category_stats: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    # similarity vector for cold-start (keyword embedding skip-gram / BM25-ish)
    feature_vector: Optional[List[float]] = None

    def has_category(self, category: str) -> bool:
        """Check if pack claims to support a category."""
        return category in self.supported_tasks

    def similarity_to_keywords(self, keywords: List[str]) -> float:
        """Compute keyword overlap (Jaccard) for cold-start prior."""
        if not keywords or not self.keywords:
            return 0.0
        a = set(k.lower() for k in self.keywords)
        b = set(k.lower() for k in keywords)
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0


# ----------------------------------------------------------------------
# Cold-Start Prior via Similarity
# ----------------------------------------------------------------------


def build_similarity_prior(
    task_category: str,
    task_keywords: List[str],
    candidates: List[PackDescriptor],
    global_alpha: float = PRIOR_ALPHA,
    global_beta: float = PRIOR_BETA,
) -> Dict[str, Tuple[float, float]]:
    """Build a prior for unseen (pack, category) pairs via keyword similarity.

    For packs with no history in the target category, we borrow strength
    from packs that have similar keyword profiles using Jaccard similarity.

    Args:
        task_category: The category we're selecting for
        task_keywords: Keywords from the current task
        candidates: All candidate packs
        global_alpha: Prior alpha to start from
        global_beta: Prior beta to start from

    Returns:
        Dict mapping pack_id -> (alpha, beta) adjusted prior
    """
    if not task_keywords or not candidates:
        return {p.pack_id: (global_alpha, global_beta) for p in candidates}

    # Compute similarity for each candidate
    priors: Dict[str, Tuple[float, float]] = {}
    for pack in candidates:
        sim = pack.similarity_to_keywords(task_keywords)
        if sim > 0:
            # Blend toward global prior proportional to (1 - sim)
            # Higher sim -> less smoothing toward prior
            alpha_adj = global_alpha + sim * 2.0  # slight boost to alpha
            beta_adj = global_beta
            priors[pack.pack_id] = (alpha_adj, beta_adj)
        else:
            priors[pack.pack_id] = (global_alpha, global_beta)

    return priors


# ----------------------------------------------------------------------
# Thompson Sampling Core
# ----------------------------------------------------------------------


def beta_sample_numpy(alpha: float, beta_param: float) -> float:
    """Sample from Beta distribution using numpy.

    Args:
        alpha: Alpha (wins + prior)
        beta_param: Beta (losses + prior)

    Returns:
        Sample from Beta(alpha, beta_param)
    """
    if not _NUMPY_AVAILABLE:
        # Fallback: return mean of Beta distribution
        return alpha / (alpha + beta_param) if (alpha + beta_param) > 0 else 0.5
    if alpha <= 0 or beta_param <= 0:
        return alpha / (alpha + beta_param) if (alpha + beta_param) > 0 else 0.5
    return float(np.random.beta(alpha, beta_param))


def thompson_sample(
    alpha: float,
    beta_param: float,
    seed: Optional[int] = None,
) -> float:
    """Thompson Sample from Beta(alpha, beta).

    Args:
        alpha: Alpha parameter
        beta_param: Beta parameter
        seed: Optional random seed for reproducibility

    Returns:
        Sampled value from Beta distribution
    """
    if seed is not None:
        np.random.seed(seed)
    return beta_sample_numpy(alpha, beta_param)


# ----------------------------------------------------------------------
# Contextual Selector
# ----------------------------------------------------------------------


@dataclass
class SelectorResult:
    """Result of a selector recommendation."""
    pack_id: str
    category: str
    score: float
    sampled_value: float
    uncertainty: float
    is_exploration: bool = False
    reputation: float = 0.5


class ContextualSelector:
    """Hierarchical Contextual Thompson Sampling selector.

    Selects packs using:
    1. Task classification into categories
    2. Per-category Beta posteriors for each pack
    3. Thompson Sampling for exploration/exploitation balance
    4. 20% explicit exploration (pick highest uncertainty)
    5. Cold-start via similarity-based priors

    Usage:
        selector = ContextualSelector()
        result = selector.select(task_context, candidates)
    """

    def __init__(
        self,
        exploration_budget: float = EXPLORATION_BUDGET,
        prior_alpha: float = PRIOR_ALPHA,
        prior_beta: float = PRIOR_BETA,
        feedback_loop=None,
    ):
        """Initialize the selector.

        Args:
            exploration_budget: Fraction of calls that force exploration (default 0.20)
            prior_alpha: Beta prior alpha (default 1.0 = uninformative)
            prior_beta: Beta prior beta (default 1.0 = uninformative)
            feedback_loop: Optional FeedbackLoop instance for signal-based boost
        """
        self.exploration_budget = exploration_budget
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self._feedback_loop = feedback_loop
        # Main posterior store: (pack_id, category) -> BetaPosterior
        self._posteriors: Dict[Tuple[str, str], BetaPosterior] = {}
        # Total selection calls (for exploration budget tracking)
        self._selection_count = 0
        self._exploration_count = 0

    def _get_posterior(
        self,
        pack_id: str,
        category: str,
        create: bool = True,
    ) -> Optional[BetaPosterior]:
        """Get or create a posterior for (pack, category)."""
        key = (pack_id, category)
        if key not in self._posteriors:
            if create:
                self._posteriors[key] = BetaPosterior(
                    pack_id=pack_id,
                    category=category,
                    alpha=self.prior_alpha,
                    beta=self.prior_beta,
                )
            else:
                return None
        return self._posteriors[key]

    def feedback_signal_boost(self, pack_id: str) -> float:
        """Compute multiplicative boost from FeedbackLoop signals.

        Returns float in [0.0, 2.0]. Values < 1.0 reduce sampling
        probability (negative drift); values > 1.0 increase it (positive drift).
        """
        if not hasattr(self, '_feedback_loop') or self._feedback_loop is None:
            return 1.0  # neutral
        signals = self._feedback_loop.get_signals(pack_id)
        if not signals:
            return 1.0  # neutral
        quality = sum(s.quality_score for s in signals) / len(signals)
        trend = sum(s.success_rate_trend for s in signals) / len(signals)
        boost = quality * (1.0 + trend / 2.0)
        return max(0.0, min(2.0, boost))

    def record_outcome(
        self,
        pack_id: str,
        category: str,
        successful: bool,
    ) -> None:
        """Record an execution outcome for a (pack, category) pair.

        Args:
            pack_id: The pack that was selected
            category: The category of the task
            successful: Whether the execution was successful
        """
        posterior = self._get_posterior(pack_id, category)
        if posterior:
            if successful:
                posterior.record_success()
            else:
                posterior.record_failure()

    def record_outcomes(
        self,
        outcomes: List[Tuple[str, str, bool]],
    ) -> None:
        """Record multiple outcomes at once.

        Args:
            outcomes: List of (pack_id, category, successful) tuples
        """
        for pack_id, category, successful in outcomes:
            self.record_outcome(pack_id, category, successful)

    def _should_explore(self) -> bool:
        """Determine if this call should be an exploration call.

        Returns True with probability = exploration_budget.
        Uses a simple counter-based approach for deterministic behavior.
        """
        if self.exploration_budget <= 0.0:
            return False
        if self.exploration_budget >= 1.0:
            self._selection_count += 1
            self._exploration_count += 1
            return True
        # 20% of calls are exploration (every 5th call)
        self._selection_count += 1
        if self._selection_count % 5 == 0:  # Every 5th call
            self._exploration_count += 1
            return True
        return False

    def select(
        self,
        task_context: Dict[str, Any],
        candidates: List[PackDescriptor],
        limit: int = 1,
        seed: Optional[int] = None,
    ) -> List[SelectorResult]:
        """Select the best pack(s) for a task using contextual Thompson Sampling.

        Args:
            task_context: Dict with keys:
                - task_type: Optional[str]
                - error_type: Optional[str]
                - language: Optional[str]
                - keywords: Optional[List[str]]
                - file_path: Optional[str]
            candidates: List of candidate PackDescriptor objects
            limit: Number of packs to return (default 1)
            seed: Optional random seed

        Returns:
            List of SelectorResult, ordered by score descending
        """
        if not candidates:
            return []

        # 1. Classify the task
        category = classify_task(
            task_type=task_context.get("task_type"),
            error_type=task_context.get("error_type"),
            language=task_context.get("language"),
            keywords=task_context.get("keywords"),
            file_path=task_context.get("file_path"),
        )

        # 2. Build similarity prior for cold-start
        task_keywords = task_context.get("keywords", [])
        sim_priors = build_similarity_prior(
            task_category=category,
            task_keywords=task_keywords,
            candidates=candidates,
            global_alpha=self.prior_alpha,
            global_beta=self.prior_beta,
        )

        # 3. Thompson sample per candidate
        results: List[SelectorResult] = []
        is_exploration = self._should_explore()

        for pack in candidates:
            # Get posterior (or create with similarity-adjusted prior)
            posterior = self._get_posterior(pack.pack_id, category, create=True)

            if posterior:
                alpha = posterior.alpha
                beta_param = posterior.beta
                uncertainty = posterior.uncertainty
                reputation = posterior.mean
            else:
                # Cold-start: use similarity prior
                alpha, beta_param = sim_priors.get(
                    pack.pack_id,
                    (self.prior_alpha, self.prior_beta),
                )
                uncertainty = 1.0  # max uncertainty for unseen
                reputation = alpha / (alpha + beta_param) if (alpha + beta_param) > 0 else 0.5

            # Thompson sample
            sampled = thompson_sample(alpha, beta_param, seed=seed)

            # Apply feedback signal boost
            boost = self.feedback_signal_boost(pack.pack_id)
            sampled *= boost

            results.append(SelectorResult(
                pack_id=pack.pack_id,
                category=category,
                score=sampled,
                sampled_value=sampled,
                uncertainty=uncertainty,
                is_exploration=is_exploration,
                reputation=reputation,
            ))

        # 4. Rank results
        if is_exploration:
            # Exploration: pick by highest uncertainty
            results.sort(key=lambda r: r.uncertainty, reverse=True)
        else:
            # Exploitation: pick by highest Thompson sample
            results.sort(key=lambda r: r.score, reverse=True)

        # Mark exploration results
        for r in results:
            r.is_exploration = is_exploration

        return results[:limit]

    def get_posterior(
        self,
        pack_id: str,
        category: str,
    ) -> Optional[BetaPosterior]:
        """Get the posterior for a specific (pack, category) pair."""
        return self._get_posterior(pack_id, category, create=False)

    def get_stats(self) -> Dict[str, Any]:
        """Get selector statistics."""
        return {
            "total_selections": self._selection_count,
            "exploration_selections": self._exploration_count,
            "exploration_rate": (
                self._exploration_count / self._selection_count
                if self._selection_count > 0
                else 0.0
            ),
            "total_posteriors": len(self._posteriors),
            "posteriors": {
                f"{p.pack_id}|{p.category}": {
                    "alpha": p.alpha,
                    "beta": p.beta,
                    "mean": p.mean,
                    "uncertainty": p.uncertainty,
                }
                for p in self._posteriors.values()
            },
        }


# ----------------------------------------------------------------------
# V2 Fixed-Blend Selector (for comparison)
# ----------------------------------------------------------------------


@dataclass
class V2FixedBlendResult:
    """Result from V2 fixed-blend selector."""
    pack_id: str
    category: str  # Added: the task category for this result
    score: float
    components: Dict[str, float]


def v2_fixed_blend_score(
    pack: PackDescriptor,
    task_context: Dict[str, Any],
    seed: Optional[int] = None,
) -> V2FixedBlendResult:
    """Compute V2-style fixed-blend score for comparison.

    V2 formula: win_rate*0.35 + return*0.30 + confidence*0.20 + freshness*0.15

    For general packs (non-DeFi), we adapt as:
    - win_rate: from category_stats or uniform
    - return: derived from success rate in supported_tasks
    - confidence: based on total_samples
    - freshness: default 0.5 (no temporal data)

    Args:
        pack: PackDescriptor to score
        task_context: Task context dict
        seed: Optional random seed

    Returns:
        V2FixedBlendResult with score and components
    """
    if seed is not None:
        np.random.seed(seed)

    # Extract signals
    category = classify_task(
        task_type=task_context.get("task_type"),
        error_type=task_context.get("error_type"),
        language=task_context.get("language"),
        keywords=task_context.get("keywords"),
        file_path=task_context.get("file_path"),
    )

    # Win rate from category stats or prior
    successes, failures = pack.category_stats.get(category, (0, 0))
    total = successes + failures
    if total > 0:
        win_rate = successes / total
    else:
        # Uniform prior for unseen
        win_rate = 0.5

    # Simulated return: map win_rate to a return-like score
    # (For DeFi this is actual return_pct; for general packs we use win_rate)
    return_score = win_rate  # simplified

    # Confidence based on sample count (log scale)
    if total == 0:
        confidence = 0.0
    elif total < 3:
        confidence = 0.1 * total
    else:
        confidence = min(1.0, 0.3 + 0.1 * math.log2(total))

    # Freshness (default 0.5 for general packs)
    freshness = 0.5

    # Fixed blend
    score = (
        win_rate * 0.35
        + return_score * 0.30
        + confidence * 0.20
        + freshness * 0.15
    )

    return V2FixedBlendResult(
        pack_id=pack.pack_id,
        category=category,
        score=score,
        components={
            "win_rate": win_rate,
            "return": return_score,
            "confidence": confidence,
            "freshness": freshness,
        },
    )


def select_v2(
    task_context: Dict[str, Any],
    candidates: List[PackDescriptor],
    limit: int = 1,
    seed: Optional[int] = None,
) -> List[V2FixedBlendResult]:
    """Run V2 fixed-blend selection for comparison.

    Args:
        task_context: Task context dict
        candidates: List of candidate packs
        limit: Max results to return

    Returns:
        List of V2FixedBlendResult sorted by score descending
    """
    if not candidates:
        return []

    results = [v2_fixed_blend_score(p, task_context, seed=seed) for p in candidates]
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


# ----------------------------------------------------------------------
# Comparison Function
# ----------------------------------------------------------------------


@dataclass
class ComparisonResult:
    """Result of comparing V2 vs V3 selector."""
    v2_wins: int
    v3_wins: int
    ties: int
    v2_total_score: float
    v3_total_score: float
    details: List[Dict[str, Any]]


def compare_selectors(
    task_contexts: List[Dict[str, Any]],
    candidates: List[PackDescriptor],
    v3_selector: Optional[ContextualSelector] = None,
    ground_truth: Optional[List[str]] = None,
    seed: int = 42,
) -> ComparisonResult:
    """Compare V2 fixed-blend vs V3 contextual selector on identical inputs.

    Runs both selectors on the same task contexts and candidates, then
    compares which selection is "better" based on:
    1. Which selector picks the pack with higher actual win rate (if known)
    2. If no ground truth, uses the V3 selector's posterior as proxy

    Args:
        task_contexts: List of task context dicts to test
        candidates: Candidate packs available for selection
        v3_selector: Optional pre-configured ContextualSelector
                     If None, creates a fresh one.
        ground_truth: Optional list of correct pack_ids per task
                      If provided, used as the win metric.
        seed: Random seed for reproducibility

    Returns:
        ComparisonResult with win counts and detailed breakdown
    """
    if v3_selector is None:
        v3_selector = ContextualSelector()

    v2_wins = 0
    v3_wins = 0
    ties = 0
    v2_total = 0.0
    v3_total = 0.0
    details: List[Dict[str, Any]] = []

    np.random.seed(seed)

    for i, ctx in enumerate(task_contexts):
        # Run V2 selection
        v2_results = select_v2(ctx, candidates, limit=1, seed=seed + i)
        v2_top = v2_results[0] if v2_results else None

        # Run V3 selection
        v3_results = v3_selector.select(ctx, candidates, limit=1, seed=seed + i)
        v3_top = v3_results[0] if v3_results else None

        if v2_top is None or v3_top is None:
            continue

        # Determine ground truth winner
        if ground_truth and i < len(ground_truth):
            correct_pack = ground_truth[i]
            v2_correct = v2_top.pack_id == correct_pack
            v3_correct = v3_top.pack_id == correct_pack
            v2_score_for = 1.0 if v2_correct else 0.0
            v3_score_for = 1.0 if v3_correct else 0.0
        else:
            # Use V3 posterior as proxy for true quality
            v3_post = v3_selector.get_posterior(v3_top.pack_id, v3_top.category)
            if v3_post and v3_post.total_samples > 0:
                v3_true_win_rate = v3_post.mean
            else:
                # Check category_stats for ground truth
                pack_desc = next(
                    (p for p in candidates if p.pack_id == v3_top.pack_id), None
                )
                if pack_desc:
                    succ, fail = pack_desc.category_stats.get(
                        v3_top.category, (1, 1)
                    )
                    v3_true_win_rate = succ / (succ + fail) if (succ + fail) > 0 else 0.5
                else:
                    v3_true_win_rate = 0.5

            v2_post = v3_selector.get_posterior(v2_top.pack_id, v2_top.category)
            if v2_post and v2_post.total_samples > 0:
                v2_true_win_rate = v2_post.mean
            else:
                pack_desc = next(
                    (p for p in candidates if p.pack_id == v2_top.pack_id), None
                )
                if pack_desc:
                    succ, fail = pack_desc.category_stats.get(
                        v2_top.category, (1, 1)
                    )
                    v2_true_win_rate = succ / (succ + fail) if (succ + fail) > 0 else 0.5
                else:
                    v2_true_win_rate = 0.5

            v2_score_for = v2_true_win_rate
            v3_score_for = v3_true_win_rate

        v2_total += v2_score_for
        v3_total += v3_score_for

        if v2_score_for > v3_score_for:
            v2_wins += 1
        elif v3_score_for > v2_score_for:
            v3_wins += 1
        else:
            ties += 1

        details.append({
            "task_index": i,
            "task_type": ctx.get("task_type", "unknown"),
            "category": v3_top.category,
            "v2_selected": v2_top.pack_id,
            "v2_score": v2_top.score,
            "v2_true_win_rate": v2_score_for,
            "v3_selected": v3_top.pack_id,
            "v3_score": v3_top.score,
            "v3_true_win_rate": v3_score_for,
            "v3_uncertainty": v3_top.uncertainty,
            "winner": "v2" if v2_score_for > v3_score_for else ("v3" if v3_score_for > v2_score_for else "tie"),
        })

    return ComparisonResult(
        v2_wins=v2_wins,
        v3_wins=v3_wins,
        ties=ties,
        v2_total_score=v2_total,
        v3_total_score=v3_total,
        details=details,
    )


# ----------------------------------------------------------------------
# Self-tests / smoke tests (run when executed directly)
# ----------------------------------------------------------------------

def _smoke_test():
    """Run smoke tests when module is executed directly."""
    print("Running contextual_selector smoke tests...")

    # Test task classification
    assert classify_task(task_type="fix_bug_in_auth") == "debug"
    assert classify_task(task_type="debug_memory_leak") == "debug"
    assert classify_task(task_type="run_unit_tests") == "test"
    assert classify_task(task_type="execute_test_suite") == "test"
    assert classify_task(task_type="deploy_to_kubernetes") == "deploy"
    assert classify_task(task_type="run_docker_build") == "deploy"
    assert classify_task(task_type="extract_class_method") == "refactor"
    assert classify_task(task_type="rename_variables_refactor") == "refactor"
    assert classify_task(task_type="review_pull_request") == "review"
    assert classify_task(task_type="check_code_quality") == "review"
    assert classify_task(task_type="migrate_postgres_db") == "data"
    assert classify_task(task_type="run_database_migration") == "data"
    assert classify_task(task_type="random_task_xyz") == "other"
    print("  - classify_task: PASS")

    # Test with error patterns
    assert classify_task(
        error_type="NullPointerException at line 42"
    ) == "debug"
    assert classify_task(
        task_type="test_auth_module",
        keywords=["pytest", "unit test"]
    ) == "test"
    print("  - classify_task with error/keywords: PASS")

    # Test BetaPosterior
    bp = BetaPosterior("test-pack", "debug")
    assert bp.successes == 0
    assert bp.failures == 0
    assert abs(bp.mean - 0.5) < 0.01  # uninformative prior

    bp.record_success()
    bp.record_success()
    bp.record_failure()
    assert bp.successes == 2
    assert bp.failures == 1
    assert bp.total_samples == 3
    # With prior (1,1): alpha=3, beta=2, mean=3/5=0.6
    assert abs(bp.mean - 0.6) < 0.01
    print("  - BetaPosterior: PASS")

    # Test Thompson sampling
    samples = [beta_sample_numpy(2.0, 1.0) for _ in range(100)]
    assert all(0 <= s <= 1 for s in samples)
    assert abs(sum(samples) / len(samples) - 2/3) < 0.1  # should be near 0.67
    print("  - Thompson sampling: PASS")

    # Test similarity prior
    candidates = [
        PackDescriptor(
            pack_id="p1",
            name="Debug Pack",
            keywords=["error", "debug", "crash"],
            supported_tasks=["debug", "other"],
        ),
        PackDescriptor(
            pack_id="p2",
            name="Test Pack",
            keywords=["test", "pytest", "coverage"],
            supported_tasks=["test", "other"],
        ),
        PackDescriptor(
            pack_id="p3",
            name="Generic Pack",
            keywords=["general", "utility"],
            supported_tasks=["other"],
        ),
    ]

    priors = build_similarity_prior(
        task_category="debug",
        task_keywords=["error", "bug", "crash"],
        candidates=candidates,
    )
    assert priors["p1"][0] > priors["p3"][0]  # p1 should get higher alpha (similar)
    print("  - Similarity prior: PASS")

    # Test selector
    selector = ContextualSelector(exploration_budget=0.20)

    ctx = {"task_type": "debug_login_error", "keywords": ["error", "null"]}
    results = selector.select(ctx, candidates, seed=42)
    assert len(results) == 1
    assert results[0].category == "debug"
    print("  - ContextualSelector.select: PASS")

    # Test with no candidates
    empty_results = selector.select(ctx, [], seed=42)
    assert empty_results == []
    print("  - Empty candidates: PASS")

    # Test V2 comparison
    v2_result = v2_fixed_blend_score(candidates[0], ctx, seed=42)
    assert hasattr(v2_result, "score")
    assert hasattr(v2_result, "components")
    print("  - V2 fixed blend: PASS")

    # Test comparison
    comparison = compare_selectors(
        [ctx, ctx, ctx],
        candidates,
        v3_selector=selector,
        seed=42,
    )
    assert comparison.v2_wins + comparison.v3_wins + comparison.ties == 3
    print("  - compare_selectors: PASS")

    # Test exploration tracking
    initial_count = selector._selection_count
    for _ in range(100):
        selector.select(ctx, candidates, seed=42)
    stats = selector.get_stats()
    assert stats["total_selections"] == initial_count + 100
    # Approximately 20% should be exploration (allow some variance)
    expected_exp = int(100 / 5)
    assert abs(stats["exploration_selections"] - expected_exp) <= 5
    print("  - Exploration tracking: PASS")

    print("\nAll smoke tests passed!")


if __name__ == "__main__":
    _smoke_test()
