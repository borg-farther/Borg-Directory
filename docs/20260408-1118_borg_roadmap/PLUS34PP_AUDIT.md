# Prior Claims Audit — "+34pp on hard tasks" (V2 Reasoning Traces)

**Audit date:** 2026-04-08 11:28 UTC
**Auditor:** Subagent (forensic read-only pass, Priority 1.0 of BORG_TESTING_ROADMAP_20260408)
**Subject:** The claim `V2 reasoning traces → +34 percentage point improvement on hard tasks`
  as asserted in
  `borg/docs/BORG_E2E_PRD_20260402.md` (9 occurrences),
  `borg/FINAL_EXPERIMENT_REPORT.md`,
  `borg/EXPERIMENT_FINAL_REPORT_V2.md`,
  `borg/EXPERIMENT_V2_DESIGN.md`,
  `borg/EXPERIMENT_V2_STATUS.md`,
  and 2 skill descriptions in `.hermes/skills/`.
**Companion to:** `docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md`
  (which determined the separate `p=0.031, A=40% → B=90%, +50pp` claim was fabricated).

---

## Executive Verdict

**PARTIALLY SUPPORTED** — a real raw dataset exists
(`dogfood/final_experiment_data.json`, committed 2026-04-02 in 8a43f8a) with
3 hard tasks (HARD-004, HARD-006, HARD-015), 1 run each under Condition A
(no cache) and Condition B (correct reasoning trace). The data shows
**A=1/3 PASS (33.3%), B=2/3 PASS (66.7%), raw difference = +33.3pp
(rounded to "+34 percentage points" inside the JSON itself)**. The
direction matches the claim. However:

1. **n=3 single runs** is insufficient for any statistical claim.
   Recomputed McNemar exact two-tailed **p = 1.0**
   (one discordant pair, b=0/c=1).
   One-tailed binomial on the single discordant pair: p = 0.5.
   95% CI on B−A is essentially (−∞, +∞): the data contains effectively
   zero statistical information.

2. The original source document (`FINAL_EXPERIMENT_REPORT.md`, 2026-03-31)
   **is honest**: it explicitly states "n=3 hard task pairs is too small
   for formal statistical testing", "What we CANNOT say: Statistical
   significance (p-value) — insufficient n", and labels the finding
   "preliminary results that indicate direction, not proof".

3. But **downstream propagation stripped those caveats**. In particular,
   `BORG_E2E_PRD_20260402.md` contains two **fabricated significance
   annotations** around the +34pp number:
   - Line 454: `| Hard tasks | 8% | 42% | +34pp | < 0.05 | YES |`
     (framed as "Expected Results" table, but presented next to a claimed
     p<0.05 that does not exist in any dataset)
   - Lines 1005-1010: `HARD TASKS (difficulty=hard): Control: 8%,
     Treatment: 42%, Delta: +34pp, p-value: 0.001, SIGNIFICANT: YES`
     (framed as an ACCEPTANCE TEST "RESULT" block). **p=0.001 is not
     computable from n=3; it is a fabricated number.**

4. The raw baseline numbers in the BORG_E2E_PRD expected-results table
   (8% and 42% with +34pp delta) **do not match the actual
   final_experiment_data.json** which has 33% → 67%. The "8% → 42%"
   framing is a different fabrication layered on top of the real +34pp
   directional finding.

**Summary:** the +34pp directional observation is supported by a real
n=3 experiment at exactly the claimed magnitude (within 0.67pp rounding).
The claim becomes UNSUPPORTED / FABRICATED the moment it is used in a
context that implies statistical significance, and the specific
"8% → 42%, p<0.05, p=0.001, SIGNIFICANT YES" framing in
`BORG_E2E_PRD_20260402.md` lines 454 and 1005-1010 is a second
fabrication on top of the honest pilot number.

---

## Claim enumeration

### Category 1 — Direct claim with n=3 context (honest or near-honest)

| File | Line | Exact text | Assessment |
|------|------|------------|------------|
| `borg/FINAL_EXPERIMENT_REPORT.md` | 30 | "+34 percentage point improvement on hard tasks." | HONEST in context — same doc says n=3, not significant, preliminary |
| `borg/FINAL_EXPERIMENT_REPORT.md` | 66 | "Effect size on hard tasks: +34pp success rate (large effect)" | HONEST in context — inside "What we CAN say" section, balanced by "What we CANNOT say: Statistical significance" |
| `borg/FINAL_EXPERIMENT_REPORT.md` | 98 | "reasoning traces help on hard tasks (+34pp success rate)" | HONEST in context — inside "CONDITIONAL GO" section that immediately notes n=3 insufficient |
| `borg/EXPERIMENT_FINAL_REPORT_V2.md` | 87 | "Improvement \| +34pp \| +43pp \|" | HONEST — comparison table labels row as "Pilot (synthetic)" vs "SWE-bench" |
| `borg/EXPERIMENT_FINAL_REPORT_V2.md` | 92 | "REPLICATES the pilot finding... with a LARGER effect size (+43pp vs +34pp)" | HONEST — pilot finding is explicitly labeled as such |
| `borg/dogfood/final_experiment_data.json` | 40 | `"difference": "+34 percentage points"` | HONEST — but arithmetic is slightly wrong (1/3→33%, 2/3→67%, 67−33=34, true value is 33.33) |
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md` | 133 | "V2 (reasoning traces +34pp on n=3)" | HONEST — explicitly notes n=3 |

### Category 2 — Claim without n=3 / not-significant context (misleading)

| File | Line | Exact text | Assessment |
|------|------|------------|------------|
| `borg/docs/BORG_E2E_PRD_20260402.md` | 58 | "V2: Reasoning traces +34pp on hard tasks" | MISLEADING — no n=3 qualifier, presented as confirmed evidence |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 76 | "SWE-bench improvement \| +34pp (lab)" | MISLEADING — (lab) implies measured lab result; no n=3 |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 423 | "E2E Outcome Improvement... +34pp (lab)" | MISLEADING — framed as a measured Current value in a Success Metrics table |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 630 | "V2 results: reasoning traces +34pp (baseline)" | MISLEADING — framed as a baseline to improve from |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 1411 | "V2: Reasoning traces only... Result: +34pp on hard tasks" | MISLEADING — in an experiment log with no n |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 1431 | "Targeted intelligence: +34pp vs baseline" | MISLEADING — generic effect-size claim |
| `.hermes/skills/research/rigorous-agent-experiment-design/SKILL.md` | 90 | "+34pp success rate on HARD tasks, not token reduction" | MISLEADING — in "pitfalls discovered" list, no n=3 |
| `borg/EXPERIMENT_V2_DESIGN.md` | 126 | "Expected effect: +34pp (based on pilot)" | DEPENDENT — power-analysis assumption built on n=3 observation |
| `borg/EXPERIMENT_V2_DESIGN.md` | 136 | "If true effect = 34pp: ~85% power at alpha = 0.05" | DEPENDENT — power-analysis assumption |
| `.hermes/skills/research/rigorous-agent-experiment-design/SKILL.md` | 126 | "McNemar's at n=25 pairs, alpha=0.05: detects 34pp effect with ~85% power" | DEPENDENT — power-analysis pedagogical example |

### Category 3 — FABRICATED SIGNIFICANCE ANNOTATIONS (layered on top)

| File | Line | Exact text | Assessment |
|------|------|------------|------------|
| `borg/docs/BORG_E2E_PRD_20260402.md` | 454 | `\| Hard tasks \| 8% \| 42% \| +34pp \| < 0.05 \| YES \|` | **FABRICATED** — no dataset supports p<0.05 for any +34pp claim; no dataset has 8%→42% baseline |
| `borg/docs/BORG_E2E_PRD_20260402.md` | 1005-1010 | "HARD TASKS... Control: 8%, Treatment: 42%, Delta: +34pp, p-value: 0.001, SIGNIFICANT: YES" | **FABRICATED** — p=0.001 is not computable from n=3; baseline numbers don't match the real data (which is 33%→67%) |

### Category 4 — Historical / hypothetical / memory file

| File | Line | Exact text | Assessment |
|------|------|------------|------------|
| `hermes-workspace/memory/observations.md` | 131 | "Hard tasks: +34pp success rate with correct trace (33%→67%)" | HONEST — exact raw data match |
| `hermes-workspace/memory/observations.md` | 134 | "Borg experiment concluded (+34pp hard tasks)" | HONEST in context — chronological entry |
| `borg/EXPERIMENT_V2_STATUS.md` | 69 | "Even a 34pp improvement on that 9% = 3% overall improvement" | HONEST — explicitly hypothetical ("even a ... would be ...") |

---

## Provenance chain

### Commit where the data file first appeared

```
commit 8a43f8a57de6c2d2636e4840d380242a6255a5a4
Author: root <root@example.server>
Date:   Thu Apr 2 12:44:24 2026 +0000

    feat: E2E learning loop v2 — all 8 PRD items implemented and verified
```

This single commit introduced all of:
- `dogfood/final_experiment_data.json` (the raw data)
- `FINAL_EXPERIMENT_REPORT.md` (the honest write-up)
- `EXPERIMENT_FINAL_REPORT_V2.md`
- `EXPERIMENT_V2_DESIGN.md`
- `EXPERIMENT_V2_STATUS.md`
- `docs/BORG_E2E_PRD_20260402.md`

Note the `timestamp: "2026-03-31"` inside the JSON: the experiment was
allegedly run 2 days before the commit landed.

### Data file existence check

`dogfood/final_experiment_data.json` — **EXISTS, 47 lines, readable.**

Contents (condensed):
```
HARD-001: A/B/C all PASS (both runs)   ← "easy" task, 100% baseline
HARD-002: A/B/C all PASS (both runs)   ← "easy" task, 100% baseline
HARD-004: A=FAIL (1 run), B=FAIL (1 run)
HARD-006: A=PASS (1 run), B=PASS (1 run)
HARD-015: A=FAIL (1 run), B=PASS (1 run)
```

Only the three "hard" tasks (004, 006, 015) drive the +34pp claim.

### Raw data truthfulness

The raw JSON data **is consistent with itself** — no obvious post-hoc
edits, no contradictory `calibration.json` flagging "test patch not
properly applied" notes of the kind that contaminated the p=0.031
dataset. Unlike the p=0.031 fabrication, there are no missing B runs,
no unexplained outcome flips, and no separate data file that contradicts
this one.

### The fabrication on top: BORG_E2E_PRD 8%→42% numbers

The `BORG_E2E_PRD_20260402.md` lines 454 and 1005-1010 use **different
raw numbers**: 8% control, 42% treatment, +34pp delta, p<0.05 / p=0.001,
"SIGNIFICANT YES". These cannot be derived from the final_experiment_data.json:

- 8% and 42% do not appear in `final_experiment_data.json`.
- 8% and 42% do not correspond to any ratio of integers reachable with
  n=3 (possible values: 0, 33.33%, 66.67%, 100%).
- p=0.001 is not reachable from any n=3 paired binary outcome (the
  minimum exact McNemar p at n=3 is 0.25, not 0.001).
- The "+34pp" delta is preserved across a different baseline (8 vs 33),
  suggesting someone took the pilot delta and invented new absolute
  baselines to make it look like a real SWE-bench protocol result.

These lines are in subsections explicitly titled "Expected Results" (§4.2.2)
and "ACCEPTANCE TEST" (§8.4), so they can be defended as
*hypothetical pre-registration* — but they are formatted as a results
table and do not say "hypothetical" or "target" anywhere nearby. A
casual reader will read them as measured results. This is the exact
same "hypothetical becomes real" failure mode that produced the
p=0.031 fabrication.

---

## Raw data — computed statistics

**Source:** `hermes-workspace/borg/dogfood/final_experiment_data.json`
**Computed with:** `/usr/bin/python3.12`, `scipy.stats`, `statsmodels.stats.contingency_tables`

### Hard tasks, paired A vs B

```
Task       A (no cache)   B (correct trace)
HARD-004   FAIL           FAIL
HARD-006   PASS           PASS
HARD-015   FAIL           PASS

n_tasks (paired) = 3
runs per cell    = 1
A pass rate      = 1/3 = 33.33%
B pass rate      = 2/3 = 66.67%
Raw difference   = +33.33pp  (JSON says "+34", off by 0.67)
```

### 2x2 contingency table (rows=A outcome, cols=B outcome)

```
          B=PASS  B=FAIL
A=PASS       1       0
A=FAIL       1       1

Discordant pairs: b+c = 0+1 = 1  (only HARD-015 flipped)
```

### Statistical tests

| Test | Statistic | p-value |
|------|-----------|---------|
| McNemar exact (two-tailed) | b=0, c=1 | **p = 1.0000** |
| One-tailed binomial (B > A), k=1/n_disc=1, p0=0.5 | 1 success of 1 trial | **p = 0.5000** |
| Clopper-Pearson 95% CI on A rate (1/3) | — | **(0.84%, 90.6%)** |
| Clopper-Pearson 95% CI on B rate (2/3) | — | **(9.4%, 99.2%)** |

### Comparison to claimed value

| Source | Claimed statistic | Supported by data? |
|--------|-------------------|---------------------|
| `FINAL_EXPERIMENT_REPORT.md` | "+34pp, n=3, not statistically significant" | **YES** (modulo 0.67pp rounding) |
| `final_experiment_data.json` | `"difference": "+34 percentage points"` | **YES** (with same rounding caveat) |
| `BORG_E2E_PRD_20260402.md:454` | "+34pp, p<0.05, YES significant" | **NO — fabricated significance** |
| `BORG_E2E_PRD_20260402.md:1008` | "+34pp, p=0.001, SIGNIFICANT: YES" | **NO — fabricated, impossible from n=3** |
| `BORG_E2E_PRD_20260402.md:454` baselines | "8% control, 42% treatment" | **NO — data has 33%/67%** |
| `EXPERIMENT_V2_DESIGN.md:126` | "+34pp (based on pilot)" as power-analysis input | YES as an assumption, but the pilot has no statistical resolution to motivate it |

### Effect-size CI sanity check

With n=3 and 1 discordant pair, the approximate 95% CI on the paired
difference B−A spans roughly (−67pp, +100pp). **The observed +33.3pp is
not distinguishable from zero at any conventional confidence level.**
Any statement of the form "+34pp is a validated effect" is
statistically unsupported regardless of whether the raw numbers
themselves exist.

---

## What the honest claim looks like

```
Pilot experiment (2026-03-31): 3 hard synthetic tasks (HARD-004/006/015),
single runs per condition, Condition A (no trace) vs Condition B
(correct reasoning trace). A=1/3, B=2/3, raw difference +33.3pp
(one task flipped FAIL→PASS with trace). n=3 is too small for
statistical inference: McNemar exact p=1.0 (two-tailed),
one-tailed binomial p=0.5. The direction is suggestive but the data
contain essentially zero statistical information. This is a
directional pilot finding, not evidence. See
docs/20260408-1118_borg_roadmap/PLUS34PP_AUDIT.md.
```

---

## Files to patch

**High priority** (claim cited without n=3 context, or with fabricated
significance annotations):

1. `borg/docs/BORG_E2E_PRD_20260402.md` (9 occurrences across 8 lines)
   — especially lines 454 and 1005-1010 which contain fabricated
   p<0.05 / p=0.001 annotations around the +34pp number
2. `.hermes/skills/research/rigorous-agent-experiment-design/SKILL.md`
   — line 90 (cited without n=3 context)

**Medium priority** (claim used as an assumption in a power analysis):

3. `borg/EXPERIMENT_V2_DESIGN.md` — lines 126, 136
4. `.hermes/skills/research/rigorous-agent-experiment-design/SKILL.md`
   — line 126 (power-analysis example)

**Low priority** (already honest in context; add audit pointer):

5. `borg/FINAL_EXPERIMENT_REPORT.md` — add pointer to audit
6. `borg/EXPERIMENT_FINAL_REPORT_V2.md` — add pointer to audit
7. `.hermes/skills/software-development/experiment-before-architecture/SKILL.md`
   — line 133 already says "n=3", add pointer
8. `hermes-workspace/memory/observations.md` — extend existing
   top-of-file correction header to cover +34pp

**No patch needed** (the JSON is forensic evidence; the raw data is
consistent with itself):

- `borg/dogfood/final_experiment_data.json` — preserved as evidence.
  (Could optionally add a `_CORRECTION_20260408_1128` field noting that
  the arithmetic rounds 1/3→33% and 2/3→67% to get +34pp rather than
  the true +33.33pp; this is a minor accuracy note, not a fabrication
  marker.)

---

## Correction banner to insert

```
[CORRECTION 20260408-1128] Prior citation of '+34pp on hard tasks' was
audited 20260408-1128 and determined to be PARTIALLY SUPPORTED (raw data
exists with correct direction) but statistically insufficient. Actual
measured: n=3 hard synthetic tasks (HARD-004/006/015), single runs per
cell, Condition A (no trace) = 1/3 PASS (33.3%), Condition B (correct
trace) = 2/3 PASS (66.7%), raw difference +33.3pp, 1 discordant pair,
McNemar exact p=1.0 (two-tailed), one-tailed binomial p=0.5. The
direction is consistent with the claim but the data contain essentially
zero statistical information. Any use of "+34pp" without the n=3 / not
statistically significant qualifier is misleading. The companion
BORG_E2E_PRD_20260402.md:454 and :1008 annotations of "p<0.05 YES" and
"p=0.001 SIGNIFICANT: YES" around this number are FABRICATED and do
not exist in any dataset. See docs/20260408-1118_borg_roadmap/PLUS34PP_AUDIT.md.
```

---

## Recommendation for downstream roadmap

1. **Do not** cite +34pp anywhere without the n=3 / McNemar p=1.0
   qualifier. The honest characterization is "n=3 pilot, 1/3 → 2/3,
   directional only, not statistically significant".

2. **Do not** cite the 8% → 42% baseline/treatment numbers anywhere.
   Those are not in any dataset.

3. **Do** retain the finding as a *pilot observation* worth replicating
   at a powered sample size. The pilot is not disqualified; it is merely
   too small to decide anything.

4. **Companion to the p=0.031 audit:** unlike p=0.031, this claim is not
   a pure fabrication — the raw data file exists, the arithmetic is
   approximately right, and the original report was honest. The failure
   mode here is **caveat stripping** across 8 downstream citations,
   plus one new fabrication (8%/42%/p=0.001) layered on top in
   BORG_E2E_PRD_20260402.md.

5. **Pattern**: this is the same failure mode observed in the p=0.031
   case — a hypothetical/aspirational number in an acceptance-test
   template gets read as a measured result and propagates downstream.
   Future PRDs must mark expected/hypothetical numbers with an explicit
   `(HYPOTHETICAL)` or `(TARGET)` tag wherever they appear in tables.
