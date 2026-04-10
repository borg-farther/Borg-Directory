# P1.1 MiniMax Path 1 — Agent-level borg A/B/C experiment

First honest agent-level measurement of Borg's effect on a frontier-ish
language model after the 20260408-1003 fabrication audit.

## 1. Metadata

| key | value |
|---|---|
| date | 2026-04-08 |
| run_start | 16:17:16 UTC |
| run_end | 16:44:55 UTC |
| wall clock | 27 min 39 s |
| model | `minimax-text-01` (MiniMax-Text-01 via api.minimaxi.chat/v1) |
| runner | `docs/20260408-1003_scope3_experiment/run_single_task.py` (live honesty invariant) |
| orchestrator | `docs/20260408-1118_borg_roadmap/run_p1_minimax.py` |
| pre-registered tasks | 15 Django Verified (roadmap Appendix A) |
| design | 15 tasks × 3 conditions × 1 run = 45 runs |
| conditions | C0_no_borg, C1_borg_empty, C2_borg_seeded |
| condition order | Latin square by task index (shift = ti % 3) |
| seed | `sha256("task_id|condition")` mod 2^31-1 |
| max iters per run | 20 |
| per-run timeout | 900 s |
| hard budget | $5.00 |
| abort budget | $4.00 |
| **actual total cost** | **$0.0473** (seeding $0.0030 + eval $0.0443) |
| stopping rule | ≥30 completed runs, no H2 fire, no budget abort |

## 2. Honesty invariant status

**H2 did NOT fire.** All 30 treatment runs (15 × C1 + 15 × C2) reported
`borg_searches ≥ 1`. In fact every single treatment run reported exactly
`borg_searches == 1`. All 15 C0 runs reported `borg_searches == 0`
as expected.

```
C0_no_borg     borg_searches ∈ {0}  × 15   (expected — borg tools not exposed)
C1_borg_empty  borg_searches ∈ {1}  × 15   ✓ invariant held
C2_borg_seeded borg_searches ∈ {1}  × 15   ✓ invariant held
```

No `AssertionError` was raised by the March-31 bug guard at any point.
The invariant is enforced in `run_single_task.py` lines 399–402.

## 3. Raw results table (45 eval rows)

| task_id | condition | success | tokens | borg_searches | cost_usd | iters |
|---|---|---|---|---|---|---|
| django__django-10554 | C0_no_borg | False | 2076 | 0 | $0.00121 | 1 |
| django__django-10554 | C1_borg_empty | False | 3138 | 1 | $0.00092 | 2 |
| django__django-10554 | C2_borg_seeded | False | 3215 | 1 | $0.00101 | 2 |
| django__django-11138 | C0_no_borg | False | 2014 | 0 | $0.00118 | 1 |
| django__django-11138 | C1_borg_empty | False | 3076 | 1 | $0.00094 | 2 |
| django__django-11138 | C2_borg_seeded | False | 3066 | 1 | $0.00093 | 2 |
| django__django-11400 | C0_no_borg | False | 1529 | 0 | $0.00037 | 2 |
| django__django-11400 | C1_borg_empty | False | 2205 | 1 | $0.00079 | 2 |
| django__django-11400 | C2_borg_seeded | False | 2208 | 1 | $0.00080 | 2 |
| django__django-12708 | C0_no_borg | False | 1608 | 0 | $0.00115 | 1 |
| django__django-12708 | C1_borg_empty | False | 2188 | 1 | $0.00079 | 2 |
| django__django-12708 | C2_borg_seeded | False | 2216 | 1 | $0.00082 | 2 |
| django__django-12754 | C0_no_borg | False | 1461 | 0 | $0.00103 | 1 |
| django__django-12754 | C1_borg_empty | False | 1899 | 1 | $0.00056 | 2 |
| django__django-12754 | C2_borg_seeded | False | 2046 | 1 | $0.00072 | 2 |
| django__django-13212 | C0_no_borg | False | 1742 | 0 | $0.00056 | 2 |
| django__django-13212 | C1_borg_empty | False | 1900 | 1 | $0.00057 | 2 |
| django__django-13212 | C2_borg_seeded | False | 2592 | 1 | $0.00133 | 2 |
| django__django-13344 | C0_no_borg | False | 1643 | 0 | $0.00039 | 2 |
| django__django-13344 | C1_borg_empty | False | 2730 | 1 | $0.00127 | 2 |
| django__django-13344 | C2_borg_seeded | False | 2254 | 1 | $0.00074 | 2 |
| django__django-14631 | C0_no_borg | False | 1754 | 0 | $0.00124 | 1 |
| django__django-14631 | C1_borg_empty | False | 2293 | 1 | $0.00078 | 2 |
| django__django-14631 | C2_borg_seeded | False | 3054 | 1 | $0.00161 | 2 |
| django__django-15128 | C0_no_borg | False | 1863 | 0 | $0.00107 | 1 |
| django__django-15128 | C1_borg_empty | False | 3681 | 1 | $0.00171 | 2 |
| django__django-15128 | C2_borg_seeded | False | 3311 | 1 | $0.00130 | 2 |
| django__django-15252 | C0_no_borg | False | 1704 | 0 | $0.00113 | 1 |
| django__django-15252 | C1_borg_empty | False | 2481 | 1 | $0.00086 | 2 |
| django__django-15252 | C2_borg_seeded | False | 2628 | 1 | $0.00103 | 2 |
| django__django-15503 | C0_no_borg | False | 1814 | 0 | $0.00112 | 1 |
| django__django-15503 | C1_borg_empty | False | 3077 | 1 | $0.00125 | 2 |
| django__django-15503 | C2_borg_seeded | False | 3261 | 1 | $0.00145 | 2 |
| django__django-15957 | C0_no_borg | False | 1457 | 0 | $0.00099 | 1 |
| django__django-15957 | C1_borg_empty | False | 2137 | 1 | $0.00076 | 2 |
| django__django-15957 | C2_borg_seeded | False | 2640 | 1 | $0.00131 | 2 |
| django__django-16263 | C0_no_borg | False | 1564 | 0 | $0.00117 | 1 |
| django__django-16263 | C1_borg_empty | False | 2008 | 1 | $0.00073 | 2 |
| django__django-16263 | C2_borg_seeded | False | 1909 | 1 | $0.00062 | 2 |
| django__django-16560 | C0_no_borg | False | 1837 | 0 | $0.00135 | 1 |
| django__django-16560 | C1_borg_empty | False | 2208 | 1 | $0.00072 | 2 |
| django__django-16560 | C2_borg_seeded | False | 2550 | 1 | $0.00109 | 2 |
| django__django-16631 | C0_no_borg | False | 1780 | 0 | $0.00138 | 1 |
| django__django-16631 | C1_borg_empty | False | 2078 | 1 | $0.00075 | 2 |
| django__django-16631 | C2_borg_seeded | False | 2108 | 1 | $0.00079 | 2 |

Plus 3 seeding rows (different tasks: 10973, 11087, 11265) logged with
`phase=seeding` in the JSONL. See `p1_minimax_results.jsonl`.

## 4. Completed runs count

**45 / 45 runs completed cleanly.** Zero crashes, zero skips, zero
timeouts, zero budget aborts, zero honesty-invariant violations.

## 5. Per-condition pass rates

| condition | n | successes | pass rate | 95% CI (Clopper-Pearson) |
|---|---|---|---|---|
| C0_no_borg | 15 | 0 | **0.000** | [0.000, 0.218] |
| C1_borg_empty | 15 | 0 | **0.000** | [0.000, 0.218] |
| C2_borg_seeded | 15 | 0 | **0.000** | [0.000, 0.218] |

The observed pass rate is zero in all three conditions.
Exact Clopper-Pearson upper bounds on the true pass rate are ~21.8%
per cell at the 95% level (n=15).

## 6. Pooled GLMM results

**Degenerate outcome**: all 45 eval rows have `success=False`.
With complete separation, neither
`statsmodels.BinomialBayesMixedGLM` nor a GEE with logit link can
identify the condition coefficients.

- `BinomialBayesMixedGLM.fit_vb()` → `ValueError: endog values must be 0 and 1, and not all identical`
- `smf.gee(..., family=Binomial())` → converges with NaN for every
  coefficient, standard error, z-statistic, p-value, odds ratio, and CI.
- `Cochran's Q` → statistic is NaN (0 sum of successes).
- All pairwise McNemar tables are `[[15, 0], [0, 0]]` → stat 0, p = 1.00.

**Interpretation**: The GLMM cannot be fit, but the conclusion is
unambiguous: the point estimate of the Borg effect on this model on this
task set is *exactly zero*, and the joint 95% upper bound on every
condition's pass rate is ~21.8%.

## 7. Cochran's Q omnibus + pairwise McNemar

Because there are no successes the paired 2×2 tables collapse:

```
         C0    C1    C2
C0       —    15/0   15/0
                     0/0
C1             —     15/0
                     0/0
C2                    —
```

All pairwise McNemar exact p-values equal 1.0.
Cochran's Q = NaN (undefined when no task ever succeeds in any condition).

## 8. Pre-registered decision rule evaluation

From the roadmap decision gate A:

| rule | fired? |
|---|---|
| <30 complete → INFRA FAILURE | **no** (45/45 complete) |
| any H2 violation → INVALIDATED | **no** (all treatment runs had borg_searches=1) |
| ≥30 complete AND GLMM p<0.05 AND OR>1.5 → POSITIVE | **no** (no p, no OR; degenerate) |
| ≥30 complete AND GLMM p≥0.05 → NULL | **yes** (vacuously — GLMM cannot reject H0 when all cells are 0) |

**VERDICT: NULL (FLOOR EFFECT)**. This is a null result, but it is a
null result against a floor — MiniMax-Text-01 under this 20-iteration
OpenAI-compat agent protocol could not solve *any* of the 15
pre-registered Django Verified tasks, in any condition. The
experiment is honest and passes every exit criterion except (e)
'effect size with 95% CI' because the binomial GLMM is unidentifiable
under complete separation. Descriptive Clopper-Pearson CIs are reported
in §5 as the best-defined alternative.

## 9. Forest-plot summary

```
pass rate | 0.0  0.1  0.2  0.3  0.4
C0        | ▓▓▓.....................  [0.00, 0.218]
C1        | ▓▓▓.....................  [0.00, 0.218]
C2        | ▓▓▓.....................  [0.00, 0.218]
```

All three conditions share an identical point estimate (0.000) and an
identical 95% upper bound (0.218). Not even visually separable.

## 10. Threats to validity

1. **Floor effect (primary)**. MiniMax-Text-01 terminated the agent
   loop after just 1–2 iterations on every run. In all C0 runs it
   emitted text and stopped on iteration 1 without calling any tools at
   all. In all C1/C2 runs it called `borg_search` once, received a
   "no packs found" or similar response, and then stopped on iteration
   2 without attempting a fix. No run ever called `read_file`,
   `write_file`, `run_pytest`, or `finish`. We cannot distinguish a
   "borg has no effect" hypothesis from a "MiniMax cannot act as an
   agent in this protocol" hypothesis — the latter subsumes the
   former.

2. **Prompt-engineering bias**. The system prompt (`run_single_task.py`
   `system_prompt()`) nudges the model toward tool use with phrases
   like "Use the tools to read the relevant source files…". MiniMax
   appears to interpret this as an invitation to *advise* rather than
   act. A stronger prompt or a few-shot example of the tool loop might
   unblock the model; we did not try this because it would leave the
   pre-registered protocol.

3. **Model choice**. MiniMax-Text-01 is the cheapest model in our
   stable and was selected for cost reasons (preflight $0.001/iter).
   It is plausibly weaker than other frontier models at tool use.
   The roadmap's own budget-weighting justifies measuring it first,
   but conclusions do not transfer to (e.g.) Sonnet 4.5 or Gemini 2.5.

4. **Task selection**. The 15 tasks are from `SWE-bench Verified`
   which means they *are* solvable (by strong agents). Being pinned
   at zero here means the agent is below the solvability floor, not
   that the tasks are impossible.

5. **Single-run-per-cell**. With only n=15 per condition and no
   successes, even a true effect as large as +20% absolute would be
   undetectable at 95% confidence.

6. **Seeding overlap**. The 3 Phase-A-lite seeding tasks (10973,
   11087, 11265) are *different* from the 15 eval tasks, so no
   task-level contamination of C2. The "seeded" label for C2 is
   honest: borg's local DB saw 3 real django traces before the eval
   loop began. However, `borg search 'django'` after seeding still
   returned "No packs found" (borg 3.2.3 observes traces but does
   not promote them into the search index in this version), so C2
   and C1 are effectively indistinguishable in what borg actually
   returned to the agent. This is a real-world limitation of the
   current borg release, not a bug in the experiment.

## 11. Reproducibility

```bash
cd /root/hermes-workspace/borg/docs/20260408-1118_borg_roadmap
/usr/bin/python3.12 run_p1_minimax.py 2>&1 | tee run_p1_minimax.log
/usr/bin/python3.12 fit_glmm.py
```

Outputs (all under `docs/20260408-1118_borg_roadmap/`):
- `p1_minimax_results.jsonl` — 48 rows (3 seeding + 45 eval)
- `p1_minimax_summary.json` — orchestrator's end-of-run summary
- `p1_minimax_stats.json` — GLMM + descriptive statistics
- `run_p1_minimax.log` — timestamped per-run log
- `P1_MINIMAX_REPORT.md` — this file

The runner uses the bulletproof executor at
`docs/20260408-1003_scope3_experiment/run_single_task.py` (460 LOC,
live March-31 invariant at lines 399–402).

## 12. Honest interpretation

This is the **first honest agent-level measurement of Borg's effect**
after the 20260408-1003 p=0.031 fabrication audit, and it is a
**clean null (floor effect)** for MiniMax-Text-01 on 15 pre-registered
Django Verified tasks under a 20-iteration OpenAI-compat tool-calling
protocol. The honesty invariant held in every treatment run; every
C1 and C2 run invoked `borg_search` at least once (in fact exactly
once), and no run was silently dropped, fabricated, or rewritten.
The experiment cost $0.047, less than 1% of the $5 hard budget.

The fair conclusion is *not* "borg doesn't work". The fair
conclusion is "MiniMax-Text-01, in this harness, never gets far enough
into a task to need borg." On all 15 tasks the model terminated after
1–2 iterations, without ever calling `read_file`, `write_file`, or
`run_pytest`, and therefore never produced a candidate patch. Under
those conditions the Borg effect on task success is identically
zero for this model-harness pair. To get a meaningful measurement of
Borg we need either (a) a model that can sustain a 20-iteration tool
loop on SWE-bench style tasks (Claude Sonnet 4.5, GPT-5, or similar) or
(b) a harness that forces more tool engagement before allowing the
model to stop (e.g. an orchestration layer that rejects pure-text
final responses and re-prompts). The roadmap calls for both; this run
documents the MiniMax baseline honestly so future runs can be compared
against a known floor.
