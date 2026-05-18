# Borg readiness

## Current verdict

- Controlled first-10 beta: **GO**.
- Public waitlist / narrow beta: **GO only with the limits below disclosed**.
- Public self-serve launch: **NO-GO until real external-user evidence exists**.

## Why controlled beta is OK

- Public install path exists: `python3 -m pip install agent-borg`.
- CLI entrypoints exist: `borg`, `borg-mcp`, `borg-doctor`.
- First value path exists: `borg rescue "<error>"` returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- First-10 contract exists: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md).
- Security/privacy/prompt-injection surface has a baseline and CI gates.
- Current default-branch GitHub CI and security gates are green.

## What is not proven

- Statistically significant agent-level success lift.
- Real external-user network effects.
- Broad non-Python coverage.
- Global/federated multi-node reliability.
- Public self-serve onboarding at scale.

## First-10 success threshold

At least 6 of the first 10 users get one relevant ACTION/STOP/VERIFY moment without maintainer handholding, and every miss is recorded as NO_CONFIDENT_MATCH or explicit negative feedback instead of being hidden.

## Evidence links

- [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md)
- [`SECURITY_HARDENING_BASELINE.md`](SECURITY_HARDENING_BASELINE.md)
- [`PRIVACY_MODEL.md`](PRIVACY_MODEL.md)
- [`PROMPT_INJECTION_THREAT_MODEL.md`](PROMPT_INJECTION_THREAT_MODEL.md)
- [`../eval/first_user_release_gate_snapshot.json`](../eval/first_user_release_gate_snapshot.json)
- [`../eval/security_hardening_baseline.json`](../eval/security_hardening_baseline.json)

Historical status snapshots are archived under [`archive/root-md/`](archive/root-md/).
