# DEBUG-001: Flask App with Wrong HTTP Status Codes

## Task Description
A Flask REST API has two bugs related to incorrect HTTP status codes:

1. `GET /api/users/<id>` - When a user is not found, it returns HTTP 200 with `null` body instead of HTTP 404
2. `POST /api/users` - When sent invalid JSON, it crashes with HTTP 500 instead of returning HTTP 400

## Your Task
Fix the bugs in `src/app.py` so that:
- Missing users return HTTP 404
- Invalid JSON in POST returns HTTP 400

## Files
- `src/app.py` - The buggy Flask application
- `tests/test_app.py` - Tests that verify correct status codes
- `check.sh` - Run tests to verify the fix
