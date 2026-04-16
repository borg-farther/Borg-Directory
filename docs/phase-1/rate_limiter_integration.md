# Rate Limiter Integration Plan (M6 / G5)

Module ships in `borg/core/rate_limiter.py` in commit on `phase-0-honest`. Not yet wired into `mcp_server.py`.

## Why not wired now

Same reason as MCP rename (see mcp_tool_rename.md): `mcp_server.py` is 3115 lines and drives a live gateway. Risky to edit via heredoc. Scheduled for a maintenance window.

## Integration steps (when scheduled)

### Backup
```bash
cp borg/integrations/mcp_server.py borg/integrations/mcp_server.py.pre-ratelimit
```

### Add import at top of mcp_server.py
```python
from borg.core.rate_limiter import check_rate_limit, RateLimitExceeded
```

### Wrap each tool function
For each of `borg_observe`, `borg_rate`, `borg_search`, `borg_suggest`, `borg_publish`, add at the top of the function:

```python
try:
    check_rate_limit('borg_observe', agent_id=context_dict.get('agent_id', 'anonymous') if context_dict else 'anonymous')
except RateLimitExceeded as e:
    return f"RATE_LIMIT: {e}"
```

### Restart gateway
```bash
pkill -9 -f "gateway run"
systemctl --user start hermes-gateway
```

### Verify
Send 15 rapid `borg_observe` calls from Hermes. Expect first 10 to succeed, 11+ to return RATE_LIMIT.

## Tuning

Default limits (in `_DEFAULT_LIMITS`):
- `borg_observe`: 60/min, burst 10
- `borg_rate`: 30/min, burst 5
- `borg_publish`: 5/min, burst 2

Public launch requires re-tuning based on observed traffic. Start conservative; raise based on real usage.

## Rollback
```bash
cp borg/integrations/mcp_server.py.pre-ratelimit borg/integrations/mcp_server.py
pkill -9 -f "gateway run"
systemctl --user start hermes-gateway
```

## Known limitations

- In-process only: does NOT survive gateway restart (buckets reset).
- Single-node: if Borg scales to multiple gateways, need Redis-backed bucket store.
- Trusts `context_dict.agent_id`: a malicious agent can claim different IDs to circumvent. Phase 2 addresses this via signed agent credentials.
