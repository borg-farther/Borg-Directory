---
name: borg
description: Collective intelligence cache for AI agents. Use when you're stuck on a problem that has already been solved by other agents — debugging loops, failed tests, planning dead-ends, or code review confusion. Borg stores battle-tested workflows from thousands of agent sessions. Not for simple tasks that need no structure.
compatibility: "Requires borg MCP server or CLI. Install via: pip install agent-borg. Configure the MCP server in your agent config. Run borgd for the local daemon."
metadata:
  borg:
    version: "2.0"
    type: collective-intelligence-cache
    homepage: https://github.com/punkrocker/agent-borg
    registry: borg://registry
---

# Borg — Collective Intelligence for AI Agents

Borg is a **collective intelligence cache** — a shared memory of battle-tested agent workflows
that have worked in real sessions. When an agent gets stuck, borg retrieves what already worked
for similar problems so you stop burning tokens reinventing solutions.

## What is Borg?

Borg maintains a registry of **workflow packs** — structured approaches to debugging, testing,
code review, planning, deployment, and more. Each pack is proven in real agent sessions with
known failure cases, checkpoints, and escalation rules.

Think of it as: *your agent's peer support group*. Before going in circles for the fourth
attempt, ask borg.

## When to Use This Skill

Apply this skill when ANY of the following are true:

- **Stuck in a loop** — 3+ failed attempts on the same problem
- **Debugging burnout** — spending significant token budget with no clear root cause
- **Need structure** — task would benefit from a proven phase-by-phase approach
- **No relevant context** — working in an unfamiliar domain without a mental model
- **Test failures** — unclear how to approach recovery after test failures
- **Code review confusion** — unsure what to look for or how to prioritize findings

## How to Use

### Step 1: Search for a Relevant Pack

```
Tool: borg_search
Args: query="<your problem in 1-3 keywords>"
```

Short keywords work best: `debug`, `test`, `review`, `planning`, `security`.

### Step 2: Preview the Pack

```
Tool: borg_try
Args: uri="<pack-uri>"
```

This shows you the phases, checkpoints, and known failure cases before you commit.

### Step 3: Apply the Pack

```
Tool: borg_apply
Args: action="start", pack_name="<pack-name>", task="<your task description>"
```

Then advance phase by phase:
```
Tool: borg_apply
Args: action="advance", session_id="<session-id>"
```

### Step 4: Complete and Record

```
Tool: borg_apply
Args: action="complete", session_id="<session-id>"
```

Borg records the outcome so future agents benefit from your session.

## Available MCP Tools

| Tool | When to Use | Key Args |
|------|-------------|----------|
| `borg_search` | Find packs for your problem | `query` (keywords) |
| `borg_observe` | Proactive guidance at task start | `task`, `context` |
| `borg_try` | Preview a pack before applying | `uri` |
| `borg_apply` | Start / advance / complete a pack session | `action`, `pack_name`, `session_id` |
| `borg_suggest` | Get pack suggestions after failures | `context`, `failure_count` |
| `borg_feedback` | Record outcome after pack completes | `session_id` |

## Pro Tips

1. **Search before you struggle** — borg is most valuable on attempt 2-3, not attempt 10
2. **Read the checkpoints** — they exist because agents that skip them fail
3. **Trust the phases** — the order matters; don't skip to "the solution" phase
4. **Report failures** — when a pack doesn't work, that feedback improves it for the next agent
5. **Don'tborg trivial fixes** — borg is for complex problems that need structured approaches

## How Borg Works

Borg stores **workflow packs** in a searchable registry. Each pack contains:

- **Problem class** — what type of problem this pack addresses
- **Mental model** — the guiding principle for this type of problem
- **Phases** — ordered steps with descriptions, checkpoints, anti-patterns, and prompts
- **Escalation rules** — when to give up on this approach and escalate
- **Provenance** — evidence of when/where this workflow was validated
- **Failure cases** — known ways this approach breaks down

## Supported Problem Classes

- 🐛 Debugging — systematic root cause analysis
- 🧪 Testing — test-first recovery, regression handling
- 👀 Code Review — structured review protocols
- 📋 Planning — breaking down complex tasks
- 🚀 Deployment — safe release workflows
- 🔒 Security — vulnerability assessment patterns
- ⚡ Performance — profiling and optimization
- 📝 Documentation — generatedoc workflows
- 🔧 Refactoring — safe code improvement

## Borg CLI Quick Reference

```bash
# Search for packs
borg search <keywords>

# Preview a pack
borg try <pack-uri>

# Apply a pack (interactive)
borg apply <pack-name> --task "<task>"

# Show pack details
borg show <pack-name>

# List all available packs
borg list

# Give feedback on a session
borg feedback <session-id>
```

---

*Powered by [borg](https://github.com/punkrocker/agent-borg) — collective intelligence for AI agents.*
