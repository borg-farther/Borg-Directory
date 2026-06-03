# Borg controlled 7-user launch and 100-user stage gates

Generated: 2026-05-26
Source target: `agent-borg==3.3.18`, canonical repo `borg-farther/Borg-Directory`

## Executive verdict

- **7 external users at once:** NO-GO until `agent-borg==3.3.18` package canaries remain green and the served-runtime/ops/watchdog proof chain is green; then controlled testers remain capped under the first-10 beta limit.
- **Broad public self-serve:** NO-GO until row-derived first-10 external-user evidence passes.
- **100 real users:** NO-GO until first-10 evidence passes and the 100-user rollout gate is green.
- **Served Hermes/Borg MCP runtime:** NO-GO for launch traffic until an operator-supervised runtime fingerprint proves the served process version and code match the current package/source. Agents must not restart or reload the gateway.

## Task decomposition

1. **Scope the launch claim**
   - Claim allowed: controlled beta for 7 consented external users.
   - Claims forbidden: broad public launch, 100-user real rollout, measured savings/lift, served remote MCP readiness.
   - Challenge: a green synthetic load test could be mistaken for real-user evidence.
   - Countermeasure: every status artifact must separate `synthetic_load_all_pass`, `ready_for_controlled_first_10_beta`, and `ready_for_100_real_users`.

2. **Verify the package path users will actually run**
   - Required: PyPI latest `agent-borg==3.3.18`; fresh install; `borg`, `borg-doctor`, `borg rescue`, and stdio `borg-mcp` canary.
   - Challenge: local source tests can mask a broken wheel or stale PyPI README.
   - Countermeasure: run `eval/run_first_user_release_gate.py`, PyPI fresh-install snapshot checks, and public launch gate before invites.

3. **Verify first-answer trust**
   - Required: meta/readiness prompts fail closed with `NO_CONFIDENT_MATCH`; concrete errors produce ACTION / STOP / VERIFY.
   - Challenge: irrelevant but high-confidence traces can destroy first-user trust.
   - Countermeasure: `eval/cold_start_trust_gate.py --no-write` must pass.

4. **Verify self-service ops and incident handling**
   - Required: bad-answer intake, install/MCP support intake, first-10 evidence intake, support policy, security policy, rollback/comms runbook, dry-run rollback drill, watchdog workflow.
   - Challenge: issue forms can exist but miss required fields; rollback drills can mutate real services.
   - Countermeasure: `eval/self_service_ops_gate.py --no-write --json` and `eval/rollback_comms_drill.py` must pass; rollback must remain dry-run-only.

5. **Verify learning and feedback mechanisms**
   - Required: `borg_record_failure` / failure memory persistence, feedback loop tests, aggregator report generation, no host-state leakage into explicit Borg dirs, telemetry/feedback grouping, wiki/dojo paths remaining optional and non-breaking.
   - Challenge: tests can accidentally read the operator's real `~/.hermes` data and pass/fail based on host state.
   - Countermeasure: aggregator tests are included in default pytest and assert explicit Borg dirs do not ingest unrelated HOME feedback.

6. **Verify concurrency mechanics without overclaiming**
   - Required: local logical-user load at 10 and 100 users passes thresholds.
   - Challenge: asyncio logical users are not 100 external users.
   - Countermeasure: load reports must state synthetic-only scope and cannot unlock public/100-real-user gates.

7. **Verify docs/status consistency**
   - Required: README, public status JSON, value dashboard, proof dashboard, go/no-go report, and PyPI copy must not contradict the current launch tier.
   - Challenge: stale conservative NO-GO copy can block testers or undermine trust; stale GO copy can overclaim.
   - Countermeasure: public docs claim guard blocks stale package NO-GO after package canaries and unsupported public-launch GO before first-10 evidence.

8. **Verify served-runtime split-brain**
   - Required before using served Hermes/Borg MCP for external users: runtime fingerprint reports current version, source version match, current function hashes, and canaries pass.
   - Challenge: source/PyPI can be green while the served process is still old.
   - Countermeasure: served runtime remains a separate STOP gate; operator reload/cutover is required and outside agent authority.

## Gate board

### Gate A — immediate 7-user controlled beta

All must pass:

1. `python eval/public_self_serve_launch_gate.py --no-write`
   - expected: exit code `1` while public self-serve is blocked.
   - required fields: `ready_for_controlled_first_10_beta=true`, `ready_for_public_self_serve_launch=false`, `max_recommended_real_users_now=10`, docs guard pass.
2. `python eval/self_service_ops_gate.py --no-write --json`
   - expected: `passed=true`, blockers `[]`.
3. `python eval/cold_start_trust_gate.py --no-write`
   - expected: pass.
4. `python eval/rollback_comms_drill.py`
   - expected: pass, `dry_run_only=true`.
5. `python scripts/security_gate_check.py`
   - expected: pass.
6. `python scripts/borg_proof_dashboard_lint.py`
   - expected: pass.
7. `python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker first_10_external_evidence --require-ci-schedule`
   - expected: pass, only allowed public blocker is first-10 external evidence.
8. Learning-loop regression tests:
   - `python -m pytest -q tests/learning/test_failure_memory.py tests/learning/test_feedback_loop.py scripts/test_run_aggregator.py --tb=short`
9. Concurrency mechanics:
   - `BORG_READINESS_SOAK_SECONDS=5 python eval/load_soak.py --users 10`
   - `BORG_READINESS_SOAK_SECONDS=5 python eval/load_soak.py --users 100`
10. Final code gate:
   - `python -m pytest -q`
   - `git diff --check`

STOP if any gate fails, if any privacy/security incident appears, if any docs claim broad public/self-serve GO, or if evidence intake cannot capture consented rows.

### Gate B — expansion from 7 to 10

All Gate A items must still pass, plus first-10 evidence intake must show no critical incidents and no systemic install/MCP support blocker among the first 7 users.

### Gate C — 100 real users / public self-serve

Gate C is blocked until all are true:

- `verified_external_users >= 10`
- `real_users >= 10`
- `install_successes >= 8`
- `useful_rescue_moments >= 6`
- `critical_privacy_security_failures == 0`
- public self-serve gate passes without `--allow-public-blocker`
- real-user rollout gate passes
- docs/status/PyPI/public JSON/proof dashboard all say the same thing

## Invite packet requirements for the 7 users

Every invite must include:

1. Install path: `pipx install agent-borg==3.3.18`
2. Verify path: `borg version`, `borg-doctor --json`
3. First value path: `borg rescue "<redacted real error>" --json`
4. Optional local MCP path: configure `borg-mcp` as a stdio MCP server in the tester's own agent host.
5. Safety line: do not paste secrets, private keys, credentials, proprietary traces, customer data, or unredacted logs.
6. Evidence line: submit the first-10 evidence form with consent, install success, time-to-first-rescue, useful/not-useful outcome, MCP status, `NO_CONFIDENT_MATCH` behavior, privacy/security incident flag, and whether maintainer handholding was needed.
7. Bad-answer path: submit bad guidance with sanitized input and returned ACTION / STOP / VERIFY.

## Final reflective pass

Re-evaluated from scratch:

- If the question is only "can 7 users try Borg at once?" the answer is currently no for this source revision: `agent-borg==3.3.18` is published and freshly canaried, but the cap stays 0 until served-runtime freshness, ops/watchdog, release-control proof, and first-10 evidence are green.
- If the question is "is Borg ready for 100 concurrent public self-service users?" the answer is no, because 100 real-user readiness is evidence-gated and first-10 evidence is still zero.
- If the question is "are local source and package enough?" the answer is no for served channels; runtime fingerprinting is a separate gate.
- If the question is "should we build new features now?" the answer is no; the immediate work is proof, docs consistency, feedback capture, and fail-closed gates.

Bottom line: do not launch 7 yet. The immutable package is now published and freshly canaried; next clear served-runtime freshness and ops/watchdog gates, then launch at most 10 controlled testers with consented row capture, pause on any incident, and do not expand beyond 10 until row-derived evidence passes.
