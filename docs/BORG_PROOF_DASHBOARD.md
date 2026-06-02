# Borg Proof Dashboard

Generated: `2026-06-02T00:05:45Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `8a12952126e4f6a76a826d1f66a9114b9f3cd1f8+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until these failed gates are green: PyPI latest/fresh-install/stdout MCP package path; served-runtime freshness; release governance / main branch protection |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until these failed gates are green: PyPI latest/fresh-install/stdout MCP package path; served-runtime freshness; release governance / main branch protection; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package/release-control/ops evidence is green.

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
| release_governance_gate | FAIL | RELEASE_GOVERNANCE_BRANCH_PROTECTION_GATE | eval/release_governance_snapshot.json |
| release_controls_gate | FAIL | SERVED_RUNTIME_PLUS_RELEASE_GOVERNANCE | eval/real_user_rollout_gate_snapshot.json |
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| pypi_package_current_gate | FAIL | PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE | eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.15 runtime=3.3.15 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | FAIL | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7141415262594819, "p99_ms": 0.7846186403185129, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-31T10:09:46.692829+00:00", "total_requests": 50316, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.9827278554439545, "p99_ms": 3.343379381112749, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-31T10:10:16.830140+00:00", "total_requests": 40066, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7121274247765541, "p99_ms": 0.7705441676080227, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-31T10:10:47.003248+00:00", "total_requests": 49726, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | cb383c14193f1c5b8947e8cf0f51a96e69b363b2fe412e81a335799374594ed9 | 2026-05-30T19:28:30Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 2fd457d8a9b6868ac1481274954fab0ade3afacc1c642c1a5e344d35b54677a1 | 2026-05-31T10:10:48.072287+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 92860954f0bf4c1b3a21827b29cc837f840e72fe9988b73414a7d87126c49aa6 | 2026-05-31T10:10:48.023553+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 374c4d6b2013e5a5c7f9f88cf088aa8eba1db29ea2f4520c00d64dee530f0c62 | 2026-06-02T00:05:45.514351+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: same-version PyPI upload predates current source revision', "served runtime borg_version '3.3.14' != source version '3.3.15'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'release governance live check failed: HTTP Error 403: rate limit exceeded', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 8d8e4c2a20de4bf69052e554a89deac093516c0be11a26e233ad82783ad13bcf | 2026-06-02T00:05:45.249054+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata is stale: same-version release upload predates current source revision', "served runtime borg_version '3.3.14' != source version '3.3.15'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'release governance live check failed: HTTP Error 403: rate limit exceeded', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | 260603615c7a193973b834d0c2f372cee5ae7a1f2d13a0f0a652c77255e0e00d | 2026-06-02T00:05:41.769417+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | f3310aed3b00581668a6de62932af13aaed9f67176387a5b39b4d49c3bf95399 | 2026-06-02T00:05:45.647327+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | 629750c4eb89ebee2cb448df9cf7a9a77a40e5688f9dc258286869f89d57258d | 2026-06-02T00:05:44.893574+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | a11fad179f690114f4c19606b0fbb699f2127e420309f54df99c2f0a2f3c242f | 2026-06-02T00:05:43.317036+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | 7739fc7758f4505760bcdd7855775bbdd37f1a67f5c59cd6a9abb8356ef7486d | 2026-06-02T00:04:58Z | PyPI fresh-install canary success=True; version=3.3.15 |
| eval/load_10_snapshot.json | True | 0d2e68df17bda30f2f2c85063c29c904fa18677f5c6a74757ac3e3e95233a881 | 2026-05-31T10:09:46.692829+00:00 | logical load 10: passed=True; total_requests=50316; success_rate=1.0; p95_ms=0.7141415262594819; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 2b51f0f8e7e6c1444239373695387da9257eb757101fdd12fdcc7481122b9f71 | 2026-05-31T10:10:16.830140+00:00 | logical load 100: passed=True; total_requests=40066; success_rate=1.0; p95_ms=0.9827278554439545; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | ada29dab187cb1f36f9d942af35d1ff85b271f3dec1e7393a794cb759e323ea8 | 2026-05-31T10:10:47.003248+00:00 | logical load 1000: passed=True; total_requests=49726; success_rate=1.0; p95_ms=0.7121274247765541; model=asyncio_logical_users |
| pyproject.toml | True | 7c64582d55eaa41d409632bb5e00a9cbea510dbf800a22e0b809bc590ca5a46b | 2026-05-28T17:43:46Z | package version=3.3.15; scripts declared in project metadata |
| borg/__init__.py | True | 2a40b7e278285891a085a945b3a58251ab65ccf2df9de1a4099578df9012a911 | 2026-05-28T17:43:46Z | runtime __version__=3.3.15; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI package gate is not green for the current source revision yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is not green yet.<br>Release governance gate is not green yet.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: same-version PyPI upload predates current source revision', "served runtime borg_version '3.3.14' != source version '3.3.15'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'release governance live check failed: HTTP Error 403: rate limit exceeded', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

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
| 1 | Do not invite controlled first-10 testers yet: publish a new immutable `agent-borg` version after `3.3.15`, then require PyPI latest metadata, fresh-install, stdio MCP, served-runtime, release-governance, ops, and watchdog gates to pass before using that exact version with testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
