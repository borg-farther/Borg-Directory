---
name: test-driven-development
trigger: "Implementing any feature or bugfix"
---

# Test-Driven Development

## Principles
1. Write smallest failing test first — defines "done" before code.
2. Write only enough implementation to pass — resist over-engineering.
3. Refactor AFTER tests green — tests are your safety net.
4. Test behavior not implementation — mocking internals makes tests brittle.
5. Can't write a test? You don't understand the feature yet.

## Output Format
Return: Failing test | Minimal implementation | Refactored version

## Edge Cases
- LEGACY (no tests): write test for bug before fixing
- LARGE FEATURE: break into testable steps
- EXTERNAL API: mock at boundary, integration test separately

## Example
INPUT: "validate email"
OUTPUT:
```python
# Test first
def test_email(): assert validate_email("x@y.z") and not validate_email("x")
# Minimal
def validate_email(e): return "@" in e and "." in e.split("@")[1][-1]
# Refactored
import re; validate_email = lambda e: bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', e))
```

## Recovery
Test passes before implementation? Test is wrong — passing for wrong reason.
