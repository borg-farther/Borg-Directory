#!/usr/bin/env python3.12
"""Fit GLMM + descriptive tests on P1 MiniMax JSONL results.

Model: success ~ condition + (1|task), binomial link.
Primary: statsmodels BinomialBayesMixedGLM (variational Bayes)
Backup : GEE with exchangeable working correlation (sandwich SE)
Also computes Cochran's Q and pairwise McNemar for complete cases.
Writes p1_minimax_stats.json next to the JSONL.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

OUTDIR = Path("/root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap")
JSONL = OUTDIR / "p1_minimax_results.jsonl"
STATS = OUTDIR / "p1_minimax_stats.json"

CONDITIONS = ["C0_no_borg", "C1_borg_empty", "C2_borg_seeded"]

def load() -> pd.DataFrame:
    rows = []
    for ln in open(JSONL):
        ln = ln.strip()
        if not ln: continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(rows)
    return df

def per_condition_rates(df: pd.DataFrame) -> dict:
    out = {}
    for c in CONDITIONS:
        sub = df[(df["condition"] == c) & (df["phase"] == "eval")]
        completed = sub[sub["success"].notna()]
        successes = int((completed["success"] == True).sum())  # noqa: E712
        skipped = int(completed.get("skipped", pd.Series([False]*len(completed))).fillna(False).astype(bool).sum())
        n = int(len(completed))
        non_crash = n  # n already excludes crashes (success is None for crashes)
        out[c] = {
            "n": n,
            "skipped": skipped,
            "successes": successes,
            "pass_rate": (successes / n) if n else None,
        }
    return out

def fit_glmm(df: pd.DataFrame) -> dict:
    sub = df[(df["phase"] == "eval") & (df["success"].notna())].copy()
    if len(sub) == 0:
        return {"error": "no eval rows with a success label"}
    sub["y"] = sub["success"].astype(int)
    # dummy encoding for condition (reference = C0)
    for c in CONDITIONS[1:]:
        sub[c] = (sub["condition"] == c).astype(int)

    res = {
        "n_rows": int(len(sub)),
        "n_tasks": int(sub["task_id"].nunique()),
        "overall_pass": int(sub["y"].sum()),
    }

    # ── Primary: BinomialBayesMixedGLM ───────────────────────────────────────
    try:
        import statsmodels.api as sm
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        import patsy
        y = sub["y"].values
        X = sub[[c for c in CONDITIONS[1:]]].values
        X = np.column_stack([np.ones(len(sub)), X])
        # random intercept by task
        task_codes = pd.Categorical(sub["task_id"]).codes
        n_tasks = task_codes.max() + 1
        Z = np.zeros((len(sub), n_tasks))
        for i, t in enumerate(task_codes):
            Z[i, t] = 1.0
        exog_vc = {"task": Z}
        ident = np.array([0] * n_tasks)
        model = BinomialBayesMixedGLM(
            y, X, Z, ident,
            vcp_p=2.0, fe_p=2.0,
        )
        fit = model.fit_vb()
        coefs = fit.fe_mean
        ses = fit.fe_sd
        zvals = coefs / ses
        # 2-sided normal approx p-values (variational Bayes — approximate)
        from scipy.stats import norm
        pvals = 2 * (1 - norm.cdf(np.abs(zvals)))
        names = ["intercept"] + CONDITIONS[1:]
        res["glmm_bayes"] = {}
        for i, nm in enumerate(names):
            ci_lo = coefs[i] - 1.96 * ses[i]
            ci_hi = coefs[i] + 1.96 * ses[i]
            res["glmm_bayes"][nm] = {
                "coef": float(coefs[i]),
                "se": float(ses[i]),
                "z": float(zvals[i]),
                "p": float(pvals[i]),
                "or": float(math.exp(coefs[i])),
                "or_ci_lo": float(math.exp(ci_lo)),
                "or_ci_hi": float(math.exp(ci_hi)),
            }
        res["glmm_backend"] = "BinomialBayesMixedGLM (VB)"
    except Exception as e:
        res["glmm_bayes_error"] = f"{type(e).__name__}: {e}"

    # ── Backup: GEE with logit + exchangeable working correlation ────────────
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        from statsmodels.genmod.cov_struct import Exchangeable
        gee_model = smf.gee(
            "y ~ C(condition, Treatment('C0_no_borg'))",
            "task_id",
            data=sub,
            family=sm.families.Binomial(),
            cov_struct=Exchangeable(),
        )
        gee_fit = gee_model.fit()
        res["gee"] = {}
        ci = gee_fit.conf_int()
        for name, val in gee_fit.params.items():
            se = gee_fit.bse[name]
            p = gee_fit.pvalues[name]
            z = gee_fit.tvalues[name]
            lo, hi = ci.loc[name].values
            res["gee"][name] = {
                "coef": float(val),
                "se": float(se),
                "z": float(z),
                "p": float(p),
                "or": float(math.exp(val)),
                "or_ci_lo": float(math.exp(lo)),
                "or_ci_hi": float(math.exp(hi)),
            }
    except Exception as e:
        res["gee_error"] = f"{type(e).__name__}: {e}"

    # ── Cochran's Q ─────────────────────────────────────────────────────────
    try:
        from statsmodels.stats.contingency_tables import cochrans_q
        wide = sub.pivot_table(index="task_id", columns="condition", values="y", aggfunc="first")
        wide = wide.dropna()
        res["cochrans_q_n_complete_tasks"] = int(len(wide))
        if len(wide) >= 2 and set(CONDITIONS) <= set(wide.columns):
            q = cochrans_q(wide[CONDITIONS].values)
            res["cochrans_q"] = {"stat": float(q.statistic), "df": int(q.df), "p": float(q.pvalue)}
    except Exception as e:
        res["cochrans_q_error"] = f"{type(e).__name__}: {e}"

    # ── pairwise McNemar ────────────────────────────────────────────────────
    try:
        from statsmodels.stats.contingency_tables import mcnemar
        res["mcnemar"] = {}
        for a, b in [("C0_no_borg","C1_borg_empty"), ("C0_no_borg","C2_borg_seeded"), ("C1_borg_empty","C2_borg_seeded")]:
            if a not in wide.columns or b not in wide.columns:
                continue
            tab = [[0,0],[0,0]]
            for _, row in wide.iterrows():
                ai = int(row[a]); bi = int(row[b])
                tab[ai][bi] += 1
            mc = mcnemar(tab, exact=True)
            res["mcnemar"][f"{a}_vs_{b}"] = {
                "table": tab, "stat": float(mc.statistic), "p": float(mc.pvalue),
            }
    except Exception as e:
        res["mcnemar_error"] = f"{type(e).__name__}: {e}"

    return res

def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    """Exact Clopper-Pearson binomial CI. Works for k=0 and k=n edge cases."""
    from scipy.stats import beta
    if n == 0:
        return (None, None)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha/2, k, n-k+1))
    hi = 1.0 if k == n else float(beta.ppf(1-alpha/2, k+1, n-k))
    return (lo, hi)

def _sanitize(obj):
    """Recursively replace NaN/inf with None for JSON-valid output."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

def main():
    df = load()
    print(f"loaded {len(df)} rows from {JSONL}")
    if "phase" not in df.columns:
        df["phase"] = "eval"
    rates = per_condition_rates(df)
    # Add Clopper-Pearson CIs
    for c, v in rates.items():
        lo, hi = clopper_pearson(v["successes"], v["n"])
        v["pass_rate_ci95_lo"] = lo
        v["pass_rate_ci95_hi"] = hi
    print("per-condition:", rates)
    glmm = fit_glmm(df)

    # Degenerate all-zero / all-one check
    sub = df[(df["phase"] == "eval") & (df["success"].notna())].copy()
    n_success = int((sub["success"] == True).sum())  # noqa: E712
    n_fail = int((sub["success"] == False).sum())  # noqa: E712
    degenerate = (n_success == 0 or n_fail == 0)
    glmm["degenerate_outcome"] = degenerate
    if degenerate:
        glmm["degenerate_note"] = (
            f"All {len(sub)} eval rows have success={bool(n_success)}. "
            "GLMM/GEE cannot estimate effects (complete separation / floor effect). "
            "Report descriptive Clopper-Pearson CIs per condition instead."
        )

    out = {
        "jsonl": str(JSONL),
        "n_total_rows": int(len(df)),
        "n_eval_rows": int(((df["phase"]=="eval") & (df["success"].notna())).sum()),
        "per_condition": rates,
        "glmm": glmm,
    }
    out = _sanitize(out)
    with open(STATS, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"wrote {STATS}")

if __name__ == "__main__":
    main()
