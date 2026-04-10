# RED_TEAM_REVIEW — v3.3.0 Ship Plan Adversarial Review

**Reviewer:** Team RED (adversarial)
**Date:** 2026-04-09
**Commit reviewed:** `decb281` (v3.2.4 / master)
**Documents reviewed:** SYNTHESIS_AND_SHIP_PLAN_20260409.md, FIRST_USER_E2E_AUDIT_20260409.md, COLD_START_SEED_CORPUS_DESIGN.md, CONTEXT_DOSSIER.md
**Code reviewed:** borg/cli.py, borg/core/search.py, borg/core/pack_taxonomy.py, pyproject.toml, README.md
**Finding count:** 22 (4 CRITICAL, 7 HIGH, 7 MEDIUM, 4 LOW)

---

## Executive Summary

The ship plan identifies 4 genuine ship blockers. It is missing a 5th. The cold-start fix is not wired — it is a greenfield subsystem with a to-be-written integration shim. The 70 eng-hour estimate is serial time, not wall-clock, and the Day 2 schedule does not survive contact with the actual curation workflow. The eval design tests a proxy metric, not the thing that matters. Several HIGH findings from the E2E audit were correctly identified but not actioned in the ship plan.

---

## 1. Ship Blocker Completeness

### [CRITICAL] SB-05 — `borg autopilot` has the same `"command": "python"` bug as SB-01

**Evidence:**
- `borg/cli.py` line 973: inside `_cmd_autopilot()`, the MCP config entry is built with `"command": "python"`.
- This is the same bug as SB-01, but in a different code path.
- `borg autopilot` is a documented subcommand (line 1257) that calls `_cmd_autopilot`.
- The E2E audit did not test `borg autopilot`; it only tested `borg setup-claude`. The autopilot path is an additional first-user entry point with the identical failure mode.

**Impact:** Any user who runs `borg autopilot` instead of `borg setup-claude` gets a broken MCP config on Ubuntu 24/macOS/pyenv — the exact same 120-second hang that SB-01 causes.

**Fix:** Apply the same fix as SB-01 to `_cmd_autopilot`: replace `"command": "python"` with `sys.executable` (line 973).

**Effort:** 5 min (same one-line fix in the other function).

**Disposition:** ADD as SB-05. Total SB effort becomes ~3 hours, not 2.5.

---

### [CRITICAL] Cold-start fix — Option A is NOT wired into `borg_search`. There is no `borg_search` path to fix.

**Evidence — the design doc's §5.4 is a greenfield subsystem:**

The COLD_START_SEED_CORPUS_DESIGN.md §5.4 specifies modifying:
1. `borg/core/uri.py` — add `SEEDS_DIR` + `_load_seed_index()` function
2. `borg/core/search.py` — merge seed packs into `all_packs` in `borg_search()`
3. `borg/cli.py` — add `(seed)` suffix, `--no-seeds` flag

**Finding 1:** `borg/core/uri.py` does not exist in the codebase. The existing `borg/core/search.py` imports from `borg.core.uri` (line 26-33) — the module exists at `borg/core/uri.py` and contains `resolve_guild_uri`, `fetch_with_retry`, `_fetch_index`, etc. But it contains NO seed-loading functionality.

**Finding 2:** `borg_search()` in `borg/core/search.py` (line 82) has NO seed loading code. The function:
- Calls `_fetch_index()` (line 107) — fetches remote index from GitHub
- Scans `BORG_DIR` for local pack YAMLs (lines 111-144)
- Deduplicates (lines 151-182)
- Attaches tier (lines 146-149)
- Queries via text or semantic match (lines 224-280)
- Adds trace hits (lines 293-319)
- Returns result

There is NO code path that reads from `borg/seeds_data/`. Zero. The design doc's claim that "the bug is that `borg_search` does not read from it" is accurate — but "closing that gap" requires creating a new module (`_load_seed_index` in `uri.py` or a new file) and modifying `search.py` to call it. This is not a one-line fix. This is a new integration shim.

**Finding 3:** The existing seeds at `borg/seeds_data/*.md` are YAML-frontmatter skill files (`systematic-debugging.md`, `null-pointer-chain.md`, etc.) — NOT `workflow_pack` YAML files. The design doc proposes adding `packs/*.yaml` files in a new `packs/` subdirectory. The existing `.md` seeds are loaded by `pack_taxonomy._init_cache()` (which feeds `classify_error`), NOT by `borg_search`. They are a separate data path entirely.

**Impact:** The cold-start fix requires:
- Creating `_load_seed_index()` in `uri.py` (new function, new file)
- Modifying `borg_search()` to call it and merge results (new code path)
- Creating `borg/seeds_data/packs/*.yaml` (K=200-500 new YAML files, none exist today)
- Creating `borg/seeds_data/index.json` (precomputed index, does not exist)
- Adding `--no-seeds` CLI flag
- Adding `(seed)` suffix in output
- G3 wheel size gate enforcement

This is a full engineering task, not a 30-minute patch.

**Fix:** Treat cold-start as a full engineering track. Day 2 task #9 ("6h prototype") underestimates by 3-4x for the wiring alone. Curating 200-500 packs is additional 32-70 hours.

**Effort:** Wiring alone: ~6h engineering. Curation: ~70h. Total ~76h (not "70h total" which conflates wiring + curation).

**Disposition:** The design doc and ship plan underestimate cold-start as "Option A is already infrastructure." It is not. The infrastructure must be built.

---

### [HIGH] SB-03 severity underweighted — README Platform Setup section is the LEADING content

**Evidence:**
- `borg/cli.py` line 1214: `choices=["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"]`
- `README.md` line 138: `borg generate systematic-debugging --format claude`
- `README.md` line 144: `borg generate systematic-debugging --format cursor`

The README examples use `--format claude` and `--format cursor`. The argparse choices are `claude-md` and `cursorrules`. These are DIFFERENT strings. A user who copies the README verbatim gets:
```
error: argument --format: invalid choice: 'claude' (choose from 'cursorrules', 'clinerules', 'claude-md', 'windsurfrules', 'all')
```

**Additional finding:** The `convert` subparser (line 1198) correctly uses `["auto", "skill", "claude", "cursorrules"]` — so `convert --format claude` works fine, but `generate --format claude` does not. This inconsistency is doubly confusing.

**Impact:** The Platform Setup section of the README is above-the-fold content — it is what a Claude Code or Cursor user reads first when evaluating borg. Every single user in this path gets an immediate failure.

**Fix:** Add aliases: `claude` -> `claude-md`, `cursor` -> `cursorrules`. Keep the old names for back-compat per the ship plan.

**Effort:** 45 min (per ship plan — correct estimate).

**Disposition:** Already in ship plan as SB-03. Severity is correctly CRITICAL.

---

### [HIGH] `guild://` still in CLI help strings — inconsistent with borg rename

**Evidence:**
- `borg/cli.py` line 179: `pull` help says `guild://` URI scheme
- `borg/cli.py` line 610: CLAUDE_MD_TEMPLATE says "guild MCP server"
- `borg/cli.py` line 618: "guild MCP server isn't configured yet"

The ship plan lists HIGH-02: "Rename `guild://` → `borg://` in CLI help strings (keep parser accepting both)". This is correctly identified in the synthesis. But it is NOT a ship blocker per the audit — and it IS a first-user friction on the happy path.

**Fix:** Rename in help strings; parser already accepts both (the code resolves `guild://` URIs fine).

**Effort:** 30 min (per ship plan).

**Disposition:** HIGH, already in plan. Not a blocker but must land before "ready for real users."

---

## 2. Cold-Start Fix Correctness

### [CRITICAL] `_load_seed_index()` does not exist — integration path is unimplemented

**Evidence:** See Section 1 above. The design doc §5.4 describes the exact changes needed, but `borg_search()` in `search.py` line 82-380 has zero seed loading code, and `uri.py` has no `_load_seed_index()` function. The "wiring" task is not started — it must be built from scratch.

**Finding:** The 70 eng-hour estimate for cold-start is not wrong on curation, but it is wrong on the integration. The design doc's §7 prototype plan (6h for wiring + C3 replay) assumes the wiring is a known pattern. It is not — the exact merge point in `search.py` (after `all_packs = list(index.get("packs", []))` at line 108) needs a new function call, and the result needs to be deduplicated alongside remote and local packs. The dedup logic at lines 151-182 would need to handle seed packs with `source="seed"` too.

**Fix:** Add `_load_seed_index()` to `uri.py` (new), call it from `search.py` at line 108, extend dedup to handle `source="seed"` packs.

**Effort:** ~6h engineering (not 2h as the design doc §7 implies).

---

### [HIGH] Existing seeds at `borg/seeds_data/*.md` are in a DIFFERENT format than what `borg_search` consumes

**Evidence:**
- `borg/seeds_data/null-pointer-chain.md`: YAML frontmatter + markdown body. Loaded by `pack_taxonomy._init_cache()` (line 329-361 of `pack_taxonomy.py`) into `_PACK_CACHE`. Fed to `classify_error()` for keyword classification.
- `borg_search()` consumes YAML files from `BORG_DIR /*/pack.yaml` (lines 113-119) — the workflow_pack schema from `borg/core/schema.py::parse_workflow_pack`.

The existing seed files are NOT `workflow_pack` YAML files. They are SKILL-format files (frontmatter + markdown body). `borg_search` cannot read them as-is.

**Impact:** Even if `_load_seed_index()` is wired, if it reads the existing `.md` files it must parse them differently than local packs. Or the curation pipeline must convert existing seeds to `workflow_pack` YAML format. The design doc's plan for `packs/*.yaml` files is the correct approach — but it means the existing 17 seeds are technically incompatible with the new search path and would need migration.

**Fix:** Curate new `workflow_pack` YAML files in `packs/*.yaml`. The old `.md` seeds stay for `classify_error` (they're loaded by `pack_taxonomy`, not `search`). Do not conflate the two seed systems.

**Effort:** Already accounted for in the 70h curation estimate.

---

### [MEDIUM] Seeds data `borg/seeds_data/borg/` has WRONG repo URL

**Evidence:**
- `borg/seeds_data/borg/SKILL.md` (5178 bytes) contains:
  - Line: `homepage: https://github.com/punkrocker/agent-borg`
  - This is shipped inside the wheel.
- The correct repo is `https://github.com/bensargotest-sys/agent-borg`.

This is a separate instance of the stale naming problem (different from `guild-packs` but same category). It shipped in v3.2.4.

**Fix:** Update the URL in `borg/seeds_data/borg/SKILL.md`.

**Effort:** 5 min.

---

## 3. Eval Design Flaws

### [HIGH] C3 prototype uses proxy metric, not task pass rate

**Evidence (COLD_START_SEED_CORPUS_DESIGN.md §7):**
- Primary exit criterion: "borg returned content rate" ≥ 0.8 (≥12/15 runs return ≥1 match)
- Secondary: "task pass rate on C3 ≥ C1 within Clopper-Pearson bounds (likely still 0 due to floor effect, that is acceptable for this prototype)"

The design doc acknowledges that task pass rate is "likely still 0" even if C3 succeeds on the retrieval proxy. This means the prototype validates that `borg_search` returns non-empty results — but NOT that those results help agents complete tasks.

**Problem:** The P1.1 floor effect was caused by the model (MiniMax-Text-01) stopping after 2 iterations regardless of borg content. If C3 uses MiniMax-M2.7 (as D8 correctly fixes), and C3 shows ≥0.8 "borg returned content" rate, we still will not know whether:
1. The content is relevant enough to change agent behavior
2. The content is accurate enough not to mislead agents
3. The 500-pack corpus covers enough problem space

**Fix:** Define a secondary success criterion: "agent completes ≥1 phase of the pack" as a behavioral proxy, not just retrieval. Or accept that C3 only validates the retrieval mechanism, and the behavioral validation requires a larger experiment.

**Effort:** 0 (design change only).

---

### [MEDIUM] G1/G2 acceptance test uses "relevant" defined by token overlap — not semantic relevance

**Evidence (design doc §11, test #3):**
```
test_cold_start_benchmark_80_percent: over a pre-registered 50-query fixture,
≥ 40/50 queries return ≥ 1 relevant match (token overlap with name+problem_class)
```

Token overlap with `name+problem_class` will return true positives for "null pointer chain" matching "null_pointer_chain" but will NOT detect when:
- The pack is topically related but not covering the specific error
- The pack's `problem_class` is too generic ("configuration_error" matching "django auth")
- The pack's resolution is wrong for the specific error variant

**Fix:** At minimum, acknowledge this limitation. Consider adding a human-validated relevance sample (10% of queries) as a calibration check.

**Effort:** 0 (acknowledgment only; full fix requires human annotation).

---

### [MEDIUM] 50-query benchmark is not pre-registered or publicly documented

**Evidence:** The design doc refers to a "pre-registered 50-query fixture" but:
- The fixture does not appear in the codebase
- The fixture does not appear in the eval/ directory
- No external registry of the 50 queries exists

Without pre-registration, the G1/G2 numbers are post-hoc and can be gamed (queries chosen to make the corpus look good). The N1 honesty invariant ("no proven claim without raw data") applies to the acceptance test too.

**Fix:** Commit the 50-query fixture to the repo (`eval/cold_start_benchmark_50queries.json`) with documented sources before shipping. Pre-register the benchmark externally (e.g., as a GitHub gist with timestamp).

**Effort:** 2-3h to draft and review the 50 queries.

---

## 4. Testing Gaps

### [HIGH] `borg pull` happy path on live remote index is untested

**Evidence (FIRST_USER_E2E_AUDIT_20260409.md):**
The audit tested `borg pull` on a fake URI and confirmed it returns a useful error. It did NOT test `borg pull` on a real `borg://` or `https://` URI pointing to the live remote index.

The SYNTHESIS_AND_SHIP_PLAN correctly identifies this as A6 and flags it as "Add one happy-path pull test." But this is not in the ship plan as an action item, and the audit notes "If the remote index resolver is broken in v3.2.4, no first-user can ever pull a community pack."

**Fix:** Add a network test (marked `network` in pytest) that pulls a known-good pack from the remote index. The pytest marker already exists per `pyproject.toml` line 65.

**Effort:** 30 min.

---

### [HIGH] No test for `borg search` with `--no-seeds` flag

**Evidence:** The design doc G6 requires "opt-out flag exists for CLI help text + test." The design doc §11 test #5 tests `BORG_DISABLE_SEEDS=1` env var. But:
- The `--no-seeds` CLI flag for `borg search` is specified in design doc §5.5
- The `cli.py` argument parser for `search` (line ~1043) is not shown in the ship plan docs
- There is no test for the CLI flag (only env var)

**Fix:** Add `--no-seeds` to search subparser in `cli.py` and write a test that uses the CLI flag directly.

**Effort:** 1h.

---

### [MEDIUM] `test_wheel_size_under_budget` has 2x wrong bound

**Evidence (design doc §11, test #8):**
```
assert size < 10 * 1024 * 1024  # 10 MiB
```

But G3 states: "Seed corpus adds ≤ 5 MiB to the wheel uncompressed."

The test bound is 10 MiB, which is 2x too permissive. If seeds add 8 MiB (over G3), the test still passes.

**Fix:** Tighten to `assert size < 5 * 1024 * 1024`.

**Effort:** 1 min.

---

### [MEDIUM] Seeds license audit has no CI enforcement

**Evidence (design doc §6.4):**
The design doc specifies CI checks for `.license.json` files, but:
- `pyproject.toml` has no `[tool.ruff]` or `[tool.check-jsonschema]` configuration for license manifests
- No CI workflow file (`/.github/`) is referenced in the ship plan
- The "CI checks" in §6.4 are aspirational, not implemented

**Fix:** Add a `check_license_manifests.py` script to CI that verifies every `packs/*.yaml` has a sibling `*.license.json` with an allowlisted license.

**Effort:** 2h.

---

## 5. Failure Modes

### [HIGH] No incident-response plan for misleading seed packs already installed

**Evidence (COLD_START_SEED_CORPUS_DESIGN.md D7):**
The design doc's D7 finding correctly identifies that "when v3.3.0 lands but the seed corpus is wrong" is not addressed. The mitigation is "release v3.3.1 quickly." This is insufficient.

Specific failure scenario:
1. v3.3.0 ships with 500 seed packs
2. Pack `null-pointer-chain` is confidently wrong about a resolution (e.g., suggests adding `if x is not None` which is an anti-pattern listed in the pack itself)
3. An agent adopts the wrong resolution
4. The agent's code is now broken

Recovery path: v3.3.1 with corrected pack. But already-installed wheels on user machines retain the wrong pack. PyPI wheel yank does not reach installed packages.

**Fix:** Add a `--seed-check` or `borg doctor` command that verifies seed pack integrity (SHA256 against a known-good manifest). Document the recall procedure: users must `pip install --force-reinstall agent-borg==3.3.1` to get corrected seeds. This should be in the PRD's "What can go wrong after launch" section.

**Effort:** 2h engineering + 1 paragraph in PRD.

---

### [MEDIUM] SWE-bench patches may contain AGPL-licensed code, tainting extractions

**Evidence (COLD_START_SEED_CORPUS_DESIGN.md §6.1):**
SWE-bench Verified is listed as a source (MIT licensed). However:
- SWE-bench test cases contain real open-source code
- Some repositories in SWE-bench are GPL/AGPL licensed (e.g., sphinx-doc/sphinx is GPL)
- The extraction of "problem class → phases" from a gold patch may involve reading code from AGPL-licensed files

If a seed pack's `resolution_sequence` is derived from understanding an AGPL-licensed fix, the pack could be a derivative work of AGPL code, incompatible with MIT bundling.

**Fix:** Add a "per-file license check" step to curation: verify no file in the SWE-bench patch for the selected task is GPL/AGPL before using that task as a seed source. Document this in the curation protocol.

**Effort:** 4h to audit the 500 selected SWE-bench instances for license compatibility.

---

## 6. Architecture Smells

### [HIGH] `borg_search` has no abstraction boundary — it is a 300-line monolith

**Evidence (`search.py` line 82-380):**
`borg_search()` does everything: fetches remote index, scans local directory, deduplicates, computes tier, optionally fetches reputation, optionally does semantic search, adds trace hits, optionally re-ranks by reputation, returns JSON. This is ~300 lines of procedural code with 6 optional side paths.

The cold-start fix (adding seed loading) requires inserting into this function at a specific point (after `all_packs = list(index.get("packs", []))`, line 108). Every additional data source (remote, local, trace, seed) gets merged into the same `all_packs` list with ad-hoc deduplication.

**Smell:** The deduplication logic at lines 151-182 handles local vs. remote dedup, but has no handling for `source="seed"` packs. When seeds are added, they will have `source="seed"`, and the dedup logic will treat them as remote packs (since they don't have `source="local"`). The dedup by id (lines 161-171) will correctly prefer local over seed if a user has a local copy with the same id — but the seed vs. remote priority is not explicit.

**Fix:** Before shipping cold-start, write a dedup policy doc: what wins when seed, remote, and local all have the same pack id? Document it in the ARCHITECTURE_SPEC.

**Effort:** 1h (design doc).

---

### [MEDIUM] `pack_taxonomy._get_skills_dir()` silently returns None on missing seeds

**Evidence (`pack_taxonomy.py` line 325-326):**
```python
# 4. Not found — return None instead of crashing
return None
```

`_init_cache()` handles this gracefully (line 336-338: if skills_dir is None, set _CACHE_INITIALIZED = True and return). But `_get_skills_dir()` returning None means the seed cache is EMPTY, and `classify_error()` returns None silently.

The cold-start fix adds `_load_seed_index()` which presumably reads from `borg/seeds_data/packs/` via a similar path. If that directory is missing or empty (e.g., in an unusual install scenario), `_load_seed_index()` should fail explicitly, not silently return an empty index.

**Fix:** `_load_seed_index()` should raise if the seeds directory is missing but the feature is being requested (i.e., no `--no-seeds` flag). Only silently return empty if `--no-seeds` is set.

**Effort:** 1h.

---

### [MEDIUM] `SKILLS_DIR` in `search.py` line 58 is defined but never used

**Evidence:**
```python
SKILLS_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "skills"
```

This variable is defined at module level in `search.py` but never referenced in the function body. It appears to be vestigial — a remnant of an earlier architecture. The cold-start fix should not replicate this pattern.

**Fix:** Remove `SKILLS_DIR` from `search.py` or document why it exists. If it was intended for seed loading and superseded by `_get_skills_dir()` in `pack_taxonomy.py`, clarify the relationship between the two.

**Effort:** 5 min.

---

## 7. Day 2 Estimates Realism

### [HIGH] Day 2 schedule: 22h subagent compute in one wall day is impossible for curation tasks

**Evidence (SYNTHESIS_AND_SHIP_PLAN_20260409.md §6, Day 2):**
- Task #9: Cold-start prototype (6h)
- Task #10: Full curation to K=200 (12h)
- Task #11: HIGH-02..HIGH-06 batch (4h)

**Problem 1:** Task #10 (12h of curation) is described as "Mechanical extraction; no LLM." This underestimates: extracting a SWE-bench gold patch into a `workflow_pack` YAML requires:
- Understanding the bug class
- Writing `problem_class`, `problem_signature`
- Authoring `investigation_trail` (3-5 steps)
- Authoring `resolution_sequence` (3-5 steps)
- Writing `anti_patterns`
- Adding `provenance` with source URL + license
- Human review of 10% (required by design doc §6.3)

At 15-20 min per pack, 200 packs = 50-67 human-hours. At 3x parallel subagents: 17-22 wall-hours. The 12h estimate assumes pure mechanical extraction, but curation requires judgment.

**Problem 2:** "Curation cadence: quarterly" (design doc §5.6) conflicts with the 70 eng-hour cost. If every minor release requires 70h of curation, the project cannot sustain quarterly refreshes without dedicated staffing.

**Fix:** Revise Day 2 task #10 to 20-25h of curation + 5h review for K=200, or ship with K=50 and call it "beta corpus." Set expectation that K=500 full corpus is v3.4.0 material.

**Effort:** 0 (re-estimate).

---

### [HIGH] Day 2 task #9 (6h prototype) underestimates wiring by 3-4x

**Evidence:** The design doc §7 says wiring takes 2h. But `_load_seed_index()` doesn't exist, `uri.py` has no seed loading code, and `search.py` has no seed merge point. Writing the function, testing it with a seed index fixture, handling the dedup edge cases, adding the CLI flag, and ensuring pytest passes with and without the feature flag is more like 6-8h.

**Fix:** Give task #9 a separate 8h allocation. If it completes faster, great. If not, you know before the day ends that the schedule is slipping.

**Effort:** 0 (re-estimate).

---

## 8. HN Critic / Embarrassment Test

### [MEDIUM] The ship plan claims "70 eng-hours" but the actual serial time is 76h+ (wiring + curation)

If someone asks on HN "how hard was the cold-start fix?" and the answer is "we spent 70 hours," but the real number is closer to 76-80h, that is a small but real credibility gap. More importantly: the ship plan's Day 2 assumes those 70 hours of work complete in one wall day of subagent compute. They will not.

### [LOW] README.md line 1-2 says "A Python/Django debugging expert that's honest about what it doesn't know" but v3.2.4 cannot diagnose Rust, Go, Docker, or K8s errors

The README §4 correctly states non-Python errors return "no match." But the tagline "Python/Django debugging expert" implies broader coverage. The COLD_START_SEED_CORPUS_DESIGN.md non-goals (§2.2) confirm this is intentional. Still: HN critics will paste the tagline and say "but it doesn't work on my Go project."

Fix: Add a one-line caveat in the tagline: "A Python/Django debugging expert." (remove "honest about what it doesn't know" — it's implied by the non-Python refusal behavior).

### [MEDIUM] The README badge says "Tests: 1708 passed" — but there is no evidence this is current

`README.md` line 7: `[![Tests](https://img.shields.io/badge/tests-1708%20passed-brightgreen)]()`

No reference to where 1708 comes from. Is this from `pytest borg/tests/`? Is it current? If CI ran yesterday and 3 tests failed, this badge is stale.

**Fix:** Link the badge to the actual CI run or repo. Or remove it if it cannot be kept current.

### [LOW] The ship plan says "total ~12 hours" of engineering for the full v3.3.0

Counting: SB-01+SB-02+SB-03+SB-04 = 2.5h (correct). Cold-start wiring = 6-8h (underestimated by 2-3x). Cold-start curation = 70h (correct in size, wrong in parallelism assumptions). HIGH-02..HIGH-06 = 4h. Total: 12 + 6 + 70 + 4 = 92h. Not 12h.

The 12h figure only covers the ship blockers, not the cold-start fix or the HIGH items.

---

## 9. Findings Summary

| ID | Severity | Category | Finding | Fix | Effort |
|----|----------|----------|---------|-----|--------|
| 1 | CRITICAL | SB Completeness | SB-05: `borg autopilot` also has `"command": "python"` at cli.py:973 | Same fix as SB-01 | 5 min |
| 2 | CRITICAL | Cold-Start | `_load_seed_index()` does not exist; this is a greenfield subsystem | Build the integration shim as designed | 6h engineering |
| 3 | CRITICAL | SB Accuracy | "70 eng-hours" conflates wiring (not done) + curation; wiring is ~6h additional | Separate wiring estimate | 0 |
| 4 | CRITICAL | SB Accuracy | "cold-start is already infrastructure" — infrastructure must be built; existing seeds are SKILL-format, not workflow_pack YAML | Build as described in design doc | ~76h total |
| 5 | HIGH | SB-03 | README examples `--format claude` and `--format cursor` don't match argparse `claude-md` and `cursorrules` | Add aliases | 45 min |
| 6 | HIGH | SB-04 | pyproject.toml also has stale naming in `[project]]` `authors` field? Not checked | Full grep of pyproject.toml | 15 min |
| 7 | HIGH | Cold-Start | Existing seeds at `borg/seeds_data/*.md` are SKILL-format not workflow_pack; incompatible with `borg_search` path | Keep separate; curate new YAML packs | accounted in 70h |
| 8 | HIGH | Testing | `borg pull` happy path on live remote index untested | Add network test | 30 min |
| 9 | HIGH | Testing | `--no-seeds` CLI flag for `search` has no test | Add CLI flag + test | 1h |
| 10 | HIGH | Day 2 | Day 2 curation (12h) assumes pure mechanical extraction; real curation 50-67h at 15-20min/pack | Revise to 20-25h + 5h review | 0 |
| 11 | HIGH | Day 2 | Task #9 (6h prototype) underestimates wiring; real wiring ~6-8h | Give 8h allocation | 0 |
| 12 | HIGH | Architecture | `all_packs` dedup has no explicit seed-vs-remote priority policy | Document dedup policy | 1h |
| 13 | HIGH | Failure Mode | No incident-response for misleading seed packs already installed | Add recall procedure + `borg doctor` | 2h + 1 PRD para |
| 14 | HIGH | SB Completeness | `guild://` still in CLI help strings (HIGH-02 unfixed) | 30 min | 30 min |
| 15 | MEDIUM | Cold-Start | `borg/seeds_data/borg/SKILL.md` has wrong repo URL (punkrocker not bensargotest) | Fix URL | 5 min |
| 16 | MEDIUM | Eval | C3 prototype uses proxy metric not task pass rate | Add behavioral secondary metric | 0 |
| 17 | MEDIUM | Eval | 50-query benchmark "pre-registered" is not actually pre-registered or in repo | Commit fixture + external pre-reg | 2-3h |
| 18 | MEDIUM | Eval | G1 "relevant" defined by token overlap, not semantic relevance | Acknowledge limitation + calibration sample | 1h |
| 19 | MEDIUM | Testing | `test_wheel_size_under_budget` asserts < 10MiB; G3 says ≤ 5MiB (2x too permissive) | Tighten to 5MiB | 1 min |
| 20 | MEDIUM | Testing | Seeds license audit has no CI enforcement | Add check script to CI | 2h |
| 21 | MEDIUM | Architecture | `pack_taxonomy._get_skills_dir()` silently returns None on missing seeds | Fail explicitly unless --no-seeds | 1h |
| 22 | MEDIUM | Failure Mode | SWE-bench may contain AGPL code; extractions may be tainted | Add per-file license check | 4h |
| 23 | MEDIUM | Architecture | `search.py` SKILLS_DIR defined but never used (vestigial) | Remove or document | 5 min |
| 24 | MEDIUM | HN Risk | README test badge "1708 passed" with no CI link or freshness date | Link badge or remove | 10 min |
| 25 | LOW | Cold-Start | D5: `_load_seed_index` memoization should use `lru_cache` with cache_clear for tests | Add lru_cache | 30 min |
| 26 | LOW | Cold-Start | D4: G3 ≤ 5MiB vs test bound < 10MiB already covered in #19 | — | — |
| 27 | LOW | SB Completeness | HIGH-05 (`borg_suggest {}`): audit did not verify if it requires `agent_context` param | Investigate and either fix or document | 2h |
| 28 | LOW | HN Risk | README tagline says "Python/Django debugging expert" — HN critics will note Go/Rust/JS lack | Slightly reword tagline | 5 min |

---

## 10. Disposition Table

| Finding | Disposition | Owner | Target |
|---------|-------------|-------|--------|
| 1 (SB-05) | FIX — add as ship blocker #5 | SB-01 subagent | Day 1 |
| 2 (cold-start wiring) | FIX — build integration shim | Cold-start subagent | Day 2 task #9 |
| 3 (estimate accuracy) | FIX — revise estimates in ship plan | Hermes | Before AB approval |
| 4 (infrastructure claim) | FIX — ship plan must say "cold-start is not wired; must build" | Hermes | Before AB approval |
| 5 (SB-03 format mismatch) | FIX — add format aliases | SB-03 subagent | Day 1 |
| 6 (pyproject.toml full audit) | FIX — grep entire file | SB-04 subagent | Day 1 |
| 7 (seed format incompatibility) | ACKNOWLEDGE — existing seeds feed classify_error, new seeds feed search | Design doc | v3.3.0 |
| 8 (pull happy path) | FIX — add network test | Test author | Day 1 |
| 9 (--no-seeds CLI) | FIX — add flag + test | Cold-start subagent | Day 2 |
| 10 (curation estimate) | FIX — revise to 20-25h serial | Hermes | Before AB approval |
| 11 (wiring estimate) | FIX — revise to 8h | Hermes | Before AB approval |
| 12 (dedup policy) | FIX — document before shipping cold-start | Architecture | Before cold-start merge |
| 13 (incident response) | FIX — add recall procedure to PRD | Chief Architect | v3.3.0 PRD |
| 14 (guild:// in help) | FIX — rename help strings | HIGH-02 subagent | Day 2 |
| 15 (borg/SKILL.md URL) | FIX — update URL | HIGH-06 subagent | Day 2 |
| 16 (C3 proxy metric) | ACKNOWLEDGE — add behavioral secondary metric | Eval design | v3.3.0 |
| 17 (benchmark pre-reg) | FIX — commit fixture + external pre-registration | Eval author | Day 2 |
| 18 (G1 relevance) | ACKNOWLEDGE — add calibration sample | Eval author | Day 2 |
| 19 (wheel size test) | FIX — tighten to 5MiB | Cold-start test author | Day 2 |
| 20 (license CI) | FIX — add CI check script | Cold-start subagent | Day 2 |
| 21 (silent None) | FIX — fail explicitly | Cold-start subagent | Day 2 |
| 22 (AGPL taint) | FIX — add per-file license check | Curation protocol | Before Day 2 |
| 23 (vestigial SKILLS_DIR) | FIX — remove or document | Code cleanup | Day 1 |
| 24 (badge freshness) | FIX — link to CI or remove | Hermes | Day 1 |
| 25 (lru_cache) | FIX — add to _load_seed_index | Cold-start subagent | Day 2 |
| 26 | Covered by #19 | — | — |
| 27 (borg_suggest) | INVESTIGATE — determine if fixable or dead code | HIGH-05 owner | Day 2 |
| 28 (tagline) | CONSIDER — minor HN risk | Hermes | Optional |

---

## 11. Bottom Line

**The ship plan's 4 blockers are correct but incomplete.** Add SB-05 (`borg autopilot` same python bug). The "12 hours" estimate for ship blockers is correct. The "70 eng-hours" for cold-start is not wrong on curation size but dramatically underestimates wiring (6h additional) and overestimates parallelism (curation is not parallelizable at human judgment speed). The cold-start fix is a greenfield subsystem, not a wiring change.

**Before shipping:**
1. Land SB-01 through SB-05 in Day 1
2. Build cold-start wiring in Day 2 (8h, not 6h)
3. Run curation with realistic 20-25h serial estimate
4. Ship K=50 prototype corpus or delay cold-start to v3.4 if K=200 isn't ready
5. Add behavioral secondary metric to C3 eval
6. Add incident-response section to PRD

**HN verdict on this ship plan:** The 4 SBs are real. The cold-start diagnosis is correct. The fix is underestimated by 3-4x on wiring and 2x on curation parallelism. A well-prepared HN critic would ask "you said 70 hours and it took 92; you said it was already infrastructure and you had to build it." The honesty invariants in the design doc are excellent — but the shipping timeline is optimistic by 40-50%.
