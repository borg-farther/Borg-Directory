# Borg Telegram Communication — Critical Reflection TL;DR

## Executive TL;DR

Current pain is not model quality; it is *communication quality*. Users see tool activity but not value deltas.

We implemented a checkpoint standard that makes each Borg touchpoint legible in six lines:
- phase
- whether Borg was used
- source + confidence
- decision delta
- estimated savings (calls/time/tokens/$ range)
- next action

## 3-Lens Review (adversarial style)

### Lens A — Human clarity
- Problem: updates were verbose and process-heavy.
- Decision: enforce one compact `[borg checkpoint]` block.
- Result: user can parse value in under 10 seconds.

### Lens B — Integrity / anti-hype
- Problem: dollar savings can be over-claimed.
- Decision: transparent formula + low/high range only.
- Result: auditable math and lower trust-risk.

### Lens C — Operational usefulness
- Problem: same update cadence for all tasks causes noise.
- Decision: risk-based mechanism selection:
  - low risk: 1 checkpoint
  - medium risk: 2 checkpoints
  - high risk: 4 checkpoints
- Result: less spam, more signal.

## Optimum mechanism selection

- **Low risk**: final-only checkpoint (minimal overhead).
- **Medium risk**: decision + final checkpoints (balanced).
- **High risk / debugging / incident**: investigate, decide, execute, verify (max transparency).

## What shipped

- Standard doc: `docs/BORG_TELEGRAM_CHECKPOINT_STANDARD.md`
- Machine contract: `eval/borg_telegram_checkpoint_contract.json`
- Rendering + estimation module: `borg/core/checkpoint_comms.py`
- Unit tests: `borg/tests/test_checkpoint_comms.py`
- Contract tests: `eval/tests/test_borg_telegram_checkpoint_contract.py`
- Lint gate: `scripts/borg_checkpoint_lint.py`
- Docs index updates: `README.md`, `docs/README.md`

## Example output

```text
[borg checkpoint]
phase: decide
borg used: yes (source: borg, confidence: high)
what changed: Dropped retry-without-logs path due to known dead-end trace.
estimated save: 3 calls | 75s | 12000 tokens | $0.0360-$0.1800
next step: Run verification tests before any commit.
```

## Recommended rollout

1. Start with medium-risk mode (2 checkpoints) as default.
2. Promote to high-risk mode only on incidents/debug loops.
3. Log checkpoint blocks in session artifacts for value audits.
4. Review weekly: checkpoint usefulness score + false-confidence rate.
