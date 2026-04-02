---
type: workflow_pack
version: "1.0"
id: timeout-hang
problem_class: timeout_hang
framework: python
problem_signature:
  error_types:
    - TimeoutError
    - GatewayTimeout
    - ConnectionRefused
    - Connection timed out
  framework: python
  problem_description: The code is waiting for something that never completes. A network call, a lock, or a loop that never exits.
root_cause:
  category: timeout_hang
  explanation: The code waited for a resource that did not respond within the expected time. The resource is either slow, down, unreachable, or the timeout is set too low.
investigation_trail:
  - file: "@blocking_call"
    position: FIRST
    what: Find the blocking network call or database query
    grep_pattern: requests|urllib|httpx|aiohttp|connect|query
  - file: config.py
    position: SECOND
    what: Check configuration for the service being contacted
    grep_pattern: timeout|TIMEOUT|url|HOST
  - file: "@service_check"
    position: THIRD
    what: Check if the service is actually reachable
    grep_pattern: ""
resolution_sequence:
  - action: increase_timeout
    command: Increase the timeout value if the resource is legitimately slow
    why: Some operations take longer than the default timeout
  - action: add_retry
    command: Use tenacity or requests.adapters.HTTPAdapter with retry and exponential backoff
    why: Transient timeouts often succeed on retry with backoff
  - action: circuit_breaker
    command: Use pybreaker or similar to stop calling a failing service
    why: Circuit breakers prevent hammering a down service
  - action: fix_url
    command: Verify the service URL, host, and port are correct
    why: Wrong configuration causes immediate or premature timeout
anti_patterns:
  - action: Setting timeout to None
    why_fails: Indefinite hang in production
  - action: Catching TimeoutError and ignoring it
    why_fails: Silent failures are worse than visible failures
  - action: Retrying without backoff
    why_fails: Hammering a failing service makes it slower to recover
evidence:
  success_count: 28
  failure_count: 5
  success_rate: 0.85
  avg_time_to_resolve_minutes: 4.0
  uses: 33
provenance: Seed pack v1 | General Python debugging | 2026-04-02
---

## When to Use This Pack

Use when you encounter:
- `TimeoutError` or `GatewayTimeout`
- `ConnectionRefused` or `Connection timed out`
- Any blocking operation that hangs indefinitely

Do NOT use when the issue is concurrent access to shared state.
