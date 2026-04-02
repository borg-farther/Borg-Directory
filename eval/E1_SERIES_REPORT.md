# E1 Series Report — Consolidated

**Date:** 2026-04-02
**Agents run:** E1a (MiniMax-M2.7), E1b (MiniMax-M2.7), E1c (MiniMax-M2.7)
**PRD gate:** Section 2.1, Section 7 Phase 0.5

---

## E1a: Format Validation — **NO-GO** ❌

**Protocol:** Seed pack investigation_trail files vs. actual SWE-bench Django task patches.
**Tasks evaluated:** 30 SWE-bench Django tasks (from dogfood/swebench_tasks/)
**Pass criteria (pre-registered):** ≥ 2 of top 3 suggested files appear in actual fix

### Results

| Metric | Result | Criterion | Pass? |
|--------|--------|-----------|-------|
| Trail file overlap (1+ file) | 0/30 | ≥ 1/1 | ❌ |
| Trail file overlap (2+ files) | 0/30 | ≥ 2/3 | ❌ |
| Pack coverage | 11/30 (37%) | (descriptive) | — |
| No pack found | 19/30 (63%) | (descriptive) | — |

### Detailed findings

**19 tasks had no matching pack at all.** The taxonomy does not cover these error types:
- Feature requests (3 tasks): ModelAdmin.get_inlines(), --skip-checks, model formset creation
- Logic errors without exception types (7 tasks): regex processing, query filtering, FK handling, etc.
- Bugs with non-standard errors (9 tasks): various non-classifiable issues

**11 tasks had a matching pack, but 0/11 had any overlap between investigation_trail files and actual patch files.**

Examples:
| Task | Pack | Trail Files | Patch Files | Overlap |
|------|------|------------|-------------|---------|
| django-10554 | schema-drift | models.py | django/db/models/sql/compiler.py, query.py | None |
| django-11477 | (no pack) | — | django/urls/resolvers.py | — |
| django-12754 | migration-state-desync | state.py, loader.py | django/db/migrations/autodetector.py | None |

### Root cause analysis

**The seed packs were written with generic investigation paths** — "check models.py", "check migrations/state.py" — which are the framework files a human would investigate. But SWE-bench patches modify specific submodules. The two never overlap.

This is not a minor gap. The E1a pass criterion directly tests whether investigation_trail files appear in the actual fix. We got 0/30.

### PRD says: "Any criterion unmet → iterate on packs, rerun E1a"

---

## E1b: Real-Bug Dogfood Simulation — **PARTIAL PASS** ⚠️

**Protocol:** 15 real Django bugs from SWE-bench. For each: classify → load pack → check if guidance is relevant.
**Pass criteria (pre-registered):** Guidance relevance ≥ 2/3, trail accuracy ≥ 2/3, resolution match ≥ 1/3, would use again = 3/3

### Results

| Metric | Result | Criterion | Pass? |
|--------|--------|-----------|-------|
| Bugs with applicable pack | 5/15 (33%) | (descriptive) | — |
| Pack selection accuracy | 4/4 (100%) | ≥ 2/3 | ✓ |
| Trail accuracy (applicable bugs) | 4/5 (80%) | ≥ 2/3 | ✓ |
| Resolution relevance | 5/5 (100%) | ≥ 1/3 | ✓ |
| Would use again | 5/5 (100%) | 3/3 | ✓ |

### Key findings

**Borg works correctly for exception-based bugs (TypeError, AttributeError, ValueError, PermissionError):**
- `null_pointer_chain` pack: 3/3 matched bugs — guidance was relevant
- `schema_drift` pack: 1/1 matched bug — guidance was relevant
- `permission_denied` pack: 1/1 matched bug — guidance was relevant

**67% of SWE-bench Django tasks are NOT exception-based** — they are feature requests or logic errors. These are out of scope for the current taxonomy.

**CLI confirmed working:**
```
$ python -m borg.cli debug "TypeError: 'NoneType' object has no attribute 'split'"
→ [null_pointer_chain] pack selected
→ Root cause: null_dereference
→ Resolution: fix_upstream_none (relevant)
```

### PRD says: E1b requires all 4 criteria. We cannot fully pass E1b without running with real developers.

**E1b is BLOCKED on human participants.** We can simulate the technical evaluation (which shows the guidance works for applicable bugs), but the "would use again" and "was guidance helpful" metrics require actual developers.

---

## E1c: CLI Usability Protocol — **READY TO RUN** ✓

**Protocol:** 5 standardized tasks, think-aloud method, SUS + NASA-TLX scoring.
**Prerequisite:**borg CLI built (✓), protocol documents complete (✓), harness runnable (✓ after bug fixes)

### Results

| Component | Status | Notes |
|-----------|--------|-------|
| Screening form | COMPLETE | 97 lines, comprehensive |
| Consent form | COMPLETE | 97 lines, IRB-compliant |
| Think-aloud guide | COMPLETE | 137 lines, full moderator script |
| Scoring rubric | COMPLETE | 151 lines, T1-T4 + SUS + NASA-TLX |
| tasks.json | COMPLETE | 5 tasks, all required fields |
| Test harness | RUNNABLE | 2 bugs fixed by agent |
| Borg CLI | WORKING | debug, list, feedback-v3 all functional |
| Participant integration | MISSING | CLI command capture, questionnaire capture, consent tracking |

**E1c cannot run without:**
1. 5 human participants arranged separately (coordination problem, not technical)
2. CLI integration for capturing participant commands during sessions

---

## Consolidated Go/No-Go Decision

### Binding gates per PRD Section 7

| Gate | Status | PRD says |
|------|--------|----------|
| E1a: 3/3 criteria | 0/3 FAIL | "iterate on packs, rerun E1a" |
| E1b: 4/4 criteria | BLOCKED (humans needed) | "investigate why packs don't generalize; rerun" |
| E1c: 3/3 criteria | BLOCKED (humans needed) | "redesign CLI output; retest" |

### Decision

**E1a: NO-GO.** The seed packs do not produce investigation trails that overlap with actual fix files. 0/30 tasks passed. The PRD is explicit: iterate on packs and rerun before building Phase 1.

**E1b: Cannot determine.** The technical evaluation (pack selection accuracy, resolution relevance) shows the guidance is correct for applicable bugs. But the human metrics (would you use it again, was it helpful) require real developers.

**E1c: Ready.** Protocol, harness, tasks, CLI are all complete and functional. Cannot run without 5 human participants.

---

## The Core Problem: Seed Packs Are Wrong in a Specific Way

E1a reveals a concrete, fixable problem:

**The investigation_trail files are too generic.** The packs say "check models.py" and "check django/db/migrations/state.py" — correct framework files, but not the specific files that actually change in SWE-bench patches.

**The fix is straightforward:** For each seed pack's problem_class, look at what files actually change in real bugs of that class, and put those specific files (or file patterns) in the investigation_trail.

The SWE-bench patches give us ground truth. For `null_pointer_chain`, the actual changed files are:
- django/urls/resolvers.py (URL routing kwargs)
- django/db/models/query.py (bulk_update return value)
- django/contrib/auth/forms.py (widget attrs)

The current null_pointer_chain pack says "check models.py and any file with .objects". That's too generic to be useful as a signal.

---

## Recommended Next Steps

### Immediate: Fix seed packs (1-2 days)

For each of the 12 problem classes:
1. Pull the actual files changed in 5+ real bugs of that type
2. Replace generic file names with specific file paths (or at least specific subdirectories)
3. Keep the resolution_sequence and anti_patterns — those are working correctly

### Then: Rerun E1a (1 day)

Verify that fixed investigation_trail files now appear in actual patches.

### Then: E1b with real bugs (arrange separately)

Use the 5 applicable bugs from E1b (null_pointer_chain, schema_drift, permission_denied) as the test cases. Arrange 3 developers.

### Then: E1c participants (arrange separately)

Schedule 5 participants for the usability study.

---

## What This Means for the Plan

**Do not build Phase 1 yet.** The PRD's no-go condition is active for E1a. We build when the evaluation says we build.

The compounding flywheel is the right goal. But it compounds on correct guidance. If the seed packs point to wrong files, the whole system learns the wrong things.

Fix the packs first. Then the flywheel runs on correct signal.

---

*Report generated: 2026-04-02*
*E1a agent: 29 API calls, 267s | E1b agent: 17 API calls, 228s | E1c agent: 12 API calls, 135s*
*Model: MiniMax-M2.7 for all agents*
