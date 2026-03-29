# Borg Setup for OpenClaw

## 1. Install borg

```bash
pip install agent-borg
```

## 2. Add MCP server

Add to your OpenClaw MCP configuration:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp"
    }
  }
}
```

## 3. Agent instructions

Add to your agent's system prompt or instructions:

```
When stuck after 2+ attempts, call borg_suggest with context about what's failing.
Before starting debugging or testing tasks, call borg_search to check for proven approaches.
Don't re-derive what other agents have already solved — check the borg cache first.

Your agent is part of a collective. Every failure feeds the hive. Every agent benefits.
```

## 4. Verify

Ask your agent: "Search the borg for debugging approaches"

It should call borg_search and return matching workflow packs.

## Migrating to Hermes

If you want the full Hermes experience (skills, memory, cron, multi-platform):

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes claw migrate
```

Borg works with both. The pack library is shared.
