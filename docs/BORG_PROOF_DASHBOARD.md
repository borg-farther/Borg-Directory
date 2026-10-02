# Borg Proof Dashboard

Generated: `2026-10-02T09:02:00Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `8038f108f0d8be526406cab2cf16bfb3bcd364e4+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until these failed gates are green: PyPI latest/fresh-install/stdio MCP package path; served-runtime freshness |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and row-derived first-10 external evidence passes. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until these failed gates are green: PyPI latest/fresh-install/stdio MCP package path; served-runtime freshness; Do not present as unattended public launch ready.; Keep tester-intake forms prepared, but blocked until package/release-control/ops evidence is green.

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
| pypi_fresh_install_canary | FAIL | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| pypi_package_current_gate | FAIL | PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE | eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.4.2 runtime=3.4.2 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | FAIL | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 1.317520067095756, "p99_ms": 1.9241905771195884, "passed": true, "success_rate": 1.0, "timestamp": "2026-09-18T16:29:20.981008+00:00", "total_requests": 29732, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 1.1239005252718925, "p99_ms": 1.1847499758005142, "passed": true, "success_rate": 1.0, "timestamp": "2026-09-18T16:29:51.118895+00:00", "total_requests": 31031, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 1.683654636144638, "p99_ms": 5.0628274679184235, "passed": true, "success_rate": 1.0, "timestamp": "2026-09-18T16:30:21.293987+00:00", "total_requests": 25845, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 5449cc2248640442b3ccf3d629ed752e9f4eb4ab28cd07165f1c22ec394f9369 | 2026-10-02T08:40:48Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | fc5d65b0e7e4ecba483f4c21a4024dee56fa244dcd4fdb3086a7460526ca041a | 2026-09-18T16:30:23.291206+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 36e8d89bf24625da1a647409bd88ab37ae9eda21c0aea0dcc56a7b4c41a101d1 | 2026-09-18T16:30:23.234842+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | e05874bcb1ac2b04af111524caaa2d4fdbb7010b9eee0d331928ba769e55c5d2 | 2026-10-02T09:01:57.932848+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', "served runtime borg_version '3.3.18' != source version '3.4.2'", "served runtime source_version '3.3.18' != source version '3.4.2'", 'controlled first-10 beta is closed because the frozen protocol or row-level evidence integrity gate is not green', 'controlled first-10 beta enrollment is not open or has no remaining slots', 'protocol: protocol status does not permit enrollment or completed evidence', 'protocol: protocol artifact version is not locked', 'protocol: protocol artifact wheel_sha256 is not locked', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, no_match_controls=0/8 (must equal installs=0), false_confident_matches=0/0, harmful_guidance=0/0, critical_incidents=0/0', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 349fe2c0b07cc2bb05f202e02ec092d47a8586acc0b1cbdb164f9b4cdd75f2ba | 2026-10-01T16:05:35Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 51a506170b687f5f8c56ea54a54b9075a14ab3ddf43b642ed2248b51726b3394 | 2026-10-02T09:01:56.826907+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest is agent-borg==3.4.1; expected agent-borg==3.4.2', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', "served runtime borg_version '3.3.18' != source version '3.4.2'", "served runtime source_version '3.3.18' != source version '3.4.2'", 'protocol: protocol status does not permit enrollment or completed evidence', 'protocol: protocol artifact version is not locked', 'protocol: protocol artifact wheel_sha256 is not locked', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, no_match_controls=0/8 (must equal installs=0), false_confident_matches=0/0, harmful_guidance=0/0, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | 734ca8fc7d15399180ee55906e3fe7aac37d3db66d02bb464c02012adeee4da7 | 2026-10-02T08:59:33.546639+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | cabdfa6fa651c5f890c481c040820ce846f17a90a2dbd929a0e9ad1a5f0a32ac | 2026-10-02T09:02:00.738392+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | f434e94aaaf59a3ac08c26378ef716769651a7f4a2366707a9ac5ab292db547a | 2026-10-02T09:02:00.526153+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | bf99ce5b88aae904c90d0d18b8d89aa2f638b38c3e06d1e4ad22e9253d73d7de | 2026-10-02T08:59:33.648108+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | f927ef88c08d70de7110bc4393d91b8ff5fb2c9ba49d5dce2a16335907bf4397 | 2026-10-02T08:41:19Z | PyPI fresh-install canary success=False; version=3.4.2 |
| eval/load_10_snapshot.json | True | 3ef517008d992cc9c7b23e40e12b9df48bb5155f6cc0483a6a2fc348c5c01ac4 | 2026-09-18T16:29:20.981008+00:00 | logical load 10: passed=True; total_requests=29732; success_rate=1.0; p95_ms=1.317520067095756; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 3651d8e6fcadd9a627d0bc8f158c28870220cd31eb51a81bb5ba20cb2075f64f | 2026-09-18T16:29:51.118895+00:00 | logical load 100: passed=True; total_requests=31031; success_rate=1.0; p95_ms=1.1239005252718925; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 1703951993fff014e72619d7361f12204ca047a3029d87403db16263a53e7ef7 | 2026-09-18T16:30:21.293987+00:00 | logical load 1000: passed=True; total_requests=25845; success_rate=1.0; p95_ms=1.683654636144638; model=asyncio_logical_users |
| pyproject.toml | True | dee9875742e45a3cf8a29db8ecc7973711c33dc38c11c956bbac844ad47bd455 | 2026-10-02T08:34:04Z | package version=3.4.2; scripts declared in project metadata |
| borg/__init__.py | True | e8a7c4419a589d203f586fd0e3aa57212f7a04f5896ca9d2f0388068d3b1c553 | 2026-10-02T08:34:11Z | runtime __version__=3.4.2; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI package gate is not green for the current source revision yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is not green yet.<br>Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', "served runtime borg_version '3.3.18' != source version '3.4.2'", "served runtime source_version '3.3.18' != source version '3.4.2'", 'controlled first-10 beta is closed because the frozen protocol or row-level evidence integrity gate is not green', 'controlled first-10 beta enrollment is not open or has no remaining slots', 'protocol: protocol status does not permit enrollment or completed evidence', 'protocol: protocol artifact version is not locked', 'protocol: protocol artifact wheel_sha256 is not locked', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, no_match_controls=0/8 (must equal installs=0), false_confident_matches=0/0, harmful_guidance=0/0, critical_incidents=0/0', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

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
| 1 | Do not invite controlled first-10 testers yet: publish immutable `agent-borg==3.4.2`, then require PyPI latest metadata, fresh-install, stdio MCP, served-runtime, release-governance, ops, and watchdog gates to pass before using that exact version with testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
