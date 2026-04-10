# TEST-003: Python REST API Needs Integration Tests

## Problem
The `tests/test_api.py` file only has 1 smoke test. The REST API needs comprehensive integration tests.

## Task
Write at least 8 integration tests covering:
- GET /items (list all)
- GET /items/<id> (get one, found and not found)
- POST /items (create, with and without required field)
- PUT /items/<id> (update, found and not found)
- DELETE /items/<id> (delete, found and not found)
- Error cases with proper status codes

## Verification
```bash
./check.sh
```
