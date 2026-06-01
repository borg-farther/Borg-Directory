# Borg public self-serve launch go/no-go

Generated: 2026-06-01T08:59:33.584180+00:00
Source version: `3.3.15`

Public self-serve launch: **NO-GO**
Controlled first-10 beta infrastructure: **NO-GO**
Max recommended real users now: **0**

## Hard rule

Public self-serve is GO only after PyPI/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/watchdog gates pass AND row-derived first-10 external-user evidence passes. Synthetic users and aggregate-only edits never count.

## Gate results

- `first_user_release`: `PASS`
- `pypi_latest`: `FAIL`
- `pypi_fresh_install_and_mcp_stdio`: `PASS`
- `cold_start_trust_hardening`: `PASS`
- `served_runtime_freshness`: `FAIL`
- `release_governance`: `FAIL`
- `self_service_ops_readiness`: `PASS`
- `ops_readiness_watchdog`: `PASS`
- `docs_claim_guard`: `PASS`
- `privacy_security_incident_pause`: `PASS`
- `first_10_external_evidence`: `FAIL`

## Blockers

- PyPI latest metadata is stale: same-version release upload predates current source revision
- served runtime borg_version '3.3.14' != source version '3.3.15'
- served runtime version_matches_source is not true
- served runtime reload_status is not loaded_code_matches_source_behavior
- main branch is not protected
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Evidence artifacts

- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
- `eval/cold_start_trust_gate_snapshot.json`
- `eval/served_runtime_fingerprint_snapshot.json`
- `eval/release_governance_snapshot.json`
- `eval/self_service_ops_gate_snapshot.json`
- `eval/ops_readiness_watchdog_snapshot.json`
