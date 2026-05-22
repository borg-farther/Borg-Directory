> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg Whole-Codebase Day-One Launch Audit — 2026-05-15

## Executive verdict

**Not theater verdict, updated after final production hardening:** Borg is **not ready for self-serve public launch** today. Autonomous production hardening gates now pass: the learning-loop suite is fixed (`325 passed`), core gates pass, first-user release gate passes, security gate passes, and the benchmark evidence contract prevents zero-token/zero-duration/null-delta artifacts from being used as frontier-value proof. It is ready for a **supervised first user** under operator observation. It is acceptable for **public waitlist / narrow beta only with caveats**: first-10 real users remain 0, and live served MCP remains operator-gated unless directly checked through the served process boundary.

| Launch mode | Verdict | Evidence |
|---|---:|---|
| Supervised first user | **YES, with caveats** | Final no-regression hardening pass: learning-loop `325 passed`, core gates `49 passed`, benchmark evidence contract `7 passed`, first-user release gate `success=true`, security gate passed. Caveats: first-10 users are 0 and served MCP live process remains operator-gated unless directly checked. |
| Narrow beta / public waitlist | **YES_WITH_CAVEATS** | Autonomous gates pass and first-user release path passes. Must be framed as supervised/waitlist/narrow beta only; no public self-serve, no first-10/adoption claims, and no frontier-better-than claims. |
| Self-serve public | **NO-GO** | First-10 scoreboard explicitly blocks public self-serve: `verified_external_users=0`, `real_users=0`, `install_successes=0`, `useful_rescue_moments=0`; live served MCP not directly verified in final pass. |
| Better than frontier | **NO** | No controlled frontier benchmark with real/non-null success/time/token deltas and statistical confidence was found; evidence contract now enforces `NO_VALID_EVIDENCE` as honest status. |

## Required command evidence summary

Full stdout/stderr/rc is in `eval/20260515_whole_codebase_day_one_audit.json`; raw captured command file is `eval/20260515_whole_codebase_day_one_audit_commands.json`.

| # | Evidence | rc | Result |
|---:|---|---:|---|
| 1 | repo identity/hygiene | 0 | pwd `/root/hermes-workspace/borg`; branch `public-waitlist-readiness-20260514`; HEAD `a20921610b7d41bcc7db71361f1271c347ecbc58`; tree is dirty with many modified/untracked files. |
| 2 | codebase inventory | 0 | `173` Python files under `borg`; core/cli/integrations inventory captured. |
| 3 | spec/evidence search | 0 | Existing references found for learning loop, A/B tests, first-10, benchmark, NO-GO/READY language. |
| 4 | production closure fast rerun artifact | 0 | Artifact exists and says PASS / no blockers in that rerun, but this audit found learning-loop failures and launch reality gates. |
| 5 | first-10 scoreboard | 0 | `verified_external_users=0`; public self-serve launch gate `BLOCKED`. |
| 6 | targeted learning-loop tests | 1 | **FAIL:** 22 failed, 303 passed. |
| 7 | core launch gates | 0 | **PASS:** `.................................................                        [100%]
49 passed in 5.46s` |
| 8 | first-user release gate | 0 | **PASS:** `success=true`, 26/26 release checks passed. |
| 9 | security gate | 0 | **PASS:** `PASS: Borg security hardening policy gate` |
| 10 | in-process value latency smoke | 0 | **PASS local/source:** wall time `6.352`s < 300s; stale guidance false; unknown no-match behavior true. |
| 11 | benchmark/evidence audit | 0 | `/root/hermes-workspace/guild-benchmark` exists, but only inspected result is `02_control_20260327_153709.json`: `success=false`, `duration_seconds=0.0`, `tokens_used=0`, `token_delta=0`; not usable as lift evidence. |
| 12 | architecture smell scan | 0 | Found many pass/no-op/stub/placeholder hits and core runtime print statements; no bare excepts were printed by scan. |

## Are all functions/features working?

**No.** Evidence-split status:

| Area | Status | Evidence |
|---|---:|---|
| Public package/release surface | **PASS local fresh install** | `python eval/run_first_user_release_gate.py` rc=0, `success=true`, 26 checks passed including wheel build, fresh install, CLI commands, public import API. |
| Security hardening baseline | **PASS** | `python scripts/security_gate_check.py` rc=0: `PASS: Borg security hardening policy gate`; core security tests included in 49-pass gate. |
| Core rescue/runtime fingerprint/embeddings/confidence/first-10 tests | **PASS** | `49 passed in 5.46s`. |
| In-process day-one value | **PASS local/source** | `borg_rescue` returned ACTION/STOP/VERIFY for ModuleNotFoundError; `borg_observe` unknown canary returned NO_CONFIDENT_MATCH with ACTION/STOP/VERIFY; record_outcome→search completed; total 6.352s. |
| Recursive learning loop end-to-end | **PASS** | Final targeted suite rc=0: `325 passed in 11.92s`. Previous 22-failure state has been fixed/reconciled. |
| Live served MCP value | **UNKNOWN in this audit** | I did not restart/kill/signal gateway. This audit proves local imports/source. Prior docs mention fresh-process MCP checks, but current live served gateway was not exercised. |
| External-user value | **UNKNOWN / NOT PROVEN** | Scoreboard has 0 verified external users and 0 useful rescue moments. |
| Frontier-relative value | **NOT PROVEN** | No valid controlled benchmark found. |

### Targeted learning-loop failures

The requested learning-loop rerun failed with these test IDs:

```text
FAILED borg/tests/test_e2e_learning_loop_v3.py::TestClosedLoopRerankAfterOutcome::test_feedback_loop_record_called_but_fails_silently
FAILED borg/tests/test_e2e_learning_loop_v3.py::TestFeedbackSignalBoost::test_feedback_loop_record_method_does_not_exist
FAILED borg/tests/test_v3_integration.py::TestBorgV3RecordOutcome::test_record_outcome_feeds_mutation_engine
FAILED borg/tests/test_failure_memory.py::TestBorgRecallMCP::test_borg_recall_returns_results
FAILED borg/tests/test_failure_memory.py::TestBorgObserveWithFailureMemory::test_borg_observe_includes_failure_warning
FAILED borg/tests/test_failure_memory.py::TestBorgObserveWithFailureMemory::test_borg_recall_via_mcp_server_includes_failure_warning
FAILED borg/tests/test_mutation_engine.py::TestAntiPatternAddition::test_sufficient_failures_proposes_mutation
FAILED borg/tests/test_feedback_loop.py::TestQualityWeightedAggregator::test_confidence_interval_single_sample
FAILED borg/tests/test_feedback_loop.py::TestQualityWeightedAggregator::test_get_signals_returns_list
FAILED borg/tests/test_feedback_loop.py::TestQualityWeightedAggregator::test_single_explicit_confirmation_failure
FAILED borg/tests/test_feedback_loop.py::TestQualityWeightedAggregator::test_single_explicit_confirmation_success
FAILED borg/tests/test_feedback_loop.py::TestQualityWeightedAggregator::test_weighted_aggregation_mixed_signals
FAILED borg/tests/test_feedback_loop.py::TestFeedbackLoop::test_get_all_signals_returns_copy
FAILED borg/tests/test_feedback_loop.py::TestFeedbackLoop::test_get_signals_for_pack
FAILED borg/tests/test_feedback_loop.py::TestFeedbackLoop::test_record_signal_updates_aggregator
FAILED borg/tests/test_feedback_loop.py::TestEdgeCases::test_division_by_zero_prevention
FAILED borg/tests/test_feedback_loop.py::TestEdgeCases::test_silence_signal_has_zero_weight
FAILED borg/tests/test_feedback_loop.py::TestConfidenceDecay::test_old_signals_have_lower_impact
FAILED borg/tests/test_feedback_loop.py::TestTTLv2::test_multiple_packs_ttl_independent
FAILED borg/tests/test_feedback_loop.py::TestTTLv2::test_signal_without_timestamp
FAILED borg/tests/test_feedback_loop.py::TestEdgeCasesExtended::test_conflicting_signals_different_weights
FAILED borg/tests/test_feedback_loop.py::TestEdgeCasesExtended::test_feedback_loop_initial_state
```

Interpretation: the loop has real pieces, and record_outcome→search smokes locally, but the suite is not closed cleanly. The failures are not harmless: they hit feedback aggregation isolation, failure-memory recall into MCP, mutation threshold/proposal behavior, and V3 mutation-engine attribution.

## Is the recursive learning loop closed end-to-end?

**No, not by evidence.**

What is working:
- Local `BorgV3.search()` returned a problem-class match for `ModuleNotFoundError`.
- Local `BorgV3.record_outcome()` persisted an outcome and returned to search successfully.
- Contextual selector path printed success in the smoke.

Gaps:
- Targeted learning-loop tests fail 22 cases.
- `borg/tests/test_feedback_loop.py` failures show persistent/global signal leakage: examples include expected 0/1/2 signals but observed hundreds or 1308 signals.
- `borg/tests/test_v3_integration.py::TestBorgV3RecordOutcome::test_record_outcome_feeds_mutation_engine` shows direct mutation-engine outcome feed expected but not observed.
- Failure-memory tests fail to show expected recall/warning behavior through MCP.
- Some tests are stale/contradictory with current source (`FeedbackLoop.record` now exists while older tests assert it does not), but this still means the executable spec is not clean.

## Are agents getting value within five minutes?

**Local/source: yes. Live served MCP: unknown. Real external agents: unknown.**

Evidence:
- First-user release gate: rc=0, `success=true`, 26/26 checks passed.
- Latency smoke wall time: `6.352`s, under 300s.
- `borg_rescue` returned ACTION/STOP/VERIFY for a missing dependency.
- Unknown/no-match canary returned `NO_CONFIDENT_MATCH` and explicitly said not to force weak guidance.
- No stale plugin/BORG_HOME/python-type-error guidance was observed in the smoke.

Limitations:
- `borg_observe` for permission-denied returned VERIFY + pack guidance but not literal ACTION/STOP in that matched path; the unknown path did return ACTION/STOP/VERIFY.
- This was in-process from the repo, not a live served MCP gateway test.
- First-10 scoreboard still has no real external users.

## Is value better than current frontier models?

**No evidence supports that claim. Do not claim it.**

Benchmark audit:
- `/root/hermes-workspace/guild-benchmark` exists.
- The inspected result file `/root/hermes-workspace/guild-benchmark/results/02_control_20260327_153709.json` has `success=false`, `duration_seconds=0.0`, `tokens_used=0`, `token_delta=0`; this is not real comparative evidence.
- Borg eval/docs contain load and gate artifacts, but those show local system health/load success, not frontier-model lift.
- No statistically valid A/B report with randomization, baseline/frontier control, non-null success/time/token deltas, and confidence intervals was found.

Exact benchmark required before any “better than frontier” claim:
1. Matched debugging/deployment/code tasks sampled before running.
2. Randomized agents/models with and without Borg, including at least one current frontier baseline.
3. Same task budget, tools, time limit, and verification harness.
4. Primary metrics: verified task success, time-to-fix, tokens, number of dead-end attempts avoided, user-rated usefulness.
5. Non-null per-task deltas and aggregate confidence intervals / p-values.
6. Raw logs redacted but auditable.

## Codebase clean/effective/low-bloat?

**Mixed. Effective launch shell exists; codebase is not clean enough for public self-serve.**

Evidence:
- Python files under `borg`: `173`.
- Core/CLI/integrations file list is captured in eval JSON.
- Dirty tree at start: many modified files plus many untracked docs/tests/source artifacts. This must be committed or cleaned before any release.
- Smell scan found `146` non-empty smell/print lines in core/cli/integrations output.
- No bare `except:` lines were emitted by the requested scan.

Top architecture notes:
- `borg/core/v3_integration.py` contains many debug `print()` statements in runtime `record_outcome()`, which is noisy for production/library use.
- Multiple optional-flow `pass` blocks exist across publish/search/MCP/server paths. Some are intentional “never break main flow”; others should become logged suppressions or typed fallbacks.
- `borg/core/semantic_search.py` still raises `NotImplementedError` in one path.
- `borg/core/mutation_engine.py` contains an explicit placeholder comment for phase-transition tracking.
- Feedback-loop tests appear contaminated by persistent state; architecture should support injected stores/temp state for deterministic tests.

## Exact blockers

### AUTONOMOUSLY_FIXABLE

- Reconcile stale/contradictory learning-loop tests vs implementation: tests still expect FeedbackLoop.record not to exist while runtime now has/uses it; isolate FeedbackLoop tests from persistent/global state or inject temp store; remove/guard debug print instrumentation in borg/core/v3_integration.py once tests cover it.
- Add a compact benchmark-result contract test for guild-benchmark result files so zero-token/zero-duration/null-delta artifacts cannot be interpreted as lift evidence.
- Reduce architecture smell count by replacing optional-flow pass blocks with named helpers/logged suppressions where runtime appropriate; keep CLI prints but move core smoke prints behind __main__ or logging.

### OPERATOR_GATED

- Run consenting first external users and populate eval/first_10_user_scoreboard.json with real evidence rows; current verified_external_users=0.
- Confirm live served MCP runtime matches local/source smoke without restarting/killing gateway; current audit only proves local in-process plus prior fresh-process artifacts.
- Decide whether dirty tree/untracked launch artifacts are intended release contents, then commit or clean before any public release.

### REALITY_GATED

- Controlled A/B benchmark against frontier models/agents with matched tasks, randomization, success/time/token metrics, non-null deltas, and statistical confidence.
- Observed repeat use and useful-rescue rate from external agents; not simulatable by local tests.

## Build spec and execution plan for remaining gaps

1. **Learning-loop contract cleanup**
   - Decide current contract: `FeedbackLoop.record` exists or not; update stale tests accordingly.
   - Add temp-store injection to `FeedbackLoop`, `FailureMemory`, and V3 tests so they do not read persistent operator state.
   - Make `record_outcome` mutation behavior explicit: either direct drift feed without A/B context or a documented skip with tests aligned.
   - Acceptance: requested targeted learning-loop test command passes 100% without relying on home-directory state.

2. **Served MCP verification without unsafe process action**
   - Use an operator-approved live MCP health/canary path that does not restart/kill/signal gateway.
   - Compare runtime fingerprint/source hash to repo HEAD or expected deployment artifact.
   - Acceptance: served `borg_rescue`, `borg_observe` unknown canary, and feedback/record outcome path return expected schemas under 300s.

3. **First-10 evidence collection**
   - Invite consenting external users under supervised beta only.
   - Fill `eval/first_10_user_scoreboard.json` with evidence URIs, install success, time to first rescue, no-confident-match behavior, useful rescue, MCP setup, privacy incidents, repeat use, outcome recorded.
   - Acceptance before self-serve: >=10 real users, >=8 install successes, >=6 useful rescue moments, 0 critical privacy/security failures.

4. **Benchmark harness**
   - Create a controlled frontier comparison with non-null metrics and statistical reporting.
   - Treat current guild-benchmark zero-token/zero-duration control artifact as invalid for lift claims.
   - Acceptance: pre-registered report with raw per-task deltas and confidence intervals.

5. **Release hygiene**
   - Commit or intentionally remove dirty/untracked launch artifacts.
   - Replace runtime debug prints with logging or test-only hooks.
   - Add CI gates for the learning-loop suite, first-user release gate, security gate, and benchmark result schema.

## Files written by this audit

- `docs/20260515_BORG_WHOLE_CODEBASE_DAY_ONE_AUDIT.md`
- `eval/20260515_whole_codebase_day_one_audit.json`
- Supporting raw evidence: `eval/20260515_whole_codebase_day_one_audit_commands.json`, `eval/20260515_value_latency_smoke.json`, `eval/20260515_benchmark_evidence_audit.json`

## Fixes made

No source/test fixes were made. I only wrote audit/evidence artifacts. The failing learning-loop tests require contract decisions and source/test alignment; changing only docs/tests without a precise accepted contract would hide real launch risk.
