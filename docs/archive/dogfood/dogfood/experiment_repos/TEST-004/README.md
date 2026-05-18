# TEST-004: Python Data Validator Needs Edge Case Tests

## Problem
The `tests/test_validator.py` only has 3 basic tests. Validators need comprehensive edge case tests.

## Task
Add at least 12 tests covering:
- Invalid emails: missing @, missing domain, invalid characters, empty string
- Valid/invalid phones: various formats, too short, letters
- Valid/invalid URLs: missing scheme, missing TLD, special characters
- Edge cases: None, empty string, very long inputs

## Verification
```bash
./check.sh
```
