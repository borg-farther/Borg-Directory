# Live MCP self-serve canary

Generated: 2026-05-23T20:15:16Z. Historical/stale canary retained as evidence of the served-runtime split-brain class; do not treat the version numbers below as current release proof.

## Verdict

**BLOCKED_VERSION_DRIFT_OPERATOR_RELOAD_REQUIRED**

The historical live Borg MCP calls were functionally responding, but the served process reported
`borg_version=3.3.7` while the then-current source/PyPI target was `3.3.10`. Current source now targets `agent-borg==3.3.14`, and served remote MCP remains NO-GO until a fresh operator-supervised runtime fingerprint/canary passes against the current version.

No gateway restart, kill, signal, or reload was performed by the agent.

## Evidence

- Runtime fingerprint: PASS for callable path and confidence-gate canary.
- Served PID: `423397`.
- Borg home: `/root/.borg`.
- Module path: `/root/hermes-workspace/borg/borg/__init__.py`.
- Module hash: `079ca796afcc3456c3b01cf9cea780a87ace0c1a1fe502f60864f9b9bab5b035`.
- Reported Borg version: `3.3.7`.
- Expected source/PyPI version at the time: `3.3.10`; current source target: `3.3.14`.

## Canary calls

- Nonsense observe prompt: PASS — returned `NO_CONFIDENT_MATCH`.
- Permission-denied rescue prompt: PASS — matched `permission_denied` with tested confidence and `chmod`/`chmod 777` ACTION/STOP shape.

## Blocker

Public self-serve / served MCP readiness remains **NO-GO** until an operator-supervised
reload/cutover makes the served runtime report the current release identity and the
same canaries pass again. Agents must not restart, kill, signal, or reload the Hermes gateway.
