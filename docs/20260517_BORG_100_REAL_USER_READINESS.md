# Borg 100 real-user readiness

Generated: 2026-06-03T20:33:14.420374+00:00

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
- ops_readiness_watchdog_ready: `False`
- infrastructure_ready_for_100: `False`
- ready_for_100_real_users: `False`

## First-10 evidence

- verified_external_users: `0`
- real_users: `0`
- install_successes: `0`
- useful_rescue_moments: `0`
- critical_privacy_security_failures: `0`
- scoreboard_gate: `BLOCKED`
- scoreboard_reason: `First-10 external-user evidence thresholds have not passed.`

## Blockers

- served runtime borg_version '3.3.14' != source version '3.3.18'
- served runtime source_version '3.3.15' != source version '3.3.18'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
- source_revision_honesty failed: {'passed': False, 'head': 'b035825711211a98693171d7963af3d26ccb859b', 'git_clean': False, 'source_revision': 'fb8192a173bc802d8d4411b2e276ebf40d4a536a+dirty', 'policy': 'Committed dashboards may be generated from a dirty tree and must mark +dirty; clean-tree status endpoints should match HEAD or a dirty ancestor used to generate committed proof artifacts.'}
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Required action to unlock 100 real users

1. Run 10 consented external users through the published PyPI path.
2. Record evidence rows in `eval/first_10_user_scoreboard.json`.
3. Require at least 8 install successes, 6 useful rescue moments, and 0 critical privacy/security incidents.
4. Keep served-runtime, release-governance, self-service ops/watchdog gates green; pause controlled beta if runtime freshness, branch protection, bad-answer/support/privacy intake fails.
5. Rerun `python eval/real_user_rollout_gate.py`; only a green gate authorizes 100 real users.

Machine snapshot: `eval/real_user_rollout_gate_snapshot.json`
