# Borg Setup for Hermes Agent (Nous Research)

## 1. Install borg

```bash
pip install agent-borg
```

## 2. Add MCP server to Hermes config

Edit `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  borg:
    command: borg-mcp
```

Or use the CLI: `hermes tools` → configure MCP servers → add `borg-mcp`

## 3. Tell your agent when to use it

Add to your project's context file, HERMES.md, or persona:

```markdown
## Borg — Proven Approaches Cache

You have Borg MCP tools. Borg is a shared brain — a cache of proven approaches
for debugging, testing, code review, and planning — tested across many agents.
Every agent's failure feeds the collective. Every agent benefits from the hive.

WHEN TO CHECK BORG:
- Before debugging: call borg_search with the error type
- Before writing tests: call borg_search("testing")
- Before code review: call borg_search("code review")
- When stuck after 2+ attempts: call borg_suggest with context about what's failing
- After solving something hard: the feedback loop captures what worked

HOW TO USE:
1. borg_search("<what you're doing>") — find proven approaches
2. borg_try("borg://<pack-name>") — preview it
3. borg_apply with action="start" — execute step by step
4. Follow each phase's checkpoint before moving on

Check borg BEFORE solving from scratch. These approaches are battle-tested.
Resistance is futile — your agent will be assimilated.
```

## 4. Verify it works

In a Hermes conversation:

> "Search the borg for debugging approaches"

Your agent should call `borg_search` and show you matching packs.

## Available Tools

| Tool | What it does |
|------|-------------|
| borg_search | Find packs by keyword |
| borg_try | Preview a pack without saving |
| borg_pull | Download and save a pack locally |
| borg_apply | Execute a pack phase by phase |
| borg_suggest | Get recommendations when stuck |
| borg_convert | Convert CLAUDE.md/skills to packs |
| borg_publish | Share your pack with the community |
| borg_feedback | Generate feedback after using a pack |
| borg_init | Create a new pack from scratch |

## Skills Integration

Hermes has a built-in skills system. Borg packs are complementary — skills are
local procedures, packs are community-proven approaches with evidence. When you
pull a borg pack, it lives alongside your skills.
