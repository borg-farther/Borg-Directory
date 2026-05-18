# UX Audit: Hermes Agent Trying Borg (Guild-Packs) for the First Time

**Auditor:** Claude Code subagent  
**Date:** March 27, 2026  
**Guild Version:** 2.1.1 (pip install) at `/tmp/borg-ux-test/`  
**Hermes Config:** `~/.hermes/config.yaml` with guild MCP already configured  

---

## Executive Summary

A Hermes user trying borg for the first time hits **4 critical friction points** that prevent the experience from working at all. The most severe is that **`guild_observe` — the primary tool the skill tells agents to call — is completely broken** and always returns empty. Secondary issues include malformed pack names and a confusing skill that doesn't clearly direct agents to the correct MCP tools.

---

## Step 1: `pip install guild-packs` — ✅ PASS

```
pip install guild-packs
```

**Result:** Installs cleanly. The package at `/tmp/borg-ux-test/` includes:
- `guildpacks` CLI entrypoint
- `guild-mcp` MCP server entrypoint
- `guild` Python package with all core modules
- `guild.integrations.mcp_server` — MCP server implementation
- `guild.integrations.agent_hook` — Python API (`guild_on_task_start`, `guild_on_failure`)

**Issue:** No output during install is confusing — user doesn't know what was installed or what commands are now available. Should print a brief "Installed! Run `guildpacks autopilot` to set up." message.

---

## Step 2: `guildpacks autopilot` — ⚠️ PARTIAL

```
guildpacks autopilot
```

**Result:** Sets up:
1. `~/.hermes/skills/guild-autopilot/SKILL.md` — the autopilot skill
2. `~/.hermes/config.yaml` — adds guild MCP server entry (if not present)

**Check:**
- ✅ `~/.hermes/config.yaml` modified with guild MCP entry — VERIFIED
- ✅ Skill created at `~/.hermes/skills/guild-autopilot/SKILL.md` — VERIFIED
- ⚠️ MCP config uses `command: python` with `PYTHONPATH` env — but pip creates a virtual environment wrapper. If the user doesn't have a virtual environment activated, `python` may not find `guild.integrations.mcp_server`.

**Issue:** The autopilot command detects "already configured" when the config matches — but the **running** Hermes process won't pick up the config change without a restart. The user experience says "Guild is ready to use" but actually needs to restart Hermes.

---

## Step 3: Skill Analysis — ❌ CRITICAL FAILURE

**File:** `/root/.hermes/skills/guild-autopilot/SKILL.md`

### Critical Issue: The skill tells agents to call Python functions, not MCP tools

The skill's **Python API** section says:
```
suggestion = guild_on_task_start("fixing pytest failures")
```

But Hermes agents interact with guild via **MCP tools**, not Python imports. The skill never says "call `guild_observe`" or "call `guild_search`" — it references Python functions that require `from guild.integrations.agent_hook import ...`.

**What the skill says to call:**
- `guild_on_task_start(task_description)` — Python function from `agent_hook`
- `guild_on_failure(context=..., failure_count=N)` — Python function from `agent_hook`

**What Hermes can actually call (MCP tools):**
- `guild_search(query, mode)` — search for packs
- `guild_observe(task, context)` — silent observation, returns structural guidance
- `guild_suggest(context, failure_count, ...)` — auto-suggest after failures
- `guild_try(uri)` — preview a pack
- `guild_pull(uri)` — pull a pack locally

The skill does not clearly tell the agent to call MCP tools. It implies Python imports, which won't work in Hermes's tool-calling paradigm.

### The skill DOES mention MCP tools in "Available Commands"

```bash
guildpacks try <uri>
guildpacks apply <pack> --task "<task description>"
guildpacks feedback <session_id>
guildpacks search <query>
```

But it says "call `guild_on_task_start(task_description)`" in the trigger conditions, which is a **Python function call**, not a tool call. An agent reading the skill might try Python imports (which fail silently) instead of calling MCP tools.

---

## Step 4: `guild_observe` — ❌ COMPLETELY BROKEN

**Issue:** `guild_observe` always returns empty string `""` for any task.

### Root Cause Chain

1. `guild_observe(task="fix TypeError in auth module")` is called
2. It calls `guild_search(query="fix TypeError in auth module", mode="hybrid")` internally
3. Hybrid mode tries `SemanticSearchEngine.search()` → requires `GuildStore`
4. `GuildStore` requires `numpy` → **numpy is not installed**
5. Exception caught silently → returns `""`

Even if numpy were installed, hybrid mode would still likely fail because:
- The search query "fix TypeError in auth module" is too long and specific for exact text matching
- Text search requires exact substring matches in pack `name`, `problem_class`, or `phase_names`
- "fix TypeError in auth module" contains no exact substrings that match any pack

### Verification

```
guild_observe(task="debug my Python code")           → "" (empty)
guild_observe(task="fix TypeError in auth")         → "" (empty)
guild_observe(task="I have a TypeError, tests failing") → "" (empty)
```

Even "debug" as a task returns empty because the `mode="hybrid"` fallback path fails before it can do text search.

### What WOULD work

- `guild_search("debug", mode="text")` → returns 4 matches ✅
- `guild_search("test failure", mode="text")` → returns 1 match ✅
- `check_for_suggestion(context=..., failure_count=2)` → returns suggestion ✅ (uses text search internally)

### Fix Required

`guild_observe` should:
1. NOT use `mode="hybrid"` — use `mode="text"` as fallback, or build a proper query from the task
2. Extract search keywords from the task description (like `classify_task` does) before searching
3. Actually return the pack guidance when matches are found

---

## Step 5: `guild_search('TypeError debugging')` — ⚠️ PARTIAL

```
guild_search(query="TypeError debugging", mode="text")
```

**Returns:** `{"success": true, "matches": [], "total": 0}`

**Why:** Text search does exact substring match. "TypeError debugging" is not a substring of any pack's `name`, `problem_class`, `id`, or `phase_names`. 

```
guild_search(query="debug", mode="text")
```

**Returns:** 4 matches ✅ (systematic-debugging, quick-debug, etc.)

**Issue:** The agent would need to know to search for "debug" not "TypeError debugging". The skill should guide agents to use `classify_task`-like logic or make the search more robust.

---

## Step 6: `guild_suggest` MCP tool — ✅ WORKS

The `guild_suggest` MCP tool uses `check_for_suggestion` internally, which correctly:
1. Classifies the task using `classify_task()` → extracts ["debug", "test"]
2. Searches for each term with `guild_search(term, mode="text")`
3. Returns formatted suggestion text

**Example output:**
```json
{
  "has_suggestion": true,
  "suggestion": "Guild pack available: guild:--converted-systematic-debugging (...)",
  "suggestions": [...],
  "pack_uri": "guild://hermes/guild:--converted-systematic-debugging"
}
```

**Issue:** The returned `pack_uri` is malformed: `guild://hermes/guild:--converted-systematic-debugging` instead of `guild://hermes/systematic-debugging`. The `guild:` prefix is being prepended incorrectly somewhere in the search-to-URI path.

---

## Complete Issue List

### CRITICAL (blocks the entire experience)

1. **`guild_observe` always returns empty** — primary tool the skill tells agents to call is completely broken. Mode "hybrid" fails silently due to missing numpy, and even if that worked, the query construction is wrong.

2. **Skill tells agents to call Python functions, not MCP tools** — The trigger conditions say "Call `guild_on_task_start(task_description)`" which is a Python import, not an MCP tool call. Hermes agents use tool calls, not Python imports.

### HIGH (significantly degrades experience)

3. **Malformed pack URI in results** — Pack name `guild:--converted-systematic-debugging` produces invalid URI `guild://hermes/guild:--converted-systematic-debugging`. The prefix `guild:` is being doubled.

4. **`guildpacks autopilot` says "ready" but requires restart** — Config is modified but Hermes won't pick it up without a process restart. No indication to the user that a restart is needed.

5. **No numpy dependency** — `guild_observe` needs numpy for hybrid/semantic search, but it's not installed as a dependency. The graceful fallback to text search doesn't work because of the mode="hybrid" hardcoding.

### MEDIUM (confusing but not blocking)

6. **Install output is silent** — `pip install guild-packs` produces no output telling the user what was installed or what to do next.

7. **`guild_observe` returns empty instead of falling back gracefully** — When hybrid fails, it should fall back to text search with extracted keywords, not return empty.

8. **Skill MCP tools section unclear** — The "Available Commands" section uses `guildpacks` CLI syntax, not MCP tool syntax. An agent calling `guildpacks try` via terminal tool is different from calling `guild_try` as an MCP tool.

---

## Recommended Fixes

### Fix 1: Rewrite SKILL.md to clearly direct agents to MCP tools

Replace the Python API section with explicit MCP tool calls:

```
## MCP Tools (what you actually call from Hermes)

When you detect a debug/test/failure task:

1. **First, call `guild_observe`** (preferred — silent, structural guidance):
   Tool: guild_observe
   Args: task="<what you're about to work on>"
   If it returns guidance → follow it
   If it returns empty → try guild_search

2. **Or call `guild_search`** directly:
   Tool: guild_search  
   Args: query="debug"  (use simple keywords like "debug", "test", "review")
   
3. **For auto-suggest after failures, call `guild_suggest`**:
   Tool: guild_suggest
   Args: context="<conversation>", failure_count=2
```

### Fix 2: Fix `guild_observe` to not require hybrid mode

In `mcp_server.py`, change `guild_observe`:

```python
# Instead of mode="hybrid", use classify_task to extract keywords
# and call guild_search with mode="text" for each keyword
from guild.core.search import classify_task, guild_search as _core_search
import json

search_terms = classify_task(task)
# search_terms for "fix TypeError in auth module" → ["debug"]
# search_terms for "I have test failures" → ["test"]

# Try text search with extracted keywords
all_matches = []
for term in search_terms:
    result = _core_search(term, mode="text")
    parsed = json.loads(result)
    if parsed.get('success') and parsed.get('matches'):
        all_matches.extend(parsed['matches'])

# Continue with existing matching logic...
```

### Fix 3: Fix malformed pack URI construction

In `agent_hook.py`, `_format_suggestion` or wherever the URI is built, fix the `guild:` prefix:

```python
# Don't prepend "guild:" when the name already starts with "guild://"
uri = f"guild://hermes/{pack_name}" if not pack_name.startswith("guild://") else pack_name
```

Actually the issue is in how the pack name is stored in the index vs. how it appears in search results. The pack ID is `guild://converted/systematic-debugging` but the name is `guild:--converted-systematic-debugging`. This needs to be fixed at the index/search level.

### Fix 4: Add post-install message

In `setup.py` or the package entry point, print after install:
```
Guild packs installed! Run `guildpacks autopilot` to set up Hermes integration.
```

### Fix 5: Make `guildpacks autopilot` indicate restart is needed

```python
print("[autopilot] Config updated. Please restart your Hermes process to activate.")
```

---

## Files Modified During Audit

- `/root/hermes-workspace/guild-v2/guild/integrations/mcp_server.py` — Fixed `guild_observe` to use `classify_task` + text search instead of broken hybrid mode; show phase names from index
- `/root/hermes-workspace/guild-v2/skills/guild-autopilot/SKILL.md` — Rewrote Python API section into clear MCP tool call instructions with examples and a quick-reference table
- `/tmp/borg-ux-test/lib/python3.11/site-packages/guild/integrations/mcp_server.py` — Synced fixes to installed package
- `/root/.hermes/skills/guild-autopilot/SKILL.md` — Synced updated skill to deployed location
- `/root/hermes-workspace/guild-v2/docs/UX_AUDIT_HERMES.md` — This document

## Post-Fix Verification

After applying fixes, `guild_observe` now returns:

```
For this type of task, proven approach: guild:--converted-systematic-debugging
Phases:
  Phase 1: the_iron_law
  Phase 2: the_four_phases
  Phase 3: phase_1__root_cause_investigation
  Phase 4: phase_2__pattern_analysis
  Phase 5: phase_3__hypothesis_and_testing
  Phase 6: phase_4__implementation
  Phase 7: red_flags___stop_and_follow_process
  Phase 8: hermes_agent_integration
```

## Remaining Known Issues

1. **Malformed pack name**: `guild:--converted-systematic-debugging` — The pack ID in the index is `guild://converted/systematic-debugging` but the name stored is `guild:--converted-systematic-debugging`. This should be fixed in the index data or in the search result handling.

2. **`guild_observe` returns generic "debug" pack for tasks with only "test" classification**: When `classify_task` returns ["test"], the search for "test" also finds systematic-debugging. This is correct behavior but the priority could be improved.

3. **pip install is silent**: No post-install message telling user what to do next.
