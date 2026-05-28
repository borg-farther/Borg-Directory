# Borg Proof Dashboard

Generated: `2026-05-28T17:22:09Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `0097aec9a1069786b533cdfe79e2fba006ea9066+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until the public package path and ops layer are green, and any first-10 privacy/security incidents are triaged: PyPI latest metadata, fresh-install canary, stdio MCP canary, cold-start trust gate, self-service ops gate, and docs guard must all pass. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust/self-service-ops gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until PyPI latest, fresh-install, stdio MCP, cold-start trust, self-service ops, and watchdog gates are green.; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package/ops evidence is green.

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
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | FAIL | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.15 runtime=3.3.15 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_EVALUATED_BY_THIS_BUILD | EVIDENCE_GAP | This dashboard build does not restart or fingerprint long-lived served Hermes/MCP runtimes; it is not live cutover proof. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.692504458129406, "p99_ms": 0.745874014683068, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-28T08:03:10.671717+00:00", "total_requests": 55571, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6818614318035543, "p99_ms": 0.7167507149279118, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-28T08:03:40.794857+00:00", "total_requests": 55624, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7186339935287833, "p99_ms": 0.8631944004446266, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-28T08:04:10.957423+00:00", "total_requests": 51863, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 5865d736587836f25dc06340cc1314b43148a99b1311747b85593476a0f2f82d | 2026-05-28T17:22:08Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 5bf3463de69dcf869e0844a66940cf512e88ee6a797f12092e6024ff27568572 | 2026-05-28T08:04:11.821427+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 3d0fa6cb6f32dae032fbcc0f9b5467a6299fbcaacca4110c8c204df48963ad17 | 2026-05-28T08:04:11.774469+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 14eb1c88454a18d20a5eff4e6baec7fb6319b75ec5cd86eddb7a31b951c95a13 | 2026-05-28T17:22:09.342905+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | d6394343eda2921c8e3628d21214eed74fc93ddcc963bec7f3691085378dfe74 | 2026-05-28T17:22:09.205027+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata does not match source version or required project URLs', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | 3adb5712a233b38852379546c775ed0997dd11f5aa0ccc4f750238c4f80be140 | 2026-05-28T08:04:53.760111+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | 12b46e82979c724d14cf883e94d874c3070fe120d0793ee9d6595efd4e8e1323 | 2026-05-28T08:04:34.595763+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | ac9f46157dcf07d7fbd4387b2c7300ab4ac86aa7a37416e274fdb71547c1bb25 | 2026-05-26T06:22:04.958363+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | 8f4b0d8a09689b2379aeecaa970b51970e6fdc30e0eb31bac5602b85cbc57ff6 | 2026-05-27T20:55:01.908873+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | a4291a3acf05ca3286eb4aea1531a8d09d0f8ed69b357bfe4e6513b817964d2d | 2026-05-28T09:11:35Z | PyPI fresh-install canary success=True; version=3.3.14 |
| eval/load_10_snapshot.json | True | c701c046aacf047771171220ade45c2ea585e226fd0cc893de9fce7d96b0a4e0 | 2026-05-28T08:03:10.671717+00:00 | logical load 10: passed=True; total_requests=55571; success_rate=1.0; p95_ms=0.692504458129406; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 7fe6342c5388dd80fd41354d1c4e4d694b5b7d97e210d52b072980bf17e7c5ea | 2026-05-28T08:03:40.794857+00:00 | logical load 100: passed=True; total_requests=55624; success_rate=1.0; p95_ms=0.6818614318035543; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 0f2f9453b6f9d6bb10ca0a7172b46610056d8a857a1d1b5daed5915aa7ccd884 | 2026-05-28T08:04:10.957423+00:00 | logical load 1000: passed=True; total_requests=51863; success_rate=1.0; p95_ms=0.7186339935287833; model=asyncio_logical_users |
| pyproject.toml | True | 7c64582d55eaa41d409632bb5e00a9cbea510dbf800a22e0b809bc590ca5a46b | 2026-05-28T09:51:56Z | package version=3.3.15; scripts declared in project metadata |
| borg/__init__.py | True | 2a40b7e278285891a085a945b3a58251ab65ccf2df9de1a4099578df9012a911 | 2026-05-28T09:51:57Z | runtime __version__=3.3.15; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is not green for the current source version yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog must stay green; any P0/P1 bad-answer, privacy, support, or stale-proof failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime split-brain was not evaluated by this dashboard build; source/fresh-process green is not live cutover proof. |

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
| 1 | After `agent-borg==3.3.15` is published and the PyPI fresh-install + stdio MCP canary passes, use that exact PyPI version with controlled first-10 beta testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
