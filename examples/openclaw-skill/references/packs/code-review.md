# Code Review

**Confidence:** inferred
**Problem class:** Guidelines for performing thorough code reviews with security and quality focus

## Required Inputs
- task_description: what you need to accomplish

## Phases

### review_checklist
### 1. Security First
- [ ] No hardcoded secrets, API accesss, or credentials
- [ ] Input validation on all user-provided data
- [ ] SQL queries use parameterized statements (no string concatenation)
- [ ] File operations validate paths (no path traversal)
- [ ] Authentication/authorization checks present where needed

### 2. Error Handling
- [ ] All external calls (API, DB, file) have try/catch
- [ ] Errors are logged with context (but no sensitive data)
- [ ] User-facing errors are helpful but don't leak internals
- [ ] Resources are cleaned up in finally blocks or context managers

### 3. Code Quality
- [ ] Functions do one thing and are reasonably sized (<50 lines ideal)
- [ ] Variable names are descriptive (no single letters except loops)
- [ ] No commented-out code left behind
- [ ] Complex logic has explanatory comments
- [ ] No duplicate code (DRY principle)

### 4. Testing Considerations
- [ ] Edge cases handled (empty inputs, nulls, boundaries)
- [ ] Happy path and error paths both work
- [ ] New code has corresponding tests (if test suite exists)

**Checkpoint:** Verify review checklist is complete and correct.

### review_response_format
When providing review feedback, structure it as:

```

**Checkpoint:** Verify review response format is complete and correct.

### summary
[1-2 sentence overall assessment]

**Checkpoint:** Verify summary is complete and correct.

### critical_issues__must_fix
- Issue 1: [description + suggested fix]
- Issue 2: ...

**Checkpoint:** Verify critical issues (must fix) is complete and correct.

### suggestions__nice_to_have
- Suggestion 1: [description]

**Checkpoint:** Verify suggestions (nice to have) is complete and correct.

### questions
- [Any clarifying questions about intent]
```

**Checkpoint:** Verify questions is complete and correct.


## Examples
**Example 1:**
- Problem: Agent reviewed a PR and only commented on style issues — missed that user input was passed directly to shell command
- Solution: review_checklist Security First phase: checked all user-provided data paths. Found os.system(user_input) without sanitization.
- Outcome: Critical SQL injection-equivalent vulnerability caught before merge. Fix applied in 10 minutes.

**Example 2:**
- Problem: Agent approved a PR that later caused production outage — error handling was missing on API calls
- Solution: review_checklist Error Handling phase: verified all external calls have try/catch. Found missing error handling on 3 API endpoints.
- Outcome: Issues caught in review, not production. Error handling added before merge.

**Example 3:**
- Problem: Agent reviewed a database migration PR but didn't notice there was no rollback plan
- Solution: review_checklist: Noted that migration adds column without backup strategy. Requested rollback plan as blocking issue.
- Outcome: Rollback script created before merge. Data loss risk eliminated.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Security-first ordering catches injection/auth issues that get missed in correctness-first reviews.
Failure cases: Very large diffs (1000+ lines) where the checklist becomes overwhelming, Languages/frameworks the agent has limited training on, Reviews where the architecture is wrong but the code is clean — misses forest for trees
