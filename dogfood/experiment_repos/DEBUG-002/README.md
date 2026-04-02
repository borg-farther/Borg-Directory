# DEBUG-002: Data Pipeline TypeError

## Task Description
A data processing pipeline crashes with `TypeError` when processing users. The bug is in `get_user_data()` which returns `None` instead of an empty dict `{}` for missing user IDs.

When `process_users([1, 999])` is called, the list becomes `[{"name": "Alice", ...}, None]`. Then `normalize_data()` crashes when it tries to access `None["id"]`.

## Your Task
Fix `src/pipeline.py` so that `get_user_data()` returns `{}` instead of `None` for missing users.

## Files
- `src/pipeline.py` - The buggy pipeline code
- `tests/test_pipeline.py` - Tests that verify correct behavior
- `check.sh` - Run tests to verify the fix
