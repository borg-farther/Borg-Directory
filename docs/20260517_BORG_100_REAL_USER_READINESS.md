# Borg 100 real-user readiness

Generated: 2026-05-25T10:25:23.442872+00:00

100 real-user verdict: **NO-GO**
Max recommended real users now: **10**

## Distinction

Synthetic/logical load tests prove throughput mechanics. They do not prove real external-user readiness.
Real-user rollout requires first-10 external evidence before expanding to 100.

## Current gates

- ready_for_10_controlled_beta: `True`
- infrastructure_ready_for_100: `True`
- ready_for_100_real_users: `False`

## First-10 evidence

- verified_external_users: `0`
- real_users: `0`
- install_successes: `0`
- useful_rescue_moments: `0`
- critical_privacy_security_failures: `0`
- scoreboard_gate: `BLOCKED`
- scoreboard_reason: `No verified external user rows exist yet.`

## Blockers

- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Required action to unlock 100 real users

1. Run 10 consented external users through the published PyPI path.
2. Record evidence rows in `eval/first_10_user_scoreboard.json`.
3. Require at least 8 install successes, 6 useful rescue moments, and 0 critical privacy/security incidents.
4. Rerun `python eval/real_user_rollout_gate.py`; only a green gate authorizes 100 real users.

Machine snapshot: `eval/real_user_rollout_gate_snapshot.json`
