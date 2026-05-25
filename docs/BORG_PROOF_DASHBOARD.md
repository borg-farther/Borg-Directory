# Borg Proof Dashboard

Generated: `2026-05-25T17:06:00Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `6ee0e2d279c3165c17b64a1da38c28a9baf2f88e+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | CONDITIONAL | Controlled first-10 beta infrastructure is green; keep broad launch blocked until row-derived external-user evidence passes. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked only by row-derived first-10 external-user evidence; PyPI/latest/fresh-install/MCP/docs/cold-start-trust gates are green. |

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
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.14 runtime=3.3.14 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_EVALUATED_BY_THIS_BUILD | EVIDENCE_GAP | This dashboard build does not restart or fingerprint long-lived served Hermes/MCP runtimes; it is not live cutover proof. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5729895550757647, "p99_ms": 0.5962290475144982, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:29:46.179824+00:00", "total_requests": 2244, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.603423360735178, "p99_ms": 0.6225142069160939, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:29:47.280417+00:00", "total_requests": 2109, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5894859321415424, "p99_ms": 0.6199854891747236, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:29:48.411265+00:00", "total_requests": 2269, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | db23445734dd053c4787abcd6d8b2f348464fded364ab7d6eddf9a2b006ce425 | 2026-05-25T16:29:23Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | c5d2107d5640374bf920690c851d4c8f43e72bef32e6067a3c32616285ef2fa9 | 2026-05-25T16:29:49.164672+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 9fd1d2ce279885086c6567e1aa2202d7a8a5fcd14c2efbaee4bb2ae43cfb3b06 | 2026-05-25T16:29:49.123089+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | e72a57ff5ce723b5f62c87593bf85aa532a8c8f4b2050eeff1c0e99dc3e32291 | 2026-05-25T16:29:49.062909+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 4c0efefc72f85148e38d9a9b80c5f267a7852a749ed87eb86cfeed16d17fc0bd | 2026-05-25T17:04:55Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | ad11666f353833f325495c9c04f8a1ae417709801f81e64838a5a9d709dd20b4 | 2026-05-25T17:05:59.967842+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | b0d54d982f988be8212ee3756b4622076bdfe08f0528ede9cea56f48f074d185 | 2026-05-25T17:05:58.450437+00:00 | cold-start trust gate=True; blockers=[] |
| eval/pypi_fresh_install_snapshot.json | True | eb443a71e5d6b34ff9c390983d2e038acdcdbd83aba2f95a9c689e059b7c2634 | 2026-05-25T17:04:55Z | PyPI fresh-install canary success=True; version=3.3.14 |
| eval/load_10_snapshot.json | True | 62b5a6711972806f6e11c6346fc3816bd8ab668fbdda5253bf5c91104e36947f | 2026-05-25T16:29:46.179824+00:00 | logical load 10: passed=True; total_requests=2244; success_rate=1.0; p95_ms=0.5729895550757647; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 0a1e37536751f6f9d566d5018923a1911f52c700f46e14f9f8e1045a121950e1 | 2026-05-25T16:29:47.280417+00:00 | logical load 100: passed=True; total_requests=2109; success_rate=1.0; p95_ms=0.603423360735178; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 1cdb00c07c735da3772346b51b9f4730593ec942c9bfa92a2c00ea0fb6c433b8 | 2026-05-25T16:29:48.411265+00:00 | logical load 1000: passed=True; total_requests=2269; success_rate=1.0; p95_ms=0.5894859321415424; model=asyncio_logical_users |
| pyproject.toml | True | 2c1888f1f9c22ec2d75394d1e8b0a821b8b50a6de9515440fca1032ef6445d43 | 2026-05-25T16:54:20Z | package version=3.3.14; scripts declared in project metadata |
| borg/__init__.py | True | 20fd27330f31ba0829ebd6ab9fbe42834584418ac761947113c22e871438a5c9 | 2026-05-25T16:54:20Z | runtime __version__=3.3.14; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 0226e97842f0893efaabca3ea4f75c0ef986562864906392e1344f4506d0bcfc | 2026-05-25T16:29:49Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | 44bae7a32e78646f26acb0b00bbc72cbd581e5998f40cd7df3155d5de7035e1f | 2026-05-25T16:29:49Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | 2cfb3206dc395bda4f657b7f64d460cafaa1ca9c4504af527f441352b86e742c | 2026-05-25T16:29:49Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is green for the current source version.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime split-brain was not evaluated by this dashboard build; source/fresh-process green is not live cutover proof. |

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
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
