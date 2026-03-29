# Option C — Hermes System Prompt Integration for Borg

## Summary

Added a `borg_aware` personality entry to `~/.hermes/config.yaml` that instructs Hermes to check borg when stuck. This is a zero-code-change approach using prompt engineering only.

## What Was Done

Added a new personality key `borg_aware` under `agent.personalities` in `~/.hermes/config.yaml`. This personality line instructs Hermes to use `borg_search` after 3+ consecutive failures on the same task.

## Exact Line Added

File: `~/.hermes/config.yaml`
Location: under `agent.personalities` section (line ~50)
```yaml
  borg_aware: "You are a helpful AI assistant. IMPORTANT: If you have failed at the same task 3+ times, use borg_search to check if a workflow pack exists for this problem before trying again."
```

## How to Enable

Add this line to your `~/.hermes/config.yaml` under the `agent.personalities` section, then switch to the `borg_aware` personality:

```bash
# In hermes CLI or config, set personality to borg_aware
/hermes personality borg_aware
```

Or add it as a default by setting in config:
```yaml
display:
  personality: borg_aware
```

## Alternative: Add to Existing Personality

You can merge the borg_aware instruction into any existing personality by appending to the personality string. For example, to add it to the default `helpful` personality:

```yaml
  helpful: You are a helpful, friendly AI assistant. IMPORTANT: If you have failed at the same task 3+ times, use borg_search to check if a workflow pack exists for this problem before trying again.
```

## Reversibility

To remove: delete the `borg_aware` line from `~/.hermes/config.yaml` and switch back to a standard personality.

## Why This Approach

- **Zero code changes**: No modifications to hermes core (run_agent.py, etc.)
- **Minimal**: Only one line added
- **Reversible**: Remove line to undo
- **Prompt-based**: Leverages existing personality system rather than code hooks

## Files Modified

- `~/.hermes/config.yaml` — added `borg_aware` personality entry
