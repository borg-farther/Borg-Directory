# Borg support policy

Borg targets `agent-borg==3.3.19` as the next immutable package; production PyPI latest remains 3.3.18, so exact-version PyPI fresh-install/stdio MCP proof for 3.3.19 is not green yet. Controlled first-10 beta is currently **NO-GO** until package/source provenance, served-runtime freshness, release-governance, ops/watchdog, docs-claim, and evidence-intake guardrails are green. GitHub `main` release governance is enforced. Broad public self-serve, 100-user rollout, served remote MCP, and measured lift are not claimed until row-derived external evidence passes.

## Supported path

- Target package path: `agent-borg==3.3.19` from PyPI after merge/tag/CI and upload; first-10 invites remain paused until package proof, served-runtime freshness, and external-evidence guardrails are green.
- First command: `borg rescue "<redacted real error>" --short`.
- MCP path: `borg-mcp` over stdio from a local client.
- Evidence intake: `.github/ISSUE_TEMPLATE/first-10-evidence.yml`.
- Bad first-answer report: `.github/ISSUE_TEMPLATE/bad-answer.yml`.
- Install/MCP support: `.github/ISSUE_TEMPLATE/install-mcp-support.yml`.

## First-10 beta support window

During the controlled first-10 beta, maintainers review new P0/P1 first-user reports daily when the beta is active. This is not a guaranteed enterprise SLA. It is a beta support window for proving whether a cold external user can install Borg, get a useful ACTION / STOP / VERIFY rescue, and report outcome evidence without private maintainer handholding.

## Severity levels

- **P0 — pause first-10 invites immediately**: suspected secret/privacy leak, harmful guidance that could damage user systems, broken PyPI package install for most users, served/runtime split-brain causing stale unsafe guidance, or any critical privacy/security incident.
- **P1 — fix before adding more testers**: bad first answer for a common real error, MCP stdio canary regression, docs telling users the wrong install path, broken evidence intake, or repeated setup failure affecting more than one tester.
- **P2 — normal beta backlog**: confusing copy, missing examples, non-blocking doc gaps, edge-case advice quality issues, optional integration friction.

## Target triage times

- P0: acknowledge within 24 hours during active first-10 beta; keep invites paused until the incident owner records a mitigation and reruns the relevant gate.
- P1: acknowledge within 48 hours during active first-10 beta; do not expand beyond the current tester cohort until fixed or explicitly accepted as a known limitation.
- P2: review weekly or before the next public readiness decision.

## What pauses first-10 invites

Pause first-10 invites when any of these occur:

1. A P0 report is opened.
2. `eval/self_service_ops_gate.py` fails.
3. `eval/ops_readiness_watchdog.py` fails outside a known GitHub outage.
4. PyPI latest/fresh-install/MCP stdio canary no longer matches the current version.
5. A bad-answer report shows irrelevant first guidance on a concrete common error.
6. Any consent/redaction/privacy issue appears in first-10 evidence rows.

## Privacy/security escalation

Open a security report using `SECURITY.md`. Do not include secrets, API keys, tokens, passwords, private repo URLs, or raw user traces. Replace sensitive values with `[REDACTED]` and attach only minimal reproduction evidence.

## Maintainer handholding definition

A first-10 row counts as self-service only when the tester can complete install, first rescue, and evidence submission using public docs/templates. Private maintainer debugging, manual JSON edits by a maintainer, or non-public setup steps must be recorded as blocker notes and do not count as clean self-service proof.

## Current boundary

Controlled first-10 beta can run only after the current immutable package metadata, trust, ops, and watchdog gates are green for the same version.
Broad public self-serve remains NO-GO until row-derived first-10 external-user evidence passes: 10 verified external users, at least 8 installs, at least 6 useful rescues, and 0 critical privacy/security incidents.
