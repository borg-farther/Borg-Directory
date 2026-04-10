#!/usr/bin/env python3.12
"""
Monte Carlo power analysis for Scope 3 Borg SWE-bench experiment.

Models:
  - Phase B: within-subject paired design, N=15 tasks per framework,
            3 conditions (C0/C1/C2), 2 runs/cell.
            Per-framework McNemar's exact test on paired binary outcomes.
  - Phase C: paired transfer test, N=10 task-pairs.
  - Mixed-effects GLMM: pooled cross-framework analysis.

Key questions:
  Q: What is the minimum detectable OR (odds ratio) for McNemar at N=15?
  Q: At what absolute risk difference do we hit 80% power?
  Q: Is N=10 Phase C hopeless?
  Q: Does pooling across frameworks recover power for cross-framework interaction?
"""
import sys
import numpy as np
from scipy import stats


def out(*a):
    print(*a, flush=True)


RNG_SEED = 20260408


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


# -----------------------------------------------------------------------------
# 1. McNemar exact test
# -----------------------------------------------------------------------------
def mcnemar_exact_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(2 * stats.binom.cdf(k, n, 0.5), 1.0)


def mcnemar_exact_one_sided_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return stats.binom.cdf(b, n, 0.5)


# -----------------------------------------------------------------------------
# 2. Calibrate intercept once per (p0, sigma)
# -----------------------------------------------------------------------------
_INTERCEPT_CACHE = {}
def calibrate_intercept(p0, sigma, rng):
    key = (round(p0, 3), round(sigma, 3))
    if key in _INTERCEPT_CACHE:
        return _INTERCEPT_CACHE[key]
    tg = rng.normal(0, sigma, 80000)
    best_inter = 0.0
    best_err = 1e9
    for inter in np.linspace(-3, 3, 1201):
        err = abs(sigmoid(inter + tg).mean() - p0)
        if err < best_err:
            best_err = err
            best_inter = inter
    _INTERCEPT_CACHE[key] = best_inter
    return best_inter


# -----------------------------------------------------------------------------
# 3. Simulate one paired trial (C0 vs C1) and compute McNemar power
# -----------------------------------------------------------------------------
def power_mcnemar(
    n_tasks: int,
    p0_base: float,
    or_b_vs_a: float,
    sigma_task: float = 1.0,
    alpha: float = 0.05,
    n_sim: int = 2000,
    runs_per_cell: int = 2,
    one_sided: bool = False,
    seed: int = 42,
):
    rng = np.random.default_rng(seed)
    intercept = calibrate_intercept(p0_base, sigma_task, rng)
    log_or = np.log(or_b_vs_a)
    rejects = 0
    for _ in range(n_sim):
        thetas = rng.normal(0, sigma_task, n_tasks)
        p0 = sigmoid(intercept + thetas)
        p1 = sigmoid(intercept + thetas + log_or)

        r0 = rng.binomial(1, np.repeat(p0[:, None], runs_per_cell, 1))
        r1 = rng.binomial(1, np.repeat(p1[:, None], runs_per_cell, 1))

        c0 = (r0.sum(1) > 0).astype(int)
        c1 = (r1.sum(1) > 0).astype(int)

        b = int(((c0 == 1) & (c1 == 0)).sum())
        c = int(((c0 == 0) & (c1 == 1)).sum())

        p = mcnemar_exact_one_sided_p(b, c) if one_sided else mcnemar_exact_p(b, c)
        if p < alpha:
            rejects += 1
    return rejects / n_sim


# -----------------------------------------------------------------------------
# 4. Fast pooled GLMM-ish power (clustered logistic via statsmodels, very short n_sim)
# -----------------------------------------------------------------------------
def power_pooled_glmm(
    n_tasks: int,
    n_frameworks: int,
    p0_base: float,
    or_treatment: float,
    sigma_task: float = 1.0,
    alpha: float = 0.05,
    n_sim: int = 200,
    runs_per_cell: int = 2,
    seed: int = 7,
):
    import statsmodels.api as sm
    import pandas as pd

    rng = np.random.default_rng(seed)
    intercept = calibrate_intercept(p0_base, sigma_task, rng)
    log_or = np.log(or_treatment)

    rejects = 0
    for _ in range(n_sim):
        tasks_col, fw_col, cond_col, y_col = [], [], [], []
        for f in range(n_frameworks):
            thetas = rng.normal(0, sigma_task, n_tasks)
            p0 = sigmoid(intercept + thetas)
            p1 = sigmoid(intercept + thetas + log_or)
            for t in range(n_tasks):
                for r in range(runs_per_cell):
                    tasks_col.append(f * 10000 + t)
                    fw_col.append(f)
                    cond_col.append(0)
                    y_col.append(rng.binomial(1, p0[t]))
                    tasks_col.append(f * 10000 + t)
                    fw_col.append(f)
                    cond_col.append(1)
                    y_col.append(rng.binomial(1, p1[t]))
        df = pd.DataFrame({"task": tasks_col, "fw": fw_col, "cond": cond_col, "y": y_col})
        X = sm.add_constant(df[["cond"]].astype(float))
        try:
            mod = sm.GLM(df["y"].values, X.values, family=sm.families.Binomial()).fit(
                cov_type="cluster", cov_kwds={"groups": df["task"].values}
            )
            if mod.pvalues[1] < alpha:
                rejects += 1
        except Exception:
            pass
    return rejects / n_sim


# -----------------------------------------------------------------------------
# 5. Driver
# -----------------------------------------------------------------------------
def main():
    out("=" * 78)
    out("POWER ANALYSIS — SCOPE 3 BORG SWE-BENCH EXPERIMENT")
    out("=" * 78)
    out()
    out("Assumptions:")
    out("  - Baseline C0 marginal success rate: 40% (Sonnet on SWE-bench 1-4h)")
    out("  - Task-level heterogeneity: sigma_task = 1.0 (logit scale, moderate)")
    out("  - Two runs per cell, aggregated as pass@2 (any-pass)")
    out("  - McNemar two-sided exact test (one-sided noted)")
    out()

    # ----- A. Per-framework power at alpha=0.05 uncorrected
    out("-" * 78)
    out("A. Per-framework McNemar power (N=15 tasks, uncorrected alpha=0.05)")
    out("-" * 78)
    out(f"{'OR':>6}  {'approx_risk_diff':>18}  {'power':>7}")
    for or_ in [1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0]:
        p = power_mcnemar(15, 0.40, or_, sigma_task=1.0, alpha=0.05, n_sim=2000)
        p1 = sigmoid(np.log(0.4 / 0.6) + np.log(or_))
        out(f"{or_:>6.2f}  {p1 - 0.4:>18.3f}  {p:>7.3f}")
    out()

    # ----- A'. One-sided power (directional H1)
    out("-" * 78)
    out("A'. Per-framework McNemar ONE-sided power (N=15, alpha=0.05)")
    out("-" * 78)
    out(f"{'OR':>6}  {'power_1s':>9}")
    for or_ in [1.5, 2.0, 3.0, 4.0, 5.0]:
        p = power_mcnemar(15, 0.40, or_, 1.0, 0.05, 2000, one_sided=True)
        out(f"{or_:>6.2f}  {p:>9.3f}")
    out()

    # ----- B. Per-framework power with Holm correction (alpha=0.0025)
    out("-" * 78)
    out("B. Per-framework McNemar power at Holm-corrected alpha=0.0025")
    out("   (family-wise alpha=0.05, family size=20)")
    out("-" * 78)
    out(f"{'OR':>6}  {'power':>7}")
    for or_ in [1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]:
        p = power_mcnemar(15, 0.40, or_, 1.0, 0.0025, n_sim=2000)
        out(f"{or_:>6.2f}  {p:>7.3f}")
    out()

    # ----- C. Sample size sweep at OR=3.0
    out("-" * 78)
    out("C. Sample size curve (OR=3.0, Holm alpha=0.0025)")
    out("-" * 78)
    for n in [10, 15, 20, 25, 30, 40, 50, 75]:
        p = power_mcnemar(n, 0.40, 3.0, 1.0, 0.0025, n_sim=1500)
        out(f"  N={n:>3}  power={p:.3f}")
    out()

    # ----- D. Phase C — N=10 paired transfer
    out("-" * 78)
    out("D. Phase C transfer power (N=10 task-pairs)")
    out("-" * 78)
    out(f"{'OR':>6}  {'pow_a05':>9}  {'pow_Holm':>10}  {'pow_1s05':>10}")
    for or_ in [1.5, 2.0, 3.0, 4.0, 5.0, 7.0]:
        p05 = power_mcnemar(10, 0.40, or_, 1.0, 0.05, 2000)
        pH = power_mcnemar(10, 0.40, or_, 1.0, 0.0025, 2000)
        p1s = power_mcnemar(10, 0.40, or_, 1.0, 0.05, 2000, one_sided=True)
        out(f"{or_:>6.2f}  {p05:>9.3f}  {pH:>10.3f}  {p1s:>10.3f}")
    out()

    # ----- E. Pooled GLMM across 4 frameworks
    out("-" * 78)
    out("E. Pooled 4-framework GLMM power for main condition effect")
    out("   (15 tasks × 4 frameworks × 2 conditions × 2 runs = 240 obs)")
    out("-" * 78)
    out(f"{'OR':>6}  {'power_a05':>10}")
    for or_ in [1.25, 1.5, 2.0, 2.5, 3.0]:
        try:
            p = power_pooled_glmm(15, 4, 0.40, or_, 1.0, 0.05, n_sim=150)
            out(f"{or_:>6.2f}  {p:>10.3f}")
        except Exception as e:
            out(f"{or_:>6.2f}  GLMM failed: {e}")
    out()

    # ----- E'. Pooled GLMM across 3 frameworks (fallback scenario)
    out("-" * 78)
    out("E'. Pooled 3-framework GLMM power (Scope 3 minus OpenClaw fallback)")
    out("    (15 tasks × 3 frameworks × 2 conditions × 2 runs = 180 obs)")
    out("-" * 78)
    out(f"{'OR':>6}  {'power_a05':>10}")
    for or_ in [1.5, 2.0, 3.0]:
        try:
            p = power_pooled_glmm(15, 3, 0.40, or_, 1.0, 0.05, n_sim=150)
            out(f"{or_:>6.2f}  {p:>10.3f}")
        except Exception as e:
            out(f"{or_:>6.2f}  GLMM failed: {e}")
    out()

    # ----- E''. Pooled 4-framework GLMM under Holm-corrected alpha
    out("-" * 78)
    out("E''. Pooled 4-framework GLMM power at Holm alpha=0.0025")
    out("-" * 78)
    out(f"{'OR':>6}  {'power':>7}")
    for or_ in [1.5, 2.0, 2.5, 3.0, 4.0]:
        try:
            p = power_pooled_glmm(15, 4, 0.40, or_, 1.0, 0.0025, n_sim=150)
            out(f"{or_:>6.2f}  {p:>7.3f}")
        except Exception as e:
            out(f"{or_:>6.2f}  GLMM failed: {e}")
    out()

    # ----- E'''. Pooled power at family size=6 (rational primary-test family)
    out("-" * 78)
    out("E'''. Pooled 4-framework GLMM at family size=6 (alpha=0.0083)")
    out("     (6 primary tests: main cond, main fw, interaction,")
    out("      + 3 pre-registered pairwise C0vC1/C1vC2/C0vC2 pooled)")
    out("-" * 78)
    out(f"{'OR':>6}  {'power':>7}")
    for or_ in [1.5, 2.0, 2.5, 3.0, 4.0]:
        try:
            p = power_pooled_glmm(15, 4, 0.40, or_, 1.0, 0.0083, n_sim=150)
            out(f"{or_:>6.2f}  {p:>7.3f}")
        except Exception as e:
            out(f"{or_:>6.2f}  GLMM failed: {e}")
    out()

    # ----- F. Minimum detectable OR at 80% power
    out("-" * 78)
    out("F. Minimum detectable OR at 80% power")
    out("-" * 78)
    for n, alpha, label in [
        (15, 0.05, "N=15 per framework, alpha=0.05 uncorrected"),
        (15, 0.05, "N=15 per framework, alpha=0.05 (one-sided)"),
        (15, 0.0025, "N=15 per framework, alpha=0.0025 Holm-corrected"),
        (10, 0.05, "N=10 Phase C, alpha=0.05 uncorrected"),
        (10, 0.05, "N=10 Phase C, alpha=0.05 (one-sided)"),
        (10, 0.0025, "N=10 Phase C, alpha=0.0025 Holm-corrected"),
    ]:
        one_sided = "one-sided" in label
        lo, hi = 1.0, 50.0
        mde = None
        for _ in range(14):
            mid = (lo + hi) / 2
            p = power_mcnemar(
                n, 0.40, mid, 1.0, alpha, n_sim=800, one_sided=one_sided
            )
            if p < 0.80:
                lo = mid
            else:
                hi = mid
                mde = hi
        mde_str = f"{mde:.2f}" if mde is not None else ">50"
        out(f"  {label}: MDE OR ≈ {mde_str}")
    out()

    # ----- G. Pooled GLMM MDE at 80% power
    out("-" * 78)
    out("G. Pooled GLMM MDE at 80% power (primary analysis)")
    out("-" * 78)
    for n, nf, alpha, label in [
        (15, 4, 0.05, "Scope 3 full (4 frameworks × 15 tasks), alpha=0.05"),
        (15, 4, 0.0083, "Scope 3 full, alpha=0.0083 (family=6)"),
        (15, 3, 0.05, "Scope 3 fallback (3 frameworks × 15 tasks), alpha=0.05"),
        (15, 3, 0.0083, "Scope 3 fallback, alpha=0.0083 (family=6)"),
    ]:
        lo, hi = 1.0, 10.0
        mde = None
        for _ in range(10):
            mid = (lo + hi) / 2
            p = power_pooled_glmm(n, nf, 0.40, mid, 1.0, alpha, n_sim=120)
            if p < 0.80:
                lo = mid
            else:
                hi = mid
                mde = hi
        mde_str = f"{mde:.2f}" if mde is not None else ">10"
        out(f"  {label}: MDE OR ≈ {mde_str}")
    out()
    out("=" * 78)
    out("END POWER ANALYSIS")
    out("=" * 78)


if __name__ == "__main__":
    main()
