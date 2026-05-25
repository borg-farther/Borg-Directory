# Borg Proof Dashboard

Generated: `2026-05-25T09:57:55Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `d0de486518bc0363e6ea12accf9a00fd127d5f6e+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | CONDITIONAL | Controlled first-10 beta infrastructure is green; keep broad launch blocked until row-derived external-user evidence passes. |
| local release candidate | CONDITIONAL | Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked only by row-derived first-10 external-user evidence; PyPI/latest/fresh-install/MCP/docs gates are green. |

**Controlled first-10 beta only?** GO — Controlled testers only.; Do not present as unattended public launch ready.; Capture real first-user outcome evidence immediately.

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
| max_recommended_real_users_now | 10 | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| public_self_serve_launch_gate | FAIL | PUBLIC_LAUNCH_GATE | eval/public_self_serve_launch_gate_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.12 runtime=3.3.12 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5667443969286978, "p99_ms": 0.5931002832949162, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:57:05.799889+00:00", "total_requests": 2228, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5870543187484145, "p99_ms": 0.6074796989560127, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:57:06.889657+00:00", "total_requests": 2055, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5786204012110829, "p99_ms": 0.6155471736565232, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T09:57:08.023236+00:00", "total_requests": 2152, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | d7e2f6788c3c2043e0cab2fea49098d52429fc424b0130f145b98c33d8d00146 | 2026-05-25T09:28:21Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | dab3d7fb3a7422b4b1df44b86b1820ef593e94373665f2b81afb08e30b56cd1f | 2026-05-25T09:57:08.771788+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | 86c7faab73ab153ab95246199dbe7728b4850e84788979c63145b36c56a6ab6e | 2026-05-25T09:57:08.736349+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/real_user_rollout_gate_snapshot.json | True | 2dcdd3b93ff1efe6862e5c14a841be0ce70cb790ab93d836723cacbc17c4b213 | 2026-05-25T09:57:08.673332+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/public_self_serve_launch_gate_snapshot.json | True | ba22299cdb6e9ebb54941486067ccd0ec57bf2020baf30fa214abcd8f2886634 | 2026-05-25T09:57:55.075307+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/pypi_fresh_install_snapshot.json | True | a3efad4c6c4e5b84902edfe6b490ad12e73a1ae633255c54bd547354a3627c1f | 2026-05-25T09:55:55Z | PyPI fresh-install canary success=True; version=3.3.12 |
| eval/load_10_snapshot.json | True | d38ef47dd2526d3c2fef14d056add1ee4d8539a59ed081c7be23c03c1085357b | 2026-05-25T09:57:05.799889+00:00 | logical load 10: passed=True; total_requests=2228; success_rate=1.0; p95_ms=0.5667443969286978; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | dbaa86138266a4c0946e516d65fda28e0ab8bca247c292627a0b98141c502dea | 2026-05-25T09:57:06.889657+00:00 | logical load 100: passed=True; total_requests=2055; success_rate=1.0; p95_ms=0.5870543187484145; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 8ebb3c94afe6912d7a1a35fe46e9a3c23563d843f9257a96a1c468f48b64963c | 2026-05-25T09:57:08.023236+00:00 | logical load 1000: passed=True; total_requests=2152; success_rate=1.0; p95_ms=0.5786204012110829; model=asyncio_logical_users |
| pyproject.toml | True | a6898c4a2abd5f7e5f6f1dbd01eedb39fd7beb43f01a2c2a031deb89c73eaf54 | 2026-05-24T22:42:25Z | package version=3.3.12; scripts declared in project metadata |
| borg/__init__.py | True | 392f554ea0c3768fd4940de71a267bc30d97b98cc1e52ca4fba2e0e29cfb38dc | 2026-05-24T22:42:26Z | runtime __version__=3.3.12; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 441c70a8b1a6d968af3cbd5305d00d892f2c97572327c6afa78f6f24855a0f71 | 2026-05-25T09:57:08Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | b4f64bdf48fd48990634d35c4db3abd7b4d4a698c5cf766d8996b791b00cded0 | 2026-05-25T09:57:08Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | e5c1885af0eb718eb1fcf6ceb9a74b0ab12b769ac2e45e846ddcef27a84e58b9 | 2026-05-25T09:57:08Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is green.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>100-real-user gate remains blocked: ['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Host/runtime split-brain was not freshly reproduced by this dashboard build. |

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
| 1 | Use `pipx install agent-borg==3.3.12` with controlled first-10 beta testers and label it as beta evidence capture, not public launch. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
