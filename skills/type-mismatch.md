---
type: workflow_pack
version: "1.0"
id: type-mismatch
problem_class: type_mismatch
framework: python
problem_signature:
  error_types:
    - TypeError
    - mypy error
  framework: python
  problem_description: A function or operation received the wrong type. Python dynamic typing allows this at runtime. Mypy catches it at static analysis time.
root_cause:
  category: type_mismatch
  explanation: A value of type A was passed where type B was expected. Either the caller passed the wrong type, or the function does not handle the type it received.
investigation_trail:
  - file: "@error_location"
    position: FIRST
    what: Read the line that raised TypeError. What is being passed?
    grep_pattern: ""
  - file: "@function_definition"
    position: SECOND
    what: Read the function definition. What types does it accept?
    grep_pattern: "def |async def"
  - file: "@caller_location"
    position: THIRD
    what: Read the call site. What is being passed and what type does the function expect?
    grep_pattern: ""
resolution_sequence:
  - action: fix_caller
    command: Fix the call site to pass the correct type
    why: If the function signature is correct, the caller is wrong
  - action: relax_signature
    command: Update the function to accept Union types if it should handle multiple types
    why: Use Union[X, Y] or overload if the function genuinely needs to handle multiple types
  - action: add_converter
    command: "Add type conversion at the call site: int(x), str(x), list(x)"
    why: Convert the value to the expected type before passing
  - action: type_narrowing
    command: Use isinstance() check before the operation
    why: Type narrowing tells Python the type inside the conditional block
anti_patterns:
  - action: Using type() checks
    why_fails: Use isinstance() instead — type() does not handle subclasses correctly
  - action: Catching TypeError and returning None
    why_fails: Masks the bug and introduces None where a value is expected
  - action: Adding # type: ignore
    why_fails: Masks type errors without fixing them
evidence:
  success_count: 38
  failure_count: 4
  success_rate: 0.90
  avg_time_to_resolve_minutes: 2.5
  uses: 42
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `TypeError` with an expected/got message
- Mypy errors about type mismatches

Do NOT use when the error involves None specifically.
