---
name: systematic-debugging
trigger: "Any bug, test failure, or unexpected behavior"
---

# Systematic Debugging

## Principles
1. Reproduce first — can't make it fail on command? You're guessing.
2. Binary search — halve the codebase, find which half has bug, repeat.
3. Bug is never where you think — check the integration boundary.
4. Adding prints is slower than reading the call stack.
5. Verify: input fails before fix, passes after.

## Output Format
Return: Reproduction | Root cause | Fix | Verification

## Edge Cases
- FLAKY test: timing, randomness, or shared state
- HEISENBERG (print changes behavior): read-only inspection
- PROD-only: check env vars, config, data

## Example
INPUT: `pytest tests/test_auth.py::test_login -v` → `AssertionError: expected 'token'`
OUTPUT:
```
Repro: pytest tests/test_auth.py::test_login -v
Root cause: auth returns bytes not str
Fix: data['token'] = resp.read().decode()
Verify: pytest tests/test_auth.py::test_login -v passes
```

## Recovery
Cannot reproduce? Bug needs specific timing, env, or data.
