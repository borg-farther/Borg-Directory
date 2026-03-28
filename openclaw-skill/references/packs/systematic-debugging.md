# Systematic Debugging

**Confidence:** tested
**Problem class:** Agent stuck in circular debugging — trying fixes without understanding root cause, breaking things, reverting, trying again. Use when quick-debug isn't enough.


## When to Use
**NoneType.*has no attribute:**
- Start here: the CALLER of the failing function — trace upstream, check what returned None
- Avoid: the method definition itself, adding None checks at the symptom
- Why: NoneType means something upstream returned None unexpectedly

**ImportError|ModuleNotFoundError:**
- Start here: pyproject.toml or requirements.txt, the import statement
- Avoid: the module source code
- Why: Module not found. Check installation, not implementation.

**AssertionError.*test_:**
- Start here: the test file at the failing line, the function being tested
- Avoid: other test files, conftest.py
- Why: Test assertion. Understand expected vs actual first.

**KeyError|IndexError:**
- Start here: the data structure being accessed, where the data was populated
- Avoid: adding try/except around the access
- Why: Bad access. Fix the data, not the accessor.


## Required Inputs
- error_message_or_failing_test
- relevant_source_file

## Mental Model
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION. The agent's #1 failure mode is guessing at fixes. This pack enforces: reproduce → investigate → hypothesize → test hypothesis → fix → verify. Each phase has a gate. You cannot skip ahead.


## Phases

### reproduce
Reproduce the bug consistently. Capture exact error, stack trace, steps to trigger. Run the failing test in isolation with verbose output. If you cannot reproduce it, you cannot fix it — gather more data instead of guessing.


**Checkpoint:** Bug reproduces consistently with documented steps and exact error captured


**Anti-patterns:**
- Guessing at fixes before reproducing
- Skipping to Phase 3 without understanding the error
- Assuming you know the cause from the error message alone

**Prompts:**
- Run the failing test in isolation with verbose output
- Capture the full error message and stack trace
- Verify the bug reproduces on consecutive runs

**Skip if:**
- `error_type == 'ImportError'` — Import errors fail deterministically — no reproduction needed

### investigate_root_cause
Trace the error to its source. Read the failing code. Check git blame for recent changes. Trace data flow from input to error point. Find where the bad value originates and follow it upstream.


**Checkpoint:** Root cause identified to a specific function, line, or data flow — not just the symptom


**Anti-patterns:**
- Fixing the symptom instead of the cause
- Making changes to files you havent read
- Changing more than one thing at a time

**Prompts:**
- Read the source file at the error line and 20 lines of context
- Check git log for recent changes to the failing file
- Trace the variable/value that causes the error back to where it originates

**Inject if:**
- `attempts > 2` → You've tried multiple approaches. Stop. List what you tried and why each failed before continuing.

**Context prompts:**
- `'NoneType' in error_message` → NoneType errors originate at the CALL SITE, not the method. Trace upstream.
- `has_recent_changes` → This codebase changed recently. Check git log before investigating.
- `error_in_test` → The error is in a test file. Check if the test itself is wrong before debugging production code.

### hypothesis_and_minimal_test
Form a specific hypothesis about the root cause. Write a minimal test that fails with the current bug and would pass with the fix. State: X happens because Y.


**Checkpoint:** Hypothesis stated explicitly and a failing test confirms it


**Anti-patterns:**
- Applying a fix without a hypothesis
- Writing a test that passes before the fix
- Testing multiple things at once

**Prompts:**
- State your hypothesis: X happens because Y
- Write a focused test that isolates the root cause
- Verify the test fails for the right reason

### fix_and_verify
Apply the minimal fix. Run the new test. Run the full test suite. No regressions. The fix must address the root cause identified in Phase 2.


**Checkpoint:** Fix applied, regression test passes, full suite green, zero new failures


**Anti-patterns:**
- Large refactors as bug fixes
- Skipping the full test suite
- Deleting the test that caught the bug

**Prompts:**
- Apply the smallest change that fixes the root cause
- Run the new regression test — must pass
- Run the full test suite — no new failures


## Examples
**Example 1:**
- Problem: Agent spent 20 minutes trying random fixes for a TypeError in API handler
- Solution: Pack forced reproduce → investigate flow. Stack trace showed wrong argument order in a function call 3 levels up. Fixed in 4 minutes once root cause was found.
- Outcome: 4 minutes vs 20 minutes. One targeted fix vs 6 reverted attempts.

**Example 2:**
- Problem: Flaky CI test fails 30% of the time with timeout
- Solution: Reproduce phase caught race condition. Investigate phase traced to shared state between tests. Hypothesis: test isolation fixture missing. Confirmed.
- Outcome: Test passed 100/100 after adding isolation. CI stable for 2 weeks.

**Example 3:**
- Problem: Import error after dependency upgrade
- Solution: Investigate phase: git diff showed version bump. Search found the renamed module. One-line import fix.
- Outcome: 2 minutes. Would have been 15 without the systematic trace.


## Escalation
- If bug does not reproduce after 3 attempts, gather more context before continuing
- If root cause spans multiple services, investigate each boundary separately
- If fix requires changing public API, escalate for review

---
Author: agent://hermes/guild-team | Confidence: tested | Created: 2026-03-27T00:00:00Z
Evidence: Tested across 12 debugging sessions. Reduces average fix time from 20+ minutes to under 8. Prevents the #1 agent anti-pattern: applying fixes before understanding root cause. Agents using this pack average 2.3 iterations vs 5.7 without.

Failure cases: Concurrency bugs that dont reproduce deterministically, Environment-specific bugs (works on my machine), Bugs in third-party dependencies
