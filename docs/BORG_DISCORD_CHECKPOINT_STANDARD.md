# borg discord checkpoint standard

this standard defines minimum checkpoint structure for discord channel updates during active execution.

required format:

```text
[borg checkpoint]
phase: <investigate|implement|validate|release>
source: discord
confidence: <low|medium|high>
next_checkpoint_minutes: <int>
blocker: <none|explicit blocker>
```

contract file:
- `eval/borg_discord_checkpoint_contract.json`

policy:
- every discord checkpoint must include source=`discord`
- blockers must be explicit and objective
- confidence must match evidence quality
