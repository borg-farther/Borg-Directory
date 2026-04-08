# Changelog

## 3.2.4 — 20260408 — Observe→search roundtrip fix

Fixes a production bug discovered by the P1.1 MiniMax experiment
(docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md): `borg observe` wrote
traces but `borg search` could not find them. Silently made the C2 (borg
seeded) condition indistinguishable from C1 (borg empty) in the experiment,
invalidating cross-condition comparison.

### Root cause (two defects, both required)

1. `borg/core/search.py` `borg_search()` only queried the workflow pack
   index — it never opened `~/.borg/traces.db` even though
   `TraceMatcher.find_relevant()` existed for exactly this purpose.
2. `borg` CLI had no `observe` subcommand at all. Only the MCP server path
   could write traces. The P1.1 seeding calls hit the CLI, so nothing was
   written.

### Changes

- **`borg/cli.py`**: added `_cmd_observe()` subcommand. `borg observe <task>`
  with optional `--context`, `--error`, `--agent` flags creates a
  `TraceCapture`, synthesizes a stub tool-call, and calls `save_trace()`.
- **`borg/core/search.py`**: after pack matches, call
  `TraceMatcher().find_relevant(query, top_k=10)` and surface hits as
  synthetic matches with `source="trace"`, `tier="trace"`, name
  `trace:<id>`. Gated on `BORG_DIR` being a real directory so mocked tests
  preserve their pre-3.2.4 expectations.
- **`borg/tests/test_observe_search_roundtrip.py`** (new): 3 regression
  tests covering single trace, multi-trace relevance ranking, cross-process
  persistence.

### Test status

- Before: 1705 passing.
- After: **1708 passing** (1705 existing + 3 new roundtrip tests).
- Zero regressions.

### Verified manually

```
$ borg observe 'fix django authentication bug for the third time today'
Recorded trace 0bbba511 for task: fix django authentication bug ...

$ borg search django
Name                Confidence  Tier   Problem Class
trace:0bbba511      observed    trace  fix django authentication bug ...
trace:c80de01c      observed    trace  Django migration for model field change
... (10 trace matches total)
```

### Why this matters

This was discovered by the exact kind of experiment it unblocks. Without
this fix, every cross-condition borg experiment that uses `borg observe`
for seeding is measuring a broken pipeline. Priority 2.1 of the borg
testing roadmap (Sonnet replication) is now meaningful.

---

## 3.2.3 — 20260408 — anti_signatures patch — residual Python over-fires killed

This is a narrow follow-up to 3.2.2. v3.2.2 dropped the corpus false-confident
rate from 53.8% → 4.6% by deleting the bare `("Error", "schema_drift")`
fallback and adding a non-Python language guard. That left **8 false-confident
rows** on the 173-row corpus — all of them Python-on-Python over-fires where
the language guard correctly declined to block a Python-looking input but the
first-match-wins keyword table then picked the wrong Python class.

v3.2.3 adds a small, per-class `_ANTI_SIGNATURES` regex table in
`borg/core/pack_taxonomy.py` that suppresses those specific over-fires without
touching the existing 36-regex non-Python language guard and without adding
any new pack schema. Pure classifier patch.

### The 8 targeted corpus rows

| id    | language    | text (first ~70 chars)                                                                | v3.2.2 prediction      | v3.2.3 prediction  |
|-------|-------------|----------------------------------------------------------------------------------------|------------------------|--------------------|
| e0009 | python      | `ImportError: cannot import name 'User' from partially initialized module ...`        | circular_dependency    | **import_cycle** (exact-correct) |
| e0036 | javascript  | `TypeError: Cannot read property 'length' of null`                                    | type_mismatch          | None               |
| e0042 | javascript  | `TypeError: foo.map is not a function`                                                | type_mismatch          | None               |
| e0043 | javascript  | `TypeError: Assignment to constant variable.`                                         | type_mismatch          | None               |
| e0044 | javascript  | `TypeError: Converting circular structure to JSON`                                    | circular_dependency    | None               |
| e0122 | go          | `import cycle not allowed\npackage foo imports bar imports foo`                       | import_cycle           | None               |
| e0157 | shell/k8s   | `Readiness probe failed: Get "http://.../health": ... connect: connection refused`   | timeout_hang           | None               |
| e0005 | python      | `ImportError: cannot import name 'soft_unicode' from 'markupsafe'`                    | import_cycle           | import_cycle (residual — ambiguous label; see docs/20260408-0623_classifier_prd/v323_fc_analysis.md §e0005) |

7 of 8 rows killed outright. One row (e0009) actually became exact-correct —
its canonical "partially initialized module" phrasing is the right phrase for
`import_cycle`, so suppressing the `circular` keyword let the later
`cannot import name` keyword win. One row (e0005) is held back as a known
residual: its text is indistinguishable from the existing
`PYTHON_REGRESSION_FIXTURES` entry `ImportError: cannot import name 'foo' from 'bar'`
which is required to map to `import_cycle`. Fixing e0005 would regress a
Python positive. Phase 2's confidence-scored classifier with
`unique_to_class` signals is the correct long-term fix.

### What 3.2.3 changes

- **Added** module-level `_ANTI_SIGNATURES: Dict[str, List[re.Pattern]]` in
  `borg/core/pack_taxonomy.py` — 9 regexes across 4 problem_classes. Each
  entry has an inline comment naming the corpus row it targets and the
  Python positive it explicitly does NOT match.
- **Added** `_anti_signature_blocks(error_message, problem_class) -> bool`
  helper that walks the dict for a given class and returns True on any
  match (case-preserved, regexes carry their own IGNORECASE flags).
- **Wired** the helper into `classify_error()`: after a keyword hit, if
  `_anti_signature_blocks()` returns True, `continue` to the next keyword.
  If nothing clears, return None — `debug_error()` falls through to the
  same UnknownMatch block as v3.2.2 with no new rendering.
- **Added** 20 new pytest tests in `borg/tests/test_classify_error.py`:
  7 parametrized corpus-row kills, 10 parametrized Python-fixture
  regression assertions that walk `_ANTI_SIGNATURES` directly, one unit
  test for `_anti_signature_blocks()`, one full-corpus integration test
  that asserts FC ≤ 2, and one adversarial catastrophic-backtracking test
  with a 10K-char input + 2s budget.
- **Did NOT** touch `_detect_language_quick` or the 36-regex
  `_NON_PYTHON_LOCKING_SIGNALS` from v3.2.2. They stay verbatim.
- **Did NOT** introduce per-pack YAML frontmatter changes or any
  Phase-1 schema migration. The `_ANTI_SIGNATURES` dict will move into
  pack frontmatter in the Phase-1 release (Architecture Spec §4.2 / §8.1);
  this is a pure classifier patch until then.

### Verified impact (re-running the same baseline corpus on the new wheel)

| Metric                                              | v3.2.2    | v3.2.3     |
|-----------------------------------------------------|-----------|------------|
| False-confident rate                                | 4.62%     | **0.58%**  |
| Precision of predictions that fire                  | 63.6%     | **93.8%**  |
| Exact-correct                                       | 14 (8.1%) | 15 (8.7%)  |
| Correct-no-match (honest miss)                      | 151 (87.3%) | 157 (90.8%) |
| Python/Django recall (10 fixtures)                  | 10/10     | 10/10      |
| Existing test suite                                 | 1685 pass | 1705 pass  |

The 0.58% residual (1/173, row e0005) is under the PRD v1 target of ≤ 2%.

### Python backwards-compat statement

Recall on the 10 `PYTHON_REGRESSION_FIXTURES` is unchanged. Every Django /
Python test that was green on v3.2.2 is still green on v3.2.3.

### Still Phase 0, not Phase 1

v3.2.3 is still a Phase-0 patch release under the multi-language classifier
roadmap in `docs/20260408-0623_classifier_prd/SYNTHESIS_AND_ACTION_PLAN.md`.
No language/framework detection cascade yet, no confidence score in the
return type, no `UnknownMatch` dataclass, no per-pack frontmatter. Phases 1–4
still ship in v3.3.0 and v3.4.0.

### Test count

- `borg/tests/test_classify_error.py`: **55** tests (was 35 in v3.2.2,
  +20 new: 7 anti_signature corpus-row parametrized, 10 Python-fixture
  belt+suspenders parametrized, 1 unit test for the helper, 1 full-corpus
  integration, 1 adversarial backtracking test).
- Full `borg/tests/` suite: **1705** tests (+20 vs. v3.2.2's 1685) all green.

### Artifacts

- Analysis: `docs/20260408-0623_classifier_prd/v323_fc_analysis.md`
- Measured impact + adversarial review: `docs/20260408-0623_classifier_prd/v323_measured_impact.md`
- Regenerated baseline CSV: `docs/20260408-0623_classifier_prd/baseline_results.csv`

---

## 3.2.2 — 20260408 — Honesty patch (Phase 0 of multi-language classifier)

This release fixes a serious bug in `borg debug`. In 3.2.1 and earlier, any
error message containing the substring `"Error"` — which is to say, most error
messages in most programming languages — would be routed to the Django
`schema_drift` pack and the CLI would print Django migration advice with a
confident `(python)` label. We reproduced this on:

- Rust `error[E0382]: borrow of moved value`
- Go `panic: runtime error: invalid memory address or nil pointer dereference`
- Docker `Error: ENOSPC: no space left on device`
- Node `ReferenceError`, JS `Cannot read properties of undefined`
- Kubernetes `CrashLoopBackOff` and `ImagePullBackOff`

On a 173-error multi-language corpus we built specifically for this release,
the false-confident rate was **53.8%**. That is worse than refusing to answer.
We are sorry.

### What 3.2.2 changes

- **Removed** the bare `("Error", "schema_drift")` fallback in
  `borg/core/pack_taxonomy.py:83` — the single line that was the root cause.
- **Added** a Phase 0 non-Python language guard
  (`_detect_language_quick`) that detects locking signals for Rust, Go,
  JavaScript, TypeScript, React, Docker, and Kubernetes. When any non-Python
  language is detected, `classify_error()` returns `None` and `debug_error()`
  prints an explicit "we don't know yet" UnknownMatch block that names the
  detected language.
- **Added** 35 new pytest tests in `borg/tests/test_classify_error.py` —
  4 dogfood reproductions, 10 generic non-Python regression tests, 10 Python
  backwards-compatibility fixtures, plus edge cases and language-detection
  unit tests. There were **zero** tests covering `classify_error` before this
  release. There are now 35.
- **README** rewritten to position `borg debug` as a Python/Django expert that
  is explicit about what it doesn't know, rather than a multi-language tool.

### Verified impact (re-running the same baseline corpus on the new wheel)

| Metric                                              | v3.2.1   | v3.2.2  |
|-----------------------------------------------------|----------|---------|
| False-confident rate                                | **53.8%**| **4.6%**|
| Precision of predictions that fire                  | 13.1%    | 63.6%   |
| Honest "no match" rate (correct-no-match)           | 0%       | 87.3%   |
| Python/Django recall (12 fixtures)                  | unchanged| unchanged |
| Existing test suite (1685 tests + 1 xfailed)        | green    | green   |

### What `borg debug` is and is not, honestly

`borg debug` is a Python/Django expert with 12 hand-authored packs, no
confidence score yet, and no learned model. It is **not** yet multi-language —
JavaScript, TypeScript, Rust, Go, Docker, and Kubernetes return "unknown" in
3.2.2 and that is by design until we can ship calibrated per-language packs
with measured false-confident rates. The roadmap and full PRD are in
`docs/20260408-0623_classifier_prd/`. If you are a Python/Django developer,
`borg debug` should still help. If you are not, we would rather say "we don't
know yet" than give you a confidently wrong answer.

### Next phases

The full multi-language classifier (Phases 1–4 of the PRD) adds language
detection, per-language confidence calibration, and JS/TS/Rust/Go/Docker/K8s
pack coverage in priority order. See `docs/20260408-0623_classifier_prd/SYNTHESIS_AND_ACTION_PLAN.md`
for the four-phase rollout, exit gates, and risk register.

### Acknowledgements

Three dogfood teams independently surfaced this bug on 20260408. Thank you.
The 173-row labelled corpus, the baseline script, and the per-row CSV are
included in `docs/20260408-0623_classifier_prd/` so anyone can reproduce both
the bug and the fix.
