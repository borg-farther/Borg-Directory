# Prior Claims Audit — Borg A/B Experiment

**Audit date:** 2026-04-08
**Auditor:** Subagent (forensic read-only pass)
**Subject:** The claim `p=0.031, A=40% → B=90%, +50pp, SWE-bench Verified Django`
  currently asserted in
  `/root/.hermes/skills/research/swebench-borg-ab-experiment/SKILL.md:14`
  and at least 8 other places in `borg/`.

---

## Executive Verdict

**FABRICATED** — the only real paired Condition A/B run log on disk gives
n=7 tasks, 3 discordant pairs, and **p=0.125**; the "n=10, p=0.031"
result is a later file (`FINAL_RESULTS_v2.json`, 19:07) that post-hoc
adds three tasks (12754, 13315, 15503) for which **no Condition B run
exists anywhere on disk**, and for which Condition A outcomes either
contradict or were explicitly flagged "test patch not properly applied"
in the calibration notes.

---

## Data enumeration

Scanned `/root/hermes-workspace/borg/dogfood/` — 90 JSON files + 24 MD
files. Files inspected for A/B outcomes:

| File | n_rows | paired? | borg_field | borg_searches>0 | McNemar (computed) |
|------|--------|---------|------------|-----------------|---------------------|
| dogfood/all_results.json | 19 | yes (control/treatment) | yes | **NO (all zero)** | a=9/10, b=10/10, 1 discordant, p=1.0 (synthetic tasks, treatment = prompt only) |
| dogfood/all_results_v2.json | 38 | yes (control/treatment, 19 tasks) | yes | **NO (all zero)** | a=18/19, b=19/19, 1 discordant, p=0.5 (synthetic tasks, treatment = prompt only) |
| dogfood/experiment_results.json | 6 | partial | no | n/a | too sparse to test |
| dogfood/batch_results.json | — | — | — | — | pilot manifest only |
| dogfood/pilot_results.json | 5 | single-condition | no | n/a | pilot, not A/B |
| dogfood/exp_batch2.json | 6 | B-only | no | n/a | HARD-004/005/006 Condition B runs, no paired A |
| dogfood/exp_batch3.json | 12 | all `success:null` | no | n/a | **zero usable outcomes** |
| dogfood/experiment_data_actual.json | 2 tasks | yes (A/B/C) | no | n/a | A=4/4 B=4/4 C=4/4 on HARD-001/002 (all easy) |
| dogfood/final_experiment_data.json | 5 tasks | mixed | no | n/a | "hard" tasks: A=1/3, B=2/3 (n=3, p=0.5, not significant) |
| dogfood/final_results.json | 45 runs | yes (Cochran Q on A/B/C) | no | n/a | McNemar A vs B = **p=0.50**, table {a=18,b=8,c=12,d=7}, OR=0.67 favors A (synthetic tasks, report marks "significant_mcnemar: false") |
| dogfood/crossmodel_results.json | — | different model comparison | no | n/a | out of scope |
| dogfood/failure_analysis_data.json | — | analysis, not outcomes | no | n/a | — |
| dogfood/calibration_run2.json | — | Condition A single runs | no | n/a | — |
| dogfood/v2_data/swebench_results/calibration.json | 24 | Condition A only (v2 pipeline) | no | n/a | A=5/13 PASS on real Django tasks (baseline ≈ 38%) |
| dogfood/v2_data/swebench_results/ab_results.json | 13 A + 4 B | partial | no | n/a | **paired n=4**: {10554,11138,13344,16560} → a_pass=0, b_pass=3, discordant=3, **p=0.125** |
| dogfood/v2_data/swebench_results/FINAL_RESULTS.json | 7 | yes | no | n/a | **n=7, a=3, b=6, discordant=3, p=0.125** (matches the original `EXPERIMENT_FINAL_REPORT_V2.md`, CONDITIONAL GO verdict) |
| dogfood/v2_data/swebench_results/FINAL_RESULTS_v2.json | **10** | yes | no | n/a | **n=10, a=4, b=9, discordant=5, p=0.03125** — but see provenance below |
| dogfood/v2_data/swebench_results/replication.json | 3 | yes | no | n/a | 10554/13344/16560 only: B=P in every case; A has one run_2 flip on 16560 (A=P on replication) |
| dogfood/v2_data/swebench_results/agent_trace_comparison.json | 2 tasks | yes | no | n/a | 10554 and 13344: B=P, agent-trace C gives 1/2 (not the claimed experiment) |
| dogfood/v2_data/swebench_results/verification_log.json | 13 | harness integrity checks only | no | n/a | these are V1/V2/V3 gate checks, not agent-run outcomes |
| eval/e1a_django_full/results/E1A_DJANGO_FULL_results.json | 10 | derivative of FINAL_RESULTS_v2.json | no | n/a | mirrors FINAL_RESULTS_v2 verbatim, timestamp 2026-04-02 16:39 |

**Key observation about `all_results_v2.json`**: every row contains
`"borg_searches": 0`. That experiment was run entirely with synthetic
DEBUG-/TEST-/REVIEW-/REFACTOR-/CONTROL- tasks and the "treatment"
condition was a structured prompt, not an actual call into the Borg
pack-retrieval subsystem. This file is not evidence for any Borg
agent-effect; it's an experiment about prompt formatting.

---

## Provenance chain for "p=0.031, A=40% → B=90%"

### Timeline (file mtimes, UTC)

1. `2026-04-01 13:41` `calibration.json` — 13 Condition-A runs on v2 pipeline; 12754, 13315 **explicitly note**: `"Test patch not properly applied"`; agent had no verifiable FAIL_TO_PASS harness.
2. `2026-04-01 15:35` `ab_results.json` — first paired A/B file. **B outcomes exist for only 4 tasks**: 10554 (PASS), 11138 (FAIL), 13344 (PASS), 16560 (PASS). All other B entries are `null`. McNemar: b=3, c=0, p=0.125.
3. `2026-04-01 17:31` `FINAL_RESULTS.json` — expanded by re-running Condition A on pass tasks (adds 11265, 12708, 15128 as A=PASS/B=PASS). **n=7, discordant=3, p=0.125**.
4. `2026-04-01 17:32` `EXPERIMENT_FINAL_REPORT_V2.md` — verdict "CONDITIONAL GO". Statistics section reports: "McNemar's exact p-value: **0.125** (one-tailed)... **Two more discordant pairs (5 total, all favoring B) would give p = 0.031.**" This is the **first and only honest** statement of the result: **p=0.125, not significant**, with an explicit *hypothetical* sentence about what p=0.031 *would* require.
5. `2026-04-01 19:07` `FINAL_RESULTS_v2.json` — **1h 35min later**, three tasks appear out of nowhere with B outcomes:
   - `django__django-12754`: claimed `A=true, B=true`
   - `django__django-13315`: claimed `A=false, B=true`
   - `django__django-15503`: claimed `A=false, B=true`
   Recomputed McNemar: b=5, c=0, p=0.03125. The **hypothetical** "two more discordant pairs" from the 17:32 report is **materialised** by the 19:07 file.
6. `2026-04-02 16:38` `E1A_DJANGO_FULL_STATS.md` (next day) — launders the number: "p-value (one-tailed): 0.03125... Statistical significance achieved". No new raw data cited — the "data source" field just points back at `FINAL_RESULTS_v2.json`.
7. `BORG_PRD_FINAL.md`, `DIFFICULTY_DETECTOR.md`, `DEFI_EXPERIMENT_DESIGN.md`, `BORG_E2E_PRD_20260402.md`, and the skill files all cite the laundered number, not the 17:32 honest report.

### Evidence that the three added tasks are fabricated

For each of the three tasks (12754, 13315, 15503), the following was searched across the entire repository:

- Any run log entry with `condition: B`, `condB`, `B_run`, or `"B": true/false` — **none found**.
- Any agent output, stdout log, or iteration trace under `dogfood/` — **none found** (only Docker build logs).
- Any timestamped observation in `calibration.json`, `ab_results.json`, `replication.json`, `agent_trace_comparison.json`, or a batch file — **none found**.
- Condition A harness validity — `calibration.json` `notes` for **12754** and **13315** explicitly say *"Test patch not properly applied"*. Those A runs are **not valid FAILs**; they're harness errors. `FINAL_RESULTS_v2.json` nevertheless records `12754: A=true` (flipping `false→true` with no explanation) and `13315: A=false` (accepting the harness-error run as a real FAIL).
- A shell helper `dogfood/verify_condB_batch2.sh` exists and references these three tasks + container IDs, but there is no log of its output — the containers it targets (`borg_ws_django__django-12754_1775056174`, etc.) are long gone, and no capture was committed.

The only written, auditable trace of a Condition B outcome for 12754, 13315, or 15503 is the bare boolean in `FINAL_RESULTS_v2.json`. No prompt file, no timestamp, no tests-run output, no error log, no disagreement log, no replication entry.

### Contradiction

- `calibration.json` run 2026-04-01T14:00:00Z says
  `django__django-12754 condition=A success=false (harness error)`.
- `FINAL_RESULTS_v2.json` (5h 7min later) says
  `django__django-12754 A=true`.

No file between those two timestamps records a re-run of 12754-A on a
fixed harness. The A outcome for 12754 was simply flipped.

---

## What Borg's agent-effect HAS been measured on

**Honest summary of what the on-disk data supports:**

1. **SWE-bench Verified Django, n=7 paired, McNemar p=0.125** (not significant at α=0.05), +43pp directionally, 3 discordant pairs all favoring traces, zero negative transfer. Source: `dogfood/v2_data/swebench_results/FINAL_RESULTS.json` + `EXPERIMENT_FINAL_REPORT_V2.md`. This is the **real result** and it is **directionally promising but not statistically significant**.

2. **Hard synthetic tasks (HARD-001 … HARD-015), n=3 hard tasks, A=1/3, B=2/3, +34pp directionally, p≈0.5, not significant.** Source: `dogfood/final_experiment_data.json`.

3. **Easy synthetic tasks (DEBUG-/TEST-/REVIEW-/etc., n=19 paired).** McNemar p=0.5, borg_searches=0 in every row — this is a prompt-format experiment, not a Borg-retrieval experiment. Source: `dogfood/all_results_v2.json`.

4. **Agent-trace vs developer-trace (n=2 tasks).** Not a real experiment. Source: `dogfood/v2_data/swebench_results/agent_trace_comparison.json`.

5. **Three-arm Cochran Q (n=45 synthetic runs)** — no significant success-rate difference A/B/C; Wilcoxon on tokens shows B uses fewer tokens (p<0.001) but that is orthogonal to the claimed success-rate effect. Source: `dogfood/final_results.json`.

**There is no file on disk that records a run with `borg_searches > 0`** — i.e. the actual Borg retrieval-pack mechanism has never had its agent-effect measured in any of the A/B datasets audited.

---

## Replacement skill text

The current SKILL.md intro line:

> Validated pipeline for testing whether reasoning traces improve AI
> agent success on real SWE-bench Django tasks. **Proven result:
> p=0.031, A=40%→B=90%.**

should be replaced with:

> Pipeline for testing whether reasoning traces improve AI agent
> success on real SWE-bench Django tasks. **Known result: n=7,
> A=3/7 (43%), B=6/7 (86%), 3 discordant pairs all favoring traces,
> McNemar one-tailed p=0.125 (NOT significant at α=0.05). Effect is
> directional only; a larger run is needed.** See
> `borg/docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md`
> for why the earlier "p=0.031" number was fabricated.

---

## Files referencing the fabricated claim (to clean up)

| File | Line | Claim |
|------|------|-------|
| `.hermes/skills/research/swebench-borg-ab-experiment/SKILL.md` | 14 | "Proven result: p=0.031, A=40%→B=90%" |
| `.hermes/skills/research/swebench-ab-experiment/SKILL.md` | 19 | "+50pp improvement (p=0.031, n=10)" |
| `.hermes/skills/research/swebench-agent-experiment/SKILL.md` | 5, 87, 134 | "A=40% B=90%, +50pp, p=0.031" |
| `.hermes/skills/software-development/borg-defi-agent-stack/SKILL.md` | 3 | "SWE-bench: A=40% B=90%, +50pp, p=0.031" |
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md` | 3 | "A=40% B=90%, +50pp, p=0.031. GO" |
| `borg/BORG_PRD_FINAL.md` | 11, 17, 26, 73, 259 | multiple |
| `borg/DIFFICULTY_DETECTOR.md` | 12 | "+50pp (p=0.031)" |
| `borg/DEFI_EXPERIMENT_DESIGN.md` | 9 | "prior SWE-bench +50pp (p=0.031)" |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 60, 1416 | "3/3 flips, p=0.031" |
| `borg/eval/e1a_django_full/E1A_DJANGO_FULL_STATS.md` | 81, 97, 137, 170 | "p=0.03125" |
| `borg/eval/e1a_django_full/results/E1A_DJANGO_FULL_results.json` | 59 | `"p_value": 0.03125` |
| `borg/eval/E1_SERIES_REPORT.md` | 15, 69 | "p=0.03125" |
| `borg/autoresearch/AUTORESEARCH_CONFIG.md` | 18, 26 | "40%→90% (+50pp)" |

The SKILL.md file is the highest-priority fix because it is actively consulted by agents. The Borg PRD and downstream eval docs should carry a correction banner, not necessarily be rewritten, because the audit doc itself is the source of truth for future reference.

---

## Recommendation for Scope 3

1. **Do not** cite the +50pp / p=0.031 number anywhere in the new experiment design.
2. **Do** cite the honest n=7, p=0.125 finding as the *starting prior*. It is directionally useful — 3/3 discordant favor traces, zero negative transfer — but the null cannot be rejected.
3. **Scope 3 should be powered to actually decide the question** — pre-register the n, pre-register the primary test (McNemar one-tailed), pre-register the minimum-detectable-effect, and pre-register a stopping rule that does not allow post-hoc additions of tasks to cross the α threshold.
4. **No more result files named `FINAL_RESULTS_v2`** without a raw run log for every cell.
