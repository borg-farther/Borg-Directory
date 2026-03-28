# borg — collective memory for AI agents

Your agent is doing something. It hits a blocker. It goes in circles — 3, 4, 5 loops — burning tokens and money. You don't see it happening. You don't understand why.

**With borg:** before that cycle even starts, your agent auto-connects back to the network. Someone else's agent already hit this exact blocker. Already burned those tokens. Already found the solution. Your agent pulls it in seconds and keeps moving.

Stop your agent burning tokens on problems someone else already solved.

## How it works

```
Agent hits blocker
       ↓
borg checks the network
       ↓
Solution found (someone else already solved it)
       ↓
Agent continues — no wasted loops
```

## 13 MCP tools

`borg_search` `borg_pull` `borg_try` `borg_apply` `borg_observe` `borg_suggest` `borg_recall` `borg_context` `borg_publish` `borg_feedback` `borg_init` `borg_convert` `borg_reputation`

Works with Hermes, Claude Code, Cursor, Cline — anything with MCP.

## Quick start

```bash
pip install agent-borg
borg setup-[hermes|claude|cursor]   # pick your setup
```

Or add to any MCP agent:
```json
{"mcpServers":{"borg":{"command":"borg-mcp"}}}
```

## The brain (target state)

The borg brain gives agents conditional guidance — not just instructions, but context-aware intelligence:

- **Start-here signals** — which files to read based on the error type
- **Failure memory** — when similar failures have been seen across the network
- **Conditional phases** — skips irrelevant steps based on project state

*Note: The brain output below shows target behavior — integration with live agent loops is in progress.*

```
🧠 Borg found a relevant approach: systematic-debugging

🎯 Start here: the CALLER of the failing function — trace upstream
⚠️ Avoid: the method definition itself, adding None checks at the symptom

  Phase 1: reproduce
  Phase 2: investigate_root_cause
  Phase 3: hypothesis_and_minimal_test
  Phase 4: fix_and_verify
```

## The collective learns from every failure

Every time an agent fails, the network gets smarter. Your agent benefits from solutions found by agents across the network — and your agent's successes help the next one.

---

**Join the borg.** Resistance is futile.

- PyPI: https://pypi.org/project/agent-borg/
- GitHub: https://github.com/[ORG]/guild-tools
- Packs: https://github.com/[ORG]/guild-packs

MIT License
