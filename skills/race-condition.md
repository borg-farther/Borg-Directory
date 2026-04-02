---
type: workflow_pack
version: "1.0"
id: race-condition
problem_class: race_condition
framework: python
problem_signature:
  error_types:
    - TimeoutError
    - ConcurrencyError
  framework: python
  problem_description: Two code paths execute concurrently and interfere with each other. The error appears intermittently. Adding logs or breakpoints makes it disappear because those slow execution.
root_cause:
  category: race_condition
  explanation: Two or more code paths accessed shared state concurrently. The first path read a value, the second modified or deleted it before the first wrote, causing one path to operate on stale or invalid state.
investigation_trail:
  - file: "@shared_resource"
    position: FIRST
    what: Find the shared state accessed by both concurrent paths
    grep_pattern: ""
  - file: "@error_location"
    position: SECOND
    what: Read the line that raised the concurrency error
    grep_pattern: ""
  - file: "@timing_window"
    position: THIRD
    what: Identify the window between when the first path reads and when it writes
    grep_pattern: ""
resolution_sequence:
  - action: add_lock
    command: "lock = threading.Lock(); with lock: # access shared state"
    why: Lock ensures only one code path can access shared state at a time
  - action: database_transaction
    command: SELECT FOR UPDATE (PostgreSQL) or LOCK TABLE within a transaction
    why: Database-level locking prevents concurrent transactions from seeing uncommitted state
  - action: atomic_operation
    command: Use Redis INCR, SETNX, or atomic operations instead of read-modify-write
    why: Atomic operations are inherently race-free
anti_patterns:
  - action: Adding time.sleep()
    why_fails: Masks the problem temporarily but fails under real load
  - action: Catching the exception and retrying without backoff
    why_fails: Creates retry storms under load
  - action: Disabling concurrency entirely
    why_fails: Defeats the purpose of async code
evidence:
  success_count: 11
  failure_count: 6
  success_rate: 0.65
  avg_time_to_resolve_minutes: 12.0
  uses: 17
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `TimeoutError` or `ConcurrencyError` intermittently
- Errors that only appear under load
- Errors that disappear when you add print statements or breakpoints
- `RuntimeError: dictionary changed size during iteration`

Do NOT use when the timeout is from network operations.
