#!/usr/bin/env python3.12
"""
Run the current borg.core.pack_taxonomy.classify_error against the labelled
error corpus. Emit a per-row CSV so DATA_ANALYSIS.md can aggregate.

Columns of baseline_results.csv:
  id, language, framework, family, expected_problem_class, actual_problem_class,
  is_correct, is_silent_miss, is_false_confident, is_correct_no_match, text

Definitions (from the task brief):
  correct             = actual == expected
  silent_miss         = actual is None and expected is None           (good)
  false_confident     = actual is not None and actual != expected      (BAD)
  correct_no_match    = actual is None and expected is not None        (honest miss)

Run: python3.12 run_baseline.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from borg.core.pack_taxonomy import classify_error

HERE = Path(__file__).parent
CORPUS = HERE / "error_corpus.jsonl"
OUT_CSV = HERE / "baseline_results.csv"


def main() -> None:
    rows_in = [json.loads(line) for line in CORPUS.read_text().splitlines() if line.strip()]

    out_rows = []
    n_total = len(rows_in)
    n_correct = 0
    n_silent_miss = 0
    n_false_confident = 0
    n_correct_no_match = 0

    for r in rows_in:
        expected = r["expected_problem_class"]
        actual = classify_error(r["text"])
        is_correct = actual == expected
        is_silent_miss = actual is None and expected is None
        is_false_confident = actual is not None and actual != expected
        is_correct_no_match = actual is None and expected is not None

        n_correct += int(is_correct)
        n_silent_miss += int(is_silent_miss)
        n_false_confident += int(is_false_confident)
        n_correct_no_match += int(is_correct_no_match)

        out_rows.append(
            {
                "id": r["id"],
                "language": r["language"],
                "framework": r["framework"] or "",
                "family": r["family"],
                "expected_problem_class": expected or "",
                "actual_problem_class": actual or "",
                "is_correct": int(is_correct),
                "is_silent_miss": int(is_silent_miss),
                "is_false_confident": int(is_false_confident),
                "is_correct_no_match": int(is_correct_no_match),
                "text": r["text"],
            }
        )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    # Summary
    precision_den = sum(1 for r in out_rows if r["actual_problem_class"])
    recall_den = sum(1 for r in out_rows if r["expected_problem_class"])
    tp = sum(1 for r in out_rows if r["is_correct"] and r["expected_problem_class"])
    precision = tp / precision_den if precision_den else 0.0
    recall = tp / recall_den if recall_den else 0.0

    print(f"Rows evaluated       : {n_total}")
    print(f"Exact-correct        : {n_correct}  ({n_correct / n_total:.1%})")
    print(f"Silent-miss (honest) : {n_silent_miss}")
    print(f"False-confident      : {n_false_confident}  ({n_false_confident / n_total:.1%})")
    print(f"Correct-no-match     : {n_correct_no_match}  ({n_correct_no_match / n_total:.1%})")
    print(f"Precision (of predictions that fired) : {precision:.1%}  ({tp}/{precision_den})")
    print(f"Recall    (vs. rows with expected PC) : {recall:.1%}  ({tp}/{recall_den})")
    print(f"CSV written to       : {OUT_CSV}")


if __name__ == "__main__":
    main()
