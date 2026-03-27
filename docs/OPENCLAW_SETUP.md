# Guild Setup for OpenClaw

## 1. Install guild-packs

```bash
pip install guild-packs
```

## 2. Add MCP server

Add to your OpenClaw MCP configuration:

```json
{
  "mcpServers": {
    "guild": {
      "command": "guild-mcp"
    }
  }
}
```

## 3. Agent instructions

Add to your agent's system prompt or instructions:

```
When stuck after 2+ attempts, call guild_suggest with context about what's failing.
Before starting debugging or testing tasks, call guild_search to check for proven approaches.
Don't re-derive what other agents have already solved — check the guild cache first.
```

## 4. Verify

Ask your agent: "Search the guild for debugging approaches"

It should call guild_search and return matching workflow packs.

## Migrating to Hermes

If you want the full Hermes experience (skills, memory, cron, multi-platform):

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes claw migrate
```

Guild works with both. The pack library is shared.
