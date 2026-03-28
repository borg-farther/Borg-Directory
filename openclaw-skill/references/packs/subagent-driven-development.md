# Subagent Driven Development

**Confidence:** inferred
**Problem class:** Use when executing implementation plans with independent tasks. Dispatches fresh delegate_task per task with two-stage review (spec compliance then code quality).

## Required Inputs
- task_description: what you need to accomplish

## Phases

### the_process
### 1. Read and Parse Plan

Read the plan file. Extract ALL tasks with their full text and context upfront. Create a todo list:

```python
# Read the plan
read_file("docs/plans/feature-plan.md")

# Create todo list with all tasks
todo([
    {"id": "task-1", "content": "Create User model with email field", "status": "pending"},
    {"id": "task-2", "content": "Add credential hashing utility", "status": "pending"},
    {"id": "task-3", "content": "Create login endpoint", "status": "pending"},
])
```

**Key:** Read the plan ONCE. Extract everything. Don't make subagents read the plan file — provide the full task text directly in context.

### 2. Per-Task Workflow

For EACH task in the plan:

#### Step 1: Dispatch Implementer Subagent

Use `delegate_task` with complete context:

```python
delegate_task(
    goal="Implement Task 1: Create User model with email and password_hash fields",
    context="""
    TASK FROM PLAN:
    - Create: src/models/user.py
    - Add User class with email (str) and password_hash (str) fields
    - Use bcrypt for credential hashing
    - Include __repr__ for debugging

    FOLLOW TDD:
    1. Write failing test in tests/models/test_user.py
    2. Run: pytest tests/models/test_user.py -v (verify FAIL)
    3. Write minimal implementation
    4. Run: pytest tests/models/test_user.py -v (verify PASS)
    5. Run: pytest tests/ -q (verify no regressions)
    6. Commit: git add -A && git commit -m "feat: add User model with credential hashing"

    PROJECT CONTEXT:
    - Python 3.11, Flask app in src/app.py
    - Existing models in src/models/
    - Tests use pytest, run from project root
    - bcrypt already in requirements.txt
    """,
    toolsets=['terminal', 'file']
)
```

#### Step 2: Dispatch Spec Compliance Reviewer

After the implementer completes, verify against the original spec:

```python
delegate_task(
    goal="Review if implementation matches the spec from the plan",
    context="""
    ORIGINAL TASK SPEC:
    - Create src/models/user.py w

**Checkpoint:** Verify the process is complete and correct.

### task_granularity
**Each task = 2-5 minutes of focused work.**

**Too big:**
- "Implement user authentication system"

**Right size:**
- "Create User model with email and credential fields"
- "Add credential hashing function"
- "Create login endpoint"
- "Add JWT auth credential generation"
- "Create registration endpoint"

**Checkpoint:** Verify task granularity is complete and correct.

### red_flags___never_do_these
- Start implementation without a plan
- Skip reviews (spec compliance OR code quality)
- Proceed with unfixed critical/important issues
- Dispatch multiple implementation subagents for tasks that touch the same files
- Make subagent read the plan file (provide full text in context instead)
- Skip scene-setting context (subagent needs to understand where the task fits)
- Ignore subagent questions (answer before letting them proceed)
- Accept "close enough" on spec compliance
- Skip review loops (reviewer found issues → implementer fixes → review again)
- Let implementer self-review replace actual review (both are needed)
- **Start code quality review before spec compliance is PASS** (wrong order)
- Move to next task while either review has open issues

**Checkpoint:** Verify red flags — never do these is complete and correct.

### handling_issues
### If Subagent Asks Questions

- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### If Reviewer Finds Issues

- Implementer subagent (or a new one) fixes them
- Reviewer reviews again
- Repeat until approved
- Don't skip the re-review

### If Subagent Fails a Task

- Dispatch a new fix subagent with specific instructions about what went wrong
- Don't try to fix manually in the controller session (context pollution)

**Checkpoint:** Verify handling issues is complete and correct.

### efficiency_notes
**Why fresh subagent per task:**
- Prevents context pollution from accumulated state
- Each subagent gets clean, focused context
- No confusion from prior tasks' code or reasoning

**Why two-stage review:**
- Spec review catches under/over-building early
- Quality review ensures the implementation is well-built
- Catches issues before they compound across tasks

**Cost trade-off:**
- More subagent invocations (implementer + 2 reviewers per task)
- But catches issues early (cheaper than debugging compounded problems later)

**Checkpoint:** Verify efficiency notes is complete and correct.

### integration_with_other_skills
### With writing-plans

This skill EXECUTES plans created by the writing-plans skill:
1. User requirements → writing-plans → implementation plan
2. Implementation plan → subagent-driven-development → working code

### With test-driven-development

Implementer subagents should follow TDD:
1. Write failing test first
2. Implement minimal code
3. Verify test passes
4. Commit

Include TDD instructions in every implementer context.

### With requesting-code-review

The two-stage review process IS the code review. For final integration review, use the requesting-code-review skill's review dimensions.

### With systematic-debugging

If a subagent encounters bugs during implementation:
1. Follow systematic-debugging process
2. Find root cause before fixing
3. Write regression test
4. Resume implementation

**Checkpoint:** Verify integration with other skills is complete and correct.


## Examples
**Example 1:**
- Problem: Agent dispatched 3 subagents simultaneously to implement a feature — they overwrote each other's changes
- Solution: the_process: Sequential dispatch per task. Each task touches different files (User model, auth utils, login endpoint). No conflicts.
- Outcome: Clean sequential implementation. Each task completed without merge conflicts.

**Example 2:**
- Problem: Implementer subagent completed task but spec compliance reviewer found it didn't match requirements
- Solution: the_process Step 2: Spec compliance review caught missing password_hash field. Implementer fixed before code quality review.
- Outcome: Spec violation caught early. Fixed in same session, not after merge.

**Example 3:**
- Problem: Agent let implementer self-review their own code — obvious issues were missed
- Solution: the_process: Separate reviewer subagent for code quality. Different perspective caught a race condition the implementer missed.
- Outcome: Two-stage review caught what self-review would have missed. 2 reviewers > 1.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from subagent-driven-development skill. Requires validation through usage.
Failure cases: May not apply to all subagent driven development scenarios
