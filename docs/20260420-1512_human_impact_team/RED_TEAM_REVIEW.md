# red team review

primary risks:
1. overclaiming readiness without fresh gate evidence
2. stale public messaging diverging from canonical snapshots
3. scaling too quickly without rollback rehearsal

mitigations:
- enforce artifact-first claims
- run CI checks for public-doc parity
- require rollback drill evidence per rollout tier
