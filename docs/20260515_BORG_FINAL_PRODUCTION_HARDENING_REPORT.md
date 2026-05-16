# Borg final production hardening report — 2026-05-15

## Exact verdict

Autonomous production hardening is complete. All autonomous no-regression gates requested in this pass returned rc=0.

Operator/reality gates still remain. Public self-serve is **not** approved because first-10 real users are still 0 and the live served MCP process was not directly exercised in this final pass. Frontier-better-than is **not** proven because there is no valid controlled frontier benchmark evidence.

## Final booleans

| Boolean | Value |
|---|---:|
| READY_FOR_SUPERVISED_FIRST_USER | **YES** |
| READY_FOR_PUBLIC_WAITLIST_OR_NARROW_BETA | **YES_WITH_CAVEATS** |
| READY_FOR_SELF_SERVE_PUBLIC_LAUNCH | **NO** |
| FRONTIER_BETTER_THAN_PROVEN | **NO** |

## Files changed by this hardening continuation

- `scripts/benchmark_evidence_contract.py` — new conservative JSON evidence contract/CLI for benchmark artifacts.
- `eval/tests/test_benchmark_evidence_contract.py` — tests proving honest `NO_VALID_EVIDENCE` is allowed and invalid zero-token/zero-duration/null-delta/frontier-claim artifacts are rejected; hardened to reject bogus token-status strings and unpaired cross-task control/treatment rows.
- `eval/20260515_benchmark_evidence_audit.json` — marked top-level `status=NO_VALID_EVIDENCE`, `frontier_better_than_proven=false`, and contract note.
- `docs/20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md` — reconciled blocker board: learning-loop pass, benchmark contract pass, served MCP remains operator-gated unless directly checked, first-10 remains 0.
- `docs/20260515_BORG_WHOLE_CODEBASE_DAY_ONE_AUDIT.md` — reconciled old learning-loop failure language with final pass evidence.
- `scripts/capture_final_production_hardening.py` — helper used to capture exact stdout/stderr/rc for the required command list.
- `eval/20260515_final_production_hardening_commands.json` — exact command evidence capture for this final pass.
- `docs/20260515_BORG_FINAL_PRODUCTION_HARDENING_REPORT.md` — this report.
- `eval/20260515_final_production_hardening_report.json` — machine-readable final report.

Note: the repository already had many modified/untracked/deleted files before/around this continuation. The final `git status --short` is captured exactly in `eval/20260515_final_production_hardening_commands.json` under `git_status_short`.

## PASS/FAIL table

| Gate | Command | rc | Verdict | Evidence summary |
|---|---|---:|---:|---|
| Learning-loop suite | `python -m pytest -q borg/tests/test_e2e_learning_loop_v3.py borg/tests/test_v3_integration.py borg/tests/test_failure_memory.py borg/tests/test_mutation_engine.py borg/tests/test_feedback_loop.py borg/tests/test_contextual_selector.py --tb=short` | 0 | PASS | `325 passed in 11.35s` |
| Core production gates | `python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py eval/tests/test_security_hardening_baseline.py borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py --tb=short` | 0 | PASS | `49 passed in 5.75s` |
| Benchmark evidence contract | `python -m pytest -q eval/tests/test_benchmark_evidence_contract.py --tb=short` | 0 | PASS | `9 passed in 0.07s` |
| First-user release gate | `python eval/run_first_user_release_gate.py` | 0 | PASS | JSON output has `success: true`; fresh venv/build/install/CLI/rescue/doctor checks passed. |
| Security gate | `python scripts/security_gate_check.py` | 0 | PASS | `PASS: Borg security hardening policy gate` |
| In-process MCP observe canaries | requested Python heredoc | 0 | PASS_LOCAL_SOURCE | Unrelated readiness prompt: `NO_CONFIDENT=True`, `STALE=False`; permission prompt: `PERMISSION=True`, `STALE=False`. This is not live served gateway proof. |
| First-10 scoreboard | requested Python heredoc | 0 | BLOCKED_REALITY | Scoreboard exists; `real_users=0`, `install_successes=0`, `useful_rescue_moments=0`, public self-serve gate `BLOCKED`. |
| Git status capture | `git status --short` | 0 | CAPTURED | Exact output captured in command evidence JSON. Dirty tree remains a release-hygiene issue. |

## Benchmark evidence contract result

Added a conservative contract that:

- accepts honest `status: NO_VALID_EVIDENCE` artifacts;
- rejects artifacts that try to serve as evidence with zero/missing positive time metrics;
- rejects artifacts that try to serve as evidence with zero/missing token metrics unless explicit token-unavailable status is present;
- rejects null delta metrics;
- rejects frontier/better-than claims unless controlled evidence fields exist (`randomized`, `matched_tasks`, `frontier_baseline`, and confidence/controlled evidence); rejects bogus token-status strings such as `measured` when no token count exists; and rejects control/treatment rows that are not paired on the same task.

Current benchmark/frontier status: **NO_VALID_EVIDENCE**. The inspected guild-benchmark zero-token/zero-duration control artifact cannot be interpreted as frontier-value proof.

## Remaining blockers

### Autonomous

- None for the requested final hardening scope. The learning-loop suite, core gates, first-user release gate, security gate, and benchmark contract all pass.
- Release hygiene still needs human review because the working tree is dirty with many pre-existing modified/untracked/deleted files and generated build/dist side effects in status.

### Operator

- Directly verify the **live served MCP** runtime through the actual configured MCP client/process boundary without unsafe gateway kill/restart/signal. Required canaries: served runtime fingerprint/path/hash, unrelated `borg_observe` returns `NO_CONFIDENT_MATCH`, permission-denied returns permission/chmod guidance, and no stale plugin/BORG_HOME/python-type-error guidance.
- Decide what to do with the dirty tree and generated artifacts before release: commit intended changes on the release branch or clean/isolate unrelated files.
- Review public copy before announcement to avoid unsupported adoption/frontier claims.

### Reality

- First-10 real external users remain absent: `real_users=0`, `install_successes=0`, `useful_rescue_moments=0`, `verified_external_users=0`.
- Public self-serve remains blocked until the scoreboard has 10 real user rows, at least 8 install successes, at least 6 useful rescue moments, and 0 critical privacy/security failures.
- Frontier-better-than remains unproven until a controlled A/B benchmark exists with matched tasks, randomization, current frontier baseline, positive/non-null success/time/token evidence, raw paired rows/deltas, and statistical confidence.

## Evidence locations

- Exact stdout/stderr/rc: `eval/20260515_final_production_hardening_commands.json`
- Machine-readable final verdict: `eval/20260515_final_production_hardening_report.json`
- Human report: `docs/20260515_BORG_FINAL_PRODUCTION_HARDENING_REPORT.md`

## Final statement

All autonomously fixable production hardening items requested after the learning-loop fix are complete. The system is ready for a supervised first user and a caveated public waitlist/narrow beta. It is **not** ready for self-serve public launch, and it has **not** proven frontier-better-than value.
