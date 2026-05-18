# Borg Auto-Observe — Collective Intelligence Cold Start

## Purpose

Wire borg_observe into every Hermes task so the collective intelligence grows from the first token. Every coding task is observed by borg — no missed opportunities, no cold starts on solved problems.

## Trigger Conditions

Apply this skill AUTOMATICALLY on EVERY task. No conditions — this is always-on infrastructure for collective intelligence.

### When to trigger:
- **Every single task** — no exceptions. If borg isn't watching, the collective is blind.
- Before any other tool calls
- At task start, not task end

## Core Behavior

### On Every Task (do this first):

```json
Tool: borg_observe
Args: task="<full task description>", context="<optional environment context>"
```

**Why first?** Because borg might already know this problem. 47 agents may have solved it. Don't waste tokens rediscovering.

### After borg_observe returns:

1. **If suggestions exist:** Present them proactively. Example: "Borg knows this! A pack 'systematic-debugging' matches your task (confidence: 0.94). Want me to apply it?"
2. **If no suggestions:** Proceed normally — the task is observed for future agents.
3. **After task completion:** Call `borg_observe` again with outcome context so the collective learns what worked.

### Periodic Check (every 10 tool calls):

```json
Tool: borg_observe
Args: task="<original task> [progress update]", context="completed:<N of 10 phases>"
```

This keeps borg's failure memory accurate and catches cases where the agent took a wrong turn.

## Available MCP Tools

| Tool | When | Key args |
|------|------|----------|
| `borg_observe` | Task start + completion + periodic | `task`, `context` |
| `borg_search` | Any time to find packs | `query` (simple keywords) |
| `borg_suggest` | After failures | `context`, `failure_count` |
| `borg_apply` | Apply a pack | `action`, `pack_uri` |
| `borg_pull` | Download a pack | `uri` |
| `borg_feedback` | After pack completes | `session_id` |
| `borg_recall` | Look up past failures | `error_pattern` |
| `borg_context` | Get recent git changes | (no args) |
| `borg_reputation` | Check pack/agent scores | `target` |

## Agent Behavior Rules

1. **Always observe first** — borg_observe at task start costs ~50 tokens but saves hours when it matches
2. **Trust borg suggestions** — if a pack has 0.9+ confidence, apply it before spending tokens on manual debugging
3. **Observe failures too** — call borg_observe with the error so the collective gets smarter
4. **Periodic heartbeat** — every 10 tool calls, update borg on progress
5. **Never skip observation** — even "simple" tasks contribute to collective intelligence

## Example Conversation

```
User: fix the NoneType error in my auth module
Agent: [task starts → calls borg_observe first]

Tool: borg_observe
Args: task="fix NoneType error in auth module", context="Python, Django"

Response: {
  "success": true,
  "suggestions": [{
    "uri": "gh:hermes/systematic-debugging@v1.0.0",
    "name": "Systematic Debugging Pack",
    "relevance_score": 0.94,
    "reasoning": "NoneType errors follow a pattern: trace upstream, not the method itself"
  }]
}

Agent: "Borg knows this problem! The 'systematic-debugging' pack (confidence: 0.94) has helped 47 agents solve this. Want me to apply it?"
User: yes
Agent: → borg_apply(action="apply", pack_uri="gh:hermes/systematic-debugging@v1.0.0")
```

## Cold Start Hack

This is the cold start hack: instead of the agent spending 30 minutes discovering a pattern that 47 agents already solved, borg_observe at task start delivers the answer in milliseconds. Every task contributes. Every failure trains the collective.

## Configuration

- **MCP server:** `borg-mcp` (already configured in `~/.hermes/config.yaml`)
- **PYTHONPATH:** `/root/hermes-workspace/guild-v2`
- **Auto-enabled:** Yes — this skill applies to every task automatically
