---
type: workflow_pack
version: "1.0"
id: null-pointer-chain
problem_class: null_pointer_chain
framework: python
problem_signature:
  error_types:
    - AttributeError
    - TypeError
  framework: python
  problem_description: "'NoneType' object has no attribute — the error occurs at the call site, not the method definition. The method returned None because something upstream was None."
root_cause:
  category: null_dereference
  explanation: A method returned None because an upstream value was None. The AttributeError occurs where None is used, but the bug is where None was created. Reading the method that raised the error is almost always wrong.
investigation_trail:
  - file: "@call_site"
    position: FIRST
    what: Read the line that called the method. What did it pass? Trace one level up.
    grep_pattern: ""
  - file: "@method_return"
    position: SECOND
    what: Find the return statement. Was None returned intentionally?
    grep_pattern: return
  - file: "@upstream_call_site"
    position: THIRD
    what: Read the caller's caller. Repeat until you find where None was produced.
    grep_pattern: ""
resolution_sequence:
  - action: fix_upstream_none
    command: Fix the line that PRODUCES None — not the line that consumes it
    why: None checks downstream are bug masks. Fixing the source is the real fix.
  - action: use_get_or_create
    command: For DB queries, replace .get() with .get_or_create() or check result for None
    why: .get() raises DoesNotExist or returns None. Handle both cases explicitly.
  - action: validate_input
    command: Add input validation at function entry. Raise ValueError if required param is None.
    why: Fail fast at the boundary. None should not propagate into core logic.
anti_patterns:
  - action: Adding 'if obj is not None' checks downstream
    why_fails: Hides the bug instead of fixing it. The calling code should not need defensive checks.
  - action: Wrapping in try/except pass
    why_fails: Masks the symptom, not the cause.
  - action: Returning empty string or 0 instead of fixing why None was produced
    why_fails: Changes the type and breaks callers in different ways.
evidence:
  success_count: 47
  failure_count: 5
  success_rate: 0.90
  avg_time_to_resolve_minutes: 3.1
  uses: 52
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `TypeError: 'NoneType' object has no attribute`
- `AttributeError` where the object is None
- Any error involving None being used as an object

Do NOT use when the error is about wrong types (e.g., int instead of str).

## How to Use

1. DO NOT read the method that raised the error.
2. Read the LINE THAT CALLED that method.
3. Find the return statement in the called method. What did it return?
4. Trace one level higher: read the caller's caller.
5. Repeat until you find where None was produced.
6. Fix THAT line.
