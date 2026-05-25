# Borg Proof Dashboard

Generated: `2026-05-25T16:09:12Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `d8e1c416dbce0e54b1a275355c6868d917d29a91+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until the public package path is green: PyPI latest metadata, fresh-install canary, stdio MCP canary, cold-start trust gate, and docs guard must all pass. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs/cold-start-trust gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until PyPI latest, fresh-install, and stdio MCP canaries are green.; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package evidence is green.

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
| pypi_fresh_install_canary | FAIL | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.14 runtime=3.3.14 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_EVALUATED_BY_THIS_BUILD | EVIDENCE_GAP | This dashboard build does not restart or fingerprint long-lived served Hermes/MCP runtimes; it is not live cutover proof. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7021749624982476, "p99_ms": 1.1334862792864464, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:03:01.823442+00:00", "total_requests": 1886, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6465265178121626, "p99_ms": 0.827525625936687, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:03:02.943176+00:00", "total_requests": 1816, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5889080930501222, "p99_ms": 0.6321987789124252, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T16:03:04.106780+00:00", "total_requests": 1934, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | cd519e1a1aad2904a8e2e0f63954b63a0ba49eeda6bbf645d6a26704797e227e | 2026-05-25T16:02:38Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 3c51ab357a4f552a577d23ae47d5aa578a6d3b0069a37dbb4225afe19a9b3377 | 2026-05-25T16:03:04.905843+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 65d2958c7966f79110ffc0fedbff47fb154222a91573110880b1d3023d4e7688 | 2026-05-25T16:03:04.867432+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | cfdfbf93dfdd9bb46bbbbeb917b08c1ee634b94e84f930c292aaa1462f0fed2a | 2026-05-25T16:03:04.806999+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 24a4123d546aa319da8ebf23817bab54f052ff68f559a5b4eaf1ccb226b33ffc | 2026-05-25T16:08:49Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | 5a2439491e2e4176e1e19e22681bd74500dbca13e666ce44d610662b0e555949 | 2026-05-25T16:09:12.753399+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata does not match source version or required project URLs', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | 32044c0bbd1bf1349a3fa569a39c3e1320a0f4b1c38f173a2b793c99a97ba0c1 | 2026-05-25T16:09:10.892388+00:00 | cold-start trust gate=True; blockers=[] |
| eval/pypi_fresh_install_snapshot.json | True | 1dc93d7ba6abb8c7e52f5afb3f26317bf66c7768d9ebc4da62a705221fab226f | 2026-05-25T10:24:34Z | PyPI fresh-install canary success=True; version=3.3.13 |
| eval/load_10_snapshot.json | True | c9ee4fdec11df4cb0ddebb6f5f1827a40249820fdc670bd30dc13b6c6e5d85f0 | 2026-05-25T16:03:01.823442+00:00 | logical load 10: passed=True; total_requests=1886; success_rate=1.0; p95_ms=0.7021749624982476; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | fbbd1559156a135728a7bd43c147bd1f6098e503d1b0fcc888bad90658832505 | 2026-05-25T16:03:02.943176+00:00 | logical load 100: passed=True; total_requests=1816; success_rate=1.0; p95_ms=0.6465265178121626; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | ddf2ba572275c781aa4c3b9ffaf9e652ebacdfe5b4219fb31c39d1edb9da390c | 2026-05-25T16:03:04.106780+00:00 | logical load 1000: passed=True; total_requests=1934; success_rate=1.0; p95_ms=0.5889080930501222; model=asyncio_logical_users |
| pyproject.toml | True | 2c1888f1f9c22ec2d75394d1e8b0a821b8b50a6de9515440fca1032ef6445d43 | 2026-05-25T15:02:34Z | package version=3.3.14; scripts declared in project metadata |
| borg/__init__.py | True | 20fd27330f31ba0829ebd6ab9fbe42834584418ac761947113c22e871438a5c9 | 2026-05-25T15:02:34Z | runtime __version__=3.3.14; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 89bb39b0084a4c0705e9ca5c251efafa7667bce5890cf7d1d749143571c39795 | 2026-05-25T16:03:04Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | 1f06bd2ed89c0879f03ac99e1a8cf711e05c5c2c520e1f0a30ea86833d73ddf0 | 2026-05-25T16:03:04Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | 4dc02e5a817f36ff4aff0874dc55f89dac696fc8783f58256e7c10cec5bb9c8f | 2026-05-25T16:03:04Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is not green for the current source version yet.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
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
| 1 | After `agent-borg==3.3.14` is published and the PyPI fresh-install + stdio MCP canary passes, use that exact PyPI version with controlled first-10 beta testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
