# Borg Brain Specification
## From Cookbook to Collective Intelligence

Date: 2026-03-27
Status: SPECIFICATION
Version: 1.0

---

## Overview

Borg currently delivers static YAML workflow packs — instructions an agent
reads and hopefully follows. This spec defines 4 features that transform
borg from a cookbook into a brain: conditional logic, file signals, failure
memory, and change awareness.

Each feature has: what it does, the format, success criteria, and how to
verify it works.

---

## Feature 1: Conditional Phases

### What It Does

Packs become context-aware. Phases can be skipped, modified, or extended
based on conditions evaluated at runtime. The agent doesn't follow a fixed
sequence — it follows the right sequence for THIS situation.

### Format Extension

```yaml
phases:
  - name: reproduce
    description: "Reproduce the bug consistently"
    checkpoint: "Bug reproduces with documented steps"

    # NEW: conditions evaluated by borg_observe / borg_apply
    skip_if:
      - condition: "error_type == 'ImportError'"
        reason: "Import errors don't need reproduction — they fail deterministically"
    
    inject_if:
      - condition: "attempts > 2"
        message: "You've tried {{attempts}} approaches. Stop. List what you tried and why each failed before continuing."
      - condition: "'NoneType' in error_message"
        message: "NoneType errors originate at the CALL SITE, not the method. Trace upstream."

  - name: investigate_root_cause
    description: "Trace the error to its source"
    
    context_prompts:
      - condition: "has_recent_changes"
        prompt: "This codebase changed in the last 24h. Check git log before investigating."
      - condition: "error_in_test"
        prompt: "The error is in a test file. Check if the test itself is wrong before debugging production code."
```

### Implementation

1. Add `skip_if`, `inject_if`, `context_prompts` to pack schema (schema.py)
2. `borg_observe` evaluates conditions against provided context and returns filtered phases
3. `borg_apply` action=checkpoint evaluates inject_if before returning next phase
4. Conditions are simple string matches — not a full expression engine. Patterns:
   - `"'substring' in error_message"` — string containment
   - `"error_type == 'TypeError'"` — exact match
   - `"attempts > N"` — numeric comparison
   - `"has_recent_changes"` — boolean flag from context

### Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Pack with skip_if parses without error | `parse_workflow_pack()` returns valid dict |
| 2 | Phase is skipped when condition matches | `borg_observe(task="fix ImportError")` omits reproduce phase |
| 3 | Phase is NOT skipped when condition doesn't match | `borg_observe(task="fix TypeError")` includes reproduce phase |
| 4 | inject_if adds message when condition matches | After 3 failed checkpoints, response includes "Stop. List what you tried" |
| 5 | context_prompts appear when relevant | When context includes `has_recent_changes=true`, git prompt appears |
| 6 | Existing packs without conditions still work | All 23 packs pass validation unchanged |
| 7 | Tests: 15+ new tests covering all condition types | `pytest borg/tests/test_conditions.py` all pass |

---

## Feature 2: Start-Here Signals

### What It Does

Instead of the agent reading random files, borg tells it exactly where to
start based on the error type. This eliminates the #1 token waste: reading
wrong files first.

### Format Extension

```yaml
# Added to pack YAML
start_signals:
  - error_pattern: "NoneType has no attribute"
    start_here:
      - "the file and line from the stack trace"
      - "the CALLER of that function (trace upstream)"
    avoid:
      - "the method definition itself — the bug is upstream"
      - "configuration files"
    reasoning: "NoneType means something returned None. Find where."

  - error_pattern: "ImportError|ModuleNotFoundError"
    start_here:
      - "pyproject.toml or setup.py (check dependencies)"
      - "the import statement itself"
    avoid:
      - "the module's source code (it may not exist yet)"
    reasoning: "Missing module. Check if it's installed, not if it's correct."

  - error_pattern: "AssertionError in test_"
    start_here:
      - "the test file at the failing line"
      - "the function being tested"
    avoid:
      - "other test files"
      - "test infrastructure/conftest"
    reasoning: "Test assertion failed. Understand what's expected vs actual."
```

### Implementation

1. Add `start_signals` to pack schema
2. `borg_observe` matches error_pattern against provided context
3. Returns `start_here` and `avoid` lists in the response
4. Agent uses these to prioritize which files to read first

### Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | start_signals parsed correctly from YAML | `parse_workflow_pack()` includes start_signals |
| 2 | Error pattern matching works | "NoneType has no attribute 'split'" matches "NoneType has no attribute" |
| 3 | borg_observe returns start_here for matching error | Response includes start_here list |
| 4 | borg_observe returns nothing for non-matching error | Response omits start_here |
| 5 | Multiple patterns, first match wins | Test with overlapping patterns |
| 6 | Existing packs without signals still work | All 23 packs pass unchanged |
| 7 | Tests: 10+ tests | `pytest borg/tests/test_start_signals.py` all pass |

---

## Feature 3: Failure Memory

### What It Does

When agents fail, the failure pattern is logged. Future agents hitting the
same error get a shortcut: "47 agents tried X and failed. Try Y instead."
This is where the collective gets smarter.

### Data Model

```yaml
# Stored in borg/failures/<pack_id>/<error_hash>.yaml
error_pattern: "NoneType has no attribute 'split'"
pack_id: "systematic-debugging"
phase: "investigate_root_cause"

wrong_approaches:
  - approach: "Added if val is not None check in the method"
    failure_count: 23
    why_fails: "The None comes from the caller, not this method"
  - approach: "Changed return type annotation"
    failure_count: 8
    why_fails: "Annotations don't affect runtime behavior"

correct_approaches:
  - approach: "Traced upstream to find missing default value in caller"
    success_count: 31
    avg_tokens: 3200
  - approach: "Checked git blame for recent return type changes"
    success_count: 12
    avg_tokens: 4100

total_sessions: 74
last_updated: "2026-03-27T16:00:00Z"
```

### Implementation

1. Extend `borg_apply` action=checkpoint to log: error_type, approach_taken, pass/fail
2. Extend `aggregator.py` to cluster failures by error pattern and extract wrong/correct approaches
3. Add `borg_recall` MCP tool (11th tool): given an error message, check failure memory for shortcuts
4. `borg_observe` automatically checks failure memory and includes shortcuts in response

### Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Checkpoint logs include error_type and approach | JSONL event has `error_type` and `approach` fields |
| 2 | Aggregator clusters failures by error pattern | 5 mock failures with same error → 1 cluster |
| 3 | Wrong approaches extracted with frequency | Cluster shows "approach X failed 3 times" |
| 4 | Correct approaches extracted with frequency | Cluster shows "approach Y succeeded 2 times" |
| 5 | borg_recall returns shortcuts for known error | `borg_recall("NoneType has no attribute")` returns approaches |
| 6 | borg_recall returns empty for unknown error | `borg_recall("never seen this")` returns nothing |
| 7 | borg_observe includes failure memory in response | When matching error found, response includes "other agents tried X and failed" |
| 8 | Failure memory persists across sessions | Write failure, restart, read failure → still there |
| 9 | Tests: 15+ tests | `pytest borg/tests/test_failure_memory.py` all pass |

---

## Feature 4: Change Awareness

### What It Does

Borg knows what changed recently in the project. When the agent's error
is in a recently modified file, borg says so immediately. Eliminates 30%
of wasted exploration.

### Implementation

1. Add `borg_context` MCP tool (12th tool) that the agent calls with the project path
2. `borg_context` runs: `git log --oneline -10`, `git diff --stat`, `git diff --name-only HEAD~5`
3. Returns: recently changed files, uncommitted changes, last commit messages
4. `borg_observe` includes change data if available: "The error is in auth.py. auth.py was modified 2 hours ago."

### Success Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | borg_context returns recent git changes | In a git repo, returns file list with timestamps |
| 2 | borg_context works in non-git dirs | Returns empty/message, doesn't crash |
| 3 | borg_observe cross-references changes with error | If error file in recent changes, includes "recently modified" note |
| 4 | Performance: borg_context < 2 seconds | Timed test in a real repo |
| 5 | Tests: 8+ tests | `pytest borg/tests/test_change_awareness.py` all pass |

---

## Implementation Order

### Phase 1: Conditional Phases (Days 1-2)
- Schema extension: skip_if, inject_if, context_prompts
- borg_observe evaluates conditions
- Tests
- Update systematic-debugging pack with real conditions

### Phase 2: Start-Here Signals (Days 3-4)
- Schema extension: start_signals with error_pattern matching
- borg_observe includes file guidance
- Tests
- Add signals to systematic-debugging and quick-debug packs

### Phase 3: Failure Memory (Days 5-7)
- Checkpoint logging extension (error_type, approach)
- Aggregator clustering
- borg_recall MCP tool
- Integration with borg_observe
- Tests

### Phase 4: Change Awareness (Days 8-9)
- borg_context MCP tool
- Git integration
- Cross-reference with borg_observe
- Tests

### Phase 5: Verify the Brain (Day 10)
- End-to-end test: agent hits TypeError → borg_observe returns conditional
  phases + start-here signals + failure memory + change awareness
- Before/after token measurement
- Update all docs

---

## Overall Success Criteria

| # | Criterion | Target | Verification |
|---|-----------|--------|-------------|
| 1 | All existing 859 tests still pass | 859/859 | `pytest borg/tests/` |
| 2 | New tests for all 4 features | 48+ new | `pytest` count increases |
| 3 | Conditional phases work | Skip/inject evaluated | Manual test with borg_observe |
| 4 | Start-here signals reduce file reads | Measurable in demo | Before/after comparison |
| 5 | Failure memory persists and recalls | Round-trip test | Write → read → verify |
| 6 | Change awareness returns git data | In any git repo | `borg_context` call |
| 7 | borg_observe returns richer guidance | All 4 features in one response | E2E test |
| 8 | Flagship pack updated with conditions | systematic-debugging | YAML review |
| 9 | PyPI published with all features | agent-borg new version | `pip install` test |
| 10 | Fresh install works | 5-user concurrent | Deep test script |

---

## What This Does NOT Include

- Real-time agent monitoring (needs infrastructure we don't have)
- Automatic pack updating from ML (needs scale we don't have)
- Cross-project knowledge transfer (needs data we don't have)
- Perfect failure detection (agents don't always know when they failed)

These are future work. This spec builds the foundation they need.

---

## The Test: Is This A Brain?

After implementation, try this:

1. Agent hits: `TypeError: 'NoneType' has no attribute 'split'`
2. Agent calls `borg_observe` with the error
3. Borg responds:
   - 🧠 "Using systematic-debugging (confidence: tested)"
   - **Start here:** "trace the CALL SITE, not the method — NoneType means upstream returned None"
   - **Skip:** reproduce phase (TypeError is deterministic)
   - **Warning:** "23 agents tried adding a None check in the method. That's the symptom, not the cause."
   - **Note:** "auth.py was modified 2 hours ago — check if that change affected the return type"
   - **Phase 1:** investigate_root_cause → trace upstream callers

That's a brain. Not a cookbook. The agent doesn't just get instructions —
it gets intelligence shaped by every agent that came before it.
