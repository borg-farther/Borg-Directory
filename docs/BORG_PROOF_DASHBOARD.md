# Borg Proof Dashboard

Generated: `2026-05-25T09:35:05Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `12451cbcaea5581fa72a2380aa878d87d6345602+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until the public package path is green: PyPI latest metadata, fresh-install canary, stdio MCP canary, and docs guard must all pass. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until PyPI latest, fresh-install, and stdio MCP canaries are green.; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package evidence is green.

## Metrics with provenance and honesty labels

| Metric | Value | Honesty label | Provenance |
| --- | --- | --- | --- |
| verified_external_users | 0 | HARD_EVIDENCE_ABSENT_DEFAULT_ZERO | No artifact found that identifies real verified external users; simulated/logical load users are excluded. |
| active_contributors_consumers | UNKNOWN | MISSING_BORG_ANALYTICS_ARTIFACT | No Borg analytics export artifact was found under eval/ or docs/. |
| packs | 11 | REPO_FILE_COUNT | borg/seeds_data/packs/*.yaml |
| first_user_release_gate | PASS | LOCAL_ARTIFACT | eval/first_user_release_gate_snapshot.json |
| uat_scoreboard_synthetic_load | PASS | LOCAL_ARTIFACT_LOGICAL_USERS | eval/uat_scoreboard_snapshot.json |
| gate_run_synthetic_load | PASS | LOCAL_ARTIFACT_LOGICAL_USERS | eval/gate_run_snapshot.json |
| real_user_100_rollout_gate | FAIL | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| max_recommended_real_users_now | 0 | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| public_self_serve_launch_gate | FAIL | PUBLIC_LAUNCH_GATE | eval/public_self_serve_launch_gate_snapshot.json |
| pypi_fresh_install_canary | FAIL | PYPI_FRESH_INSTALL | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.12 runtime=3.3.12 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5594801041297615, "p99_ms": 0.5933718127198517, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:28:24.069323+00:00", "total_requests": 2234, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5969941150397062, "p99_ms": 0.6344049051403998, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:28:25.163348+00:00", "total_requests": 2137, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5754714016802609, "p99_ms": 0.6166691356338562, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:28:26.298618+00:00", "total_requests": 2230, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | d7e2f6788c3c2043e0cab2fea49098d52429fc424b0130f145b98c33d8d00146 | 2026-05-25T09:28:21Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 95eaca2db396f57624c7cef48c265d6e2a74abe0a65842a3a481a16e695dc54d | 2026-05-25T09:28:26.974772+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | c081a1b5aba536fc49d7572ffb36dd7b8367ed6378965673f2362021e8df2134 | 2026-05-25T09:28:26.936250+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/real_user_rollout_gate_snapshot.json | True | 1be3d5c3156374aeb80103445491e5a303d904b40c0bf6d90df5ad303d5262d3 | 2026-05-25T09:28:26.877922+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/public_self_serve_launch_gate_snapshot.json | True | 0d69c3a18b5d3a20e839dde686536962d3bb0829bbd257e86cf9582dfc143c4b | 2026-05-25T09:35:05.119721+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata does not match source version or required project URLs', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/pypi_fresh_install_snapshot.json | True | 335e835f213bb86a9e75054d0d91a52c125501e55e75e31450602bb0845e231b | 2026-05-25T09:35:04Z | PyPI fresh-install canary success=False; version=3.3.12 |
| eval/load_10_snapshot.json | True | bfdb7186801d5e51d42f2d1e1dbeca6d223a5d12189a1a5b407314abba9e3d29 | 2026-05-25T09:28:24.069323+00:00 | logical load 10: passed=True; total_requests=2234; success_rate=1.0; p95_ms=0.5594801041297615; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | c1026f28f1a9ff792042ecc4a2d46e08988789524335d7652ccb004a551ddbe5 | 2026-05-25T09:28:25.163348+00:00 | logical load 100: passed=True; total_requests=2137; success_rate=1.0; p95_ms=0.5969941150397062; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | da827777ed18bf144c4f50b51e96639f39db261e66e9242d84c74e64c55ade1f | 2026-05-25T09:28:26.298618+00:00 | logical load 1000: passed=True; total_requests=2230; success_rate=1.0; p95_ms=0.5754714016802609; model=asyncio_logical_users |
| pyproject.toml | True | a6898c4a2abd5f7e5f6f1dbd01eedb39fd7beb43f01a2c2a031deb89c73eaf54 | 2026-05-24T22:42:25Z | package version=3.3.12; scripts declared in project metadata |
| borg/__init__.py | True | 392f554ea0c3768fd4940de71a267bc30d97b98cc1e52ca4fba2e0e29cfb38dc | 2026-05-24T22:42:26Z | runtime __version__=3.3.12; top-level check() delegates to search |
| PROJECT_STATUS.md | True | f636d707a88b1bc201d096a445d6c63574372661bc75e0c8a2769000142e2b1b | 2026-05-25T09:28:26Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | d31a9fdee8f629d90ebd544ccc9edf8dd7a767554d1382a6828fa3d28f5bfca8 | 2026-05-25T09:28:26Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | c67ee90203ef964851ddcceb3d6a108d5d5ab56820e9cc088e6f2c8705cd541c | 2026-05-25T09:28:26Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is not green yet.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', 'PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Host/runtime split-brain was not freshly reproduced by this dashboard build. |

## First-10-user scoreboard template

| # | user id/pseudonym | install success | time to first rescue | rescue useful yes/no | MCP setup success | blocker | outcome recorded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |

## Anti-hype section

Simulated/logical users are not real users. Internal sessions, tool calls, local tests, and maintainer runs are not adoption. Real verified external users are 0 unless a hard evidence artifact proves otherwise; no such artifact was found by this build.

## Next action queue before controlled first-10 beta testers

| # | Action |
| --- | --- |
| 1 | After `agent-borg==3.3.12` is published and the PyPI fresh-install + stdio MCP canary passes, use that exact PyPI version with controlled first-10 beta testers. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
