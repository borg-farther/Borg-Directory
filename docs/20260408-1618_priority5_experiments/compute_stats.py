#!/usr/bin/env python3.12
"""
Compute cross-model classifier benchmark statistics.

Reads classifier_benchmark_results.jsonl (written by run_classifier_benchmark.py)
and emits classifier_benchmark_stats.json plus a short stdout summary.

Metrics per approach ({borg, gemini_zero, gemini_ctx, null}):
  n                      : rows scored
  exact_correct          : actual == expected
  false_confident        : actual != None and actual != expected   (BAD)
  correct_no_match       : actual == None and expected != None     (honest refusal)
  silent_miss            : actual == None and expected == None
  errored                : model refused to produce parseable output
  fcr                    : false_confident / n
  precision              : exact_correct / (exact_correct + false_confident)   (of rows where it fired)
  recall                 : exact_correct / n                                    (rows with any expected)
  recall_in_taxonomy     : exact_correct / |expected in borg taxonomy|          (only borg-relevant)

Comparisons:
  paired McNemar vs borg (gemini_zero, gemini_ctx, null) on
    (a) exact-correct rate
    (b) false-confident rate
  5x4 confusion across approaches — count rows classified (correct/wrong/none) per approach
  Per-language breakdown of exact-correct and FCR

95% CI: Wilson score interval.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "classifier_benchmark_results.jsonl"
OUT = HERE / "classifier_benchmark_stats.json"

BORG_CLASSES = {
    "circular_dependency", "null_pointer_chain", "missing_foreign_key",
    "migration_state_desync", "import_cycle", "race_condition",
    "configuration_error", "type_mismatch", "missing_dependency",
    "timeout_hang", "schema_drift", "permission_denied",
}

APPROACHES = ["borg", "gemini_zero", "gemini_ctx", "null"]


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact binomial two-sided McNemar p-value on the (b,c) discordant pairs.

    b, c = counts where model A correct & B wrong, and A wrong & B correct.
    """
    n = b + c
    if n == 0:
        return 1.0
    # two-sided: sum of binomial(n, k) * 0.5^n for |k - n/2| >= |min(b,c) - n/2|
    k = min(b, c)
    # P(X <= k or X >= n - k) under Binomial(n, 0.5)
    from math import comb
    p = 0.0
    for i in range(0, k + 1):
        p += comb(n, i)
    for i in range(n - k, n + 1):
        if i > k:  # avoid double count when b==c==n/2
            p += comb(n, i)
    p /= (1 << n)
    return min(1.0, p)


def load_rows() -> List[Dict[str, Any]]:
    return [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]


def classify_outcome(pred: Optional[str], expected: Optional[str]) -> str:
    if pred is None and expected is None:
        return "silent_miss"
    if pred is None and expected is not None:
        return "correct_no_match"
    if pred is not None and pred == expected:
        return "exact_correct"
    return "false_confident"


def per_approach_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    n = len(rows)
    n_in_borg = sum(1 for r in rows if r["expected_problem_class"] in BORG_CLASSES)
    for ap in APPROACHES:
        counts = Counter()
        errored = 0
        tp_in_borg = 0
        fired = 0
        correct = 0
        fc = 0
        for r in rows:
            exp = r["expected_problem_class"]
            if ap == "borg":
                pred = r["borg_pred"]
                err = False
            elif ap == "gemini_zero":
                pred = r["gemini_zero_pred"]
                err = bool(r.get("gemini_zero_errored"))
            elif ap == "gemini_ctx":
                pred = r["gemini_ctx_pred"]
                err = bool(r.get("gemini_ctx_errored"))
            else:  # null
                pred = None
                err = False
            if err:
                errored += 1
            outcome = classify_outcome(pred, exp)
            counts[outcome] += 1
            if pred is not None:
                fired += 1
                if pred == exp:
                    correct += 1
                else:
                    fc += 1
                    if exp in BORG_CLASSES and pred == exp:
                        tp_in_borg += 1
            if pred == exp and exp in BORG_CLASSES:
                tp_in_borg += 1
        fcr = fc / n
        precision = correct / fired if fired else 0.0
        recall = correct / n
        recall_in_taxonomy = tp_in_borg / n_in_borg if n_in_borg else 0.0
        fcr_lo, fcr_hi = wilson(fc, n)
        out[ap] = {
            "n": n,
            "exact_correct": counts["exact_correct"],
            "false_confident": counts["false_confident"],
            "correct_no_match": counts["correct_no_match"],
            "silent_miss": counts["silent_miss"],
            "errored": errored,
            "fcr": fcr,
            "fcr_95ci": [fcr_lo, fcr_hi],
            "precision": precision,
            "recall": recall,
            "recall_in_borg_taxonomy": recall_in_taxonomy,
            "fired": fired,
        }
    out["_n_in_borg_taxonomy"] = n_in_borg
    return out


def paired_comparisons(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Paired McNemar: borg vs each of {gemini_zero, gemini_ctx, null}."""
    out: Dict[str, Any] = {}

    def correct(ap: str, r: Dict[str, Any]) -> bool:
        exp = r["expected_problem_class"]
        if ap == "borg":
            return r["borg_pred"] == exp
        if ap == "gemini_zero":
            return r["gemini_zero_pred"] == exp
        if ap == "gemini_ctx":
            return r["gemini_ctx_pred"] == exp
        return None == exp  # null

    def false_confident(ap: str, r: Dict[str, Any]) -> bool:
        exp = r["expected_problem_class"]
        if ap == "borg":
            p = r["borg_pred"]
        elif ap == "gemini_zero":
            p = r["gemini_zero_pred"]
        elif ap == "gemini_ctx":
            p = r["gemini_ctx_pred"]
        else:
            p = None
        return p is not None and p != exp

    for ap in ["gemini_zero", "gemini_ctx", "null"]:
        # McNemar on exact-correct
        b = sum(1 for r in rows if correct("borg", r) and not correct(ap, r))
        c = sum(1 for r in rows if not correct("borg", r) and correct(ap, r))
        p_correct = mcnemar_exact(b, c)
        # McNemar on false-confident
        bf = sum(1 for r in rows if false_confident("borg", r) and not false_confident(ap, r))
        cf = sum(1 for r in rows if not false_confident("borg", r) and false_confident(ap, r))
        p_fc = mcnemar_exact(bf, cf)
        out[f"borg_vs_{ap}"] = {
            "correct_discordant_borg_only": b,
            "correct_discordant_other_only": c,
            "p_mcnemar_correct": p_correct,
            "fc_discordant_borg_only": bf,
            "fc_discordant_other_only": cf,
            "p_mcnemar_false_confident": p_fc,
        }
    return out


def per_language_breakdown(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_lang: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_lang[r["language"] or "unknown"].append(r)
    out: Dict[str, Any] = {}
    for lang, rs in sorted(by_lang.items()):
        n = len(rs)
        row: Dict[str, Any] = {"n": n}
        for ap in APPROACHES:
            fc = 0
            correct = 0
            for r in rs:
                exp = r["expected_problem_class"]
                if ap == "borg":
                    p = r["borg_pred"]
                elif ap == "gemini_zero":
                    p = r["gemini_zero_pred"]
                elif ap == "gemini_ctx":
                    p = r["gemini_ctx_pred"]
                else:
                    p = None
                if p is not None and p != exp:
                    fc += 1
                if p == exp:
                    correct += 1
            row[ap] = {
                "correct": correct,
                "correct_rate": correct / n,
                "false_confident": fc,
                "fcr": fc / n,
            }
        out[lang] = row
    return out


def confusion_matrix(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Co-occurrence: for every (approach_A, approach_B) pair, count rows where
    (A_correct, B_correct) falls in each 2x2 bucket."""
    mat: Dict[str, Dict[str, Dict[str, int]]] = {}

    def correct(ap: str, r: Dict[str, Any]) -> bool:
        exp = r["expected_problem_class"]
        if ap == "borg":
            return r["borg_pred"] == exp
        if ap == "gemini_zero":
            return r["gemini_zero_pred"] == exp
        if ap == "gemini_ctx":
            return r["gemini_ctx_pred"] == exp
        return None == exp

    for a in APPROACHES:
        mat[a] = {}
        for b in APPROACHES:
            both = only_a = only_b = neither = 0
            for r in rows:
                ca = correct(a, r)
                cb = correct(b, r)
                if ca and cb:
                    both += 1
                elif ca and not cb:
                    only_a += 1
                elif not ca and cb:
                    only_b += 1
                else:
                    neither += 1
            mat[a][b] = {"both": both, "only_a": only_a, "only_b": only_b, "neither": neither}
    return mat


def agreement(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Did borg and gemini fail on the same rows?"""
    def correct(ap: str, r: Dict[str, Any]) -> bool:
        exp = r["expected_problem_class"]
        if ap == "borg":
            return r["borg_pred"] == exp
        if ap == "gemini_zero":
            return r["gemini_zero_pred"] == exp
        if ap == "gemini_ctx":
            return r["gemini_ctx_pred"] == exp
        return None == exp

    out = {}
    for other in ["gemini_zero", "gemini_ctx", "null"]:
        phi = 0.0
        n = len(rows)
        a = sum(1 for r in rows if correct("borg", r) and correct(other, r))
        b = sum(1 for r in rows if correct("borg", r) and not correct(other, r))
        c = sum(1 for r in rows if not correct("borg", r) and correct(other, r))
        d = sum(1 for r in rows if not correct("borg", r) and not correct(other, r))
        denom = math.sqrt(max(1, (a + b) * (c + d) * (a + c) * (b + d)))
        phi = (a * d - b * c) / denom if denom else 0.0
        out[f"borg_vs_{other}"] = {
            "both_correct": a,
            "only_borg_correct": b,
            "only_other_correct": c,
            "both_wrong": d,
            "phi": phi,
        }
    return out


def main() -> None:
    rows = load_rows()
    stats = {
        "n_rows": len(rows),
        "per_approach": per_approach_metrics(rows),
        "paired_mcnemar": paired_comparisons(rows),
        "per_language": per_language_breakdown(rows),
        "confusion_matrix_correctness": confusion_matrix(rows),
        "agreement": agreement(rows),
    }
    OUT.write_text(json.dumps(stats, indent=2, ensure_ascii=False))

    print(f"\n=== P5 classifier benchmark — n={len(rows)} ===\n")
    print(f"{'approach':<14}{'correct':>10}{'fcr':>10}{'precision':>12}{'errored':>10}")
    for ap in APPROACHES:
        m = stats["per_approach"][ap]
        print(
            f"{ap:<14}{m['exact_correct']:>10}"
            f"{m['fcr']*100:>9.2f}%"
            f"{m['precision']*100:>11.1f}%"
            f"{m['errored']:>10}"
        )
    print()
    for k, v in stats["paired_mcnemar"].items():
        print(
            f"{k:<22} p_correct={v['p_mcnemar_correct']:.4f}  "
            f"(borg_only={v['correct_discordant_borg_only']}, "
            f"other_only={v['correct_discordant_other_only']}) | "
            f"p_fc={v['p_mcnemar_false_confident']:.4f}"
        )
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
