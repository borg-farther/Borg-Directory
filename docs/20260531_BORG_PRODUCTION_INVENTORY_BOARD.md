# Borg production inventory board

Generated: `2026-06-04T19:53:50Z`
Repo: `https://github.com/borg-farther/Borg-Directory`
Branch/head: `ab/git-source-self-service-proof-20260604` / `16281fa2f0f17ec852f1471f7da4ec6295349d00`
Working tree dirty: `True`
Version: pyproject `3.3.18` / borg `__version__` `3.3.18`

## Task outline / decomposition

- reconstruct promised production features from docs/session evidence
- separate proof lanes: GitHub source install, PyPI package, served runtime, governance, ops, external users, federated protocol, recursive learning, measured value
- challenge readiness claims against fail-closed gates and row-derived evidence
- produce durable docs and machine-readable outstanding inventory
- add regression tests so future edits cannot collapse the boundaries

## Bottom-line verdicts

- GitHub source install: `NO_GO`
- controlled first-10 beta: `NO_GO`
- broad public self-serve: `NO_GO`
- 100 real users: `NO_GO`
- current source/hardening branch: `IN_PROGRESS`
- published package/local stdio: `NO_GO`
- served runtime freshness: `NO_GO`
- remote MCP/marketplace distribution: `NO_GO`
- global/federated learning protocol: `GO_PROTOCOL_ONLY`
- recursive collective learning mechanism: `GO_INTERNAL_ONLY`
- recursive pack optimizer: `GO_INTERNAL_MANUAL_ONLY`
- Google/God-tier measured external lift: `NO_GO`

## Evidence summary

- first-10 external rows: `{'verified_external_users': 0, 'real_users': 0, 'install_successes': 0, 'useful_rescue_moments': 0, 'critical_privacy_security_failures': 0, 'repeat_use_within_7_days': 0}`
- GitHub source install + commit binding: `False` resolved=`71213e1c7b3167905d3afc927da6706798fbe400` expected_sha=`True` matches_expected=`True`
- PyPI fresh install + stdio MCP: `True`
- first-user release gate: `True`
- cold-start trust: `True`
- served runtime freshness: `False`
- release governance: `True`
- self-service ops: `True`
- ops watchdog: `True`
- rollback drill: `True`
- federated protocol gate: `True`
- collective loop primitives: `True`
- pack optimizer local/manual gate: `True`
- optimality ceiling: `2.0`

## Component inventory

### source_package_cli_stdio — source, PyPI package, CLI, generated rules, and local stdio MCP

Status: `IN_PROGRESS`

Evidence:
- `pyproject.toml and borg/__init__.py`
- `eval/first_user_release_gate_snapshot.json`
- `eval/pypi_fresh_install_snapshot.json`
Done/proven:
- source versions match: True (3.3.18)
- PyPI latest metadata/current-source gate green: False
- PyPI fresh-install/stdout MCP canary green: True
- first-user release gate green: True
Blockers:
- PyPI latest metadata gate is not green for the current source revision
- working tree is dirty/unshipped; current hardening branch is not committed/pushed/CI-proven
Outstanding:
- publish a new immutable version when source is ahead of PyPI
- rerun full proof on the final branch head
- commit/push and watch CI before claiming shipped
Challenge:
- A clean PyPI canary proves installed package behavior, not source revisions that landed after the wheel upload or a long-lived served process.

### github_source_install_cli_api_stdio — GitHub source install, direct_url commit binding, CLI/API, generated rules, OpenClaw, and local stdio MCP

Status: `NO_GO`

Evidence:
- `eval/run_github_source_install_canary.py`
- `eval/github_source_install_snapshot.json`
- `pip direct_url.json vcs_info.commit_id`
- `eval/public_self_serve_launch_gate.py github_source_install_check`
Done/proven:
- snapshot exists: True
- canonical GitHub target: True
- resolved commit: 71213e1c7b3167905d3afc927da6706798fbe400
- expected commit is 40-hex SHA: True
- resolved commit matches recorded expected: True
- checkout import leakage check passed: True
- failed command count: 0
Blockers:
- GitHub source-install proof is not current/strict for this working tree
- source honesty: {'passed': False, 'resolved_commit': '71213e1c7b3167905d3afc927da6706798fbe400', 'head': '16281fa2f0f17ec852f1471f7da4ec6295349d00', 'dirty_paths': ['.github/workflows/self-service-watchdog.yml', 'AGENTS.md', 'README.md', 'SUPPORT.md', 'docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md', 'docs/20260531_BORG_PRODUCTION_INVENTORY_BOARD.md', 'docs/CHANNELS_AND_INSTALL_METHODS.md', 'docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md', 'docs/READINESS.md', 'docs/README.md', 'docs/ROADMAP.md', 'docs/TRYING_BORG.md', 'docs/VALUE_COMMUNICATION_DASHBOARD.html', 'docs/VALUE_COMMUNICATION_DASHBOARD.md', 'eval/ops_readiness_watchdog.py', 'eval/production_inventory_board.py', 'eval/production_inventory_board_snapshot.json', 'eval/public_self_serve_launch_gate.py', 'eval/real_user_rollout_gate.py', 'eval/run_github_source_install_canary.py', 'eval/run_pypi_fresh_install_canary.py', 'eval/tests/test_production_inventory_board.py', 'eval/tests/test_real_user_rollout_gate.py', 'llms.txt', 'tests/packaging/test_github_source_install_canary_contract.py', 'tests/packaging/test_public_presentation_contract.py', 'tests/readiness/test_ops_readiness_watchdog.py', 'tests/readiness/test_public_self_serve_launch_gate.py'], 'non_generated_dirty_paths': ['.github/workflows/self-service-watchdog.yml', 'AGENTS.md', 'README.md', 'SUPPORT.md', 'docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md', 'docs/CHANNELS_AND_INSTALL_METHODS.md', 'docs/READINESS.md', 'docs/README.md', 'docs/ROADMAP.md', 'docs/TRYING_BORG.md', 'docs/VALUE_COMMUNICATION_DASHBOARD.html', 'docs/VALUE_COMMUNICATION_DASHBOARD.md', 'eval/ops_readiness_watchdog.py', 'eval/production_inventory_board.py', 'eval/public_self_serve_launch_gate.py', 'eval/real_user_rollout_gate.py', 'eval/run_github_source_install_canary.py', 'eval/run_pypi_fresh_install_canary.py', 'eval/tests/test_production_inventory_board.py', 'eval/tests/test_real_user_rollout_gate.py', 'llms.txt', 'tests/packaging/test_github_source_install_canary_contract.py', 'tests/packaging/test_public_presentation_contract.py', 'tests/readiness/test_ops_readiness_watchdog.py', 'tests/readiness/test_public_self_serve_launch_gate.py'], 'changed_paths_since_resolved': [], 'reason': 'non_generated_dirty_paths'}
- missing required results: []
- failures: []
Outstanding:
- rerun exact-SHA GitHub source canary after final commit
- refresh public/dashboard/watchdog artifacts
- watch exact-head GitHub Actions before merge
Challenge:
- A git+https install URL is not proof by itself; pip direct_url must resolve to the expected PR SHA and runtime commands must execute outside the checkout.

### security_hardening_current_branch — current hardening branch: pack safety, pickle removal, HTTP/MCP hardening, docs truth gates

Status: `IN_PROGRESS`

Evidence:
- `git status --short`
- `tests/security`
- `tests/mcp`
- `tests/readiness`
- `eval/tests`
Done/proven:
- pack ingestion/export hardening is implemented in working tree
- embedding cache pickle load has been replaced with safe JSON schema in working tree
- HTTP MCP auth/body/schema/read-only hardening is implemented in working tree
- served-runtime and release-governance gates are implemented in working tree
Blockers:
- not yet full-suite/static/security proven after latest dashboard/inventory changes
- not committed or pushed
Outstanding:
- run focused and full pytest
- run security_gate_check.py
- regenerate dashboard/status artifacts
- commit/push only after proof is green or report blockers
Challenge:
- Regression tests for narrow fixes are not equivalent to a release proof over every changed surface.

### served_runtime — served/Hermes MCP runtime freshness

Status: `NO_GO`

Evidence:
- `eval/served_runtime_fingerprint_snapshot.json`
- `borg_runtime_fingerprint MCP canary`
Done/proven:
- snapshot captured: borg_version=3.3.14, source_version=3.3.15
Blockers:
- served runtime borg_version '3.3.14' != source version '3.3.18'
- served runtime source_version '3.3.15' != source version '3.3.18'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
Outstanding:
- operator-approved reload/cutover
- recapture fingerprint through the exact served channel
- rerun behavior canaries after cutover
Challenge:
- Local source, PyPI, and fresh stdio MCP can all be green while a long-lived served process is stale.

### release_governance — GitHub release governance and main-branch protection

Status: `GO`

Evidence:
- `eval/release_governance_snapshot.json`
- `GitHub branch API payload for main`
Done/proven:
- protected=True
- observed checks=['dependency-audit', 'old-account-reference', 'ops-readiness-watchdog', 'policy-check', 'secret-scan', 'static-security', 'test (3.10)', 'test (3.11)', 'test (3.12)']
Outstanding:
- maintain release-governance snapshot freshness
- keep required CI/security/watchdog/account-firewall checks exact
- keep CODEOWNERS validation green
Challenge:
- Green local checks do not matter if main can bypass the release ritual.

### self_service_ops_watchdog — self-service ops, rollback/comms, support intake, watchdog freshness

Status: `GO`

Evidence:
- `eval/self_service_ops_gate_snapshot.json`
- `eval/ops_readiness_watchdog_snapshot.json`
- `eval/rollback_comms_drill_snapshot.json`
Done/proven:
- watchdog passed: True
Outstanding:
- refresh rollback/comms drill
- rerun self-service ops gate
- keep watchdog under freshness SLA
Challenge:
- Ops docs are not readiness unless the live snapshots are fresh and fail closed.

### first_10_external_evidence — first-10 consented external-user evidence

Status: `NO_GO`

Evidence:
- `eval/first_10_user_scoreboard.json`
- `eval/first_10_evidence.py`
Done/proven:
- row_count=0
- counts={'verified_external_users': 0, 'real_users': 0, 'install_successes': 0, 'useful_rescue_moments': 0, 'critical_privacy_security_failures': 0, 'repeat_use_within_7_days': 0}
Blockers:
- first-10 evidence not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0
Outstanding:
- recruit 10 consented external users
- record installs, useful rescues, repeated use, and negative outcomes
- keep critical privacy/security incidents at 0
Challenge:
- Synthetic load users, internal dogfood, and anecdotes never count as first-10 external evidence.

### controlled_first_10_beta — controlled first-10 beta readiness

Status: `NO_GO`

Evidence:
- `eval/public_self_serve_launch_gate.py --no-write`
- `eval/real_user_rollout_gate.py --no-write`
Blockers:
- served runtime borg_version '3.3.14' != source version '3.3.18'
- served runtime source_version '3.3.15' != source version '3.3.18'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
Outstanding:
- served runtime fresh
- branch protection/release governance green
- ops snapshots fresh
- cap at 10 until first-10 rows pass
Challenge:
- Earlier conditional GO is revoked when release controls or ops freshness fail.

### public_self_serve — broad public self-serve launch

Status: `NO_GO`

Evidence:
- `eval/public_self_serve_launch_gate.py`
- `docs/public/status.json`
- `eval/first_10_user_scoreboard.json`
Blockers:
- first-10 evidence not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0
- served runtime borg_version '3.3.14' != source version '3.3.18'
- served runtime source_version '3.3.15' != source version '3.3.18'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
Outstanding:
- pass first-10 row-derived evidence
- keep package/served-runtime/governance/ops/docs gates green
- regenerate public status/dashboard from current snapshots
Challenge:
- A polished dashboard is dangerous if it hides the first-10 or served-runtime blockers.

### hundred_user_rollout — 25 -> 50 -> 100 real-user staged rollout

Status: `NO_GO`

Evidence:
- `eval/real_user_rollout_gate.py`
- `docs/20260517_BORG_100_REAL_USER_READINESS.md`
Blockers:
- 100-user rollout is downstream of first-10 evidence and public self-serve gate
Outstanding:
- 25-user stage
- 50-user repeat-use/retention stage
- 100-user support/incident proof
Challenge:
- 100 synthetic/load users are not 100 real users.

### remote_global_federated_protocol — remote/global/federated learning protocol

Status: `GO_PROTOCOL_ONLY`

Evidence:
- `eval/run_federated_learning_gate.py`
- `eval/federated_learning_gate_snapshot.json`
- `tests/security/test_federated_learning_gate.py`
Done/proven:
- signed hosted-registry manifest sync
- hash/size verification before import
- replay/tamper/key/channel/expiry rejection
- tombstone-first revocation convergence
Outstanding:
- production hosted registry ops
- monitoring and revocation SLO telemetry
- backup/restore and key-rotation drills
- transparency-log anchoring
Challenge:
- Protocol GO is not hosted-registry production ops, public self-serve, or measured value proof.

### collective_recursive_learning_loop — outcome-grounded collective/recursive learning mechanism

Status: `GO_INTERNAL_ONLY`

Evidence:
- `eval/run_collective_intelligence_loop_gate.py`
- `eval/collective_intelligence_loop_gate.json`
- `eval/federated_learning_optimality_audit.json`
Done/proven:
- intervention IDs and signed outcome receipts
- verified helpful/unhelpful outcome storage
- dedupe/generalization clusters
- registry-computed quorum from signed receipts
- sanitized atom candidate/promotion path
- unified scored retrieval with negative evidence
Outstanding:
- prove real external lift
- run 3-condition no-Borg/empty-Borg/seeded-Borg evaluation
- operate production registry
- abuse/quarantine workflow and transparency anchoring
Challenge:
- Internal synthetic loop primitives are real, but they do not prove agents improve in the wild.

### recursive_pack_optimizer — recursive/local pack optimizer and learning-to-improve packs

Status: `GO_INTERNAL_ONLY`

Evidence:
- `eval/pack_optimizer_gate_snapshot.json`
- `borg/core/pack_optimizer.py`
- `borg/core/pack_optimizer_rejections.py`
Done/proven:
- local-only candidate generation
- privacy/prompt-injection scans
- manual-review eligibility
- rejected-edit memory
Outstanding:
- wire into a supervised recurring improvement lane
- run cross-agent A/B before accepting edits
- keep global promotion disabled until first-10 and registry ops gates pass
Challenge:
- Recursive optimization must stay evidence-bound; autonomous global edits before external proof would amplify mistakes.

### google_tier_measured_lift — Google/God-tier measured utility and learning optimality

Status: `NO_GO`

Evidence:
- `eval/federated_learning_optimality_audit.json`
- `eval/first_10_user_scoreboard.json`
- `docs/20260526-2230_MAX_VALUE_COLLECTIVE_INTELLIGENCE_LOOP.md`
Done/proven:
- optimality scores={'effective_collective_learning': 6.0, 'external_truth_grounding': 1.0, 'overall_optimality_ceiling': 2.0, 'proof_packet_richness': 10.0, 'protocol_security': 9.0, 'routing_value_speed': 6.0, 'signal_quality': 4.0}
Blockers:
- Collect consented first-10 external outcome rows with measured minutes/tokens/dead-ends impact; internal/synthetic gates must not count.
- Pass row-derived first-10 public-package evidence: 10 real users, 8 installs, 6 useful rescues, 0 critical privacy/security incidents.
- Run the 3-condition knowledge-system evaluation: no Borg, empty Borg scaffold, seeded Borg knowledge; report pure knowledge lift separately.
- Operate a production hosted registry with monitoring, key rotation, backup/restore, incident response, and revocation SLO telemetry.
- Add transparency-log anchoring before high-trust public federation claims.
Outstanding:
- measured external outcomes
- statistically honest counterfactual evaluation
- repeat-use and negative-guidance analysis
Challenge:
- Strong protocol/security scores can coexist with a low optimality ceiling when external truth grounding is 0-1/10.

### marketplace_remote_distribution — marketplaces, remote MCP listings, and public distribution channels

Status: `NO_GO`

Evidence:
- `deploy/smithery/smithery.yaml`
- `docs/ROADMAP.md`
- `docs/20260528_BORG_PRODUCTION_READY_FINAL_TODO.md`
Blockers:
- served remote MCP/runtime freshness is not green
- no production hosted registry ops proof
Outstanding:
- keep Smithery/local stdio draft honest
- remote HTTP auth/rate-limit/audit-redaction proof
- served-runtime fingerprint for the listed channel
Challenge:
- Distribution breadth is not value; premature listings multiply support and trust failures.

## Outstanding production work, ordered

### P0 — Finish and prove the current hardening branch

Why: Security/runtime/governance changes exist in the working tree but are not shipped or full-suite proven.

Acceptance:
- focused tests green
- full pytest/static/security gates green
- dashboard/status regenerated
- commit/push/CI watched

### P0 — Refresh served runtime through operator-approved cutover

Why: Current served fingerprint says 3.3.14 while source targets 3.3.18.

Acceptance:
- served borg_version == source_version == PyPI latest
- runtime hash/path/schema canary captured
- behavior canaries pass

### P1 — Maintain release-governance freshness

Why: Current GitHub main release-governance proof is green; keep the snapshot fresh and exact-check policy enforced through PR/merge/tag.

Acceptance:
- release_governance_gate passes
- required checks remain exact
- CODEOWNERS review remains required
- no bypass allowances appear

### P1 — Maintain ops/watchdog/rollback readiness freshness

Why: Self-service ops, watchdog, and rollback/comms proof are controlled-beta prerequisites; current gate state is green.

Acceptance:
- rollback drill fresh
- self-service ops gate passes
- watchdog passes with freshness SLA

### P0 — Run first-10 external beta evidence collection

Why: Public self-serve, 100 users, and measured lift are all blocked at 0/10 external rows.

Acceptance:
- 10 verified external users
- 8 installs
- 6 useful rescues
- 0 critical privacy/security incidents
- negative rows retained

### P0 — Regenerate proof dashboard/public status from current gates

Why: Generated snapshots/status must reflect served-runtime, release-governance, and ops blockers, not older conditional-GO language.

Acceptance:
- public gate snapshot current
- rollout snapshot current
- borg proof dashboard rebuilt
- dashboard lint passes

### P1 — Operate production federated registry

Why: Federated protocol is green, but hosted ops are still not production-proven.

Acceptance:
- monitoring
- backups
- restore drill
- key rotation
- revocation telemetry
- abuse/quarantine workflow
- transparency-log plan

### P1 — Graduate recursive optimizer from local/manual to evidence-backed supervised loop

Why: Pack optimizer is local/manual only; autonomous/global promotion must wait for external proof and ops controls.

Acceptance:
- scheduled supervised lane
- A/B comparison
- manual approval
- negative-evidence rejection memory
- no global promotion without first-10 + registry gates

### P1 — Cross-platform first-user matrix

Why: Linux PyPI canary is strong but not enough for broad self-serve.

Acceptance:
- Linux/macOS/Windows
- Python 3.10/3.11/3.12
- pipx and pip
- multiple MCP hosts

### P1 — Measured value experiment

Why: Google-tier claims require counterfactual evidence, not mechanism proof.

Acceptance:
- no Borg vs empty Borg vs seeded Borg
- minutes/tokens/dead-ends measured
- repeat use
- false-positive/NO_CONFIDENT_MATCH analysis

## Final reflective challenge pass

- Could GitHub source proof alone justify public readiness? No: it proves one install channel only; PyPI/current-source, served runtime, governance, ops, and row-derived users are separate gates.
- Could package proof alone justify controlled beta? No: current release controls add served-runtime freshness, release-governance freshness, and ops freshness; any red/stale required gate blocks beta.
- Could protocol GO mean federated learning is production-ready? No: it proves signed sync/revocation mechanics, not hosted operations or public utility.
- Could internal outcome receipts prove recursive learning is ready? Only as internal primitives; external lift and autonomous promotion remain blocked.
- Could synthetic load tests stand in for users? No: first-10 row-derived evidence is 0/10 and explicitly blocks public/100-user claims.
- Could a dashboard hide these blockers? It must not; stale generated artifacts are themselves blockers until rebuilt from current gates.

## Current blocker hierarchy

1. GitHub source-install exact-SHA proof is stale/missing/failing for the current working tree
2. PyPI package-current/source-alignment proof is not green
3. served runtime stale or not proven current
4. current hardening branch unshipped/full-proof pending
5. first-10 external evidence 0/10
6. public self-serve, 100-user, marketplace, measured-lift claims blocked until above gates pass

## Hard boundary

The global/federated and recursive learning mechanisms have real internal/protocol proof, but they are not production-global value proof. Public production still requires served-runtime freshness, release governance, fresh ops readiness, first-10 external rows, and measured outcomes.
