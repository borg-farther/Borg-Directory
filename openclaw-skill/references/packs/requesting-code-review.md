# Requesting Code Review

**Confidence:** inferred
**Problem class:** Use when completing tasks, implementing major features, or before merging. Validates work meets requirements through systematic review process.

## Required Inputs
- task_description: what you need to accomplish

## Phases

### when_to_request_review
**Mandatory:**
- After each task in subagent-driven development
- After completing a major feature
- Before merge to main
- After bug fixes

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After complex logic implementation
- When touching critical code (auth, payments, data)

**Never skip because:**
- "It's simple" — simple bugs compound
- "I'm in a hurry" — reviews save time
- "I tested it" — you have blind spots

**Checkpoint:** Verify when to request review is complete and correct.

### review_process
### Step 1: Self-Review First

Before dispatching a reviewer, check yourself:

- [ ] Code follows project conventions
- [ ] All tests pass
- [ ] No debug print statements left
- [ ] No hardcoded secrets or credentials
- [ ] Error handling in place
- [ ] Commit messages are clear

```bash
# Run full test suite
pytest tests/ -q

# Check for debug code
search_files("print(", path="src/", file_glob="*.py")
search_files("console.log", path="src/", file_glob="*.js")

# Check for TODOs
search_files("TODO|FIXME|HACK", path="src/")
```

### Step 2: Gather Context

```bash
# Changed files
git diff --name-only HEAD~1

# Diff summary
git diff --stat HEAD~1

# Recent commits
git log --oneline -5
```

### Step 3: Dispatch Reviewer Subagent

Use `delegate_task` to dispatch a focused reviewer:

```python
delegate_task(
    goal="Review implementation for correctness and quality",
    context="""
    WHAT WAS IMPLEMENTED:
    [Brief description of the feature/fix]

    ORIGINAL REQUIREMENTS:
    [From plan, issue, or user request]

    FILES CHANGED:
    - src/models/user.py (added User class)
    - src/auth/login.py (added login endpoint)
    - tests/test_auth.py (added 8 tests)

    REVIEW CHECKLIST:
    - [ ] Correctness: Does it do what it should?
    - [ ] Edge cases: Are they handled?
    - [ ] Error handling: Is it adequate?
    - [ ] Code quality: Clear names, good structure?
    - [ ] Test coverage: Are tests meaningful?
    - [ ] Security: Any vulnerabilities?
    - [ ] Performance: Any obvious issues?

    OUTPUT FORMAT:
    - Summary: [brief assessment]
    - Critical Issues: [must fix — blocks merge]
    - Important Issues: [should fix before merge]
    - Minor Issues: [nice to have]
    - Strengths: [what was done well]
    - Verdict: APPROVE / REQUEST_CHANGES
    """,
    toolsets=['file']
)
```

### Step 4: Act on Feedback

**Critical Issues (block merge):**
- Security vulnerabilities
- Broken functionality
- Data loss risk
- Test failures
- **Action:** Fix immediate

**Checkpoint:** Verify review process is complete and correct.

### review_dimensions
### Correctness
- Does it implement the requirements?
- Are there logic errors?
- Do edge cases work?
- Are there race conditions?

### Code Quality
- Is code readable?
- Are names clear and descriptive?
- Is it too complex? (Functions >20 lines = smell)
- Is there duplication?

### Testing
- Are there meaningful tests?
- Do they cover edge cases?
- Do they test behavior, not implementation?
- Do all tests pass?

### Security
- Any injection vulnerabilities?
- Proper input validation?
- Secrets handled correctly?
- Access control in place?

### Performance
- Any N+1 queries?
- Unnecessary computation in loops?
- Memory leaks?
- Missing caching opportunities?

**Checkpoint:** Verify review dimensions is complete and correct.

### review_output_format
Standard format for reviewer subagent output:

```markdown

**Checkpoint:** Verify review output format is complete and correct.

### review_summary
**Assessment:** [Brief overall assessment]
**Verdict:** APPROVE / REQUEST_CHANGES

---

**Checkpoint:** Verify review summary is complete and correct.

### critical_issues__fix_required
1. **[Issue title]**
   - Location: `file.py:45`
   - Problem: [Description]
   - Suggestion: [How to fix]

**Checkpoint:** Verify critical issues (fix required) is complete and correct.


## Examples
**Example 1:**
- Problem: Agent completed a feature and directly merged it — no review, shipped a security vulnerability
- Solution: when_to_request_review: Mandatory review before merge caught SQL injection in the new endpoint.
- Outcome: Vulnerability patched before production. 30-minute incident avoided.

**Example 2:**
- Problem: Agent requested review but didn't run tests first — reviewer found 3 test failures in the PR
- Solution: review_process Step 1: Self-review first ran pytest. Fixed 3 failures before dispatching reviewer.
- Outcome: Reviewer received clean PR. No back-and-forth on known issues.

**Example 3:**
- Problem: Agent dispatched reviewer without context — subagent asked 10 clarifying questions
- Solution: review_process Step 3: Provided full context including original requirements, files changed, and review checklist in delegate_task context.
- Outcome: Reviewer subagent completed in one pass without questions.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from requesting-code-review skill. Requires validation through usage.
Failure cases: May not apply to all requesting code review scenarios
