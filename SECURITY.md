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

## Federation kill-switch (emergency stop for atom sharing)

Borg is local-first: by default nothing leaves your machine (`sharing.mode = local_only`).
On top of that opt-in default there is a one-command **kill-switch** that immediately
halts every learning-atom egress path — use it during a suspected leak, poisoning, or
denial-of-wallet incident.

```bash
borg sharing status        # is the kill-switch engaged?
borg sharing off           # PANIC: block ALL atom egress now (fail-closed)
borg sharing off --reason "incident #42"
borg sharing on            # re-allow opt-in atom egress
```

When engaged, `borg sharing off` writes a sentinel file (`$BORG_HOME/SHARING_DISABLED`)
and the following paths **fail closed** with a clear error, leaving no atom on the wire:

- `borg publish` and `borg atom publish`
- `borg atom distill` for any non-local scope (`org` / `global_candidate` / `global`)
- the `borg_publish` MCP tool

Local-only operations (rescue, search, local distill, observe) are unaffected — Borg keeps
working offline. The switch is a plain file: an operator can also engage it by hand
(`touch $BORG_HOME/SHARING_DISABLED`) or back it up, and disengage with `borg sharing on`.

## Current launch boundary

A privacy/security incident is an automatic public-self-serve NO-GO and pauses first-10 invites until the rollback/comms runbook has been executed and the relevant gates pass again.
