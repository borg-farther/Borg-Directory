# External Communication Standard (agent-borg)

Last updated: 2026-04-20
Canonical truth source: `eval/gate_run_snapshot.json`

## Purpose
This document defines what we are allowed to claim publicly and how those claims are derived.

## Canonical truth rules
1. **Readiness truth is only from** `eval/gate_run_snapshot.json`.
2. Public status artifacts must be regenerated from canonical truth:
   - `docs/public/status.json`
   - `docs/public/value.json`
   - `docs/public/index.html`
3. If any public doc contradicts canonical truth, CI must fail.

## Telemetry standard (canonical event contract)
- Schema: `eval/telemetry_event_schema.json`
- Required event fields:
  - `event_version`, `event_name`, `event_time`
  - `run_id`, `agent_id`, `task_type`
  - `success`, `latency_ms`, `tokens_used`
  - `source` (`real` or `synthetic`)
- Policy: production reports must present real/synthetic counts separately.

## Claim policy

### Allowed claims (when true in latest gate snapshot)
- "100-user readiness gate is passing"
- "ready_for_100=true"
- "all required launch gates passing"

### Disallowed claims
- Any stale statement like `ready_for_100=false` in canonical public docs after gate is green.
- Any claim mixing synthetic benchmark outcomes as if they are production outcomes.

## Message templates

### If gate is green
- Value signal: strong and measured.
- Reliability signal: passing at 100-user gate thresholds.
- Proof: link `docs/public/status.json` and `docs/public/value.json`.

### If gate is red
- Value signal: measured but readiness gate not yet passing.
- Reliability signal: in hardening.
- Proof: link failing gate fields from latest snapshot.

## Standardized terminology
- **Value signal** = completion/pass/tokens/time improvements.
- **Readiness signal** = go/no-go gate outcome from canonical snapshot.
- **Proof artifacts** = machine-readable files and session trace IDs.

## Release checklist (external)
- [ ] Run `python scripts/sync_public_status.py`
- [ ] Run `python scripts/generate_human_impact_case_studies.py`
- [ ] Run `python scripts/value_dashboard_lint.py`
- [ ] Run `python scripts/borg_human_impact_lint.py`
- [ ] Run `pytest -q eval/tests/test_value_communication_dashboard.py eval/tests/test_external_comms_alignment.py eval/tests/test_human_impact_case_studies.py eval/tests/test_first_user_external_readiness.py eval/tests/test_external_channel_uat_matrix.py`
- [ ] Confirm `docs/public/index.html` reflects current gate values
- [ ] Confirm canonical install path is `pip install agent-borg` in README + getting-started docs
- [ ] Confirm no stale NO-GO phrasing in canonical public docs

## Scope note
Historical/archival docs may contain old states for audit trail. Canonical public docs are:
- `docs/VALUE_COMMUNICATION_DASHBOARD.md`
- `docs/VALUE_COMMUNICATION_DASHBOARD.html`
- `docs/public/index.html`
- `docs/public/status.json`
- `docs/public/value.json`
