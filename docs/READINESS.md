# Borg readiness

## Current verdict

- Controlled first-10 beta: **NO-GO right now**. `agent-borg==3.3.18` is the published runtime-canary-proven package (not current for this post-tag source line); exact-version fresh-install/stdio MCP/generated-rules/OpenClaw runtime canaries are green. GitHub `main` release governance is enforced; the served runtime fingerprint is stale and remains a separate release-control blocker, and first-10 external-user evidence is still zero.
- Public waitlist / narrow beta: **0 testers may proceed** until served-runtime freshness is green and first-10 evidence intake is ready to capture consented external-user rows; then the first-10 evidence contract caps the cohort at 10.
- Public self-serve launch: **NO-GO until first-10 external-user evidence passes** (10 verified external users, >=8 installs, >=6 useful rescues, 0 critical incidents).

## What passed for source/local package infrastructure

- Public install path exists: `python3 -m pip install agent-borg`.
- CLI entrypoints exist: `borg`, `borg-mcp`, `borg-doctor`.
- First value path exists: `borg rescue "<error>"` returns ACTION / STOP / VERIFY or `NO_CONFIDENT_MATCH`.
- First-10 contract exists: [`FIRST_10_BETA_READINESS.md`](FIRST_10_BETA_READINESS.md).
- Security/privacy/prompt-injection surface has a baseline and CI gates.
- GitHub CI/security gates are part of the release proof chain. PR branches still need their own green checks and post-merge `main` proof refresh before branch-specific source changes are claimed on `main`.
- Local first-user gate and exact-version production PyPI runtime canaries are green for `agent-borg==3.3.18`, including generated rules, OpenClaw export, stdio MCP, CLI, and Python API. PyPI latest/current-source package proof remains red for this post-tag source line until a new immutable version is published and canaried. Served-runtime freshness and first-10 external-user evidence remain the current release-control blockers.

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
