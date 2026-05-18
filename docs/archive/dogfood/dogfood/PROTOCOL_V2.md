# Experiment Protocol V2 — Fixes from Preliminary Results

## Flaws Found in V1
1. **No counterbalancing** — control always ran first, treatment second
2. **No actual borg_search** — treatment just got a better prompt
3. **Tasks too easy** — 7/10 solved trivially by control
4. **Token measurement proxy** — used output text length, not API tokens

## V2 Protocol Fixes

### Fix 1: Counterbalancing
- Alternate: odd-numbered tasks run treatment FIRST, even run control FIRST
- Record run_order for every result
- This controls for "second attempt advantage"

### Fix 2: Actual borg_search
- Treatment agents MUST call borg_search via Python import
- Verified working command:
  ```
  python3 -c "import sys; sys.path.insert(0,'/root/hermes-workspace/borg'); from borg.core.search import borg_search; print(borg_search('debugging'))"
  ```
- Treatment prompt explicitly requires calling this before starting

### Fix 3: Use harder remaining tasks
- REVIEW-001 (security vulns), REVIEW-002 (performance)
- REFACTOR-001 (duplicate extraction), REFACTOR-002 (callback→async)
- TEST-003 (integration tests), TEST-004 (edge case tests)
- These require more reasoning than the DEBUG tasks

### Fix 4: Token measurement
- Use subagent API call metadata: tokens.input + tokens.output from delegate_task results
- This is the actual API token count, not a proxy
