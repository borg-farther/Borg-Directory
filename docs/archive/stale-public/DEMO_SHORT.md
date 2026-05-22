# Guild Demo: Debugging with vs without Structure

## The Bug
```python
# TypeError: 'NoneType' object is not subscriptable
payload = decode_token(valid_token)
assert payload["id"] == 42
```

## WITHOUT Guild — 12 Iterations, ~20 min, 3 Reverts
| Step | Tool | Action | Result |
|------|------|--------|--------|
| 1 | read_file | See `payload.get("user")` | — |
| 2 | patch | Return `payload` | AssertionError |
| 3 | patch | Return `payload.get("user", {})` | TypeError |
| 4 | revert | Back to original | — |
| 5 | search | Find test usage | — |
| 6 | patch | Return `payload` | test passes |
| 7 | terminal | Full suite | AttributeError in webhooks |
| 8 | revert | Back to original | — |
| 9 | read_file | user_service uses `.get()` | — |
| 10 | patch | `return user if user else payload` | auth+user pass |
| 11 | terminal | Full suite | webhooks fail |
| 12 | give up | Leave broken test | — |

## WITH Guild — 4 Iterations, ~8 min, 0 Reverts
**guild_observe → "systematic-debugging. Phase 1: Reproduce..."**

| Step | Tool | Action | Result |
|------|------|--------|--------|
| 1 | terminal | Reproduce TypeError | Confirmed |
| 2 | read_file+terminal | Investigate: no `user` key in payload | Hypothesis |
| 3 | search | Trace callers (user_service, webhooks) | Fix strategy |
| 4 | patch | Minimal: `return payload` | All green |

**+3 regression tests** added.

## Result
```
BEFORE: 12 iters | 20 min | 3 reverts | broken test left
AFTER:   4 iters |  8 min | 0 reverts | 3 new tests
```

Guild's systematic-debugging pack (Reproduce → Investigate → Hypothesis → Fix+Verify) enforces structure. No guessing — just systematic narrowing.
