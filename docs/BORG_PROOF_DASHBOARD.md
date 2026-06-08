# Borg Proof Dashboard

Generated: `2026-06-08T10:58:07Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `3dd1069ec0a8ffd1e9390a0ce1bb522e78f14a1e+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | CONDITIONAL | The 10-tester infrastructure, served-runtime freshness, release governance, and ops guardrails are green; broad launch remains NO-GO pending row-derived external-user evidence. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| github source install | CONDITIONAL | Clean temp-venv install from canonical public GitHub resolved to the expected commit, then CLI and local stdio MCP first-value canaries passed. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked only by row-derived first-10 external-user evidence; GitHub source install/PyPI/latest/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates are green. |

**Controlled first-10 beta only?** CONDITIONAL GO — Controlled testers only while package, served-runtime, release-governance, ops, watchdog, rollback, and docs gates remain green.; Do not present as unattended public launch ready.; Capture real first-user outcome evidence immediately.

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
| max_recommended_real_users_now | 10 | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| public_self_serve_launch_gate | FAIL | PUBLIC_LAUNCH_GATE | eval/public_self_serve_launch_gate_snapshot.json |
| github_source_install_canary | PASS | GITHUB_SOURCE_INSTALL_EXACT_COMMIT | eval/github_source_install_snapshot.json resolved=3dd1069ec0a8ffd1e9390a0ce1bb522e78f14a1e expected=3dd1069ec0a8ffd1e9390a0ce1bb522e78f14a1e |
| cold_start_trust_hardening_gate | PASS | FIRST_ANSWER_TRUST_GATE | eval/cold_start_trust_gate_snapshot.json |
| served_runtime_freshness_gate | PASS | SERVED_RUNTIME_FINGERPRINT_GATE | eval/served_runtime_fingerprint_snapshot.json |
| release_governance_gate | PASS | RELEASE_GOVERNANCE_BRANCH_PROTECTION_GATE | eval/release_governance_snapshot.json |
| release_controls_gate | PASS | SERVED_RUNTIME_PLUS_RELEASE_GOVERNANCE | eval/real_user_rollout_gate_snapshot.json |
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| pypi_package_current_gate | PASS | PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE | eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.18 runtime=3.3.18 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | PASS | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7014390866970643, "p99_ms": 0.7474009954603388, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-07T20:14:38.570812+00:00", "total_requests": 55999, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7358029950410123, "p99_ms": 1.1172219703439619, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-07T20:15:08.685576+00:00", "total_requests": 50923, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7105699914973229, "p99_ms": 0.744672876317054, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-07T20:15:38.851782+00:00", "total_requests": 51969, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 7d0361c8ec68076688b68ba33a33919cb611a33447155e8e274f23fcbd280a5d | 2026-06-08T10:57:13Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 74916ab2c869fd9a7a08dedb8689c1506f571e2d2e9c07560246c520ce420e11 | 2026-06-07T20:15:40.778723+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 92fce969983f454dced78eac67e8634962284e7eef2e9aca5fef291b2d1e7094 | 2026-06-07T20:15:40.737235+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 35078c00a8105dfeb2469fec55ad292cfbffca84fb4f3065abecea562b0dd7be | 2026-06-08T10:57:16.779892+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 35ec6fd336ca7f91bee26ba50d66aa0b8890b9b01035a40443480d2ae5fe6f05 | 2026-06-08T10:57:15.333263+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | ccc5cb369b2818e72d0516788861fc085707b5451eb6710dd6f1e449c6c7418b | 2026-06-07T23:45:46.996124+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | 5e7517222428bae16d83e7897ff1c2bdcee39e8ebbe525ac0b083216b8aeee0a | 2026-06-08T10:58:07.112535+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | 798ee73bb2c4892424615c96d7ef66c8afa6bc0a6e21d565edc8cb706e617ffa | 2026-06-08T10:58:06.947604+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | 20b9562df58f19e7b8a2800779af979c329ebde12b58c39ac2a49a7eba5631a7 | 2026-06-07T23:45:49.519759+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | 88a1b102261e3a812b7bbc15ec968bc7e36263b4535ec262a22ba296e57636aa | 2026-06-08T10:57:05Z | PyPI fresh-install canary success=True; version=3.3.18 |
| eval/load_10_snapshot.json | True | 399cdc975b7fda8ec44386362d48b80ced66cf2c2ee0664278217405c8da0aaa | 2026-06-07T20:14:38.570812+00:00 | logical load 10: passed=True; total_requests=55999; success_rate=1.0; p95_ms=0.7014390866970643; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 554799f1bd185d72f7ac64326704be22e776b0a92bbd4f6c7d188d1c9a31a484 | 2026-06-07T20:15:08.685576+00:00 | logical load 100: passed=True; total_requests=50923; success_rate=1.0; p95_ms=0.7358029950410123; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 02cc4cd8f04392c110b85fcec8bd76b8c605ac92d4329ae3ddb1db31d25fdf8e | 2026-06-07T20:15:38.851782+00:00 | logical load 1000: passed=True; total_requests=51969; success_rate=1.0; p95_ms=0.7105699914973229; model=asyncio_logical_users |
| pyproject.toml | True | 619ce855c989f498ce35d0b14017e9c2dd5328d69d8bd0896e351a63abe9cb0c | 2026-06-07T20:12:16Z | package version=3.3.18; scripts declared in project metadata |
| borg/__init__.py | True | cb5bcde2504e5803603db8df7807887df9cfdd101ddeab7c8cb65a80a5a5a4d5 | 2026-06-07T20:12:15Z | runtime __version__=3.3.18; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>GitHub source-install canary is green: canonical public GitHub VCS install resolved the expected commit and CLI/MCP first-value commands passed.<br>PyPI latest metadata and fresh-install canary are green for the current source revision.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is green: live MCP fingerprint matches source and behavior canaries.<br>Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

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
| 1 | Use `pipx install agent-borg==3.3.18` with controlled first-10 beta testers and label it as beta evidence capture, not public launch. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
