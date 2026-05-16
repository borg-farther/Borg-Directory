# Borg no-fuckups deep/wide verification — 2026-05-15

Workdir: `/root/hermes-workspace/borg`  
Evidence JSON: `eval/20260515_no_fuckups_deep_wide_verification.json`  
Commit checked at command start: `a20921610b7d41bcc7db71361f1271c347ecbc58`  
Branch: `public-waitlist-readiness-20260514`

## Bottom line

**Autonomous source/local verification is green after one safe fix.** The deeper pass found a first-10 value-contract gap in `borg_observe` for seed-pack-only permission-denied guidance: it returned `VERIFY` and pack guidance but did **not** put `ACTION:`/`STOP:` at the top. I fixed that in `borg/integrations/mcp_server.py` by making seed-pack-only guidance action-first and adding a non-overclaiming seed-pack STOP guard, then reran the full requested evidence suite.

**Do not call this a public self-serve launch pass yet.** The evidence supports a supervised first-10/narrow beta from source/local package paths, not open self-serve public release, because the live served MCP boundary was not directly exercised by this job and real first-10 users are still not proven.

## Exact evidence command results

All requested commands were run and their full `stdout`, `stderr`, return code, and duration are captured in `eval/20260515_no_fuckups_deep_wide_verification.json`.

| # | Command | rc | Result |
|---|---|---:|---|
| 1 | `git status --short; git rev-parse HEAD; git branch --show-current` | 0 | Dirty working tree with many pre-existing modified/untracked/deleted files plus this pass's new docs/eval and `borg/integrations/mcp_server.py` fix; HEAD `a20921610b7d41bcc7db71361f1271c347ecbc58`; branch `public-waitlist-readiness-20260514`. |
| 2 | V3/e2e/failure/mutation/feedback/contextual pytest bundle | 0 | `325 passed in 12.95s`. |
| 3 | rescue/runtime/schema/security/benchmark/confidence/first-10 pytest bundle | 0 | `56 passed in 6.28s`. |
| 4 | `python eval/run_first_user_release_gate.py` | 0 | Gate `success=True`; 26/26 checks passed; fresh venv create, source build, wheel install, public API check all passed. |
| 5 | `python scripts/security_gate_check.py` | 0 | `PASS: Borg security hardening policy gate`. |
| 6 | First-10 local value timing proof | 0 | Three local calls completed in seconds. Missing dependency rescue: ACTION/STOP/VERIFY true, stale false, 0.069s. Unknown observe: NO_CONFIDENT_MATCH with ACTION/STOP/VERIFY true, stale false, 5.149s. Permission observe: after fix ACTION/STOP/VERIFY true, stale false, 0.716s. |
| 7 | Isolated recursive learning loop proof | 0 | Fresh isolated `BORG_HOME`; first search count 1; recorded failure then success; second search count 1; top pack `missing-dependency` with evidence `42` successes, `3` failures, `0.93` success rate. |
| 8 | Benchmark evidence contract state | 0 | Found 3 benchmark JSON candidates: `eval/benchmark_tasks.json`, `eval/20260515_benchmark_evidence_audit.json`, and `/root/hermes-workspace/guild-benchmark/results/02_control_20260327_153709.json`. This is inventory only, not controlled frontier proof. |
| 9 | Claim grep for frontier/public-self-serve language | 0 | Hits are mainly caveats/contract tests and old privacy checklist forbidden-claim examples. Current hardening docs explicitly say self-serve/frontier claims are not proven. |
| 10 | TODO/FIXME/placeholder/NotImplemented/pass/print scan | 0 | Found benign/legacy implementation smells and smoke-test prints; notable remaining items include `borg/core/semantic_search.py` raising `NotImplementedError` for disabled semantic search and `borg/core/mutation_engine.py` placeholder phase-transition comment. Not launch-blocking for the verified first-10 path, but not a whole-codebase perfection proof. |

## What this deeper pass covered

- Source-tree learning loop, failure memory, feedback loop, mutation engine, contextual selector, confidence gate, observe confidence gate, first-10 readiness, rescue, runtime fingerprint, embeddings schema compatibility, and security hardening tests.
- Release gate from source into a fresh venv, source build, wheel build, fresh wheel install, public import/API smoke, and declared entrypoint/path checks as implemented by `eval/run_first_user_release_gate.py`.
- Local first-10 value proof for three high-signal cases: missing dependency rescue, no-confident-match behavior for an unknown nontechnical request, and permission-denied observe guidance.
- Recursive feedback/value loop in an isolated temporary Borg home: search → record failure → record success → search again.
- Benchmark-evidence contract posture and claim grep to reduce false frontier/public-self-serve claims.
- Security baseline via both pytest security tests and `scripts/security_gate_check.py`.

## What this did not cover

- **Live served MCP boundary.** This job imported and called `borg.integrations.mcp_server` in-process. It did not restart, signal, or directly exercise the currently served MCP process/gateway, per constraints. If the chat-served MCP tool is known from the prompt/history to have returned stale/wrong guidance, that remains a live-boundary issue until the served process is canaried without violating gateway constraints. Do **not** claim served MCP pass from this evidence.
- Real first-10 humans. No production user sessions, onboarding friction, retention, or actual feedback ratings were measured here.
- Controlled frontier/model benchmark. The benchmark contract exists and prevents false claims; it does not itself prove token savings or frontier-superior value.
- Full whole-codebase cleanup. The grep found TODO/pass/placeholder/NotImplemented patterns. The critical first-10 path passed, but this is not a statement that every module is complete or production-grade.
- Networked install/PyPI end-to-end beyond local source build/fresh wheel install. The package-fresh-install evidence is local from the current source artifact.
- Load/soak/concurrency beyond the requested suites and release gate.

## First-10 readiness now

### Local/source path

**PASS for supervised first-10.** The core source tests and in-process MCP/rescue/value probes pass. The local calls return actionable contracts in under five minutes by a large margin.

### Package fresh install

**PASS for local fresh package path.** `eval/run_first_user_release_gate.py` created a fresh venv, built `agent_borg-3.3.1`, installed the wheel, and verified public import/API behavior. This is not a PyPI/public-index proof.

### Security

**PASS for current baseline.** Pytest security baseline passed and `scripts/security_gate_check.py` returned `PASS: Borg security hardening policy gate`.

### Recursive learning loop

**PASS for isolated local proof.** The proof exercised search, negative/positive outcome recording, and subsequent search. It showed the expected `missing-dependency` pack after feedback, with evidence metadata present. This proves the local feedback/value loop is wired, not that live fleet learning has operational scale.

### Value under five minutes

**PASS locally/in-process.** Timed cases:

- `rescue_missing_dep`: 0.069s, ACTION/STOP/VERIFY, stale false.
- `observe_unknown`: 5.149s, NO_CONFIDENT_MATCH, ACTION/STOP/VERIFY, stale false.
- `observe_permission`: 0.716s, ACTION/STOP/VERIFY after fix, stale false.

## Autonomous issue found and fixed

Issue: seed-pack-only `borg_observe` output for bash permission denied had `VERIFY` and pack detail but lacked top-level `ACTION:`/`STOP:`. That is a first-10 UX/value-contract bug because a new user should see the recommended next move immediately.

Fix made safely in `borg/integrations/mcp_server.py`:

- If there are no positive traces but a confident pack match exists, emit `ACTION: from matched seed pack, <first pack step>`.
- If there is a pack match and no real STOP/AVOID already emitted, emit a conservative STOP line. For permission packs specifically: `STOP: do not use chmod 777 or blanket sudo; identify the exact file, owner, and minimum required permission.`

Verification after fix:

- Full requested evidence suite reran green.
- Command 6 now reports `observe_permission` with `has_action=true`, `has_stop=true`, `has_verify=true`, `stale=false`.

## Token savings / frontier value

**Not proven.** Do not claim “better than frontier,” “30% improvement,” scale validation, or equivalent. The benchmark evidence contract is present and grep shows current docs mostly caveat this correctly, but there is no controlled benchmark with randomized matched tasks, current frontier baseline, raw paired deltas, positive/non-null token/time/success evidence, and confidence/statistics.

## Remaining risks / must-do before public release

1. **Canary the live served MCP boundary without restarting/killing/signaling gateway.** We need proof that the actual chat-served `borg_observe` returns current guidance and not stale/wrong output. If it still serves old code, source/local green is insufficient.
2. **Run first-10 as supervised/narrow beta, not public self-serve.** Capture real user feedback, success/failure ratings, confusion points, and time-to-value receipts.
3. **Add a regression test for seed-pack-only observe ACTION/STOP/VERIFY.** The fix is verified by command 6, but a dedicated pytest would prevent regression.
4. **Controlled benchmark before value claims.** Run matched randomized tasks against a current frontier baseline with raw paired rows and statistical confidence before any token-savings/frontier-superiority claim.
5. **Triage grep findings.** `semantic_search.py` disabled-path `NotImplementedError`, mutation placeholder comments, broad `pass` handlers, and smoke-test prints should be audited before broad self-serve. They are not blocking the narrow verified path but remain engineering debt.
6. **Dirty tree/release hygiene.** The repo is very dirty with many pre-existing modified/deleted/untracked files and local dist/build churn. Before tagging/public release, isolate the intended diff, rebuild artifacts cleanly, and ensure only desired files ship.
7. **PyPI/public-index install proof.** Local fresh wheel install passes; public release still needs a clean install from the intended distribution channel.

## Final recommended next action for AB

**Proceed with a supervised first-10/narrow beta only after live served MCP canary confirms the deployed chat tool is using the current source behavior.** Do not announce public self-serve and do not make frontier/token-savings claims. The source/local/package/security/recursive-loop gates are green; the remaining blockers are operator/reality-boundary issues: live served MCP freshness, real first-10 user evidence, clean release hygiene, and controlled benchmark proof.
