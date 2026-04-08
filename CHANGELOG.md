# Changelog

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
