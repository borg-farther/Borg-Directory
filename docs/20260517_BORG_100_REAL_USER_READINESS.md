# Borg 100 real-user readiness

Generated: 2026-06-03T14:33:34.490309+00:00

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

- PyPI latest/fresh-install package evidence is not green: same-version PyPI upload predates current source revision
- PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green
- served runtime borg_version '3.3.14' != source version '3.3.17'
- served runtime source_version '3.3.15' != source version '3.3.17'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
- public_gate_live_matches_snapshot failed: {'passed': False, 'snapshot': {'source_version': '3.3.17', 'ready_for_controlled_first_10_beta': False, 'ready_for_public_self_serve_launch': False, 'max_recommended_real_users_now': 0, 'blockers': ['PyPI project description/long-description contains stale release-status copy', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', "served runtime borg_version '3.3.14' != source version '3.3.17'", "served runtime source_version '3.3.15' != source version '3.3.17'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'public docs/claim guard found stale install pins or unsupported launch/value claims', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']}, 'live': {'source_version': '3.3.17', 'ready_for_controlled_first_10_beta': False, 'ready_for_public_self_serve_launch': False, 'max_recommended_real_users_now': 0, 'blockers': ['PyPI project description/long-description contains stale release-status copy', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', "served runtime borg_version '3.3.14' != source version '3.3.17'", "served runtime source_version '3.3.15' != source version '3.3.17'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']}}
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Required action to unlock 100 real users

1. Run 10 consented external users through the published PyPI path.
2. Record evidence rows in `eval/first_10_user_scoreboard.json`.
3. Require at least 8 install successes, 6 useful rescue moments, and 0 critical privacy/security incidents.
4. Keep served-runtime, release-governance, self-service ops/watchdog gates green; pause controlled beta if runtime freshness, branch protection, bad-answer/support/privacy intake fails.
5. Rerun `python eval/real_user_rollout_gate.py`; only a green gate authorizes 100 real users.

Machine snapshot: `eval/real_user_rollout_gate_snapshot.json`
