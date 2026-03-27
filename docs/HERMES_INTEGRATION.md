# Hermes + Guild v2 Integration

This document describes how to wire Guild v2's `agent_hook` auto-suggest functions into the Hermes agent loop.

---

## What exists vs. what was missing

| Component | Location | Status |
|---|---|---|
| Guild v2 `agent_hook.py` (the functions) | `guild-v2/guild/integrations/agent_hook.py` | Exists but **never called** |
| Hermes `tools/guild_autosuggest.py` (tool + `check_for_suggestion`) | `hermes-agent/tools/guild_autosuggest.py` | Exists; used by `run_agent.py` |
| Hermes `_maybe_inject_guild_suggestion()` in `run_agent.py` | `hermes-agent/run_agent.py:5352` | Calls `tools.guild_autosuggest.check_for_suggestion` |
| Hermes `_consecutive_tool_errors` counter | `run_agent.py:917, 5019, 5255, 5634` | Incremented on tool errors; reset at task start |

The gap: Hermes has its own autosuggest system that calls `tools/guild_autosuggest.check_for_suggestion`, but that function uses Hermes-local search logic. The Guild v2 functions at `guild/integrations/agent_hook.py` (which call `guild.core.search`) were never wired into anything.

---

## What the plugin does

The `hermes-plugin/` directory is a Hermes plugin that bridges this gap:

1. **Patches `tools.guild_autosuggest.check_for_suggestion`** to delegate to `guild.integrations.agent_hook.guild_on_failure`. This means all existing autosuggest callers (including `run_agent.py`'s `_maybe_inject_guild_suggestion`) automatically get Guild v2 results — no changes to `run_agent.py` required.

2. **Registers `guild_v2_autosuggest` as a callable tool** (toolset: `skills`), letting the LLM directly invoke `guild_on_failure` or `guild_on_task_start`.

3. **Registers lifecycle hooks** `on_consecutive_failure` and `on_task_start` (informational logging only, since `run_agent.py` doesn't yet invoke these via `invoke_hook`).

---

## Installation

### Option 1: Symlink (recommended for development)

```bash
ln -s /root/hermes-workspace/guild-v2/hermes-plugin ~/.hermes/plugins/guild-v2
```

Then restart the Hermes agent.

### Option 2: pip install via entry-points

If guild-v2 is installed as a package, it registers the plugin via the `hermes_agent.plugins` entry-point group. No manual symlink needed.

---

## Configuration

In `~/.hermes/config.yaml`:

```yaml
agent:
  guild:
    autosuggest_enabled: true       # master switch (default: true)
    error_threshold: 3              # consecutive failures before triggering
    proactive_suggest: true        # also call guild_on_task_start on new tasks
    v2_bridge_enabled: true        # use guild-v2 engine (default: true)
```

Environment variable override:

```bash
export HERMES_GUILD_V2_ENABLED=false  # disable the plugin entirely without removing it
```

---

## How the integration works

### 1. Consecutive failure detection (existing Hermes infrastructure)

`run_agent.py` tracks `_consecutive_tool_errors`:

```
Line 5019:  self._consecutive_tool_errors += 1   # on batch tool error
Line 5021:  self._consecutive_tool_errors = 0    # on batch success
Line 5255:  self._consecutive_tool_errors += 1   # on individual tool error
Line 5257:  self._consecutive_tool_errors = 0    # on individual tool success
Line 5634:  self._consecutive_tool_errors = 0    # reset at task/turn start
```

### 2. Suggestion injection (existing)

`_maybe_inject_guild_suggestion(messages)` at line 5352 is called after tool execution (line 7013):

```python
if self._consecutive_tool_errors >= self._guild_autosuggest_threshold:
    # builds context from recent messages
    suggestion_json = check_for_suggestion(conversation_context=..., failure_count=..., tried_packs=...)
    # injects as system message: "[Guild AutoSuggest] ..."
```

With the plugin enabled, `check_for_suggestion` now delegates to `guild.integrations.agent_hook.guild_on_failure`.

### 3. Task start hooks (future-use)

The plugin registers `on_task_start` and `on_consecutive_failure` hooks with the Hermes plugin system. Currently `run_agent.py` does not invoke these via `invoke_hook` — they are registered for forward compatibility and log suggestions for observability.

---

## Key files

| File | Purpose |
|---|---|
| `hermes-plugin/plugin.yaml` | Hermes plugin manifest |
| `hermes-plugin/__init__.py` | Plugin entry point; patches autosuggest + registers tool + registers hooks |
| `guild-v2/guild/integrations/agent_hook.py` | Guild v2 auto-suggest functions (`guild_on_failure`, `guild_on_task_start`) |
| `guild-v2/guild/core/search.py` | Guild v2 search engine (`guild_search`, `check_for_suggestion`, `classify_task`) |
| `hermes-agent/run_agent.py:5352` | Existing `_maybe_inject_guild_suggestion` — **unchanged** |
| `hermes-agent/tools/guild_autosuggest.py` | Existing Hermes autosuggest — **patched by plugin** |

---

## Making `run_agent.py` call lifecycle hooks directly (optional)

If you want `on_task_start` and `on_consecutive_failure` to be actively invoked rather than just logged, add these calls to `run_agent.py`:

```python
# At run_conversation start (after line 5636), add:
from hermes_cli.plugins import invoke_hook
invoke_hook("on_task_start", task_description=user_message)

# At _maybe_inject_guild_suggestion call site (line 7013), add before/after:
invoke_hook("on_consecutive_failure",
            task_description=user_message,
            error_context=recent_context,
            failure_count=self._consecutive_tool_errors)
```

This is **optional** — the plugin works without these changes because it patches `check_for_suggestion` directly.

---

## Opt-in safety

- `HERMES_GUILD_V2_ENABLED=false` environment variable disables the entire plugin before it does anything
- `v2_bridge_enabled: false` in config.yaml also makes the plugin a no-op
- All operations are wrapped in try/except; failures log warnings but never crash the agent
- No modifications to `run_agent.py` — fully additive change

---

## Troubleshooting

**Plugin not loading:**
```bash
ls -la ~/.hermes/plugins/       # should show guild-v2 symlink
hermes plugins list             # should show guild-autosuggest
```

**No suggestions appearing:**
- Check `HERMES_GUILD_V2_ENABLED=true` and `v2_bridge_enabled: true` in config
- Check that `guild-v2` Python package is importable: `python -c "from guild.integrations import agent_hook; print('ok')"`
- Check logs for `Guild v2 plugin loaded successfully`
- Verify `guild` index exists at `~/.hermes/guild-search/` or remote endpoint is reachable
