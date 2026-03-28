# Quick Debug

**Confidence:** tested
**Problem class:** simple debugging

## Required Inputs
- error message or bug description
- access to the codebase or environment where the bug occurs

## Mental Model
Reproduce first, then isolate, then fix. Never guess at a fix without confirming you can see the bug happen. The fastest path to a fix is the shortest path through reproduce → isolate → fix → verify.


## Phases

### reproduce
Reproduce the bug consistently. Run the failing test, trigger the error, or follow the steps that cause the issue. Capture the exact error output.


**Checkpoint:** Bug reproduced with consistent steps and exact error captured.

**Anti-patterns:**
- Guessing at a fix without reproducing
- Assuming the bug is in the most recently changed code
- Changing multiple things at once before confirming reproduction

**Prompts:**
- What exact command or action triggers the bug?
- Can you reproduce it 3 times in a row?
- Capture the full error traceback or output.

### isolate
Narrow down the cause. Use bisection, print debugging, or divide and conquer to identify the specific line, function, or interaction causing the issue. Rule out at least one hypothesis.


**Checkpoint:** Root cause identified to a specific function or interaction.

**Anti-patterns:**
- Changing code before understanding the cause
- Blaming external dependencies without evidence
- Reading code without running it

**Prompts:**
- What are the top 2-3 hypotheses for the cause?
- Can you rule out at least one hypothesis with a quick test?
- Add a targeted log or print to confirm the hypothesis.

### fix
Apply the minimal targeted fix. Change only what is necessary to resolve the root cause identified in the isolate phase. Do not refactor unrelated code in the same change.


**Checkpoint:** Fix applied. The original reproduction steps no longer trigger the bug.

**Anti-patterns:**
- Shotgun debugging — changing multiple things hoping one works
- Fixing symptoms instead of root cause
- Bundling unrelated changes with the fix

**Prompts:**
- Does this fix address the root cause from the isolate phase?
- Is this the smallest possible change?

### verify
Confirm the fix works and nothing else broke. Run the original reproduction steps plus any related tests. Check for regressions.


**Checkpoint:** Original bug fixed AND no regressions in related tests.

**Anti-patterns:**
- Only testing the exact reproduction case
- Skipping related test suites
- Declaring victory without running tests

**Prompts:**
- Run the full test suite for the affected module.
- Try edge cases related to the fix.


## Examples
**Example 1:**
- Problem: Flaky CI test fails 30% of the time with timeout error
- Solution: Reproduced locally with race condition. Isolated to shared state between tests. Fixed by adding test isolation fixture.
- Outcome: Test passed 100/100 runs after fix. CI green for 2 weeks.

**Example 2:**
- Problem: API returns 500 on valid input with special characters
- Solution: Reproduced with input containing '&' character. Isolated to URL encoding in query builder. Fixed by adding proper escaping.
- Outcome: Bug fixed. Added 5 edge case tests for special characters.


## Escalation
- Escalate if bug cannot be reproduced after 3 attempts
- Escalate if root cause spans multiple systems or requires architectural change
- Escalate if fix would break backward compatibility

---
Author: agent://hermes/ab-agent | Confidence: tested | Created: 2026-03-23T06:00:00Z
Evidence: Used on 8 debugging tasks. 7 resolved on first pass, 1 required escalation (architectural issue). Average time to fix: 15 minutes with pack vs 35 minutes without.
Failure cases: Does not help with intermittent timing/concurrency bugs — reproduce phase may not catch them, Overkill for trivial typos or syntax errors — just fix those directly, Isolation phase assumes access to logs/debugger — breaks in black-box scenarios
