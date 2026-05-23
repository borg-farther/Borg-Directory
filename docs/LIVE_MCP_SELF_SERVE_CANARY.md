# Live MCP self-serve canary

Generated: 2026-05-23T20:15:16Z

## Verdict

**BLOCKED_VERSION_DRIFT_OPERATOR_RELOAD_REQUIRED**

The live Borg MCP calls are functionally responding, but the served process reports
`borg_version=3.3.7` while canonical source and PyPI are `3.3.10`.

No gateway restart, kill, signal, or reload was performed by the agent.

## Evidence

- Runtime fingerprint: PASS for callable path and confidence-gate canary.
- Served PID: `423397`.
- Borg home: `/root/.borg`.
- Module path: `/root/hermes-workspace/borg/borg/__init__.py`.
- Module hash: `079ca796afcc3456c3b01cf9cea780a87ace0c1a1fe502f60864f9b9bab5b035`.
- Reported Borg version: `3.3.7`.
- Expected source/PyPI version: `3.3.10`.

## Canary calls

- Nonsense observe prompt: PASS — returned `NO_CONFIDENT_MATCH`.
- Permission-denied rescue prompt: PASS — matched `permission_denied` with tested confidence and `chmod`/`chmod 777` ACTION/STOP shape.

## Blocker

Public self-serve / served MCP readiness remains **NO-GO** until an operator-supervised
reload/cutover makes the served runtime report the current `3.3.10` identity and the
same canaries pass again.
