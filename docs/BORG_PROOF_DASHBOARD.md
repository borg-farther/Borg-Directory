# Borg Proof Dashboard

Generated: `2026-05-25T10:25:23Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `99b7f3105db973975fafc255714899d94836e848+dirty`

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
| source_version_consistency | pyproject=3.3.13 runtime=3.3.13 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5851601017639041, "p99_ms": 0.6082637002691627, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T10:25:20.529162+00:00", "total_requests": 2171, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5741093773394823, "p99_ms": 0.6039737351238728, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T10:25:21.633314+00:00", "total_requests": 2129, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5724917049519718, "p99_ms": 0.6040538428351281, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-25T10:25:22.773460+00:00", "total_requests": 2114, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | dd08f1c95c376af47413b94bf7f5d04453606fc535cdb9d1d9d7d1ddd3aa2fc9 | 2026-05-25T10:25:17Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 88c183536a95aa0fbe821b91e8cfc01e6482fa6d694545c553aafaeae87d54a0 | 2026-05-25T10:25:23.534324+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | c12e864a473c53fb8b731aed0c6a1bd0deb213da29ebe461b1db76e3a8b5bbc7 | 2026-05-25T10:25:23.499358+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/real_user_rollout_gate_snapshot.json | True | fb39aac92ca0f3016976ab5727b38b56e141c9cc23e29e7c2e5e2a9e84d9d4ee | 2026-05-25T10:25:23.442872+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/public_self_serve_launch_gate_snapshot.json | True | a3ea3ec90d01d9ff53adcb280f9246781c262a7ff515eb1c417e08809c88469f | 2026-05-25T10:25:23.857642+00:00 | public self-serve gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/pypi_fresh_install_snapshot.json | True | 1dc93d7ba6abb8c7e52f5afb3f26317bf66c7768d9ebc4da62a705221fab226f | 2026-05-25T10:24:34Z | PyPI fresh-install canary success=True; version=3.3.13 |
| eval/load_10_snapshot.json | True | 754c139b6766f020b0215bd5a9bc966cf564f95fbac9e427350b2ca06934a459 | 2026-05-25T10:25:20.529162+00:00 | logical load 10: passed=True; total_requests=2171; success_rate=1.0; p95_ms=0.5851601017639041; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 7f1ff2972fc99fdbce239112fe588e1d4879e69c638e1f7e83de96fa5977c3c0 | 2026-05-25T10:25:21.633314+00:00 | logical load 100: passed=True; total_requests=2129; success_rate=1.0; p95_ms=0.5741093773394823; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | dd89c902e6c0b9ce04aeeaaa05fa49c0c9af12b32df383fe950ee32f6c242a47 | 2026-05-25T10:25:22.773460+00:00 | logical load 1000: passed=True; total_requests=2114; success_rate=1.0; p95_ms=0.5724917049519718; model=asyncio_logical_users |
| pyproject.toml | True | 17f37d190f878a6f2aa5429d1c68b33256a7cf6fe79ddbf04940c1d38862a3cd | 2026-05-25T10:19:13Z | package version=3.3.13; scripts declared in project metadata |
| borg/__init__.py | True | bfc9e1fefbd02a99ebd1dc6746f5d1dfb9d8edf9f0edb9f63b848202ebc6b44a | 2026-05-25T10:19:13Z | runtime __version__=3.3.13; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 354cc3bacf9633df012dcf9555736ac004b36968eabcb5e6f50bdd9ba66a76b2 | 2026-05-25T10:25:23Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | 31592dec9fdb3256201207964586b2f15469c1638316d35c660dafd706822b43 | 2026-05-25T10:25:23Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | 2e3c451b911b4f65ed643ec59ec2995854d9bf247a252cb84b018f0a9842e35f | 2026-05-25T10:25:23Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

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
| 1 | Use `pipx install agent-borg==3.3.13` with controlled first-10 beta testers and label it as beta evidence capture, not public launch. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
