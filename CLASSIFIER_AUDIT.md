# Classifier Audit 2026-04-24

Audit of the "173-row Python/Django corpus, FCR 53.8 to 0.58 percent, precision 13.1 to 93.8 percent" claim in BORG_PRD_FINAL.md and CHANGELOG.md.

## TL;DR

The numbers reproduce exactly. The framing misleads.

- run_baseline.py reruns deterministically (0.09s, no API). Output matches committed baseline_results.csv byte-for-byte.
- FCR 0.58 percent and precision 93.8 percent are real, but computed across a 173-row corpus where the classifier is silent on 91 percent of rows.
- The corpus is NOT Python/Django. It is 6 languages: shell 43, javascript 38, python 34, rust 22, typescript 20, go 16.
- The classifier is effectively Python-only. Of 16 predictions, 15 are on Python and 1 on shell.
- Handoff note about "30 percent synthetic" appears incorrect. Every row has a real-world source attribution (docs, SO, issue trackers). No synthetic-vs-real split exists in the data.

## What the numbers actually say

| Scope | n | Correct | Fires | Recall | Precision |
|---|---:|---:|---:|---:|---:|
| Python subset | 34 | 14 | 15 | 41.2% | 93.3% |
| Shell subset | 43 | 1 | 1 | 2.3% | 100% |
| JS / TS / Rust / Go | 96 | 0 | 0 | 0% | N/A |
| Full corpus | 173 | 15 | 16 | 8.7% | 93.8% |

Reading: the classifier prefers silence over wrong answers (good property). Of the 16 times it volunteers a class, 15 are right. But it stays silent on 91 percent of inputs overall, and 100 percent of non-Python non-shell inputs.

## The one false-confident row (e0005)

Input: ImportError: cannot import name soft_unicode from markupsafe
Expected: missing_dependency (Flask/markupsafe version incompatibility)
Predicted: import_cycle (reasonable partial match on surface form)

Genuinely ambiguous row, not a classifier bug. Leave as-is or relabel; either is defensible.

## Recommended framing for public claims

Replace current PRD and CHANGELOG language with:

On the Python subset (n=34) of the classifier PRD corpus: 41.2 percent recall, 93.3 percent precision, FCR 2.9 percent (1/34). The corpus is multi-language (173 rows across 6 languages); non-Python rows are intentionally outside classifier scope and return None.

This is accurate (stable denominator), still compelling, honest about scope, and defensible under technical DD.

## What was NOT audited (deferred)

- The "53.8 to 0.58 percent" historical baseline. CHANGELOG cites it; raw pre-v3.2.4 baseline data was not reproduced today. The current 0.58 percent IS reproduced.
- The "1708 passing tests" claim. Unit tests not run as part of this audit.
- Per-family breakdown within Python subset (null_deref, missing_module, type_mismatch, django_*).
- Shell recall ceiling (43 rows, 1 hit). Is this intentional scope or a gap?

## Reproducibility

    cd /root/hermes-workspace/borg
    python3.12 docs/20260408-0623_classifier_prd/run_baseline.py

Writes docs/20260408-0623_classifier_prd/baseline_results.csv (stable under rerun; diff against committed version is empty).

## Files touched

- Read: docs/20260408-0623_classifier_prd/error_corpus.jsonl, run_baseline.py, baseline_results.csv
- No writes outside the regenerated CSV (byte-identical to committed)
- No commits to code paths; classifier unchanged
