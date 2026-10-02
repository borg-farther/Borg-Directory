# Borg 100 real-user readiness

Generated: 2026-10-02T09:01:57.932848+00:00

100 real-user verdict: **NO-GO**
Max recommended real users now: **0**

## Distinction

Synthetic/logical load tests prove throughput mechanics. They do not prove real external-user readiness.
Real-user rollout requires first-10 external evidence before expanding to 100.

## Current gates

- ready_for_10_controlled_beta: `False`
- release_controls_ready: `False`
- served_runtime_fresh: `False`
- release_governance_ready: `True`
- self_service_ops_ready: `True`
- ops_readiness_watchdog_ready: `True`
- infrastructure_ready_for_100: `False`
- ready_for_100_real_users: `False`

## First-10 evidence

- verified_external_users: `0`
- real_users: `0`
- install_successes: `0`
- useful_rescue_moments: `0`
- critical_privacy_security_failures: `0`
- scoreboard_gate: `BLOCKED`
- scoreboard_reason: `Enrollment is closed: the immutable study artifact is not locked and no verified external-user rows exist.`

## Blockers

- PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version
- PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green
- served runtime borg_version '3.3.18' != source version '3.4.2'
- served runtime source_version '3.3.18' != source version '3.4.2'
- controlled first-10 beta is closed because the frozen protocol or row-level evidence integrity gate is not green
- controlled first-10 beta enrollment is not open or has no remaining slots
- protocol: protocol status does not permit enrollment or completed evidence
- protocol: protocol artifact version is not locked
- protocol: protocol artifact wheel_sha256 is not locked
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, no_match_controls=0/8 (must equal installs=0), false_confident_matches=0/0, harmful_guidance=0/0, critical_incidents=0/0
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Required action to unlock 100 real users

1. Run 10 consented external users through the published PyPI path.
2. Record evidence rows in `eval/first_10_user_scoreboard.json`.
3. Require at least 8 install successes, 6 useful rescue moments, and 0 critical privacy/security incidents.
4. Keep served-runtime, release-governance, self-service ops/watchdog gates green; pause controlled beta if runtime freshness, branch protection, bad-answer/support/privacy intake fails.
5. Rerun `python eval/real_user_rollout_gate.py`; only a green gate authorizes 100 real users.

Machine snapshot: `eval/real_user_rollout_gate_snapshot.json`
