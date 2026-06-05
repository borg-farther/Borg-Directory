# Borg Proof Dashboard

Generated: `2026-06-05T10:24:14Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Source snapshot: `af152bb15ee998dbc091ff6bbbb88fd94b3968bb+dirty`

## Big top verdict

| Scope | Verdict | Why |
| --- | --- | --- |
| controlled first 10 beta | NO-GO | Controlled first-10 beta is blocked until these failed gates are green: PyPI latest package source/metadata alignment (package_source_changed_after_reference); served-runtime freshness |
| local release candidate | CONDITIONAL | Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence. |
| unattended git onboarding | NO-GO | No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes. |
| broad public launch | NO-GO | Public self-serve gate is blocked until PyPI latest/fresh-install/MCP, GitHub source-install, docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and first-10 external evidence exists. |

**Controlled first-10 beta only?** NO-GO — Do not invite controlled beta users until these failed gates are green: PyPI latest package source/metadata alignment (package_source_changed_after_reference); served-runtime freshness; Do not present as unattended public launch ready.; Keep first-10 evidence capture prepared, but blocked until package/release-control/ops evidence is green.

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
| served_runtime_freshness_gate | FAIL | SERVED_RUNTIME_FINGERPRINT_GATE | eval/served_runtime_fingerprint_snapshot.json |
| release_governance_gate | PASS | RELEASE_GOVERNANCE_BRANCH_PROTECTION_GATE | eval/release_governance_snapshot.json |
| release_controls_gate | FAIL | SERVED_RUNTIME_PLUS_RELEASE_GOVERNANCE | eval/real_user_rollout_gate_snapshot.json |
| self_service_ops_gate | PASS | SELF_SERVICE_OPS_GATE | eval/self_service_ops_gate_snapshot.json |
| first_10_privacy_security_incidents | 0 | ROW_DERIVED_EXTERNAL_USER_RISK | eval/first_10_user_scoreboard.json row-derived external-user evidence |
| ops_readiness_watchdog | PASS | OPS_PROOF_FRESHNESS_GATE | eval/ops_readiness_watchdog_snapshot.json |
| rollback_comms_drill | PASS | DRY_RUN_ROLLBACK_COMMS_DRILL | eval/rollback_comms_drill_snapshot.json |
| pypi_fresh_install_canary | PASS | PYPI_FRESH_INSTALL_CURRENT_VERSION | eval/pypi_fresh_install_snapshot.json |
| github_source_install_canary | PASS | GITHUB_SOURCE_FRESH_INSTALL_CURRENT_VERSION | eval/github_source_install_snapshot.json |
| github_source_green | PASS | STRICT_GITHUB_SOURCE_INSTALL_GATE | eval/github_source_install_snapshot.json; canonical_target=True; missing_results=[]; missing_mcp_tools=[] |
| github_source_gate_detail | `{"canonical_install_target": true, "checkout_import_leakage_passed": true, "commit_matches_recorded_expected": true, "exists": true, "expected_commit_is_sha": true, "expected_version": "3.3.18", "failed_count": 0, "failures": [], "freshness": {"age_hours": 0.012547761388888887, "failure_kind": null, "max_age_hours": 24.0, "passed": true}, "generated_at_utc": "2026-06-05T10:23:29Z", "install_source": "github_source", "install_target": "git+https://github.com/borg-farther/Borg-Directory.git@af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "install_target_commit": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "installed_file": "/tmp/borg-github-source-8prgqhmb/lib/python3.11/site-packages/borg/__init__.py", "mcp_server_info": {"name": "borg-mcp-server", "version": "3.3.18"}, "mcp_stdio_canary_passed": true, "missing_mcp_tools": [], "missing_required_results": [], "passed": true, "path": "eval/github_source_install_snapshot.json", "resolved_commit": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "source_commit_honesty": {"changed_paths_since_resolved": [], "dirty_paths": ["docs/20260517_BORG_100_REAL_USER_READINESS.md", "docs/BORG_PROOF_DASHBOARD.html", "docs/BORG_PROOF_DASHBOARD.md", "docs/COLD_START_TRUST_HARDENING.md", "docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md", "docs/SELF_SERVICE_OPS_READINESS_REPORT.md", "docs/public/impact/impact.json", "docs/public/proof-dashboard/index.html", "docs/public/status.json", "docs/public/value.json", "docs/status.json", "eval/borg_proof_dashboard.json", "eval/cold_start_trust_gate_snapshot.json", "eval/github_source_install_snapshot.json", "eval/ops_readiness_watchdog_snapshot.json", "eval/public_self_serve_launch_gate_snapshot.json", "eval/pypi_fresh_install_snapshot.json", "eval/real_user_rollout_gate_snapshot.json", "eval/release_governance_snapshot.json", "eval/rollback_comms_drill_snapshot.json", "eval/self_service_ops_gate_snapshot.json"], "head": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "non_generated_dirty_paths": [], "passed": true, "reason": "exact_head", "resolved_commit": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb"}, "source_resolution": {"commit_matches_expected": true, "detail": "installed VCS direct_url commit matches expected commit", "direct_url": {"url": "https://github.com/borg-farther/Borg-Directory.git", "vcs_info": {"commit_id": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "requested_revision": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "vcs": "git"}}, "expected_commit": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "expected_commit_is_sha": true, "passed": true, "requested_revision": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "resolved_commit": "af152bb15ee998dbc091ff6bbbb88fd94b3968bb", "vcs": "git"}, "source_resolution_passed": true, "version": "3.3.18"}` | STRICT_GITHUB_SOURCE_INSTALL_GATE_DETAIL | eval/public_self_serve_launch_gate.py github_source_install_check |
| pypi_package_current_gate | FAIL | PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE | eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json |
| source_version_consistency | pyproject=3.3.18 runtime=3.3.18 | REPO_SOURCE | pyproject.toml; borg/__init__.py |
| host_runtime_split_brain | FAIL | SERVED_RUNTIME_EVIDENCE | Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true. |
| load_gates | `{"10": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7294940995052457, "p99_ms": 0.8128765365108848, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:46:33.549678+00:00", "total_requests": 48934, "users_label": 10}, "100": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7360600866377354, "p99_ms": 0.9644317068159578, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:47:03.681996+00:00", "total_requests": 48942, "users_label": 100}, "1000": {"concurrency_model": "asyncio_logical_users", "exists": true, "p95_ms": 0.7110125618055462, "p99_ms": 0.773976217024028, "passed": true, "success_rate": 1.0, "timestamp": "2026-06-02T21:47:33.846766+00:00", "total_requests": 49978, "users_label": 1000}}` | LOGICAL_USERS_NOT_REAL_USERS | eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json |

## Evidence table

| Source file path | Exists | SHA256 | Freshness timestamp | Exact claim derived |
| --- | --- | --- | --- | --- |
| eval/first_user_release_gate_snapshot.json | True | 1a46e0d720645a0553914654a7ad170b404d586175f63a219dc1bd079e6b1c21 | 2026-06-02T10:01:26Z | first-user release gate all_pass=True |
| eval/uat_scoreboard_snapshot.json | True | 91609d7d1c36b321f4c08bd4ed9ee9d0c92346b843cbe3c61f1dda3d4f598406 | 2026-06-02T21:47:35.869382+00:00 | UAT synthetic_load_all_pass=True; real_user_100_all_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/gate_run_snapshot.json | True | 64506c28195ec35a14e633335085ea262e96eb9ea5aba75aec2d2303314be615 | 2026-06-02T21:47:35.821086+00:00 | gate run synthetic_load_all_pass=True; overall_100_real_user_pass=False; ready_for_10_logical_load=True; ready_for_1000_logical_load=True; not_real_user_or_public_beta_evidence=True |
| eval/real_user_rollout_gate_snapshot.json | True | 3ace6828005a04eb79832e5e30b3e3bcae7892d8e643e266b584496e09a18a19 | 2026-06-05T10:24:11.281527+00:00 | 100-real-user gate=False; max_recommended_real_users=0; blockers=['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', "served runtime borg_version '3.3.14' != source version '3.3.18'", "served runtime source_version '3.3.15' != source version '3.3.18'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/first_10_user_scoreboard.json | True | 232585546e34fc07459365e00123aa512098f215f7bcd6307d0bde9bb20813f0 | 2026-05-25T23:32:37Z | first-10 row evidence users=0; measured_savings={'rows_with_measured_value': 0, 'dead_ends_avoided_confirmed': 0, 'net_minutes_saved': 0.0, 'positive_minutes_saved': 0.0, 'negative_minutes_cost': 0.0, 'net_tokens_saved': 0, 'positive_tokens_saved': 0, 'negative_tokens_cost': 0, 'counterfactual_basis_counts': {}}; gate=BLOCKED |
| eval/public_self_serve_launch_gate_snapshot.json | True | f65f39e8d2214f71fe8c7aa4a70b4d7c3bf805958fc41bf89ea73dfd4929a625 | 2026-06-05T10:24:10.013190+00:00 | public self-serve gate=False; max_recommended_real_users=0; blockers=['package-impacting source/metadata changed after the immutable package reference tag', "served runtime borg_version '3.3.14' != source version '3.3.18'", "served runtime source_version '3.3.15' != source version '3.3.18'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0'] |
| eval/cold_start_trust_gate_snapshot.json | True | feefa7e04285bca0c61d7dde023fb197532e88f01927d69b62d7c89b231ca4fd | 2026-06-05T10:23:56.294485+00:00 | cold-start trust gate=True; blockers=[] |
| eval/self_service_ops_gate_snapshot.json | True | c8edd3174cc6f830b34e838ed2e35d1f11efee03e143e291a4d44afa8d771454 | 2026-06-05T10:23:59.069117+00:00 | self-service ops gate=True; blockers=[] |
| eval/ops_readiness_watchdog_snapshot.json | True | c828e824c64d803ab26f05d014e3b70191e86f4a97d2b00200d378d068e831c5 | 2026-06-05T10:24:14.052578+00:00 | ops readiness watchdog=True; blocker details live in eval/ops_readiness_watchdog_snapshot.json |
| eval/rollback_comms_drill_snapshot.json | True | d0922eb9d432f0037958cb11797b9e201409dcd01137e657a423b8290d205bba | 2026-06-05T10:23:58.989613+00:00 | rollback/comms drill=True; dry_run_only=True |
| eval/pypi_fresh_install_snapshot.json | True | ab30e0efd664867a910d695a1b9ef133bfd277f869efd93006b190a165724cc6 | 2026-06-05T10:23:36Z | PyPI fresh-install canary success=True; version=3.3.18 |
| eval/github_source_install_snapshot.json | True | 2b40b12b22c5f61edce928545e3bc28a6f976fce995832006d379bf954c64946 | 2026-06-05T10:23:29Z | GitHub source-install canary strict_gate=True; success=True; version=3.3.18; canonical_target=True; missing_required_results=[]; missing_mcp_tools=[] |
| eval/load_10_snapshot.json | True | ab6c0e1e52b1527fe988b0d84f01e243d3d8c30919dc41fc3559dd0257a2e4f7 | 2026-06-02T21:46:33.549678+00:00 | logical load 10: passed=True; total_requests=48934; success_rate=1.0; p95_ms=0.7294940995052457; model=asyncio_logical_users |
| eval/load_100_snapshot.json | True | 6a0a345a71bbb3f3a457da8eceffc10fcc377d0aeb4553f1005c3cbc22a07b7a | 2026-06-02T21:47:03.681996+00:00 | logical load 100: passed=True; total_requests=48942; success_rate=1.0; p95_ms=0.7360600866377354; model=asyncio_logical_users |
| eval/load_1000_snapshot.json | True | efd3c036fb2cfe1f6aa296f7f995070f6d4b569d4242ba1ebe416c86c92e4928 | 2026-06-02T21:47:33.846766+00:00 | logical load 1000: passed=True; total_requests=49978; success_rate=1.0; p95_ms=0.7110125618055462; model=asyncio_logical_users |
| pyproject.toml | True | 619ce855c989f498ce35d0b14017e9c2dd5328d69d8bd0896e351a63abe9cb0c | 2026-06-03T20:14:15Z | package version=3.3.18; scripts declared in project metadata |
| borg/__init__.py | True | cb5bcde2504e5803603db8df7807887df9cfdd101ddeab7c8cb65a80a5a5a4d5 | 2026-06-03T20:14:15Z | runtime __version__=3.3.18; top-level check() delegates to search |

## Blockers

| Category | Blockers |
| --- | --- |
| user affecting | No real external first-user install/rescue outcome has been recorded yet.<br>PyPI package gate is not green for the current source revision yet.<br>GitHub source-install canary is green: git-based install, CLI/API, and local stdio MCP work from an isolated non-repo environment.<br>Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.<br>Served runtime freshness gate is not green yet.<br>Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.<br>Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.<br>Ops watchdog is green: proof snapshots and public status are internally consistent.<br>Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention. |
| investor affecting | Verified external users: 0 based on available hard evidence.<br>Local/logical load gates prove engineering readiness, not market adoption or retention. |
| security privacy | Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.<br>Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script. |
| release hygiene | Do not change repo visibility from this proof build.<br>Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness. |
| evidence gaps | No Borg analytics export proving active contributors or consumers was found.<br>No first-10-user scoreboard with real outcomes exists yet.<br>Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.<br>100-real-user gate remains blocked: ['PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version', "served runtime borg_version '3.3.14' != source version '3.3.18'", "served runtime source_version '3.3.15' != source version '3.3.18'", 'served runtime version_matches_source is not true', 'served runtime reload_status is not loaded_code_matches_source_behavior', 'first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0']<br>Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.<br>Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness. |

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
| 1 | Do not invite controlled first-10 testers yet: `agent-borg==3.3.18` installs and runs, but package source/metadata alignment is blocked by `package_source_changed_after_reference`; fix the source/proof state or publish a new immutable version after `3.3.18` before tester use. |
| 2 | Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers. |
| 3 | Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails. |
| 4 | Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields. |
| 5 | If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO. |
| 6 | Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN. |
| 7 | Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction. |
