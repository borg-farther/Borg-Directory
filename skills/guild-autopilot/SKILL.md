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

## Python API (for agent frameworks)

```python
from guild.integrations.agent_hook import guild_on_failure, guild_on_task_start

# On task start — proactive suggestion
suggestion = guild_on_task_start("fixing a pytest failure in test_auth.py")
# Returns: "You might find this useful: systematic-debugging [tested] (Debugging workflow)"

# After 2+ failures — reactive injection
suggestion = guild_on_failure(context="...", failure_count=2)
# Returns: "Guild pack available: systematic-debugging (Debugging workflow). Try: guild://hermes/systematic-debugging"
```

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
