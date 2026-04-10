# TEST-002: API Client Edge Cases

## Task Description
The `src/client.py` contains an HTTP client wrapper with retry logic. The `tests/test_client.py` has only 2 basic tests. You need to add more edge case tests.

## Requirements
- Add at least 8 more edge case tests (for total >= 10 tests)
- Test timeout handling
- Test rate limiting (429)
- Test empty responses
- Test malformed JSON
- Test connection errors
- Test 404 and 500 responses
- Test retry behavior

## Files
- `src/client.py` - The API client implementation (do not modify)
- `tests/test_client.py` - Has 2 basic tests, add more
- `check.sh` - Runs pytest, requires >= 10 tests to pass
