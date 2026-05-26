# Borg Proof Dashboard

Generated: `2026-05-26T10:13:28Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `4d38c3d710d597122d022d77977c9574679483a8+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | CONDITIONAL | Controlled first-10 beta infrastructure and ops guardrails are green; keep broad launch blocked until row-derived external-user evidence passes. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked only by row-derived first-10 external-user evidence; PyPI/latest/fresh-install/MCP/docs/cold-start-trust/self-service-ops gates are green. |

**Controlled first-10 beta only?** GO — Controlled testers only.; Do not present as unattended public launch ready.; Capture real first-user outcome evidence immediately.

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
| cold_start_trust_hardening_gate | PASS | FIRST_ANSWER_TRUST_GATE | eval/cold_start_trust_gate_snapshot.json |
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.14 runtime=3.3.14 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_EVALUATED_BY_THIS_BUILD | EVIDENCE_GAP | This dashboard build does not restart or fingerprint long-lived served Hermes/MCP runtimes; it is not live cutover proof. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5990194738842546, "p99_ms": 0.6211620359681547, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-26T10:13:24.573071+00:00", "total_requests": 2060, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5893629277125001, "p99_ms": 0.6130644236691297, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-26T10:13:25.677348+00:00", "total_requests": 2096, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5626976257190108, "p99_ms": 0.6110555166378617, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-26T10:13:26.812907+00:00", "total_requests": 2288, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | ae8dfbb3e02879d0e7213ae7d4fb316166eafae47953bd06136181f00fe0607a | 2026-05-26T10:12:00Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | f768ad5540096868e213657b855e9a4d28224d1424f69a3b3e1917a522b4a73b | 2026-05-26T10:13:27.630827+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 9198a839c319ef17f789c99487771422e95dabedf76cbcef6a4c8bb7fa3896b4 | 2026-05-26T10:13:27.590039+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 13f984a1c557121d20a3021b815a5b03e7544e1dffccf0585e1bf8a5cf4667a1 | 2026-05-26T10:13:27.930659+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 2e20fb55d6e71fc8a81087c127204d07df280197bb2a664f1acab04f14f91347 | 2026-05-26T09:22:46.556868+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | d07aaaae3faaa350827f64a7e1be10bd65b32da2d6982acaec846eb8204fa437 | 2026-05-26T10:13:22.047215+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | c07e7d65aa82485ad9aecdd75c2c3a84c3506253631091c17a9e08cd12d6c375 | 2026-05-26T09:22:46.371352+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | ac9f46157dcf07d7fbd4387b2c7300ab4ac86aa7a37416e274fdb71547c1bb25 | 2026-05-26T06:22:04.958363+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | 0f384ce592be113340886fc31a9a49f64455e79b3486c6d9c5662c3c6c0a56e4 | 2026-05-26T10:12:23.434840+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | eb443a71e5d6b34ff9c390983d2e038acdcdbd83aba2f95a9c689e059b7c2634 | 2026-05-25T17:04:55Z | PyPI fresh-install canary success=True; version=3.3.14 |
| eval/load_10_snapshot.json | True | 5f9ed0b21e755d5936030ea50b72fcffad04e5ceae3dc7371ab791c493991c92 | 2026-05-26T10:13:24.573071+00:00 | logical load 10: passed=True; total_requests=2060; success_rate=1.0; p95_ms=0.5990194738842546; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | ed9f8a1e5a81f12c169565a533119063c10efce794c1e5473e8ffdcaa2c2e546 | 2026-05-26T10:13:25.677348+00:00 | logical load 100: passed=True; total_requests=2096; success_rate=1.0; p95_ms=0.5893629277125001; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 9333a8cb891e72d816e8b14670c1503d9925f5e4dcb7719ea005c04b808cb7a7 | 2026-05-26T10:13:26.812907+00:00 | logical load 1000: passed=True; total_requests=2288; success_rate=1.0; p95_ms=0.5626976257190108; model=asyncio_logical_users |
| pyproject.toml | True | d0bc7249b4c0f2119b4d22d23ea59b58f19968f766dc188655ecf28f7c0823d6 | 2026-05-26T10:10:33Z | package version=3.3.14; scripts declared in project metadata |
| borg/__init__.py | True | 20fd27330f31ba0829ebd6ab9fbe42834584418ac761947113c22e871438a5c9 | 2026-05-25T16:54:20Z | runtime __version__=3.3.14; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is green for the current source version.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog must stay green; any P0/P1 bad-answer, privacy, support, or stale-proof failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime split-brain was not evaluated by this dashboard build; source/fresh-process green is not live cutover proof. |

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
| 1 | Use `pipx install agent-borg==3.3.14` with controlled first-10 beta testers and label it as beta evidence capture, not public launch. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
