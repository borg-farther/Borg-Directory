# BORG DEBUG CLASSIFIER — ARCHITECTURE SPEC

**Team:** BLUE (Architects)
**Date:** 2026-04-08 06:30Z
**Status:** DRAFT v1 — for AB review
**Target package:** `agent-borg` v3.2.1 → v3.3.0
**Owners:** core/pack_taxonomy.py, core/classifier/* (new)

---

## 1. PROBLEM STATEMENT

`borg debug "<error>"` is the marketed killer feature of `agent-borg`, but its
classifier is a 53-line ordered substring table (`borg/core/pack_taxonomy.py`
lines 32–84) whose final entry is the bare token `"Error"`. Because virtually
every error message in every language contains the substring `Error`, the
classifier short-circuits to `schema_drift` and tells Rust/Docker/JS/TS users
to run `python manage.py makemigrations`. There is no language detection, no
framework detection, no confidence score, no "I don't know" path, and no
telemetry on misclassification — confidently wrong answers are silent. We need
to replace this with a multi-language, confidence-gated classifier that (a)
preserves the existing Python/Django quality bar, (b) refuses to answer rather
than mis-route when uncertain, and (c) can grow to JS/TS/Rust/Go/Docker/K8s
without architectural rework.

---

## 2. GOALS / NON-GOALS

### Goals (v1, must)
- **G1.** Eliminate the bare-`"Error"` fallback. No untyped wildcard match exists in v1.
- **G2.** Detect language (Python, JS, TS, Rust, Go, Docker, K8s, cross-language) before any pack scoring.
- **G3.** Return a calibrated confidence score in `[0,1]` for every classification.
- **G4.** Refuse to answer ("UnknownMatch" path) when `confidence < τ` and render an actionable "we don't know yet, here's how to help us" CLI block.
- **G5.** Backwards compatible: `classify_error(str) -> Optional[str]` keeps its signature; Python/Django seed packs work unchanged with no quality regression.
- **G6.** New pack schema is a strict superset of today's frontmatter (additive only).
- **G7.** Ship a measurement harness that reports per-language **precision, recall, F1, ECE, and FCR**, and gate releases on FCR.
- **G8.** Offline-able. The classifier must work with no network and no LLM dependency on the hot path.

### Goals (v1, should)
- **G9.** New seed packs for JS/TS, Rust, Go, Docker, K8s in Phase 3.
- **G10.** Telemetry hook (opt-in, local-first) for misclassification feedback.
- **G11.** Explainable: every classification returns a list of features that fired and their weights.

### Non-Goals (v1, will not)
- **NG1.** No fine-tuned ML model in the wheel. No PyTorch/TF dependency.
- **NG2.** No remote LLM call on the `borg debug` hot path. (Optional, opt-in "explain harder" path can call an LLM in Phase 4+, but not the default.)
- **NG3.** No deep stack-trace parsing for v1 — we treat the input as a flat string. (Phase 4.)
- **NG4.** No multi-lingual error messages (i18n) in v1. ASCII/English only.
- **NG5.** No automatic pack synthesis from telemetry in v1. Humans review every new pack.
- **NG6.** No cross-error correlation ("you also got error Y two seconds ago"). Single-error in, single-classification out.

---

## 3. FORMAL MODEL

### 3.1 Inputs

```
ClassifyInput := {
    error:      str           # required, raw error text or short traceback
    hint:       LanguageHint? # optional, e.g. "python" | "rust" | None
    file_path:  str?          # optional, file the user was editing (for ext hint)
    framework:  str?          # optional explicit framework hint
}
```

`error` is treated as opaque text. We do **not** parse it as structured JSON
or as a Python traceback object — that brittleness is what got us here.

### 3.2 Outputs

```
ClassificationResult := Match | UnknownMatch

Match := {
    problem_class:  str        # one of PROBLEM_CLASSES (per-language allowed)
    language:       str        # 'python' | 'javascript' | ... | 'cross-language'
    framework:      str|None   # 'django' | 'react' | ... | None
    confidence:     float      # in [0, 1], calibrated
    explanation:    Explanation
    pack_id:        str|None   # FK into pack cache
    score_raw:      float      # pre-calibration raw score (for debugging)
}

UnknownMatch := {
    confidence:     float           # max raw score < τ
    top_k:          list[Candidate] # k=3 best partial matches with their scores
    detected_lang:  str|None
    diagnostics:    Diagnostics     # what we *did* see, what we wish we'd seen
}

Explanation := {
    features_fired: list[Feature]   # [(name, weight, source_regex)]
    language_signal: LanguageSignal # what locked the language
    framework_signal: FrameworkSignal|None
    competing_classes: list[(problem_class, score)]  # top 3
}

Diagnostics := {
    tokens_seen:        list[str]   # n-grams we extracted but didn't recognise
    near_miss_pack:     str|None    # closest pack by raw score
    near_miss_score:    float
    threshold:          float       # τ at time of decision
    suggested_action:   str         # human-readable next-step advice
}
```

### 3.3 Score function S(error, pack)

For each pack `p` we compute a score in `[0, 1]`:

```
S(e, p) = sigmoid(
        w_lang  * I[lang(e) == p.language]
      + w_fw    * I[framework(e) ∈ p.frameworks]
      + w_sig   * Σ_i ( weight_i * regex_hit(p.error_signatures[i], e) )
      + w_uniq  * Σ_i ( unique_to_class_i ? bonus_i : 0 )
      + w_ext   * I[file_ext(file_path) ∈ p.file_extensions]
      - w_anti  * Σ_j ( regex_hit(p.anti_signatures[j], e) )
      - w_xlang * I[lang(e) ≠ p.language ∧ p.language ≠ 'cross-language']
)
```

Where:
- `I[·]` is the indicator function.
- `sigmoid(x) = 1 / (1 + exp(-x))` keeps the output in `[0,1]`. Uncalibrated.
- Default weights: `w_lang=2.5, w_fw=1.5, w_sig=1.0, w_uniq=2.0, w_ext=0.5, w_anti=2.0, w_xlang=4.0`.
- **`w_xlang=4.0` is large on purpose** — a Rust error matched to a Python pack
  must be virtually impossible. This is the antidote to today's bug.

`regex_hit(rx, e)` returns `1` if the compiled regex matches anywhere in `e`,
else `0`. (We deliberately do **not** count multiple hits — one signature firing
once is enough; counting hits over-rewards verbose tracebacks.)

The chosen problem class is `argmax_p S(e, p)`. Confidence is the calibrated
output of `S(e, p*)` after Phase 2 isotonic regression (see §6).

### 3.4 Unknown handling (the τ gate)

```
def classify(e, hint=None) -> ClassificationResult:
    lang = detect_language(e, hint, file_path)
    candidates = [p for p in packs
                  if p.language == lang or p.language == 'cross-language']
    if not candidates:
        return UnknownMatch(
            confidence=0.0,
            top_k=[],
            detected_lang=lang,
            diagnostics=Diagnostics(
                suggested_action=f"borg has no packs for {lang} yet. "
                                 "Run `borg debug --teach` to contribute one."
            ),
        )
    scored = sorted(((p, S(e,p)) for p in candidates), key=lambda x: -x[1])
    best, best_score = scored[0]
    if best_score < τ(lang):
        return UnknownMatch(
            confidence=best_score,
            top_k=scored[:3],
            detected_lang=lang,
            diagnostics=build_diagnostics(e, scored, τ(lang)),
        )
    return Match(
        problem_class=best.problem_class,
        language=lang,
        framework=detect_framework(e, lang),
        confidence=calibrate(best_score, lang),
        explanation=build_explanation(e, best, scored[:3]),
        pack_id=best.id,
        score_raw=best_score,
    )
```

`τ(lang)` is **per-language** because calibration data density varies wildly:
Python has 12 packs and SWE-bench coverage; Rust will start with 4 packs and no
labelled data, so its τ must start higher (we reject more aggressively until
we earn the right to be confident).

---

## 4. PRINCIPLED TAXONOMY

### 4.1 Per-language taxonomy

A `problem_class` is a `(language, class_name)` pair. Classes with the same
name across languages are different rows in the catalogue, because their
investigation trail and resolution sequence are language-specific. The
v1 catalogue (intentionally small):

| Language       | problem_class           | Pre-condition (signal)                          | Post-condition (action class)            |
|----------------|-------------------------|--------------------------------------------------|------------------------------------------|
| python         | null_pointer_chain      | `'NoneType'`, `AttributeError`                   | upstream-trace, fix producer             |
| python         | migration_state_desync  | `OperationalError`, `no such table`, Django path | `migrate --fake`, register manually      |
| python         | schema_drift            | `no such column`, `OperationalError` + ORM       | `makemigrations`, manual ALTER           |
| python         | import_cycle            | `cannot import name`, `circular import`          | break cycle, lazy import                 |
| python         | missing_dependency      | `ModuleNotFoundError`, `No module named`         | install package, fix venv                |
| python         | type_mismatch           | `TypeError` + `expected ... got`                 | fix call site, add coercion              |
| python         | configuration_error     | `ImproperlyConfigured`, `SECRET_KEY`             | fix settings.py / env                    |
| python         | permission_denied       | `PermissionError`, `EACCES`, `EPERM`             | chmod / sudo / fix process user          |
| python         | timeout_hang            | `TimeoutError`, `Connection refused`             | retry/backoff, check service             |
| python         | race_condition          | `dictionary changed size during iteration`      | lock/snapshot, async semantics           |
| python         | circular_dependency     | `InvalidMoveError`, `dependency cycle`           | reorder migrations                       |
| python         | missing_foreign_key     | `FOREIGN KEY constraint failed`, `IntegrityError`| add FK, fix delete order                 |
| javascript     | null_or_undefined       | `Cannot read propert(y\|ies) of (null\|undefined)` | optional chaining, nullish coalesce      |
| javascript     | module_not_found        | `Cannot find module`, `MODULE_NOT_FOUND`         | npm install, fix path                    |
| javascript     | unhandled_promise       | `UnhandledPromiseRejection`                      | add `.catch`, await                      |
| javascript     | enospc                  | `ENOSPC`, `no space left on device`              | clean disk, fix watcher limit            |
| typescript     | type_assignment         | `TS2322`, `is not assignable to type`            | fix type, narrow union                   |
| typescript     | property_does_not_exist | `TS2339`, `Property '.*' does not exist on type` | declare prop, fix interface              |
| typescript     | possibly_undefined      | `TS18048`, `is possibly 'undefined'`             | guard, narrow                            |
| react          | hydration_mismatch      | `Hydration failed`, `did not match`              | match SSR/CSR markup, mark client-only   |
| react          | invalid_hook_call       | `Invalid hook call`, `Hooks can only be called`  | move hook to component, fix dup React    |
| rust           | borrow_of_moved_value   | `error\[E0382\]`, `borrow of moved value`        | clone, ref, restructure                  |
| rust           | lifetime_mismatch       | `error\[E0623\]`, `lifetime mismatch`            | annotate lifetimes                       |
| rust           | trait_not_satisfied     | `error\[E0277\]`, `the trait .* is not implemented` | impl trait, derive                       |
| rust           | mismatched_types        | `error\[E0308\]`, `mismatched types`             | coerce, fix signature                    |
| go             | nil_pointer_dereference | `runtime error: invalid memory address`, `nil pointer dereference` | nil check, init               |
| go             | undefined_symbol        | `undefined: \w+`                                 | import package, declare                  |
| go             | goroutine_leak          | `goroutine .* \[chan send\]`, `fatal error: all goroutines are asleep` | close chan, ctx cancel       |
| docker         | no_space                | `no space left on device`, `ENOSPC`              | `docker system prune`                    |
| docker         | image_not_found         | `image .* not found`, `manifest unknown`         | `docker pull`, fix tag                   |
| docker         | port_already_in_use     | `port is already allocated`, `address already in use` | free port, change mapping             |
| kubernetes     | image_pull_backoff      | `ImagePullBackOff`, `ErrImagePull`               | check creds, fix image ref               |
| kubernetes     | crash_loop_backoff      | `CrashLoopBackOff`                               | read pod logs, fix entrypoint            |
| kubernetes     | oomkilled               | `OOMKilled`, `exit code 137`                     | bump memory limit, fix leak              |
| cross-language | permission_denied       | `EACCES`, `EPERM`, `Permission denied`           | chmod, sudo                              |
| cross-language | enospc                  | `ENOSPC`, `no space left on device`              | free disk                                |
| cross-language | dns_resolution          | `getaddrinfo`, `EAI_AGAIN`, `ENOTFOUND`          | check /etc/resolv, retry                 |
| cross-language | tls_cert_invalid        | `unable to verify the first certificate`, `x509: certificate signed by unknown authority` | install CA   |

Pre-conditions are necessary signals to **consider** the class; post-conditions
are the action classes the resolution sequence belongs to. A class that has no
pre-condition fired cannot win (its raw score will be < τ).

### 4.2 Minimum viable cross-language pack schema (additive)

This is a strict superset of today's frontmatter. Every existing field is
preserved verbatim. The new fields are optional for v1 packs that already
exist (they default sensibly), but **required** for any new pack accepted in
Phase 3+.

```yaml
---
type: workflow_pack          # unchanged
version: '1.1'                # bump from 1.0 to signal new optional fields
id: borrow-of-moved-value     # unchanged
problem_class: borrow_of_moved_value  # unchanged

# === NEW REQUIRED FIELDS ===
language: rust                # NEW, required. one of: python|javascript|typescript|rust|go|docker|kubernetes|cross-language
frameworks: []                # NEW, list[str]. e.g. ['actix', 'tokio']. [] = framework-agnostic.
file_extensions: ['.rs']      # NEW, list[str]. boosts score when file_path matches.

# === NEW SCORING FIELDS ===
error_signatures:             # NEW. ordered list of regex+weight pairs.
  - regex: 'error\[E0382\]'
    weight: 1.0
    unique_to_class: true     # if true, score gets the w_uniq bonus when this fires
  - regex: 'borrow of moved value'
    weight: 0.8
    unique_to_class: true
  - regex: 'value used here after move'
    weight: 0.4
    unique_to_class: false

anti_signatures:              # NEW. negative evidence — penalises score if matched.
  - regex: 'NoneType'         # python-only token; if present, this is not a Rust error
  - regex: 'error\[E0277\]'   # different rust error code

# === EXISTING FIELDS (unchanged from v1.0) ===
problem_signature:
  error_types:                # kept for backwards compat with classify_error
    - E0382
  framework: rust             # kept; mirrors top-level `language` for legacy code
  problem_description: ...
root_cause:
  category: ownership_violation
  explanation: ...
investigation_trail:          # unchanged shape
  - file: '@offending_function'
    position: FIRST
    what: ...
    grep_pattern: ...
resolution_sequence:          # unchanged shape
  - action: clone_value
    command: 'let y = x.clone();'
    why: ...
anti_patterns:                # unchanged shape
  - action: '...'
    why_fails: '...'
evidence:                     # unchanged shape
  success_count: 0
  failure_count: 0
  success_rate: 0.0
  uses: 0
  avg_time_to_resolve_minutes: 0.0
provenance: 'Seed pack v1 | rust | 2026-04-08'
---
```

**Backwards compatibility rule:** for legacy v1.0 packs that lack the new
fields, the loader synthesises them from existing data:

| New field         | Synthesised from                                               |
|-------------------|----------------------------------------------------------------|
| `language`        | `problem_signature.framework` mapped via `_FRAMEWORK_TO_LANG`  |
| `frameworks`      | `[problem_signature.framework]` if non-empty                   |
| `file_extensions` | `_LANG_TO_DEFAULT_EXT[language]`                               |
| `error_signatures`| derived from `problem_signature.error_types` with `weight=1.0` |
| `anti_signatures` | `[]`                                                           |

This means **zero changes are required to existing seed packs** for Phase 0/1.

### 4.3 Language detection (deterministic first, probabilistic later)

Detection is a cascade. The first stage that returns a non-`None` answer wins.

1. **Explicit hint** (`hint=`): trust the caller. (Used by IDE plugins.)
2. **File-extension hint** (`file_path=`): `.rs` → rust, `.go` → go, `.py` → python, `.ts/.tsx` → typescript, `.js/.jsx/.mjs` → javascript, `Dockerfile` → docker, `*.yaml` containing `apiVersion:` → kubernetes.
3. **Deterministic token signals** (signal table in §5.1). E.g. `error[E0382]` locks rust at confidence 1.0.
4. **Probabilistic token n-gram model** (Phase 2): a bag-of-tokens classifier trained on the labelled corpus, returning a softmax over languages.
5. **Default**: `cross-language`. If no language signal fires at all, the cross-language packs (permission_denied, enospc, dns_resolution, tls_cert_invalid) are still scored.

### 4.4 Languages in scope for v1
`python, javascript, typescript, rust, go, docker, kubernetes, cross-language`.
All others (java, kotlin, c++, php, ruby, swift, c#, ...) explicitly out of v1
scope and will return `UnknownMatch` with `detected_lang='unknown'`.

---

## 5. CLASSIFIER ARCHITECTURE

### 5.1 Stage 1 — Language detection signal table

These are exact tokens that **lock** language with confidence 1.0. They are
hand-curated, regex-anchored where needed, and unit-tested.

| Language    | Locking signals (regex)                                                                       |
|-------------|-----------------------------------------------------------------------------------------------|
| rust        | `error\[E\d{4}\]`, `\bborrow checker\b`, `\bcargo\b`, `^\s*-->\s+.*\.rs:`                     |
| go          | `\bgoroutine \d+ \[`, `runtime error: invalid memory address`, `^panic: `, `\bfunc main\(\)` |
| python      | `Traceback \(most recent call last\)`, `^\s*File ".*\.py", line \d+`, `\bModuleNotFoundError\b`, `\bNoneType\b`, `\bImproperlyConfigured\b` |
| typescript  | `\bTS\d{4}\b`, `is not assignable to type '`, `\.tsx?\b`                                      |
| javascript  | `\bUnhandledPromiseRejection\b`, `at .*\.js:\d+`, `\bENOSPC\b` (also cross-language), `Cannot read propert(y\|ies) of (null\|undefined)` |
| docker      | `\bdocker:\b`, `OCI runtime`, `Error response from daemon:`                                   |
| kubernetes  | `\b(ImagePullBackOff\|CrashLoopBackOff\|OOMKilled\|ErrImagePull)\b`, `kubectl`, `apiVersion:` |
| (cross)     | `EACCES`, `EPERM`, `getaddrinfo`, `x509: certificate`                                          |

Conflict resolution: if two languages' locking signals fire (e.g. both Rust
and Python tokens are present, which would be a paste from a polyglot CI log),
we return `cross-language` with `LanguageSignal.ambiguous=True`. The CLI will
show "we see both rust and python here — please run with --lang rust to disambiguate".

### 5.2 Stage 2 — Framework detection within language

Framework detection runs **after** language is locked, and is also a token
signal table. Examples:

| Lang | Framework | Locking signals                                                          |
|------|-----------|--------------------------------------------------------------------------|
| py   | django    | `django\.`, `manage\.py`, `ImproperlyConfigured`, `OperationalError`, `models\.py` |
| py   | flask     | `flask\.`, `werkzeug\.`, `Flask app `                                    |
| py   | fastapi   | `fastapi\.`, `pydantic\.`, `uvicorn\.`                                   |
| js   | react     | `react-dom`, `Hydration failed`, `Invalid hook call`                     |
| js   | next      | `\bnext\b/`, `__NEXT_DATA__`                                             |
| ts   | react     | (inherits js/react signals)                                              |
| rs   | actix     | `actix_web::`, `actix-web`                                               |
| rs   | tokio     | `tokio::`, `tokio runtime`                                               |
| go   | gin       | `gin-gonic`, `gin\.`                                                     |

Framework is **non-locking** — it boosts score (`w_fw`) but never excludes a
class. A user with no framework still gets a classification.

### 5.3 Stage 3 — Problem-class scoring

For each candidate pack `p` (i.e. packs whose `language ∈ {detected_lang, cross-language}`), compute `S(e, p)` per §3.3. Features:

| Feature                | Source                                           | Weight    | Notes                                  |
|------------------------|--------------------------------------------------|-----------|----------------------------------------|
| `lang_match`           | language detector                                | `w_lang`  | already filtered, but still weighted   |
| `framework_match`      | framework detector ∩ pack.frameworks             | `w_fw`    | 0 if pack.frameworks=[]                |
| `signature_hit`        | regex hits over `pack.error_signatures` (sum of weights) | `w_sig`   | clipped at 1.0 per signature          |
| `unique_token_bonus`   | sum of `unique_to_class` flags that fired        | `w_uniq`  | the strongest evidence                 |
| `file_extension_match` | file_path extension ∈ pack.file_extensions       | `w_ext`   | small boost                            |
| `anti_signature_hit`   | hits over `pack.anti_signatures`                 | `-w_anti` | negative evidence                      |
| `cross_lang_penalty`   | language(e) ≠ pack.language ∧ pack ≠ cross-lang  | `-w_xlang`| huge penalty (already filtered, but defence-in-depth) |

Pseudocode:

```python
def score(e: str, p: Pack, ctx: ClassifyContext) -> tuple[float, list[Feature]]:
    fired: list[Feature] = []
    raw = 0.0

    # 1. language
    if ctx.language == p.language or p.language == 'cross-language':
        raw += W.LANG
        fired.append(Feature("lang_match", W.LANG, p.language))
    else:
        raw -= W.XLANG
        fired.append(Feature("cross_lang_penalty", -W.XLANG, p.language))

    # 2. framework
    if ctx.framework and ctx.framework in p.frameworks:
        raw += W.FW
        fired.append(Feature("framework_match", W.FW, ctx.framework))

    # 3. signatures
    sig_score = 0.0
    for sig in p.error_signatures:
        if sig.regex.search(e):
            sig_score += sig.weight
            fired.append(Feature("signature_hit", sig.weight, sig.regex.pattern))
            if sig.unique_to_class:
                raw += W.UNIQ
                fired.append(Feature("unique_token_bonus", W.UNIQ, sig.regex.pattern))
    raw += W.SIG * min(sig_score, 1.5)  # clip to avoid runaway

    # 4. anti-signatures
    for anti in p.anti_signatures:
        if anti.search(e):
            raw -= W.ANTI
            fired.append(Feature("anti_signature_hit", -W.ANTI, anti.pattern))

    # 5. file extension
    if ctx.file_ext and ctx.file_ext in p.file_extensions:
        raw += W.EXT
        fired.append(Feature("file_extension_match", W.EXT, ctx.file_ext))

    return sigmoid(raw), fired
```

### 5.4 Stage 4 — Confidence gate τ

After scoring, we sort candidates and inspect the best:

```python
best, best_score = scored[0]
if best_score < τ(ctx.language):
    return UnknownMatch(...)
return Match(confidence=calibrate(best_score, ctx.language), ...)
```

`τ` defaults (Phase 1, before any telemetry): `python: 0.55, javascript: 0.65,
typescript: 0.65, rust: 0.65, go: 0.65, docker: 0.60, kubernetes: 0.60,
cross-language: 0.70`. Python is lowest because we have evidence; Rust/Go/JS
start strict because we will earn the right to be confident with telemetry.

### 5.5 Why regex+features (and not LLM, not ML)

**Decision: regex + hand-engineered features + isotonic calibration.**
Defended on five axes:

| Axis              | Regex+features | LLM (remote)     | Embedding-NN     | Fine-tuned classifier |
|-------------------|----------------|------------------|------------------|------------------------|
| Cost / call       | ~0 (CPU only)  | $0.001–$0.02     | ~0 after load    | ~0 after load          |
| Latency p50       | <2 ms          | 800–4000 ms      | 50–200 ms        | 20–80 ms               |
| Offline           | ✓              | ✗                | ✓ (200MB+ model) | ✓ (50MB+ model)        |
| Wheel-size impact | +50 KB         | 0 (network)      | +200 MB          | +50–500 MB             |
| Explainability    | Perfect (which regex fired) | None / hallucinated | Nearest-neighbour at best | Saliency maps |
| Determinism       | Perfect        | None             | Perfect          | Perfect                |
| Update cost       | Edit a yaml    | Prompt-eng       | Re-embed corpus  | Retrain                |
| Cold start        | Zero examples  | Zero examples    | Needs corpus     | Needs labelled corpus  |
| Failure mode      | Misses unknown classes (acceptable — UnknownMatch) | Confidently wrong (the EXACT bug we're fixing) | Nearest wrong neighbour | Distribution shift |

Real-world precedents we're explicitly emulating:
- **Sentry's error grouping** uses fingerprint rules (regex over stack frames + module names). It is regex+heuristic, not ML, by design — for the same reasons. (See `sentry/grouping/strategies/`.)
- **Rollbar** and **Bugsnag** ship rule-based fingerprinters in their open-source SDKs.
- **GitHub's `linguist`** detects programming languages via a strategy cascade: extension → filename → shebang → modeline → heuristics → bayesian classifier. We are emulating exactly this pattern for language detection.
- **Drain3** (log clustering) is template-based, not ML, for offline/explainability reasons. It's the dominant production log clusterer.
- **`error-stack-parser`** (npm, 7M weekly downloads) parses stack traces with regex.

LLM-only would (a) violate G8 (offline), (b) make every `borg debug` invocation
cost money and ~2s latency, (c) hallucinate, (d) be the *exact failure mode*
that broke us — confidently wrong with no calibration. Embedding-NN balloons
the wheel by 200MB+ and gives nearest-neighbour-of-wrong-thing as the failure
mode. Fine-tuned classifier needs labelled data we don't have.

We are not religious — Phase 4 explicitly leaves room for an opt-in LLM "explain
harder" call when the regex layer returns UnknownMatch and the user passes
`--llm`. But it is never on the default path.

---

## 6. CALIBRATION

### 6.1 Expected Calibration Error (ECE)

Bucket predictions into `B=10` equal-width bins by predicted confidence. For
each bin compute `acc(b)` (fraction correct) and `conf(b)` (mean predicted
confidence). Then:

```
ECE = Σ_b (|b| / N) * |acc(b) - conf(b)|
```

Target: **ECE ≤ 0.05** per language at v1 ship.

This is the same definition Guo et al. 2017 use ("On Calibration of Modern
Neural Networks"), and what scikit-learn's `CalibrationDisplay` computes.

### 6.2 False-Confident Rate (FCR) — the metric we hill-climb on

```
FCR = P(classification is wrong | confidence > τ)
    = #{wrong & conf > τ} / #{conf > τ}
```

This is our **headline metric** because the dogfood incident proved that a
confident wrong answer is worse than no answer. We want **FCR ≤ 2% per
language** at v1 ship. Releases that regress FCR are blocked.

Why FCR and not just accuracy? Accuracy hides the tail. A classifier that is
80% accurate but only 50% accurate among the high-confidence predictions is
*more harmful* than one that is 60% accurate but 95% on its confident
predictions. FCR penalises exactly the failure mode that hurt the dogfood teams.

### 6.3 Setting τ initially

Phase 1 (no real telemetry yet): set τ from a small held-out labelled set
(target ≥ 50 examples per language; cross-language ≥ 30).

Procedure:
1. Score every example. Plot raw-score histograms split by `correct/incorrect`.
2. Find the lowest τ such that FCR ≤ 2% on the held-out set, with the
   constraint that recall (fraction of correct classifications kept) ≥ 0.7.
3. If no such τ exists (true positive distribution overlaps too much with
   false positives), the language is **not ready for confident answers** —
   set τ = 1.01 so it always returns UnknownMatch, and call out the gap in the
   release notes. (This is the explicit "earn the right to be confident" gate.)

### 6.4 Updating τ from telemetry (Phase 4 continuous loop)

Telemetry events (opt-in, local-first; sync only on explicit `borg telemetry sync`):

```
TelemetryEvent := {
    timestamp, error_hash, detected_lang, problem_class, confidence, raw_score,
    user_outcome: 'helpful' | 'wrong' | 'unknown_was_correct' | None
}
```

User outcome is captured by the existing `borg feedback-v3` path, plus a new
`--unknown-was-actually X` flag for the UnknownMatch path.

Calibration loop (runs nightly in CI on the aggregated public corpus, not
on private telemetry):

1. Recompute per-language `(score, correct)` pairs.
2. Fit isotonic regression `score → P(correct)`. Store as
   `borg/core/classifier/calibrators/{lang}.json`.
3. Recompute τ subject to `FCR ≤ 2%` and `recall ≥ 0.75`.
4. If τ changes by > 0.05, ship as a patch release with a note in the changelog.
5. Track ECE and FCR on a regression dashboard.

---

## 7. INTERFACE CONTRACTS

### 7.1 New public API

```python
# borg/core/classifier/api.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Feature:
    name: str
    weight: float
    source: str  # the regex pattern or signal name that fired

@dataclass(frozen=True)
class Explanation:
    features_fired: list[Feature]
    language_signal: str           # e.g. 'rust:error[E0382]'
    framework_signal: Optional[str]
    competing_classes: list[tuple[str, float]]  # top 3, post-calibration

@dataclass(frozen=True)
class Diagnostics:
    tokens_seen: list[str]
    near_miss_pack: Optional[str]
    near_miss_score: float
    threshold: float
    suggested_action: str

@dataclass(frozen=True)
class Match:
    problem_class: str
    language: str
    framework: Optional[str]
    confidence: float
    explanation: Explanation
    pack_id: Optional[str]
    score_raw: float
    is_known: bool = True

@dataclass(frozen=True)
class UnknownMatch:
    confidence: float
    top_k: list[tuple[str, float]]  # [(pack_id, score), ...]
    detected_lang: Optional[str]
    diagnostics: Diagnostics
    is_known: bool = False

ClassificationResult = Match | UnknownMatch  # py3.10+ union syntax

def classify(
    error: str,
    hint: Optional[str] = None,
    file_path: Optional[str] = None,
    framework: Optional[str] = None,
) -> ClassificationResult: ...
```

### 7.2 Backwards compatibility

```python
# borg/core/pack_taxonomy.py — keep this signature, forever.
def classify_error(error_message: str) -> Optional[str]:
    """Legacy API. Returns problem_class string, or None.

    Internally calls classify() and returns .problem_class on Match,
    None on UnknownMatch. Existing callers see no behavioural regression
    *for inputs that previously matched*. Inputs that previously matched
    spuriously (i.e. the bare-'Error' fallback) will now return None,
    which is the desired correction.
    """
    result = classify(error_message)
    return result.problem_class if isinstance(result, Match) else None
```

### 7.3 `debug_error` returns guidance OR UnknownGuidance

```python
@dataclass(frozen=True)
class UnknownGuidance:
    """Rendered as the 'we don't know yet' CLI block."""
    error_excerpt: str
    detected_lang: Optional[str]
    top_k: list[tuple[str, float]]   # near misses, for transparency
    suggested_action: str            # "borg debug --teach", "try --lang rust", ...
    contribute_url: str              # link to contribute a pack
    threshold: float

def debug_error(
    error_message: str,
    show_evidence: bool = True,
    hint: Optional[str] = None,
) -> Union[str, UnknownGuidance]:
    """
    Returns:
        - str (formatted guidance) if classify() returned Match
        - UnknownGuidance dataclass if classify() returned UnknownMatch

    The CLI is responsible for rendering UnknownGuidance to text.
    Returning a structured object (not a pre-rendered string) lets the CLI,
    MCP server, and HTTP server each render it appropriately.
    """
```

CLI rendering for UnknownGuidance:

```
============================================================
ERROR: error[E0382]: borrow of moved value: `x`
============================================================
[unknown] (detected language: rust)

borg doesn't have a confident answer for this error yet.

  Detected language : rust
  Best partial match: borrow_of_moved_value (score 0.42, threshold 0.65)
  Other near misses : lifetime_mismatch (0.18), trait_not_satisfied (0.12)

Why we didn't answer: we have ≤ 4 rust packs and our confidence
threshold for rust is 0.65 (we earn the right to be confident).

You can help:
  ► If borrow_of_moved_value is the right answer, run:
        borg debug --confirm borrow_of_moved_value
  ► If it's something else, contribute a pack:
        borg debug --teach
  ► Or open an issue with this error and your fix:
        https://github.com/.../guild-packs/issues/new?template=missing-pack
============================================================
```

This is the "we don't know yet, here's how to help us" UX. Critical: it
**never** invents an answer.

---

## 8. DATA MODEL — full updated YAML pack schema

```yaml
---
# === IDENTITY (unchanged) ===
type: workflow_pack
version: '1.1'           # bumped from 1.0 — new optional fields below
id: borrow-of-moved-value
problem_class: borrow_of_moved_value

# === NEW: language + framework taxonomy ===
language: rust           # REQUIRED for new packs. one of: python|javascript|typescript|rust|go|docker|kubernetes|cross-language
frameworks: []           # OPTIONAL list. e.g. ['actix', 'tokio']. [] = framework-agnostic.
file_extensions:         # OPTIONAL. boosts score when ctx.file_path matches.
  - '.rs'

# === NEW: scoring features ===
error_signatures:        # REQUIRED for new packs. ordered list of regex+weight.
  - regex: 'error\[E0382\]'
    weight: 1.0
    unique_to_class: true
  - regex: 'borrow of moved value'
    weight: 0.8
    unique_to_class: true
  - regex: 'value used here after move'
    weight: 0.4
    unique_to_class: false
  - regex: 'cannot move out of'
    weight: 0.3
    unique_to_class: false

anti_signatures:         # OPTIONAL. negative evidence — penalise score.
  - regex: 'NoneType'           # never a Rust error
  - regex: 'error\[E0277\]'     # different rust error code
  - regex: 'TS\d{4}'            # never a Rust error

# === EXISTING (preserved verbatim) ===
problem_signature:
  error_types:           # legacy; classify_error() still reads this for fallback
    - E0382
  framework: rust        # legacy; mirrors top-level `language`
  problem_description: >
    The compiler refuses to use a value that has been moved to another binding.
    Rust enforces single-ownership; the original binding is no longer valid
    after the move.

root_cause:
  category: ownership_violation
  explanation: >
    A value was moved (transferred ownership) and is then used again. Rust
    forbids this because the original binding no longer owns the data.

investigation_trail:
  - file: '@offending_function'
    position: FIRST
    what: Find the line that says "value moved here" in the rustc output
    grep_pattern: 'value moved here'
  - file: '@move_site'
    position: SECOND
    what: Inspect the function call or assignment that took ownership
    grep_pattern: 'fn .*\(.*: \w+\)|let \w+ = '

resolution_sequence:
  - action: clone_value
    command: 'let y = x.clone();'
    why: Allocates a copy so both bindings own independent data. Cheapest fix.
  - action: borrow_instead
    command: '&x  // pass by reference instead of by value'
    why: Avoid the move entirely if the callee only needs to read.
  - action: restructure_ownership
    command: 'use Rc<T> or Arc<T> for shared ownership'
    why: When multiple owners are genuinely needed.

anti_patterns:
  - action: 'unsafe { ... }'
    why_fails: 'Hides the bug under unsafe and risks UB. Never the right fix for E0382.'
  - action: 'std::mem::transmute'
    why_fails: 'Same reason. Almost always wrong.'

evidence:
  success_count: 0
  failure_count: 0
  success_rate: 0.0
  uses: 0
  avg_time_to_resolve_minutes: 0.0

provenance: 'Seed pack v1 | rust | drafted 2026-04-08 | needs SWE-bench-Rust validation'
---

## When to Use This Pack

Use when rustc emits `error[E0382]: borrow of moved value`.

Do NOT use when the error is about lifetimes (E0623) or traits (E0277).
```

### 8.1 Validation rules (enforced by `borg pack validate`)

- `language` must be in the allowed set, or pack load fails.
- Every regex in `error_signatures` and `anti_signatures` must compile.
- At least one `error_signatures` entry with `unique_to_class: true` is **required**, otherwise the pack cannot win confidently and we reject it at load time. (Catches "I forgot to add a unique signal" mistakes.)
- `weight ∈ [0, 2]`. Reject otherwise.
- `frameworks` entries must match a known framework for the language (or be the literal string the user wants to claim — we warn but don't reject).
- Existing `evidence` schema is unchanged and still required.

---

## 9. ROLLOUT PHASES

### Phase 0 — STOP THE BLEEDING (1 day, blocking)
**Goal:** ship within 24h to remove the harmful default.
**Effort:** ~4 engineer-hours.
**Dependencies:** none.
**Changes:**
1. Delete the `("Error", "schema_drift")` row from `_ERROR_KEYWORDS` in `pack_taxonomy.py:83`.
2. Add a per-keyword language tag to every entry in `_ERROR_KEYWORDS`. Match only when `detected_lang ∈ {keyword.lang, None, 'cross-language'}`.
3. Add a 30-line `_detect_language_quick(s: str) -> str|None` using only the locking signals from §5.1 — no calibration, no scoring yet.
4. `classify_error()` returns `None` (and `debug_error()` returns the existing "no matching problem class" message) when language ≠ python.
**Success criteria:**
- Reproduce the 4 dogfood errors from CONTEXT_DOSSIER.md. None should match a Python pack.
- All 2862 existing tests pass.
- Add 4 new regression tests for the dogfood errors (must return `None` from `classify_error`).
**Exit gate:** PR merged + v3.2.2 patch released.

### Phase 1 — Language detection layer + UnknownMatch CLI (1 week)
**Goal:** structured language detection, UnknownGuidance dataclass, CLI rendering.
**Effort:** ~30 engineer-hours.
**Dependencies:** Phase 0.
**Deliverables:**
- `borg/core/classifier/language.py` — full signal table from §5.1.
- `borg/core/classifier/types.py` — Match, UnknownMatch, Explanation, Diagnostics dataclasses.
- `borg/core/classifier/api.py` — `classify()` thin shim that wraps the existing keyword table for python and returns UnknownMatch otherwise.
- CLI rendering of UnknownGuidance per §7.3.
- Telemetry hook stub (writes to `~/.borg/telemetry.jsonl`, no network).
**Success criteria:**
- 100% precision on language detection for the curated 200-example test set.
- All 4 dogfood errors render the UnknownGuidance block (not the Python pack).
- Backwards compat: `classify_error()` returns the same problem_class for the existing eval harness.
**Exit gate:** `pytest borg/tests/classifier/` passes; v3.3.0-rc1 cut.

### Phase 2 — Confidence-scored classifier + ECE/FCR metrics (2 weeks)
**Goal:** the full feature-scoring pipeline from §5, with calibration and metrics.
**Effort:** ~80 engineer-hours.
**Dependencies:** Phase 1, Green Team's labelled corpus (≥ 50 ex/lang).
**Deliverables:**
- `borg/core/classifier/scoring.py` — implements §5.3 pseudocode.
- `borg/core/classifier/calibration.py` — isotonic regression per language.
- `borg/eval/e1c_classifier_calibration.py` — new eval harness, same style as e1a, computes ECE+FCR per language and prints a table.
- `borg/seeds_data/*.md` — backfill `language`, `error_signatures`, `anti_signatures` for the existing 12 Python packs.
- Per-language τ stored in `borg/core/classifier/thresholds.json`.
- Tests for every weight default and every signal in the table.
**Success criteria:**
- ECE ≤ 0.05 on python (we have data).
- FCR ≤ 2% on python.
- No regression on existing eval (must still hit the seed packs at >= today's recall).
**Exit gate:** e1c report shows green for python; v3.3.0 released.

### Phase 3 — JS/TS, Rust, Go, Docker, K8s pack seeds (3 weeks)
**Goal:** new languages reach v1 quality bar.
**Effort:** ~120 engineer-hours (mostly content authoring + corpus collection by Green Team).
**Dependencies:** Phase 2 + Green Team's per-language labelled corpora.
**Deliverables:**
- ≥ 4 packs per new language (so the per-language scorer has competition).
- Green Team labelled corpus per language (≥ 100 examples each).
- Calibrated τ per language. Languages without enough data ship with τ=1.01 ("always unknown") and a release-note caveat.
**Success criteria:**
- Every language with shipped packs hits ECE ≤ 0.05 and FCR ≤ 2%.
- Every dogfood error from CONTEXT_DOSSIER.md classifies correctly.
- No python regression.
**Exit gate:** v3.4.0 with multi-language support announced.

### Phase 4 — Continuous calibration loop (ongoing)
**Goal:** telemetry → corpus → recalibration loop closes automatically.
**Effort:** ~60 hours initial, then steady-state.
**Dependencies:** Phase 3 + opt-in telemetry consented.
**Deliverables:**
- `borg telemetry sync` command (opt-in, requires explicit user enable).
- Nightly CI job that re-fits isotonic calibrators and updates `thresholds.json`.
- Public dashboard showing ECE/FCR per language over time.
- Optional `--llm` flag on UnknownMatch path that calls a remote LLM as a *suggestion*, never auto-merged.
**Success criteria:**
- Recalibration runs nightly, fails loud on regression.
- FCR stays ≤ 2% for 30 consecutive days post-launch per language.
**Exit gate:** none — this is steady-state.

---

## 10. EXPLICIT NON-GOALS for v1

1. **No remote LLM on the hot path.** `borg debug` must work offline. LLM as
   optional `--llm` flag only, and only on the UnknownMatch path.
2. **No fine-tuned ML model.** No PyTorch/TF in the wheel. The wheel size must
   not grow by more than 200KB for the classifier.
3. **No multi-error correlation.** One error in, one classification out.
4. **No i18n.** English/ASCII error messages only. Localised error messages are
   v2 work.
5. **No automatic pack synthesis.** Telemetry suggests; humans accept and
   author packs.
6. **No deep stack-trace structural parser.** We treat the input as a flat
   string. Parsing pretty-printed Python tracebacks into frames is v2.
7. **No language-server integration.** That's a separate product.
8. **No probabilistic n-gram language model.** Pure deterministic signal table
   in v1; n-grams are Phase 4+.
9. **No PII redaction.** Telemetry is opt-in and local-first; we don't ship a
   redactor in v1. Telemetry sync is gated behind a v2 review.
10. **No "auto-correct" / "auto-fix" actions.** We give guidance, never run
    `rm -rf` style commands on the user's behalf.

---

## 11. ASCII ARCHITECTURE DIAGRAM

```
                          ┌────────────────────────┐
   user CLI invocation    │ borg debug "<error>"   │
                          └───────────┬────────────┘
                                      │
                                      ▼
                          ┌────────────────────────┐
                          │ borg/cli.py            │
                          │ _cmd_debug()           │
                          └───────────┬────────────┘
                                      │ classify(error, hint, file_path)
                                      ▼
        ┌──────────────────────────────────────────────────────┐
        │       borg/core/classifier/api.py — classify()        │
        │                                                       │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 1: language.detect()                     │   │
        │  │   1. explicit hint?            ──► return      │   │
        │  │   2. file extension?           ──► return      │   │
        │  │   3. locking signal table?     ──► return      │   │
        │  │   4. (Phase4) n-gram model?    ──► return      │   │
        │  │   5. fallback: 'cross-language'                 │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    │                                   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 2: framework.detect(lang, error)         │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    │                                   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 3: scoring.score_all(error, ctx, packs)  │   │
        │  │                                                 │   │
        │  │   for pack in packs where lang matches:        │   │
        │  │     S(e, p) = sigmoid( w_lang*lang             │   │
        │  │                       + w_fw*fw                 │   │
        │  │                       + w_sig*Σ sig_hits        │   │
        │  │                       + w_uniq*Σ unique_hits    │   │
        │  │                       + w_ext*ext_match         │   │
        │  │                       - w_anti*Σ anti_hits      │   │
        │  │                       - w_xlang*xlang_penalty)  │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    │                                   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 4: confidence gate τ(lang)                │   │
        │  │                                                 │   │
        │  │   conf = calibrate(best_score, lang)            │   │
        │  │   if conf < τ(lang):                             │   │
        │  │     return UnknownMatch(top_k, diagnostics)     │   │
        │  │   else:                                          │   │
        │  │     return Match(pack, conf, explanation)       │   │
        │  └─────────────────┬──────────────────────────────┘   │
        └────────────────────┼──────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                              │
              ▼                              ▼
   ┌─────────────────────┐       ┌──────────────────────────┐
   │ Match               │       │ UnknownMatch             │
   │  → load_pack()      │       │  → UnknownGuidance       │
   │  → render_pack(...) │       │  → "we don't know yet"   │
   └──────────┬──────────┘       └────────────┬─────────────┘
              │                                │
              └──────────────┬─────────────────┘
                             ▼
                  ┌────────────────────────┐
                  │ telemetry.append(...)  │  (opt-in, local-first)
                  └────────────────────────┘

  Side data:
    borg/seeds_data/*.md       — pack catalogue (loaded at startup)
    borg/core/classifier/      — language sigs, scoring, calibrators, thresholds
    ~/.borg/telemetry.jsonl    — opt-in event log
```

---

## 12. RISKS (top 5) WITH MITIGATIONS

| # | Risk                                                                                  | Severity | Mitigation                                                                                                       |
|---|---------------------------------------------------------------------------------------|----------|------------------------------------------------------------------------------------------------------------------|
| 1 | **τ set too low → confident wrong answers leak through.**                             | CRITICAL | Per-language τ; reject any release where FCR > 2% on the held-out set; ship with τ=1.01 (always-unknown) for any language without enough data. Hill-climb FCR, not accuracy. |
| 2 | **Regex maintenance burden grows quadratically with packs.**                          | HIGH     | Force unique signals in `unique_to_class`; lint at load time; auto-generate test cases from the regex set; cap pack count via review.                  |
| 3 | **Polyglot logs confuse language detection (Python calling Rust via PyO3, etc).**     | HIGH     | When two languages' locking signals fire, return `cross-language` with `LanguageSignal.ambiguous=True` and ask the user to disambiguate via `--lang`. |
| 4 | **Telemetry → calibration loop becomes a vector for adversarial mis-tagging.**        | MEDIUM   | Telemetry is opt-in, local-first. Calibration uses only the curated public corpus + manually-reviewed events. No automatic retraining from raw telemetry. |
| 5 | **Backwards-incompat: a previously-matching error message now returns UnknownMatch.** | MEDIUM   | Phase-2 eval harness must show no regression on the existing eval. Add explicit regression tests for every previously-known error. Bump τ down for python *only* if needed. |

---

## 13. ALTERNATIVES CONSIDERED

### A1. LLM-only classifier (rejected)
- **Pros:** zero engineering, generalises to any language.
- **Cons:** $$, latency 2–4s, hallucinates, no offline mode, **the exact failure
  mode that broke us was a confidently-wrong classifier**. Adding a remote LLM
  doesn't fix overconfidence — it amplifies it. Cited counterexample: every
  major error-tracking product (Sentry, Rollbar, Bugsnag) ships rule-based
  fingerprinters, not LLMs, even though they could afford the inference.

### A2. Embedding nearest-neighbour over labelled corpus (rejected for v1)
- **Pros:** offline-able, generalises better than regex, decent failure mode.
- **Cons:** ships a 200MB+ embedding model (sentence-transformers); cold start
  needs labelled corpus we don't have for non-Python; failure mode is
  "nearest wrong neighbour" which is silent and hard to debug; explainability
  reduces to "we picked the closest vector" which is unhelpful in a CLI.
- **Verdict:** revisit in v2 as an *additive* signal feeding into `S(e,p)`,
  not as the main classifier.

### A3. Drain log clustering (rejected)
- **Pros:** battle-tested for log line templating; offline; deterministic.
- **Cons:** Drain is for *deduplicating* log lines into templates, not for
  classifying their semantic class. We'd still need a downstream classifier
  on top of the templates, so this is orthogonal, not a replacement.
- **Verdict:** could be useful in Phase 4+ as a preprocessor when telemetry
  produces many similar but not identical errors that need deduping before
  human review. Not on the v1 critical path.

### A4. Fine-tuned classifier (rejected for v1)
- **Pros:** good accuracy ceiling once trained; small inference footprint
  with distilled models.
- **Cons:** needs labelled corpus we don't have; needs to be retrained per
  language; training infra overhead; distribution shift means continuous
  retraining; bad failure mode (silent miscalibration); ships extra model
  weights in the wheel.
- **Verdict:** the corpus we need to *build* for calibration becomes the
  corpus we'd need to *train* on, so v2 can revisit once we have labelled
  data at scale (≥ 1000 examples per language).

### A5. Pure regex with no confidence (rejected — this is what we have today)
- **Pros:** simplest; what's already here.
- **Cons:** **literally the bug we're fixing.** No way to refuse to answer.
  No way to compare candidates. No way to add cross-language packs without
  poisoning each other.
- **Verdict:** the status quo is the failure mode.

### A6. Hybrid (regex + embedding-NN reranker) (deferred)
- **Pros:** regex provides explainability + offline default, embeddings handle
  the long tail.
- **Cons:** complex; embedding model still ships in wheel; two systems to
  calibrate.
- **Verdict:** explicitly designed-for as a v2 path. The dataclass shape and
  scoring function in this spec accommodate adding `embedding_similarity` as
  an additional feature in `S(e,p)` without breaking changes.

---

## 14. SUCCESS METRICS (target numbers, not vibes)

| Metric                                                    | Today    | v3.3.0 (Phase 2 ship) | v3.4.0 (Phase 3 ship) | v4.0 steady state |
|-----------------------------------------------------------|----------|-----------------------|------------------------|--------------------|
| **FCR (false-confident rate), python**                   | unknown (silent) | ≤ 2%                | ≤ 2%                  | ≤ 1%              |
| **FCR, javascript/typescript**                            | n/a      | n/a (always unknown)  | ≤ 2%                  | ≤ 1%              |
| **FCR, rust**                                             | n/a      | n/a (always unknown)  | ≤ 2%                  | ≤ 2%              |
| **FCR, go**                                               | n/a      | n/a (always unknown)  | ≤ 2%                  | ≤ 2%              |
| **FCR, docker / k8s**                                     | n/a      | n/a (always unknown)  | ≤ 2%                  | ≤ 2%              |
| **ECE, all languages with shipped packs**                 | n/a      | ≤ 0.05 (python)       | ≤ 0.05                | ≤ 0.03            |
| **Recall (correct-and-confident / total correct), python**| ~unknown | ≥ 0.70                | ≥ 0.75                | ≥ 0.80            |
| **Recall, all other languages**                           | n/a      | n/a                   | ≥ 0.55                | ≥ 0.70            |
| **Cross-language poison rate** (rust/docker matched to python) | 100% on dogfood examples | 0%   | 0%                    | 0%                |
| **Wheel size delta**                                      | baseline | ≤ +50 KB              | ≤ +200 KB             | ≤ +500 KB         |
| **`classify()` p50 latency**                              | ~1 ms    | ≤ 5 ms                | ≤ 5 ms                | ≤ 10 ms           |
| **`classify()` p99 latency**                              | unknown  | ≤ 20 ms               | ≤ 20 ms               | ≤ 30 ms           |
| **Unknown-match rate** (UnknownMatch / total queries)     | 0% (all forced) | 25–40% acceptable in v3.3 | 15–25%        | ≤ 15%             |
| **Existing python eval (e1a)**                            | passes   | passes (no regression) | passes               | passes            |
| **Test count**                                            | 2862     | +50 minimum           | +120 minimum          | +200 minimum      |
| **Languages with confident packs**                       | 1 (py)   | 1 (py)                | 7 (py, js, ts, rs, go, docker, k8s) | 7+ |

**Headline release gate (Phase 2 / v3.3.0):** FCR-python ≤ 2% AND no eval regression.
**Headline release gate (Phase 3 / v3.4.0):** zero cross-language poison on the dogfood corpus AND FCR ≤ 2% on every shipped language.

---

## Appendix A — Real systems we are emulating

- **Sentry grouping (`getsentry/sentry`):** rule-based fingerprint strategies, regex over stack frames. Same explainability/offline justification we use here.
- **GitHub Linguist (`github/linguist`):** strategy cascade for language detection — exactly the model in §4.3.
- **Drain3 (`logpai/Drain3`):** template-based log clustering. Deliberately not ML.
- **Guo et al. 2017, "On Calibration of Modern Neural Networks":** ECE definition.
- **scikit-learn `IsotonicRegression`:** the calibrator we'll use in Phase 2.
- **`error-stack-parser` (npm):** regex-based stack frame parsing.
- **mypy/pyright/rustc/go vet error code conventions:** the basis for our locking signal table.

## Appendix B — File layout after Phase 2

```
borg/core/
├── pack_taxonomy.py            # legacy classify_error() wrapper, kept for compat
└── classifier/
    ├── __init__.py
    ├── api.py                  # classify(), debug_error()
    ├── types.py                # Match, UnknownMatch, Explanation, ...
    ├── language.py             # detect_language() + signal table
    ├── framework.py            # detect_framework() + signal table
    ├── scoring.py              # score(), Feature, weight constants
    ├── calibration.py          # isotonic calibrators, τ loading
    ├── thresholds.json         # per-language τ
    ├── calibrators/
    │   ├── python.json
    │   └── ...                 # one per language
    └── unknown.py              # UnknownGuidance dataclass + builders

borg/eval/
├── e1a_seed_pack_validation.py  # existing
└── e1c_classifier_calibration.py  # NEW — ECE/FCR/precision/recall per lang

borg/tests/classifier/
├── test_language_detection.py
├── test_framework_detection.py
├── test_scoring.py
├── test_calibration.py
├── test_unknown_match_path.py
└── test_backwards_compat.py
```

---

**END OF SPEC.**
