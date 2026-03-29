# Borg Autopilot — Zero-Config Borg Experience

## Purpose

Borg Autopilot is a **self-configuring skill** that makes borg work automatically,
without any user setup or CLAUDE.md editing. A user only needs agent-borg installed
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

**Action:** Call `borg_on_task_start(task_description)` and include the result
in your reasoning. If a pack is suggested, mention it proactively to the user.

### 2. Failure Detection (after 2+ consecutive failures)
When the agent has failed 2 or more consecutive times on the same task:
- Call `borg_on_failure(context=recent_conversation, failure_count=N)`
- Inject the returned suggestion into your context as a **system message**
- Example injection: `"Borg notice: A tested borg pack 'systematic-debugging' is available for this task. Apply it with: borg apply systematic-debugging --task <task>"`

### 3. Phase-by-Phase Pack Application
When applying a borg pack, follow this strict sequence:

1. **Before applying:** Run `borg try <pack_uri>` to preview phases and validate safety
2. **Start:** Run `borg apply <pack> --task "<task description>"`
3. **Per phase:** Read the phase description, complete the work, then advance
4. **Track progress:** Log each completed phase in your context
5. **On completion:** Generate feedback with `borg feedback <session_id>`

### 4. Completion Feedback
After a pack session completes (success or failure):
- Call `borg feedback <session_id>` to get structured feedback
- Present the feedback to the user in a clear summary
- Note what worked and what didn't for future sessions

## Available Tools / Commands

```bash
# Preview a pack (always do this first)
borg try <uri>

# Start applying a pack
borg apply <pack_name> --task "<task description>"

# Get session feedback
borg feedback <session_id>

# Search for relevant packs
borg search <query>
```

## Python API (for agent frameworks)

```python
from borg.integrations.agent_hook import borg_on_failure, borg_on_task_start

# On task start — proactive suggestion
suggestion = borg_on_task_start("fixing a pytest failure in test_auth.py")
# Returns: "You might find this useful: systematic-debugging [tested] (Debugging workflow)"

# After 2+ failures — reactive injection
suggestion = borg_on_failure(context="...", failure_count=2)
# Returns: "Borg pack available: systematic-debugging (Debugging workflow). Try: borg://hermes/systematic-debugging"
```

## Agent Behavior Rules

1. **Always check borg first** for debug/test/review tasks — don't waste time
2. **Never apply a pack without previewing** with `borg try` first
3. **Apply packs phase by phase** — don't skip steps
4. **Generate feedback** after every pack session
5. **Respect tried_packs** — don't suggest the same failed pack twice
6. **Safety first** — if `borg try` shows safety threats, warn the user before proceeding

## Integration Points

- **Hermes MCP:** The borg MCP server must be configured in `~/.hermes/config.yaml`
- **agent_hook.py:** Contains `borg_on_failure()` and `borg_on_task_start()` functions
- **Zero user action required:** The skill file itself is the only setup needed

## Example Conversation

User: "my auth tests are failing after I added JWT"
Agent: [detects "test" + "failing" → calls borg_on_task_start]
→ "I see you're dealing with test failures. Borg suggests 'test-recovery' [tested] (Test debugging workflow) — try: borg://hermes/test-recovery"

User: "why is my server crashing on startup"
Agent: [detects "crash" → calls borg_on_task_start]
→ "This looks like a startup crash. Borg suggests 'systematic-debugging' (Debugging workflow) — try: borg://hermes/systematic-debugging"

## The Borg Mantra

> "Your agent is burning tokens re-deriving approaches other agents already proved. Every failure feeds the collective. Every agent benefits from the hive. Resistance is futile — your agent will be assimilated."
