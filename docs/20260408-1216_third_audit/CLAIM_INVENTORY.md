# Claim Inventory — Third Sweep 20260408-1216

Categorisation of all statistical-claim hits across hermes-workspace,
.hermes/skills, obsidian-vaults, memory.

Categories:
- CAT_A: References to the already-corrected p=0.031 claim (skip)
- CAT_B: References to the already-audited +34pp claim (skip)
- CAT_C: NEW statistical significance claims not yet audited
- CAT_D: Vague success claims with no number (lower priority)
- CAT_E: Forward-looking research claims (aspirational, acceptable)

---

## CAT_C — NEW claims to audit

### C1. "+43pp" SWE-bench claim (n=7 paired)

This claim was NOT covered by either prior audit (audit 1 = p=0.031, audit
2 = +34pp pilot). It is the SWE-bench n=7 success-rate delta.

| File | Line | Exact text | Has n=7 / not-sig qualifier? |
|------|------|------------|------------------------------|
| `borg/STRATEGIC_SYNTHESIS.md` | 12 | "+43pp improvement, zero negative transfer" | NO |
| `borg/STRATEGIC_SYNTHESIS.md` | 34 | "**Evidence**: +43pp on SWE-bench" | NO |
| `borg/STRATEGIC_SYNTHESIS.md` | 64 | "**Evidence**: +43pp on SWE-bench coding tasks." | NO |
| `borg/STRATEGIC_SYNTHESIS.md` | 104 | "Reasoning traces improve coding agent success by +43pp on real tasks" | NO |
| `borg/STRATEGIC_SYNTHESIS.md` | 129 | "We now have 7 data points from real SWE-bench tasks showing a +43pp improvement." | partial (n=7 cited, "proof" denied) |
| `borg/COMPETITIVE_ANALYSIS.md` | 174 | "Already proven +43pp on SWE-bench" | NO — uses "proven" |
| `borg/EXPERIMENT_FINAL_REPORT_V2.md` | 33,59,69,86,96,101 | "+43pp" / "+43 percentage points" | YES — top of file has audit pointer + n=7 throughout |
| `borg/DIFFICULTY_DETECTOR.md` | 12 | "Directional +43pp; 3/3 discordant pairs favor traces" | YES — explicit "directional", n=7, McNemar p=0.125 in same block |
| `borg/BORG_PRD_FINAL.md` | 89 | "+43pp directional success-rate improvement on SWE-bench Django tasks (3/7 → 6/7)" | YES — "directional" + 3/7→6/7 |
| `borg/docs/BORG_PACK_AUTO_GENERATION_PRD.md` | 185 | "The prior experiment (+43pp with traces) proved that investigation trails help." | NO — uses "proved" |

### C2. p=0.96 / +13.3% token claim (V2 19-pair)

| File | Line | Exact text |
|------|------|------------|
| `borg/EXPERIMENT_REPORT.md` | 14 | "Tokens (primary) 1,365 mean 1,547 mean +13.3% MORE p=0.96 NO" |
| `borg/EXPERIMENT_REPORT.md` | 79 | "E1 Token reduction significant p < 0.025 p = 0.96 FAIL" |
| `borg/AUDIT_METHODOLOGY.md` | 140 | "V2 showed that with n=19, p=0.96 for the token reduction hypothesis" |
| `borg/AUDIT_ACADEMIC.md` | 103 | "the V1/V2 report used a Wilcoxon test and reported p=0.96 (one-sided)" |
| `.hermes/skills/software-development/borg-defi-agent-stack/SKILL.md` | 66 | "V2 protocol... p=0.96, NOT significant" |
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md` | 91 | "Tokens: Treatment +13.3% MORE (p=0.96, NOT significant)" |

### C3. p=0.86 / V1 10-pair token claim

| File | Line | Exact text |
|------|------|------------|
| `.hermes/skills/software-development/experiment-before-architecture/SKILL.md` | 85 | "V1 (10 pairs, flawed protocol — control always first) Tokens: Treatment +13.4% MORE (p=0.86, NOT significant)" |

### C4. "DEBUG-002 4.5x efficiency" claim

| File | Line | Exact text |
|------|------|------------|
| `borg/BORG_PRD_FINAL.md` | 79 | "django-13344: Agent A failed after 50 tool calls. Agent B with Agent A's notes succeeded in 11 tool calls. 4.5x efficiency improvement." |

(NOTE: this is a different claim — django-13344, tool-call count, not pp delta. It comes from dogfood notes; not part of the main A/B and not yet audited.)

### C5. "+18pp" stats field in pack template

| File | Line | Exact text |
|------|------|------------|
| `borg/docs/BORG_E2E_PRD_20260402.md` | 407 | `"avg_improvement": "+18pp on hard tasks"` |

(Inside an EXAMPLE pack JSON template — appears to be illustrative, but worth flagging because it's in an "expected results" section.)

---

## CAT_E — Aspirational / forward-looking specs (NOT to audit)

The following hits are research-design specs that describe what an
experiment WILL test, not measured results. They use "p < 0.05" as a
threshold/decision rule, not as a measured value. All acceptable as
aspirational pre-registration:

- `borg/EXPERIMENT_V3_SPEC.md` (lines 91, 233) — Phase 3 spec criteria
- `borg/EXPERIMENT_V3_FORMAL_SPEC.md` (lines 119, 127, 143, 149-187) — formal Phase 3 spec
- `borg/EXPERIMENT_V2_DESIGN.md` (lines 16, 120-141, 217-224) — Phase 2 design
- `borg/SWEBENCH_EXPERIMENT_DESIGN.md` (lines 99, 129, 135, 169-182) — protocol
- `borg/BORG_V3_LEARNING_LOOP_SPEC.md` (lines 234, 241, 428) — V3 spec
- `borg/BORG_V3_PRD.md` (line 257) — V3 PRD threshold
- `borg/BORG_EXPERIMENT_SPEC.md` (lines 133, 168, 299) — protocol
- `borg/STRATEGIC_SYNTHESIS.md` (lines 85, 113) — "expand to achieve p<0.05" (forward-looking)
- `borg/FINAL_EXPERIMENT_REPORT.md` (line 114) — "next step achieve p<0.05"
- `borg/EXPERIMENT_FINAL_REPORT_V2.md` (line 71) — "expand to 15+ to achieve p<0.05"
- `borg/EXPERIMENT_V2_STATUS.md` (line 20) — GO threshold spec
- `borg/eval/e1a_django_full/E1A_DJANGO_FULL_STATS.md` (lines 44, 192) — threshold/next-steps
- `borg/dogfood/EXPERIMENT_V3_REDESIGN.md` (lines 72, 73) — "if N favor, p=0.011" hypothetical
- `borg/docs/E2E_LEARNING_LOOP_PRD.md` (line 133) — acceptance criterion
- `borg/docs/PRD_BORG_PACK_AUTO_GENERATION.md` (lines 269, 279, 280, 813) — decision rule
- `borg/docs/PRD_BORG_VALIDATION.md` (line 135) — acceptance criterion
- `borg/docs/BORG_PACK_AUTO_GENERATION_PRD.md` (lines 124, 302, 309, 310, 470, 508, 563) — decision rules
- `borg/docs/20260408-1003_scope3_experiment/STATS_PLAN.md` (lines 199, 348-419, 632) — scope 3 stats plan (pre-registered)
- `borg/docs/20260408-1003_scope3_experiment/RED_TEAM_METHODOLOGY_REVIEW.md` (line 240) — red-team review
- `borg/docs/20260408-1118_borg_roadmap/BORG_TESTING_ROADMAP_20260408.md` (lines 133, 163) — roadmap thresholds
- `borg/AUDIT_METHODOLOGY.md` (line 224) — repeats V2 target
- `borg/autoresearch/AUTORESEARCH_CONFIG.md` (lines 74, 367, 368, 393, 448, 494, 497) — autoresearch decision rules
- `borg/DEFI_EXPERIMENT_DESIGN.md` (lines 66, 96, 143) — DeFi experiment design
- `.hermes/skills/research/rigorous-agent-experiment-design/SKILL.md` (multiple) — pedagogical
- `.hermes/skills/research/swebench-ab-experiment/SKILL.md` (line 69) — pedagogical
- `.hermes/skills/research/swebench-borg-ab-experiment/SKILL.md` (line 83) — pedagogical
- `.hermes/skills/research/swebench-agent-experiment/SKILL.md` (line 12) — pedagogical
- `.hermes/skills/research/knowledge-system-evaluation/SKILL.md` (lines 90, 91) — example/pedagogical
- `.hermes/skills/software-development/agent-ab-experiment-repos/SKILL.md` (line 90) — generic protocol
- `obsidian-vaults/borg/experiments/Evaluation Protocol V3.md` (line 29) — protocol
- `obsidian-vaults/borg/experiments/Adversarial Review Findings.md` (line 10) — methodology comment
- `borg/docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md` (line 157) — gate condition

---

## CAT_A — already-handled p=0.031 references

All occurrences of `p=0.031`, `40%→90%`, `+50pp`, `n=10` already covered
by `FABRICATION_SWEEP_20260408.md`. Skipping.

## CAT_B — already-handled +34pp pilot references

All occurrences of `+34pp` with the pilot context (n=3 hard, 33%→67%)
already covered by `PLUS34PP_AUDIT.md`. Skipping.
