# Borg readiness

## Current verdict

- Controlled first-10 beta: **NO-GO until source/package/release/ops/docs gates are green**. `agent-borg==3.3.18` is the published package, but current source/package proof must pass the GitHub source exact-commit canary, exact-version PyPI fresh-install/stdio MCP/generated-rules/OpenClaw runtime canary, served-runtime fingerprint, release governance, self-service ops, watchdog, and docs-claim guard before any controlled beta invites.
- Public waitlist / narrow beta: **0 real users recommended right now**. Move back to at most 10 controlled, consented, instrumented external users only after those gates are green; every row must capture install outcome, first useful rescue outcome, MCP/setup blockers, negative feedback, and consented measurement fields. No synthetic or maintainer-only run counts.
- Public self-serve launch: **NO-GO until first-10 external-user evidence passes** (10 verified external users, >=8 installs, >=6 useful rescues, 0 critical incidents).

## What passed for source/local package infrastructure

- Public install path exists: `python3 -m pip install agent-borg`.
- CLI entrypoints exist: `borg`, `borg-mcp`, `borg-doctor`.
- First value path exists: `borg rescue "<error>"` returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- First-10 contract exists: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md).
- Security/privacy/prompt-injection surface has a baseline and CI gates.
- GitHub `main` release governance is enforced and part of the release proof chain. PR branches still need their own green checks and post-merge `main` proof refresh before branch-specific source changes are claimed on `main`.
- Local first-user path, GitHub source exact-commit canary, exact-version PyPI fresh-install/stdio MCP canary, served-runtime fingerprint, release governance, self-service ops, and watchdog checks are the required proof chain for `agent-borg==3.3.18`. Current verdicts come from the generated gate snapshots; first-10 external-user evidence remains the broad public launch blocker after the source/package/ops gates are green.

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
- [`../eval/github_source_install_snapshot.json`](../eval/github_source_install_snapshot.json)
- [`../eval/served_runtime_fingerprint_snapshot.json`](../eval/served_runtime_fingerprint_snapshot.json)
- [`../eval/release_governance_snapshot.json`](../eval/release_governance_snapshot.json)
- [`../eval/ops_readiness_watchdog_snapshot.json`](../eval/ops_readiness_watchdog_snapshot.json)
- [`../eval/public_self_serve_launch_gate_snapshot.json`](../eval/public_self_serve_launch_gate_snapshot.json)
- [`../eval/first_10_user_scoreboard.json`](../eval/first_10_user_scoreboard.json)
- [`../eval/security_hardening_baseline.json`](../eval/security_hardening_baseline.json)

Historical status snapshots are archived under [`archive/root-md/`](archive/root-md/).
