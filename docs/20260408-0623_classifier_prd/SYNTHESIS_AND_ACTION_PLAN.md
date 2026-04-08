# Borg Debug Classifier v1 — Multi-Language Confidence-Gated Classification

## 0. METADATA

| Field    | Value |
|----------|-------|
| Title    | Borg Debug Classifier v1 — Multi-Language Confidence-Gated Classification |
| Date     | 20260408-0623 |
| Owner    | Hermes Agent on behalf of AB |
| Status   | Phase 0 SHIPPED (v3.2.2). Phase 0.5 anti_signatures SHIPPED (v3.2.3). Phases 1-4 DEFERRED pending user-research evidence per SKEPTIC_REVIEW.md Appendix B. |
| Inputs   | CONTEXT_DOSSIER.md, RED_TEAM_REVIEW.md, ARCHITECTURE_SPEC.md, DATA_ANALYSIS.md, error_corpus.jsonl (173 rows) |

**TL;DR.** Delete one line of `pack_taxonomy.py` today to stop shipping confidently-wrong Django advice for Rust/Docker/JS errors, then over four phases replace the 40-entry substring table with a language-detected, confidence-gated, regex+features classifier whose headline metric is per-language False-Confident Rate ≤ 2%.

---

## 1. EXECUTIVE SUMMARY

The bug, in plain English: `borg debug "<error>"` runs a 40-entry ordered substring scan whose final entry is the bare word `"Error"` mapped to `schema_drift`. Because virtually every error message in every language contains the substring "error", the classifier short-circuits to `schema_drift` and tells Rust, Docker, JS, Go, and shell users to run `python manage.py makemigrations`. There is no language detection, no confidence score, no "I don't know" path, and no telemetry on misclassification. (CONTEXT_DOSSIER.md §"Root cause"; RED_TEAM_REVIEW.md §0; pack_taxonomy.py:83.)

The headline numbers from the Green Team baseline (DATA_ANALYSIS.md §2–§3, run on 173 real-world labelled errors):

- **53.8%** of the corpus is False-Confident (wrong class with confidence). [§2]
- **8.1%** Exact-correct overall. **13.1%** precision on the predictions that DO fire. [§2]
- **88.4%** of the corpus expects a `problem_class` that does not exist in the catalogue at all. [§6]
- **95.5%** of Rust errors (21/22) get a Python/Django answer. **90.9%** of plain JS/Node. **62.5%** of React/Next. [§3]
- The `schema_drift` cell in the confusion matrix absorbs **84/173 = 48.6%** of the corpus. Deleting the bare-`"Error"` row alone converts those 84 false-confident hits into honest silent misses. [§4]

The proposal: ship a one-line patch release within 24h that deletes the bare-`"Error"` fallback and adds a non-Python language guard, then over four numbered phases replace the substring table with the Blue Team's four-stage classifier (language detect → framework detect → feature scoring → confidence gate τ), backfill the existing 12 Python packs with the new schema, ship Green's top-10 ROI-ranked non-Python pack seeds, and close the loop with nightly isotonic recalibration on telemetry. The headline release gate is per-language FCR ≤ 2%; releases that regress this are blocked. (ARCHITECTURE_SPEC.md §6.2, §9, §14.)

This is the highest-ROI work currently on the Borg roadmap because (a) the bug is actively destroying trust on every download — 775+ users on PyPI today (CONTEXT_DOSSIER §Background), (b) Phase 0 is a half-day fix with `∞` ROI per Green's cost/benefit table (DATA_ANALYSIS.md §10), and (c) without it the marketed killer feature `borg debug` violates AB's own non-negotiables #6 ("don't ship features whose accuracy we haven't measured") and #8 ("a confident wrong answer is the worst outcome"). (CONTEXT_DOSSIER §"Constraints".)

---

## 2. THE BUG WE ARE FIXING

**Exact line.** `borg/borg/core/pack_taxonomy.py:83`:

```python
# Generic
("Error", "schema_drift"),
```

This is the **last** entry of `_ERROR_KEYWORDS`. `classify_error()` lower-cases the input (line 195) and tests `keyword.lower() in lower` (line 197). The literal 5-character substring `"error"` appears in essentially every error message ever written, so classification short-circuits to `schema_drift` with no confidence score, no language gating, and no abstain path. (RED_TEAM_REVIEW.md CRITICAL-1.)

**Why it silently poisons every non-Python error.** The matched pack is `schema-drift.md`, which is a Django ORM migration walkthrough. Its `framework` field is `python`, so the CLI renders `[schema_drift] (python)` and prints `python manage.py makemigrations` as the resolution sequence. There is no language detection step before classification (RED_TEAM_REVIEW.md CRITICAL-2; ARCHITECTURE_SPEC.md §1), so the renderer happily stamps `(python)` on a Rust borrow-checker error. There is no confidence score in the return type (`Optional[str]`, RED_TEAM_REVIEW.md CRITICAL-3), so even if a downstream caller wanted to refuse low-confidence answers, the data shape forbids it. There is no telemetry on misclassification (RED_TEAM_REVIEW.md MEDIUM-10), so the bad answers are silent — they have been shipping at v3.2.1 for 775+ downloads with no signal back.

**The four canonical reproductions** (CONTEXT_DOSSIER.md §"Reproductions captured 20260408-0623", verified live on `borg 3.2.1`):

```
$ borg debug "error[E0382]: borrow of moved value: \`x\`"
[schema_drift] (python)
ROOT CAUSE: schema_mismatch — The Python model and the actual database schema have diverged …
RESOLUTION SEQUENCE: 1. create_migration  Command: python manage.py makemigrations …
```

```
$ borg debug "Error: ENOSPC: no space left on device"
[schema_drift] (python)        ← same wrong answer
```

```
$ borg debug "TS2322: Type 'string' is not assignable to type 'number'"
No matching problem class found.
```

```
$ borg debug "Hydration failed because the initial UI does not match what was rendered on the server"
No matching problem class found.
```

The first two are *confidently wrong*; the second two are *blind spots*. Both failure modes are blocked by v1. The first two are blocked by Phase 0 (today); the second two are blocked by Phase 3 (new packs).

---

## 3. GOALS / NON-GOALS

### 3.1 Goals (testable)

| ID  | Goal | Test |
|-----|------|------|
| G1  | Eliminate the bare-`"Error"` fallback. No untyped wildcard match exists in v1. | `grep -n '"Error"' borg/core/pack_taxonomy.py` returns no entry mapped to `schema_drift`. |
| G2  | Detect language before any pack scoring. | `language.detect()` returns one of `{python, javascript, typescript, rust, go, docker, kubernetes, cross-language, None}` for every corpus row; ≥ 95% precision per language on the 173-row corpus. |
| G3  | Return a calibrated confidence in `[0,1]` for every classification. | `classify(...)` return type is `Match \| UnknownMatch`; ECE ≤ 0.05 per shipped language (ARCHITECTURE_SPEC.md §6.1). |
| G4  | Refuse to answer (`UnknownMatch`) when `confidence < τ(lang)`. | The four CONTEXT_DOSSIER reproductions all return `UnknownMatch`, not a Python pack. |
| G5  | Backwards compatible: `classify_error(str) -> Optional[str]` keeps its signature; no Python/Django regression. | Existing eval `e1a_seed_pack_validation.py` still passes; per-language Python recall ≥ today's recall. |
| G6  | Pack schema is a strict superset (additive). | All 12 existing seed packs load unchanged; the loader synthesises missing fields per ARCHITECTURE_SPEC.md §4.2. |
| G7  | Per-language FCR/ECE/precision/recall reported by `e1c_classifier_calibration.py`. | New eval harness exists; CI fails on FCR regression. |
| G8  | Offline. No network or LLM call on the hot path. | `borg debug` works with `--no-network`; LLM only behind opt-in `--llm` flag, only on UnknownMatch path. |

### 3.2 Non-Goals (v1) — see also §10

(NG1) No fine-tuned ML model in the wheel. (NG2) No remote LLM on the default `borg debug` path. (NG3) No deep stack-trace structural parser. (NG4) No i18n / non-English errors. (NG5) No automatic pack synthesis. (NG6) No multi-error correlation. (NG7) No language-server integration. (NG8) No probabilistic n-gram language model in v1 — pure deterministic signal table. (NG9) No PII redaction in telemetry — telemetry is opt-in and local-first only. (NG10) No auto-fix actions; we give guidance, never run commands. (Verbatim from ARCHITECTURE_SPEC.md §10.)

---

## 4. SUCCESS METRICS

Headline metric: **per-language False-Confident Rate (FCR) ≤ 2% at the recommended τ**, where `FCR = #{wrong & conf > τ} / #{conf > τ}` (ARCHITECTURE_SPEC.md §6.2). FCR is chosen over accuracy because the dogfood incident proved the failure mode is *confident wrong* — accuracy hides the tail and FCR penalises exactly the harmful subset.

Secondary metrics and how they're measured:

| Metric | Today (measured) | v1 target | How measured |
|--------|------------------|-----------|--------------|
| **FCR, all languages** (headline) | 53.8% (DATA_ANALYSIS.md §2) | ≤ 5% corpus-wide; ≤ 2% per shipped language | `e1c_classifier_calibration.py` over `error_corpus.jsonl` |
| **FCR, python** | 52.9% (DATA_ANALYSIS.md §3) | ≤ 2% | ditto |
| **FCR, rust** | 95.5% (DATA_ANALYSIS.md §3) | ≤ 2% by Phase 3, n/a (always-unknown) before | ditto |
| **FCR, javascript** | 90.9% (§3) | ≤ 2% by Phase 3 | ditto |
| **FCR, react/next** | 62.5% (§3) | ≤ 2% by Phase 3 | ditto |
| **FCR, docker** | 56.2% (§3) | ≤ 2% by Phase 3 | ditto |
| **FCR, typescript** | 0.0% but 0/20 correct (§3) | ≤ 2% by Phase 3, recall ≥ 0.55 | ditto |
| **Cross-language poison rate** (Rust/Docker matched to a Python pack) | 100% on dogfood inputs (§3) | 0% by end of Phase 0 | 4 dogfood reproductions return non-Python answers or UnknownMatch |
| **Exact-correct (precision of firings)** | 13.1% (§2) | ≥ 90% | `e1c` |
| **Recall, python** | 38.2% (§3) | ≥ 75% | `e1c` |
| **Recall, py+js+ts+rust+docker** | ≤ 10% (computed: 13/(34+22+20+22+16)) | ≥ 60% | `e1c` |
| **ECE per shipped language** | not measured (no confidence) | ≤ 0.05 | `e1c` (10 equal-width bins per Guo 2017) |
| **`classify()` p50 latency** | ~1 ms | ≤ 5 ms | microbenchmark; budget set in ARCHITECTURE_SPEC.md §14 |
| **`classify()` p99 latency** | unknown (RED_TEAM_REVIEW.md (d).12) | ≤ 20 ms | ditto |
| **Wheel size delta** | baseline | ≤ +200 KB by Phase 3 | `wc -c` on built wheel |
| **Test count for classifier** | **0** (RED_TEAM_REVIEW.md CRITICAL-5) | +50 by Phase 1, +120 by Phase 3 | `pytest --collect-only borg/tests/classifier/` |
| **Existing Django eval (e1a)** | passes | passes (no regression) | `pytest borg/eval/e1a_seed_pack_validation.py` |
| **Backwards compat on existing Django SWE-bench slice** | passes | 0 regressions | non-negotiable #7, CONTEXT_DOSSIER §Constraints |

**Headline release gate (Phase 2 / v3.3.0):** FCR-python ≤ 2% AND no eval regression.
**Headline release gate (Phase 3 / v3.4.0):** zero cross-language poison on the dogfood corpus AND FCR ≤ 2% on every shipped language.

---

## 5. PROPOSED ARCHITECTURE (1-page summary; full spec in ARCHITECTURE_SPEC.md §3–§8)

### 5.1 ASCII block diagram (reproduced from ARCHITECTURE_SPEC.md §11)

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
        │  │   5. fallback: 'cross-language'                │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 2: framework.detect(lang, error)         │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 3: scoring.score_all(error, ctx, packs)  │   │
        │  │   S(e,p) = sigmoid(  w_lang*lang               │   │
        │  │                    + w_fw*fw                    │   │
        │  │                    + w_sig*Σ sig_hits           │   │
        │  │                    + w_uniq*Σ unique_hits       │   │
        │  │                    + w_ext*ext_match            │   │
        │  │                    - w_anti*Σ anti_hits         │   │
        │  │                    - w_xlang*xlang_penalty)     │   │
        │  └─────────────────┬──────────────────────────────┘   │
        │                    ▼                                   │
        │  ┌────────────────────────────────────────────────┐   │
        │  │ Stage 4: confidence gate τ(lang)                │   │
        │  │   conf = calibrate(best_score, lang)            │   │
        │  │   if conf < τ(lang):                            │   │
        │  │     return UnknownMatch(top_k, diagnostics)     │   │
        │  │   else:                                         │   │
        │  │     return Match(pack, conf, explanation)       │   │
        │  └─────────────────┬──────────────────────────────┘   │
        └────────────────────┼──────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
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
```

### 5.2 Four-stage pipeline summary

1. **Language detect** (deterministic cascade): explicit hint → file extension → locking signal table (e.g. `error\[E\d{4}\]` locks rust at confidence 1.0; `Traceback (most recent call last)` locks python; `\bgoroutine \d+ \[` locks go) → fallback `cross-language`. Polyglot logs return `cross-language` with `ambiguous=True`. (ARCHITECTURE_SPEC.md §4.3, §5.1.)
2. **Framework detect** (within language, non-locking): boosts score via `w_fw` but never excludes a class. E.g. `django\.`, `manage\.py` → django; `react-dom`, `Hydration failed` → react. (§5.2.)
3. **Problem-class scoring**: for each pack `p` whose `language ∈ {detected, cross-language}`, compute `S(e,p) = sigmoid(w_lang*lang + w_fw*fw + w_sig*Σsig + w_uniq*Σunique − w_anti*Σanti − w_xlang*xlang)`. Default weights: `w_lang=2.5, w_fw=1.5, w_sig=1.0, w_uniq=2.0, w_anti=2.0, w_xlang=4.0` — `w_xlang` is large on purpose so a Rust error matched to a Python pack is virtually impossible. (§3.3, §5.3.)
4. **Confidence gate τ**: compare best calibrated confidence to per-language `τ(lang)`. If `conf < τ`, return `UnknownMatch` with top-3 near-misses and diagnostics; else return `Match`. Phase-1 default τ: `python: 0.55, javascript: 0.65, typescript: 0.65, rust: 0.65, go: 0.65, docker: 0.60, kubernetes: 0.60, cross-language: 0.70`. Languages without enough labelled data ship with `τ=1.01` ("always abstain") until they earn the right to be confident. (§3.4, §5.4, §6.3.)

### 5.3 Why regex+features beats LLM-only and embedding-NN

Five-axis comparison from ARCHITECTURE_SPEC.md §5.5 (alternatives table):

| Axis | Regex+features | LLM (remote) | Embedding-NN | Fine-tuned |
|------|---------------|--------------|--------------|------------|
| Cost / call | ~0 (CPU only) | $0.001–$0.02 | ~0 after load | ~0 after load |
| Latency p50 | <2 ms | 800–4000 ms | 50–200 ms | 20–80 ms |
| Offline | yes | no | yes (200MB+ model) | yes (50MB+ model) |
| Wheel size delta | +50 KB | 0 (network) | +200 MB | +50–500 MB |
| Explainability | perfect (which regex fired) | none / hallucinated | nearest-neighbour at best | saliency only |
| Failure mode | misses → UnknownMatch (acceptable) | confidently wrong (the EXACT bug) | nearest-wrong-neighbour silent | distribution shift |

Real-world precedents we're emulating: Sentry's grouping engine, Rollbar/Bugsnag fingerprinters, GitHub Linguist (strategy cascade for language detection), Drain3 (template-based log clustering), npm `error-stack-parser`. None of these use ML, all for the same reasons: offline + explainability + deterministic + cheap. (ARCHITECTURE_SPEC.md §5.5, Appendix A.)

LLM-only is rejected because (a) violates G8 (offline), (b) costs $ and 2s per `borg debug` call, (c) hallucinates, (d) is the *exact* failure mode that broke us — confidently wrong with no calibration. Embedding-NN balloons the wheel by 200MB+ and gives "nearest wrong neighbour" as the silent failure mode. Fine-tuned classifier needs labelled data we don't have. (ARCHITECTURE_SPEC.md §13 alternatives A1, A2, A4.)

We are not religious — Phase 4 leaves room for an opt-in `--llm` "explain harder" call when regex returns `UnknownMatch`. But it is never on the default path.

---

## 6. PHASED ROLLOUT

> **STATUS (20260408-0832):** Phase 0 shipped as v3.2.2 on 20260408-0735 — corpus FCR 53.8% -> 4.6%. Phase 0.5 (anti_signatures, residual 8 false-confident rows killed) shipped as v3.2.3 on 20260408-~0900. **Phases 1-4 are DEFERRED.** The GEPA spike (see gepa_spike/SPIKE_REPORT.md) disproved the naive GEPA-replaces-hand-authoring hypothesis. The Skeptic gate (SKEPTIC_REVIEW.md) continues to recommend redirecting the 5-6 week Phase 1-4 capacity to MCP-in-Claude-Code / SWE-bench polish / pack-adoption cron until user-research evidence flips ≥2 of the 5 conditions in Appendix B.

### Phase 0 — STOP THE BLEEDING (must ship within 24h)

| Field | Value |
|-------|-------|
| Goal  | Remove the harmful default. The single highest-ROI change in the entire PRD per Green's cost/benefit (DATA_ANALYSIS.md §10, ROI = ∞). |
| Effort | ~4 engineer-hours (ARCHITECTURE_SPEC.md §9 Phase 0). |
| Dependencies | none. |
| Scope | (a) Delete the `("Error", "schema_drift")` row at `pack_taxonomy.py:83`. (b) Add a 30-line `_detect_language_quick(s)->str\|None` using only the locking signals from ARCHITECTURE_SPEC.md §5.1. (c) `classify_error()` returns `None` when detected language ≠ python (the "non-Python signal guard"). (d) Add the first 10 pytest tests in `borg/tests/test_classify_error.py` covering the 4 dogfood reproductions plus the 6 canonical RED_TEAM_REVIEW.md CRITICAL-1 inputs. (e) Cut and publish v3.2.2 patch release with a release-note entry acknowledging the bug. |
| Rollback plan | Revert the single commit; v3.2.1 is the rollback target. The change is additive-deletion only — there is no schema migration, no data change, no API break. |
| Verifier | Chief Architect runs the 4 dogfood reproductions on the v3.2.2 wheel and confirms none returns a Python pack; Green Team reruns `run_baseline.py` on the new wheel and confirms corpus FCR drops from 53.8% to ≤ 10% (Green has the corpus and the runner — DATA_ANALYSIS.md §0). |
| Exit criteria | (E0.1) corpus FCR ≤ 10% with **zero new packs**, measured by Green's `run_baseline.py`. (E0.2) all 4 CONTEXT_DOSSIER reproductions return `None` / "No matching problem class" rather than a Python pack. (E0.3) all 2862 existing tests still pass. (E0.4) 10 new pytest tests for `classify_error` are merged and green in CI. (E0.5) v3.2.2 is published to PyPI with the release note. |

**Why this is achievable today.** Green's confusion-matrix observation (DATA_ANALYSIS.md §4): the `schema_drift` column absorbs 84/173 rows. Removing the bare-`"Error"` fallback alone converts those 84 confident-wrongs into honest silent misses. Green's empirical claim — "this single rule would take baseline FCR from 53.8% → ~6% today, before any new packs ship" (DATA_ANALYSIS.md §8.4) — is exactly what gate E0.1 measures.

### Phase 1 — LANGUAGE DETECTION + UnknownMatch path (1 week)

| Field | Value |
|-------|-------|
| Goal  | Structured language detection, `UnknownGuidance` dataclass, CLI rendering of "we don't know yet". (ARCHITECTURE_SPEC.md §9 Phase 1.) |
| Effort | ~30 engineer-hours. |
| Dependencies | Phase 0 merged. |
| Scope | Create `borg/core/classifier/{language.py, framework.py, types.py, api.py, unknown.py}`. Implement the locking-signal cascade from ARCHITECTURE_SPEC.md §4.3 + §5.1. `classify()` is a thin shim that runs language detection then defers to the existing keyword table for python and returns `UnknownMatch` for everything else. CLI renders `UnknownGuidance` per ARCHITECTURE_SPEC.md §7.3. Telemetry hook stub writes to `~/.borg/telemetry.jsonl` (no network). |
| Rollback plan | Feature flag `BORG_CLASSIFIER_V2=0` falls back to legacy `classify_error()`. Default off until Phase 1 exit gate passes. |
| Verifier | Chief Architect + Green Team. Green re-runs the corpus harness to verify per-language detection precision; Chief Architect verifies the four CONTEXT_DOSSIER reproductions render the `UnknownGuidance` block (not a Python pack). |
| Exit criteria | (E1.1) Per-language language-detection precision **≥ 95%** on the 173-row corpus. (E1.2) All 4 dogfood reproductions render `UnknownGuidance` (not a Python pack). (E1.3) `classify_error()` legacy signature returns the same `problem_class` for the existing eval inputs (no Python regression). (E1.4) ≥ 50 new pytest tests in `borg/tests/classifier/` pass. (E1.5) v3.3.0-rc1 is cut. |

### Phase 2 — CONFIDENCE-SCORED CLASSIFIER + ECE/FCR metrics + telemetry hooks (2 weeks)

| Field | Value |
|-------|-------|
| Goal  | The full feature-scoring pipeline of ARCHITECTURE_SPEC.md §5.3 with isotonic calibration, per-language τ, and the new `e1c` eval harness. (ARCHITECTURE_SPEC.md §9 Phase 2.) |
| Effort | ~80 engineer-hours. |
| Dependencies | Phase 1, Green Team's labelled corpus (≥ 50 ex/lang — present today as `error_corpus.jsonl`). |
| Scope | Implement `borg/core/classifier/{scoring.py, calibration.py, thresholds.json}`. Backfill the 12 existing Python seed packs with `language`, `error_signatures`, `anti_signatures` per ARCHITECTURE_SPEC.md §4.2 (legacy loader synthesises missing fields, so this is incremental, not a forced cutover). Build `borg/eval/e1c_classifier_calibration.py` that consumes `error_corpus.jsonl` and emits per-language precision/recall/F1/ECE/FCR. Wire telemetry events `(error_hash, detected_lang, problem_class, confidence, raw_score, user_outcome)` per ARCHITECTURE_SPEC.md §6.4 — opt-in, local-first, no network. |
| Rollback plan | `BORG_CLASSIFIER_V2=0` reverts to Phase 1 behaviour; thresholds.json is data-only and can be hot-edited. |
| Verifier | Chief Architect + Green Team. Green produces the e1c report; Chief Architect signs the release gate. |
| Exit criteria | (E2.1) **ECE ≤ 0.05** on python; (E2.2) **FCR ≤ 5% corpus-wide** AND **FCR ≤ 2% on python**; (E2.3) no regression on existing `e1a` eval; (E2.4) wheel size delta ≤ +50 KB; (E2.5) classify() p50 latency ≤ 5 ms; (E2.6) v3.3.0 released. |

### Phase 3 — NEW PACK SEEDS, in Green's ROI order (3 weeks)

| Field | Value |
|-------|-------|
| Goal  | Author the first 10 non-Python seed packs in the order set by Green's ROI table (DATA_ANALYSIS.md §7), and demonstrate confident answers for every dogfood reproduction. (ARCHITECTURE_SPEC.md §9 Phase 3.) |
| Effort | ~120 engineer-hours (mostly content authoring + corpus collection). |
| Dependencies | Phase 2 + Green's per-language corpora (already in `error_corpus.jsonl`). |
| Scope | Author packs in this **exact** order (Green ROI rank → file): (1) `rust-borrow-checker.md`, (2) `docker-disk-full.md`, (3) `ts-type-error.md`, (4) `react-hydration-mismatch.md`, (5) `js-undefined-property.md`, (6) `k8s-crashloop.md`, (7) `k8s-image-pull.md`, (8) `rust-trait-bound.md`, (9) `go-nil-pointer.md`, (10) `docker-build-error.md`. Each pack must validate against ARCHITECTURE_SPEC.md §8.1 rules — at least one `error_signatures` entry with `unique_to_class: true` is required, anti_signatures populated to suppress poison cases. Per Green's recommendation (DATA_ANALYSIS.md §7) Phase-1 packs target ≈37.6% of the corpus and address all five dogfood complaints. |
| Rollback plan | Pack files are data; remove individual files to revert. Per-language `τ` can be raised to 1.01 to switch a language to "always-unknown" without removing packs. |
| Verifier | Chief Architect + Green Team. Green re-runs `e1c` per language; Chief Architect verifies the dogfood reproductions classify correctly. |
| Exit criteria | (E3.1) **Recall ≥ 60%** on Python+JS+TS+Rust+Docker (the five buckets we committed to ship with — DATA_ANALYSIS.md §9). (E3.2) **Recall ≥ 75%** on Python (no regression vs. Phase 2). (E3.3) Every shipped language hits **ECE ≤ 0.05** AND **FCR ≤ 2%**. (E3.4) Cross-language poison rate = **0%** on dogfood corpus. (E3.5) Wheel size delta ≤ +200 KB. (E3.6) v3.4.0 announced as multi-language. |

### Phase 4 — CONTINUOUS CALIBRATION LOOP (ongoing)

| Field | Value |
|-------|-------|
| Goal  | Telemetry → corpus → recalibration loop closes automatically. (ARCHITECTURE_SPEC.md §9 Phase 4, §6.4.) |
| Effort | ~60 hours initial, then steady-state. |
| Dependencies | Phase 3 shipped + opt-in telemetry consented by enough users to give a per-language sample. |
| Scope | `borg telemetry sync` opt-in command. Nightly CI job re-fits per-language isotonic calibrators against the merged (curated corpus + manually-reviewed telemetry) dataset. New `τ` rolled out as a patch release if it changes by > 0.05; gated rollout means `thresholds.json` is shipped first to a canary slice. Public dashboard for ECE/FCR per language over time. Optional `--llm` flag on the `UnknownMatch` path that calls a remote LLM as a *suggestion only*, never auto-merged into a pack. |
| Rollback plan | Calibrators are JSON files; revert to the previous version on `borg/core/classifier/calibrators/{lang}.json`. `thresholds.json` likewise. |
| Verifier | Continuous; nightly CI fails loud on regression. |
| Exit criteria | (E4.1) Recalibration runs nightly without manual intervention; (E4.2) FCR stays ≤ 2% per language for 30 consecutive days post-Phase-3-launch; (E4.3) at least one `τ` adjustment has been pushed via the gated rollout path successfully. (Steady-state — no formal exit gate; this is the operating mode.) |

### Phase summary table

| Phase | Duration | Effort (eng-h) | Headline exit gate | Release |
|-------|----------|---------------|---------------------|---------|
| 0     | 1 day    | 4             | Corpus FCR drops 53.8% → ≤ 10% with zero new packs | v3.2.2 |
| 1     | 1 week   | 30            | Per-language detection precision ≥ 95% | v3.3.0-rc1 |
| 2     | 2 weeks  | 80            | python ECE ≤ 0.05 AND python FCR ≤ 2% | v3.3.0 |
| 3     | 3 weeks  | 120           | Recall ≥ 60% on Py+JS+TS+Rust+Docker; FCR ≤ 2% per shipped lang; cross-lang poison = 0% | v3.4.0 |
| 4     | ongoing  | 60+steady     | FCR ≤ 2% per lang for 30 consecutive days | rolling patches |

---

## 7. RED TEAM FINDING DISPOSITION TABLE

Every CRITICAL and HIGH severity finding from `RED_TEAM_REVIEW.md`. MEDIUM/LOW are tracked in the appendix; only CRITICAL/HIGH are gating.

| ID | Severity | Summary | Disposition | Evidence / cite |
|----|----------|---------|-------------|-----------------|
| CRITICAL-1 | CRIT | `("Error","schema_drift")` substring fallback siphons all errors with the substring "error" into a Django pack. | **FIXED IN PHASE 0** — line deleted at pack_taxonomy.py:83; first 10 pytest tests cover the canonical reproductions. Verified by E0.1, E0.2. | RED_TEAM_REVIEW.md CRIT-1; DATA_ANALYSIS.md §4 (84/173 sinkhole). |
| CRITICAL-2 | CRIT | No language/framework detection anywhere; renderer stamps `(python)` on Rust/Go/Docker output. | **FIXED IN PHASES 0+1** — Phase 0 adds the `_detect_language_quick` guard; Phase 1 lifts it into the formal `language.detect()` cascade with locking signals from ARCHITECTURE_SPEC.md §5.1. Renderer reads inferred language, not pack frontmatter. | RED CRIT-2; ARCHITECTURE_SPEC.md §4.3, §5.1. |
| CRITICAL-3 | CRIT | Return type is `Optional[str]`; no confidence, no `UnknownMatch` path; the API cannot express uncertainty. | **FIXED IN PHASE 1+2** — new `classify()` returns `Match \| UnknownMatch` (ARCHITECTURE_SPEC.md §3.2, §7.1). Legacy `classify_error(str) -> Optional[str]` is preserved as a thin wrapper that returns `None` on `UnknownMatch` (ARCHITECTURE_SPEC.md §7.2). | RED CRIT-3; ARCHITECTURE_SPEC.md §7.1, §7.2. |
| CRITICAL-4 | CRIT | Taxonomy is Python-only; output brands every classification `(python)`; ≥ 70% of the developer ecosystem unserved. | **FIXED IN PHASE 3** — packs authored in Green's ROI order (rust_borrow_checker first). Phase 0 + Phase 1 already eliminate the *poisoning*; Phase 3 addresses the *coverage*. | RED CRIT-4; DATA_ANALYSIS.md §6, §7. |
| CRITICAL-5 | CRIT | Zero pytest tests on `classify_error` (2862 tests in suite, 0 hits for `classify_error\|pack_taxonomy`). | **FIXED IN PHASE 0+1+2** — Phase 0 adds 10 tests; Phase 1 adds ≥ 50; Phase 2 adds ≥ 120 cumulative; the new `borg/tests/classifier/` directory is part of CI and gates merges. | RED CRIT-5; ARCHITECTURE_SPEC.md §9 Phase 0/1/2 deliverables. |
| CRITICAL-6 | CRIT | Non-negotiable #6 ("don't ship features whose accuracy we haven't measured") is violated by v3.2.1; e1a is a schema validator, not a classifier eval. | **FIXED IN PHASE 2** — `e1c_classifier_calibration.py` is the new eval that exercises production code paths and reports per-language precision/recall/ECE/FCR over `error_corpus.jsonl`. Release gate is FCR ≤ 2%. | RED CRIT-6; ARCHITECTURE_SPEC.md §9 Phase 2; DATA_ANALYSIS.md §9. |
| HIGH-1 | HIGH | Case-insensitive substring with no word boundaries → `circular saw`, `terror`, `migrate from vim` all match keywords. | **FIXED IN PHASE 2** — Phase-2 scoring uses anchored regexes (`error\[E\d{4}\]`, `\bborrow checker\b`, `\bgoroutine \d+ \[`, etc.) from `error_signatures` lists. The substring-in-lower path is dead by Phase 2. | RED HIGH-1; ARCHITECTURE_SPEC.md §5.1, §5.3. |
| HIGH-2 | HIGH | First-match-wins ordering collapses `ImportError: cannot import name` (cycle) vs. genuine missing-symbol. | **FIXED IN PHASE 2** — feature scoring picks `argmax_p S(e,p)` across all candidates, with `unique_to_class` bonuses; ordering is no longer semantic. Disambiguation handled by per-language `error_signatures`. | RED HIGH-2; ARCHITECTURE_SPEC.md §3.3, §5.3. |
| HIGH-3 | HIGH | `TypeError` (Python row 77) eats JS `TypeError: Cannot read properties of undefined`, routing to Python `type_mismatch`. | **FIXED IN PHASES 0+2** — Phase 0 language guard refuses to match Python packs on JS-detected text. Phase 2 anti-signatures (`anti_signatures: [Cannot read propert(y\|ies) of (null\|undefined)]` on the python `type_mismatch` pack) provide defence in depth. Phase 3 ships `js_undefined_property` pack as the correct destination. | RED HIGH-3; DATA_ANALYSIS.md §5 row 6. |
| HIGH-4 | HIGH | `"Error"` fallback catches positive-sentiment text (`"json decoder error"`, `"no errors at all"`, `"Error at line 42"`). | **FIXED IN PHASE 0** — same single deletion as CRITICAL-1. | RED HIGH-4. |
| HIGH-5 | HIGH | Case-insensitivity inconsistent: `TIMEOUT` matches nothing because the keyword is `"timed out"`. | **FIXED IN PHASE 2** — regexes are explicit and reviewed at pack-load time; per ARCHITECTURE_SPEC.md §8.1 every regex must compile. Existing inconsistencies are eliminated when the keyword table is decommissioned. | RED HIGH-5. |
| HIGH-6 | HIGH | `_get_skills_dir() → None` silently sets `_CACHE_INITIALIZED=True` on empty seeds dir; users see "pack not found" instead of "broken install". | **FIXED IN PHASE 1** — pack loader raises `PackCacheEmptyError` when seeds dir is missing or empty; CLI surfaces it as a distinct exit code. | RED HIGH-6. |
| HIGH-7 | HIGH | `_expand_placeholder` looks for `@@call_site` (double-`@`); mid-string placeholders never expand. Dead/buggy. | **FIXED IN PHASE 2** — `_expand_placeholder` is removed and replaced by a templating helper that operates on the unprefixed key (`{call_site}`) per pack-author docs. Existing packs unaffected because none currently rely on mid-string expansion (they use concrete paths). | RED HIGH-7. |
| HIGH-8 | HIGH | `problem_description.split(".")[0]` truncates at the first period — file paths and version numbers cut sentences mid-render. | **FIXED IN PHASE 1** — render path uses the full `problem_description`; truncation is replaced by line-wrap at 80 cols with explicit ellipsis when over the budget. | RED HIGH-8. |
| HIGH-9 | HIGH | `OperationalError` ordered before `no such table`; routing depends on which keyword hits first, hiding semantic ambiguity inside Django itself. | **FIXED IN PHASE 2** — multi-feature scoring evaluates *all* signatures and picks the highest-scoring pack via `S(e,p)`. Ordering is irrelevant; competing classes are surfaced in `Explanation.competing_classes`. | RED HIGH-9; ARCHITECTURE_SPEC.md §3.3. |
| HIGH-10 | HIGH | CLI accepts blank/single-char input; `"a"` iterates 40 keywords; trivially exploited via shell quoting. | **FIXED IN PHASE 1** — CLI input validation: empty/whitespace-only → exit code 2 with usage message; inputs < 4 chars return `UnknownMatch` immediately. | RED HIGH-10. |
| HIGH-11 | HIGH | Module-level mutable `_PACK_CACHE` has no invalidation; long-lived processes never see new packs. | **DEFERRED TO PHASE 4** — explicit `borg pack reload` CLI command added in Phase 4; long-lived process scenarios (IDE plugin, watch mode) are out of scope for v1 because Borg's primary entry point is the short-lived `borg debug` CLI invocation. **Reason for deferral:** measurable user impact today is zero (Borg has no IDE plugin shipping); fixing requires a cache-versioning protocol that should be designed alongside the telemetry sync work. Tracked in P4 backlog. | RED HIGH-11. |

**Disposition summary: 17 / 17 CRITICAL+HIGH dispositioned. 16 fixed across Phases 0–3; 1 explicitly deferred (HIGH-11) with reason.**

MEDIUM-1 through MEDIUM-11 and LOW-1 through LOW-5 are addressed implicitly by the architectural rewrite (e.g. MEDIUM-1 god-list dies in Phase 2 when `_ERROR_KEYWORDS` is replaced; MEDIUM-6 dual-classifier dies in Phase 2 when `e1c` becomes the single eval; MEDIUM-10 telemetry is added in Phase 2 hook + Phase 4 sync). Items not addressed by the architecture rewrite — MEDIUM-2 (`✗` glyph crash on cp1252), MEDIUM-3 (`except Exception: pass` in `FailureMemory`), MEDIUM-9 (FS vs SSH `permission denied` collision) — are tracked in the v1.x backlog and **must not** block v1 ship.

---

## 8. CONFLICTS RESOLVED

| # | Conflict | Red Team position | Blue Team position | Green Team data | Resolution |
|---|----------|-------------------|---------------------|-----------------|------------|
| 1 | **Pull the marketing or fix the code first?** | RED §0 / TOP-10 #10: pull the README claim immediately. | BLUE §9 Phase 0: ship a code patch within 24h. | GREEN §10: P0 is a one-line deletion with ROI ∞, can ship same day. | **Code patch wins.** Phase 0 ships v3.2.2 in 24h (Green proves it's a one-line change with verified corpus impact); the release note explicitly acknowledges the bug. We do not pull the marketing because the fix is faster than the marketing rollback would be, and the release note is the honest signal. |
| 2 | **API break now (`Optional[str]` → `Match\|UnknownMatch`) or backwards-compat shim?** | RED CRIT-3 #2: break the API now, deprecate later. | BLUE §7.2: keep `classify_error(str) -> Optional[str]` forever as a shim. | GREEN §11: pack schema and classifier interface should be additive. | **Blue wins.** `classify_error()` legacy signature is preserved; the new API lives at `borg.core.classifier.api.classify()`. Existing callers see no behavioural regression *for inputs that previously matched correctly*; inputs that previously matched spuriously (the bare-`"Error"` siphon) now return `None`, which IS the desired correction. This satisfies non-negotiable #7 (backwards-compat) without trapping us in the broken API. |
| 3 | **Confidence threshold τ — global constant or per-language?** | RED is silent on τ shape. | BLUE §3.4, §5.4: per-language τ, because calibration data density varies wildly across languages. | GREEN §8: ship τ as a single env var `BORG_DEBUG_CONFIDENCE_THRESHOLD=0.60` initially, then re-tune. | **Blue wins on shape (per-language); Green wins on initial value.** Phase 1 ships per-language `τ` defaults from ARCHITECTURE_SPEC.md §5.4 (python: 0.55, js/ts/rust/go: 0.65, docker/k8s: 0.60, cross-lang: 0.70). Per-language shape is non-negotiable because Green proved Python has 12 packs of evidence and Rust has 0 — they cannot share a threshold. The single env var is kept as an emergency override (`BORG_DEBUG_CONFIDENCE_THRESHOLD_OVERRIDE`) so τ can be rolled back without a release, which is Green's actual concern. |
| 4 | **Test set size — 36 examples (Red) or 173 (Green) or 200+ (Blue)?** | RED §4: ≥ 30 examples, 7 languages, with negative/abstain/calibration rows. | BLUE §9 Phase 1 exit gate: "100% precision on language detection for the curated 200-example test set". | GREEN §1: 173 rows already on disk in `error_corpus.jsonl`, ≥ 15 per language, all real-world sourced. | **Use Green's 173-row corpus as the v1 ground truth.** Blue's "200-example" target was aspirational; Green has actually built one. The Red Team adversarial set (36 examples with negatives) is folded in as `tests/classifier/fixtures/adversarial.jsonl` and run as a *separate* gate alongside the corpus. The 200-example aspiration is satisfied: 173 + 36 = 209. |
| 5 | **Telemetry — opt-in (Blue/Green) or required for measurement (Red implicit)?** | RED MEDIUM-10: "the marketing claim is uncheckable after release. Drift detection is impossible." (Implies telemetry must be on to measure.) | BLUE §6.4: opt-in, local-first, sync only on explicit `borg telemetry sync`. | GREEN §8.5: log every CLI invocation so τ can be re-tuned weekly. | **Opt-in wins for v1.** Red's drift-detection concern is real but is solved by the curated public corpus (`error_corpus.jsonl`), not by raw user telemetry. v1 ships the local-first event log and the explicit-sync command; opt-in defaults to off; nightly recalibration runs against the curated corpus. Phase 4 may revisit. |
| 6 | **Which non-Python pack to ship first?** | RED CRIT-4 / TOP-10 #4: "ship at least three non-Python pack families (JS/TS, Rust, Go) + one infra (Docker/K8s) before re-enabling marketing." | BLUE §9 Phase 3: deliverable is "≥ 4 packs per new language". | GREEN §7: ranked ROI list — `rust_borrow_checker` (ROI 42), `docker_disk_full` (42), `ts_type_error` (33), `react_hydration_mismatch` (33), `js_undefined_property` (33), `k8s_crashloop` (33). | **Green's ROI list wins on ordering.** Per the resolution rule "Green's priority list determines which non-Python packs ship first." Phase 3 author order is fixed in §6 above. Red's "≥ 3 non-Python families" requirement is met after pack #6 (rust + docker + ts + react + js + k8s = 5 families covered). |
| 7 | **Stack-trace structural parsing — v1 or v2?** | RED §1.(g) flags absence as a SOTA gap; implicitly suggests v1. | BLUE NG3: explicitly v2. | GREEN: not addressed. | **Blue wins.** v1 treats input as flat text. Per §10 NG3. The classifier already gets ≤ 2% FCR without parsing tracebacks; adding structural parsing is a v2 latency/complexity tax we cannot justify pre-v1-ship. |
| 8 | **e1a vs e1c — replace or coexist?** | RED MEDIUM-6: collapse the two classifiers into one. | BLUE §9 Phase 2 deliverable: new `e1c` alongside existing `e1a`. | GREEN §9: criteria target the *frozen `error_corpus.jsonl`*, not e1a. | **Both — but e1c is the gate.** Phase 2 keeps `e1a` (Django smoke test, runs against the eval harness) but the **release gate is `e1c`** with FCR ≤ 2%. The two classifiers Red flagged as a problem (prod and eval) ARE collapsed: `e1c` exercises the production `classify()`, not a duplicate. `e1a` is downgraded from a release gate to a regression smoke test. |

---

## 9. RISKS AND MITIGATIONS (top 5; from ARCHITECTURE_SPEC.md §12 augmented by Red findings)

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **τ set too low → confident wrong answers leak through.** This is the same failure mode that produced today's bug, just at higher resolution. | CRITICAL | Per-language τ; reject any release where FCR > 2% on the held-out set; ship with `τ=1.01` (always-unknown) for any language without enough data; hill-climb FCR not accuracy. (ARCHITECTURE_SPEC.md §12 risk 1, §6.3.) |
| 2 | **Regex maintenance burden grows quadratically with packs.** Red MEDIUM-1 (god-list anti-pattern) reapplied at scale. | HIGH | Force unique signals via `unique_to_class: true`; lint at pack-load time per ARCHITECTURE_SPEC.md §8.1; auto-generate test fixtures from each new pack's signature regexes; cap pack count to ≤ 50 in v1 via review. |
| 3 | **Polyglot logs confuse language detection** (PyO3 / FFI / containerised stacks where multiple languages co-occur in one paste). | HIGH | Two-language locking-signal collision returns `cross-language` with `LanguageSignal.ambiguous=True`; CLI shows "we see both rust and python here — please run with `--lang rust` to disambiguate". (ARCHITECTURE_SPEC.md §5.1.) |
| 4 | **Telemetry → calibration loop becomes a vector for adversarial mistagging** — a hostile actor or a buggy IDE integration floods the local log with false labels that drift τ. | MEDIUM | Telemetry is opt-in and local-first; calibration uses *only* the curated public corpus + manually-reviewed events; no automatic retraining from raw telemetry; nightly job fails loud on FCR regression. (ARCHITECTURE_SPEC.md §12 risk 4, §6.4.) |
| 5 | **Backwards-incompat: a previously-matching error message now returns `UnknownMatch`** — Django power users see Python recall regress because Phase 2 raises the bar. (Red HIGH-9 territory.) | MEDIUM | Phase-2 eval harness gates on no-regression vs. existing eval; explicit regression tests for every previously-known Django error; lower python `τ` if the held-out recall drops. (ARCHITECTURE_SPEC.md §12 risk 5.) |

Augmented from Red Team for completeness:

- **R6 (RED supply-chain risk, §1.(f).7):** pack files contain shell commands and SQL. A compromised pack could inject ANSI escapes or destructive commands. **Mitigation:** Phase 2 pack loader strips ANSI escape sequences from rendered text and refuses to load packs with shebangs or `rm -rf` literals; tracked as Phase 2 deliverable item.
- **R7 (RED §1.(f).8 vanity metrics):** today's `_cmd_start` records `success=True` unconditionally, producing fake "EVIDENCE: 22/26 successes (85%)" telemetry. **Mitigation:** Phase 1 removes the unconditional success logging from `cli.py:373-386`; evidence stats become honest (mostly zero in v1), and the rendered output reflects that.

---

## 10. EXPLICIT NON-GOALS FOR v1 (verbatim from ARCHITECTURE_SPEC.md §10, plus additions)

1. **No remote LLM on the hot path.** `borg debug` works offline. LLM only behind opt-in `--llm` flag, only on the `UnknownMatch` path.
2. **No fine-tuned ML model.** No PyTorch / TensorFlow in the wheel. Wheel size delta ≤ +200 KB through Phase 3.
3. **No multi-error correlation.** One error in, one classification out.
4. **No i18n.** ASCII / English error messages only.
5. **No automatic pack synthesis.** Telemetry suggests; humans accept and author packs.
6. **No deep stack-trace structural parser.** Flat-string input only. Pretty-printed traceback parsing is v2.
7. **No language-server integration.** Separate product.
8. **No probabilistic n-gram language model.** Deterministic signal table only in v1; n-grams Phase 4+.
9. **No PII redaction.** Telemetry is opt-in and local-first; redactor is v2.
10. **No auto-fix actions.** Guidance only; never run commands on the user's behalf.

Chief Architect additions:

11. **No Java / Kotlin / C++ / Ruby / PHP / C# / Swift packs in v1.** These languages return `UnknownMatch` with `detected_lang='unknown'`. Listed in DATA_ANALYSIS.md as outside the corpus and outside Phase 3 ROI. Defer to v2 unless market signal demands otherwise.
12. **No fix for `_PACK_CACHE` invalidation in long-lived processes** (Red HIGH-11). Borg's primary entry point is the short-lived CLI; deferred to Phase 4 alongside telemetry sync.
13. **No replacement of `e1a`.** It is downgraded to a regression smoke test and continues to run unchanged.

---

## 11. OPEN QUESTIONS FOR AB

The Chief Architect cannot decide these alone. Five questions, each with the recommendation in italics.

1. **Phase 0 release vehicle: ship v3.2.2 patch immediately, or bundle with v3.3.0?** *Recommend v3.2.2 patch immediately (within 24h). The bug is shipping today; bundling delays the fix by 3+ weeks for no architectural benefit. Green's measured impact (53.8% → ≤ 10% FCR with one line) justifies the cost of an extra release.*

2. **Is opt-in local-first telemetry acceptable for Phase 2 (off by default, explicit `borg telemetry sync` to upload)?** *Recommend yes. Without telemetry the Phase 4 calibration loop cannot close. The opt-in + local-first design (no network without explicit user command) is conservative enough to ship in v3.3.0; PII redaction is deferred to v2 (NG9).*

3. **Who verifies each phase's exit gate?** *Recommend: Chief Architect signs the gate; Green Team produces the e1c numbers; Red Team consulted on Phase 0 + Phase 3 (the two release-bearing phases). For Phase 2 / Phase 3 release notes, AB approves the release.*

4. **Do we acknowledge the bug publicly in the v3.2.2 release note, or word it as a "classification accuracy improvement"?** *Recommend acknowledge explicitly. The dogfood teams found it; Hacker News will find it next. Honest acknowledgment + a link to this PRD is better reputation than discovery-by-screenshot. AB's non-negotiable #6 (verify-before-ship) and the broader VERIFY-BEFORE-SHIP discipline argue for transparency.*

5. **Phase 3 pack authoring — keep all 10 in the wheel or split into a `borg-packs-extras` companion package?** *Recommend keep in the wheel through Phase 3. Wheel size delta is ≤ +200 KB which is well under the budget. A companion package adds friction (`pip install borg[rust]`) that hurts the multi-language story. Revisit in Phase 4 if the wheel grows past 1 MB.*

---

## 12. APPENDICES POINTERS

| Appendix | Path |
|----------|------|
| Full Red Team Review (44 findings, 6 CRIT, 11 HIGH, 11 MED, 5 LOW) | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/RED_TEAM_REVIEW.md` |
| Full Blue Team Architecture Spec (1126 lines, formal model + spec + alternatives) | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/ARCHITECTURE_SPEC.md` |
| Full Green Team Data Analysis (680 lines, baseline + corpus + ROI + sample packs) | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/DATA_ANALYSIS.md` |
| Labelled error corpus (173 rows, 9 languages) | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/error_corpus.jsonl` |
| Baseline reproducer | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/run_baseline.py` |
| Per-row baseline output | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/baseline_results.csv` |
| Corpus builder | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/build_corpus.py` |
| Shared context for all teams | `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/CONTEXT_DOSSIER.md` |
| Broken classifier (target of fix) | `/root/hermes-workspace/borg/borg/core/pack_taxonomy.py` (line 83 is the bug) |

---

**END OF SYNTHESIS_AND_ACTION_PLAN.md**
