# Borg Autopilot — Zero-Config Borg Experience

## Purpose

Borg Autopilot is a **self-configuring skill** that makes agent-borg work automatically,
without any user setup or CLAUDE.md editing. A Hermes user only needs agent-borg installed
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

## Available Commands

```bash
borg try <uri>     # Preview a pack (always do this first)
borg apply <pack> --task "<task description>"  # Start applying
borg feedback <session_id>  # Get session feedback
borg search <query>  # Search for relevant packs
```

## Python API

```python
from borg.integrations.agent_hook import borg_on_failure, borg_on_task_start

# On task start — proactive suggestion
suggestion = borg_on_task_start("fixing pytest failures")
# Returns: "You might find this useful: systematic-debugging [tested]..."

# After 2+ failures — reactive injection
suggestion = borg_on_failure(context="...", failure_count=2)
# Returns: "Borg pack available: systematic-debugging..."
```

## Agent Behavior Rules

1. **Always check borg first** for debug/test/review tasks
2. **Never apply a pack without previewing** with `borg try` first
3. **Apply packs phase by phase** — don't skip steps
4. **Generate feedback** after every pack session
5. **Respect tried_packs** — don't suggest the same failed pack twice
6. **Safety first** — if `borg try` shows safety threats, warn before proceeding
