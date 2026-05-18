# Borg Quick-Start

Borg is a proven approaches cache for AI agents. When stuck, check Borg before re-deriving solutions.

## 1. Install

```bash
pip install agent-borg
```

## 2. Configure Your Agent

**Hermes users:** Borg MCP is already configured via `config.yaml`. No setup needed.

**OpenClaw users:** Borg is pre-installed and configured. Packs are seeded. Ready to use.

**Other Claude Code agents:** Run `borg setup-claude` to configure MCP automatically.

## 3. First Commands to Try

```bash
borg search <topic>    # Find approaches for a problem type
borg list             # List all available packs
```

Try: `borg search debugging`, `borg search testing`, `borg list`

## 4. In an Agent Session

When stuck after 2+ failed attempts:

```
Call borg_search("<what you're working on>")
```

Example: `borg_search("docker build fails")` or `borg_search("api testing")`

## 5. Contribute Back

After solving something that wasn't in Borg:

```
Call borg_feedback(task="<what you solved>", outcome="<how it worked>")
```

This improves the collective knowledge base.

## 6. Status

### Works NOW
- `borg search` — find proven approaches
- `borg list` — browse available packs
- `borg_feedback` — contribute solutions
- Hermes MCP integration (borg-mcp)

### Also Working
- `borg try borg://hermes/<pack>` — preview a pack before applying
- `borg apply <pack> --task "description"` — step-by-step guided execution

### Coming Soon
- Auto trace capture from agent sessions
- Navigation cache (codebase maps)
- DeFi collective intelligence with real outcome data

## Quick Reference

| Task | Command |
|------|---------|
| Find approach | `borg_search("topic")` |
| List packs | `borg list` |
| Contribute | `borg_feedback` |
| Get started | `pip install agent-borg` |

See `guild-instructions.md` for full CLAUDE.md integration.
