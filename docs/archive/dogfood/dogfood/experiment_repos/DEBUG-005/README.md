# DEBUG-005: Memory Leak in Cache

## Task Description
The `Cache` class uses an unbounded dict that grows forever as items are added. This causes a memory leak in long-running applications.

The tests verify that after inserting 1000 items into a cache with `max_size=100`, the cache should not exceed 100 items.

## Your Task
Fix `src/cache.py` to add LRU eviction so the cache respects `max_size` and evicts the least recently used items when full.

## Files
- `src/cache.py` - The buggy unbounded cache
- `tests/test_cache.py` - Tests that verify bounded behavior
- `check.sh` - Run tests to verify the fix
