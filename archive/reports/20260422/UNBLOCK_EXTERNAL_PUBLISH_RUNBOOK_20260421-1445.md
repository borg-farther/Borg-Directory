# Unblock external publish (2 hard gates)

## Gate A — Publisher tier must be VALIDATED (score >= 10)
Observed in `borg/core/publish.py` (`_check_publish_access`): COMMUNITY is blocked from publish.

### Fast legitimate path
Use a publisher identity that already has VALIDATED tier in the guild reputation store.

If you want current identities (`agent://hermes-seed`, `agent://hermes/guild-team`) to pass:
1. Submit/record at least one quality pack publication event at confidence `validated` (weight 15), OR enough contribution actions to reach score >=10.
2. Re-check profile and tier.

## Gate B — guild MCP server is unreachable
Your config points `guild` and `borg-mcp` to:
- command: `/root/.hermes/hermes-agent/venv/bin/python3`
- args: `-m borg.integrations.mcp_server`
- env: `PYTHONPATH=/root/hermes-workspace/borg`

### Recovery steps
1. On host shell, verify module launch works:
   `/root/.hermes/hermes-agent/venv/bin/python3 -m borg.integrations.mcp_server`
2. If import fails, reinstall/sync borg package in that venv and verify `PYTHONPATH` path exists.
3. Restart Hermes agent process so MCP connections are re-established from fresh startup.
4. Validate by calling `mcp_guild_borg_publish(action='list')` until success.

## Then execute publish
- publish `systematic-debugging`
- publish `test-driven-development`
- publish `plan`
- publish `quick-debug`

and capture outputs into final rollout proof doc.
