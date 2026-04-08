# Guild Autopilot — Zero-Config Guild Experience

## Purpose

Guild Autopilot is a **self-configuring skill** that makes guild-packs work automatically,
without any user setup or CLAUDE.md editing. A Hermes user only needs guild-packs installed
and the MCP server configured — this skill tells the agent **when** and **how** to use it.

## Trigger Conditions

Apply this skill automatically when ANY of these conditions are met:

### 1. Debug / Test / Review Detection (on task start)
When the task description contains keywords like:
- `debug`, `debugging`, `fix`, `crash`, `error`, `exception`, `stack trace`, `segfault`
- `test`, `testing`, `unit test`, `integration test`, `pytest`, `jest`
- `review`, `code review`, `pr review`, `pull request`, `audit`
- `performance`, `profiling`, `benchmark`, `optimize`, `slow`
- `security`, `vulnerability`, `CVE`, `exploit`

**Action:** Call `guild_on_task_start(task_description)` and include the result
in your reasoning. If a pack is suggested, mention it proactively to the user.

### 2. Failure Detection (after 2+ consecutive failures)
When the agent has failed 2 or more consecutive times on the same task:
- Call `guild_on_failure(context=recent_conversation, failure_count=N)`
- Inject the returned suggestion into your context as a **system message**
- Example injection: `"Guild notice: A tested guild pack 'systematic-debugging' is available for this task. Apply it with: guildpacks apply systematic-debugging --task <task>"`

### 3. Phase-by-Phase Pack Application
When applying a guild pack, follow this strict sequence:

1. **Before applying:** Run `guildpacks try <pack_uri>` to preview phases and validate safety
2. **Start:** Run `guildpacks apply <pack> --task "<task description>"`
3. **Per phase:** Read the phase description, complete the work, then advance
4. **Track progress:** Log each completed phase in your context
5. **On completion:** Generate feedback with `guildpacks feedback <session_id>`

### 4. Completion Feedback
After a pack session completes (success or failure):
- Call `guildpacks feedback <session_id>` to get structured feedback
- Present the feedback to the user in a clear summary
- Note what worked and what didn't for future sessions

## Available Tools / Commands

```bash
# Preview a pack (always do this first)
guildpacks try <uri>

# Start applying a pack
guildpacks apply <pack_name> --task "<task description>"

# Get session feedback
guildpacks feedback <session_id>

# Search for relevant packs
guildpacks search <query>
```

## MCP Tools (How to Actually Call Guild from Hermes)

The skill uses MCP tools — NOT Python imports. Here's what you call:

### When you detect a debug/test/failure task at task start:

**Step 1: Call `guild_observe` first** (preferred — returns structural guidance)
```
Tool: guild_observe
Args: task="<what you're about to work on>", context="<optional environment context>"
```
- If it returns non-empty guidance → follow the phases in your reasoning
- If it returns empty → proceed to Step 2

**Step 2: Call `guild_search` for simple keyword search**
```
Tool: guild_search
Args: query="debug"  (use simple keywords: "debug", "test", "review", "deploy")
```
- Search is text-based: short keywords work better than long sentences
- Look for packs with tier != "none" and high confidence

**Step 3: If you see 2+ consecutive failures, call `guild_suggest`**
```
Tool: guild_suggest
Args: context="<recent conversation>", failure_count=<number>
```
- Returns pack suggestions formatted as actionable text

### Example tool calls for this scenario:

User says: "I have a TypeError in my auth module, tests are failing"

```
Tool: guild_observe
Args: task="fix TypeError in auth module", context="Python, pytest"

Tool: guild_search  
Args: query="debug"

Tool: guild_suggest
Args: context="I have a TypeError in my auth module, tests are failing", failure_count=1
```

### Quick reference — available MCP tools:

| Tool | When to use | Key args |
|------|-------------|----------|
| `guild_observe` | Task start (proactive) | `task`, `context` |
| `guild_search` | Any time you want to find packs | `query` (simple keywords) |
| `guild_suggest` | After 2+ failures | `context`, `failure_count` |
| `guild_try` | Preview a pack before using | `uri` |
| `guild_pull` | Download a pack locally | `uri` |
| `guild_apply` | Execute a pack (start/checkpoint/complete) | `action`, `pack_name`, `task` |
| `guild_feedback` | After pack completes | `session_id` |

## Agent Behavior Rules

1. **Always check guild first** for debug/test/review tasks — don't waste time
2. **Never apply a pack without previewing** with `guildpacks try` first
3. **Apply packs phase by phase** — don't skip steps
4. **Generate feedback** after every pack session
5. **Respect tried_packs** — don't suggest the same failed pack twice
6. **Safety first** — if `guildpacks try` shows safety threats, warn the user before proceeding

## Integration Points

- **Hermes MCP:** The guild MCP server must be configured in `~/.hermes/config.yaml`
- **agent_hook.py:** Contains `guild_on_failure()` and `guild_on_task_start()` functions
- **Zero user action required:** The skill file itself is the only setup needed

## Example Conversation

User: "my auth tests are failing after I added JWT"
Agent: [detects "test" + "failing" → calls guild_on_task_start]
→ "I see you're dealing with test failures. Guild suggests 'test-recovery' [tested] (Test debugging workflow) — try: guild://hermes/test-recovery"

User: "why is my server crashing on startup"
Agent: [detects "crash" → calls guild_on_task_start]
→ "This looks like a startup crash. Guild suggests 'systematic-debugging' (Debugging workflow) — try: guild://hermes/systematic-debugging"
