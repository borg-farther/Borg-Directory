# DEBUG-003: Race Condition in Counter

## Task Description
A `Counter` class is used by multiple threads. The `increment()` method has a race condition because the read-modify-write operation is not atomic.

When 10 threads each increment 100 times, the expected final count is 1000, but due to the race condition, the actual count is often less.

## Your Task
Fix `src/counter.py` by adding thread safety with `threading.Lock`.

## Files
- `src/counter.py` - The buggy counter code
- `tests/test_counter.py` - Tests that verify thread safety
- `check.sh` - Run tests to verify the fix
