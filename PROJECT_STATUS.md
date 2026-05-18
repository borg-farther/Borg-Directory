# Borg Project Status

Updated: `2026-05-18T07:46:07.702390+00:00`

## Synthetic/load rollout decision

These flags are for logical load gates only. They do not authorize 100 real external users.

- Ready for 10 logical load users: GO
- Ready for 100 logical load users: GO
- Ready for 1000 logical load users: GO
- Synthetic/load overall: GO

Real external-user rollout is gated separately by `eval/real_user_rollout_gate_snapshot.json`.

## Hard gates

- version_consistency: PASS
- first_user_surface: PASS
- security_surface: PASS
- load_10: PASS
- load_100: PASS
- load_1000: PASS

## Load gates

- 10 logical users: passed=True total_requests=59794 p95_ms=0.6281427631620318 p99_ms=0.8716626581735909
- 100 logical users: passed=True total_requests=59981 p95_ms=0.6004410097375512 p99_ms=0.6370391696691513
- 1000 logical users: passed=True total_requests=59947 p95_ms=0.6051470059901476 p99_ms=0.7191141927614809

## Real external-user rollout decision

- Ready for 10 controlled real users: GO
- Ready for 100 real external users: NO-GO
- Max recommended real users now: 10
- Source: `eval/real_user_rollout_gate_snapshot.json`

## Real-user blockers

- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

Canonical machine snapshot: `eval/uat_scoreboard_snapshot.json`
