# Borg security policy

## Report a vulnerability

Use GitHub private vulnerability reporting if available, or open a minimal public issue that says a private report is needed without posting sensitive details. Do not include secrets, tokens, passwords, private traces, customer data, or connection strings. Replace sensitive values with `[REDACTED]`.

## What counts as a privacy/security incident

- Borg output exposes a secret or asks a tester to paste one into public evidence.
- A rescue/action path could damage a user's system or delete data without explicit confirmation.
- A prompt-injection, trace-ingestion, or failure-memory path stores unredacted private data.
- A first-10 evidence row includes raw credentials, private repo data, or personal information that was not consented for collection.
- Served MCP/runtime behavior diverges from source/package proof in a way that can expose stale unsafe guidance.

## Supported versions

The controlled first-10 beta uses the current PyPI package line documented in README and the public proof dashboard. Older versions may be yanked or deprecated if a bad release is identified.

## Revocation

If a submitted trace/evidence row must be removed, open a security/privacy report with the row pseudonym and evidence URI. Maintainers must remove or redact the row, rerun `python eval/first_10_evidence.py --input eval/first_10_user_scoreboard.json --write`, and regenerate public proof artifacts before making readiness claims.

## Current launch boundary

A privacy/security incident is an automatic public-self-serve NO-GO and pauses first-10 invites until the rollback/comms runbook has been executed and the relevant gates pass again.
