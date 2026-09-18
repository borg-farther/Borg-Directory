# Borg readiness

## Current verdict

- Controlled first-10 beta: **NO-GO right now** (zero external users; cap 0). The source line is `agent-borg==3.3.21`, but source, PyPI, served-runtime, governance, watchdog, docs-claim, and evidence-intake gates must independently agree before inviting controlled testers. Version-string equality alone is not release proof. External first-10 row count is still zero.
- Public waitlist / narrow beta: **0 testers may proceed** until those controlled-beta infrastructure and guardrail gates are green; then the first-10 evidence contract caps the cohort at 10.
- Public self-serve launch: **NO-GO until first-10 external-user evidence passes** (10 verified external users, >=8 installs, >=6 useful rescues, 0 critical incidents).

## What passed for source/local package infrastructure

The scheduled readiness workflow requires the repository secret
`BORG_GOVERNANCE_TOKEN`: a read-only fine-grained GitHub token with access to
repository Administration metadata (branch protection/rulesets) and Actions
metadata. The workflow's default `github.token` remains the fallback for public
metadata, but a 403 without a rate-limit header is treated as a permissions
failure and is not retried. Missing or under-scoped governance credentials must
fail the release-governance gate closed rather than report a false release GO.

- Public install path exists: `python3 -m pip install agent-borg`.
- CLI entrypoints exist: `borg`, `borg-mcp`, `borg-doctor`.
- First value path exists: `borg rescue "<error>"` returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- First-10 contract exists: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md).
- Security/privacy/prompt-injection surface has a baseline and CI gates.
- GitHub CI/security gates are part of the release proof chain. PR branches still need their own green checks and post-merge `main` proof refresh before branch-specific source changes are claimed on `main`.
- The local first-user gate covers `agent-borg==3.3.21`, including generated rules, OpenClaw export, stdio MCP, CLI, and Python API. Local proof does not substitute for an exact-version PyPI fresh-install canary or served-runtime fingerprint. First-10 external-user evidence remains mandatory after infrastructure gates turn green.

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
- [`../eval/served_runtime_fingerprint_snapshot.json`](../eval/served_runtime_fingerprint_snapshot.json)
- [`../eval/release_governance_snapshot.json`](../eval/release_governance_snapshot.json)
- [`../eval/ops_readiness_watchdog_snapshot.json`](../eval/ops_readiness_watchdog_snapshot.json)
- [`../eval/public_self_serve_launch_gate_snapshot.json`](../eval/public_self_serve_launch_gate_snapshot.json)
- [`../eval/first_10_user_scoreboard.json`](../eval/first_10_user_scoreboard.json)
- [`../eval/security_hardening_baseline.json`](../eval/security_hardening_baseline.json)

Historical status snapshots are archived under [`archive/root-md/`](archive/root-md/).
