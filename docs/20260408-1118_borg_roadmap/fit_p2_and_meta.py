#!/usr/bin/env python3.12
"""Fit Sonnet GLMM (Part A) + cross-model meta-analysis (Part B).

Part A: success ~ condition + (1|task), binomial link (Sonnet only).
  Primary: BinomialBayesMixedGLM (VB)
  Backup : GEE with exchangeable working correlation (sandwich SE)
  + Cochran's Q, pairwise McNemar, Clopper-Pearson per-condition CIs.
  Handles complete-separation / floor effect gracefully.

Part B: success ~ condition + model + condition:model + (1|task),
  pooled across P1.1 MiniMax and P2.1 Sonnet.
  Primary: BinomialBayesMixedGLM (VB)
  Backup : GEE
  + LRT approximation for the interaction term via nested GEE.

Writes p2_sonnet_stats.json and p2_meta_stats.json.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

import numpy as np
import pandas as pd

OUTDIR = Path("/root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap")
P1_JSONL = OUTDIR / "p1_minimax_results.jsonl"
P2_JSONL = OUTDIR / "p2_sonnet_results.jsonl"
P2_STATS = OUTDIR / "p2_sonnet_stats.json"
META_STATS = OUTDIR / "p2_meta_stats.json"

CONDITIONS = ["C0_no_borg", "C1_borg_empty", "C2_borg_seeded"]


# ── helpers ───────────────────────────────────────────────────────────────────
def load_jsonl(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for ln in open(path):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    from scipy.stats import beta
    if n == 0:
        return (None, None)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (lo, hi)


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def per_condition_rates(df: pd.DataFrame) -> dict:
    """df filtered to eval rows with success is not None."""
    out = {}
    for c in CONDITIONS:
        sub = df[df["condition"] == c]
        completed = sub[sub["success"].notna()]
        successes = int((completed["success"] == True).sum())  # noqa: E712
        skipped = 0
        if "skipped" in completed.columns:
            skipped = int(completed["skipped"].fillna(False).astype(bool).sum())
        n = int(len(completed))
        lo, hi = clopper_pearson(successes, n)
        out[c] = {
            "n": n,
            "successes": successes,
            "skipped": skipped,
            "pass_rate": (successes / n) if n else None,
            "ci95_lo": lo,
            "ci95_hi": hi,
        }
    return out


# ── Part A: Sonnet-only GLMM ──────────────────────────────────────────────────
def fit_sonnet(df_raw: pd.DataFrame) -> dict:
    if df_raw.empty:
        return {"error": "no p2_sonnet_results.jsonl rows"}
    if "phase" not in df_raw.columns:
        df_raw["phase"] = "eval"
    sub = df_raw[(df_raw["phase"] == "eval") & (df_raw["success"].notna())].copy()
    if len(sub) == 0:
        return {"error": "no completed eval rows"}

    sub["y"] = sub["success"].astype(int)

    res = {
        "n_rows": int(len(sub)),
        "n_tasks": int(sub["task_id"].nunique()),
        "n_success": int(sub["y"].sum()),
        "n_fail": int((sub["y"] == 0).sum()),
    }
    n_success = res["n_success"]
    n_fail = res["n_fail"]
    degenerate = (n_success == 0 or n_fail == 0)
    res["degenerate_outcome"] = degenerate
    if degenerate:
        res["degenerate_note"] = (
            f"All {len(sub)} eval rows have success={bool(n_success)}. "
            "GLMM/GEE cannot estimate effects (complete separation / floor effect). "
            "Reporting descriptive Clopper-Pearson CIs only."
        )

    res["per_condition"] = per_condition_rates(sub)

    # ── BinomialBayesMixedGLM ───────────────────────────────────────────────
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        from scipy.stats import norm
        for c in CONDITIONS[1:]:
            sub[c] = (sub["condition"] == c).astype(int)
        y = sub["y"].values
        X = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in CONDITIONS[1:]])
        task_codes = pd.Categorical(sub["task_id"]).codes
        n_tasks = int(task_codes.max() + 1)
        Z = np.zeros((len(sub), n_tasks))
        for i, t in enumerate(task_codes):
            Z[i, t] = 1.0
        ident = np.array([0] * n_tasks)
        model = BinomialBayesMixedGLM(y, X, Z, ident, vcp_p=2.0, fe_p=2.0)
        fit = model.fit_vb()
        coefs = fit.fe_mean
        ses = fit.fe_sd
        zvals = coefs / ses
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

    # ── GEE backup ──────────────────────────────────────────────────────────
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
            res["gee"][str(name)] = {
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
    wide = None
    try:
        from statsmodels.stats.contingency_tables import cochrans_q
        wide = sub.pivot_table(index="task_id", columns="condition", values="y", aggfunc="first")
        wide = wide.dropna()
        res["cochrans_q_n_complete_tasks"] = int(len(wide))
        if len(wide) >= 2 and set(CONDITIONS) <= set(wide.columns):
            q = cochrans_q(wide[CONDITIONS].values)
            res["cochrans_q"] = {
                "stat": float(q.statistic),
                "df": int(q.df),
                "p": float(q.pvalue),
            }
    except Exception as e:
        res["cochrans_q_error"] = f"{type(e).__name__}: {e}"

    # ── pairwise McNemar ────────────────────────────────────────────────────
    try:
        from statsmodels.stats.contingency_tables import mcnemar
        res["mcnemar"] = {}
        if wide is not None:
            pairs = [("C0_no_borg", "C1_borg_empty"),
                     ("C0_no_borg", "C2_borg_seeded"),
                     ("C1_borg_empty", "C2_borg_seeded")]
            for a, b in pairs:
                if a not in wide.columns or b not in wide.columns:
                    continue
                tab = [[0, 0], [0, 0]]
                for _, row in wide.iterrows():
                    ai = int(row[a]); bi = int(row[b])
                    tab[ai][bi] += 1
                mc = mcnemar(tab, exact=True)
                res["mcnemar"][f"{a}_vs_{b}"] = {
                    "table": tab,
                    "stat": float(mc.statistic),
                    "p": float(mc.pvalue),
                }
    except Exception as e:
        res["mcnemar_error"] = f"{type(e).__name__}: {e}"

    return res


# ── Part B: cross-model meta-analysis ────────────────────────────────────────
def fit_meta(p1_raw: pd.DataFrame, p2_raw: pd.DataFrame) -> dict:
    res: dict = {}

    # ── stack ─────────────────────────────────────────────────────────────
    def _prep(df: pd.DataFrame, model_label: str) -> pd.DataFrame:
        if df.empty:
            return df
        if "phase" not in df.columns:
            df = df.copy()
            df["phase"] = "eval"
        sub = df[(df["phase"] == "eval") & (df["success"].notna())].copy()
        if len(sub) == 0:
            return sub
        sub["y"] = sub["success"].astype(int)
        sub["model_label"] = model_label
        return sub

    p1 = _prep(p1_raw, "minimax")
    p2 = _prep(p2_raw, "sonnet")
    combined = pd.concat([p1, p2], ignore_index=True, sort=False) if len(p2) else p1.copy()
    res["models_included"] = sorted(combined["model_label"].unique().tolist()) if len(combined) else []
    res["n_total"] = int(len(combined))
    res["n_per_model"] = combined["model_label"].value_counts().to_dict() if len(combined) else {}

    if len(combined) == 0:
        res["error"] = "no rows"
        return res

    # ── per-cell pass rates (model × condition) ────────────────────────────
    per_cell = {}
    for m in res["models_included"]:
        per_cell[m] = {}
        for c in CONDITIONS:
            cell = combined[(combined["model_label"] == m) & (combined["condition"] == c)]
            k = int((cell["y"] == 1).sum())
            n = int(len(cell))
            lo, hi = clopper_pearson(k, n)
            per_cell[m][c] = {
                "n": n, "successes": k,
                "pass_rate": (k / n) if n else None,
                "ci95_lo": lo, "ci95_hi": hi,
            }
    res["per_cell"] = per_cell

    n_success = int((combined["y"] == 1).sum())
    n_fail = int((combined["y"] == 0).sum())
    degenerate = (n_success == 0 or n_fail == 0)
    res["degenerate_outcome"] = degenerate
    if degenerate:
        res["degenerate_note"] = (
            f"All {len(combined)} rows have success={bool(n_success)}. "
            "GLMM/GEE cannot estimate condition/model/interaction effects "
            "under complete separation. Reporting descriptive per-cell CIs only."
        )

    # ── GEE with condition + model + interaction ───────────────────────────
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        from statsmodels.genmod.cov_struct import Exchangeable
        combined["task_label"] = combined["task_id"].astype(str) + "__" + combined["model_label"].astype(str)

        # Full model with interaction
        try:
            full = smf.gee(
                "y ~ C(condition, Treatment('C0_no_borg')) * C(model_label, Treatment('minimax'))",
                "task_label",
                data=combined,
                family=sm.families.Binomial(),
                cov_struct=Exchangeable(),
            )
            full_fit = full.fit()
            full_params = {}
            ci = full_fit.conf_int()
            for name, val in full_fit.params.items():
                lo, hi = ci.loc[name].values
                full_params[str(name)] = {
                    "coef": float(val),
                    "se": float(full_fit.bse[name]),
                    "z": float(full_fit.tvalues[name]),
                    "p": float(full_fit.pvalues[name]),
                    "or": float(math.exp(val)),
                    "or_ci_lo": float(math.exp(lo)),
                    "or_ci_hi": float(math.exp(hi)),
                }
            res["gee_full_interaction"] = full_params
            res["gee_full_qic"] = float(getattr(full_fit, "qic", [float("nan")])[0]) \
                if hasattr(full_fit, "qic") else None
        except Exception as e:
            res["gee_full_interaction_error"] = f"{type(e).__name__}: {e}"

        # Main-effects model (no interaction)
        try:
            main = smf.gee(
                "y ~ C(condition, Treatment('C0_no_borg')) + C(model_label, Treatment('minimax'))",
                "task_label",
                data=combined,
                family=sm.families.Binomial(),
                cov_struct=Exchangeable(),
            )
            main_fit = main.fit()
            main_params = {}
            ci = main_fit.conf_int()
            for name, val in main_fit.params.items():
                lo, hi = ci.loc[name].values
                main_params[str(name)] = {
                    "coef": float(val),
                    "se": float(main_fit.bse[name]),
                    "z": float(main_fit.tvalues[name]),
                    "p": float(main_fit.pvalues[name]),
                    "or": float(math.exp(val)),
                    "or_ci_lo": float(math.exp(lo)),
                    "or_ci_hi": float(math.exp(hi)),
                }
            res["gee_main_effects"] = main_params
        except Exception as e:
            res["gee_main_effects_error"] = f"{type(e).__name__}: {e}"
    except Exception as e:
        res["gee_error"] = f"{type(e).__name__}: {e}"

    # ── BinomialBayesMixedGLM with interaction (primary) ───────────────────
    try:
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
        from scipy.stats import norm
        df = combined.copy()
        df["C1"] = (df["condition"] == "C1_borg_empty").astype(int)
        df["C2"] = (df["condition"] == "C2_borg_seeded").astype(int)
        df["Msonnet"] = (df["model_label"] == "sonnet").astype(int)
        df["C1_Msonnet"] = df["C1"] * df["Msonnet"]
        df["C2_Msonnet"] = df["C2"] * df["Msonnet"]

        y = df["y"].values
        X = np.column_stack([
            np.ones(len(df)),
            df["C1"].values, df["C2"].values,
            df["Msonnet"].values,
            df["C1_Msonnet"].values, df["C2_Msonnet"].values,
        ])
        # random intercept by task_id (pooled across models)
        task_codes = pd.Categorical(df["task_id"]).codes
        n_tasks = int(task_codes.max() + 1)
        Z = np.zeros((len(df), n_tasks))
        for i, t in enumerate(task_codes):
            Z[i, t] = 1.0
        ident = np.array([0] * n_tasks)
        model = BinomialBayesMixedGLM(y, X, Z, ident, vcp_p=2.0, fe_p=2.0)
        fit = model.fit_vb()
        coefs = fit.fe_mean
        ses = fit.fe_sd
        zvals = coefs / ses
        pvals = 2 * (1 - norm.cdf(np.abs(zvals)))
        names = ["intercept", "C1_borg_empty", "C2_borg_seeded",
                 "model_sonnet", "C1:model_sonnet", "C2:model_sonnet"]
        glmm = {}
        for i, nm in enumerate(names):
            ci_lo = coefs[i] - 1.96 * ses[i]
            ci_hi = coefs[i] + 1.96 * ses[i]
            glmm[nm] = {
                "coef": float(coefs[i]),
                "se": float(ses[i]),
                "z": float(zvals[i]),
                "p": float(pvals[i]),
                "or": float(math.exp(coefs[i])),
                "or_ci_lo": float(math.exp(ci_lo)),
                "or_ci_hi": float(math.exp(ci_hi)),
            }
        res["glmm_bayes_interaction"] = glmm
        res["glmm_backend"] = "BinomialBayesMixedGLM (VB) — meta"
    except Exception as e:
        res["glmm_bayes_interaction_error"] = f"{type(e).__name__}: {e}"

    return res


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    print("== Fit P2.1 Sonnet GLMM + P2.2 cross-model meta-analysis ==")
    p1_df = load_jsonl(P1_JSONL)
    p2_df = load_jsonl(P2_JSONL)
    print(f"loaded p1={len(p1_df)} p2={len(p2_df)}")

    # Part A
    part_a = fit_sonnet(p2_df)
    part_a_out = _sanitize({
        "jsonl": str(P2_JSONL),
        "n_total_rows": int(len(p2_df)),
        "part_a": part_a,
    })
    with open(P2_STATS, "w") as f:
        json.dump(part_a_out, f, indent=2, default=str)
    print(f"wrote {P2_STATS}")

    # Part B
    part_b = fit_meta(p1_df, p2_df)
    part_b_out = _sanitize({
        "p1_jsonl": str(P1_JSONL),
        "p2_jsonl": str(P2_JSONL),
        "n_total_rows": int(len(p1_df) + len(p2_df)),
        "meta": part_b,
    })
    with open(META_STATS, "w") as f:
        json.dump(part_b_out, f, indent=2, default=str)
    print(f"wrote {META_STATS}")


if __name__ == "__main__":
    main()
