#!/usr/bin/env python3
"""Phase B Analysis — Borg 3-Condition Experiment.

Loads phase_b_results.jsonl and produces:
  1. Majority-vote binary outcomes (3 runs → 1 per task×condition)
  2. Cochran's Q omnibus test
  3. Pairwise McNemar's tests with Holm correction
  4. Odds ratios with 95% CIs
  5. Supplementary GLMM on raw (un-aggregated) runs
  6. Summary table + LaTeX-ready output

Usage:
    python phase_b_analyze.py                          # default file
    python phase_b_analyze.py --results custom.jsonl
    python phase_b_analyze.py --latex                   # include LaTeX output
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS = SCRIPT_DIR / "phase_b_results.jsonl"
CONDITIONS = ["C0", "C1", "C2"]
CONDITION_LABELS = {"C0": "Baseline", "C1": "Borg (fresh)", "C2": "Borg (seeded)"}
RUNS_PER_CELL = 3


def load_results(path: Path) -> list[dict]:
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def majority_vote(outcomes: list[int]) -> int:
    """Majority vote: 1 if >50% of runs succeeded."""
    if not outcomes:
        return 0
    return 1 if sum(outcomes) > len(outcomes) / 2 else 0


def build_matrices(results: list[dict]):
    """Build per-task outcome matrices.

    Returns:
        tasks: sorted list of instance_ids
        raw: dict[condition][instance_id] -> list of outcomes (per run)
        voted: dict[condition][instance_id] -> 0 or 1 (majority vote)
    """
    raw = defaultdict(lambda: defaultdict(list))
    for r in results:
        iid = r["instance_id"]
        cond = r["condition"]
        outcome = r.get("outcome", 0)
        if outcome is None:
            continue
        raw[cond][iid].append(outcome)

    # Get task list (union across conditions)
    all_tasks = set()
    for cond in raw:
        all_tasks.update(raw[cond].keys())
    tasks = sorted(all_tasks)

    voted = {}
    for cond in CONDITIONS:
        voted[cond] = {}
        for t in tasks:
            runs = raw[cond].get(t, [])
            voted[cond][t] = majority_vote(runs)

    return tasks, raw, voted


# ---------------------------------------------------------------------------
# Cochran's Q test
# ---------------------------------------------------------------------------

def cochrans_q(voted: dict, tasks: list[str], conditions: list[str] = CONDITIONS):
    """Cochran's Q test for k related dichotomous samples.

    H0: all conditions have the same proportion of successes.
    """
    from scipy.stats import chi2

    k = len(conditions)
    n = len(tasks)

    # Build matrix: n × k
    X = np.zeros((n, k), dtype=int)
    for i, t in enumerate(tasks):
        for j, c in enumerate(conditions):
            X[i, j] = voted[c].get(t, 0)

    T_j = X.sum(axis=0)  # column sums (successes per condition)
    T_i = X.sum(axis=1)  # row sums (successes per task)
    N = X.sum()

    num = (k - 1) * (k * (T_j ** 2).sum() - N ** 2)
    den = k * N - (T_i ** 2).sum()

    if den == 0:
        return {"Q": 0.0, "df": k - 1, "p": 1.0, "note": "Degenerate (all same)"}

    Q = num / den
    df = k - 1
    p = 1.0 - chi2.cdf(Q, df)

    return {"Q": round(Q, 4), "df": df, "p": round(p, 6)}


# ---------------------------------------------------------------------------
# McNemar's test (pairwise)
# ---------------------------------------------------------------------------

def mcnemar_test(voted: dict, tasks: list[str], cond_a: str, cond_b: str):
    """McNemar's test comparing two conditions on matched binary outcomes.

    Returns dict with statistic, p-value, and contingency counts.
    """
    from scipy.stats import binom

    # b = cond_a=0, cond_b=1 (b improved over a)
    # c = cond_a=1, cond_b=0 (a better than b)
    b = 0  # discordant: A=0, B=1
    c = 0  # discordant: A=1, B=0
    a_count = 0  # concordant: both=1
    d_count = 0  # concordant: both=0

    for t in tasks:
        va = voted[cond_a].get(t, 0)
        vb = voted[cond_b].get(t, 0)
        if va == 0 and vb == 1:
            b += 1
        elif va == 1 and vb == 0:
            c += 1
        elif va == 1 and vb == 1:
            a_count += 1
        else:
            d_count += 1

    n_discord = b + c

    if n_discord == 0:
        p_value = 1.0
        statistic = 0.0
    elif n_discord < 25:
        # Exact binomial test (small sample)
        p_value = 2.0 * binom.cdf(min(b, c), n_discord, 0.5)
        p_value = min(p_value, 1.0)
        statistic = float(min(b, c))
    else:
        # Chi-squared approximation with continuity correction
        statistic = (abs(b - c) - 1) ** 2 / (b + c)
        from scipy.stats import chi2
        p_value = 1.0 - chi2.cdf(statistic, 1)

    return {
        "comparison": f"{cond_a} vs {cond_b}",
        "b_discord": b,
        "c_discord": c,
        "concordant_11": a_count,
        "concordant_00": d_count,
        "statistic": round(statistic, 4),
        "p_raw": round(p_value, 6),
    }


def holm_correction(pvalues: list[float]) -> list[float]:
    """Holm-Bonferroni step-down correction for multiple comparisons."""
    m = len(pvalues)
    indexed = sorted(enumerate(pvalues), key=lambda x: x[1])
    corrected = [0.0] * m

    cummax = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adjusted = p * (m - rank)
        adjusted = max(adjusted, cummax)  # enforce monotonicity
        adjusted = min(adjusted, 1.0)
        corrected[orig_idx] = adjusted
        cummax = adjusted

    return corrected


# ---------------------------------------------------------------------------
# Odds ratios + CIs
# ---------------------------------------------------------------------------

def odds_ratio_ci(voted: dict, tasks: list[str], cond_a: str, cond_b: str,
                  alpha: float = 0.05):
    """Compute odds ratio and 95% CI for cond_b vs cond_a (matched pairs).

    Uses the discordant pairs: OR = b/c where b = A fail & B pass, c = A pass & B fail.
    CI via exact method on the conditional binomial.
    """
    from scipy.stats import norm

    b = 0  # A=0, B=1
    c = 0  # A=1, B=0

    for t in tasks:
        va = voted[cond_a].get(t, 0)
        vb = voted[cond_b].get(t, 0)
        if va == 0 and vb == 1:
            b += 1
        elif va == 1 and vb == 0:
            c += 1

    # Add 0.5 correction to avoid division by zero
    b_adj = b + 0.5
    c_adj = c + 0.5

    OR = b_adj / c_adj
    log_OR = math.log(OR)
    se_log_OR = math.sqrt(1.0 / b_adj + 1.0 / c_adj)

    z = norm.ppf(1 - alpha / 2)
    ci_low = math.exp(log_OR - z * se_log_OR)
    ci_high = math.exp(log_OR + z * se_log_OR)

    return {
        "comparison": f"{cond_b} vs {cond_a}",
        "OR": round(OR, 3),
        "CI_95": (round(ci_low, 3), round(ci_high, 3)),
        "log_OR": round(log_OR, 4),
        "SE_log_OR": round(se_log_OR, 4),
        "b_discord": b,
        "c_discord": c,
    }


# ---------------------------------------------------------------------------
# GLMM on raw runs (supplementary)
# ---------------------------------------------------------------------------

def run_glmm(results: list[dict], tasks: list[str]):
    """Run a generalized linear mixed model on raw (un-aggregated) runs.

    Model: outcome ~ condition + (1|task) + (1|run)
    Uses statsmodels if available; falls back to simple logistic regression.
    """
    try:
        import statsmodels.api as sm
        from statsmodels.genmod.generalized_estimating_equations import GEE
        from statsmodels.genmod.families import Binomial
        from statsmodels.genmod.cov_struct import Exchangeable
    except ImportError:
        return _glmm_fallback(results, tasks)

    # Build dataframe-like arrays
    outcomes = []
    cond_c1 = []  # dummy for C1
    cond_c2 = []  # dummy for C2
    task_ids = []
    run_ids = []

    task_map = {t: i for i, t in enumerate(tasks)}

    for r in results:
        if r.get("outcome") is None or r.get("dry_run"):
            continue
        iid = r["instance_id"]
        if iid not in task_map:
            continue
        outcomes.append(r["outcome"])
        cond_c1.append(1 if r["condition"] == "C1" else 0)
        cond_c2.append(1 if r["condition"] == "C2" else 0)
        task_ids.append(task_map[iid])
        run_ids.append(r.get("run_idx", 0))

    if len(outcomes) < 10:
        return {"note": "Too few observations for GLMM", "n": len(outcomes)}

    outcomes = np.array(outcomes)
    X = np.column_stack([
        np.ones(len(outcomes)),  # intercept
        np.array(cond_c1),
        np.array(cond_c2),
    ])
    groups = np.array(task_ids)

    try:
        model = GEE(
            outcomes, X, groups,
            family=Binomial(),
            cov_struct=Exchangeable(),
        )
        fit = model.fit()

        return {
            "method": "GEE (Exchangeable, Binomial)",
            "n_obs": len(outcomes),
            "params": {
                "intercept": round(float(fit.params[0]), 4),
                "C1_effect": round(float(fit.params[1]), 4),
                "C2_effect": round(float(fit.params[2]), 4),
            },
            "std_err": {
                "intercept": round(float(fit.bse[0]), 4),
                "C1_effect": round(float(fit.bse[1]), 4),
                "C2_effect": round(float(fit.bse[2]), 4),
            },
            "p_values": {
                "intercept": round(float(fit.pvalues[0]), 6),
                "C1_effect": round(float(fit.pvalues[1]), 6),
                "C2_effect": round(float(fit.pvalues[2]), 6),
            },
            "summary": str(fit.summary()),
        }
    except Exception as e:
        return _glmm_fallback(results, tasks, note=f"GEE failed ({e}), using fallback")


def _glmm_fallback(results: list[dict], tasks: list[str], note: str = ""):
    """Fallback: simple per-condition success rates with Wilson CIs."""
    from scipy.stats import norm

    rates = {}
    for cond in CONDITIONS:
        cond_results = [r for r in results
                        if r["condition"] == cond and r.get("outcome") is not None]
        n = len(cond_results)
        k = sum(1 for r in cond_results if r["outcome"] == 1)
        if n == 0:
            rates[cond] = {"n": 0, "k": 0, "rate": 0, "ci": (0, 0)}
            continue

        p_hat = k / n
        z = 1.96
        denom = 1 + z ** 2 / n
        centre = (p_hat + z ** 2 / (2 * n)) / denom
        spread = z * math.sqrt((p_hat * (1 - p_hat) + z ** 2 / (4 * n)) / n) / denom
        ci_low = max(0, centre - spread)
        ci_high = min(1, centre + spread)

        rates[cond] = {
            "n": n, "k": k,
            "rate": round(p_hat, 4),
            "ci_95": (round(ci_low, 4), round(ci_high, 4)),
        }

    return {
        "method": "Wilson CI fallback (statsmodels not available)",
        "note": note,
        "per_condition": rates,
    }


# ---------------------------------------------------------------------------
# Summary + LaTeX
# ---------------------------------------------------------------------------

def print_summary_table(tasks, voted, raw, results):
    """Print a human-readable summary table."""
    print("\n" + "=" * 78)
    print("PHASE B RESULTS — BORG 3-CONDITION EXPERIMENT")
    print("=" * 78)

    # Per-condition summary
    print(f"\n{'Condition':<20} {'Label':<18} {'Pass':<6} {'Total':<6} {'Rate':<8}")
    print("-" * 58)
    for cond in CONDITIONS:
        n_pass = sum(voted[cond].get(t, 0) for t in tasks)
        n_total = len(tasks)
        rate = n_pass / n_total if n_total > 0 else 0
        label = CONDITION_LABELS[cond]
        print(f"{cond:<20} {label:<18} {n_pass:<6} {n_total:<6} {rate:<8.1%}")

    # Per-task breakdown
    print(f"\n{'Task':<35}", end="")
    for cond in CONDITIONS:
        print(f" {cond:<12}", end="")
    print()
    print("-" * 71)

    for t in tasks:
        print(f"{t:<35}", end="")
        for cond in CONDITIONS:
            runs = raw[cond].get(t, [])
            vote = voted[cond].get(t, 0)
            run_str = "/".join(str(r) for r in runs) if runs else "—"
            vote_str = "✓" if vote else "✗"
            print(f" {vote_str} ({run_str}){'':<4}", end="")
        print()

    # Secondary metrics
    print(f"\n{'Condition':<12} {'Avg Time(s)':<14} {'Avg Tools':<12} {'Avg Files':<12}")
    print("-" * 50)
    for cond in CONDITIONS:
        cond_results = [r for r in results if r["condition"] == cond and not r.get("dry_run")]
        if not cond_results:
            continue
        avg_time = np.mean([r.get("wall_seconds", 0) for r in cond_results])
        avg_tools = np.mean([r.get("tool_calls", 0) for r in cond_results])
        avg_files = np.mean([len(r.get("files_modified", [])) for r in cond_results])
        print(f"{cond:<12} {avg_time:<14.1f} {avg_tools:<12.1f} {avg_files:<12.1f}")


def generate_latex(tasks, voted, q_result, mcnemar_results, or_results, glmm_result):
    """Generate LaTeX-ready tables."""
    lines = []

    # Main results table
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Phase B: Borg 3-Condition Experiment Results}")
    lines.append(r"\label{tab:phase-b-results}")
    lines.append(r"\begin{tabular}{lrrr}")
    lines.append(r"\toprule")
    lines.append(r"Condition & Pass & Total & Rate \\")
    lines.append(r"\midrule")

    for cond in CONDITIONS:
        n_pass = sum(voted[cond].get(t, 0) for t in tasks)
        n_total = len(tasks)
        rate = n_pass / n_total if n_total > 0 else 0
        label = CONDITION_LABELS[cond]
        lines.append(f"{label} ({cond}) & {n_pass} & {n_total} & {rate:.1%} \\\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")
    lines.append("")

    # Cochran's Q
    lines.append(f"% Cochran's Q = {q_result['Q']}, df = {q_result['df']}, "
                  f"p = {q_result['p']}")
    lines.append("")

    # Pairwise tests table
    lines.append(r"\begin{table}[htbp]")
    lines.append(r"\centering")
    lines.append(r"\caption{Pairwise McNemar's Tests with Holm Correction}")
    lines.append(r"\label{tab:phase-b-pairwise}")
    lines.append(r"\begin{tabular}{lrrrrl}")
    lines.append(r"\toprule")
    lines.append(r"Comparison & $b$ & $c$ & Statistic & $p_{\text{adj}}$ & OR [95\% CI] \\")
    lines.append(r"\midrule")

    for mc, orr in zip(mcnemar_results, or_results):
        comp = mc["comparison"]
        b = mc["b_discord"]
        c = mc["c_discord"]
        stat = mc["statistic"]
        p_adj = mc["p_holm"]
        OR = orr["OR"]
        ci = orr["CI_95"]
        sig = "*" if p_adj < 0.05 else ""
        lines.append(
            f"{comp} & {b} & {c} & {stat:.2f} & {p_adj:.4f}{sig} & "
            f"{OR:.2f} [{ci[0]:.2f}, {ci[1]:.2f}] \\\\"
        )

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase B Analysis")
    parser.add_argument("--results", type=str, default=str(DEFAULT_RESULTS),
                        help="Path to results JSONL")
    parser.add_argument("--latex", action="store_true",
                        help="Generate LaTeX output")
    parser.add_argument("--output", type=str, default=None,
                        help="Save analysis report to file")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        sys.exit(1)

    # Install scipy if needed
    try:
        import scipy
    except ImportError:
        import subprocess
        print("Installing scipy...")
        subprocess.run([sys.executable, "-m", "pip", "install", "scipy", "-q"])
        import scipy

    results = load_results(results_path)
    print(f"Loaded {len(results)} trial records from {results_path}")

    # Filter out dry runs
    results = [r for r in results if not r.get("dry_run")]
    print(f"  ({len(results)} actual trials after filtering dry runs)")

    if not results:
        print("No results to analyze!")
        sys.exit(1)

    # Build matrices
    tasks, raw, voted = build_matrices(results)
    print(f"  {len(tasks)} tasks × {len(CONDITIONS)} conditions")

    # Print summary table
    print_summary_table(tasks, voted, raw, results)

    # --- Statistical tests ---
    print("\n" + "=" * 78)
    print("STATISTICAL ANALYSIS")
    print("=" * 78)

    # 1. Cochran's Q
    q_result = cochrans_q(voted, tasks)
    print(f"\n1. Cochran's Q Omnibus Test:")
    print(f"   Q = {q_result['Q']}, df = {q_result['df']}, p = {q_result['p']}")
    if q_result['p'] < 0.05:
        print("   → Significant difference among conditions (p < 0.05)")
    else:
        print("   → No significant difference among conditions")

    # 2. Pairwise McNemar's
    pairs = [("C0", "C1"), ("C0", "C2"), ("C1", "C2")]
    mcnemar_results = []
    for ca, cb in pairs:
        mc = mcnemar_test(voted, tasks, ca, cb)
        mcnemar_results.append(mc)

    # Holm correction
    raw_ps = [mc["p_raw"] for mc in mcnemar_results]
    corrected_ps = holm_correction(raw_ps)
    for mc, p_holm in zip(mcnemar_results, corrected_ps):
        mc["p_holm"] = round(p_holm, 6)

    print(f"\n2. Pairwise McNemar's Tests (Holm-corrected):")
    print(f"   {'Comparison':<15} {'b':<4} {'c':<4} {'Stat':<8} {'p_raw':<10} {'p_holm':<10} {'Sig':<5}")
    print("   " + "-" * 56)
    for mc in mcnemar_results:
        sig = "*" if mc["p_holm"] < 0.05 else ""
        print(f"   {mc['comparison']:<15} {mc['b_discord']:<4} {mc['c_discord']:<4} "
              f"{mc['statistic']:<8.3f} {mc['p_raw']:<10.4f} {mc['p_holm']:<10.4f} {sig}")

    # 3. Odds ratios
    or_results = []
    for ca, cb in pairs:
        orr = odds_ratio_ci(voted, tasks, ca, cb)
        or_results.append(orr)

    print(f"\n3. Odds Ratios (95% CI):")
    print(f"   {'Comparison':<20} {'OR':<8} {'95% CI':<20} {'b':<4} {'c':<4}")
    print("   " + "-" * 56)
    for orr in or_results:
        ci_str = f"[{orr['CI_95'][0]:.2f}, {orr['CI_95'][1]:.2f}]"
        print(f"   {orr['comparison']:<20} {orr['OR']:<8.2f} {ci_str:<20} "
              f"{orr['b_discord']:<4} {orr['c_discord']:<4}")

    # 4. GLMM
    print(f"\n4. Supplementary GLMM (raw runs):")
    glmm_result = run_glmm(results, tasks)
    if "summary" in glmm_result:
        print(f"   Method: {glmm_result['method']}")
        print(f"   N obs: {glmm_result['n_obs']}")
        print(f"   Parameters:")
        for k, v in glmm_result["params"].items():
            se = glmm_result["std_err"][k]
            p = glmm_result["p_values"][k]
            sig = "*" if p < 0.05 else ""
            print(f"     {k:<15} β={v:>7.4f}  SE={se:.4f}  p={p:.4f} {sig}")
    else:
        print(f"   {json.dumps(glmm_result, indent=2)}")

    # 5. LaTeX output
    if args.latex:
        print("\n" + "=" * 78)
        print("LATEX OUTPUT")
        print("=" * 78)
        latex = generate_latex(tasks, voted, q_result, mcnemar_results, or_results, glmm_result)
        print(latex)

    # Save analysis report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat() if hasattr(datetime, 'now') else "unknown",
        "n_tasks": len(tasks),
        "n_trials": len(results),
        "tasks": tasks,
        "per_condition_rates": {
            cond: {
                "pass": sum(voted[cond].get(t, 0) for t in tasks),
                "total": len(tasks),
                "rate": sum(voted[cond].get(t, 0) for t in tasks) / max(len(tasks), 1),
            }
            for cond in CONDITIONS
        },
        "cochrans_q": q_result,
        "mcnemar_pairwise": mcnemar_results,
        "odds_ratios": or_results,
        "glmm": glmm_result,
    }

    report_path = args.output or str(results_path).replace(".jsonl", "_analysis.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nAnalysis report saved to: {report_path}")


if __name__ == "__main__":
    from datetime import datetime, timezone
    main()
