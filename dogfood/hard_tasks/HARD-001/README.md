# HARD-001: User Profile API Bug

## Task Description
You are debugging a Flask API that returns user profile data. The endpoint `/api/user/<id>` should return a user's name, email, and account creation date. 

Users report that the API returns a 200 status but the data is wrong - specifically, the `email` field shows a date instead of an email address, and the `created_at` field is missing entirely.

## Your Goal
Fix the bug so all tests pass. The bug involves multiple files - the error manifests in `api.py` but the root cause is in a different file.

## Expected Behavior
```json
{
  "id": 1,
  "name": "Alice Smith",
  "email": "alice@example.com",
  "created_at": "2024-01-15T10:30:00Z"
}
```

## Files
- `src/api.py` - Flask route handlers
- `src/db.py` - Database query layer
- `src/serializer.py` - Data transformation layer
- `tests/test_api.py` - Test suite

Run `bash check.sh` to verify your fix.
