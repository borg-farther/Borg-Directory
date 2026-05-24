# Borg Proof Dashboard

Generated: `2026-05-24T21:09:22Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `215bd0f29c86ddbaff3796664772a9da452bbef1+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | CONDITIONAL | Controlled first-10 beta infrastructure is green; keep broad launch blocked until row-derived external-user evidence passes. |
| local release candidate | NO-GO | Required local first-user/readiness gates are not all passing or are missing. |
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
| gate_run_synthetic_load | FAIL | LOCAL_ARTIFACT_LOGICAL_USERS | eval/gate_run_snapshot.json |
| real_user_100_rollout_gate | FAIL | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| max_recommended_real_users_now | 10 | REAL_EXTERNAL_USERS | eval/real_user_rollout_gate_snapshot.json |
| public_self_serve_launch_gate | FAIL | PUBLIC_LAUNCH_GATE | eval/public_self_serve_launch_gate_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.11 runtime=3.3.11 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5755376303568482, "p99_ms": 0.6008552201092243, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-24T07:37:55.127417+00:00", "total_requests": 68962, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5981309339404106, "p99_ms": 0.6571157835423953, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-24T07:38:25.246013+00:00", "total_requests": 64939, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.560709391720593, "p99_ms": 0.5917398957535625, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-24T07:38:55.423045+00:00", "total_requests": 70111, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 367230553a5dd6202420becfaeaf268bf75603e5fc4dd54dc08f597dd0881af6 | 2026-05-24T19:44:51Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | f5770651e2c9e3e6d23eac9703a5e103d04ab49dba6f020dcdd743fcc16af648 | 2026-05-24T07:38:56.063440+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | f324e9c6919b605f593d14efe41940cecfa0b0f5e39eb00ad000478df20ba7bc | 2026-05-24T07:38:56.025585+00:00 | gate run synthetic_load_all_pass=False; overall_100_real_user_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/real_user_rollout_gate_snapshot.json | True | 5c6d2d9282b1dfad12d18be365f3edcb6bc821410c9d8dd69246cc012ee42409 | 2026-05-24T21:09:22.648203+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/public_self_serve_launch_gate_snapshot.json | True | 66b83c3e5c941676cbc7eb091142deb0c0d4b332928274aebdab341b6a885f8d | 2026-05-24T21:09:22.554492+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/pypi_fresh_install_snapshot.json | True | 68ac9d3aa510680781555144c519998b8ac772b6879690a3d1f8cb437d4e9a34 | 2026-05-24T21:09:22Z | PyPI fresh-install canary success=True; version=3.3.11 |
| eval/load_10_snapshot.json | True | b17c67eac7a35d03b27a598b05f543c19523e52073bf25828c722e9e76b69764 | 2026-05-24T07:37:55.127417+00:00 | logical load 10: passed=True; total_requests=68962; success_rate=1.0; p95_ms=0.5755376303568482; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | ffaee97abd21493996d056c812b26503af5e05d6432a68c2a8ae0a454f571952 | 2026-05-24T07:38:25.246013+00:00 | logical load 100: passed=True; total_requests=64939; success_rate=1.0; p95_ms=0.5981309339404106; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | b1c1bde0a6b82cb61c68d326359b49b2bcfe3cf78608f3dbc7d52d6994996aec | 2026-05-24T07:38:55.423045+00:00 | logical load 1000: passed=True; total_requests=70111; success_rate=1.0; p95_ms=0.560709391720593; model=asyncio_logical_users |
| pyproject.toml | True | b8af575dae132c157cf848dbb5f53c84ebfd58a4983cd5ff0800e6c6d7db77ea | 2026-05-24T21:04:13Z | package version=3.3.11; scripts declared in project metadata |
| borg/__init__.py | True | 0a6f8653c22cb2cda6101d26929893804c855e0c3e41ded6179fac491e33d785 | 2026-05-24T21:04:13Z | runtime __version__=3.3.11; top-level check() delegates to search |
| PROJECT_STATUS.md | True | e8b36fb233590ba0e351f571ba3f65ea644ee8b46c105e5c0cd4eef602105de3 | 2026-05-24T19:44:51Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | a12a902945e0ce27e4c2eaeabee2122064d995b8e3b7b4248a981759fb538072 | 2026-05-24T19:44:51Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | fdcc490e01ed9542b6f9a30dd00999b5d0a3416e7cb6b26528d3c764a6a8e595 | 2026-05-24T19:44:51Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

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
| 1 | Use `pipx install agent-borg==3.3.11` with controlled first-10 beta testers and label it as beta evidence capture, not public launch. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
