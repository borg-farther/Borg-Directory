# Borg Day-One First-User Readiness

Revision: `20260505-0700`
Generated: `2026-05-22T10:38:47.482623+00:00`

## blunt verdict

- Controlled first users: **GO**
- Broad public production: **NO_GO**
- Reason: local gates, security surface, first-user surface, and rescue surface are green; external outcome lift remains unproven

Borg is ready for a controlled first-user cohort if the promise is narrow: agent rescue for known technical failures. It is not ready to claim statistically proven external uplift or mature global network effects.

## what first users will see

- Path: `pip install agent-borg -> borg rescue '<error>' -> ACTION/STOP/VERIFY + human receipt`
- Speed: 30-90 for a known Python/Django class after install seconds
- Value: avoided debugging dead-end, next command/check, verification step, outcome feedback path
- Example: ModuleNotFoundError maps to missing_dependency with tested confidence and 42/45 seed evidence in the rescue smoke

## hard evidence

- Gate timestamp: `2026-05-18T07:46:07.667878+00:00`
- Synthetic/logical 10-user load gate: `True`
- Synthetic/logical 100-user load gate: `True`
- Synthetic/logical 1000-user load gate: `True`
- 100 real-user rollout: `NO_GO until first-10 external evidence passes`
- Version: `{'passed': True, 'project_version': '3.3.8', 'runtime_version': '3.3.8'}`

### load proof

- load_10: passed=`True`, success_rate=`1.0`, p95_ms=`0.6281427631620318`, p99_ms=`0.8716626581735909`, requests=`59794`
- load_100: passed=`True`, success_rate=`1.0`, p95_ms=`0.6004410097375512`, p99_ms=`0.6370391696691513`, requests=`59981`
- load_1000: passed=`True`, success_rate=`1.0`, p95_ms=`0.6051470059901476`, p99_ms=`0.7191141927614809`, requests=`59947`

## security/privacy/prompt-injection posture

- Status: **GREEN_FOR_CONTROLLED_FIRST_USERS**
- Local default: local-first; shared memory path accepts signed, sanitized, revocable learning atoms
- PII/raw trace policy: raw traces/conversations/tool outputs/source/env are not acceptable shared-memory payloads
- Prompt-injection policy: scan and neutralize retrieval poisoning/tool coercion/instruction override before retrieval/export
- CI/policy gates: secret_scan, dependency_vuln_scan, static_security_scan, policy_enforcement

Residual risk:
- scanner coverage is deterministic and test-backed, not a mathematical proof of no PII
- untrusted packs still require source/trust verification and safety scan context
- host MCP configs must set the correct absolute BORG_HOME to avoid split-brain stores

## what still blocks broad public production claims

- real external first-user outcome lift is not yet statistically proven
- network effects are not yet proven with independent external agents
- broad non-Python rescue coverage is intentionally limited/fail-closed
- served-runtime MCP reload must be verified in each host environment before claiming that host is green

## evidence inventory

- gate_run: `True`
- uat_scoreboard: `True`
- security_baseline: `True`
- readme: `True`
- rescue_engine: `True`
- rescue_tests: `True`
- privacy_scanner: `True`
- prompt_injection_scanner: `True`
- privacy_tests: `True`
- prompt_injection_tests: `True`
- security_gate: `True`

## operating answer

Ship to first users as a controlled beta. Make the first message and first command about `borg rescue`, not about packs or collective intelligence. Measure rescue rate before making bigger claims.
