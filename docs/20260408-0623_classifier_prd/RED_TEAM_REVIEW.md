# RED TEAM REVIEW — `borg debug` Classifier

Target: `borg/borg/core/pack_taxonomy.py` (v3.2.1 wheel on PyPI, 775+ downloads).
Scope: classification correctness, API, coverage, tests, architecture, reputation risk.
Stance: adversarial. Problems only. Fixes are Blue Team's job.
Reproduced on: `/usr/local/bin/borg 3.2.1` using the installed wheel at
`/tmp/borg-firstuser-audit/venv/lib/python3.11/site-packages/borg/`.

Numbers > vibes. Line cites throughout.

---

## 0. TL;DR — Hard Verdict

Production-readiness: **1 / 10**.
One-sentence reason: a 40-entry ordered substring list whose final entry is the
literal word `"Error"` mapped to `schema_drift` means the product ships an
actively-harmful, confidently-wrong answer for the majority of non-Python errors
on the planet, with zero confidence signal, zero language detection, zero
tests, and a renderer that prints `(python)` on a Rust borrow checker error.

Ship-block. Recommend pulling the `debug` marketing language from the README
until this is rewritten.

---

## 1. Severity-Rated Findings

Legend: **CRITICAL** — known-wrong answers or safety risk. **HIGH** — regular
mis-classifications or broken contracts. **MEDIUM** — poor UX / maintenance
debt. **LOW** — polish.

### CRITICAL-1 — `"Error"` substring fallback is a universal schema_drift siphon
- File: `borg/core/pack_taxonomy.py:83`
- Evidence:
  ```python
  # Generic
  ("Error", "schema_drift"),
  ```
  is the LAST entry of `_ERROR_KEYWORDS`. `classify_error()` lower-cases the
  input (line 195) and checks `keyword.lower() in lower` (line 197). So the
  literal 5-character substring `"error"` — present in virtually every error
  string ever written — drops into `schema_drift` with no gating.
- What is wrong: there is no "bare `Error`" semantic. `ENOSPC: ... on device`
  contains `Error`. `rustc error[E0382]` contains `error`. `panic: runtime
  error` contains `error`. `terror`, `mirror`, `TerraformError`, `ReferenceError`,
  `SyntaxError`, `NotImplementedError`, `json decoder error` — all of them
  become `schema_drift` and get a Django makemigrations walkthrough.
- Failure mode: **confidently wrong answer**, the worst possible outcome per
  the PRD's own non-negotiable #8. Developer trust is destroyed on first try.
- Reproducers:
  ```
  $ borg debug "error[E0382]: borrow of moved value"
    → [schema_drift] (python), run python manage.py makemigrations
  $ borg debug "Error: ENOSPC: no space left on device"
    → [schema_drift] (python)
  $ borg debug "panic: runtime error: nil pointer"
    → [schema_drift] (python)
  $ borg debug "ReferenceError: foo is not defined"
    → [schema_drift] (python)
  $ borg debug "NotImplementedError"
    → [schema_drift] (python)
  $ borg debug "TerraformError"
    → [schema_drift] (python)
  ```
  All six verified live on `borg 3.2.1`.

### CRITICAL-2 — No language / framework detection anywhere in the pipeline
- File: `borg/core/pack_taxonomy.py:186-199` (classify), 261-297 (render)
- Evidence: `classify_error` takes a string, does substring scan, returns
  `Optional[str]`. The rendered header is
  `f"[{problem_class}]" + (f" ({framework})" if framework else "")` (line 297),
  and `framework` is read from the matched **pack's** frontmatter — not from
  the input. Every Python seed pack has `framework: python` or
  `framework: django`. So even when classification happens to be correct on a
  non-Python error, the CLI still stamps `(python)` on the output.
- Failure mode: misleading provenance in the output itself. A Go developer
  sees `(python)` next to their panic trace and knows the tool is broken.
- Reproducer:
  ```
  $ borg debug "panic: runtime error: invalid memory address"
  [schema_drift] (python)     ← labelled as python on a Go panic
  ```

### CRITICAL-3 — No confidence score anywhere; no "don't know" path
- File: `borg/core/pack_taxonomy.py:186-199, 387-419`
- Evidence: return type is `Optional[str]`. No float, no struct, no calibrated
  probability. `debug_error()` either routes (line 400-419) or prints the
  canned "No matching problem class found" string (line 402-407). There is no
  "I am 35 % sure this is X" tier and no partial-confidence pack.
- What is wrong: the product's own non-negotiable #8 ("better to say we don't
  know than mis-route") is mechanically impossible — the function cannot
  express uncertainty because its return type cannot carry it. Even when the
  answer is `schema_drift` from the `"Error"` fallback, the CLI has no way to
  distinguish it from the answer to a real Django `OperationalError`.
- Failure mode: confidence-gating cannot be retrofitted without an API break.

### CRITICAL-4 — Taxonomy is Python-only; output brands everything `(python)`
- File: `borg/seeds_data/*.md` (19 files, all `framework: python|django`)
- Evidence: every seed pack's `framework` field is `python` or `django` (e.g.
  `schema-drift.md:6`, `null-pointer-chain.md:6`, `type-mismatch.md:6`). The
  PROBLEM_CLASSES list (`pack_taxonomy.py:87-100`) has 12 entries, 0 of which
  are JS/TS/Rust/Go/Docker/K8s/Java/PHP/C++/Terraform.
- Failure mode: zero recall on ≥ 70 % of the developer ecosystem. React /
  Next.js / Node — the #1 frontend stack on Earth — is a total blind spot, as
  the dogfood report confirmed (0 / 3 matched).
- Reproducers:
  ```
  borg debug "TS2322: Type 'string' is not assignable to type 'number'"
  borg debug "Hydration failed because the initial UI does not match…"
  borg debug "CrashLoopBackOff"
  borg debug "Cannot read properties of undefined (reading 'map')"
  ```
  All four: `No matching problem class found.`

### CRITICAL-5 — Zero tests of `classify_error` in the test suite
- File: `borg/tests/` (2862 tests) — `search_files` for
  `classify_error|pack_taxonomy` returns **0** test files.
- Evidence: the only grep hits for `classify_error` in `tests/` directories
  are the unrelated `borg/dojo/tests/test_session_reader.py` (a different
  classifier for a different module). The ad-hoc root-level scripts
  `/root/hermes-workspace/borg/test_pc_debug.py`,
  `test_pc_debug2.py`, `test_pc_debug3.py`, `test_feedback_trace_wiring.py`
  are one-off debug scripts, not pytest tests.
- Failure mode: any regression to the classifier is undetectable. No CI
  guard on taxonomy coverage, no regression set, no calibration tests.
- Reproducer: `grep -rn classify_error borg/tests/` → 0 hits.

### CRITICAL-6 — Non-negotiable #6 ("don't ship features whose accuracy we haven't measured") is already violated by v3.2.1
- Evidence: `borg debug` is marketed as a killer feature, shipped at
  3.2.1, and has no precision/recall/false-confident-rate measured per
  language. The existing `eval/e1a_seed_pack_validation.py` pre-registers a
  pass criterion of "**≥ 3/5 tasks match to a non-systematic-debugging pack**"
  (line 26) — i.e., a 60 % bar on FIVE Django tasks, and only tests whether
  the pack file exists with all required fields. It does not test
  classification correctness on adversarial inputs. That is not a
  classification eval, it is a schema-validator.
- Failure mode: marketing claim ("structured guidance for any error") is not
  backed by any measurable test. AB's own VERIFY-BEFORE-SHIP rule is broken.

### HIGH-1 — Case-insensitive substring without word boundaries → false positives on English words
- File: `pack_taxonomy.py:195-197`
- Evidence: `keyword.lower() in lower`. The keyword list has
  `"circular"` (line 34), `"migrate"` (line 38), `"applied migrations"` (41),
  `"Error"` (83) — none of which are anchored. Real reproductions:
  ```
  classify_error("circular saw is broken")       -> circular_dependency
  classify_error("the moon circular orbit")      -> circular_dependency
  classify_error("wanted to migrate an elephant") -> migration_state_desync
  classify_error("cobra migrates to warmer climate") -> migration_state_desync
  classify_error("I want to migrate from vim to emacs") -> migration_state_desync
  classify_error("terror in the streets")        -> schema_drift  (terror ⊇ error)
  classify_error("i hate terrorism")             -> schema_drift
  classify_error("what an error-free codebase")  -> schema_drift
  classify_error("InvalidMoveError occurred while chess") -> circular_dependency
  ```
  All verified via direct import of `classify_error` against the installed
  wheel.
- Failure mode: non-error text (logs, doc fragments, shell output, chat
  snippets) mis-classifies to confident advice; trivially exploited by piping
  unrelated stdout into `borg debug`.

### HIGH-2 — First-match-wins ordering bug collapses `ImportError` / `ModuleNotFoundError` distinction incorrectly
- File: `pack_taxonomy.py:57-75`
- Evidence:
  ```python
  ("cannot import name", "import_cycle"),      # line 59
  …
  ("ModuleNotFoundError",  "missing_dependency"),  # line 73
  ("No module named",      "missing_dependency"),  # line 74
  ("ImportError",          "missing_dependency"),  # line 75
  ```
  An `ImportError: cannot import name 'Foo' from 'bar'` (the classic circular
  import symptom) hits `"cannot import name"` at line 59 first and is labelled
  `import_cycle`. Fine, sometimes. But `ImportError: cannot import name 'json'`
  (a genuinely missing symbol in a damaged install) ALSO hits line 59 and is
  also labelled `import_cycle`. Conversely, a plain `ImportError: libstdc++.so.6`
  reaches line 75 → `missing_dependency`. The taxonomy cannot distinguish
  missing-symbol from cycle. This is mis-triage, not just a miss.
- Failure mode: Python users (the supposedly "good" path) get wrong advice
  on the subset where `cannot import name` and `import cycle` diverge.
- Reproducer: `borg debug "ImportError: cannot import name 'foo' from partially initialized module 'bar'"` → `import_cycle` regardless of whether it is actually a cycle.

### HIGH-3 — `TypeError` and `NoneType` compete, and the winner depends on word order
- File: `pack_taxonomy.py:53-55, 77-78`
- Evidence: `"NoneType"` (53) comes BEFORE `"TypeError"` (77). So
  `TypeError: 'NoneType' object has no attribute 'foo'` is routed to
  `null_pointer_chain` — usually correct. But
  `TypeError: Cannot read properties of undefined (reading 'map')` (a JS
  error) matches `TypeError` and is routed to `type_mismatch` → **rendered
  with a Python Django type_mismatch pack** — wrong language, wrong advice.
- Failure mode: every modern React / Node stack trace with `TypeError` gets
  Python-flavoured Django guidance. Reproducer:
  ```
  borg debug "TypeError: Cannot read properties of undefined"
  → [type_mismatch] (python)
  ```

### HIGH-4 — `"Error"` fallback even eats positive-sentiment success messages
- File: `pack_taxonomy.py:83`
- Evidence: `classify_error("json decoder error")` → `schema_drift`.
  `classify_error("no errors at all")` → `schema_drift`. `classify_error("Error at line 42")` → `schema_drift`.
- Failure mode: log lines scraped from grep/tail/stdout are confidently
  mis-routed if they contain the substring "error" anywhere.

### HIGH-5 — Case-insensitivity is inconsistent and breaks on ALL-CAPS / camelCase
- File: `pack_taxonomy.py:195-197`
- Evidence: Input is lower-cased, but so are the keywords. On the surface
  this is symmetric — but the keyword list mixes literal identifiers with
  English phrases (`"circular"`, `"applied migrations"`, `"ImproperlyConfigured"`,
  `"SECRET_KEY"`). A user typing a screen-recorded traceback with `EACCES` or
  `EPERM` will match fine, but `classify_error("TIMEOUT")` → None because the
  list only has `"timed out"` and `"TimeoutError"`. Inconsistent.
- Reproducer (verified): `classify_error("TIMEOUT")` → None;
  `classify_error("we need more timeout love")` → None;
  `classify_error("this has timeOut in it")` → None; but
  `classify_error("my Connection timed out earlier")` → `timeout_hang`.

### HIGH-6 — Silent failure path at `_get_skills_dir() → None`
- File: `pack_taxonomy.py:110-138, 141-150`
- Evidence: if the seeds directory is missing, `_init_cache()` sets
  `_CACHE_INITIALIZED = True` and leaves `_PACK_CACHE = {}`. `debug_error`
  then hits the "Pack for '{problem_class}' found but failed to load" branch
  (line 412-416). The classifier still returns a `problem_class`, so users get
  a system-error message even though the real bug is "the install is broken".
  No warning, no telemetry, no log line.
- Failure mode: support nightmare. Intermittent missing-wheel issues
  present as classifier misses rather than packaging bugs.

### HIGH-7 — Dead / subtly-buggy `_expand_placeholder` function
- File: `pack_taxonomy.py:225-258`
- Evidence: the dict keys are already prefixed with `@` (`"@call_site"`,
  `"@method_return"` …). Line 254 then does
  `f"@{placeholder}" in text` — i.e., it looks for `@@call_site`, which no
  pack contains. The `text == placeholder` branch does work (returns the
  expansion when the entire field is exactly `@call_site`). Line 255
  `text.replace(f"@{placeholder}", placeholder)` is a no-op because the
  double-`@` string isn't in `text`. Empirically verified:
  ```
  _expand_placeholder("@call_site")                   → "the file containing…"
  _expand_placeholder("file: @call_site")             → "file: @call_site"  ← not expanded
  _expand_placeholder("@method_return and @call_site")→ unchanged
  ```
- Failure mode: pack authors cannot use mid-string placeholders, and the
  current Python packs sidestep the bug only because they use concrete paths
  (`django/db/backends/base/schema.py`) instead of `@placeholders`. The feature
  looks live but is broken; silent time bomb.

### HIGH-8 — `problem_description` field is sliced on the first period (line 284)
- File: `pack_taxonomy.py:281-285`
  ```python
  problem_desc = pack.get("problem_signature", {}).get("problem_description", "").split(".")[0]
  ```
- What is wrong: This naïvely truncates at the first `.` in the sentence.
  Any description containing `Django 4.1.` or a file path like
  `django/db/models/__init__.py` gets truncated mid-sentence: the user sees
  `"The Python model and the actual database schema have diverged"` only —
  losing the rest. Fragile.
- Failure mode: malformed output when pack text contains common punctuation.

### HIGH-9 — `(OperationalError, schema_drift)` vs `(OperationalError, migration_state_desync)` conflict resolved by order, not evidence
- File: `pack_taxonomy.py:39-41, 80`
- Evidence: `"no such table"` → `migration_state_desync` (line 39),
  `"OperationalError"` → `schema_drift` (line 80). `"OperationalError: no such column"` contains both: `"no such table"` isn't in the message, so it hits
  `"no such column"` → `schema_drift` (line 45). OK so far. But
  `"django.db.utils.OperationalError: foo"` hits `OperationalError` at line 80
  and is force-classified as `schema_drift`, even when the real cause is a
  stale migration. Ordering hides real semantic ambiguity.
- Failure mode: Django users hit silent mis-triage on the very stack the tool
  was designed for — the Dogfood #1 team actually reported this indirectly.

### HIGH-10 — `debug` CLI accepts empty / single-char input without validation
- File: `borg/cli.py:294-312, 1122`
- Evidence: the argparse `error = nargs="+"` (line 1122) joins into one
  string (line 298), which is then passed blindly to `classify_error`. For
  blank string input (after joining tokens), `classify_error` returns `None`.
  But for an input of `"A"` or `"a"` it still iterates 40 keywords. For any
  input containing "error" (e.g., `"terror"`), you get schema_drift confidently.
- Failure mode: zero sanity-checking; invites accidental advice. A user who
  pipes an unrelated log line via shell quoting can trigger mis-advice.

### HIGH-11 — Global module-level mutable cache with no invalidation
- File: `pack_taxonomy.py:106-107, 141-173`
- Evidence: `_PACK_CACHE: Dict[str, Dict[str, Any]] = {}` module-level,
  initialized once. No TTL, no re-scan. Once loaded in a long-lived process
  (a dev daemon, an IDE extension, a watch loop), pack updates on disk are
  invisible until process restart. The "initialized" flag is set to True
  even when the directory is empty (line 149), so a pack drop-in after a
  bad first start will never be picked up.
- Failure mode: editor-embedded usage sees stale data. Hard-to-debug from
  user POV.

### MEDIUM-1 — `classify_error` is O(N) linear over 40 hand-maintained tuples
- File: `pack_taxonomy.py:32-84`
- Not a perf issue in practice (40 items) but: (a) maintenance nightmare as
  coverage grows, (b) any reshuffling changes ordering semantics, (c) no
  unit-level coverage of which entry matched and why. This IS the god-list
  anti-pattern.

### MEDIUM-2 — Anti-patterns block renders a UTF-8 `✗` glyph unconditionally
- File: `pack_taxonomy.py:356, 360, 297`
- Evidence: hard-coded `"✗"` in string template. Many Windows consoles and
  CI loggers default to cp1252 and crash on write. No stdout encoding check.
- Failure mode: crashes the CLI on `cmd.exe` / CI capture on Windows. Low
  for Linux/Mac users, medium given AB's cross-platform claim.

### MEDIUM-3 — `debug_error` silently swallows FailureMemory exceptions
- File: `borg/cli.py:315-333`
- Evidence: `except Exception: pass` around `FailureMemory.recall(...)`.
  Real errors in the memory layer (DB corruption, schema migration, perm
  issues) are invisible. Good hygiene for end-users, bad hygiene for debug
  observability. No structured logging.

### MEDIUM-4 — `_expand_placeholder`'s replacement dict is hardcoded; pack authors cannot add new placeholders
- File: `pack_taxonomy.py:227-252`
- Failure mode: non-scalable; adding a JS-specific placeholder requires
  shipping a new wheel.

### MEDIUM-5 — `debug_error` rendered output has no machine-readable format
- File: `pack_taxonomy.py:387-419, cli.py:294-335`
- Evidence: output is pure text. No `--json`, no structured schema. The
  feedback-v3 loop cannot bind the rendered answer to the input error
  reproducibly.
- Failure mode: downstream automation (Cursor, Claude Code, CI tools) must
  regex-scrape the output. No stable contract.

### MEDIUM-6 — Eval `e1a_seed_pack_validation.py` classifier is a SECOND, divergent classifier
- File: `borg/eval/e1a_seed_pack_validation.py:126-225`
- Evidence: file defines its own `_PROBLEM_CLASS_DEFINITIONS` dict (line 126)
  with different error_types and keywords than `pack_taxonomy.py`, and its own
  `classify_problem_class(error_text, problem_statement)` function (line 190)
  that returns a confidence score (!). The production classifier does not
  return confidence; the eval classifier does. They are not the same
  algorithm. So the eval does not eval production.
- Failure mode: "pass" on the eval ≠ production correctness. Two classifiers
  to maintain.

### MEDIUM-7 — `e1a` pass bar is absurdly low
- File: `borg/eval/e1a_seed_pack_validation.py:25-29`
- Evidence: "Taxonomy coverage: ≥ 3/5 tasks match to a non-systematic-debugging
  pack". A 5-task sample from one framework, with a 60 % threshold, is not a
  classification benchmark — it is a smoke test.
- Failure mode: rubber-stamp for shipping anything.

### MEDIUM-8 — Taxonomy collisions: `timeout_hang` eats `Connection refused`
- File: `pack_taxonomy.py:69`
- Evidence: `("Connection refused", "timeout_hang")` — `Connection refused`
  is not a timeout, it's a "nothing is listening" error. Different root cause,
  different fix. Conflating them under `timeout_hang` is a category error.
- Failure mode: the pack gives wrong network-debug advice for refusal.

### MEDIUM-9 — `"permission denied"` is both a Linux FS error and an HTTP 403
- File: `pack_taxonomy.py:61-64`
- Evidence: one problem_class for two distinct categories (filesystem ACLs vs
  HTTP authz vs SSH publickey). The rendered pack only knows FS semantics.
- Reproducer: `borg debug "permission denied (publickey)"` (SSH) →
  `permission_denied` (FS). Wrong advice.

### MEDIUM-10 — No telemetry on miss/mis-fire
- File: (whole module) — nothing records classification outcomes.
- Evidence: `v3_integration.record_outcome` is called only from `_cmd_start`
  (cli.py:373-386) and always with `success=True`. There is no path that
  records "classifier returned schema_drift on a non-Python input".
- Failure mode: the marketing claim is uncheckable after release. Drift
  detection is impossible.

### MEDIUM-11 — `problem_signature.framework` vs top-level `framework` duplication
- File: `borg/seeds_data/schema-drift.md:6, 11`
- Evidence: `framework: python` appears twice in the same pack. Data is
  duplicated; drift between them is a silent bug.

### LOW-1 — Docstring lies about paths
- File: `pack_taxonomy.py:12`
- Evidence: `"Seed packs live in borg/skills/*.md"` — they actually live in
  `borg/seeds_data/*.md` (the installed wheel) and `borg/skills/*.md` is the
  dev path only. Doc-code drift.

### LOW-2 — `BORG_DEBUG_KWARGS` is mentioned in the module docstring (line 9) but never defined in the file
- Evidence: top docstring promises a `BORG_DEBUG_KWARGS` symbol, but the module
  does not export one. Either it was removed or was aspirational. Misleading.

### LOW-3 — `debug_error` truncates the error echo at 120 chars (line 294) without indicating truncation beyond `...`
- File: `pack_taxonomy.py:293-295`
- Minor UX annoyance, but matters when users paste stack traces.

### LOW-4 — `"mypy"` substring is a recipe for false positives
- File: `pack_taxonomy.py:78`
- Evidence: any log line containing `mypy` (e.g., a pip install log for
  `mypy-extensions`) classifies as `type_mismatch`.

### LOW-5 — `"TypeError"` but also `"Error"` later — `TypeError` hits first, fine — but `TerraformError`, `TypeInferenceError`, etc. all hit `"Error"` fallback
- Already covered under CRITICAL-1; listing as LOW-5 because the list is fragile
  to adding new specific keywords in the wrong position.

---

## 2. Specific Checklist

### (a) API design flaws
1. `classify_error` returns `Optional[str]` — **no confidence, no tie list, no
   rationale, no language**. An API that cannot express uncertainty cannot be
   made safe. (CRITICAL-3)
2. `debug_error` returns `str`, not a `DebugResult` dataclass — downstream
   consumers must parse plain text. (MEDIUM-5)
3. No `--json` flag in `cli._cmd_debug` despite other commands supporting it.
4. No "explain why you chose this class" path; the user cannot audit the
   classifier without re-running with `--classify` and eyeballing.
5. `load_pack_by_problem_class` returns `None` for both "unknown class" and
   "pack file missing" — two very different error modes collapsed.
6. The contract of `debug_error` mixes classification AND rendering AND
   fallback-message generation — a god function with three responsibilities.
7. No versioning on `_ERROR_KEYWORDS` or the taxonomy; can't A/B two
   classifiers or shadow-eval a new one.
8. `render_pack_guidance` accepts `pack: Dict[str, Any]` — no schema, no
   validation, no TypedDict. Pack authors can silently break renders by
   dropping a field.

### (b) Correctness bugs
1. `"Error"` fallback (CRITICAL-1).
2. Unbounded substring scans over English (HIGH-1).
3. Order-dependent routing of ambiguous keywords (HIGH-2, HIGH-3, HIGH-9).
4. `_expand_placeholder` double-`@` bug (HIGH-7).
5. `problem_description.split(".")[0]` truncation bug (HIGH-8).
6. `Connection refused → timeout_hang` semantic error (MEDIUM-8).
7. FS vs SSH vs HTTP `permission denied` collision (MEDIUM-9).
8. `_init_cache` marks cache initialized even when it loaded 0 packs
   (HIGH-6).
9. Case-sensitivity asymmetry on keywords that look like English words vs
   identifiers (HIGH-5).

### (c) Coverage gaps — languages / frameworks / error families missing
Present today: Python, Django. 12 problem classes, all Python-flavoured.

Missing languages (each a top-10 GitHub language):
- **JavaScript / TypeScript / Node** — zero packs. No `TS2322`, `TS7006`,
  `Cannot read properties of undefined`, `Hydration failed`, `Next.js` RSC
  errors, `ERR_REQUIRE_ESM`, `UnhandledPromiseRejection`, `EBUSY`, `EADDRINUSE`,
  `ENOENT`, etc.
- **Rust** — zero. No `E0382` borrow of moved value, `E0308` type mismatch,
  `E0277` trait bound not satisfied, `cannot find macro`, `cannot find type`,
  lifetime errors, `cargo build` failures, `rustc` panics.
- **Go** — zero. No `panic: runtime error`, `goroutine ... [chan receive]`,
  `invalid memory address or nil pointer`, `cannot use X (type Y) as type Z`,
  `missing go.sum entry`, `undefined: foo`.
- **Java / Kotlin / JVM** — zero. No `NullPointerException`,
  `ClassNotFoundException`, `ClassCastException`, `OutOfMemoryError`,
  `NoClassDefFoundError`, `StackOverflowError`, Gradle/Maven errors.
- **C / C++** — zero. No `segmentation fault`, `undefined reference`,
  `bad_alloc`, `core dumped`, `undefined behavior`, linker errors.
- **Ruby / Rails** — zero.
- **PHP / Laravel** — zero.
- **.NET / C#** — zero.
- **Swift / iOS** — zero.
- **Shell / Bash / POSIX** — zero. No `command not found`, exit-code triage.

Missing infra / ecosystem families:
- **Docker** — no `ImagePullBackOff`, `OOMKilled`, `exited with code 137`,
  `layer not found`, `ENOSPC` on overlay2.
- **Kubernetes** — no `CrashLoopBackOff`, `ErrImagePull`, `FailedScheduling`,
  `PodPending`, `Liveness probe failed`, `OOMKilled`, `Evicted`.
- **CI/CD** — no GitHub Actions, GitLab, Jenkins specifics.
- **Terraform / Pulumi / IaC** — zero.
- **Git** — no `merge conflict`, `fatal: refusing to merge unrelated
  histories`, `rejected non-fast-forward`, `Authentication failed`.
- **Cloud** — no AWS `AccessDenied`, `ResourceNotFoundException`, S3,
  IAM, RDS; no GCP; no Azure.
- **Databases outside Django ORM** — no MySQL, no Postgres outside Django,
  no Oracle ORA-xxxxx codes, no MongoDB, no Redis, no SQLite-direct.
- **SSL/TLS** — no cert expired, `SSL_ERROR`, `x509`.
- **GraphQL, gRPC, REST APIs** — zero.
- **Build tools** — no webpack, vite, esbuild, rollup, parcel, turbopack.

Rough coverage: ~12 problem classes for 1 framework out of the ~150 most-
common dev error families. **< 5 % recall** on the real distribution.

### (d) Testing gaps
1. **Zero** pytest tests on `classify_error` or `debug_error`. Confirmed by
   search (`classify_error|pack_taxonomy` in `borg/tests/` → 0 matches).
2. No adversarial (false-positive) test set. No tests asserting the
   classifier DOES NOT match on "circular saw" or "terror".
3. No per-language regression set.
4. No calibration tests (expected probability vs empirical accuracy).
5. No confusion matrix anywhere.
6. No mutation testing of the keyword table.
7. The existing `e1a` eval tests a DIFFERENT classifier (MEDIUM-6).
8. The existing `e1a` bar is 3/5 on Django tasks (MEDIUM-7).
9. Unrealistic assumption baked in: **"error messages contain their error
   type as a substring"**. That breaks immediately on `ENOSPC`,
   `CrashLoopBackOff`, `E0382`, `panic:`, `ORA-00942`, etc.
10. Unrealistic assumption: **"a 40-entry hand-maintained list will stay
    consistent with 12 pack files"**. No cross-check enforces this.
11. No property-based tests (Hypothesis) generating error strings and
    asserting invariants (e.g. "no non-ASCII-error never matches").
12. No fuzz tests. Paste a 10MB stack trace into `borg debug` — classifier
    runs in O(N·keyword) on lower-cased copy. No DoS guard.

### (e) Architecture smells
1. **Monolithic module** — 420 LOC mixing: taxonomy data, cache, loader,
   renderer, CLI glue, placeholder expander. One file does everything.
2. **Data and code co-located** — `_ERROR_KEYWORDS` is code. A taxonomy should
   be a data artefact with an owner, versioned, testable independently.
3. **No layers** — classification (data-driven) and rendering (view) and
   retrieval (IO) and state (module globals) share one namespace.
4. **Global mutable cache** (HIGH-11).
5. **Two classifiers exist** (prod + eval) — MEDIUM-6.
6. **God function** `debug_error`: classifies, loads, renders, constructs
   fallback strings.
7. **No plugin architecture** — adding a language means editing
   `pack_taxonomy.py` and shipping a new wheel. Non-negotiable #7
   (backwards compatible) becomes harder every addition.
8. **Placeholder expansion coupled to module globals** — not configurable by
   pack authors.
9. **Rendering hardcoded** — no template engine, no i18n hook, no pluggable
   formatter, no JSON renderer.
10. **Circular import risk** — `pack_taxonomy.py` imports `borg` to find the
    install path (line 119), meaning any refactor of `borg/__init__.py`
    that touches init order can break classification.

### (f) Real-world failure modes
1. **False-confident answer** (CRITICAL-1 + CRITICAL-2): Rust / Go / Docker /
   JS users see `(python)` and a Django `makemigrations` walkthrough.
2. **Taxonomy collision**: `Connection refused` ≠ `timeout`, yet same class.
3. **Drift**: seed packs are static; no feedback loop updates keywords even
   though `v3_integration` claims to feed success/failure counts.
4. **Marketing claim risk**: README advertises "structured guidance for any
   error". Third-party Twitter screenshots of Rust-on-Django will be funny,
   and then will not.
5. **Silent break on reinstall**: empty seeds dir → cache marked init → no
   telemetry → users experience "it worked yesterday".
6. **Cross-platform breakage**: non-ASCII glyphs in output (MEDIUM-2).
7. **Supply chain risk**: pack files are YAML + markdown; `yaml.safe_load` is
   OK, but the renderer trusts pack content verbatim. A compromised pack
   can inject ANSI escape sequences, terminal hyperlinks, or worse into the
   CLI output. Not audited anywhere.
8. **Over-broadcast on feedback-v3**: `_cmd_start` (cli.py:373-386) records
   `success=True` unconditionally after `borg start` — so the evidence
   stats displayed in output (line 374 `"EVIDENCE: 22/26 successes (85%)"`)
   are **self-fulfilling vanity metrics**. Worse than no data.

### (g) Academic / state-of-the-art comparison
What real error classifiers look like — and what we are not doing:

| SOTA technique                                | Borg today       |
|-----------------------------------------------|------------------|
| **Drain** (Logpai) — structured log parsing, trees on log templates, deployed in production at MSR, Baidu, Huawei for a decade. Template extraction from variable parts. | Not used. We treat free-text as a bag of characters. |
| **Logpai benchmark** — 16 datasets, published P/R on log template extraction. | No benchmark anywhere. |
| **BERTopic** / sentence-transformers — neural topic models with calibration, cosine-sim nearest-cluster. | Not used. |
| **Regex + confidence** (classic): named captures, multiple patterns with scores, highest-confidence wins. | We have substrings, first-match, no score. |
| **DSPy Signature + ChainOfThought + Assert** — LLM-as-classifier with learned prompts, teacher-student distillation, typed outputs, measurable precision. | Not used. |
| **Calibration** (Platt scaling, isotonic regression) — predicted probability vs empirical accuracy match. | We have no probability at all. |
| **Hierarchical taxonomy** (ICD-style) — coarse-to-fine, with "I don't know" at any level. | Flat 12-class list; no hierarchy. |
| **Ensemble + abstain** — if two classifiers disagree, return "unknown". | Single classifier, no abstain. |
| **Active learning** — mis-classifications go to a review queue. | None. |
| **Human-in-the-loop labelling** — Snorkel / Label Studio / Argilla. | None. |
| **Error-code to canonical URL map** (e.g. `E0382` → rustc book). | None. |
| **Stack trace parsing** — extract language/framework from the shape of the trace (Python `File "...", line N`, JS `at foo (bar.js:1:2)`, Go `goroutine`). | None. |
| **Language ID** (fasttext, cld3) — 176-language classifiers ship at < 5 MB. | None. |
| **Shannon entropy / TF-IDF** — down-weight common words. | None. |
| **SWE-Bench-style patch-level eval** — input error → predicted fix class → accuracy vs real fix. | `e1a` hints at this but only validates structure, not prediction accuracy. |

We are shipping a regex engine from ~2005 as AI-era debug infrastructure.

### (h) Reputation / safety risk
Worst-case dev experience today, reproduced live:
1. User installs `pip install agent-borg`, excited.
2. Runs `borg debug "error[E0382]: borrow of moved value"` on a real Rust
   project.
3. CLI prints a **confident** Django makemigrations walkthrough labelled
   `(python)`, complete with fake "EVIDENCE: 22/26 successes (85%)".
4. User runs `python manage.py makemigrations` in a Rust repo. Nothing
   useful happens.
5. User screenshots it on Hacker News.

Blast radius: every download from now until this is fixed. 775+ existing
installs.

Safety dimension: **there is no guardrail on harmful advice**. The packs
contain shell commands (`python manage.py migrate --fake-initial`,
`ALTER TABLE ... ADD COLUMN ...`, `INSERT INTO django_migrations ...`).
Executing those on the wrong system is destructive. The current classifier
WILL deliver those instructions on non-Django systems under the right
phrasing.

Worst case: a user pipes a prod log with the substring `"Error"` into
`borg debug`, gets `migration_state_desync`, runs `migrate --fake-initial`
on the wrong app, corrupts the Django migrations table.

Reputational risk: HIGH. Safety risk: MEDIUM-HIGH (content is copy-pasteable
destructive SQL).

---

## 3. TOP-10 Fixes (ranked by severity × blast-radius)

Not how to fix — just what MUST change first, in order.

| # | Severity | Blast radius | What must be replaced |
|---|----------|--------------|------------------------|
| 1 | CRIT-1 | everything | Delete the `("Error", "schema_drift")` fallback entry. Period. The single highest-impact change. |
| 2 | CRIT-3 | everything | Return type of `classify_error` must carry confidence + candidates + rationale. Break the API now, deprecate later. |
| 3 | CRIT-2 | every render | Add an explicit language/framework detection step BEFORE taxonomy lookup; render header must reflect inferred language, not pack framework. |
| 4 | CRIT-4 | every non-Python user | Ship at least three non-Python pack families (JS/TS, Rust, Go) + one infra family (Docker/K8s) before re-enabling the `borg debug` marketing. |
| 5 | CRIT-5 | all future regressions | Add a pytest suite with ≥ 200 labelled examples (positive + adversarial) covering 7 languages, wired into CI. Current 0 tests is indefensible. |
| 6 | HIGH-1/2/3 | everyday Python users | Replace substring-in-lower with anchored regex + word boundaries + ordered scoring; stop letting `"migrate"` match "migrate from vim to emacs". |
| 7 | HIGH-8 | render correctness | Kill the `split(".")[0]` description truncation. |
| 8 | HIGH-7 | future pack authors | Rip out or rewrite `_expand_placeholder` — currently dead / subtly buggy. |
| 9 | MEDIUM-6 | eval credibility | Collapse the two classifiers into one source of truth; eval must exercise production code paths. |
| 10 | CRIT-6 | marketing / AB trust | Pull the "works for any error" language from README until measured per-language precision/recall is published. |

Not a design document — but the Blue Team must ensure fixes 1–4 land
together; fixing any one without the others leaves the product broken.

---

## 4. Proposed Adversarial Test Set (≥ 30 examples, 7+ languages)

Each row: (id, input, expected_language, expected_behaviour, rationale).
"expected_behaviour" uses this grammar:
- `MATCH(class, conf≥X)` — must match with at least this confidence
- `ABSTAIN` — must return "unknown" / low-confidence / "I don't know"
- `NEGATIVE` — must not match any class (non-error input)

### Rust (4)
| id | input | expected | rationale |
|----|-------|----------|-----------|
| R1 | `error[E0382]: borrow of moved value: \`x\`` | `MATCH(rust_ownership, ≥0.9)` | rustc error code is the gold signal |
| R2 | `error[E0308]: mismatched types` | `MATCH(rust_type_mismatch, ≥0.9)` | |
| R3 | `error[E0277]: the trait bound \`T: Send\` is not satisfied` | `MATCH(rust_trait_bound, ≥0.85)` | |
| R4 | `panicked at 'index out of bounds: the len is 3 but the index is 5'` | `MATCH(rust_panic, ≥0.8)` | |

### Go (3)
| G1 | `panic: runtime error: invalid memory address or nil pointer dereference` | `MATCH(go_nil_pointer, ≥0.9)` | |
| G2 | `./main.go:14:6: undefined: foo` | `MATCH(go_undefined, ≥0.85)` | |
| G3 | `fatal error: concurrent map writes` | `MATCH(go_concurrent_map, ≥0.85)` | |

### JavaScript / TypeScript / React (6)
| J1 | `TypeError: Cannot read properties of undefined (reading 'map')` | `MATCH(js_undefined_access, ≥0.9)` | must NOT match Python `type_mismatch` |
| J2 | `TS2322: Type 'string' is not assignable to type 'number'` | `MATCH(ts_type_mismatch, ≥0.9)` | |
| J3 | `TS2345: Argument of type '{}' is not assignable to parameter of type 'number'` | `MATCH(ts_type_mismatch, ≥0.85)` | |
| J4 | `Hydration failed because the initial UI does not match what was rendered on the server` | `MATCH(react_hydration_mismatch, ≥0.9)` | |
| J5 | `ReferenceError: foo is not defined` | `MATCH(js_reference_error, ≥0.85)` | |
| J6 | `Error: ENOSPC: no space left on device, watch '/app/src'` | `MATCH(node_enospc_watchers, ≥0.85)` | classic Node file-watcher ENOSPC |

### Python / Django (5 — the "must stay at or above current quality" set)
| P1 | `TypeError: 'NoneType' object has no attribute 'foo'` | `MATCH(null_pointer_chain, ≥0.9)` | current SOTA for borg |
| P2 | `django.db.utils.OperationalError: no such column` | `MATCH(schema_drift, ≥0.9)` | |
| P3 | `django.db.utils.IntegrityError: FOREIGN KEY constraint failed` | `MATCH(missing_foreign_key, ≥0.9)` | |
| P4 | `ImportError: cannot import name 'Foo' from partially initialized module 'bar'` | `MATCH(import_cycle, ≥0.85)` | must distinguish from missing-dep |
| P5 | `ModuleNotFoundError: No module named 'nonexistent_pkg'` | `MATCH(missing_dependency, ≥0.9)` | |

### Java / JVM (3)
| JV1 | `Exception in thread "main" java.lang.NullPointerException at java.util.HashMap.put(HashMap.java:612)` | `MATCH(jvm_npe, ≥0.9)` | |
| JV2 | `java.lang.ClassCastException: class A cannot be cast to class B` | `MATCH(jvm_class_cast, ≥0.85)` | |
| JV3 | `java.lang.OutOfMemoryError: Java heap space` | `MATCH(jvm_oom, ≥0.9)` | |

### C / C++ (2)
| C1 | `Segmentation fault (core dumped)` | `MATCH(c_segfault, ≥0.85)` | |
| C2 | `/usr/bin/ld: undefined reference to \`foo()'` | `MATCH(cpp_linker_undefined, ≥0.85)` | |

### Docker / Kubernetes (4)
| K1 | `CrashLoopBackOff` | `MATCH(k8s_crashloop, ≥0.9)` | no substring; needs canonical code map |
| K2 | `ImagePullBackOff` | `MATCH(k8s_image_pull, ≥0.9)` | |
| K3 | `OOMKilled (exit code 137)` | `MATCH(container_oom, ≥0.9)` | |
| K4 | `Error response from daemon: no space left on device` | `MATCH(docker_disk_full, ≥0.85)` | overlaps Node ENOSPC case |

### Shell / OS (2)
| S1 | `bash: foo: command not found` | `MATCH(shell_command_not_found, ≥0.9)` | |
| S2 | `Permission denied (publickey)` | `MATCH(ssh_auth_publickey, ≥0.85)` | must NOT match FS `permission_denied` |

### Adversarial negatives (must ABSTAIN / return NEGATIVE) (5)
| N1 | `circular saw is broken` | `NEGATIVE` | not an error; must not hit `circular_dependency` |
| N2 | `I want to migrate from vim to emacs` | `NEGATIVE` | |
| N3 | `terror in the streets` | `NEGATIVE` | substring `error` must not fire |
| N4 | `Successfully ran all migrations` | `NEGATIVE` | success log, not error |
| N5 | (empty string) | `NEGATIVE` | |

### Calibration / confidence tests (2)
| CAL1 | `Error at line 42` (ambiguous) | `ABSTAIN` (confidence < 0.5) | must not confidently pick anything |
| CAL2 | `gradle build failed with ClassCastException and OutOfMemoryError` | `MATCH` one of the two, but with `alternatives:` field listing the other | ensures multi-candidate API |

**Total: 36 labelled examples across 9 language/ecosystem families.**
Current classifier will fail nearly all of them. Verified:
- R1, R2: CRITICAL-1 mis-route to `schema_drift`.
- G1: CRITICAL-1 mis-route to `schema_drift`.
- J1: HIGH-3 mis-route to `type_mismatch` (python).
- J4, K1, K2, K3: return `None`.
- K4, J6: CRITICAL-1 mis-route (contain "Error"/"error").
- N1, N2, N3: all HIGH-1 false positives.

Measured baseline expected: **≤ 15 / 36 correct**, **≥ 10 / 36 false confident**,
**0 / 36 with calibrated confidence** (since confidence doesn't exist).

---

## 5. Hard Verdict

**Production-readiness: 1 / 10.**

**One-sentence reason:** A taxonomy driven by a 40-entry ordered
substring list whose last entry is the bare word "Error" mapped to
`schema_drift`, with no language detection, no confidence, zero tests,
and packs for only one framework, is not a classifier — it is a
liability wired to a PyPI download count.

Blocking issues that must land before this feature is marketed again:
CRITICAL-1, CRITICAL-2, CRITICAL-3, CRITICAL-4, CRITICAL-5, CRITICAL-6.
Every other finding is a drop in the ocean until those six land.

Red Team out.
