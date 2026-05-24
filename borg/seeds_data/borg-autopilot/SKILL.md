# Borg Agent Priming Helper

## Purpose

This skill teaches an agent when to call Borg after `agent-borg` is installed and the `borg-mcp` server is configured. Borg is failure memory for AI coding agents; this helper does not install Borg, edit agent config, or claim public self-serve readiness by itself.


## Current Borg first-user rule

For an exact error, failing command output, traceback, install/config/deploy failure, or agent transcript, the first MCP call is:

```text
Tool: error_lookup
Args: input="<exact error or failing command output>", show_guidance=false
```

If your host only exposes canonical Borg names, call `borg_rescue(...)`; it returns the same ACTION / STOP / VERIFY packet. Use `borg_observe(...)` for broader task-start guidance when there is not yet concrete failing output. Use `borg_search` / `borg_apply` after rescue/observe when you need a full workflow pack.

## Trigger Conditions

Apply this skill automatically when ANY of these conditions are met:

### 1. Debug / Test / Review Detection (on task start)
When the task description contains keywords like:
- `debug`, `debugging`, `fix`, `crash`, `error`, `exception`, `stack trace`, `segfault`
- `test`, `testing`, `unit test`, `integration test`, `pytest`, `jest`
- `review`, `code review`, `pr review`, `pull request`, `audit`
- `performance`, `profiling`, `benchmark`, `optimize`, `slow`
- `security`, `vulnerability`, `CVE`, `exploit`

**Action:** If exact failing output is available, call `error_lookup(input="<exact error>", show_guidance=false)` first. Otherwise call `borg_observe(task="<task description>", context="<tech stack>")` and include the result in your reasoning. If a pack is suggested, mention it proactively to the user.

### 2. Failure Detection (after 2+ consecutive failures)
When the agent has failed 2 or more consecutive times on the same task:
- Call `borg_suggest(context=recent_conversation, failure_count=N)`
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
# Concrete error rescue first
borg rescue "<exact error or failing command output>"

# Preview a pack before applying
borg try <uri>

# Start applying a pack
borg apply <pack_name> --task "<task description>"

# Get session feedback
borg feedback <session_id>

# Search for relevant packs
borg search <query>
```

## MCP Tools (How to Actually Call Borg from Hermes)

The skill uses MCP tools — NOT Python imports. Here's what you call:

### When you detect a debug/test/failure task at task start:

**Step 1: For concrete failures, call `error_lookup` first; otherwise call `borg_observe`**
```
Tool: error_lookup
Args: input="<exact error or failing command output>", show_guidance=false

Tool: borg_observe
Args: task="<what you're about to work on>", context="<optional environment context>"
```
- If `error_lookup` returns a confident rescue packet → follow ACTION / avoid STOP / rerun VERIFY
- If using `borg_observe`, follow any returned phases or explicit no-match guidance
- If no concrete guidance is available → proceed to Step 2

**Step 2: Call `borg_search` for simple keyword search**
```
Tool: borg_search
Args: query="debug"  (use simple keywords: "debug", "test", "review", "deploy")
```
- Search is text-based: short keywords work better than long sentences
- Look for packs with tier != "none" and high confidence

**Step 3: If you see 2+ consecutive failures, call `borg_suggest`**
```
Tool: borg_suggest
Args: context="<recent conversation>", failure_count=<number>
```
- Returns pack suggestions formatted as actionable text

### Example tool calls for this scenario:

User says: "I have a TypeError in my auth module, tests are failing"

```text
Tool: error_lookup
Args: input="TypeError in auth module with failing pytest output", show_guidance=false

Tool: borg_observe
Args: task="fix TypeError in auth module", context="Python, pytest"

Tool: borg_search
Args: query="debug"

Tool: borg_suggest
Args: context="I have a TypeError in my auth module, tests are failing", failure_count=2
```

### Quick reference — available MCP tools:

| Tool | When to use | Key args |
|------|-------------|----------|
| `error_lookup` | Concrete failure rescue first | `input` |
| `borg_rescue` | Canonical ACTION / STOP / VERIFY rescue packet | `input` |
| `borg_observe` | Task start (proactive) | `task`, `context` |
| `borg_search` | Any time you want to find packs | `query` (simple keywords) |
| `borg_suggest` | After 2+ failures | `context`, `failure_count` |
| `borg_try` | Preview a pack before using | `uri` |
| `borg_pull` | Download a pack locally | `uri` |
| `borg_apply` | Execute a pack (start/checkpoint/complete) | `action`, `pack_name`, `task` |
| `borg_feedback` | After pack completes | `session_id` |

## Agent Behavior Rules

1. **Always check Borg first** for debug/test/review tasks — concrete failures use `error_lookup`, broader tasks use `borg_observe`
2. **Never apply a pack without previewing** with `borg try` first
3. **Apply packs phase by phase** — don't skip steps
4. **Generate feedback** after every pack session
5. **Respect tried_packs** — don't suggest the same failed pack twice
6. **Safety first** — if `borg try` shows safety threats, warn the user before proceeding

## Integration Points

- **Hermes MCP:** The borg MCP server must be configured in `~/.hermes/config.yaml`
- **MCP server:** Exposes `error_lookup`, `borg_rescue`, `borg_observe`, `borg_search`, `borg_suggest`, and pack-application tools
- **Agent priming only:** This skill is useful after Borg has been installed and connected

## Example Conversation

User: "my auth tests are failing after I added JWT"
Agent: [detects "test" + "failing" → calls error_lookup or borg_observe]
→ "I see you're dealing with test failures. Borg suggests 'systematic-debugging' (debugging workflow) — try: borg://hermes/systematic-debugging"

User: "why is my server crashing on startup"
Agent: [detects "crash" → calls error_lookup or borg_observe]
→ "This looks like a startup crash. Borg suggests 'systematic-debugging' (Debugging workflow) — try: borg://hermes/systematic-debugging"
