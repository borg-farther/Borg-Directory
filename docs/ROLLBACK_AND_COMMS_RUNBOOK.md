# Borg rollback and communications runbook

This runbook defines the response path for a bad release, harmful guidance, privacy/security incident, stale served runtime, or broken first-user install during controlled first-10 beta. It is dry-run tested by `python eval/rollback_comms_drill.py`.

## Immediate pause rule

Pause first-10 invites when a P0 appears, when `eval/self_service_ops_gate.py` fails, when the watchdog fails outside a known GitHub outage, or when any privacy/security incident appears in first-10 evidence.

Status phrase: **pause first-10 invites** until the incident owner records mitigation and reruns the relevant gates.

## PyPI bad release response

1. Confirm the bad release with an isolated fresh install and exact version.
2. If the package is harmful or unusable, yank the bad PyPI release.
3. Pin previous version in public docs with an explicit warning.
4. Regenerate public status and proof dashboard.
5. Open a GitHub issue with reproduction, version, and mitigation.

Template status line: `agent-borg==X.Y.Z is paused; use agent-borg==A.B.C until the follow-up release passes fresh-install + stdio MCP canary.`

## Operator-supervised served MCP rollback

Agents must not kill, restart, reload, or signal the Hermes gateway. Served runtime rollback requires an operator-supervised served MCP rollback:

1. Run `borg_runtime_fingerprint` on the served process.
2. Verify version/path/hash/PID/start time.
3. Operator reloads or rolls back outside the agent session.
4. Rerun served runtime fingerprint and a concrete observe/rescue canary.
5. Record the before/after fingerprint in the incident issue.

## Bad guidance disable path

If Borg gives an irrelevant, unsafe, or overconfident first answer:

1. Open `.github/ISSUE_TEMPLATE/bad-answer.yml`.
2. Record durable learning through shipped paths: `borg_record_failure(...)` for MCP/agents or `borg feedback-v3 --pack <pack> --success no --notes <redacted>` for CLI.
3. Narrow/disable the matching path or trace injection that caused the bad answer.
4. Rerun `python eval/cold_start_trust_gate.py`.
5. Rerun `python eval/public_self_serve_launch_gate.py`.

## Public status update

Update or regenerate:

- `docs/public/status.json`
- `docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`
- `docs/BORG_PROOF_DASHBOARD.md`
- `docs/public/proof-dashboard/index.html`

The status must keep broad public self-serve NO-GO unless first-10 row-derived evidence passes.

## User notification template

Subject: `Borg beta status update: <issue summary>`

Body:

- What happened: `<one sentence>`
- Affected version/surface: `<agent-borg version, CLI/MCP/docs>`
- Secrets/privacy involved: `<yes/no/unknown; do not include secret values>`
- Current action: `<pause, workaround, pin previous version, no action needed>`
- Next update: `<timestamp or condition>`
- Evidence link: `<GitHub issue or public status link>`

## Incident owner checklist

- Incident severity assigned: P0/P1/P2.
- First-10 invites paused if P0/P1 affects new testers.
- Privacy/security escalation followed when required.
- Rollback or patch release decision recorded.
- Gates rerun after mitigation.
- Public status and support docs updated.

## Dry-run proof

Run:

```bash
python eval/rollback_comms_drill.py
```

Expected: `passed: true`, `dry_run_only: true`, with steps for pause, yank/pin, served MCP operator rollback, bad guidance disable path, public status update, and user notification template.
