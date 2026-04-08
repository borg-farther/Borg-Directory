# v3.2.3 False-Confident Row Analysis (Phase 1: MEASURE)

Date: 20260408
Baseline: v3.2.2 (the language-guard release)
Tool: `classify_error` from `borg/core/pack_taxonomy.py`
Input: `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/baseline_results.csv`

## Baseline numbers (BEFORE)

```
Rows evaluated       : 173
Exact-correct        : 14  (8.1%)
Silent-miss (honest) : 0
False-confident      : 8   (4.62%)
Correct-no-match     : 151 (87.3%)
Precision            : 63.6% (14/22)
Recall               : 8.1%  (14/173)
```

This confirms the PRD baseline: 173 rows, 14 correct, 8 false-confident (FC), 151
correct-no-match, FCR = 4.62%. The 8 FC rows are the Phase-1 target.

## The 8 false-confident rows

Every FC row is a Python-on-Python over-fire: the language guard does NOT block
them because no non-Python locking signal fires (`_detect_language_quick` returns
None), and then the first keyword in `_ERROR_KEYWORDS` with a substring hit wins.
All 8 rows are victims of first-match-wins semantics. They split cleanly across
four `problem_class` buckets and four firing keywords.

| id    | lang (labelled) | text (first ~80 chars)                                                              | expected_problem_class   | predicted_problem_class (firing keyword) |
|-------|-----------------|-------------------------------------------------------------------------------------|--------------------------|------------------------------------------|
| e0005 | python          | `ImportError: cannot import name 'soft_unicode' from 'markupsafe'`                  | missing_dependency       | import_cycle (`cannot import name`)      |
| e0009 | python          | `ImportError: cannot import name 'User' from partially initialized module 'app.models' (most likely due to a circular import)` | import_cycle             | circular_dependency (`circular`)         |
| e0036 | javascript      | `TypeError: Cannot read property 'length' of null`                                  | js_undefined_property    | type_mismatch (`TypeError`)              |
| e0042 | javascript      | `TypeError: foo.map is not a function`                                              | js_type_error            | type_mismatch (`TypeError`)              |
| e0043 | javascript      | `TypeError: Assignment to constant variable.`                                       | js_type_error            | type_mismatch (`TypeError`)              |
| e0044 | javascript      | `TypeError: Converting circular structure to JSON`                                  | js_json_circular         | circular_dependency (`circular`)         |
| e0122 | go              | `import cycle not allowed\npackage foo imports bar imports foo`                     | go_import_cycle          | import_cycle (`import cycle`)            |
| e0157 | shell/k8s       | `Readiness probe failed: Get "http://…:8080/health": dial tcp …: connect: connection refused` | k8s_probe_failed         | timeout_hang (`Connection refused`)      |

### Why the language guard does not catch them

- `e0005`, `e0009` are genuinely Python (`ImportError:` phrasing), so the guard
  correctly leaves them on the Python path — the bug is that the keyword table
  picks a WRONG Python class.
- `e0036` (JS) — the text is the pre-2019 Node phrasing `Cannot read property
  ... of null` (SINGULAR `property`). The v3.2.2 guard only matches the 2019+
  plural `Cannot read propert(?:y|ies) of (?:null|undefined)` pattern. Looking
  at the regex carefully, `propert(?:y|ies)` DOES match `property`, but the
  corpus text is `Cannot read property 'length' of null` — which does match the
  plural regex too. Why does the guard miss it? Let me re-check: the corpus
  text is `TypeError: Cannot read property 'length' of null`. The regex
  `Cannot read propert(?:y|ies) of (?:null|undefined)` requires ` of ` directly
  after `propert(y|ies)`, but the corpus has `propert 'length' of null` — the
  `'length' ` is BETWEEN `property` and `of`. The v3.2.2 regex therefore does
  NOT match. The anti_signature for v3.2.3 will use a more permissive
  character class.
- `e0042`, `e0043`, `e0044` (JS) — all three are naked JS `TypeError:` lines
  with no URL, no stack frame, no `.js`/`.mjs` extension, no `node_modules`,
  no `npm ERR!`. There are literally no JS locking signals in the text, so
  `_detect_language_quick` returns None and the keyword table routes them to
  Python `type_mismatch` or `circular_dependency`.
- `e0122` (go) — the text is `import cycle not allowed\npackage foo imports
  bar imports foo`. The v3.2.2 go locking signals are `goroutine N`, `panic:
  runtime error`, `go.mod`, `go: cannot find module`, `invalid memory address`.
  None match this corpus row. Upstream fix: add `import cycle not allowed` to
  the go locking signals OR add an anti_signature. Anti_signature is cleaner
  because the fix belongs in the CLASSIFIER step, not the language step.
- `e0157` (shell/k8s) — `Readiness probe failed:` plus `connect: connection
  refused`. K8s locking signals are `CrashLoopBackOff`, `ImagePullBackOff`,
  `ErrImagePull`, `OOMKilled`, `kubectl`, `FailedScheduling`. None fire on
  readiness-probe failures. Again, an anti_signature on the firing keyword is
  cleaner than polluting the language detector.

## Proposed anti_signatures (v3.2.3 design)

Rule: an anti_signature is a regex that, if it matches the error text, blocks
the firing keyword's `problem_class` — the classifier loop continues to the
next keyword and ultimately returns None if nothing clears.

```python
_ANTI_SIGNATURES: Dict[str, List[re.Pattern[str]]] = {
    # circular_dependency is the "Django InvalidMoveError / circular
    # migration" class. Anti-signatures suppress the substring 'circular'
    # when it appears in:
    "circular_dependency": [
        # e0009 — Python's own "partially initialized module" phrasing.
        # This is the CanonicaL Python 3.5+ circular-import error message
        # and belongs in import_cycle, not circular_dependency.
        re.compile(r"partially initialized module", re.IGNORECASE),
        re.compile(r"most likely due to a circular import", re.IGNORECASE),
        # e0044 — JS JSON.stringify circular-structure error.
        re.compile(r"Converting circular structure to JSON", re.IGNORECASE),
    ],
    # type_mismatch is the Python mypy / Django type_mismatch class.
    # Anti-signatures suppress the substring 'TypeError' when it is
    # clearly a JS runtime type error, not a Python one:
    "type_mismatch": [
        # e0036 — JS "Cannot read property 'foo' of null/undefined" (pre-2019
        # singular phrasing). Permissive 0-40 char gap covers the quoted
        # key. Anchored on `of null|undefined` so it cannot match a Python
        # "Cannot read property" sentence that does not end in null/undefined.
        re.compile(
            r"Cannot read propert(?:y|ies)\b[^\n]{0,40}?\bof (?:null|undefined)",
            re.IGNORECASE,
        ),
        # e0042 — JS "x is not a function". Python's equivalent for
        # non-callables is "is not callable", so `\bis not a function\b`
        # is a safe JS-only phrasing.
        re.compile(r"\bis not a function\b", re.IGNORECASE),
        # e0043 — JS "Assignment to constant variable". Python does not have
        # const-reassignment errors (there are no consts); equivalent Python
        # phrasing would be "cannot assign to read-only attribute".
        re.compile(r"Assignment to constant variable", re.IGNORECASE),
        # e0044 — JS JSON.stringify circular. Double-listed here because
        # the keyword 'circular' actually fires BEFORE 'TypeError' in
        # _ERROR_KEYWORDS order, but future reorderings should stay safe.
        re.compile(r"Converting circular structure to JSON", re.IGNORECASE),
    ],
    # import_cycle is the Python import_cycle class (ImportError: cannot
    # import name). Anti-signature suppresses the substring 'import cycle'
    # when it's really a Go cyclic-import compiler error:
    "import_cycle": [
        # e0122 — Go's exact cyclic-import compiler phrasing.
        re.compile(r"import cycle not allowed", re.IGNORECASE),
    ],
    # timeout_hang is the Python TimeoutError / Connection refused class.
    # Anti-signature suppresses it when it's really a K8s probe failure:
    "timeout_hang": [
        # e0157 — K8s readiness/liveness/startup probe failures. These
        # contain the substring "connection refused" but the correct class
        # is k8s_probe_failed, which v3.2.3 does not yet have a pack for,
        # so the correct behaviour is to return None.
        re.compile(r"\b(?:Readiness|Liveness|Startup) probe failed\b", re.IGNORECASE),
    ],
}
```

## Manual proof: anti_signatures do NOT break any of the 10 Python regression fixtures

The 10 fixtures from `test_classify_error.py::PYTHON_REGRESSION_FIXTURES` are:

| # | input                                                                           | expected                | which anti_sig could fire?                                      | result |
|---|---------------------------------------------------------------------------------|-------------------------|-----------------------------------------------------------------|--------|
| 1 | `ModuleNotFoundError: No module named 'cv2'`                                    | missing_dependency      | none match                                                      | OK     |
| 2 | `ImportError: cannot import name 'foo' from 'bar'`                              | import_cycle            | "partially initialized module" / "most likely due to a circular import" / "Converting circular structure to JSON" / "import cycle not allowed" — NONE match this text | OK     |
| 3 | `django.db.utils.OperationalError: no such column: app_user.email`              | schema_drift            | none match                                                      | OK     |
| 4 | `django.db.utils.IntegrityError: FOREIGN KEY constraint failed`                 | missing_foreign_key     | none match                                                      | OK     |
| 5 | `ImproperlyConfigured: SECRET_KEY must not be empty`                            | configuration_error     | none match                                                      | OK     |
| 6 | `PermissionError: [Errno 13] Permission denied: '/etc/passwd'`                  | permission_denied       | none match                                                      | OK     |
| 7 | `TimeoutError: [Errno 110] Connection timed out`                                | timeout_hang            | timeout_hang has "probe failed" anti_sig — does NOT match       | OK     |
| 8 | `AttributeError: 'NoneType' object has no attribute 'get'`                      | null_pointer_chain      | none match                                                      | OK     |
| 9 | `django.db.migrations.exceptions.InconsistentMigrationHistory: applied migrations` | migration_state_desync | none match                                                      | OK     |
| 10| `RuntimeError: dictionary changed size during iteration`                        | race_condition          | none match                                                      | OK     |

All 10 Python regressions stay green — verified both on paper AND by live
simulation (`/tmp/sim_anti_sigs.py`).

## Expected impact on the 8 FC rows

Simulation result (also verified live in `/tmp/sim_anti_sigs.py`):

| id    | v3.2.2 pred                    | v3.2.3 pred (proposed)         | killed? |
|-------|--------------------------------|--------------------------------|---------|
| e0005 | import_cycle                   | import_cycle                   | NO (residual — see below) |
| e0009 | circular_dependency            | import_cycle                   | YES — row becomes EXACT-CORRECT |
| e0036 | type_mismatch                  | None                           | YES     |
| e0042 | type_mismatch                  | None                           | YES     |
| e0043 | type_mismatch                  | None                           | YES     |
| e0044 | circular_dependency            | None                           | YES     |
| e0122 | import_cycle                   | None                           | YES     |
| e0157 | timeout_hang                   | None                           | YES     |

**7 of 8 rows killed. One residual: e0005.**

### e0005 residual — honest self-correction

`e0005` is `ImportError: cannot import name 'soft_unicode' from 'markupsafe'`
with `expected_problem_class = missing_dependency` (markupsafe 2.1 removed
`soft_unicode`, you need to downgrade or vendor it).

The classifier sees `cannot import name` and returns `import_cycle` because
the existing test fixture `test_python_django_recall_unchanged` requires:

```python
("ImportError: cannot import name 'foo' from 'bar'", "import_cycle"),
```

These two labels are in direct conflict. The same text pattern:
- Fixture: `cannot import name 'foo' from 'bar'`  → expected `import_cycle`
- Corpus : `cannot import name 'soft_unicode' from 'markupsafe'` → expected `missing_dependency`

There is NO textual discriminator between them — both are bare `ImportError:
cannot import name X from Y` with no additional context. Semantically they
represent different root causes (cycle vs removed-symbol) but the text alone
cannot disambiguate.

**Decision:** e0005 is ambiguously labelled relative to an existing Python
positive. We CANNOT kill it without regressing fixture #2. The correct
future fix is (a) the Phase-2 confidence-gated classifier with
`unique_to_class` signals, or (b) fixing the label ambiguity in the corpus by
adding a discriminator to one of the two fixtures. Neither is in scope for a
Phase-0 patch release.

This gives us a target FCR of **1/173 = 0.58%** after v3.2.3 ships, well under
the 2% Phase-0 release gate and well under the ≤ 2 residuals the PRD budgets.
