#!/usr/bin/env python3
"""
Statistical Analysis Framework for A/B Experiment:
AI Agent Performance with vs without Reasoning Cache Tool (Borg)

Design constraints:
- 25 tasks (20 treatment-sensitive, 5 control)
- Each task run twice: control (no tool) vs treatment (with tool)
- Paired design: same task evaluated in both conditions
- Metrics: success (binary), tokens (continuous), time (continuous)
- Budget: ~100 total runs (≈25-50 paired observations)

Answers the 7 key statistical questions with specific numbers.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import warnings

import numpy as np
from scipy import stats
from scipy.stats import mannwhitneyu, wilcoxon, chi2_contingency, binomtest
import numpy as np

# Optional: try to import statsmodels for power analysis
try:
    from statsmodels.stats.power import TTestIndPower, TTestPower
    from statsmodels.stats.correlation_tools import cov_nearest
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


def mcnemar_exact(table: np.ndarray) -> Tuple[float, float]:
    """
    McNemar's exact test for paired binary data.
    
    Args:
        table: 2x2 contingency table [[a, b], [c, d]]
               a = both fail, b = ctrl fail/tx success
               c = ctrl success/tx fail, d = both succeed
    
    Returns:
        (statistic, p_value) - statistic is the minimum of b and c
    """
    b, c = table[0, 1], table[1, 0]
    n = b + c
    if n == 0:
        return 0.0, 1.0
    
    # Exact binomial test (two-sided)
    # Under null, b and c should be equal, so each has probability 0.5
    # We test if the observed imbalance is unlikely
    result_b = binomtest(b, n, 0.5, alternative='two-sided')
    result_c = binomtest(c, n, 0.5, alternative='two-sided')
    p_value = 2 * min(result_b.pvalue, result_c.pvalue)
    p_value = min(1.0, p_value)  # cap at 1.0
    
    # Statistic is the number of discordant pairs (b + c)
    return float(n), p_value


def mcnemar_asymptotic(table: np.ndarray) -> Tuple[float, float]:
    """
    McNemar's asymptotic test (chi-square with continuity correction).
    
    Args:
        table: 2x2 contingency table
    
    Returns:
        (chi2 statistic, p_value)
    """
    b, c = table[0, 1], table[1, 0]
    n = b + c
    if n == 0:
        return 0.0, 1.0
    
    # Chi-square with continuity correction
    chi2 = (abs(b - c) - 1) ** 2 / n if n > 0 else 0
    p_value = 1 - chi2_contingency(table)[1]  # get p-value directly
    
    # Recalculate properly
    from scipy.stats import chi2 as chi2_dist
    p_value = 1 - chi2_dist.cdf(chi2, df=1)
    
    return float(chi2), p_value

warnings.filterwarnings('ignore', category=FutureWarning)


# =============================================================================
# QUESTION 1: SAMPLE SIZE & STATISTICAL POWER
# =============================================================================

@dataclass
class PowerAnalysisResult:
    """Results of power analysis."""
    n_pairs_required: int
    n_pairs_available: int
    effect_size: float
    alpha: float
    power: float
    min_detectable_effect: float
    actual_power: float
    meets_budget: bool
    
    def summary(self) -> str:
        return f"""
=== SAMPLE SIZE & POWER ANALYSIS ===
Required pairs for 80% power (d={self.effect_size}, α={self.alpha}): {self.n_pairs_required}
Pairs available under 100-run budget: {self.n_pairs_available}
Effect size used: {self.effect_size:.3f}

ACTUAL STATISTICAL POWER with {self.n_pairs_available} pairs: {self.actual_power:.1%}
Minimum detectable effect at {self.n_pairs_available} pairs, 80% power: {self.min_detectable_effect:.1%}

Budget constraint: {"✓ MET" if self.meets_budget else "✗ EXCEEDED"}
"""


def calculate_sample_size_paired(d: float = 0.5, alpha: float = 0.05, power: float = 0.80) -> int:
    """
    Calculate required sample size for paired t-test.
    
    Uses the formula: n = 2 * (z_α/2 + z_β)² / d² for paired design
    where d = Cohen's d = δ / σ_diff (standardized effect size)
    
    For paired design, effective n is the number of PAIRS.
    With 100 runs total, max pairs = 50.
    """
    if HAS_STATSMODELS:
        # Use statsmodels for more accurate calculation
        # For paired t-test, we use the same formula but with paired df
        from statsmodels.stats.power import TTestPower
        power_analysis = TTestPower()
        # Need to convert Cohen's d to something compatible
        # For paired: n = (z_α + z_β)² / d²
        from scipy.stats import norm
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        n = ((z_alpha + z_beta) ** 2) / (d ** 2)
        return int(np.ceil(n))
    else:
        # Manual calculation using normal approximation
        # n = 2 * (z_α/2 + z_β)² / d²  (for independent groups)
        # n = (z_α/2 + z_β)² / d²       (for paired, since paired reduces variance)
        from scipy.stats import norm
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        n = ((z_alpha + z_beta) ** 2) / (d ** 2)
        return int(np.ceil(n))


def calculate_actual_power(n_pairs: int, d: float = 0.5, alpha: float = 0.05) -> float:
    """
    Calculate actual statistical power given n pairs and effect size.
    
    For paired design with high variance:
    Power = P(reject H₀ | H₁ true)
    
    Using normal approximation for the test statistic.
    """
    from scipy.stats import norm
    z_alpha = norm.ppf(1 - alpha/2)
    # Non-central parameter for given n and effect size
    # Test statistic: Z = d * sqrt(n) under H1
    ncp = d * np.sqrt(n_pairs)
    # Power = P(|Z| > z_alpha | H1 true) = P(Z > z_alpha - ncp) + P(Z < -z_alpha - ncp)
    power = 1 - norm.cdf(z_alpha - ncp) + norm.cdf(-z_alpha - ncp)
    return min(1.0, max(0.0, power))


def calculate_min_detectable_effect(n_pairs: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """
    Given n pairs, what's the minimum detectable effect at 80% power?
    
    Solving for d: n = (z_α + z_β)² / d²
    => d = sqrt((z_α + z_β)² / n)
    """
    from scipy.stats import norm
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)
    d = (z_alpha + z_beta) / np.sqrt(n_pairs)
    return d


def analyze_sample_size(max_runs: int = 100, target_improvement: float = 0.30,
                         alpha: float = 0.05, target_power: float = 0.80) -> PowerAnalysisResult:
    """
    Comprehensive sample size and power analysis.
    
    For 30% improvement detection:
    - We need to define what "30% improvement" means per metric
    - Success rate: 30% relative improvement (e.g., 60% → 78%)
    - Time/tokens: 30% reduction (e.g., 1000 → 700)
    - Cohen's d ≈ 0.5-0.6 for a "medium" effect (30% in same-domain metrics)
    """
    # With 100 runs max, we can do at most 50 pairs
    # (each pair = 1 control run + 1 treatment run)
    max_pairs = max_runs // 2
    
    # For 30% improvement, we estimate Cohen's d
    # Rule of thumb: 0.2=small, 0.5=medium, 0.8=large
    # 30% improvement in a high-variance task typically corresponds to d ≈ 0.4-0.6
    # Conservative estimate: d = 0.5 (medium effect)
    effect_size = 0.5
    
    n_required = calculate_sample_size_paired(d=effect_size, alpha=alpha, power=target_power)
    actual_power = calculate_actual_power(max_pairs, d=effect_size, alpha=alpha)
    min_detectable = calculate_min_detectable_effect(max_pairs, alpha=alpha, power=target_power)
    
    return PowerAnalysisResult(
        n_pairs_required=n_required,
        n_pairs_available=max_pairs,
        effect_size=effect_size,
        alpha=alpha,
        power=target_power,
        min_detectable_effect=min_detectable,
        actual_power=actual_power,
        meets_budget=n_required <= max_pairs
    )


# =============================================================================
# QUESTION 2: PAIRED vs INDEPENDENT DESIGN
# =============================================================================

def get_design_recommendation() -> str:
    """
    Analysis of paired vs independent (between-subject) design.
    
    RECOMMENDATION: PAIRED (within-subject) design is STRONGLY preferred.
    
    Rationale:
    1. Same task run with/without tool = paired comparison
    2. Reduces variance by controlling for task difficulty
    3. High variance in AI agent performance (5-30 min) means
       task-to-task variance is large; pairing controls this
    4. Each task serves as its own control
    5. 50% budget savings (2 runs per task vs 2× tasks per condition)
    
    Within-subject (paired) vs Between-subject (independent):
    - Within-subject: Same task evaluated both ways ✓ RECOMMENDED
    - Between-subject: Different tasks per condition (half tasks in each)
    
    The high variance mentioned (5-30 min) is WITHIN-TASK variance,
    meaning same task can vary widely. Paired design is essential
    to control for task difficulty as a confound.
    """
    return """
=== PAIRED DESIGN ANALYSIS ===

RECOMMENDATION: USE PAIRED (WITHIN-SUBJECT) DESIGN

Reasons:
1. SAME TASK evaluated in both conditions → controls for task difficulty
2. HIGH VARIANCE (5-30 min for same task) means between-task variance is enormous
3. PAIRED = 2 runs per task (100 runs / 2 = 50 pairs with 25 tasks)
4. BETWEEN-SUBJECT would require 2× tasks for same statistical power

Within-subject (Paired) vs Between-subject (Independent):
┌─────────────────────┬────────────────────┬────────────────────┐
│     Criterion       │   Paired (Within)   │  Independent (Between)│
├─────────────────────┼────────────────────┼────────────────────┤
│ Runs per task       │        2            │        2            │
│ Tasks per condition │       25            │       25            │
│ Total runs needed   │       50            │      100            │
│ Variance reduction │   Controls task     │  Task variance     │
│                    │   difficulty        │  remains confoun   │
│ Statistical power   │   Higher (paired   │   Lower (requires  │
│                    │   error reduction)  │   larger n)        │
└─────────────────────┴────────────────────┴────────────────────┘

Order effects are controlled via counterbalancing (see Question 4).
"""


# =============================================================================
# QUESTION 3: PRIMARY METRIC SELECTION
# =============================================================================

@dataclass
class MetricPowerAnalysis:
    """Power analysis for different metric types."""
    metric_name: str
    metric_type: str  # 'binary' or 'continuous'
    estimated_variance: float
    effect_size_type: str  # 'cohen_d', 'odds_ratio', 'relative_risk'
    estimated_effect_size: float
    power_at_n25: float
    power_at_n50: float
    recommendation: str


def analyze_metric_power(n_pairs: int = 25, base_success_rate: float = 0.5,
                         base_time: float = 1000, base_tokens: float = 10000,
                         improvement: float = 0.30) -> List[MetricPowerAnalysis]:
    """
    Compare statistical power across metric types.
    
    Key insight: Continuous metrics (time, tokens) have MORE power than
    binary metrics (success) because they capture graded effects.
    
    For binary outcome:
    - McNemar's test power depends on discordant pairs
    - With p=50% baseline, need many more pairs for same power
    
    For continuous outcomes:
    - Paired t-test / Wilcoxon has higher power
    - Effect size in original units → standardized for comparison
    """
    results = []
    
    # 1. SUCCESS RATE (binary)
    # McNemar's test power calculation
    # For 30% relative improvement: 50% → 65% success rate
    p1 = base_success_rate
    p2 = min(0.95, p1 * (1 + improvement))  # 50% → 65%
    
    # Power for McNemar's test (approximate)
    # Using normal approximation for discordant pairs
    from scipy.stats import norm
    n = n_pairs
    # Expected discordant pairs under H1
    theta = (p1 + p2) / 2
    # Simplified power calculation for McNemar
    # Effect size in terms of log odds ratio
    or_effect = (p2 * (1 - p1)) / (p1 * (1 - p2))
    log_or = np.log(or_effect)
    # Approximate SE under null
    se_null = np.sqrt(2 / n)
    se_alt = np.sqrt(1/(n*p1*(1-p1)) + 1/(n*p2*(1-p2)))
    
    # Power approximation
    z_alpha = norm.ppf(0.975)  # two-tailed
    z_power = (log_or - 1.96 * se_null) / se_alt
    power_binary = norm.cdf(z_power - z_alpha) + norm.cdf(-z_power - z_alpha)
    
    results.append(MetricPowerAnalysis(
        metric_name="Success Rate",
        metric_type="binary",
        estimated_variance=p1 * (1 - p1),
        effect_size_type="odds_ratio",
        estimated_effect_size=or_effect,
        power_at_n25=max(0, min(1, power_binary)),
        power_at_n50=max(0, min(1, norm.cdf((log_or - z_alpha * se_null) / (se_alt/np.sqrt(2))))),
        recommendation="LOWEST power. Binary outcomes lose information. Use ONLY if success is the ultimate metric."
    ))
    
    # 2. TOKEN CONSUMPTION (continuous)
    # Assuming coefficient of variation (CV) ≈ 0.5-1.0 for AI tasks
    # 30% reduction with high variance
    cv = 0.75  # Coefficient of variation
    sigma = base_tokens * cv
    delta = base_tokens * improvement  # 30% reduction
    d_tokens = delta / sigma  # Cohen's d for tokens
    
    power_tokens_n25 = calculate_actual_power(25, d=d_tokens)
    power_tokens_n50 = calculate_actual_power(50, d=d_tokens)
    
    results.append(MetricPowerAnalysis(
        metric_name="Token Consumption",
        metric_type="continuous",
        estimated_variance=(cv * base_tokens) ** 2,
        effect_size_type="cohen_d",
        estimated_effect_size=d_tokens,
        power_at_n25=power_tokens_n25,
        power_at_n50=power_tokens_n50,
        recommendation=f"HIGH power (d={d_tokens:.2f}). RECOMMENDED as primary metric."
    ))
    
    # 3. TIME TAKEN (continuous)
    # Similar analysis for time
    cv_time = 0.75
    sigma_time = base_time * cv_time
    delta_time = base_time * improvement
    d_time = delta_time / sigma_time
    
    power_time_n25 = calculate_actual_power(25, d=d_time)
    power_time_n50 = calculate_actual_power(50, d=d_time)
    
    results.append(MetricPowerAnalysis(
        metric_name="Time Taken",
        metric_type="continuous",
        estimated_variance=(cv_time * base_time) ** 2,
        effect_size_type="cohen_d",
        estimated_effect_size=d_time,
        power_at_n25=power_time_n25,
        power_at_n50=power_time_n50,
        recommendation=f"HIGH power (d={d_time:.2f}). Good alternative primary metric."
    ))
    
    # 4. COMPOSITE (combined)
    # Composite of success + efficiency has potential but complex analysis
    results.append(MetricPowerAnalysis(
        metric_name="Composite Score",
        metric_type="composite",
        estimated_variance=0.3,  # mixture
        effect_size_type="cohen_d",
        estimated_effect_size=max(d_tokens, d_time) * 0.9,  # slight loss
        power_at_n25=calculate_actual_power(25, d=max(d_tokens, d_time) * 0.9),
        power_at_n50=calculate_actual_power(50, d=max(d_tokens, d_time) * 0.9),
        recommendation="COMPLEX to analyze. May not improve power. Use individual metrics instead."
    ))
    
    return results


def get_metric_recommendation() -> str:
    """
    RECOMMENDATION: Token consumption OR Time as primary metric.
    
    Rationale:
    - Continuous metrics have more information → higher power
    - 30% reduction is meaningful in practical terms
    - Success rate is binary and loses information about degree of improvement
    
    Best practice: PRIMARY = Token reduction, SECONDARY = Time reduction,
    with Success rate as a sanity check.
    """
    return """
=== PRIMARY METRIC ANALYSIS ===

RECOMMENDATION: TOKEN CONSUMPTION as PRIMARY metric

Power comparison (estimated, n=25 pairs):
┌──────────────────┬──────────┬────────────────┬───────────────────────────┐
│     Metric       │   Type   │  Effect Size   │  Power (n=25)            │
├──────────────────┼──────────┼────────────────┼───────────────────────────┤
│ Success Rate     │ Binary   │ OR ≈ 1.5-2.0   │ ~45-55% (LOW)            │
│ Token Reduction  │ Contin.  │ d ≈ 0.4-0.5    │ ~60-70% (HIGH)           │
│ Time Reduction   │ Contin.  │ d ≈ 0.4-0.5    │ ~60-70% (HIGH)           │
│ Composite        │ Mixed    │ d ≈ 0.35-0.45  │ ~55-65% (MEDIUM)         │
└──────────────────┴──────────┴────────────────┴───────────────────────────┘

Why continuous > binary:
1. Binary (success/fail) discards magnitude information
   - Task solved in 100 tokens vs 5000 tokens → same binary outcome
2. Continuous captures degree of improvement
   - "How much better?" not just "better or not?"
3. Paired t-test on continuous data has higher asymptotic relative efficiency
   than McNemar's test on binary data when underlying process is continuous

RECOMMENDATION HIERARCHY:
1. PRIMARY: Token consumption (directly measures cost efficiency)
2. SECONDARY: Time taken (measures latency)
3. SANITY CHECK: Success rate (must not decrease)

If forced to choose ONE metric: Token reduction
If you can analyze multiple: Token + Time (with correction for multiple comparisons)
"""


# =============================================================================
# QUESTION 4: RANDOMIZATION STRATEGY
# =============================================================================

def get_randomization_strategy() -> str:
    """
    Randomization controls for three key confounds:
    
    1. ORDER EFFECTS: Does running first help/hurt due to learning/warmup?
       - Counterbalancing: Half tasks do control→treatment, half do treatment→control
       - Randomize order within each task pair
       
    2. TASK DIFFICULTY VARIATION: Some tasks inherently easier/harder
       - PAIRED design (same task both conditions) controls this
       - Within-task variance is the noise, not between-task difficulty
       
    3. MODEL STOCHASTICITY: AI model has randomness (temperature, sampling)
       - Run multiple trials per (task, condition) if budget allows
       - Use median instead of mean to reduce outlier influence
       - Report variance metrics alongside point estimates
    """
    return """
=== RANDOMIZATION STRATEGY ===

CONTROL OF CONFOUNDS:

1. ORDER EFFECTS (does going first help or hurt?)
   ─────────────────────────────────────────────
   SOLUTION: Counterbalancing + Randomization
   
   A. Within each task pair:
      - 50% of tasks: Control first → Treatment second
      - 50% of tasks: Treatment first → Control second
      
   B. Randomize task order:
      - Randomize which task runs first in the experiment queue
      - Use a random seed and record for reproducibility
      
   C. Statistical control:
      - Include order as a covariate in analysis
      - Test for period effects

2. TASK DIFFICULTY VARIATION
   ─────────────────────────────────────────────
   SOLUTION: PAIRED DESIGN (same task both conditions)
   
   - Within-task variance is noise, not bias
   - Paired t-test differences out task effects
   - Task is the unit of analysis, not individual runs
   
   For 25 tasks:
   - Each task gets both conditions → 50 total runs
   - Analysis: paired comparison within each task

3. MODEL STOCHASTICITY
   ─────────────────────────────────────────────
   SOLUTION: Multiple trials + robust statistics
   
   A. Multiple trials per (task, condition):
      - If budget allows: 2 trials per cell → 100 runs total
      - Use median across trials (robust to outliers)
      
   B. Report uncertainty:
      - Bootstrap confidence intervals
      - Standard error / interquartile range
      
   C. Seed control:
      - Set explicit random seeds for reproducibility
      - Use same seed for paired conditions (fair comparison)

RECOMMENDED RANDOMIZATION SCHEME:
┌────────┬─────────────────┬──────────────┬──────────────┐
│ Task # │  Condition A    │  Condition B │  Order       │
├────────┼─────────────────┼──────────────┼──────────────┤
│   1    │  Control        │  Treatment   │  A→B         │
│   2    │  Treatment      │  Control     │  B→A         │
│   3    │  Control        │  Treatment   │  A→B         │
│  ...   │  Randomized     │  ...         │  50/50 split │
└────────┴─────────────────┴──────────────┴──────────────┘

Implement with: random.shuffle() and record order for analysis
"""


# =============================================================================
# QUESTION 5: ANALYSIS PLAN - STATISTICAL TESTS
# =============================================================================

@dataclass
class TestResult:
    """Container for statistical test results."""
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    effect_size_name: str
    conclusion: str
    confidence_interval: Optional[Tuple[float, float]] = None
    n_observations: Optional[int] = None


def run_paired_wilcoxon(control: np.ndarray, treatment: np.ndarray,
                        metric_name: str = "metric") -> TestResult:
    """
    Paired Wilcoxon signed-rank test (non-parametric).
    
    Use when:
    - Data is ordinal or continuous but not normal
    - Same subjects/paired observations
    - Robust to outliers (more robust than paired t-test)
    
    Effect size: r = Z / sqrt(N) (rank-biserial correlation)
    """
    # Remove pairs with missing values
    valid_mask = ~(np.isnan(control) | np.isnan(treatment))
    c = control[valid_mask]
    t = treatment[valid_mask]
    n = len(c)
    
    if n < 5:
        return TestResult(
            test_name=f"Wilcoxon signed-rank ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="r",
            conclusion=f"Insufficient observations (n={n})",
            n_observations=n
        )
    
    # Difference: positive means treatment > control
    diff = c - t
    
    try:
        statistic, p_value = wilcoxon(diff, alternative='two-sided')
        
        # Effect size: r = Z / sqrt(N)
        # Z is approximately normal under null
        # We can derive Z from the test statistic or use the normal approximation
        z_approx = stats.norm.ppf(p_value / 2) if p_value > 0 else np.inf
        r = abs(z_approx) / np.sqrt(n)
        r = min(1.0, r)  # Cap at 1
        
        # Confidence interval via bootstrap
        ci = bootstrap_paired_diff(c, t, n_bootstrap=1000)
        
        return TestResult(
            test_name=f"Wilcoxon signed-rank ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            effect_size=r,
            effect_size_name="rank-biserial r",
            conclusion=f"Significant difference" if p_value < 0.05 else "No significant difference",
            confidence_interval=ci,
            n_observations=n
        )
    except Exception as e:
        return TestResult(
            test_name=f"Wilcoxon signed-rank ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="r",
            conclusion=f"Test failed: {str(e)}",
            n_observations=n
        )


def run_mcnemar_test(control_success: np.ndarray, treatment_success: np.ndarray,
                     metric_name: str = "success") -> TestResult:
    """
    McNemar's test for paired binary outcomes.
    
    Use when:
    - Binary outcome (success/fail)
    - Paired design (same task in both conditions)
    - Tests if discordant pairs are balanced
    
    Produces: odds ratio, confidence interval, p-value
    
    Example contingency table:
                    Treatment
                  Fail    Success
    Control Fail    a        b
          Success   c        d
    
    McNemar tests if b == c (balanced discordance)
    """
    # Create contingency table
    # a = both fail, b = control fail, treatment success
    # c = control success, treatment fail, d = both success
    
    n00 = np.sum((control_success == 0) & (treatment_success == 0))  # both fail
    n01 = np.sum((control_success == 0) & (treatment_success == 1))  # ctrl fail, tx success
    n10 = np.sum((control_success == 1) & (treatment_success == 0))  # ctrl success, tx fail
    n11 = np.sum((control_success == 1) & (treatment_success == 1))  # both success
    
    n = len(control_success)
    
    # McNemar's test (exact for small samples, asymptotic for large)
    # Using mid-p correction for more accurate p-values with small samples
    try:
        table = np.array([[n00, n01], [n10, n11]])
        if n01 + n10 < 20:
            # Exact binomial test (Stuart's method)
            # Under null, n01 and n10 should be equal
            # Test: is the proportion of b vs c significantly different?
            stat, p_value = mcnemar_exact(table)
        else:
            # Asymptotic McNemar
            stat, p_value = mcnemar_asymptotic(table)
        
        # Odds ratio = n01 / n10 (when n10 > 0)
        if n10 > 0:
            odds_ratio = n01 / n10
        elif n01 > 0:
            odds_ratio = np.inf
        else:
            odds_ratio = 1.0
        
        # Effect size: odds ratio interpretation
        # OR > 1 means treatment improves success rate
        if odds_ratio == np.inf:
            effect_str = "Treatment always better (no failures in treatment)"
        elif odds_ratio < 1:
            effect_str = f"OR = {odds_ratio:.2f} (treatment {1/odds_ratio:.1f}x more likely to succeed)"
        else:
            effect_str = f"OR = {odds_ratio:.2f} (treatment {odds_ratio:.1f}x more likely to succeed)"
        
        return TestResult(
            test_name=f"McNemar's test ({metric_name})",
            statistic=stat,
            p_value=p_value,
            effect_size=odds_ratio,
            effect_size_name="odds_ratio",
            conclusion=f"{'Significant' if p_value < 0.05 else 'No significant'} difference (p={p_value:.4f})",
            n_observations=n
        )
    except Exception as e:
        return TestResult(
            test_name=f"McNemar's test ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="odds_ratio",
            conclusion=f"Test failed: {str(e)}",
            n_observations=n
        )


def run_paired_ttest(control: np.ndarray, treatment: np.ndarray,
                     metric_name: str = "metric") -> TestResult:
    """
    Paired t-test for continuous outcomes.
    
    Use when:
    - Continuous outcome (time, tokens)
    - Paired design
    - Data approximately normal (use Wilcoxon if not)
    
    Effect size: Cohen's d (mean difference / std of differences)
    """
    valid_mask = ~(np.isnan(control) | np.isnan(treatment))
    c = control[valid_mask]
    t = treatment[valid_mask]
    n = len(c)
    
    if n < 3:
        return TestResult(
            test_name=f"Paired t-test ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="cohen_d",
            conclusion=f"Insufficient observations (n={n})",
            n_observations=n
        )
    
    diff = c - t
    mean_diff = np.mean(diff)
    std_diff = np.std(diff, ddof=1)
    se = std_diff / np.sqrt(n)
    
    try:
        t_stat, p_value = stats.ttest_rel(c, t, alternative='two-sided')
        
        # Cohen's d = mean_diff / std_diff
        # (using standard deviation of differences, not pooled)
        d = mean_diff / std_diff if std_diff > 0 else 0
        
        # Confidence interval for mean difference
        t_crit = stats.t.ppf(0.975, df=n-1)
        ci_lower = mean_diff - t_crit * se
        ci_upper = mean_diff + t_crit * se
        
        return TestResult(
            test_name=f"Paired t-test ({metric_name})",
            statistic=t_stat,
            p_value=p_value,
            effect_size=d,
            effect_size_name="cohen_d",
            conclusion=f"{'Significant' if p_value < 0.05 else 'No significant'} difference",
            confidence_interval=(ci_lower, ci_upper),
            n_observations=n
        )
    except Exception as e:
        return TestResult(
            test_name=f"Paired t-test ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="cohen_d",
            conclusion=f"Test failed: {str(e)}",
            n_observations=n
        )


def bootstrap_paired_diff(control: np.ndarray, treatment: np.ndarray,
                          n_bootstrap: int = 1000,
                          CI: float = 0.95) -> Tuple[float, float]:
    """
    Bootstrap confidence interval for paired difference.
    
    Uses percentile bootstrap (BCa would be better but more complex).
    
    Returns: (CI_lower, CI_upper)
    """
    valid_mask = ~(np.isnan(control) | np.isnan(treatment))
    c = control[valid_mask]
    t = treatment[valid_mask]
    n = len(c)
    
    if n < 3:
        return (np.nan, np.nan)
    
    diff = c - t
    observed_diff = np.mean(diff)
    
    # Bootstrap resampling
    np.random.seed(42)  # Reproducibility
    bootstrap_diffs = []
    for _ in range(n_bootstrap):
        indices = np.random.choice(n, size=n, replace=True)
        boot_diff = np.mean(diff[indices])
        bootstrap_diffs.append(boot_diff)
    
    bootstrap_diffs = np.array(bootstrap_diffs)
    
    # Percentile CI
    alpha = 1 - CI
    ci_lower = np.percentile(bootstrap_diffs, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_diffs, 100 * (1 - alpha / 2))
    
    return (ci_lower, ci_upper)


def run_mann_whitney_u(control: np.ndarray, treatment: np.ndarray,
                       metric_name: str = "metric") -> TestResult:
    """
    Mann-Whitney U test (independent groups, non-parametric).
    
    NOTE: This is for BETWEEN-SUBJECT comparison.
    For paired data, use Wilcoxon signed-rank.
    
    Effect size: rank-biserial correlation (r)
    """
    valid_mask = ~(np.isnan(control) | np.isnan(treatment))
    c = control[valid_mask]
    t = treatment[valid_mask]
    n1, n2 = len(c), len(t)
    
    if n1 < 3 or n2 < 3:
        return TestResult(
            test_name=f"Mann-Whitney U ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="rank-biserial r",
            conclusion=f"Insufficient observations (n1={n1}, n2={n2})",
            n_observations=n1 + n2
        )
    
    try:
        statistic, p_value = mannwhitneyu(c, t, alternative='two-sided')
        
        # Effect size: r = Z / sqrt(N)
        z_approx = stats.norm.ppf(p_value / 2) if p_value > 0 else np.inf
        r = abs(z_approx) / np.sqrt(n1 + n2)
        r = min(1.0, r)
        
        return TestResult(
            test_name=f"Mann-Whitney U ({metric_name})",
            statistic=statistic,
            p_value=p_value,
            effect_size=r,
            effect_size_name="rank-biserial r",
            conclusion=f"{'Significant' if p_value < 0.05 else 'No significant'} difference",
            n_observations=n1 + n2
        )
    except Exception as e:
        return TestResult(
            test_name=f"Mann-Whitney U ({metric_name})",
            statistic=np.nan,
            p_value=np.nan,
            effect_size=np.nan,
            effect_size_name="rank-biserial r",
            conclusion=f"Test failed: {str(e)}",
            n_observations=n1 + n2
        )


# =============================================================================
# QUESTION 6: MINIMUM DETECTABLE EFFECT
# =============================================================================

def calculate_mde(n_pairs: int = 25, alpha: float = 0.05, power: float = 0.80) -> Dict[str, float]:
    """
    Minimum Detectable Effect (MDE) for paired design.
    
    For different metrics, MDE means:
    - Success rate: Absolute percentage point increase
    - Time/Tokens: Percentage reduction (relative to baseline)
    
    Based on the formula: MDE = (z_α + z_β) / sqrt(n)
    For paired design with standardized effect size.
    """
    from scipy.stats import norm
    
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)
    
    # Standardized MDE (Cohen's d)
    mde_standardized = (z_alpha + z_beta) / np.sqrt(n_pairs)
    
    # For binary outcome (McNemar's test)
    # MDE in terms of probability difference
    # Approximation: need larger effect for binary
    mde_binary = np.sqrt(2 * (z_alpha + z_beta)**2 / n_pairs) * 0.5  # rough approximation
    
    return {
        "standardized_cohens_d": mde_standardized,
        "mde_tokens_pct": mde_standardized * 0.75,  # assuming CV=0.75
        "mde_time_pct": mde_standardized * 0.75,
        "mde_success_rate_ppt": mde_binary * 100,  # percentage points
        "at_n_pairs": n_pairs,
        "at_alpha": alpha,
        "at_power": power
    }


def get_mde_analysis() -> str:
    """
    Analysis of minimum detectable effect with 25 paired observations.
    """
    mde = calculate_mde(n_pairs=25)
    mde_50 = calculate_mde(n_pairs=50)
    
    return f"""
=== MINIMUM DETECTABLE EFFECT ANALYSIS ===

With 25 paired observations (α=0.05, 80% power):

Standardized effect (Cohen's d): {mde['standardized_cohens_d']:.3f}
  - Small effect: d ≈ 0.2
  - Medium effect: d ≈ 0.5  
  - Large effect: d ≈ 0.8

Interpretation for continuous metrics (assuming CV ≈ 75%):
  - Tokens: ~{mde['mde_tokens_pct']*100:.1f}% reduction detectable
  - Time:   ~{mde['mde_time_pct']*100:.1f}% reduction detectable

Interpretation for binary metric (success rate):
  - Success: ~{mde['mde_success_rate_ppt']:.1f} percentage point improvement

With 50 paired observations (if budget allows):
  - Standardized effect: {mde_50['standardized_cohens_d']:.3f}
  - Tokens: ~{mde_50['mde_tokens_pct']*100:.1f}% reduction
  - Time:   ~{mde_50['mde_time_pct']*100:.1f}% reduction
  - Success: ~{mde_50['mde_success_rate_ppt']:.1f} percentage points

CONCLUSION:
- With 25 pairs, you can detect ~40-50% effects reliably (d ≈ 0.56)
- With 50 pairs, you can detect ~30% effects (d ≈ 0.40)
- Your TARGET of 30% improvement is on the boundary of detectability
  with 25 pairs but achievable with proper analysis
"""


# =============================================================================
# QUESTION 7: MULTIPLE COMPARISONS CORRECTION
# =============================================================================

def get_multiple_comparisons_correction() -> str:
    """
    Multiple comparisons correction strategies.
    
    We have 3 metrics:
    1. Success rate (binary)
    2. Token consumption (continuous)
    3. Time taken (continuous)
    
    Methods:
    1. Bonferroni: α_adj = α / m (conservative)
    2. Holm-Bonferroni: Step-down procedure (less conservative)
    3. Benjamini-Hochberg: FDR control (most powerful for exploration)
    4. No correction: If metrics are orthogonal/families defined
    
    RECOMMENDATION:
    - If testing 3 metrics as PRIMARY outcomes: Use Holm-Bonferroni
    - If doing exploratory analysis: Benjamini-Hochberg (FDR)
    - If one PRIMARY metric: No correction needed for secondary metrics
    """
    return """
=== MULTIPLE COMPARISONS CORRECTION ===

We are testing 3 metrics:
1. Success Rate (binary)
2. Token Consumption (continuous)
3. Time Taken (continuous)

These are RELATED but NOT identical metrics.
All three measure "efficiency" from different angles.

CORRECTION METHODS:

┌────────────────────┬─────────────┬────────────────┬───────────────────────┐
│      Method        │  α family   │    Power       │     When to Use       │
├────────────────────┼─────────────┼────────────────┼───────────────────────┤
│ Bonferroni         │ α/m = 0.017 │   Lowest       │ Conservative, simple  │
│ Holm-Bonferferroni │   Adaptive  │   Medium       │ RECOMMENDED (uniformly│
│                    │             │                │ more powerful than Bon│
│ Benjamini-Hochberg │     FDR      │   Highest      │ Exploratory, many     │
│                    │   q < 0.05   │                │ comparisons           │
│ None               │   α = 0.05   │   Highest      │ One pre-specified     │
│                    │             │                │ PRIMARY metric only   │
└────────────────────┴─────────────┴────────────────┴───────────────────────┘

IMPLEMENTATION:

def holm_bonferroni(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    '''
    Holm-Bonferroni step-down procedure.
    Returns list of whether each null hypothesis is rejected.
    '''
    n = len(p_values)
    sorted_indices = np.argsort(p_values)
    adjusted = []
    
    for rank, idx in enumerate(sorted_indices):
        adjusted_alpha = alpha / (n - rank)
        adjusted.append(p_values[idx] < adjusted_alpha)
    
    # Re-order back to original order
    result = [False] * n
    for i, idx in enumerate(sorted_indices):
        result[idx] = adjusted[i]
    
    return result

RECOMMENDATION:
1. PRIMARY analysis: Holm-Bonferroni (controls FWER)
2. Report uncorrected p-values alongside
3. Consider success rate as "sanity check" with lower weight
4. If metrics highly correlated: effective number of tests < 3

SPECIAL CASE:
If Token is the PRIMARY metric and others are secondary/sensitivity:
- Apply correction only within the "primary family"
- No correction needed if secondary metrics reported descriptively
"""


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> Tuple[List[float], List[bool]]:
    """
    Holm-Bonferroni step-down procedure for multiple comparisons.
    
    Args:
        p_values: List of uncorrected p-values
        alpha: Family-wise error rate (default 0.05)
    
    Returns:
        Tuple of (rejected_nulls, adjusted_p_values)
    """
    n = len(p_values)
    if n == 0:
        return [], []
    
    # Sort p-values and keep track of original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    
    rejected = []
    adjusted_p = []
    
    for i, p in enumerate(sorted_p):
        # Holm correction: α / (n - i + 1)
        adjusted = min(1.0, p * (n - i))
        adjusted_p.append(adjusted)
        
        # Reject if p < α / (n - i)
        rejected.append(p < alpha / (n - i))
    
    # Map back to original order
    original_rejected = [False] * n
    original_adjusted = [np.nan] * n
    
    for i, idx in enumerate(sorted_indices):
        original_rejected[idx] = rejected[i]
        original_adjusted[idx] = adjusted_p[i]
    
    return original_rejected, original_adjusted


def benjamini_hochberg(p_values: List[float], q: float = 0.05) -> Tuple[List[bool], List[float]]:
    """
    Benjamini-Hochberg FDR controlling procedure.
    
    Controls false discovery rate rather than family-wise error rate.
    More powerful for exploratory analyses.
    
    Args:
        p_values: List of uncorrected p-values
        q: FDR threshold (default 0.05)
    
    Returns:
        Tuple of (rejected_nulls, adjusted_q_values)
    """
    n = len(p_values)
    if n == 0:
        return [], []
    
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    
    rejected = []
    adjusted_q = []
    
    for i, p in enumerate(sorted_p):
        # BH adjustment: p * n / (rank)
        adjusted = min(1.0, p * n / (i + 1))
        adjusted_q.append(adjusted)
        
        # Find largest k where p_(k) <= k/n * q
        threshold = (i + 1) / n * q
        rejected.append(p <= threshold)
    
    # Find the largest index where rejection should happen
    # (find max i where p_(i) <= i/n * q)
    max_reject = 0
    for i, p in enumerate(sorted_p):
        if p <= (i + 1) / n * q:
            max_reject = i + 1
    
    # Update rejection decisions (all up to max_reject are rejected)
    rejected = [i < max_reject for i in range(n)]
    
    # Map back to original order
    original_rejected = [False] * n
    original_adjusted = [np.nan] * n
    
    for i, idx in enumerate(sorted_indices):
        original_rejected[idx] = rejected[i]
        original_adjusted[idx] = adjusted_q[i]
    
    return original_rejected, original_adjusted


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_experiment(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main analysis function taking experiment results JSON.
    
    Expected JSON structure:
    {
        "tasks": [
            {
                "task_id": "task_1",
                "task_type": "treatment" | "control_only",
                "runs": [
                    {
                        "condition": "control" | "treatment",
                        "order": "first" | "second",
                        "success": true | false,
                        "tokens": int,
                        "time_seconds": float,
                        "seed": int (optional)
                    }
                ]
            }
        ]
    }
    
    Returns:
        Dictionary with all statistical test results
    """
    # Extract data
    tasks = results.get("tasks", [])
    
    # Build paired observations
    # Each task should have 2 runs (control and treatment)
    paired_data = []
    
    for task in tasks:
        task_id = task.get("task_id")
        runs = task.get("runs", [])
        
        # Separate by condition
        control_run = None
        treatment_run = None
        
        for run in runs:
            if run.get("condition") == "control":
                control_run = run
            elif run.get("condition") == "treatment":
                treatment_run = run
        
        if control_run and treatment_run:
            paired_data.append({
                "task_id": task_id,
                "task_type": task.get("task_type", "unknown"),
                "order": control_run.get("order", "unknown"),
                "control": control_run,
                "treatment": treatment_run,
                "control_success": control_run.get("success", False),
                "treatment_success": treatment_run.get("success", False),
                "control_tokens": control_run.get("tokens", 0),
                "treatment_tokens": treatment_run.get("tokens", 0),
                "control_time": control_run.get("time_seconds", 0),
                "treatment_time": treatment_run.get("time_seconds", 0),
            })
    
    if len(paired_data) == 0:
        return {"error": "No paired observations found in data"}
    
    # Arrays for analysis
    control_success = np.array([d["control_success"] for d in paired_data], dtype=float)
    treatment_success = np.array([d["treatment_success"] for d in paired_data], dtype=float)
    
    control_tokens = np.array([d["control_tokens"] for d in paired_data])
    treatment_tokens = np.array([d["treatment_tokens"] for d in paired_data])
    
    control_time = np.array([d["control_time"] for d in paired_data])
    treatment_time = np.array([d["treatment_time"] for d in paired_data])
    
    # Calculate relative improvements
    # Token reduction: (control - treatment) / control
    token_reduction = np.where(control_tokens > 0, 
                               (control_tokens - treatment_tokens) / control_tokens * 100,
                               np.nan)
    
    time_reduction = np.where(control_time > 0,
                              (control_time - treatment_time) / control_time * 100,
                              np.nan)
    
    # Run all tests
    results_dict = {
        "n_tasks": len(paired_data),
        "n_pairs": len(paired_data),
        "summary_statistics": {
            "success_control": float(np.mean(control_success)),
            "success_treatment": float(np.mean(treatment_success)),
            "tokens_control_mean": float(np.mean(control_tokens)),
            "tokens_treatment_mean": float(np.mean(treatment_tokens)),
            "time_control_mean": float(np.mean(control_time)),
            "time_treatment_mean": float(np.mean(treatment_time)),
            "token_reduction_mean_pct": float(np.nanmean(token_reduction)),
            "time_reduction_mean_pct": float(np.nanmean(time_reduction)),
        },
        "tests": {}
    }
    
    # 1. Success Rate - McNemar's test
    results_dict["tests"]["success_mcnemar"] = asdict(run_mcnemar_test(
        control_success, treatment_success, "success"
    ))
    
    # 2. Token consumption - Paired t-test
    results_dict["tests"]["tokens_ttest"] = asdict(run_paired_ttest(
        control_tokens, treatment_tokens, "tokens"
    ))
    
    # 3. Token consumption - Wilcoxon
    results_dict["tests"]["tokens_wilcoxon"] = asdict(run_paired_wilcoxon(
        control_tokens, treatment_tokens, "tokens"
    ))
    
    # 4. Time - Paired t-test
    results_dict["tests"]["time_ttest"] = asdict(run_paired_ttest(
        control_time, treatment_time, "time"
    ))
    
    # 5. Time - Wilcoxon
    results_dict["tests"]["time_wilcoxon"] = asdict(run_paired_wilcoxon(
        control_time, treatment_time, "time"
    ))
    
    # 6. Multiple comparisons correction
    p_values = [
        results_dict["tests"]["success_mcnemar"]["p_value"],
        results_dict["tests"]["tokens_wilcoxon"]["p_value"],
        results_dict["tests"]["time_wilcoxon"]["p_value"],
    ]
    
    metric_names = ["success", "tokens", "time"]
    
    if not any(np.isnan(p) for p in p_values):
        holm_rejected, holm_adjusted = holm_bonferroni_correction(p_values)
        fdr_rejected, fdr_adjusted = benjamini_hochberg(p_values)
        
        results_dict["multiple_comparisons"] = {
            "metric_names": metric_names,
            "uncorrected_p_values": p_values,
            "holm_rejected": holm_rejected,
            "holm_adjusted_p": holm_adjusted,
            "fdr_rejected": fdr_rejected,
            "fdr_adjusted_q": fdr_adjusted,
        }
    
    # 7. Bootstrap CI for paired differences
    boot_ci_tokens = bootstrap_paired_diff(control_tokens, treatment_tokens)
    boot_ci_time = bootstrap_paired_diff(control_time, treatment_time)
    
    results_dict["bootstrap_ci"] = {
        "tokens_95ci": {"lower": boot_ci_tokens[0], "upper": boot_ci_tokens[1]},
        "time_95ci": {"lower": boot_ci_time[0], "upper": boot_ci_time[1]},
    }
    
    return results_dict


def format_results(results: Dict[str, Any]) -> str:
    """Format results for human-readable output."""
    if "error" in results:
        return f"ERROR: {results['error']}"
    
    n = results["n_pairs"]
    summary = results["summary_statistics"]
    
    output = []
    output.append("=" * 70)
    output.append("A/B EXPERIMENT ANALYSIS: AI Agent with vs without Reasoning Cache")
    output.append("=" * 70)
    
    output.append(f"\nSample size: {n} paired observations")
    
    # Summary statistics
    output.append("\n" + "-" * 70)
    output.append("SUMMARY STATISTICS")
    output.append("-" * 70)
    output.append(f"Success Rate (Control):   {summary['success_control']*100:.1f}%")
    output.append(f"Success Rate (Treatment):  {summary['success_treatment']*100:.1f}%")
    output.append(f"Token Mean (Control):      {summary['tokens_control_mean']:.0f}")
    output.append(f"Token Mean (Treatment):    {summary['tokens_treatment_mean']:.0f}")
    output.append(f"Token Reduction:           {summary['token_reduction_mean_pct']:.1f}%")
    output.append(f"Time Mean (Control):       {summary['time_control_mean']:.1f}s")
    output.append(f"Time Mean (Treatment):     {summary['time_treatment_mean']:.1f}s")
    output.append(f"Time Reduction:            {summary['time_reduction_mean_pct']:.1f}%")
    
    # Test results
    output.append("\n" + "-" * 70)
    output.append("STATISTICAL TESTS")
    output.append("-" * 70)
    
    tests = results["tests"]
    
    # Success
    s = tests["success_mcnemar"]
    output.append(f"\n1. SUCCESS RATE (McNemar's test)")
    output.append(f"   Odds Ratio: {s['effect_size']:.2f}")
    output.append(f"   p-value: {s['p_value']:.4f}" if not np.isnan(s['p_value']) else "   p-value: N/A")
    output.append(f"   Conclusion: {s['conclusion']}")
    
    # Tokens
    t = tests["tokens_wilcoxon"]
    output.append(f"\n2. TOKEN CONSUMPTION (Wilcoxon signed-rank)")
    output.append(f"   Effect size (r): {t['effect_size']:.3f}" if not np.isnan(t['effect_size']) else "   Effect size: N/A")
    output.append(f"   p-value: {t['p_value']:.4f}" if not np.isnan(t['p_value']) else "   p-value: N/A")
    output.append(f"   Conclusion: {t['conclusion']}")
    
    ci = results["bootstrap_ci"]["tokens_95ci"]
    output.append(f"   Bootstrap 95% CI: [{ci['lower']:.0f}, {ci['upper']:.0f}] tokens")
    
    # Time
    t = tests["time_wilcoxon"]
    output.append(f"\n3. TIME TAKEN (Wilcoxon signed-rank)")
    output.append(f"   Effect size (r): {t['effect_size']:.3f}" if not np.isnan(t['effect_size']) else "   Effect size: N/A")
    output.append(f"   p-value: {t['p_value']:.4f}" if not np.isnan(t['p_value']) else "   p-value: N/A")
    output.append(f"   Conclusion: {t['conclusion']}")
    
    ci = results["bootstrap_ci"]["time_95ci"]
    output.append(f"   Bootstrap 95% CI: [{ci['lower']:.1f}, {ci['upper']:.1f}] seconds")
    
    # Multiple comparisons
    if "multiple_comparisons" in results:
        output.append("\n" + "-" * 70)
        output.append("MULTIPLE COMPARISONS CORRECTION (3 metrics)")
        output.append("-" * 70)
        
        mc = results["multiple_comparisons"]
        output.append("\nHolm-Bonferroni (FWER control):")
        for name, p_raw, p_adj, rej in zip(
            mc["metric_names"], 
            mc["uncorrected_p_values"],
            mc["holm_adjusted_p"],
            mc["holm_rejected"]
        ):
            status = "REJECTED" if rej else "not rejected"
            output.append(f"  {name}: p={p_raw:.4f} → p_adj={p_adj:.4f} [{status}]")
        
        output.append("\nBenjamini-Hochberg (FDR control):")
        for name, p_raw, q_adj, rej in zip(
            mc["metric_names"],
            mc["uncorrected_p_values"],
            mc["fdr_adjusted_q"],
            mc["fdr_rejected"]
        ):
            status = "REJECTED" if rej else "not rejected"
            output.append(f"  {name}: p={p_raw:.4f} → q_adj={q_adj:.4f} [{status}]")
    
    output.append("\n" + "=" * 70)
    
    return "\n".join(output)


def generate_framework_report() -> str:
    """Generate the complete statistical framework report."""
    
    # Calculate power analysis
    power_result = analyze_sample_size()
    
    # Get MDE
    mde = calculate_mde(n_pairs=25)
    
    report = f"""
================================================================================
STATISTICAL FRAMEWORK FOR A/B EXPERIMENT
AI Agent Performance with vs without Reasoning Cache Tool (Borg)
================================================================================

CONTEXT:
- 25 tasks (20 where tool should help, 5 control)
- Each task run twice: with and without tool (paired design)
- High variance in AI agent performance (same task: 5-30 min)
- Metrics: success (binary), tokens (continuous), time (continuous)
- Budget: ~100 total runs (50 paired observations max)

================================================================================
QUESTION 1: SAMPLE SIZE & STATISTICAL POWER
================================================================================

Target: Detect 30% improvement with 80% power at α=0.05

{power_result.summary()}

KEY INSIGHT: With 100 runs maximum, you can run 50 paired observations.
This gives you ~{power_result.actual_power:.0%} power to detect a 30% improvement
(if the effect size is Cohen's d ≈ 0.5).

If variance is higher than assumed (CV > 75%), effective power drops.
If you run only 25 pairs (50 runs), power drops to ~55-60%.

================================================================================
QUESTION 2: PAIRED vs INDEPENDENT DESIGN
================================================================================

{get_design_recommendation()}

================================================================================
QUESTION 3: PRIMARY METRIC SELECTION
================================================================================

{get_metric_recommendation()}

Power comparison at n=25 pairs:
┌──────────────────┬──────────┬────────────────┬───────────────────────────┐
│     Metric       │   Type   │  Effect Size   │  Power (n=25)            │
├──────────────────┼──────────┼────────────────┼───────────────────────────┤
│ Success Rate     │ Binary   │ OR ≈ 1.5-2.0   │ ~45-55% (LOW)            │
│ Token Reduction  │ Contin.  │ d ≈ 0.4-0.5    │ ~60-70% (HIGH) ✓         │
│ Time Reduction   │ Contin.  │ d ≈ 0.4-0.5    │ ~60-70% (HIGH) ✓         │
└──────────────────┴──────────┴────────────────┴───────────────────────────┘

RECOMMENDATION: Primary = Token Reduction, Secondary = Time, Tertiary = Success

================================================================================
QUESTION 4: RANDOMIZATION STRATEGY
================================================================================

{get_randomization_strategy()}

================================================================================
QUESTION 5: ANALYSIS PLAN
================================================================================

STATISTICAL TESTS TO USE:

1. SUCCESS RATE → McNemar's test (paired binary comparison)
   - Tests if discordant pairs (success in one, fail in other) are balanced
   - Produces odds ratio and confidence interval
   
2. TOKEN/TIME → Wilcoxon signed-rank test (non-parametric, paired)
   - More robust to outliers than paired t-test
   - Uses ranks of differences, not raw values
   
3. TOKEN/TIME → Paired t-test (parametric, for sensitivity analysis)
   - Assumes normal distribution of differences
   - Use as confirmation if Wilcoxon is significant

4. CONFIDENCE INTERVALS → Bootstrap (percentile method)
   - Non-parametric CI for paired differences
   - 95% CI reported alongside p-values

PYTHON IMPLEMENTATION:
See analyze_experiment() function in this script.

================================================================================
QUESTION 6: MINIMUM DETECTABLE EFFECT
================================================================================

{get_mde_analysis()}

WITH 25 PAIRED OBSERVATIONS:
- Standardized effect (Cohen's d): ~0.56
- Token/Time: Can detect ~45-50% reductions
- Success rate: Can detect ~20-25 percentage point improvements

WITH 50 PAIRED OBSERVATIONS (full budget):
- Standardized effect (Cohen's d): ~0.40
- Token/Time: Can detect ~30-35% reductions  
- Success rate: Can detect ~15-20 percentage point improvements

YOUR 30% TARGET:
- Is detectable with 50 pairs (full budget)
- Is borderline with 25 pairs (depends on variance)

================================================================================
QUESTION 7: MULTIPLE COMPARISONS CORRECTION
================================================================================

{get_multiple_comparisons_correction()}

IMPLEMENTATION:
- Holm-Bonferroni for primary analysis (controls FWER at 5%)
- Report both raw and adjusted p-values
- Consider FDR (Benjamini-Hochberg) for exploratory findings

================================================================================
SUMMARY & RECOMMENDATIONS
================================================================================

DESIGN:
✓ Paired (within-subject) design - same task both conditions
✓ Counterbalance order (50% control-first, 50% treatment-first)
✓ Randomize task order in experiment queue
✓ Record order for each run for covariate analysis

ANALYSIS:
1. Primary: Token consumption (Wilcoxon + bootstrap CI)
2. Secondary: Time taken (Wilcoxon + bootstrap CI)
3. Tertiary: Success rate (McNemar's test)
4. Correction: Holm-Bonferroni for multiple comparisons

POWER:
- With 25 pairs: ~55-60% power for 30% effect
- With 50 pairs: ~75-80% power for 30% effect
- If possible, run full 50 pairs (100 runs)

INTERPRETATION:
- Focus on TOKEN reduction as primary (most directly measures cost)
- Time reduction is secondary (affects user experience)
- Success rate is a floor check (shouldn't decrease)
- Report effect sizes alongside p-values

================================================================================
"""
    return report


# =============================================================================
# CLI INTERFACE
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze A/B experiment results for AI agent with/without reasoning cache"
    )
    parser.add_argument(
        "results_file",
        nargs="?",
        type=Path,
        help="Path to JSON results file (optional: omit to just get framework)"
    )
    parser.add_argument(
        "--framework-only",
        action="store_true",
        help="Only print the statistical framework, don't analyze data"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save output to file"
    )
    
    args = parser.parse_args()
    
    # Generate and print framework report
    framework = generate_framework_report()
    
    if args.framework_only or args.results_file is None:
        print(framework)
        if args.output:
            args.output.write_text(framework)
        return
    
    # Load and analyze results
    try:
        with open(args.results_file) as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error loading results file: {e}")
        print("\nGenerating framework report instead...\n")
        print(framework)
        return
    
    # Run analysis
    analysis = analyze_experiment(results)
    formatted = format_results(analysis)
    
    # Combine with framework
    full_output = framework + "\n\n" + "=" * 70 + "\n"
    full_output += "EXPERIMENT RESULTS\n"
    full_output += "=" * 70 + "\n"
    full_output += formatted
    
    print(full_output)
    
    if args.output:
        args.output.write_text(full_output)


if __name__ == "__main__":
    main()
