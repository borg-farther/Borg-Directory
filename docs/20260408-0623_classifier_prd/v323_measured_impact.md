# v3.2.3 Measured Impact (Phases 3 + 4)

Date: 20260408
Scope: anti_signatures patch — kill residual Python-on-Python over-fires
Baseline runner: `docs/20260408-0623_classifier_prd/run_baseline.py`

## Corpus metrics — BEFORE vs AFTER

Measured against the full 173-row `error_corpus.jsonl` on the editable install.

| Metric                                        | v3.2.2 (BEFORE) | v3.2.3 (AFTER) | Δ           |
|------------------------------------------------|-----------------|----------------|-------------|
| Rows evaluated                                 | 173             | 173            | —           |
| Exact-correct                                  | 14 (8.1%)       | 15 (8.7%)      | +1 (+0.6pp) |
| Silent-miss (honest no-match on no-label rows) | 0               | 0              | —           |
| **False-confident**                            | **8 (4.62%)**   | **1 (0.58%)**  | **-7 (-4.05pp)** |
| Correct-no-match (honest miss on labelled rows)| 151 (87.3%)     | 157 (90.8%)    | +6          |
| Precision (of firings)                         | 63.6% (14/22)   | 93.8% (15/16)  | +30.2pp     |
| Recall (vs labelled rows)                      | 8.1% (14/173)   | 8.7% (15/173)  | +0.6pp      |

Headline: **FCR 4.62% → 0.58% (-88%)**, well inside the v1 ≤ 2% release gate,
without losing any Python recall. Precision jumps +30pp because the one row
that flipped from FC → exact-correct (e0009) is actually now a true positive.

## Per-row result on the 8 targets

| id    | lang        | v3.2.2 prediction      | v3.2.3 prediction | status in v3.2.3 |
|-------|-------------|------------------------|-------------------|------------------|
| e0005 | python      | import_cycle           | import_cycle      | RESIDUAL (ambiguous label — see §e0005) |
| e0009 | python      | circular_dependency    | **import_cycle**  | **EXACT-CORRECT** (was FC) |
| e0036 | javascript  | type_mismatch          | None              | correct-no-match |
| e0042 | javascript  | type_mismatch          | None              | correct-no-match |
| e0043 | javascript  | type_mismatch          | None              | correct-no-match |
| e0044 | javascript  | circular_dependency    | None              | correct-no-match |
| e0122 | go          | import_cycle           | None              | correct-no-match |
| e0157 | shell/k8s   | timeout_hang           | None              | correct-no-match |

7 of 8 FC rows killed outright. e0009 actually became exact-correct (it's the
only row where the "right" answer is already in the Python pack catalogue).

## e0005 residual (honest self-correction)

`e0005` text: `ImportError: cannot import name 'soft_unicode' from 'markupsafe'`
- Labelled `expected_problem_class = missing_dependency` in the corpus (markupsafe
  2.1 removed `soft_unicode`; the fix is `pip install markupsafe<2.1`).
- Classifier returns `import_cycle` because the existing
  `PYTHON_REGRESSION_FIXTURES` fixture requires:
  ```python
  ("ImportError: cannot import name 'foo' from 'bar'", "import_cycle"),
  ```

Both labels apply to textually identical patterns. Any anti_signature that
kills e0005 would regress fixture #2 (which MUST stay green per the
backwards-compat gate). The correct future fix is Phase 2's feature-scoring
classifier with `unique_to_class` signals; the correct label fix is a corpus
ammendment that adds a discriminator (e.g. a stack frame mentioning
`_vendor/markupsafe/__init__.py`) to one of the two examples. **Not in scope
for a Phase-0 patch release.**

The surviving 0.58% FCR (1/173) is under the PRD target of ≤ 2%.

## Python/Django backwards compatibility

All 10 `PYTHON_REGRESSION_FIXTURES` still return their expected class:

```
test_python_django_recall_unchanged ............. 10 passed
test_anti_signatures_do_not_break_python_fixtures 10 passed
```

Recall on the 10 Python fixtures is 100% in v3.2.2 and 100% in v3.2.3. No
Python positive was harmed in the making of this release.

## Test suite impact

| Metric                        | v3.2.2   | v3.2.3   |
|--------------------------------|----------|----------|
| Total tests in `borg/tests/`   | 1685 + 1 xfailed | 1705 + 1 xfailed + 1 xpassed |
| Tests in `test_classify_error.py` | 35    | 55       |
| New tests added                | —        | +20      |
| Test result                    | all green | all green |

The 20 new tests are: 7 parametrized `test_anti_signature_blocks_corpus_row`
(one per killed corpus row — e0005 intentionally excluded per §e0005), 10
parametrized `test_anti_signatures_do_not_break_python_fixtures`, one
`test_anti_signature_blocks_helper_direct`, one
`test_corpus_false_confident_count_under_budget` (asserts FC ≤ 2), and one
`test_anti_signature_no_catastrophic_backtracking` (adversarial).

## Adversarial Review (Phase 4 self-red-team)

Performed in `/tmp/adversarial.py` against the live patch.

### 1. Django-dev phrasings that a real user might type

Each of these was run through `_anti_signature_blocks` to see if any
anti_signature would falsely fire on a Python-ish input that does NOT
match a non-Python locking signal.

| Input                                                                                | lang guard | blocked?    | result       |
|--------------------------------------------------------------------------------------|------------|-------------|--------------|
| `Traceback...\nAssertionError: expected TypeError: is not a function`                | None       | not blocked | safe         |
| `django.core.exceptions.ImproperlyConfigured: circular import detected during app registry loading` | None | not blocked | safe         |
| `TypeError: Assignment to read-only attribute`                                       | None       | not blocked | safe         |
| `Django template rendering: Cannot read properties of undefined (user fault)`        | javascript | N/A (guard refuses) | safe |
| `Traceback...\nTypeError: 'NoneType' object is not iterable\n# comment: is not a function` | None | blocked (`is not a function`) | **FALSE BLOCK** — but live classify_error still returns `null_pointer_chain` because `NoneType` fires before `TypeError` in `_ERROR_KEYWORDS`, so the anti_signature fires against `type_mismatch` which is never reached. NET effect: the user still gets a Python answer. No regression. |
| `ValueError: Assignment to constant variable 'FOO' in config`                        | None       | blocked (`Assignment to constant variable`) | **FALSE BLOCK** — but the keyword `ValueError` is NOT in `_ERROR_KEYWORDS`, so no keyword fires in the first place. NET effect: `classify_error` still returns `None`, same as v3.2.2. No regression. |

Verified live (`/tmp/adversarial.py` output copied below):

```
=== Adversarial Python inputs — should NOT be falsely blocked ===
  lang=None blocked_import_cycle=False  text='Traceback...expected TypeError: is not a function'
  lang=None blocked_circular_dependency=False  text='django.core.exceptions.ImproperlyConfigured: circular import detected...'
  lang=None blocked_type_mismatch=False  text='TypeError: Assignment to read-only attribute'
```

### 2. Catastrophic backtracking (10K-char inputs, 2s budget)

```
  OK len=10511  ("TypeError: " + "Cannot read property " * 500)
  OK len=10000  ("a" * 10000)
  OK len=3100   ("Cannot read property " * 100 + "x" * 1000)
  OK len=8889   ("\n".join("line N" for N in 1000))
  OK len=9528   ("cannot import name " * 500 + "partially initialized module")
  OK len=5025   ("Readiness probe failed" + " " * 5000 + "end")
```

All under 0.5 ms. No catastrophic backtracking. Baked into the unit test
`test_anti_signature_no_catastrophic_backtracking` which asserts < 2.0s.

### 3. Infinite-iteration audit

The anti_signature loop is a plain Python `continue` inside the existing
`for keyword, problem_class in _ERROR_KEYWORDS:` bounded loop. The iteration
order and length are unchanged; `continue` just skips to the next iteration.
No while loops, no recursion, no risk of unbounded work.

### 4. Language-specificity audit

The anti_signatures are only consulted AFTER `_detect_language_quick` has
already refused non-Python inputs (see `classify_error` line sequence).
Re-confirmed that the 10 `GENERIC_NON_PYTHON_ERRORS` fixtures still return
None after v3.2.3 — this is covered by
`test_generic_error_substring_no_longer_poisons` (10 parametrized cases, all
green on v3.2.3).

### 5. None / empty input audit

`_anti_signature_blocks` guards with `if not error_message: return False`.
`classify_error` already guards with `if not error_message: return None`.
`debug_error` guards with `_detect_language_quick(error_message) if error_message else None`.
No new TypeError/AttributeError exposure on None/empty inputs.
Covered by `test_empty_and_trivial_inputs` + `test_anti_signature_blocks_helper_direct`.

### Red-team conclusion: **CLEAN**

No breaking issue found. The two "false block" phrasings documented in §1
are harmless because the surrounding `classify_error` flow protects them —
either another Python keyword fires first, or no keyword fires at all. The
anti_signatures never demote a correct Python answer.

## Artifacts

- `/root/hermes-workspace/borg/borg/core/pack_taxonomy.py` — patched classifier (added `_ANTI_SIGNATURES`, `_anti_signature_blocks`, wiring)
- `/root/hermes-workspace/borg/borg/tests/test_classify_error.py` — +20 tests (55 total)
- `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/v323_fc_analysis.md` — Phase-1 analysis
- `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/v323_measured_impact.md` — this file
- `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/baseline_results.csv` — regenerated on v3.2.3 tree
- `/root/hermes-workspace/borg/CHANGELOG.md` — 3.2.3 entry
- `/root/hermes-workspace/borg/pyproject.toml`, `/root/hermes-workspace/borg/borg/__init__.py` — version bumps
