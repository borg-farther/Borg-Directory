---
name: borg
description: Failure memory for AI coding agents. Use when you have a concrete error, failed test, install/config/deploy failure, or repeated debugging loop and want ACTION / STOP / VERIFY guidance with explicit confidence. Not for simple tasks that need no structure.
compatibility: "Requires the borg MCP server or CLI. Install with the package name: pip install agent-borg. Configure your agent to run the MCP server command: borg-mcp."
metadata:
  borg:
    version: "2.0"
    type: failure-memory
    homepage: https://github.com/borg-farther/Borg-Directory
    registry: borg://registry
---

# Borg — Failure Memory for AI Coding Agents

Borg helps agents check prior rescue guidance before repeating known debugging dead ends. When there is no confident match, it should return `NO_CONFIDENT_MATCH` instead of forcing advice.

## What is Borg?

Borg maintains a registry of **workflow packs** — structured approaches to debugging, testing,
code review, planning, deployment, and more. Each pack should expose its confidence level,
known failure cases, checkpoints, and verification rules.

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

### Step 0: Concrete Failure Rescue First

If you have an exact error, failing command output, traceback, or install/config/deploy failure, do **not** start with pack search. Ask Borg for the day-one rescue packet first:

```text
Tool: error_lookup
Args: input="<exact error or failing command output>", show_guidance=false
```

If your MCP host only exposes canonical Borg names, use the identical canonical call:

```text
Tool: borg_rescue
Args: input="<exact error or failing command output>", show_guidance=false
```

CLI equivalent:

```bash
borg rescue "<exact error or failing command output>"
```

Use `borg_observe(task="<task>", context="<tech stack>")` for broader task-start guidance when there is not yet a concrete failure. Use pack search/apply only after rescue/observe or when you deliberately need a workflow pack.

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

Then checkpoint each phase with explicit evidence:
```
Tool: borg_apply
Args: action="checkpoint", session_id="<session-id>", phase_name="<phase-name>", status="passed", evidence="<what verified it>"
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
| `error_lookup` | Plain-English rescue alias for concrete failures | `input` |
| `borg_rescue` | Canonical ACTION / STOP / VERIFY rescue packet | `input` |
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
5. **Don't use Borg for trivial fixes** — Borg is for problems that benefit from structured approaches

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
# Concrete error rescue first
borg rescue "<exact error or failing command output>"

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

*Powered by [borg](https://github.com/borg-farther/Borg-Directory) — failure memory for AI coding agents.*
