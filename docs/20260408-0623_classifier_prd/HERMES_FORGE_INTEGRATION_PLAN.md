# HERMES_FORGE_INTEGRATION_PLAN.md

Borg-as-target integration with NousResearch/hermes-agent-self-evolution
(internally codenamed "hermes-forge"). Spike scope and pivot/no-pivot decision packet for AB.

Date: 20260408
Author: Hermes subagent on behalf of AB
Inputs read end-to-end before writing this:
- https://raw.githubusercontent.com/NousResearch/hermes-agent-self-evolution/main/README.md (84 lines)
- https://raw.githubusercontent.com/NousResearch/hermes-agent-self-evolution/main/PLAN.md (781 lines)
- evolution/skills/evolve_skill.py (323 lines)
- evolution/skills/skill_module.py (123 lines)
- evolution/core/constraints.py (174 lines)
- evolution/core/dataset_builder.py (201 lines)
- evolution/core/fitness.py (146 lines)
- evolution/core/config.py (72 lines)
- evolution/core/external_importers.py (785 lines)
- pyproject.toml (43 lines)
- Borg: SYNTHESIS_AND_ACTION_PLAN.md, pack_taxonomy.py, e1a_seed_pack_validation.py, 3 seed packs (missing-foreign-key.md, null-pointer-chain.md, schema-drift.md), seeds_data/ listing.

---

## 1. EXECUTIVE SUMMARY (5 sentences)

1. NousResearch/hermes-agent-self-evolution is a thin DSPy+GEPA wrapper (~1,800 LOC, MIT, only Phase 1 of a 5-phase plan actually implemented) that mutates the BODY of a SKILL.md, runs an LLM-as-judge fitness function over a synthetic eval set, gates on a few size/structure constraints, and prints a diff (README.md:9-26; PLAN.md:54-86).
2. A "Borg pack target" would mean teaching that loop to mutate the YAML frontmatter + markdown body of borg/seeds_data/*.md and score candidates with a deterministic metric — per-language FCR over error_corpus.jsonl — instead of an LLM judge.
3. Cost / effort estimate: ~6-10 engineer-hours to stand up a working spike that evolves one Borg pack end-to-end; ~25-40 hours to ship a defensible v1 with PR generation, ECE/FCR gates, and integration into borg's existing 2862-test suite.
4. **Recommendation: SPIKE Strategy C (direct GEPA inside borg, no forge wrapper) and vendor ~175 lines of forge's constraint validator. Do NOT fork, do NOT take a runtime dependency on hermes-agent-self-evolution today.**
5. **Headline reason this beats hand-authoring Phases 1-4 of the classifier PRD: hand-authoring 10 non-Python packs (Phases 1-3, ~230 eng-hours) hits one human-curated point in the search space; a 6-10 hour GEPA spike searches the entire pack mutation surface against the same 173-row corpus and either produces measurably-better packs or proves the corpus is too small — and the result is a yes/no answer in <2 days, not 5-6 weeks of regex hand-authoring.**

---

## 2. UPSTREAM ARCHITECTURE NOTES

### 2.1 Project layout (verified by `git/trees/main?recursive=1`)

```
hermes-agent-self-evolution/
├── README.md                          (84 lines)
├── PLAN.md                            (781 lines — the only design doc)
├── pyproject.toml                     (43 lines, deps: dspy>=3.0.0, openai, pyyaml, click, rich)
├── generate_report.py                 (single file — not a package)
├── reports/
│   └── phase1_validation_report.pdf   (PDF only, no source)
├── datasets/
│   ├── skills/.gitkeep                (EMPTY — no committed datasets)
│   └── tools/.gitkeep                 (EMPTY)
├── evolution/
│   ├── __init__.py                    (109 bytes — basically empty)
│   ├── core/
│   │   ├── config.py                  (72 lines — EvolutionConfig dataclass)
│   │   ├── constraints.py             (174 lines — ConstraintValidator)
│   │   ├── dataset_builder.py         (201 lines — synthetic + golden loaders)
│   │   ├── external_importers.py      (785 lines — Claude Code / Copilot / Hermes session mining)
│   │   └── fitness.py                 (146 lines — LLMJudge + skill_fitness_metric)
│   ├── skills/
│   │   ├── evolve_skill.py            (323 lines — the only working entry point)
│   │   └── skill_module.py            (123 lines — SkillModule(dspy.Module))
│   ├── tools/__init__.py              (STUB — Phase 2 unbuilt)
│   ├── prompts/__init__.py            (STUB — Phase 3 unbuilt)
│   ├── code/__init__.py               (STUB — Phase 4 unbuilt)
│   └── monitor/__init__.py            (STUB — Phase 5 unbuilt)
└── tests/
    ├── core/test_constraints.py
    ├── core/test_external_importers.py
    └── skills/test_skill_module.py
```

**Headline observation: only the skills target exists. tools/, prompts/, code/, monitor/ are empty `__init__.py` placeholders.** The "Phase 2-5 planned" cells in the README table (README.md:55-60) are aspirational, not code.

### 2.2 How the Phase 1 skill evolution loop is wired

The end-to-end loop is `evolution/skills/evolve_skill.py:36-293`:

- **Step 1 — load skill:** `find_skill()` walks `<hermes_repo>/skills/**/SKILL.md` (skill_module.py:58-81). `load_skill()` parses YAML frontmatter + body (skill_module.py:15-55). Borg packs are structurally identical (frontmatter `---` block + body) — see `borg/seeds_data/null-pointer-chain.md:1-63`.

- **Step 2 — build eval dataset:** Three sources, dispatched at evolve_skill.py:83-115:
  - `synthetic`: `SyntheticDatasetBuilder.generate()` (dataset_builder.py:115-169) sends the artifact text to an LLM with a `GenerateTestCases` signature (dataset_builder.py:96-109) and asks for N (task_input, expected_behavior, difficulty, category) tuples. It then random-shuffles and splits 50/25/25 (dataset_builder.py:159-169).
  - `sessiondb`: `build_dataset_from_external()` (external_importers.py:1-200+) mines `~/.claude/history.jsonl`, `~/.copilot/session-state/*/events.jsonl`, and `~/.hermes/sessions/*.json` for messages relevant to the skill, then runs them through an LLM to score relevance.
  - `golden`: `GoldenDatasetLoader.load()` (dataset_builder.py:172-201) reads a hand-curated JSONL.

- **Step 3 — wrap as DSPy module:** `SkillModule(dspy.Module)` (skill_module.py:84-114) declares a `TaskWithSkill` signature with three fields: `skill_instructions` (the optimizable parameter), `task_input`, and `output`. `forward()` runs `dspy.ChainOfThought(TaskWithSkill)`. **The thing being evolved is the string `self.skill_text` that gets injected as `skill_instructions` to the chain-of-thought call.**

- **Step 4 — run GEPA:** evolve_skill.py:154-177:
  ```python
  optimizer = dspy.GEPA(metric=skill_fitness_metric, max_steps=iterations)
  optimized_module = optimizer.compile(baseline_module, trainset=trainset, valset=valset)
  ```
  Falls back to `dspy.MIPROv2(auto="light")` if GEPA isn't available in the installed DSPy version (evolve_skill.py:167-177). **Both optimizers are called via the public DSPy API — there is no special integration code.**

- **Step 5 — fitness:** `skill_fitness_metric()` (fitness.py:107-136) is a deterministic keyword-overlap heuristic, NOT the LLMJudge: `score = 0.3 + 0.7 * len(expected_words & output_words) / len(expected_words)`. The full LLM-as-judge in `LLMJudge.score()` (fitness.py:34-104) exists but is not called from the metric. **This is materially weaker than what the README implies — the actual fitness function in their repo is a bag-of-words proxy.**

- **Step 6 — constraint gate:** `ConstraintValidator.validate_all()` (constraints.py:30-53) runs:
  - `_check_size()` (constraints.py:95-117) — limits hardcoded per artifact_type: `max_skill_size=15_000` chars, `max_tool_desc_size=500`, `max_param_desc_size=200` (config.py:26-29).
  - `_check_growth()` (constraints.py:119-134) — max 20% growth over baseline.
  - `_check_non_empty()` (constraints.py:136-148).
  - `_check_skill_structure()` (constraints.py:150-174) — verifies `---` frontmatter + `name:` + `description:` keys present in first 500 chars. **Hardcoded to "skill"; would need a sibling `_check_pack_structure()` for Borg.**
  - Optional `run_test_suite()` (constraints.py:55-93) — shells out to `python -m pytest tests/ -q --tb=no` in the hermes-agent repo with a 300s timeout. This is the ONLY benchmark gate actually wired up.

- **Step 7 — holdout eval + report:** evolve_skill.py:207-293 runs baseline_module and optimized_module on the holdout split, prints a Rich table with baseline vs evolved scores, writes `output/<skill>/<timestamp>/{evolved_skill.md, baseline_skill.md, metrics.json}`. **There is no PR generation code anywhere in the repo.** The README and PLAN.md both promise it (PLAN.md:705-727), but `pr_builder.py` listed in PLAN.md:151 does not exist on disk.

### 2.3 Where they pull session traces from (the Mar 29 importer)

`evolution/core/external_importers.py` was added in commit `3fb26f16` (2026-03-09 — wait, the commit listing shows 2026-03-29 in `commits?path=`; the global commit log shows 2026-03-09. Verified: PR #2 "external session importers for Claude Code, Copilot, and Hermes" landed on **2026-03-29** per the path-filtered API; the earlier 03-09 commits were the initial Phase-1 skill loop). The Mar 29 commit is `3fb26f16`; PR #4 (`4693c8f0`, 2026-03-29) added the dedicated Hermes session importer + fixed short-skill-name fuzzy matching.

The three importers are:
- **`ClaudeCodeImporter`** (external_importers.py:157-220) — reads `~/.claude/history.jsonl`, user prompts only, no assistant responses.
- **`CopilotImporter`** — `~/.copilot/session-state/*/events.jsonl`, full conversations including assistant turns.
- **`HermesImporter`** — `~/.hermes/sessions/*.json`, full conversation + tool context (the richest source).

All three pass through a `_contains_secret()` filter (external_importers.py:78-80) using a regex bank covering ~17 known token formats including `sk-ant-`, `ghp_`, `xoxb-`, `AKIA[0-9A-Z]{16}`, PEM keys, and `password=*** assignments. The relevance prefilter `_is_relevant_to_skill()` (external_importers.py:121-151) is keyword overlap between the message body and the skill name/description (≥2 keyword matches required).

**Borg implication:** the session importer is NOT useful for pack evolution. Borg already has a hand-curated 173-row corpus that is higher-signal than mined session prompts, and packs are matched against terse error strings, not multi-turn chats. Skip this entire 785-line module.

### 2.4 Guardrails (how forge enforces them)

| Guardrail | README claim (README.md:71-77) | Actual enforcement on disk |
|-----------|--------------------------------|---------------------------|
| Full test suite | "must pass 100%" | constraints.py:55-93 — shells out to pytest, 300s timeout, hardcoded `tests/` path |
| Size limits ≤15KB | "Skills ≤15KB, tool descriptions ≤500 chars" | constraints.py:95-117 — verified, hardcoded per artifact_type in config.py:26-29 |
| Caching compatibility | "No mid-conversation changes" | **Not enforced in code.** This is a deployment policy stated in PLAN.md:687-694, not a constraint check. |
| Semantic preservation | "Must not drift from original purpose" | **Not enforced in code.** PLAN.md:696-703 promises "semantic similarity checks in the fitness function" — these are not present in fitness.py. |
| PR review | "All changes go through human review" | **Not implemented.** `pr_builder.py` does not exist; evolve_skill.py:255-286 only writes files to `output/<skill>/<timestamp>/`. The human is expected to `git add` manually. |

**Three of the five marketed guardrails are not actually code yet.** Whatever Borg adopts must implement them itself — there is no scaffolding to inherit.

### 2.5 Target abstraction — pluggable or hardcoded?

**Hardcoded.** Three concrete pieces of evidence:

1. `SkillModule` (skill_module.py:84-114) is named after skills, hardcodes a `TaskWithSkill` signature (skill_module.py:94-102), and assumes the optimizable parameter is `skill_instructions` injected into a `dspy.ChainOfThought` call. There is no abstract `EvolvableTarget` base class.
2. `ConstraintValidator.validate_all()` (constraints.py:30-53) takes an `artifact_type` string ("skill", "tool_description", "param_description") and dispatches with `if artifact_type == "skill":` (constraints.py:50-51). No registry, no plugin hook. Adding a "pack" type is a literal `elif artifact_type == "pack":` line edit.
3. `SyntheticDatasetBuilder.generate()` accepts `artifact_type: str = "skill"` (dataset_builder.py:118) but the prompt template (dataset_builder.py:96-109) talks generically about "skill or tool description" — adding "pack" works, but the LLM generates `(task_input, expected_behavior)` tuples that are the wrong shape for a deterministic pack metric.

**Conclusion: forge has reusable infrastructure (~545 LOC across config/constraints/dataset_builder/fitness) but no pluggable target API. To add a "pack" target you copy-paste-modify `evolve_skill.py` and `skill_module.py` and add a new constraint branch.** This is a sidecar/fork question, not an integration question.

---

## 3. WHAT 'BORG PACK TARGET' WOULD LOOK LIKE

### 3.1 The pack format that needs to be evolvable

YAML frontmatter + markdown body, identical structural shape to forge's SKILL.md format. From `borg/seeds_data/null-pointer-chain.md:1-63`:

```yaml
---
type: workflow_pack
version: '1.0'
id: null-pointer-chain
problem_class: null_pointer_chain
framework: python
problem_signature:
  error_types: [AttributeError, TypeError]
  framework: python
  problem_description: "'NoneType' object has no attribute..."
root_cause:
  category: null_dereference
  explanation: "..."
investigation_trail:
- {file: ..., position: FIRST, what: ..., grep_pattern: ...}
resolution_sequence:
- {action: fix_upstream_none, command: ..., why: ...}
anti_patterns:
- {action: ..., why_fails: ...}
evidence:
  success_count: 47
  failure_count: 5
  success_rate: 0.9
  uses: 52
provenance: ...
---
## When to Use This Pack
...
```

**Key fields GEPA would mutate (in priority order):**

| Field | Mutation type | Why it matters for FCR |
|-------|---------------|------------------------|
| `error_signatures` (planned per ARCHITECTURE_SPEC.md §4.2 — not yet in v3.2.2 schema) | regex strings | Direct positive recall signal — what GEPA evolves to fire on the right errors |
| `anti_signatures` (planned) | regex strings | Direct false-confident suppression — what GEPA evolves to NOT fire on poison cases |
| `problem_signature.problem_description` | freeform text | Used by LLM-judge metric (not the deterministic FCR metric, but useful for human review) |
| `framework` | enum | Routes language detection; rare mutation |
| `investigation_trail` / `resolution_sequence` text | LLM-readable prose | Affects render quality, not FCR — Phase 2 of pack evolution |

**Critical: today's seed packs at `borg/seeds_data/*.md` do NOT have `error_signatures` or `anti_signatures` fields.** Those are Phase-1 PRD additions (ARCHITECTURE_SPEC.md §4.2 per SYNTHESIS_AND_ACTION_PLAN.md:87, 261). **The Borg pack target work is blocked on the Phase-1 schema migration**, OR the spike has to add those fields ad-hoc on the seed packs it operates on (recommended for the spike).

Pack sizes today: 2.4-3.3 KB (verified via `wc -c borg/seeds_data/*.md`). The 15 KB limit forge inherits (config.py:26) is comfortable.

### 3.2 The seed individuals (12 workflow_packs in `borg/seeds_data/`)

Verified file listing (19 .md files; 12 are `type: workflow_pack`, 7 are higher-level skill files like `borg/SKILL.md`, `guild-autopilot/SKILL.md`, `defi-yield-strategy.md`, etc., which would NOT be Borg pack targets):

```
borg/seeds_data/
├── circular-dependency-migration.md   3336 B  ← workflow_pack
├── configuration-error.md             2585 B  ← workflow_pack
├── import-cycle.md                    2693 B  ← workflow_pack
├── migration-state-desync.md          2876 B  ← workflow_pack
├── missing-dependency.md              ~2.4 KB ← workflow_pack
├── missing-foreign-key.md             2418 B  ← workflow_pack
├── null-pointer-chain.md              3166 B  ← workflow_pack
├── permission-denied.md               ~2.4 KB ← workflow_pack
├── race-condition.md                  2477 B  ← workflow_pack
├── schema-drift.md                    2515 B  ← workflow_pack  ← THE BUG SOURCE
├── timeout-hang.md                    ~2.5 KB ← workflow_pack
├── type-mismatch.md                   2595 B  ← workflow_pack
├── borg/SKILL.md                      (skill, not pack)
├── code-review.md                     (skill)
├── defi-yield-strategy.md             (skill)
├── defi-risk-check.md                 (skill)
├── guild-autopilot/SKILL.md           (skill)
├── systematic-debugging.md            (skill)
└── test-driven-development.md         (skill)
```

**The pack target sees only the 12 workflow_packs.** The skill files are out of scope (and would actually be the right target for a true forge integration if AB ever wants to evolve Borg's higher-level guild skills).

### 3.3 The eval dataset

- **`docs/20260408-0623_classifier_prd/error_corpus.jsonl`** — 173 rows, 9 languages, hand-curated by Green Team (DATA_ANALYSIS.md §1, SYNTHESIS_AND_ACTION_PLAN.md:11, conflict resolution #4 at line 338). Already on disk: `54402` bytes, 173 lines verified.
- **`borg/eval/e1a_seed_pack_validation.py`** — existing structural smoke test (currently at 582 lines) that loads SWE-bench Django tasks and matches them against problem_class taxonomy. **e1a is downgraded to a regression smoke test in v1; it stays green but does not gate releases (SYNTHESIS_AND_ACTION_PLAN.md disposition table line 342, conflict #8).**
- **`borg/eval/e1c_classifier_calibration.py`** — **does not exist yet.** Per the PRD (SYNTHESIS_AND_ACTION_PLAN.md Phase 2 deliverable, line 260), e1c is a Phase-2 deliverable that consumes `error_corpus.jsonl` and emits per-language precision/recall/F1/ECE/FCR. **The pack-target spike must either build e1c or stub a minimum-viable version against the corpus.**

### 3.4 The metric

Per-language FCR ≤ 2% (SYNTHESIS_AND_ACTION_PLAN.md §4 lines 99-118, headline release gate at line 124). FCR is defined as `#{wrong & conf > τ} / #{conf > τ}` (line 99). Headline secondaries:

- Per-language recall ≥ 60% on Py+JS+TS+Rust+Docker (line 115)
- ECE ≤ 0.05 per shipped language (line 116)
- Cross-language poison rate = 0% on dogfood reproductions (line 112)

**The forge fitness function (`skill_fitness_metric`, fitness.py:107-136) is a bag-of-words overlap heuristic and is the WRONG shape for FCR.** FCR is a confusion-matrix statistic over the entire corpus, not a per-example score. A pack mutation that improves FCR by 1% has to be evaluated holistically — you cannot score one (task_input, expected_behavior) pair and aggregate. The metric Borg needs is:

```python
def pack_fitness_metric(candidate_packs: list[Pack], corpus: list[ErrorRow]) -> float:
    results = [classify(row.text, packs=candidate_packs) for row in corpus]
    fcr_per_lang = compute_fcr_per_language(results, corpus)
    return -max(fcr_per_lang.values())  # minimize worst-language FCR
```

This is fundamentally a corpus-level evaluator, not an example-level one. **GEPA supports this** (it mutates candidates and re-runs the metric on the validation set), but the forge plumbing assumes per-example scoring via `dspy.Example`. Bypassing forge's `skill_fitness_metric` and `SkillModule` is non-negotiable for Borg.

### 3.5 The constraint gates

| Gate | Source | How forge would help | Verdict |
|------|--------|----------------------|---------|
| Existing 2862 borg tests pass | `pytest borg/tests` | constraints.py:55-93 already shells out to pytest with a 300s timeout — directly reusable, change `cwd` and the test path | ✅ Vendor as-is |
| e1a smoke test passes | `pytest borg/eval/e1a_seed_pack_validation.py` | Same shell-out pattern | ✅ Vendor + add second invocation |
| ECE ≤ 0.05 per shipped language | new e1c harness | forge has nothing | ❌ Build it |
| FCR ≤ 2% per shipped language | new e1c harness | forge has nothing | ❌ Build it |
| Pack size <15 KB | constraints.py:95-117 | Already enforced by `max_skill_size=15_000` | ✅ Reuse, rename to `max_pack_size` |
| Pack structure (frontmatter present, problem_class set) | constraints.py:150-174 | Hardcoded to skills (`name:`, `description:`); needs sibling `_check_pack_structure()` checking `problem_class:`, `framework:`, `error_signatures:` | ⚠️ Copy + modify (~30 LOC) |
| Pack growth ≤ 20% over baseline | constraints.py:119-134 | Already generic | ✅ Reuse |

### 3.6 Where the PR lands

`bensargotest-sys/guild-tools`, branch `borg/gepa-evolved-packs/{pack_name}`. **Forge has no PR generation code** (the promised `evolution/core/pr_builder.py` does not exist on disk; PLAN.md:151 lists it but `git/trees/main?recursive=1` confirms it is not in the tree). Borg has to build this itself — but it's ~30 lines of `subprocess.run(["gh", "pr", "create", ...])` and trivial. Suggested PR body: baseline FCR per language, evolved FCR per language, the unified diff of the mutated frontmatter, the e1c report, and a link to the spike output directory.

---

## 4. INTEGRATION STRATEGIES

| | A. Fork forge | B. Sidecar (forge as library) | C. Direct GEPA (no forge) | D. Upstream contribution |
|---|---|---|---|---|
| **Pros** | Full freedom to refactor; stays one repo | Pull upstream improvements for free; clean separation; lowest "vendor everything" debt | Smallest dependency surface; no impedance mismatch; ships fastest; matches what borg actually needs (corpus-level metric, deterministic classify()) | Best long-term — Borg becomes upstream's reference for non-skill targets; raises Borg's profile in the ecosystem |
| **Cons** | Maintenance debt: every upstream change is a merge conflict; abstractions you fork into don't exist yet (target API is hardcoded), so you'd be forking dead weight | Forge has no plugin/registry interface — you'd be importing private modules (`evolution.core.constraints.ConstraintValidator`) and praying they don't refactor; only ~545 LOC of forge is actually reusable for packs; SkillModule/skill_fitness_metric are wrong shape | You re-build orchestration (~250 LOC); duplicate of upstream effort if forge later adds a pack-shaped target | Slow (1-2 weeks of upstream review); requires forge to first design a target abstraction that doesn't exist; their roadmap (PLAN.md:54-60) is skills-tools-prompts-code, not "third-party targets" |
| **Effort (eng-hours)** | 25-40h: clone, add `evolution/packs/`, vendor e1c, modify constraint validator, set up CI to track upstream | 15-25h: pip install, write `borg/evolution/pack_target.py` adapter, monkey-patch constraint validator, build PR generator | 8-15h: vendor 175-line constraint validator, write `borg/evolution/evolve_pack.py` (~250 LOC), call `gepa.optimize()` directly | 60-100h: design + propose target API to upstream, write the PR, address review, then implement the Borg target on top |
| **Blast radius** | High — borg now lives downstream of a fork you maintain forever | Medium — if forge releases break, borg evolution breaks (but borg ship doesn't) | Low — internal to borg, no external dep on forge | Very high — couples Borg release schedule to NousResearch review velocity |
| **Dependency surface** | Entire forge tree (~1,800 LOC vendored) + dspy>=3.0.0 + gepa | hermes-agent-self-evolution PyPI package (does not exist on PyPI yet — would need git+https install) + dspy + gepa | dspy>=3.0.0 + gepa only; ~175 lines vendored from forge as static borg code | All of A's surface plus a soft dependency on upstream review/release cadence |

### Important factual qualifiers

- **Upstream is not on PyPI.** `pyproject.toml` declares `name = "hermes-agent-self-evolution"` but the package is install-from-git only. Strategy B's "pip install" is `pip install git+https://github.com/NousResearch/hermes-agent-self-evolution.git` — fragile.
- **The reusable surface area is ~545 LOC, not 1,800.** core/{config.py (72) + constraints.py (174) + dataset_builder.py (201) + fitness.py (146)} = 593 LOC, of which dataset_builder and fitness are wrong-shape for packs. The truly reusable pieces are constraints.py + small bits of config.py, ~200 LOC.
- **The "Hermes session importer" everyone is excited about (785 LOC, external_importers.py) is irrelevant to packs** — Borg already has a 173-row hand-curated corpus that beats anything you'd mine from chat logs.

---

## 5. RECOMMENDED PATH

**Strategy C — Direct GEPA inside borg, with ~175 LOC of constraint scaffolding vendored from forge.**

### Defense

1. **The forge wrapper does not solve Borg's hard problem.** Borg's hard problem is the corpus-level FCR metric and the e1c harness. Forge has neither and its `skill_fitness_metric` is structurally incompatible (per-example, bag-of-words). Forge's reusable surface (constraint validation + size/structure gates) is ~175 lines that we can vendor in a single sitting.
2. **Forge's target abstraction does not exist.** §2.5 above proves it: `SkillModule` is name-bound to skills, `ConstraintValidator` dispatches by hardcoded `artifact_type` strings, there is no `EvolvableTarget` base class. Adding a "pack" type to the upstream constraint validator is a 30-LOC change — but adding it to borg's vendored copy is the same 30 LOC and you don't owe anyone a fork merge.
3. **Forge is itself early.** Only Phase 1 of 5 is implemented (README.md:55-60 — Phases 2-5 are 🔲 Planned). PR generation, semantic preservation checks, caching compat, behavioral test gating — all marketed in the README, none in the code. You would be coupling Borg's release schedule to a project that hasn't shipped its second milestone.
4. **The parallel GEPA spike is doing C anyway.** This memo gives AB the *reason* C is right (not just "it's what we're doing") and tells him precisely which 175 LOC to vendor from forge so the spike doesn't have to write constraint plumbing from scratch.
5. **C lets Borg revisit B/D later at zero migration cost.** If forge adds a real target abstraction in Phase 2-3 (likely Q3 2026 based on PLAN.md timeline), Borg can swap the spike's orchestration for forge's wrapper without touching the metric or the corpus. The vendored constraint scaffolding becomes an upstream contribution in that future.
6. **Upstream contribution (D) is the right *long-term* answer but the wrong *now* answer.** When Borg has a working pack target validated against 173 rows and showing FCR < 2%, AB has the artifact to walk into NousResearch with. Today, all he has is a hypothesis and a corpus.
7. **Forking (A) is the worst of all worlds.** It doubles maintenance against a moving upstream that doesn't yet have the abstraction we'd want to fork.

### What we're explicitly NOT doing

- We are NOT taking a pip dependency on `hermes-agent-self-evolution` (it's not on PyPI; install-from-git is fragile).
- We are NOT importing `evolution.skills.SkillModule` (wrong shape — assumes LLM-rendered output).
- We are NOT calling `evolve_skill.py:evolve()` or any of its CLI flags (wrong loop; no PR generation; LLM-judge fitness).
- We ARE vendoring `evolution/core/constraints.py` (175 lines), with attribution + license header preserved (forge is MIT, compatible with borg).

---

## 6. CONCRETE STEP-BY-STEP (Strategy C)

**Numbered tasks. First one is doable in <30 min.**

1. **[~25 min — FIRST TASK]** Vendor `evolution/core/constraints.py` from forge into `borg/evolution/constraints.py`:
   - `mkdir -p borg/evolution && touch borg/evolution/__init__.py`
   - `curl -sS https://raw.githubusercontent.com/NousResearch/hermes-agent-self-evolution/main/evolution/core/constraints.py -o borg/evolution/constraints.py`
   - Replace `from evolution.core.config import EvolutionConfig` with a 5-line inline `BorgEvolutionConfig` dataclass with `max_pack_size=15_000`, `max_prompt_growth=0.2`.
   - Add a `_check_pack_structure(text)` method (mirror of `_check_skill_structure`, lines 150-174) that asserts `---` frontmatter + `problem_class:` + `framework:` keys present.
   - Wire up the `artifact_type == "pack"` branch in `validate_all()`.
   - Add the MIT license header from forge's pyproject.toml + `# Vendored from NousResearch/hermes-agent-self-evolution@<sha> on 20260408`.
   - Confirm import works: `python -c "from borg.evolution.constraints import ConstraintValidator; print('ok')"`.
   - **Exit criteria:** file exists, imports clean, no new pip deps, no test failures. This is the proof-of-life that the spike has touched ground.

2. **[~45 min]** Stub `borg/eval/e1c_classifier_calibration.py`:
   - Load `error_corpus.jsonl` (173 rows).
   - For each row, call `borg.core.pack_taxonomy.classify_error()` (the v3.2.2 path with the Phase-0 language guard).
   - Compute per-language FCR, recall, precision against the row's gold `problem_class` field.
   - Print a table; return the worst-language FCR as the headline metric.
   - **Exit criteria:** running it produces the same baseline numbers as DATA_ANALYSIS.md §3 (53.8% corpus FCR, 95.5% Rust FCR, 90.9% JS FCR pre-Phase-0; <10% post-Phase-0).
   - This is the metric function GEPA will optimize against.

3. **[~30 min]** Add `error_signatures: []` and `anti_signatures: []` empty fields to the 12 workflow_pack frontmatters in `borg/seeds_data/*.md`. Backfill with one obvious-correct regex for `null-pointer-chain.md` (e.g., `\bNoneType\b`) and `schema-drift.md` (e.g., `no such column`) so GEPA has a non-empty seed to mutate. **Exit criteria:** packs still load via `_init_cache()` (pack_taxonomy.py:240-272), e1a smoke test still passes.

4. **[~1 h]** Modify `pack_taxonomy.py:classify_error()` to score candidates against the `error_signatures` regex list (Phase-2-style scoring, but minimal — count signature hits as the score, no calibration yet). Behind a `BORG_USE_PACK_SIGNATURES=1` env var so the legacy keyword path is the default. **Exit criteria:** `BORG_USE_PACK_SIGNATURES=1 python -m borg.eval.e1c_classifier_calibration` runs and reports per-language FCR using the new path. e1a smoke test still passes with the env var off.

5. **[~2 h]** Write `borg/evolution/evolve_pack.py` (the orchestration; ~250 LOC):
   - `pip install gepa` (MIT, ~3 MB).
   - `load_pack(pack_path) -> dict` and `save_pack(pack_path, dict) -> None` for round-tripping YAML frontmatter.
   - `mutate_signatures(pack: dict) -> str` — serialize the `error_signatures` + `anti_signatures` lists into a single mutable string blob for GEPA.
   - `apply_mutation(pack: dict, mutated_blob: str) -> dict` — round-trip back into the pack dict.
   - `pack_fitness(packs: list[dict]) -> float` — the corpus-level FCR metric from step 2.
   - `gepa.optimize(initial_candidate=baseline_blob, metric=pack_fitness, max_iterations=10)` — main loop.
   - On exit, call `borg.evolution.constraints.ConstraintValidator.validate_all(evolved_pack_text, "pack", baseline_text=baseline)` and reject if any check fails.
   - Write `output/<pack_name>/<timestamp>/{evolved_pack.md, baseline_pack.md, metrics.json, e1c_report.txt}`.
   - **Exit criteria:** `python -m borg.evolution.evolve_pack --pack schema-drift --iterations 3` runs end-to-end on the smallest possible config and prints a baseline-vs-evolved FCR delta. Result might be zero improvement (the smoke test is "did the pipeline run", not "did it improve").

6. **[~1.5 h]** Run the spike on three packs in priority order: (a) `schema-drift.md` (the bug source — high signal because the baseline FCR is 95.5% on Rust), (b) `null-pointer-chain.md` (well-shaped Python pack — sanity check), (c) a placeholder Rust pack synthesized by hand (`rust-borrow-checker.md` from Phase-3 PRD list). Record per-pack baseline-vs-evolved FCR + pack diff size. **Exit criteria:** at least one of the three shows a measurable FCR delta (positive or negative — both are signal). If all three show zero delta, the corpus is too small or GEPA is misconfigured.

7. **[~1 h]** Build a minimal PR generator: `borg/evolution/pr.py` calls `gh pr create` against `bensargotest-sys/guild-tools` on branch `borg/gepa-evolved-packs/<pack_name>`. PR body includes the e1c table (baseline vs evolved per language), the unified diff of the frontmatter, the evolved pack text, total cost (sum of OpenAI/Anthropic API spend during the run), and a link to the spike output directory. **Exit criteria:** one real PR posted (probably WIP/draft) for the schema-drift pack with the spike result.

8. **[~30 min]** Write `borg/evolution/README.md` with: how to run the spike, where vendored code came from, how to upgrade vendored constraints from upstream, and the cost-per-iteration measured in step 6. Commit. Hand to AB.

**Total spike effort: ~6.7 eng-hours for steps 1-7, ~30 min for step 8 = ~7.2 hours start-to-finish.** Add ~50% slack for surprises = 10-11 hours wall clock.

**First task (step 1) is ~25 min and produces a single committed file with no new dependencies.** That is the cheapest possible "ground touched" milestone.

---

## 7. RISKS (top 5)

| # | Risk | Likelihood | Severity | Mitigation |
|---|------|------------|----------|------------|
| 1 | **Upstream API churn** — forge refactors `ConstraintValidator` shape, breaks vendored copy | Medium (the project is 30 days old and moving fast — 7 commits, no v1 tag) | Low (we vendored, not depended; upstream changes never break us) | Pin the SHA in the vendoring header; manually re-vendor monthly if upstream evolves |
| 2 | **GEPA eval cost per iteration** — running classify() 173 times × N candidates × M iterations could blow budget | Low for direct GEPA (the metric is local Python — no LLM calls); Medium if we add an LLM-judge stage for the prose fields | Low ($) for deterministic FCR; High ($50-200 per pack) if we LLM-grade the investigation_trail text | Spike uses ONLY the deterministic FCR metric (zero LLM cost); LLM-graded prose is a Phase-2 add-on with explicit budget |
| 3 | **Test-suite pollution from generated variants** — GEPA writes broken regex into `error_signatures`, somehow gets merged, breaks the 2862-test suite for everyone | Low (constraint gate runs pytest as pre-check; PR review catches the rest) | High (would block borg releases) | Two layers: (a) constraint validator runs `pytest borg/tests/` before accepting any candidate; (b) PR generator marks all evolved-pack PRs as DRAFT until human signs off; (c) `re.compile()` every regex at constraint-validation time and reject candidates that produce invalid patterns |
| 4 | **Pack semantic drift** — GEPA evolves a pack into a regex soup that achieves low FCR by being a no-op (matches nothing, so by definition the false-confident rate is zero) | High (this is the classic "metric hacking" risk — FCR-only objective doesn't penalize abstaining) | High (would silently regress recall) | Joint metric: maximize `recall - λ * FCR` rather than minimize FCR alone; reject any candidate whose recall drops > 5% from baseline; require min 3 unique non-trivial regexes per pack via the constraint gate |
| 5 | **Reputation / attribution risk if upstream changes license** — forge is MIT today but if NousResearch pivots to AGPL or proprietary, our vendored copy is fine but our PR-back-upstream story dies | Very Low (MIT is a strong default for ML infrastructure; PLAN.md:750-753 explicitly contrasts with Darwinian Evolver's AGPL) | Low (we don't depend on upstream at runtime; vendored code stays MIT under the original commit's license) | Capture forge's LICENSE file alongside the vendored constraints.py; commit both to borg with a note that the vendored slice is permanently MIT under commit `<sha>` regardless of upstream's future relicensing |

---

## 8. OPEN QUESTIONS FOR AB

1. **Are you OK with vendoring ~175 LOC from a 30-day-old upstream project, or do you want a hard "no third-party code in borg/" rule even for permissively-licensed snippets?** (If the latter, add ~2h to step 1 to write the constraint validator from scratch.)
2. **Is the spike allowed to add `error_signatures: []` and `anti_signatures: []` empty fields to the existing 12 seed packs, or does that count as touching the Phase-1 schema migration that the PRD says blocks pack evolution?** (If we can't touch the seed packs, the spike can only operate on synthesized packs and the result is less convincing.)
3. **What's the budget cap for the spike?** (My estimate is <$1 in API spend because the deterministic FCR metric calls zero LLMs — but if we add LLM-judged prose evolution in Phase 2, it's $5-20 per pack per run. I want explicit permission to add the LLM-judge in Phase 2, or explicit instruction to stay deterministic-only.)

---

## END OF DOCUMENT

**File path:** `/root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/HERMES_FORGE_INTEGRATION_PLAN.md`
**Recommended strategy:** **C** (Direct GEPA inside borg, vendor ~175 LOC from forge)
**First concrete task effort estimate:** **~25 min** (vendor `evolution/core/constraints.py` into `borg/evolution/constraints.py`, add `_check_pack_structure()`, confirm import works)
