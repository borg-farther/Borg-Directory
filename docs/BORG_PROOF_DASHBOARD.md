# Borg Proof Dashboard

Generated: `2026-06-03T12:42:47Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `051443233b35f816b8d28b35a544714adda77d7c+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until these failed gates are green: PyPI latest project description/long-description copy; served-runtime freshness |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until these failed gates are green: PyPI latest project description/long-description copy; served-runtime freshness; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package/release-control/ops evidence is green.

## Metrics with provenance and honesty labels

| Metric | Value | Honesty label | Provenance |
| --- | --- | --- | --- |
| verified_external_users | 0 | ROW_DERIVED_EXTERNAL_USERS | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| measured_savings | `{"counterfactual_basis_counts": {}, "dead_ends_avoided_confirmed": 0, "negative_minutes_cost": 0.0, "negative_tokens_cost": 0, "net_minutes_saved": 0.0, "net_tokens_saved": 0, "positive_minutes_saved": 0.0, "positive_tokens_saved": 0, "rows_with_measured_value": 0}` | ROW_DERIVED_EXTERNAL_USER_SAVINGS | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| active_contributors_consumers | UNKNOWN | MISSING_BORG_ANALYTICS_ARTIFACT | No Borg analytics export artifact was found under eval/ or docs/. |
| packs | 11 | REPO_FILE_COUNT | borg/seeds_data/packs/*.yaml |
| first_user_release_gate | PASS | LOCAL_ARTIFACT | eval/first_user_release_gate_snapshot.json |
| uat_scoreboard_synthetic_load | PASS | LOCAL_ARTIFACT_LOGICAL_USERS | eval/uat_scoreboard_snapshot.json |
| gate_run_synthetic_load | PASS | LOCAL_ARTIFACT_LOGICAL_USERS | eval/gate_run_snapshot.json |
| real_user_100_rollout_gate | FAIL | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| max_recommended_real_users_now | 0 | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| public_self_serve_launch_gate | FAIL | PUBLIC_LAUNCH_GATE | eval/public_self_serve_launch_gate_snapshot.json |
| cold_start_trust_hardening_gate | PASS | FIRST_ANSWER_TRUST_GATE | eval/cold_start_trust_gate_snapshot.json |
| served_runtime_freshness_gate | FAIL | SERVED_RUNTIME_FINGERPRINT_GATE | eval/served_runtime_fingerprint_snapshot.json |
| release_governance_gate | PASS | RELEASE_GOVERNANCE_BRANCH_PROTECTION_GATE | eval/release_governance_snapshot.json |
| release_controls_gate | FAIL | SERVED_RUNTIME_PLUS_RELEASE_GOVERNANCE | eval/real_user_rollout_gate_snapshot.json |
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| pypi_package_current_gate | FAIL | PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE | eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.16 runtime=3.3.16 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | FAIL | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7294940995052457, "p99_ms": 0.8128765365108848, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:46:33.549678+00:00", "total_requests": 48934, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7360600866377354, "p99_ms": 0.9644317068159578, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:47:03.681996+00:00", "total_requests": 48942, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7110125618055462, "p99_ms": 0.773976217024028, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:47:33.846766+00:00", "total_requests": 49978, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 1a46e0d720645a0553914654a7ad170b404d586175f63a219dc1bd079e6b1c21 | 2026-06-02T10:01:26Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 91609d7d1c36b321f4c08bd4ed9ee9d0c92346b843cbe3c61f1dda3d4f598406 | 2026-06-02T21:47:35.869382+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 64506c28195ec35a14e633335085ea262e96eb9ea5aba75aec2d2303314be615 | 2026-06-02T21:47:35.821086+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 1eafa2bd93df3a7b915c3bf0750c93a90080a749a139b8467f540eeb98e64c53 | 2026-06-03T12:42:44.008716+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 963d34aa0eca072fce5fba1d5b10b4edaa6e3cc4047b8b49f64dead15a37c03b | 2026-06-03T12:42:42.453374+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI project description/long-description contains stale release-status copy', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | badda3b864f20009a4cc59a5e9209cd0ed76df95fbf3d9b9994b8f8e57064222 | 2026-06-03T12:42:31.172319+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | d9c59714efb0707896de59e721308e61f806c68c7dbf3d97aa178cd62448ee0f | 2026-06-03T12:42:47.243575+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | edf7f4cce3c33ef05045f207c954f0e46e150c0d54cba7abd8a63e06686b73a1 | 2026-06-03T12:42:47.060698+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | 04549265698b0187af9cc086ceb67afacdc3b6723a42c72448b58f585d7d255e | 2026-06-03T12:42:34.130960+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | 3bbab034f809592b62c4503de8babb335797aaa95b4e4be196d03345624e816e | 2026-06-03T12:42:07Z | PyPI fresh-install canary success=True; version=3.3.16 |
| eval/load_10_snapshot.json | True | ab6c0e1e52b1527fe988b0d84f01e243d3d8c30919dc41fc3559dd0257a2e4f7 | 2026-06-02T21:46:33.549678+00:00 | logical load 10: passed=True; total_requests=48934; success_rate=1.0; p95_ms=0.7294940995052457; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 6a0a345a71bbb3f3a457da8eceffc10fcc377d0aeb4553f1005c3cbc22a07b7a | 2026-06-02T21:47:03.681996+00:00 | logical load 100: passed=True; total_requests=48942; success_rate=1.0; p95_ms=0.7360600866377354; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | efd3c036fb2cfe1f6aa296f7f995070f6d4b569d4242ba1ebe416c86c92e4928 | 2026-06-02T21:47:33.846766+00:00 | logical load 1000: passed=True; total_requests=49978; success_rate=1.0; p95_ms=0.7110125618055462; model=asyncio_logical_users |
| pyproject.toml | True | 87a7b7c43e63c0a0d46f0e69b01c1dd5ccd4308ba56304d1f6da53b80c6f64eb | 2026-06-02T13:28:06Z | package version=3.3.16; scripts declared in project metadata |
| borg/__init__.py | True | c5b0048872dafb21a4f6dc1ee5c7e7c6c471f4c203acbcc06cdb9f139f3c2191 | 2026-06-02T13:28:06Z | runtime __version__=3.3.16; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI package gate is not green for the current source revision yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is not green yet.<br>Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

## First-10-user scoreboard template

| # | user id/pseudonym | install success | time to first rescue | rescue useful yes/no | MCP setup success | blocker | outcome recorded | baseline minutes without Borg | actual minutes with Borg | net minutes saved | baseline tokens without Borg | actual tokens with Borg | net tokens saved | savings counterfactual basis | dead end avoided confirmed | user confirmed value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

## Anti-hype section

Simulated/logical users are not real users. Internal sessions, tool calls, local tests, and maintainer runs are not adoption. Real verified external users are 0 unless a hard evidence artifact proves otherwise; no such artifact was found by this build.

## Next action queue before controlled first-10 beta testers

| # | Action |
| --- | --- |
| 1 | Do not invite controlled first-10 testers yet: `agent-borg==3.3.16` fresh-install/runtime canary passes, but the PyPI project description/long-description is stale; publish a new immutable version after `3.3.16` before using public package metadata as current proof. Served-runtime, release-governance, ops, and watchdog gates must also pass. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
