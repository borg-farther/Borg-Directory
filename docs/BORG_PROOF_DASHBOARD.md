# Borg Proof Dashboard

Generated: `2026-05-14T18:25:41Z`
Repo: `/root/hermes-workspace/borg`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| supervised first user onboarding | CONDITIONAL | Share only with hands-on supervision: install/runtime/security/local logical-load gates pass, but verified external users remain 0 and first-user outcome evidence is uncollected. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | No verified external-user adoption evidence, no first-10 real-user scoreboard, and public-launch claims would overstate local/logical evidence. |

**Ready to share Git now?** YES, supervised only — Do not present as unattended or public launch ready.; Capture real first-user outcome evidence immediately.

## Metrics with provenance and honesty labels

| Metric | Value | Honesty label | Provenance |
| --- | --- | --- | --- |
| verified_external_users | 0 | HARD_EVIDENCE_ABSENT_DEFAULT_ZERO | No artifact found that identifies real verified external users; simulated/logical load users are excluded. |
| active_contributors_consumers | UNKNOWN | MISSING_BORG_ANALYTICS_ARTIFACT | No Borg analytics export artifact was found under eval/ or docs/. |
| packs | 11 | REPO_FILE_COUNT | borg/seeds_data/packs/*.yaml |
| first_user_release_gate | PASS | LOCAL_ARTIFACT | eval/first_user_release_gate_snapshot.json |
| uat_scoreboard | PASS | LOCAL_ARTIFACT | eval/uat_scoreboard_snapshot.json |
| gate_run | PASS | LOCAL_ARTIFACT | eval/gate_run_snapshot.json |
| version_package | pyproject=3.3.1 runtime=3.3.1 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6120754994299205, "p99_ms": 0.666747909872356, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-06T09:31:42.148143+00:00", "total_requests": 60070, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.610864001646405, "p99_ms": 0.7458787990617565, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-06T09:32:12.279837+00:00", "total_requests": 61213, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.5984217998047825, "p99_ms": 0.6205782780307345, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-06T09:32:42.460236+00:00", "total_requests": 62409, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | f9d5f8d1b5ed91c3bfd75b342aaab07e6ecebe8ac63a79594869ab472e297e06 | 2026-05-14T18:25:31Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | fc16aa0aa9406c3877043d82912c671f1569cf9619afd1beef3c69779f0c78b5 | 2026-05-06T09:32:45.808525+00:00 | UAT all_pass=True; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | 8d48892c0ce75f87a10a47c124d4e20d94b457c38f9917c33a06ba1aa22b73fe | 2026-05-06T09:32:43.065021+00:00 | gate run all_pass=True; ready_for_10=True; ready_for_1000=True |
| eval/load_10_snapshot.json | True | 63dc32e87a6af35c21da2c5c356652a7583e2a15e363b52d1ad1aa9b7d351781 | 2026-05-06T09:31:42.148143+00:00 | logical load 10: passed=True; total_requests=60070; success_rate=1.0; p95_ms=0.6120754994299205; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 8d8cfe98612638f591ebf0b7d1544124819bb48b4d09f54832b5649485e93485 | 2026-05-06T09:32:12.279837+00:00 | logical load 100: passed=True; total_requests=61213; success_rate=1.0; p95_ms=0.610864001646405; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 67447035d513c8f7a03a9afb85b57c3aa1d0642904bc14b17ee8b1cfaec068ca | 2026-05-06T09:32:42.460236+00:00 | logical load 1000: passed=True; total_requests=62409; success_rate=1.0; p95_ms=0.5984217998047825; model=asyncio_logical_users |
| pyproject.toml | True | facdfad7d1b3b69e409bd71efe613921bb3f58c6e57c4abac10bf23bfee4f2c4 | 2026-05-06T09:28:13Z | package version=3.3.1; scripts declared in project metadata |
| borg/__init__.py | True | e96fdfa7cd6352a2df70a102a03bc091dd47c5d075895fd6c45e51193d299f15 | 2026-05-04T11:28:12Z | runtime __version__=3.3.1; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 54ec5d54e0d16489277920f97ead9fdf403518e7e8c9bab41d72422b6f88688f | 2026-05-14T18:25:31Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | 985124bb4b6e0cac5386bd445e3706f7a674df017466930467cb5e569f1677ea | 2026-05-14T18:25:31Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | 2e83876cd5966a26bd454631c520032c548a4bf67d7ac1dae71f360eb67ada4a | 2026-05-14T18:25:31Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| ROADMAP.md | True | 4a5543ec56f241a35ba0bc86f6fd6a1fd3d635292d0f306c56313d426b9ba475 | 2026-05-04T11:29:44Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real first-user install/rescue outcome has been recorded yet.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not publish/push/change repo visibility from this proof build.<br>Need one supervised dry run from clean Git clone by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Host/runtime split-brain was not freshly reproduced by this dashboard build. |

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

## Next action queue before sharing Git with first user

| # | Action |
| --- | --- |
| 1 | Share Git only with first user under live supervision and label it as a private proof, not public launch. |
| 2 | Create a fresh-clone runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
