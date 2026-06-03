# Borg self-service operations readiness

Generated: `2026-06-03T20:33:05.124064+00:00`
Verdict: **PASS**

## Scope

This gate verifies the support, bad-answer intake, first-10 evidence intake, rollback/comms drill, and watchdog automation required before Borg invites controlled first-10 testers. It does not authorize broad public self-serve; that remains row-derived external-user gated.

## Policy

Ops readiness is necessary but not sufficient for controlled first-10; package provenance, served-runtime freshness, release governance, ops/watchdog freshness, and first-10 guardrails must also pass. broad public self-serve still requires row-derived first-10 external evidence.

## Blockers

None.

## Required artifacts

### docs

- `support_policy`: `PASS` — `SUPPORT.md`
- `security_policy`: `PASS` — `SECURITY.md`
- `ops_readiness`: `PASS` — `docs/SELF_SERVICE_OPS_READINESS.md`
- `first_10_intake`: `PASS` — `docs/FIRST_10_EVIDENCE_INTAKE.md`
- `rollback_comms`: `PASS` — `docs/ROLLBACK_AND_COMMS_RUNBOOK.md`
- `cold_start_trust`: `PASS` — `docs/COLD_START_TRUST_HARDENING.md`

### issue_templates

- `bad_answer`: `PASS` — `.github/ISSUE_TEMPLATE/bad-answer.yml`
- `first_10_evidence`: `PASS` — `.github/ISSUE_TEMPLATE/first-10-evidence.yml`
- `install_mcp_support`: `PASS` — `.github/ISSUE_TEMPLATE/install-mcp-support.yml`
- `issue_config`: `PASS` — `.github/ISSUE_TEMPLATE/config.yml`

### static_files

- `codeowners`: `PASS` — `.github/CODEOWNERS`
- `watchdog_workflow`: `PASS` — `.github/workflows/self-service-watchdog.yml`
- `rollback_drill_snapshot`: `PASS` — `eval/rollback_comms_drill_snapshot.json`

### bad_answer_feedback_path

- `feedback_path`: `PASS` — `multiple`
