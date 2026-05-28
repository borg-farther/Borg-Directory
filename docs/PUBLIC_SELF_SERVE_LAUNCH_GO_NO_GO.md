# Borg public self-serve launch go/no-go

Generated: 2026-05-28T21:27:07.968009+00:00
Source version: `3.3.15`

Public self-serve launch: **NO-GO**
Controlled first-10 beta infrastructure: **GO**
Max recommended real users now: **10**

## Hard rule

Public self-serve is GO only after PyPI/fresh-install/MCP/docs/cold-start-trust/self-service-ops gates pass AND row-derived first-10 external-user evidence passes. Synthetic users and aggregate-only edits never count.

## Gate results

- `first_user_release`: `PASS`
- `pypi_latest`: `PASS`
- `pypi_fresh_install_and_mcp_stdio`: `PASS`
- `cold_start_trust_hardening`: `PASS`
- `self_service_ops_readiness`: `PASS`
- `docs_claim_guard`: `PASS`
- `privacy_security_incident_pause`: `PASS`
- `first_10_external_evidence`: `FAIL`

## Blockers

- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Evidence artifacts

- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
- `eval/cold_start_trust_gate_snapshot.json`
- `eval/self_service_ops_gate_snapshot.json`
- `eval/ops_readiness_watchdog_snapshot.json`
