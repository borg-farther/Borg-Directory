# Borg self-service operations readiness

Borg's package path may enter the first external-user evidence cohort only after the current release technical gates and operations gates pass for the same version. This document defines the self-service ops layer: bad-answer intake, install/MCP support, first-10 evidence intake, support/SLA boundaries, rollback/comms drill, and watchdog automation.

## Current boundary

- Controlled first-10 public-package beta: blocked until `eval/public_self_serve_launch_gate.py` says `ready_for_controlled_first_10_beta=true` for the current release version.
- Broad public self-serve: NO-GO until row-derived first-10 external-user evidence passes.
- Served remote MCP/runtime: separate NO-GO until operator-supervised runtime fingerprint and canary prove the served process is current.

## Required public paths

- Bad first answer: `.github/ISSUE_TEMPLATE/bad-answer.yml`
- Source-channel smoke feedback: `.github/ISSUE_TEMPLATE/source-smoke-feedback.yml`
- First-10 waitlist/request: `.github/ISSUE_TEMPLATE/first-10-request.yml`
- First-10 evidence row: `.github/ISSUE_TEMPLATE/first-10-evidence.yml`
- Validated candidate importer: `eval/first_10_issue_import.py` plus `.github/workflows/first-10-evidence-candidate.yml`
- Install/MCP support: `.github/ISSUE_TEMPLATE/install-mcp-support.yml`
- Support policy: `SUPPORT.md`
- Security/privacy escalation: `SECURITY.md`
- Rollback/comms: `docs/ROLLBACK_AND_COMMS_RUNBOOK.md`

## Bad-answer recovery path

A bad first answer is trust erosion. The shipped durable paths are:

- MCP/agent: `borg_record_failure(error_pattern=..., pack_id=..., phase=..., approach=..., outcome="failure")`
- CLI: `borg feedback-v3 --pack <pack> --success no --notes <redacted summary>`
- Human report: `.github/ISSUE_TEMPLATE/bad-answer.yml`
- Evidence report when part of beta: `.github/ISSUE_TEMPLATE/first-10-evidence.yml`

The ops gate blocks nonexistent helper names and requires the GitHub intake template to capture version, surface, sanitized input, ACTION / STOP / VERIFY output, confidence block, expected guidance, actual wrong guidance, reproduction command, severity, and privacy confirmation.

## Support and SLA boundary

`SUPPORT.md` defines the first-10 beta support window, P0/P1/P2 severity levels, target triage times, pause criteria, privacy/security escalation, and what counts as maintainer handholding. Rows that require private maintainer debugging do not count as clean self-service proof.

## Rollback/comms drill

`python eval/rollback_comms_drill.py` performs a dry run with no PyPI, service, or data mutation. The dry run checks for:

- pause first-10 invites;
- PyPI bad-release yank/pin response;
- operator-supervised served MCP rollback;
- bad guidance disable path;
- public status update;
- user notification template.

## Watchdog automation

`.github/workflows/self-service-watchdog.yml` runs on pull request, push to main, schedule, and manual dispatch. It checks package proof, cold-start trust, public launch fail-closed state, proof dashboard lint, self-service ops readiness, and stale snapshot consistency.

## Machine gates

- `python eval/self_service_ops_gate.py`
- `python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker first_10_external_evidence --require-ci-schedule`
- `python eval/public_self_serve_launch_gate.py --no-write`
- `python scripts/borg_proof_dashboard_lint.py`

## Production rule

If the ops gate fails, controlled first-10 must pause. If first-10 row-derived evidence is absent, broad public self-serve remains NO-GO even when the ops gate passes.
