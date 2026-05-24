# Borg public self-serve launch go/no-go

Generated: 2026-05-24T22:48:10.769056+00:00
Source version: `3.3.12`

Public self-serve launch: **NO-GO**
Controlled first-10 beta infrastructure: **NO-GO**
Max recommended real users now: **0**

## Hard rule

Public self-serve is GO only after PyPI/fresh-install/MCP/docs gates pass AND row-derived first-10 external-user evidence passes. Synthetic users and aggregate-only edits never count.

## Gate results

- `first_user_release`: `PASS`
- `pypi_latest`: `FAIL`
- `pypi_fresh_install_and_mcp_stdio`: `FAIL`
- `docs_claim_guard`: `PASS`
- `first_10_external_evidence`: `FAIL`

## Blockers

- PyPI latest metadata does not match source version or required project URLs
- PyPI fresh-install + MCP stdio canary snapshot is missing or failing
- first-10 external-user evidence has not passed: verified=0/10, real_users=0/10, installs=0/8, useful=0/6, critical_incidents=0/0

## Evidence artifacts

- `eval/public_self_serve_launch_gate_snapshot.json`
- `eval/first_10_user_scoreboard.json`
- `eval/pypi_fresh_install_snapshot.json`
- `eval/first_user_release_gate_snapshot.json`
