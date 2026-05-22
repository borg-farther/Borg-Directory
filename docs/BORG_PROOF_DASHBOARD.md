# Borg Proof Dashboard

Generated: `2026-05-22T11:41:37Z`
Repo: `/root/hermes-workspace/borg-firewall-fix`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| supervised first user onboarding | CONDITIONAL | Share only with hands-on supervision: install/runtime/security/local logical-load gates pass, but verified external users remain 0 and first-user outcome evidence is uncollected. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs gates pass and first-10 external evidence exists. |

**Supervised source checkout only?** CONDITIONAL — Hands-on maintainer supervision only.; Do not present as unattended or public launch ready.; Capture real first-user outcome evidence immediately.

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
| pypi_fresh_install_canary | FAIL | PYPI_FRESH_INSTALL | eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.8 runtime=3.3.8 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | NOT_REPRODUCED_IN_THIS_BUILD | EVIDENCE_GAP | Prior docs mention runtime/host issues, but this dashboard build did not run environment probes. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6281427631620318, "p99_ms": 0.8716626581735909, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-18T07:45:06.621553+00:00", "total_requests": 59794, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6004410097375512, "p99_ms": 0.6370391696691513, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-18T07:45:36.770025+00:00", "total_requests": 59981, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.6051470059901476, "p99_ms": 0.7191141927614809, "passed": true, "success_rate": 1.0, "timestamp": "2026-05-18T07:46:06.931035+00:00", "total_requests": 59947, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | c89079ed1340bf79014abb11777f4a6dd331efbec46f7bd62eb20cf898067991 | 2026-05-22T11:01:45Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | d05753c32ce3b9b3e2f115b2b164c18d7635af4e8cd6c4ae7e73dabac2e6109e | 2026-05-18T07:46:07.702390+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/gate_run_snapshot.json | True | 70e7a691c169ff9543389d7fcdab590978cd140470796e4bcfaf4931cdd29b99 | 2026-05-18T07:46:07.667878+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10=True; ready_for_1000=True |
| eval/real_user_rollout_gate_snapshot.json | True | 81e27cc60747c04ba6d95ccc41a2f2cd6effe8c2b349dfbd69974995e9954d14 | 2026-05-22T11:41:24.784350+00:00 | 100-real-user gate=False; max_recommended_real_users=10; blockers=['first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/public_self_serve_launch_gate_snapshot.json | True | e78d4d8c6bde7fe2ad3cfaba429c54e58177b1d850de8d118ddd55c16abf63d9 | 2026-05-22T11:05:40.170322+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['PyPI latest metadata does not match source version or required project URLs', 'PyPI fresh-install + MCP stdio canary snapshot is missing or failing', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/pypi_fresh_install_snapshot.json | True | d334b487e4da7c2523700f831afedb87a2eb378799752f2ec754fcaae3565d13 | 2026-05-22T11:01:05Z | PyPI fresh-install canary success=False; version=3.3.8 |
| eval/load_10_snapshot.json | True | ba59f7350f5b3cdb9078ddfe786524f00b3e1de7b384885e6297f7cb9c46a7c2 | 2026-05-18T07:45:06.621553+00:00 | logical load 10: passed=True; total_requests=59794; success_rate=1.0; p95_ms=0.6281427631620318; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | f19307704ed8df2c3b536b70b5cb4544bc07a375afa4ba9c213cdb3adc6149f4 | 2026-05-18T07:45:36.770025+00:00 | logical load 100: passed=True; total_requests=59981; success_rate=1.0; p95_ms=0.6004410097375512; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | 7a97f13045c6e54751de87963979fd47cedd19467b1b03c1f2c5f0f4aa703629 | 2026-05-18T07:46:06.931035+00:00 | logical load 1000: passed=True; total_requests=59947; success_rate=1.0; p95_ms=0.6051470059901476; model=asyncio_logical_users |
| pyproject.toml | True | 0defe018ec8a2ecc6a772aa49e4bafb93853f0e9d4b24605925af0b62f8b1154 | 2026-05-22T10:30:24Z | package version=3.3.8; scripts declared in project metadata |
| borg/__init__.py | True | 14a1cfcffc78976668925f8f06991459ba5aed9c3b6a8d558bf0e1ad6417c8e9 | 2026-05-22T10:30:28Z | runtime __version__=3.3.8; top-level check() delegates to search |
| PROJECT_STATUS.md | True | 3dd6b34789cb80255c2135ccea79bb88a608732bb8700d3a7e25c56dc797beff | 2026-05-22T11:01:45Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| GO_NO_GO_DECISION.md | True | b098e80fd7cda99c1ce448282f092f0f3b894e303d86566b6a81b83f7a110c30 | 2026-05-22T11:01:45Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |
| UAT_RESULTS.md | True | c62c172486470be070ecdf47e2e9f3a43c99a4899b49dd1a8b8dc5ce1268b0cf | 2026-05-22T11:01:45Z | prior local status/readiness narrative used as contextual evidence only, not external adoption proof |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real first-user install/rescue outcome has been recorded yet.<br>PyPI fresh-install canary is not green yet.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not publish/push/change repo visibility from this proof build.<br>Need one supervised dry run from clean Git clone by a non-author before claiming self-serve readiness. |
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

## Next action queue before supervised first user

| # | Action |
| --- | --- |
| 1 | Use source checkout only under live supervision and label it as a private proof, not public launch. |
| 2 | Create a fresh-clone runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 4 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 5 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 6 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
