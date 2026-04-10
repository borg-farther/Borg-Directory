# Third Honesty Sweep — Audit Report
**Date:** 2026-04-08 12:16 UTC
**Auditor:** Claude Code subagent (third pass)
**Scope:** Every statistical-claim hit not already covered by audits 1 (p=0.031) or 2 (+34pp).
**Tools:** `/usr/bin/python3.12`, `scipy.stats`, `ripgrep`

---

## Executive Verdict

**NEW fabrications found: 0.**
**NEW unsupported / caveat-stripped claims found: 1 (the +43pp SWE-bench statistic, propagated 5 times without n=7/p=0.125 qualifier).**
**Other significant statistical numbers checked: all SUPPORTED by the underlying raw data.**

The third pass did NOT find a third fabricated statistic. It DID find that
the +43pp success-rate delta (n=7 SWE-bench Django) — which is a real,
honest, mathematically-correct number derivable from the unfabricated
`dogfood/v2_data/swebench_results/FINAL_RESULTS.json` — has the SAME
caveat-stripping failure mode as the +34pp pilot claim. The number
itself is correct (42.857pp rounds to 43pp). But it is propagated in
five locations as "evidence", "proven", or "validated" without the
n=7 / McNemar p=0.125 / not statistically significant qualifier.

This is the same family of failure as the +34pp finding from audit 2:
the original report (`EXPERIMENT_FINAL_REPORT_V2.md`) is honest;
downstream citations strip the caveats.

---

## Per-Claim Audit Table

| File:line | Claim | Source data | Computed stat | Verdict |
|-----------|-------|-------------|---------------|---------|
| `borg/STRATEGIC_SYNTHESIS.md:9-13` | "On 7 real SWE-bench Django tasks: 43% → 86%, +43pp, zero negative transfer, 3/3 discordant pairs" | `dogfood/v2_data/swebench_results/FINAL_RESULTS.json` | n=7, A=3/7=42.86%, B=6/7=85.71%, +42.86pp, b=0 c=3, McNemar exact one-sided p=0.125, two-sided p=0.25 | **NUMBERS SUPPORTED**, but next bullet says "+43pp" without "not significant" — **caveat-stripped** in lines 12, 34, 64, 104 |
| `borg/COMPETITIVE_ANALYSIS.md:174` | "Already proven +43pp on SWE-bench" | same | same | **CAVEAT-STRIPPED** — uses "proven" for n=7 p=0.125 result; not a fabrication but technically false because not statistically significant |
| `borg/docs/BORG_PACK_AUTO_GENERATION_PRD.md:185` | "The prior experiment (+43pp with traces) proved that investigation trails help" | same | same | **CAVEAT-STRIPPED** — uses "proved"; n=7 p=0.125 does not "prove" anything |
| `borg/EXPERIMENT_FINAL_REPORT_V2.md:33,59,69,86,96,101` | Various +43pp citations | same | same | **HONEST IN CONTEXT** — same file states n=7, McNemar p=0.125, "not significant", AUDIT POINTER block at top |
| `borg/BORG_PRD_FINAL.md:89` | "+43pp directional success-rate improvement on SWE-bench Django tasks (3/7 → 6/7)" | same | same | **HONEST** — explicit "directional", explicit 3/7→6/7 |
| `borg/DIFFICULTY_DETECTOR.md:9-14` | "n=7, 3/7 (43%), 6/7 (86%), +43pp, McNemar p=0.125, NOT significant" | same | same | **HONEST** — fully qualified |
| `borg/EXPERIMENT_REPORT.md:14` | "Tokens 1,365 → 1,547, +13.3% MORE, p=0.96" | `dogfood/all_results_v2.json` | n=19 paired, control mean 1365.05, treatment mean 1546.58, +13.30%, Wilcoxon one-sided H1 (treat<control) p=0.9615 | **SUPPORTED** — exactly matches |
| `borg/EXPERIMENT_REPORT.md:79` | "E1 Token reduction p=0.96 FAIL" | same | same | **SUPPORTED** |
| `borg/AUDIT_METHODOLOGY.md:140` | "n=19, p=0.96 for token reduction" | same | same | **SUPPORTED** |
| `borg/AUDIT_ACADEMIC.md:103` | "V1/V2 report... Wilcoxon test... p=0.96 (one-sided)" | same | same | **SUPPORTED** |
| `.hermes/skills/software-development/borg-defi-agent-stack/SKILL.md:66` | "19 pairs, +13.3% token overhead, p=0.96 NOT significant" | same | same | **SUPPORTED** |
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md:91` | "V2 (19 pairs) Tokens: Treatment +13.3% MORE (p=0.96, NOT significant)" | same | same | **SUPPORTED** |
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md:85` | "V1 (10 pairs) Tokens: Treatment +13.4% MORE (p=0.86, NOT significant)" | `dogfood/all_results.json` | n=10 paired, mean control 1533.6, mean treat 1738.5, +13.36%, Wilcoxon one-sided p=0.8623 | **SUPPORTED** |
| `borg/BORG_PRD_FINAL.md:79` | "django-13344: A failed 50 tool calls → B succeeded 11 tool calls. 4.5x efficiency" | not a paired-stat claim — single-anecdote | n/a | **ANECDOTAL** — labeled "validated" but it's a single-task observation, not a statistical claim. Already framed as anecdote in surrounding text; flag for stricter wording but no numerical fabrication |
| `borg/docs/BORG_E2E_PRD_20260402.md:407` | `"avg_improvement": "+18pp on hard tasks"` (in pack JSON template) | inside an example schema | n/a | **EXAMPLE PLACEHOLDER** — clearly an illustrative pack template, not a measured value. Acceptable. |

---

## Forensic detail — the +43pp caveat-stripping pattern

### What the data actually says

`borg/dogfood/v2_data/swebench_results/FINAL_RESULTS.json` is the
**honest** source (the n=10 sibling file `FINAL_RESULTS_v2.json` is the
fabricated one — already flagged in audit 1). Contents:

```
n_tasks         = 7
A success rate  = 3/7 = 0.42857... = 42.86%
B success rate  = 6/7 = 0.85714... = 85.71%
improvement     = 0.42857...       = 42.86 pp  (rounds to "+43pp")
flips_helped    = 3   (b=0, c=3 in McNemar table)
flips_hurt      = 0
both_pass       = 3
both_fail       = 1
n_discordant    = 3
p_value         = 0.125             (McNemar exact one-sided)
```

Computed by me with `/usr/bin/python3.12 + scipy.stats.binomtest`:

```
McNemar exact two-sided: p = 0.25
McNemar exact one-sided (B better): p = 0.125
```

The "+43pp" number is **mathematically correct** (42.86 rounded up).
The McNemar p=0.125 is **mathematically correct**. The data file is
internally consistent and matches what `EXPERIMENT_FINAL_REPORT_V2.md`
reports.

### The failure mode

In 5 downstream locations the number is cited without the n=7 / p=0.125 /
not-significant context:

1. `borg/STRATEGIC_SYNTHESIS.md:12` — "+43pp improvement, zero negative transfer" (no n, no p)
2. `borg/STRATEGIC_SYNTHESIS.md:34` — "**Evidence**: +43pp on SWE-bench" (presented as proof)
3. `borg/STRATEGIC_SYNTHESIS.md:64` — "**Evidence**: +43pp on SWE-bench coding tasks." (proof)
4. `borg/STRATEGIC_SYNTHESIS.md:104` — "Reasoning traces improve coding agent success by +43pp on real tasks" (declarative)
5. `borg/COMPETITIVE_ANALYSIS.md:174` — "Already **proven** +43pp on SWE-bench" (literally uses "proven")
6. `borg/docs/BORG_PACK_AUTO_GENERATION_PRD.md:185` — "The prior experiment (+43pp with traces) **proved** that investigation trails help" (literally uses "proved")

Two of these — the "proven" and "proved" framings in COMPETITIVE_ANALYSIS
and BORG_PACK_AUTO_GENERATION_PRD — are factually false: an n=7 paired
result with McNemar p=0.125 does not prove anything at α=0.05.

This is the same family of failure as the +34pp pilot caveat-stripping
documented in `PLUS34PP_AUDIT.md`. The number itself is honest; the
downstream propagation is not.

### Why this is NOT a fabrication

Unlike `p=0.031, +50pp, n=10` (audit 1) and the layered
"8% → 42%, p<0.05 / p=0.001" annotation in BORG_E2E_PRD_20260402.md
(audit 2), the +43pp number:
- exists in a real, internally-consistent data file on disk;
- equals the directional difference computed from that file (within
  rounding);
- accompanies an honest p=0.125 McNemar value in the source report
  (`EXPERIMENT_FINAL_REPORT_V2.md`);
- is not paired anywhere with a fabricated significance annotation.

It is a real result whose magnitude is correctly reported. The harm is
in stripping the "n=7, not significant" qualifier in five downstream
documents, including two that explicitly call it "proven".

### Recommended replacement language

For each caveat-stripped citation:

```
[CORRECTION 20260408-1216] Cited "+43pp on SWE-bench" was audited
20260408-1216. The raw +42.86pp delta is correct (n=7 paired Django
tasks, A=3/7, B=6/7, dogfood/v2_data/swebench_results/FINAL_RESULTS.json),
but McNemar exact p=0.125 (3 discordant pairs all favoring traces) is
NOT statistically significant at α=0.05. The result is directionally
positive with zero negative transfer, but the framing as "proven" /
"evidence" / declarative claim is unsupported. Use "+43pp directional
(n=7, McNemar p=0.125, not significant)" instead. See
docs/20260408-1216_third_audit/THIRD_SWEEP_AUDIT.md.
```

---

## Forensic detail — the V2 19-pair tokens claim (CONFIRMED HONEST)

I recomputed this from the raw data myself to be sure no fabrication
was hiding here.

**Source:** `borg/dogfood/all_results_v2.json` — 38 result records
(19 paired tasks × 2 conditions).

**Computation:**
```python
n = 19
control_mean_tokens = 1365.05
treatment_mean_tokens = 1546.58
% diff (treatment-control)/control = +13.30%
Wilcoxon one-sided H1 (treatment < control) p = 0.9615
Wilcoxon one-sided H1 (treatment > control) p = 0.0385
Wilcoxon two-sided p = 0.0770
Treatment success: 19/19; Control success: 18/19
```

The `EXPERIMENT_REPORT.md` claim of "+13.3% MORE, p=0.96" matches the
data exactly. **SUPPORTED.**

Note that the *opposite* one-sided test (treatment > control) is
significant at p=0.0385 — i.e. the data significantly shows treatment
uses MORE tokens, not fewer. The reports state this directionally but
do not invert the p-value to claim significance for "treatment is
worse". This is honest framing.

---

## Forensic detail — V1 10-pair tokens claim (CONFIRMED HONEST)

**Source:** `borg/dogfood/all_results.json` — 20 records, 10 paired.

```python
n = 10
control_mean = 1533.6
treatment_mean = 1738.5
% diff = +13.36%
Wilcoxon one-sided (treat<control) p = 0.8623
```

The skill claim "Treatment +13.4% MORE (p=0.86, NOT significant)" matches
exactly. **SUPPORTED.**

---

## Aspirational / pre-registered statistical thresholds (CAT_E)

The sweep encountered ~30 occurrences of `p < 0.05`, `p < 0.01`,
`p < 0.0083`, `p < 0.025`, `p < 0.10`, etc. that are pre-registered
acceptance criteria or decision rules in PRDs and experiment specs
(STATS_PLAN.md, EXPERIMENT_V2_DESIGN.md, EXPERIMENT_V3_FORMAL_SPEC.md,
SWEBENCH_EXPERIMENT_DESIGN.md, AUTORESEARCH_CONFIG.md, BORG_V3_PRD.md,
etc.). These are aspirational thresholds for experiments that have
not yet run. None of them claim a measured p-value. **No audit
needed.** See `CLAIM_INVENTORY.md` CAT_E for the full list.

---

## Files to patch

| # | File | Action |
|---|------|--------|
| 1 | `borg/STRATEGIC_SYNTHESIS.md` | Add top-of-doc CORRECTION block; +43pp lines (12, 34, 64, 104) read in context of header |
| 2 | `borg/COMPETITIVE_ANALYSIS.md` | Inline correction next to "Already proven +43pp" (line 174) |
| 3 | `borg/docs/BORG_PACK_AUTO_GENERATION_PRD.md` | Inline correction next to "(+43pp with traces) proved" (line 185) |

No other files need patching:
- `EXPERIMENT_REPORT.md`, `AUDIT_METHODOLOGY.md`, `AUDIT_ACADEMIC.md`,
  the borg-defi-agent-stack and experiment-before-architecture skills:
  the p=0.96 / p=0.86 token claims are SUPPORTED by raw data.
- `EXPERIMENT_FINAL_REPORT_V2.md`, `BORG_PRD_FINAL.md`, `DIFFICULTY_DETECTOR.md`:
  already cite +43pp with the n=7 / p=0.125 / directional qualifier.
- `BORG_E2E_PRD_20260402.md`: the "+34pp / p<0.05 / 8%→42%" fabrication
  rows were patched in audit 2 (`PLUS34PP_AUDIT.md`); verified still
  carrying [CORRECTION 20260408-1128] block.

---

## Confidence assessment — are there STILL more fabrications we missed?

**Confidence remaining undiscovered fabrications: LOW (~0.85
confidence that no more single-number fabrications exist).**

Reasoning:
1. Three sweeps (this is the third) have now combed every doc, skill,
   memory file, and obsidian vault page in the workspace for
   statistical claims. The first two found one fabrication each. The
   third found ZERO new numerical fabrications.
2. Every statistical number that maps to actual raw data on disk has
   been recomputed. All match.
3. The remaining hits are either (a) pre-registered acceptance
   criteria (CAT_E, aspirational), (b) pedagogical examples in skill
   files (CAT_E), or (c) already-corrected references in audit 1 / 2.
4. The narrative-level concern that remains is **caveat stripping**,
   not **number fabrication**. The +43pp result is a real number; the
   problem is that 5 documents drop the "p=0.125, n=7, not
   significant" qualifier when citing it.

Residual risks (~15% chance one of these turns into a real find):
- We did not deeply audit dogfood test/run scripts that compute their
  own statistics (only the .md and .json reports). A bug in a runner
  could mean the raw data itself is wrong upstream of the report.
  In particular, `dogfood/all_results.json` is consistent with itself
  but I have not validated it against per-task `tokens_used` source-
  of-truth (e.g. an actual API token meter). The sample-size and
  arithmetic checks pass, but the underlying token counts could be
  estimated rather than measured.
- DeFi-vertical claims have not been checked because there is no
  dataset to audit them against — they are entirely hypothetical
  (audit 1 already flagged this).
- The 4.5x efficiency anecdote (`BORG_PRD_FINAL.md:79`) cites
  django-13344 and tool-call counts. This is a per-task observation
  rather than a statistical claim, and I did not chase the underlying
  per-task tool-call logs. Probably honest but unverified.

**Overall:** the workspace is now in a much more honest state than at
the start of audit 1. The third sweep recommends patching the three
caveat-stripping locations and treating this audit family as
substantially complete. A fourth sweep would yield diminishing returns.
