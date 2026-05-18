# DEBUG-004: Import Cycle

## Task Description
There's a circular import between `models.py` and `utils.py`:
- `models.py` imports `format_timestamp` from `utils`
- `utils.py` imports `User` from `models`

This causes an `ImportError` when importing either module.

## Your Task
Break the import cycle by creating `src/common.py` with shared code and updating imports.

## Files
- `src/models.py` - Imports from utils (part of cycle)
- `src/utils.py` - Imports from models (part of cycle)
- `tests/test_import.py` - Tests that verify imports work
- `check.sh` - Run tests to verify the fix
