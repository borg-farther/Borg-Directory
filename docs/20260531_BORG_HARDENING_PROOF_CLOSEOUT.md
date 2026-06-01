# Borg hardening proof closeout — 2026-05-31

Historical/internal — not current product documentation. This closeout records the hardening branch proof state and blockers for operators; public launch truth remains the generated dashboard/status artifacts.

## Executive verdict

- Source/hardening branch proof stack: **GREEN**.
- Published package proof: **HISTORICAL ONLY** for the earlier local package/stdio evidence; current public status is red until a new immutable version is published after the current source revision and freshly canaried.
- Served/Hermes MCP runtime: **NO-GO** until operator-supervised runtime cutover proves loaded code matches source/package.
- Controlled first-10 beta: **NO-GO** while package provenance, served runtime freshness, release governance, and first-10 evidence are red.
- Broad public self-serve: **NO-GO** until served runtime, release governance, ops/watchdog, docs, and row-derived first-10 external evidence all pass.
- 100 real users: **NO-GO** until first-10 evidence passes and rollout gate advances.

This document intentionally separates code/proof health from production launch authorization.

## What changed

- Added served-runtime freshness and release-governance gates to public self-serve and real-user rollout decisions.
- Added a production inventory board generator and machine snapshot.
- Hardened public status/dashboard wording so package proof cannot imply hosted/public readiness.
- Hardened ops watchdog release-control-blocked mode so only known package, release-control, and first-10 evidence blockers are allowed; unrelated blockers fail closed.
- Reconciled active docs and public proof artifacts to remove stale public/beta overclaims while preserving honest NO-GO blockers.
- Added/updated regressions for public gate, real-user rollout, release governance, served runtime, ops watchdog, proof dashboard, production inventory board, public presentation contract, and related source hardening.

## Regenerated artifacts

- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/real_user_rollout_gate_snapshot.json`
- `eval/ops_readiness_watchdog_snapshot.json`
- `eval/production_inventory_board_snapshot.json`
- `eval/borg_proof_dashboard.json`
- `docs/BORG_PROOF_DASHBOARD.md`
- `docs/BORG_PROOF_DASHBOARD.html`
- `docs/public/proof-dashboard/index.html`
- `docs/public/status.json`
- `docs/public/value.json`
- `docs/public/impact/impact.json`
- `docs/20260531_BORG_PRODUCTION_INVENTORY_BOARD.md`

## Exact proof commands and results

### Targeted readiness/docs/watchdog proof

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  eval/tests/test_borg_proof_dashboard.py \
  eval/tests/test_release_governance_gate.py \
  eval/tests/test_served_runtime_gate.py \
  eval/tests/test_real_user_rollout_gate.py \
  eval/tests/test_production_inventory_board.py \
  tests/readiness/test_public_self_serve_launch_gate.py \
  tests/readiness/test_ops_readiness_watchdog.py \
  tests/packaging/test_public_presentation_contract.py \
  --tb=short
```

Result:

```text
74 passed in 0.95s
```

### Broader hardening suite

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/security \
  tests/core \
  tests/mcp \
  tests/packaging \
  tests/readiness \
  tests/optimizer \
  eval/tests \
  --tb=short
```

Result:

```text
1678 passed, 37 skipped, 1 xfailed, 44 warnings in 92.05s
```

### Full pytest

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q --tb=short
```

Result:

```text
2506 passed, 40 skipped, 4 xfailed, 1 xpassed, 44 warnings in 164.52s
```

### Security/static/proof gates

Commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/security_gate_check.py
PYTHONDONTWRITEBYTECODE=1 python -m compileall -q borg eval scripts tests
git diff --check
PYTHONDONTWRITEBYTECODE=1 python scripts/borg_proof_dashboard_lint.py
PYTHONDONTWRITEBYTECODE=1 python eval/run_readiness_gates.py --synthetic-only
```

Results:

```text
PASS: Borg security hardening policy gate
compileall passed
git diff --check passed
PASS: Borg proof dashboard lint
ready_for_10_logical_load=true
ready_for_100_logical_load=true
ready_for_1000_logical_load=true
synthetic_load_all_pass=true
ready_for_10_controlled_real_users=false
ready_for_100_real_external_users=false
max_recommended_real_users_now=0
overall_100_real_user_pass=false
```

### Public/real-user fail-closed gate state

Commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/public_self_serve_launch_gate.py
PYTHONDONTWRITEBYTECODE=1 python eval/real_user_rollout_gate.py
PYTHONDONTWRITEBYTECODE=1 python eval/ops_readiness_watchdog.py \
  --mode pr \
  --json \
  --no-write \
  --max-snapshot-age-hours 24 \
  --allow-public-blocker release_controls_or_first_10_evidence \
  --require-ci-schedule
```

Results:

```text
public_self_serve_launch: ready_for_controlled_first_10_beta=false, ready_for_public_self_serve_launch=false, max_recommended_real_users_now=0
real_user_rollout: ready_for_10_controlled_beta=false, ready_for_100_real_users=false, max_recommended_real_users_now=0
ops_readiness_watchdog: passed=true while preserving NO-GO public/controlled rollout state
```

## Current machine-readiness blockers

These are still real and must not be papered over by local/source tests:

1. `served runtime borg_version '3.3.14' != source version '3.3.15'`
2. `served runtime version_matches_source is not true`
3. `served runtime reload_status is not loaded_code_matches_source_behavior`
4. `main branch is not protected`
5. `first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0`

## Snapshot-derived status

- `docs_claim_guard.passed=true`
- `ops_readiness_watchdog.passed=true`
- `self_service_ops_gate.passed=true`
- `served_runtime_freshness_gate=FAIL`
- `release_governance_gate=FAIL`
- `verified_external_users=0`
- `max_recommended_real_users_now=0`
- `docs/public/status.json.state="NO-GO public self-serve; source/local release-candidate only"`

## Remaining uncertainties / operator actions

- Served runtime cutover requires operator-supervised reload/cutover proof. Agents must not restart, kill, or signal Hermes/gateway processes.
- Branch protection must be enabled/verified on GitHub `main` with required checks/CODEOWNERS policy as appropriate.
- First-10 evidence must come from consented external-user rows; synthetic/load/internal proof does not count.
- CI on any pushed PR/head SHA must still be checked separately; local proof does not prove GitHub Actions on the pushed commit.

## Bottom line

The hardening branch now has regression-backed source proof and generated readiness artifacts. It is ready for PR review as a hardening/release-control change, not as a claim that Borg is public-production ready.
