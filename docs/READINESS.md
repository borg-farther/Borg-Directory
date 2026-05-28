# Borg readiness

## Current verdict

- Controlled first-10 beta: **NO-GO for this 3.3.15 source branch until GitHub `main`, PyPI latest, fresh-install, stdio MCP, generated-rules, OpenClaw, cold-start trust, self-service ops, watchdog, source/local first-user, and GitHub CI/security gates are green for the same version.**
- Public waitlist / narrow beta: **blocked until the 3.3.15 package/proof chain is current**; after that, up to 10 consented controlled testers may proceed under the first-10 evidence contract.
- Public self-serve launch: **NO-GO until real external-user evidence exists**.

## What passed for source/local package infrastructure

- Public install path exists: `python3 -m pip install agent-borg`.
- CLI entrypoints exist: `borg`, `borg-mcp`, `borg-doctor`.
- First value path exists: `borg rescue "<error>"` returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- First-10 contract exists: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md).
- Security/privacy/prompt-injection surface has a baseline and CI gates.
- Current default-branch GitHub CI and security gates were green before this 3.3.15 branch; this branch still needs PR/main CI proof.
- Local first-user gate is green for source `agent-borg==3.3.15`, including generated rules and OpenClaw export. PyPI latest/fresh-install/stdio MCP canary is **not yet green for 3.3.15** because production PyPI still has the prior release until the publish step completes.

## What is not proven

- Agent-level success lift at statistical confidence.
- Real external-user network effects.
- Broad non-Python coverage.
- Global/federated multi-node reliability.
- Public self-serve onboarding at scale.

## First-10 success threshold

10 consented external users, at least 8 successful installs, at least 6 useful ACTION / STOP / VERIFY rescue moments without maintainer handholding, and 0 critical privacy/security incidents. Every miss must be recorded as `NO_CONFIDENT_MATCH` or explicit negative feedback instead of hidden.

## Evidence links

- [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md)
- [`SECURITY_HARDENING_BASELINE.md`](SECURITY_HARDENING_BASELINE.md)
- [`PRIVACY_MODEL.md`](PRIVACY_MODEL.md)
- [`PROMPT_INJECTION_THREAT_MODEL.md`](PROMPT_INJECTION_THREAT_MODEL.md)
- [`../eval/first_user_release_gate_snapshot.json`](../eval/first_user_release_gate_snapshot.json)
- [`../eval/pypi_fresh_install_snapshot.json`](../eval/pypi_fresh_install_snapshot.json)
- [`../eval/public_self_serve_launch_gate_snapshot.json`](../eval/public_self_serve_launch_gate_snapshot.json)
- [`../eval/first_10_user_scoreboard.json`](../eval/first_10_user_scoreboard.json)
- [`../eval/security_hardening_baseline.json`](../eval/security_hardening_baseline.json)

Historical status snapshots are archived under [`archive/root-md/`](archive/root-md/).
