# Borg Proof Dashboard

Generated: `2026-06-02T10:11:16Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `7125ec9e19ea44efb5ec42bd69a1c9672db50983+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until these failed gates are green: PyPI latest/fresh-install/stdout MCP package path; served-runtime freshness |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until these failed gates are green: PyPI latest/fresh-install/stdout MCP package path; served-runtime freshness; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package/release-control/ops evidence is green.

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
| source_version_consistency | pyproject=3.3.16 runtime=3.3.16 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | FAIL | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7009429158642886, "p99_ms": 0.7570860907435419, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T10:02:24.261506+00:00", "total_requests": 53718, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.693068839609623, "p99_ms": 0.7233379036188128, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T10:02:54.393645+00:00", "total_requests": 54025, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6952499970793724, "p99_ms": 0.7640478946268553, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T10:03:24.559311+00:00", "total_requests": 53117, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 1a46e0d720645a0553914654a7ad170b404d586175f63a219dc1bd079e6b1c21 | 2026-06-02T10:01:26Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | b79bdfc9d53dc0ab90d5fee6debba3bac23926e2968a23cbb544b9d3a8fbda6b | 2026-06-02T10:03:26.639759+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | d59075ee21be643405404289c608ad9401c34fea29b1fb08190e1912f11e11ed | 2026-06-02T10:03:26.595448+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | cb5cc2f40f2ee5fd3b4644d953cd1480366805e5f2935e5a75baa6660ec164d5 | 2026-06-02T10:11:13.450269+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: same-version PyPI upload predates current source revision', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 76c1afa76487d7555c8a480e08b2fc2c51bc1c3ff23a085bbb7f410eb3afd263 | 2026-06-02T10:11:12.129841+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata is stale: same-version release upload predates current source revision', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | 2fbc2b7fe7181e0b6f7b8312e8bce46c2601d067b693b92bf5d34720b12edd29 | 2026-06-02T10:09:10.785062+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | 8233cdaa932d5de3672fc47ed046f25fc73616074a4bbf0648dcf78fa872e21f | 2026-06-02T10:11:16.728284+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | eb8f9416b27841d805067fbe6c56aa0033cef63783ff325d3d6699efe418383f | 2026-06-02T10:11:16.398619+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | 3f708838558195311f8e86957ba20ea314d2a50ea077a3b9149d7dbf78f45f1a | 2026-06-02T10:09:13.802460+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | b94d0f3608cda5c1c4e29356d0146ace14d66aba8255550eaf9e777852151900 | 2026-06-02T10:08:48Z | PyPI fresh-install canary success=False; version=3.3.16 |
| eval/load_10_snapshot.json | True | e42ccff03c87c93751c8b6953d0f974f7fe8f36e8eaea5b0461e77329ec91808 | 2026-06-02T10:02:24.261506+00:00 | logical load 10: passed=True; total_requests=53718; success_rate=1.0; p95_ms=0.7009429158642886; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | dbee93aa190560df61dc33280f05327d2b9b4ed8a5456bb60b622c0ddcd0c98f | 2026-06-02T10:02:54.393645+00:00 | logical load 100: passed=True; total_requests=54025; success_rate=1.0; p95_ms=0.693068839609623; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | a92f1de3787bcaafdb2f9694a750ddb146727fe0f5e2c9e2a24ec8da2b517f66 | 2026-06-02T10:03:24.559311+00:00 | logical load 1000: passed=True; total_requests=53117; success_rate=1.0; p95_ms=0.6952499970793724; model=asyncio_logical_users |
| pyproject.toml | True | 87a7b7c43e63c0a0d46f0e69b01c1dd5ccd4308ba56304d1f6da53b80c6f64eb | 2026-06-02T00:15:23Z | package version=3.3.16; scripts declared in project metadata |
| borg/__init__.py | True | c5b0048872dafb21a4f6dc1ee5c7e7c6c471f4c203acbcc06cdb9f139f3c2191 | 2026-06-02T00:15:24Z | runtime __version__=3.3.16; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI package gate is not green for the current source revision yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is not green yet.<br>Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: same-version PyPI upload predates current source revision', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', "served runtime borg_version '3.3.14' != source version '3.3.16'", "served runtime source_version '3.3.15' != source version '3.3.16'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

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
| 1 | Do not invite controlled first-10 testers yet: publish immutable `agent-borg==3.3.16`, then require PyPI latest metadata, fresh-install, stdio MCP, served-runtime, release-governance, ops, and watchdog gates to pass before using that exact version with testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
