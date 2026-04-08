#!/usr/bin/env python3
"""Phase 2 A/B Experiment - Analysis

Loads results JSON, computes McNemar's exact test for paired binary outcomes,
reports effect size with confidence intervals, secondary analyses,
and generates summary table.
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESULTS_PATH = Path(__file__).parent / "phase2_results.json"


# ---------------------------------------------------------------------------
# Statistical helpers (no scipy dependency required)
# ---------------------------------------------------------------------------

def binomial_cdf(k: int, n: int, p: float = 0.5) -> float:
    """Exact binomial CDF: P(X <= k) for X ~ Binomial(n, p)."""
    if n == 0:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        # nCi * p^i * (1-p)^(n-i)
        coeff = math.comb(n, i)
        total += coeff * (p ** i) * ((1 - p) ** (n - i))
    return total


def mcnemar_exact_test(b: int, c: int) -> float:
    """McNemar's exact test (two-sided).
    
    b = count of (A=FAIL, B=PASS) - discordant, B better
    c = count of (A=PASS, B=FAIL) - discordant, A better
    
    Under H0: b ~ Binomial(b+c, 0.5)
    Two-sided p-value.
    """
    n = b + c
    if n == 0:
        return 1.0
    
    # Two-sided: 2 * min(P(X <= min(b,c)), P(X >= max(b,c)))
    # Equivalently: 2 * P(X <= min(b,c)) for symmetric binomial
    k = min(b, c)
    p_value = 2.0 * binomial_cdf(k, n, 0.5)
    return min(p_value, 1.0)


def mcnemar_chi2(b: int, c: int) -> tuple:
    """McNemar's chi-squared test (with continuity correction).
    Returns (chi2_stat, approx_p_value).
    """
    n = b + c
    if n == 0:
        return 0.0, 1.0
    
    chi2 = ((abs(b - c) - 1) ** 2) / n if n > 0 else 0
    # Approximate p-value using normal approximation
    # For chi2 with 1 df, p = 2 * (1 - Phi(sqrt(chi2)))
    z = math.sqrt(chi2) if chi2 > 0 else 0
    # Simple normal CDF approximation
    p_approx = 2 * (1 - _norm_cdf(z))
    return chi2, p_approx


def _norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple:
    """Wilson score confidence interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))
    return (max(0, center - margin), min(1, center + margin))


def effect_size_odds_ratio(b: int, c: int) -> tuple:
    """Odds ratio for discordant pairs and its 95% CI.
    OR = b/c (B better / A better)
    """
    if c == 0:
        or_val = float('inf') if b > 0 else 1.0
        return or_val, (None, None)
    
    or_val = b / c
    
    # Log OR CI: ln(OR) +/- 1.96 * sqrt(1/b + 1/c)
    if b > 0 and c > 0:
        ln_or = math.log(or_val)
        se = math.sqrt(1/b + 1/c)
        ci_low = math.exp(ln_or - 1.96 * se)
        ci_high = math.exp(ln_or + 1.96 * se)
        return or_val, (ci_low, ci_high)
    
    return or_val, (None, None)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def load_results(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_paired_table(trials: list) -> dict:
    """Build paired outcome table from trials.
    
    Returns dict with:
    - pairs: list of (task_id, outcome_A, outcome_B)
    - a, b, c, d counts for McNemar's 2x2 table
      a = both PASS, b = A FAIL & B PASS, c = A PASS & B FAIL, d = both FAIL
    """
    # Group by task_id
    by_task = defaultdict(dict)
    for trial in trials:
        tid = trial["task_id"]
        cond = trial["condition"]
        by_task[tid][cond] = trial["outcome"]
    
    pairs = []
    a = b = c = d = 0
    
    for tid, outcomes in sorted(by_task.items()):
        if "A" in outcomes and "B" in outcomes:
            oa = outcomes["A"]
            ob = outcomes["B"]
            pairs.append((tid, oa, ob))
            
            pa = (oa == "PASS")
            pb = (ob == "PASS")
            
            if pa and pb:
                a += 1
            elif not pa and pb:
                b += 1  # B better
            elif pa and not pb:
                c += 1  # A better
            else:
                d += 1
    
    return {"pairs": pairs, "a": a, "b": b, "c": c, "d": d}


def analyze(results: dict) -> str:
    """Run full analysis and return formatted report."""
    trials = results.get("trials", [])
    
    if not trials:
        return "No trials found in results."
    
    lines = []
    lines.append("=" * 70)
    lines.append("PHASE 2 A/B EXPERIMENT ANALYSIS")
    lines.append("Borg Memory Tools Effectiveness Study")
    lines.append("=" * 70)
    lines.append("")
    
    # Overview
    n_trials = len(trials)
    task_ids = set(t["task_id"] for t in trials)
    lines.append(f"Total trials: {n_trials}")
    lines.append(f"Unique tasks: {len(task_ids)}")
    lines.append(f"Condition A trials: {sum(1 for t in trials if t['condition'] == 'A')}")
    lines.append(f"Condition B trials: {sum(1 for t in trials if t['condition'] == 'B')}")
    lines.append("")
    
    # Build paired table
    table = build_paired_table(trials)
    pairs = table["pairs"]
    a, b, c, d = table["a"], table["b"], table["c"], table["d"]
    n_paired = len(pairs)
    
    lines.append(f"Paired observations: {n_paired}")
    lines.append("")
    
    # 2x2 table
    lines.append("McNemar's 2x2 Table (Condition A vs B):")
    lines.append("-" * 40)
    lines.append(f"                    B=PASS    B=FAIL")
    lines.append(f"  A=PASS            {a:5d}     {c:5d}     | {a+c}")
    lines.append(f"  A=FAIL            {b:5d}     {d:5d}     | {b+d}")
    lines.append(f"                    -----     -----")
    lines.append(f"                    {a+b:5d}     {c+d:5d}     | {n_paired}")
    lines.append("")
    
    # Pass rates
    pass_a = a + c
    pass_b = a + b
    rate_a = pass_a / n_paired if n_paired > 0 else 0
    rate_b = pass_b / n_paired if n_paired > 0 else 0
    ci_a = wilson_ci(pass_a, n_paired)
    ci_b = wilson_ci(pass_b, n_paired)
    
    lines.append("Pass Rates:")
    lines.append(f"  Condition A (baseline): {pass_a}/{n_paired} = {rate_a:.1%}  95% CI [{ci_a[0]:.1%}, {ci_a[1]:.1%}]")
    lines.append(f"  Condition B (+ Borg):   {pass_b}/{n_paired} = {rate_b:.1%}  95% CI [{ci_b[0]:.1%}, {ci_b[1]:.1%}]")
    lines.append(f"  Difference (B - A):     {rate_b - rate_a:+.1%}")
    lines.append("")
    
    # McNemar's test
    lines.append("McNemar's Exact Test:")
    lines.append(f"  Discordant pairs: {b + c}")
    lines.append(f"    B better (A=FAIL, B=PASS): {b}")
    lines.append(f"    A better (A=PASS, B=FAIL): {c}")
    
    p_exact = mcnemar_exact_test(b, c)
    chi2, p_chi2 = mcnemar_chi2(b, c)
    
    lines.append(f"  Exact p-value: {p_exact:.4f}")
    lines.append(f"  Chi-squared (continuity corrected): {chi2:.3f}, p = {p_chi2:.4f}")
    
    sig = "YES" if p_exact < 0.05 else "NO"
    lines.append(f"  Significant at alpha=0.05: {sig}")
    lines.append("")
    
    # Effect size
    or_val, or_ci = effect_size_odds_ratio(b, c)
    lines.append("Effect Size:")
    lines.append(f"  Odds Ratio (B better / A better): {or_val:.2f}" if or_val != float('inf') else f"  Odds Ratio: inf (c=0)")
    if or_ci[0] is not None:
        lines.append(f"  95% CI: [{or_ci[0]:.2f}, {or_ci[1]:.2f}]")
    lines.append("")
    
    # Secondary analyses
    lines.append("-" * 70)
    lines.append("SECONDARY ANALYSES")
    lines.append("-" * 70)
    lines.append("")
    
    # Duration comparison
    dur_a = [t["duration_seconds"] for t in trials if t["condition"] == "A" and t.get("duration_seconds")]
    dur_b = [t["duration_seconds"] for t in trials if t["condition"] == "B" and t.get("duration_seconds")]
    
    if dur_a and dur_b:
        mean_a = sum(dur_a) / len(dur_a)
        mean_b = sum(dur_b) / len(dur_b)
        lines.append("Duration (seconds):")
        lines.append(f"  Condition A: mean={mean_a:.1f}, median={sorted(dur_a)[len(dur_a)//2]:.1f}, n={len(dur_a)}")
        lines.append(f"  Condition B: mean={mean_b:.1f}, median={sorted(dur_b)[len(dur_b)//2]:.1f}, n={len(dur_b)}")
        lines.append(f"  Difference: {mean_b - mean_a:+.1f}s ({(mean_b - mean_a) / mean_a * 100:+.1f}%)" if mean_a > 0 else "")
        lines.append("")
    
    # Tool usage
    edits_a = [t.get("num_edits", 0) or 0 for t in trials if t["condition"] == "A"]
    edits_b = [t.get("num_edits", 0) or 0 for t in trials if t["condition"] == "B"]
    
    if edits_a and edits_b:
        lines.append("Edit Count:")
        lines.append(f"  Condition A: mean={sum(edits_a)/len(edits_a):.1f}")
        lines.append(f"  Condition B: mean={sum(edits_b)/len(edits_b):.1f}")
        lines.append("")
    
    borg_q = [t.get("borg_queries", 0) or 0 for t in trials if t["condition"] == "B"]
    if borg_q:
        lines.append(f"Borg Queries (Condition B): mean={sum(borg_q)/len(borg_q):.1f}, total={sum(borg_q)}")
        lines.append("")
    
    # By difficulty
    lines.append("By Difficulty (if available in manifest):")
    try:
        manifest = json.load(open(Path(__file__).parent / "phase2_task_manifest.json"))
        diff_map = {t["instance_id"]: t.get("difficulty", "unknown") for t in manifest["tasks"]}
        
        for diff in ["easy", "medium", "hard"]:
            diff_tasks = {tid for tid, d in diff_map.items() if d == diff}
            diff_pairs = [(tid, oa, ob) for tid, oa, ob in pairs if tid in diff_tasks]
            if diff_pairs:
                dp = sum(1 for _, oa, ob in diff_pairs if oa == "PASS")
                bp = sum(1 for _, oa, ob in diff_pairs if ob == "PASS")
                lines.append(f"  {diff}: n={len(diff_pairs)}, A pass={dp}, B pass={bp}")
    except Exception:
        lines.append("  (manifest not available)")
    lines.append("")
    
    # By repo
    lines.append("By Repository:")
    repo_pairs = defaultdict(list)
    for tid, oa, ob in pairs:
        repo = tid.rsplit("-", 1)[0]
        repo_pairs[repo].append((oa, ob))
    
    for repo in sorted(repo_pairs.keys()):
        rp = repo_pairs[repo]
        ap = sum(1 for oa, _ in rp if oa == "PASS")
        bp = sum(1 for _, ob in rp if ob == "PASS")
        lines.append(f"  {repo}: n={len(rp)}, A pass={ap}/{len(rp)}, B pass={bp}/{len(rp)}")
    lines.append("")
    
    # Per-task detail table
    lines.append("-" * 70)
    lines.append("PER-TASK RESULTS")
    lines.append("-" * 70)
    lines.append(f"{'Task ID':<45} {'A':>6} {'B':>6} {'Delta':>6}")
    lines.append("-" * 70)
    
    for tid, oa, ob in pairs:
        delta = ""
        if oa != ob:
            delta = "B>A" if ob == "PASS" else "A>B"
        lines.append(f"{tid:<45} {oa:>6} {ob:>6} {delta:>6}")
    
    lines.append("-" * 70)
    lines.append("")
    
    # Order effects
    lines.append("Order Effects:")
    try:
        manifest = json.load(open(Path(__file__).parent / "phase2_task_manifest.json"))
        order_map = {t["instance_id"]: t.get("run_order", ["A", "B"]) for t in manifest["tasks"]}
        
        a_first = [(tid, oa, ob) for tid, oa, ob in pairs if order_map.get(tid, ["A"])[0] == "A"]
        b_first = [(tid, oa, ob) for tid, oa, ob in pairs if order_map.get(tid, ["A"])[0] == "B"]
        
        if a_first:
            ab = sum(1 for _, oa, ob in a_first if ob == "PASS" and oa != "PASS")
            lines.append(f"  A-first tasks: n={len(a_first)}, B advantage={ab}")
        if b_first:
            bb = sum(1 for _, oa, ob in b_first if ob == "PASS" and oa != "PASS")
            lines.append(f"  B-first tasks: n={len(b_first)}, B advantage={bb}")
    except Exception:
        lines.append("  (order data not available)")
    
    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF ANALYSIS")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze Phase 2 A/B experiment results")
    parser.add_argument("--results", type=str, default=str(RESULTS_PATH), help="Results JSON path")
    parser.add_argument("--output", type=str, help="Write report to file (otherwise stdout)")
    args = parser.parse_args()

    results = load_results(args.results)
    report = analyze(results)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
