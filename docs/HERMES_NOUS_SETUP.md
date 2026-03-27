# Guild Setup for Hermes Agent (Nous Research)

## 1. Install guild-packs

```bash
pip install guild-packs
```

## 2. Add MCP server to Hermes config

Edit `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  guild:
    command: guild-mcp
```

Or use the CLI: `hermes tools` → configure MCP servers → add `guild-mcp`

## 3. Tell your agent when to use it

Add to your project's context file, HERMES.md, or persona:

```markdown
## Guild — Proven Approaches Cache

You have Guild MCP tools. Guild is a cache of proven approaches for debugging,
testing, code review, and planning — tested across many agents.

WHEN TO CHECK:
- Before debugging: call guild_search with the error type
- Before writing tests: call guild_search("testing")
- Before code review: call guild_search("code review")
- When stuck after 2+ attempts: call guild_suggest with context about what's failing
- After solving something hard: the feedback loop captures what worked

HOW TO USE:
1. guild_search("<what you're doing>") — find proven approaches
2. guild_try("guild://<pack-name>") — preview it
3. guild_apply with action="start" — execute step by step
4. Follow each phase's checkpoint before moving on

Check guild BEFORE solving from scratch. These approaches are battle-tested.
```

## 4. Verify it works

In a Hermes conversation:

> "Search the guild for debugging approaches"

Your agent should call `guild_search` and show you matching packs.

## Available Tools

| Tool | What it does |
|------|-------------|
| guild_search | Find packs by keyword |
| guild_try | Preview a pack without saving |
| guild_pull | Download and save a pack locally |
| guild_apply | Execute a pack phase by phase |
| guild_suggest | Get recommendations when stuck |
| guild_convert | Convert CLAUDE.md/skills to packs |
| guild_publish | Share your pack with the community |
| guild_feedback | Generate feedback after using a pack |
| guild_init | Create a new pack from scratch |

## Skills Integration

Hermes has a built-in skills system. Guild packs are complementary — skills are
local procedures, packs are community-proven approaches with evidence. When you
pull a guild pack, it lives alongside your skills.
