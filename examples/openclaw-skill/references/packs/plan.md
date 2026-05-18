# Plan

**Confidence:** inferred
**Problem class:** Plan mode for Hermes — inspect context, write a markdown plan into the active workspace's `.hermes/plans/` directory, and do not execute the work.

## Required Inputs
- task_description: what you need to accomplish

## Phases

### core_behavior
For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.hermes/plans/`.

**Checkpoint:** Verify core behavior is complete and correct.

### save_location
Save the plan with `write_file` under:
- `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Hermes file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.hermes/plans/`.

**Checkpoint:** Verify save location is complete and correct.

### interaction_style
- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.

**Checkpoint:** Verify interaction style is complete and correct.


## Examples
**Example 1:**
- Problem: Agent wrote a vague plan: 'Add authentication' — subagent couldn't execute it
- Solution: writing_process: Specified exact file paths (src/auth.py:45), included complete code examples, verification commands with expected output.
- Outcome: Subagent executed plan without questions. Task completed in one pass.

**Example 2:**
- Problem: Agent wrote a 20-step plan for renaming a variable — massive over-engineering
- Solution: bite_sized_task_granularity: Renamed to 3 steps: find all refs, rename, run tests. Matched detail to actual complexity.
- Outcome: Plan completed in 10 minutes instead of an hour of unnecessary ceremony.

**Example 3:**
- Problem: Agent started implementing while writing the plan — user wanted to review before any code was written
- Solution: core_behavior: Saved plan to .hermes/plans/2026-03-28_rename-auth.md. No project files modified. Replied with plan path for review.
- Outcome: User reviewed plan, requested changes to error handling approach before implementation started.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from plan skill. Requires validation through usage.
Failure cases: May not apply to all plan scenarios
