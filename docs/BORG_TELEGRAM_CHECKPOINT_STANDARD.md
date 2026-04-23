# Borg Telegram Checkpoint Standard

## Purpose

Make Borg value legible to humans in real time on Telegram, without tool-noise.

This standard answers five user questions quickly:
1. Did Borg actually get used here?
2. Which source provided guidance (`borg` vs `guild`)?
3. What decision changed because of Borg?
4. What was likely saved (time/tokens/$)?
5. What happens next?

## Canonical Message Block

```text
[borg checkpoint]
phase: <investigate|decide|execute|verify>
borg used: <yes|no> (source: <borg|guild|none>, confidence: <high|medium|low>)
what changed: <one-line decision delta>
estimated save: <X calls | Ys | Z tokens | $low-$high>
next step: <single concrete action>
```

## Mechanism Selection (by risk)

- **low-risk task**: 1 checkpoint (final only)
- **medium-risk task**: 2 checkpoints (decision + final)
- **high-risk/debug loop**: 4 checkpoints (investigate, decide, execute, verify)

## Estimation Model (transparent + conservative)

Defaults:
- `avg_seconds_per_tool_call = 25`
- `usd_per_million_tokens_low = 3`
- `usd_per_million_tokens_high = 15`

Calculations:
- `seconds_saved = tool_calls_avoided * avg_seconds_per_tool_call`
- `usd_low = token_savings / 1_000_000 * usd_per_million_tokens_low`
- `usd_high = token_savings / 1_000_000 * usd_per_million_tokens_high`

Always present as a **range**, not a single precise value.

## Provenance and trust rules

- If Borg lookup was used, source must be explicit: `borg` or `guild`.
- If not used, source must be `none` and `borg used: no`.
- Confidence must be one of: `high`, `medium`, `low`.
- Avoid claims not grounded in observed action deltas.

## Implementation

Reference module:
- `borg/core/checkpoint_comms.py`

Tests:
- `borg/tests/test_checkpoint_comms.py`
- `eval/tests/test_borg_telegram_checkpoint_contract.py`

Contract:
- `eval/borg_telegram_checkpoint_contract.json`

Linter:
- `scripts/borg_checkpoint_lint.py`

## Example

```text
[borg checkpoint]
phase: decide
borg used: yes (source: borg, confidence: high)
what changed: Dropped retry-without-logs path due to known dead-end trace.
estimated save: 3 calls | 75s | 12000 tokens | $0.0360-$0.1800
next step: Run verification tests before any commit.
```
