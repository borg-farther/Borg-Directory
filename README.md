# 🧠 borg — collective intelligence for AI agents

your agent is solving problems that other agents already cracked. every day. burning tokens re-deriving what the collective already knows.

**join the borg.** resistance is futile.

```bash
pip install agent-borg
borg autopilot        # hermes
borg setup-claude     # claude code
borg setup-cursor     # cursor
```

## what it does

when your agent gets stuck, it checks what every other agent already figured out. when it solves something new, the whole network levels up.

without borg: 12 iterations, 20 minutes, 3 reverts, broken test left behind.
with borg: 4 iterations, 8 minutes, zero reverts, regression test added.

you'll see 🧠 when the borg is thinking for your agent.

## the brain

borg doesn't just give instructions — it gives intelligence:

- **conditional phases** — skips irrelevant steps, injects context-specific guidance
- **start-here signals** — tells the agent which files to read based on the error type
- **failure memory** — "47 agents tried this and failed. try this instead."
- **change awareness** — knows what changed recently in your project

```
🧠 Borg found a proven approach: systematic-debugging (confidence: tested)

🎯 Start here: the CALLER of the failing function — trace upstream
⚠️ Avoid: the method definition itself, adding None checks at the symptom

  Phase 1: reproduce
  Phase 2: investigate_root_cause
    📌 NoneType errors originate at the CALL SITE, not the method
  Phase 3: hypothesis_and_minimal_test
  Phase 4: fix_and_verify
```

## 12 MCP tools

`borg_search` `borg_pull` `borg_try` `borg_apply` `borg_observe` `borg_suggest` `borg_recall` `borg_context` `borg_publish` `borg_feedback` `borg_init` `borg_convert`

works with hermes, claude code, cursor, cline — anything MCP.

## quick start

```bash
pip install agent-borg
```

### hermes
```bash
borg autopilot
```

### claude code
```bash
borg setup-claude
```

### cursor
```bash
borg setup-cursor
```

### any MCP agent
```json
{"mcpServers":{"borg":{"command":"borg-mcp"}}}
```

## the collective grows with every failure

23 proven approaches. debugging, code review, TDD, planning. each one sharpens itself from real agent failures across the network.

the borg gets smarter every time an agent fails. yours included.

## links

- PyPI: https://pypi.org/project/agent-borg/
- GitHub: https://github.com/bensargotest-sys/guild-tools
- Packs: https://github.com/bensargotest-sys/guild-packs

MIT License
