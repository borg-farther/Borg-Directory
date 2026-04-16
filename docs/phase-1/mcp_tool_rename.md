# MCP Tool Rename: borg_observe -> error_lookup (G10)

## Why deferred from Day 2

Inspected borg/integrations/mcp_server.py (3115 lines) on 2026-04-16. The rename touches at least 7 locations:

- Line ~430: JSON schema entry "name": "borg_observe" in the tool list
- Line 1679: function def `def borg_observe(...)`
- Line 1845: embedded string referring to sibling tool borg_rate
- Line 1998: user-facing error string "Call borg_observe first."
- Line 2810: dispatcher whitelist tuple
- Line 2965: dispatcher `elif name == "borg_observe":`
- Line 3087-3091: wrapper pattern around the original function

Plus the live gateway process reads this file. A broken import or misnamed dispatcher case takes Hermes offline.

## Minimal-viable implementation (30-45 min + verify)

### Step 1: Backup
```bash
cp borg/integrations/mcp_server.py borg/integrations/mcp_server.py.pre-rename
```

### Step 2: Add error_lookup as alias in the tool schema
Near line 430, duplicate the borg_observe tool dict as error_lookup. Keep borg_observe with a deprecation note.

### Step 3: Extend dispatcher whitelist (line ~2810)
Add "error_lookup" to the tuple alongside borg_observe.

### Step 4: Add dispatcher case (line ~2965)
```python
elif name == "error_lookup":
    return borg_observe(**arguments)
```

### Step 5: Leave function name as-is
Full function-body rename is Phase 2 cleanup after 90-day sunset (2026-07-16).

## Deploy

1. Apply on branch phase-1-rename
2. Python import-check: `python3 -c "from borg.integrations import mcp_server"`
3. Restart gateway: `pkill -9 -f "gateway run" && systemctl --user start hermes-gateway`
4. Watch /var/log/hermes-gateway.log for 10 min

## Rollback
```bash
cp borg/integrations/mcp_server.py.pre-rename borg/integrations/mcp_server.py
pkill -9 -f "gateway run"
systemctl --user start hermes-gateway
```

## Post-ship

- Announce 2026-07-16 sunset 30 days ahead on any user channel.
- Update docs/ROADMAP.md G10 to green.
- Update README.md MCP config example to use error_lookup.
