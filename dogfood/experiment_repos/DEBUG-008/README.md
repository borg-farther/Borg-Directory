# DEBUG-008: Python JSON Serialization Bug

## Problem
The `BuggyEncoder` class in `src/serializer.py` fails to properly serialize:
- `datetime` objects - returns raw object instead of ISO format string
- `Decimal` objects - returns raw object instead of float
- `set` objects - returns raw object instead of list

## Task
Fix the `BuggyEncoder.default()` method to properly convert these types.

## Verification
```bash
./check.sh
```
