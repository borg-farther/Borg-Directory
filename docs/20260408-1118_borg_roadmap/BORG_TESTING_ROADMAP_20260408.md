# Borg Testing Roadmap — 20260408-1118
## Priority-Ranked Spec for Measuring, Validating, and Shipping Honest Borg Claims

**Author:** Hermes Agent on behalf of AB
**Status:** Proposed for approval
**Quality bar:** Google staff-level / PhD committee / HN front-page defensible
**TL;DR:** Five priority tiers, ten numbered initiatives, explicit money gates, measurable exit criteria on every step, honesty invariants that cannot be bypassed, and a pre-committed decision tree for what happens based on each experiment's outcome.

---

## 0. METADATA

| Field | Value |
|---|---|
| Date | 20260408-1118 |
| Owner | Hermes Agent |
| Status | Proposed for approval |
| Quality bar | Google staff-level / PhD committee / HN front-page defensible |
| Supersedes | /root/hermes-workspace/borg/docs/20260408-0623_classifier_prd/SYNTHESIS_AND_ACTION_PLAN.md (classifier-internal, Phase 0 complete) |
| Total budget ceiling | USD 300 in real LLM spend, distributed across tiers |
| Total time ceiling | 3 weeks wall clock |
| Critical dependency | Honest agent-level measurement of Borg — has never been done |

---

## 1. EXECUTIVE SUMMARY

In a 20-hour burst on 20260408 we shipped agent-borg v3.2.2 and v3.2.3 to PyPI, dropping the classifier's false-confident rate from 53.8% to 0.58% on a 173-row multi-language error corpus. Then a forensic audit proved that the previously-shipped "proven result p=0.031, A=40%→B=90%" was fabricated 95 minutes after an honest intermediate report saying p=0.125. A sweep corrected 20 files across 3 repositories. A preflight round built a bulletproof SWE-bench experiment runner with an honesty invariant that cannot be bypassed, and discovered that the original Scope 3 plan was 50x underpowered — a pooled GLMM with N=60 is required to have any statistical power at all.

This roadmap spans what comes next in priority order, with money gates, exit criteria, and honest decision rules. **The single highest-leverage action remaining is Priority 1.1: run a minimum-viable honest agent-level measurement. Everything downstream depends on its result.** Priorities 2-5 are conditional on 1.1's outcome.

---

## 2. CURRENT STATE (HONEST)

### 2.1 What we have measured
- **Classifier internal:** FCR 53.8% → 0.58%, precision 13.1% → 93.8%, recall unchanged on 10 Python regression fixtures, 1705 unit tests passing.
- **PyPI adoption:** 1545/month downloads (86.58% null/CI, 10.6% real Python runs ≈ 82 human installs in March).
- **173-row multi-language corpus:** committed, reproducible, benchmark baseline is locked.

### 2.2 What we have NOT measured
- **Agent-level effect of Borg on any task.** Zero clean experiments.
- **Cross-model generalization.** Unknown.
- **Cross-framework (Hermes vs OpenClaw).** Unknown — and OpenClaw is currently broken on this VPS (bundled JS ReferenceError).
- **Collective intelligence / knowledge transfer between agents.** Unknown — Phase C never run.
- **Cost-effectiveness (tokens per success).** Unknown.

### 2.3 What we thought we had measured but didn't
- **The fabricated p=0.031 result.** FABRICATED. Real result is n=7, p=0.125, directional only. Corrected across 20 files.
- **The related "+34pp on hard tasks" claim** (V2 reasoning traces, n=3). NOT YET AUDITED. Suspected also unsupported.

### 2.4 Infrastructure state
- **VPS:** 8-core EPYC, 31GB RAM, 283GB free, load avg 0.05 — 99.4% idle.
- **Docker:** 20+ Django Verified images cached from 21h ago, SWE-bench conda env available inside containers.
- **Runner:** 470-LOC bulletproof `run_single_task.py` built, honesty invariant live-verified.
- **Stats plan:** Corrected pooled-GLMM design, Monte Carlo power analysis complete, decision rules in JSON.
- **API keys:** Anthropic OAuth (shared with Claude Code, 429s under load), Gemini free-tier (throttled), GPT-4o-mini (quota dead), MiniMax-Text-01 (stable paid, measured $0.0011/iter).
- **Feedback channel:** GitHub Discussion #1 live, structured issue template committed, cron aggregating at 20260410-0700.

### 2.5 Honesty invariants now enforced in code
- Runner raises `AssertionError` if treatment-condition run has `borg_searches == 0`
- Runner refuses to mark a task successful without pytest exit code 0 verification
- Runner streams JSONL with fsync per row, crash-recoverable
- Pack classifier v3.2.3 returns structured UnknownMatch when language detected ≠ Python

---

## 3. GOALS / NON-GOALS

### 3.1 Goals (testable, measurable)

| ID | Goal | Exit measurement |
|---|---|---|
| G1 | Eliminate all downstream citations of the fabricated p=0.031 claim | `rg 'p.*0\.031' /root/hermes-workspace/ /root/.hermes/skills/ /root/obsidian-vaults/` returns zero hits outside audit/correction docs |
| G2 | Produce the first honest agent-level Borg measurement (any model) | One JSONL file with N≥30 paired runs, borg_searches >0 in all treatment rows, pooled GLMM fitted, effect size with 95% CI |
| G3 | Audit the related "+34pp on hard tasks" claim against actual data | Second forensic audit doc, SUPPORTED or UNSUPPORTED verdict, files patched if needed |
| G4 | If G2 shows positive effect: replicate on at least 2 independent models | Two JSONL files, two GLMMs, meta-analytic combined estimate |
| G5 | Ship a publication-ready report to GitHub Discussion #1 | Markdown doc with pre-registered H0/H1, decision rules, forest plot, raw data link, signed commit SHA |
| G6 | Commit to a borg product strategy based on the measured result, not the vibe | Single-page memo "Given G2 result, we will..." written within 48h of G2 completion |
| G7 | Establish continuous honesty monitoring so fabrications cannot re-enter the codebase | CI check that blocks commits adding "proven result" claims without a cited data file; nightly cron that greps for unsupported statistics |
| G8 | Pay down technical debt from the 20h v3.2.x burst | Commit cleanup (uniform `Hermes Agent` authorship if desired), branch consolidation (master → main on remote), obsolete file removal |

### 3.2 Non-goals (explicit — will NOT do in this roadmap)

1. **Fix OpenClaw.** The bundled JS is broken. Making it comparable to tool-calling loops is >1 day of harness work. Deferred until borg has a positive result on 3 other frameworks.
2. **Phase C cross-agent transfer experiment.** The original plan at N=10 was catastrophically underpowered (MDE OR > 50). Skipping until we can scale to N ≥ 40 task-pairs, which requires either a successful Path 1 result or a larger budget.
3. **Build new classifier packs for Rust/Go/JS/TS/Docker/K8s.** Deferred per the Skeptic gate in the classifier PRD. Still waiting on feedback from Discussion #1.
4. **GEPA integration or hermes-agent-self-evolution fork.** Deferred per the 20260408 spike result. Revisit only if someone else publishes a result with that stack.
5. **H4D / cosmology work.** Out of scope for this roadmap. This is borg-only per AB's 20260408-1000 directive.
6. **New Borg CLI features.** Only bugfixes and the measurement infrastructure. Feature freeze until the "does it work" question is answered.
7. **Marketing pushes** (HN posts, Twitter threads). Deferred until the measured result is in. No posts before Priority 1.1 completes.
8. **Scope 3 as originally specified.** The power analysis showed the per-framework McNemar design was impossible. The re-scoped Scope 2 with pooled GLMM is what replaces it.
9. **i18n, fine-tuning, LLM-as-hot-path, PII redaction, multi-error correlation.** Same non-goals as the classifier PRD carry forward.
10. **Dogfood DM outreach.** The GitHub Discussion already serves as the structured channel. Only the 60-second URL share remains as a human action.

---

## 4. PRIORITY-RANKED ROADMAP

The roadmap is organized in 5 tiers. Each tier has a money gate. Every item has scope, effort, dependencies, exit criteria, rollback plan, and owner. Tiers 1-2 run sequentially; tiers 3-5 are conditional on tier 1's outcome.

### **Priority 1 — HONESTY FLOOR** (this week, USD 0-5)

#### Priority 1.0 — "+34pp on hard tasks" audit (EXTENDS PATH 3)

| Field | Value |
|---|---|
| Goal | Determine if the "+34pp on hard tasks" claim in BORG_E2E_PRD_20260402.md + 2 skill descriptions is supported by actual data, or is a second fabrication |
| Effort | ~30 min, 1 subagent |
| Dependencies | Path 3 fabrication sweep (complete), forensic audit style (from 1003 audit) |
| Scope | (a) Grep workspace for every occurrence of "+34pp", "34 percentage", "HARD-004", "HARD-015", "reasoning trace". (b) Trace provenance through file mtimes. (c) Compute statistics from raw data files. (d) Produce verdict doc. (e) Patch files if unsupported. |
| Exit criteria | Single audit doc at docs/20260408-1118_borg_roadmap/PLUS34PP_AUDIT.md with SUPPORTED/PARTIAL/UNSUPPORTED/FABRICATED verdict. If unsupported, files patched and committed. |
| Rollback plan | Audit docs are additive — no rollback needed. |
| Risk | LOW. Pure forensics on local data. |
| Money | USD 0 |
| Owner | Single subagent |

#### Priority 1.1 — MiniMax Path 1 experiment (PROOF-OF-PIPELINE)

| Field | Value |
|---|---|
| Goal | Produce the first honest agent-level Borg measurement on any real model, proving the pipeline end-to-end before investing in larger experiments |
| Effort | ~2h wall clock, 1 long-running subagent |
| Dependencies | Preflight B (complete), Preflight C stats plan (complete), MiniMax API quota (confirmed stable), cached Django Verified Docker images (20+ available) |
| Scope | Run the 470-LOC `run_single_task.py` on 15 Django Verified tasks × 3 conditions (C0, C1, C2) × 1 run = 45 runs. Model: minimax-text-01. Seed fixed per (task, condition). Streaming JSONL output. Mid-run cost monitor with hard abort at USD 4. |
| Exit criteria | (a) ≥40 of 45 runs complete without infra crash; (b) borg_searches ≥1 in all 30 treatment runs (otherwise experiment is invalidated by the honesty invariant); (c) JSONL file with all metrics; (d) Pooled GLMM fitted; (e) Effect size with 95% CI reported; (f) Report written to docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md |
| Rollback plan | None needed — data is additive. |
| Risk | MEDIUM. MiniMax may refuse long tool-calling loops. If <30 runs complete, we report infrastructure failure, not a null result. |
| Money | USD 3-5 based on preflight per-iter cost ($0.0011 × ~20 iter/run × 45 runs = ~$1, with 5x safety margin = $5) |
| Owner | Single long-running subagent with strict budget cap |

**Decision gate A (after P1.1):**
- IF ≥30 runs complete AND pooled GLMM p < 0.05 with OR > 1.5 → proceed to Priority 2 (scale to Sonnet)
- IF ≥30 runs complete AND pooled GLMM p ≥ 0.05 → proceed to Priority 2 with caveat "Scale up to test if effect exists at larger N"
- IF <30 runs complete → proceed to infrastructure debugging, halt experiment track until resolved
- IF any treatment run has borg_searches == 0 → experiment INVALIDATED per honesty invariant, stop and diagnose

### **Priority 2 — HONEST CROSS-MODEL** (next 3 days, USD 30-80)

Requires human decision point: fresh Anthropic `sk-ant-api03-*` key provisioned OR explicit decision to use shared OAuth with sequential pacing.

#### Priority 2.1 — Sonnet Path 1 replication

| Field | Value |
|---|---|
| Goal | Replicate the P1.1 experiment on Claude Sonnet 4.5, the model most readers will care about |
| Effort | ~4h wall clock with fresh API key, ~8h with shared OAuth + pacing |
| Dependencies | P1.1 complete, either fresh `sk-ant-api03-*` key OR user approval for pacing |
| Scope | Same 15 tasks × 3 conditions × 1 run = 45 runs. Model: claude-sonnet-4-5-20250929 (exact ID locked). Same JSONL schema as P1.1 so results are directly comparable. |
| Exit criteria | Same as P1.1 + specific: effect size comparable in direction (even if different magnitude) to MiniMax result for the experiment to be considered replication |
| Rollback plan | None |
| Risk | HIGH if shared OAuth. MEDIUM if fresh key. |
| Money | USD 20-30 based on Sonnet pricing (~$0.50/run × 45 runs) |
| Owner | Single long-running subagent |

#### Priority 2.2 — Cross-model meta-analysis

| Field | Value |
|---|---|
| Goal | Combine P1.1 (MiniMax) and P2.1 (Sonnet) results into a single defensible claim |
| Effort | ~1h, subagent |
| Dependencies | P1.1 + P2.1 complete |
| Scope | Fit combined GLMM: `success ~ condition + model + condition:model + (1\|task)`. Report interaction p. If interaction p > 0.05, report combined fixed effect. If p < 0.05, report per-model effects separately. Produce forest plot. |
| Exit criteria | Single markdown report with combined analysis, forest plot (SVG), honest interpretation. Committed + pushed. |
| Rollback plan | None |
| Risk | LOW |
| Money | USD 0 (pure analysis) |
| Owner | Stats subagent |

**Decision gate B (after P2.2):**
- IF both models show positive effect AND interaction p > 0.05 → "borg generalizes across models" story. Proceed to Priority 3 (scale + publication).
- IF one model positive, one null → "borg is model-specific" story. Proceed to Priority 3 but revise marketing.
- IF both null → "current borg architecture does not add measurable agent value." Proceed to Priority 4 (honest pivot). This is the honest-null-result outcome the Skeptic flagged.
- IF results are ambiguous (N too small, high variance) → proceed to Priority 3.1 (add a third model to gain power).

### **Priority 3 — PUBLICATION + SCALE** (week 2, USD 0-80 depending on P2 outcome)

This tier only executes if P2.2 produces a defensible result (positive or null).

#### Priority 3.1 — Gemini or third-model replication (conditional)

| Field | Value |
|---|---|
| Goal | Add a third independent model if P2.2 was ambiguous OR if we want stronger cross-model evidence |
| Effort | ~4h |
| Dependencies | P2.2 complete, Gemini paid API access OR another provider |
| Scope | Same 45-run design on Gemini 2.0 Flash (paid tier) or another independent model. Combined 3-model GLMM. |
| Exit criteria | 3-model forest plot, interaction test with N=90 paired runs, pre-registered decision rule evaluated |
| Money | USD 10-20 (Gemini is cheap) |
| Owner | Single subagent |

#### Priority 3.2 — Publication-ready report

| Field | Value |
|---|---|
| Goal | Write the canonical Borg experimental result in a form that would survive HN front page + a PhD committee |
| Effort | ~3h, 1 writing subagent + 1 red-team subagent |
| Dependencies | P2.2 or P3.1 complete |
| Scope | Full report with sections: abstract, motivation, method, results, threats to validity, pre-registered decision rules evaluated, raw data links, reproducibility command, acknowledgments. Red-team reviews before publication. |
| Exit criteria | Markdown + PDF committed to borg repo, published as GitHub Discussion #1 reply, PyPI page updated with link, voice note drafted for AB |
| Risk | HIGH reputational — this is the canonical story. No shortcuts. |
| Money | USD 0 |
| Owner | Writing subagent + red-team subagent in sequence |

#### Priority 3.3 — Honest HN + Twitter post

| Field | Value |
|---|---|
| Goal | Publicize the honest result through AB's usual channels |
| Effort | ~30 min |
| Dependencies | P3.2 complete AND AB has read it AND AB approves |
| Scope | Post the prepared HN draft and tweet draft (updated with real numbers). AB posts from his account; Hermes does not post publicly without AB approval per session rule. |
| Exit criteria | HN post URL + tweet URL captured in docs/20260408-1118_borg_roadmap/publication_urls.txt |
| Risk | MEDIUM — one-way action |
| Money | USD 0 |
| Owner | AB |

**Decision gate C (after P3.3):**
- IF positive result + public launch → proceed to Priority 4 (follow-through: respond to feedback, iterate)
- IF null result + honest public launch → proceed to Priority 5 (pivot: what else does borg do that we could measure)

### **Priority 4 — FOLLOW-THROUGH + ADOPTION** (week 3, USD 10-50)

#### Priority 4.1 — Feedback aggregation

- Triage every response in GitHub Discussion #1 + classifier-feedback issues
- Update dogfood_responses.md
- Re-evaluate the 5 flip conditions for classifier Phase 1-4 restart
- Owner: single subagent, ~1h, USD 0

#### Priority 4.2 — Continuous monitoring infrastructure

- Nightly cron that reruns the 45-run experiment on 1 model as a smoke test
- Alerts AB if effect size drifts by >20%
- Stores time-series results
- Owner: single subagent, ~2h, USD 5-15/month in perpetual runtime
- This is what "continuous measurement" means — we never ship without proof again

#### Priority 4.3 — Scale to 50+ SWE-bench tasks (if P2 was positive)

- Expand from 15 to 50 Django Verified tasks
- Adds power, reduces task-selection bias
- 1 model (Sonnet), 2 conditions (C0 vs C2), N=100 paired
- Owner: single subagent, ~6h, USD 30-50

### **Priority 5 — PIVOT CANDIDATES** (IF P2 was null, USD 0-100)

If P2 shows borg doesn't help agents, these are the honest-pivot options, ranked by expected ROI:

1. **Pack adoption cron** — measure whether automated pack generation from session history produces packs that humans accept. This answers "is the authoring flywheel real?" (~$10, 1 week)
2. **MCP-in-Claude-Code integration** — wire `borg debug` as an MCP tool inside Claude Code and measure whether agents call it, and if calling it improves their outcomes. This tests the agent-tool niche directly. (~$30, 1 week)
3. **Knowledge-wiki-compounding dogfood at scale** — run the salvaged llm-wiki skill across all 3 obsidian vaults for 2 weeks and measure whether it produces insights humans would not have found. (~$0, 2 weeks)
4. **Cross-model classifier benchmark** — run the existing 173-row corpus classifier through N models and show per-model false-confident rates. Narrow but real. (~$10, 1 day)

Priority 5 is itself a priority-ranked sub-roadmap. It only matters if the main experiment fails.

---

## 5. CROSS-CUTTING WORK STREAMS

These run in parallel with tiers 1-5 throughout the roadmap:

### 5.1 Honesty rails

- **CI honesty check.** Add a GitHub Action that blocks PRs introducing "proven result" claims without a cited data file. ~2h, USD 0. Priority 2 slot.
- **Nightly fabrication scan.** Cron that greps the workspace for suspicious statistical claims and alerts on new ones. ~1h, USD 0. Priority 2 slot.
- **Pre-commit hook for skills.** Any skill edit that adds a number must cite its source. ~30 min, USD 0. Priority 2 slot.

### 5.2 Documentation hygiene

- **BORG_PRD_FINAL.md honest rewrite.** The current document is corrupted by fabricated citations. Needs full rewrite with the measured result from G2. ~2h, USD 0. Priority 3 slot.
- **README.md update after P2.** Reflect measured agent-level result or honest "still unmeasured" statement. ~30 min, USD 0. Priority 3 slot.
- **Skill authorship standardization.** Pick one author identity (`Hermes Agent` or `Claude Code`) and use consistently. ~30 min, USD 0. Priority 4 slot.

### 5.3 Infrastructure hardening

- **Branch consolidation.** Remote default is `main`, we ship from `master`. Pick one. ~30 min, USD 0. Priority 4 slot.
- **Docker image cleanup.** 20+ stopped containers from 21h ago. `docker container prune` + selective image retention. ~15 min, USD 0. Priority 4 slot.
- **Secrets rotation.** The OpenAI key is dead — rotate or remove to prevent future agent confusion. ~15 min, USD 0. Priority 4 slot.

### 5.4 Feedback channel maintenance

- **20260410-0700 cron firing.** Already scheduled, no action needed. Reports on Discussion #1 + issues + manual log.
- **Weekly cron for adoption monitoring.** Already running (Borg Adoption Monitor). Update its prompt post-P2 with new numbers.
- **Monthly audit.** Cron that re-runs the fabrication sweep grep and reports any new hits.

---

## 6. HONESTY INVARIANTS (cannot be bypassed)

These apply to every experiment and every ship going forward. They are pre-committed rules, not guidelines.

| # | Invariant | Enforcement |
|---|---|---|
| H1 | No result is "proven" without a committed raw data file, a reproducer script, and a git SHA | CI check + nightly cron + manual audit quarterly |
| H2 | No treatment-condition run counts if `borg_searches == 0` | Runner raises `AssertionError`; already live in run_single_task.py |
| H3 | No claim of statistical significance without pre-registered alpha, pre-committed sample size, and Holm-corrected p-values | Stats plan template mandatory for every experiment |
| H4 | No "we found that X" in a marketing doc without a link to the corresponding experiment log | Pre-commit hook blocks it |
| H5 | If a result contradicts an earlier claim, the earlier claim gets a CORRECTION block — it is never silently deleted | Git history preservation |
| H6 | No LLM on the agent's hot path for core Borg operations without an explicit offline fallback | Runner enforces |
| H7 | No experiment starts before the honesty preflight checklist is signed off | Preflight doc required |

---

## 7. DECISION TREE

```
START (20260408-1118)
│
├── Priority 1.0: +34pp audit ─────────┐
│                                       │
├── Priority 1.1: MiniMax Path 1 ──┐    │
│                                   │    │
▼                                   │    │
Decision gate A                     │    │
│                                   │    │
├── ≥30 runs, positive ───► Priority 2  │
├── ≥30 runs, null ─────► Priority 2 with caveat
├── <30 runs ──────────► debug infra, halt experiment track
└── borg_searches==0 ──► HALT, diagnose honesty invariant
                                    │    │
                                    ▼    │
                        Priority 2.1 Sonnet (needs key decision)
                        Priority 2.2 Cross-model analysis
                                    │    │
                                    ▼    │
Decision gate B                     │    │
│                                   │    │
├── Both positive ──────► Priority 3    │
├── Mixed ─────────────► Priority 3 with revised story
├── Both null ─────────► Priority 5 (pivot)
└── Ambiguous ────────► Priority 3.1 (3rd model)
                                    │    │
                                    ▼    │
                        Priority 3 Publication
                                    │    │
                                    ▼    │
Decision gate C                     │    │
│                                   │    │
├── Published positive ────► Priority 4 follow-through
└── Published null ────────► Priority 5 pivot
```

---

## 8. COST MODEL

| Priority | Best case | Expected | Worst case | Notes |
|---|---|---|---|---|
| 1.0 +34pp audit | USD 0 | USD 0 | USD 0 | Pure forensics |
| 1.1 MiniMax Path 1 | USD 2 | USD 5 | USD 10 | Hard cap at $4 per preflight |
| 2.1 Sonnet Path 1 | USD 15 | USD 30 | USD 50 | Depends on Sonnet pricing + run length |
| 2.2 Meta-analysis | USD 0 | USD 0 | USD 0 | Pure analysis |
| 3.1 Gemini third model | USD 5 | USD 15 | USD 25 | Only if P2 ambiguous |
| 3.2 Publication | USD 0 | USD 0 | USD 0 | Subagent writing |
| 3.3 Public posts | USD 0 | USD 0 | USD 0 | Human action |
| 4.1 Feedback triage | USD 0 | USD 0 | USD 0 | Subagent |
| 4.2 Continuous cron | USD 5 | USD 15 | USD 30/month | Perpetual |
| 4.3 Scale to 50 tasks | USD 15 | USD 30 | USD 60 | Only if P2 positive |
| 5.x Pivot experiments | USD 0 | USD 50 | USD 100 | Only if P2 null |
| **Total (P2 positive path)** | **USD 42** | **USD 95** | **USD 175** | |
| **Total (P2 null path)** | **USD 22** | **USD 95** | **USD 185** | Different mix |

Budget ceiling: USD 300. Any single initiative exceeding its worst-case triggers halt-and-reassess.

---

## 9. RISKS AND MITIGATIONS

| # | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| R1 | MiniMax refuses 20-iter tool-calling loops → P1.1 can't produce data | Medium | High | Runner detects malformed tool-calls, degrades to single-turn patch prompt as fallback; reports both results |
| R2 | Sonnet shared OAuth rate-limits sink P2.1 | High | Medium | Already planned: either fresh `sk-ant-api03-*` key (waits on AB) OR sequential pacing with 30s delays (8h run instead of 4h) |
| R3 | A second fabrication is discovered in Priority 1.0 | Low | High | Same patch-in-place workflow that worked for the p=0.031 sweep |
| R4 | Null result in P2.2 → public narrative collapse | Medium | High | Pre-committed "honest null is a feature, not a bug" messaging. The Skeptic gate already anticipated this. |
| R5 | Runner has a subtle bug that silently invalidates the honesty invariant | Low | CRITICAL | Adversarial red-team pass on the runner before P2 starts. Test case: injected `borg_searches=0` row should trigger AssertionError. Unit test mandatory. |
| R6 | Docker cache eviction between P1.1 and P2.1 adds 30min rebuild per task | Medium | Low | Build all images upfront in Priority 1.1 prep phase |
| R7 | SWE-bench task set is gamed because packs are co-located with Django files | High | Medium | Pre-register task list BEFORE looking at pack contents; add non-Django repos (sklearn, sympy) if time permits |
| R8 | Cost overrun due to miscounted tokens | Medium | Low | Per-run cost monitor with hard abort at USD X of remaining budget |
| R9 | Subagent fabricates a number in the report to make the experiment look good | Low | CRITICAL | Red-team subagent reviews the report against raw data BEFORE commit. Same invariant H1. |
| R10 | AB loses trust in the agent because of the 20-hour blitz pace | Low | HIGH | This roadmap IS the response. Slowing to measured, honest tiers. |

---

## 10. EXPLICIT TIMELINE

**Week 1 (20260408 → 20260415):**
- Day 1 (20260408 eve): Priority 1.0 (+34pp audit). Priority 1.1 (MiniMax Path 1) prep.
- Day 2 (20260409): Priority 1.1 execution. Decision gate A.
- Day 3 (20260410): Depending on A: Priority 2.1 prep OR infrastructure debug. 20260410-0700 cron fires with classifier feedback aggregation.
- Day 4-5 (20260411-12): Priority 2.1 execution (Sonnet). Priority 2.2 analysis.
- Day 6-7 (20260413-14): Decision gate B. Priority 3 or Priority 5 path starts.

**Week 2 (20260415 → 20260422):**
- Priority 3 execution if positive path. Publication report. Red-team review.
- Priority 5 pivot experiments if null path.

**Week 3 (20260422 → 20260429):**
- Priority 3.3 public posts (if positive) or Priority 5 pivot results.
- Priority 4 follow-through and continuous monitoring.

**Total: 3 weeks from roadmap approval to either (a) honest positive published + monitoring, or (b) honest null published + pivot roadmap.**

---

## 11. OPEN QUESTIONS FOR AB (max 4)

1. **Priority 1.1 approval**: do I run MiniMax Path 1 now with ~$5 budget, or wait for a fresh Anthropic key to run both P1.1 (MiniMax) and P2.1 (Sonnet) back-to-back? Recommend: run P1.1 tonight regardless — MiniMax data is additive, not substitutive.

2. **Fresh Anthropic key**: will you provision `sk-ant-api03-*` for P2.1, or do you want me to attempt P2.1 on the shared OAuth with sequential pacing? Recommend: fresh key. OAuth 429s will corrupt the measurement and you're the only one who can provision.

3. **Publication gate**: does any public post (HN, Twitter) require explicit AB approval on the EXACT text, or do you pre-approve "Hermes posts after P3.2 red-team review passes"? Recommend: explicit AB approval on exact text for the canonical publication. One-way actions get human sign-off.

4. **Pivot threshold**: if P2.2 shows borg has zero measurable effect (p > 0.2 in both models), do you want to ship the honest null AS the story, or do you want to try Priority 3.1 (third model) before going public? Recommend: ship the honest null. It's a better story than chasing a weakening effect. The Skeptic gate already anticipated this.

---

## 12. WHAT I NEED FROM YOU

Minimum: **approve Priority 1.1** (MiniMax Path 1 tonight, ~$5). Everything else can wait for the result.

Maximum: approve the whole roadmap AND provision the Anthropic key. I run all 3 weeks autonomously with checkpoint reports, you get a final publication-ready report at the end.

In between: pick a tier. "Approve through Priority 2" means I run P1.0, P1.1, P2.1, P2.2 and then stop for your review. "Approve through Priority 3" means I run everything up to publication draft and stop before public post.

Default if you say nothing: I run Priority 1.0 and 1.1 tonight autonomously (no new money needed beyond $5 budget I'm self-capping), produce the result, and stop. Next action waits on your input.

---

## APPENDIX A — Pre-registered sample of 15 Django Verified tasks

To prevent task-selection bias, the 15 tasks for P1.1 and P2.1 are committed NOW, before running:

```
django__django-10554
django__django-11138
django__django-11400
django__django-12708
django__django-12754  [corrected from fabricated record]
django__django-13212
django__django-13344
django__django-14631
django__django-15128
django__django-15252
django__django-15503  [corrected from fabricated record]
django__django-15957
django__django-16263
django__django-16560
django__django-16631
```

These are all tasks with Docker images cached on the VPS. Pre-committed via commit SHA of this document.

---

## APPENDIX B — Artifacts index

All paths from the 20260408 session:

**Classifier PRD bundle** (`docs/20260408-0623_classifier_prd/`):
- CONTEXT_DOSSIER.md
- RED_TEAM_REVIEW.md
- ARCHITECTURE_SPEC.md (Blue Team)
- DATA_ANALYSIS.md (Green Team)
- SYNTHESIS_AND_ACTION_PLAN.md (Chief Architect)
- SKEPTIC_REVIEW.md
- error_corpus.jsonl (173 rows)
- baseline_results.csv
- run_baseline.py
- build_corpus.py
- gepa_spike/SPIKE_REPORT.md + borg_gepa_evolve.py + results.json
- HERMES_FORGE_INTEGRATION_PLAN.md
- PHASE0_SHIP_REPORT.md
- DOGFOOD_TEAM_DM_DRAFT.md
- dogfood_responses.md
- v323_fc_analysis.md
- v323_measured_impact.md
- housekeeping_20260408_0832.md
- wiki_ingest_report.md
- github_discussion_url.txt

**Scope 3 experiment bundle** (`docs/20260408-1003_scope3_experiment/`):
- PRIOR_CLAIMS_AUDIT.md (forensic fabrication audit)
- FABRICATION_SWEEP_20260408.md (20-file correction log)
- run_single_task.py (470-LOC bulletproof runner)
- dry_run.py
- dry_runs.jsonl
- PREFLIGHT_REPORT.md
- STATS_PLAN.md (664 lines)
- RED_TEAM_METHODOLOGY_REVIEW.md (17 findings)
- decision_rules.json (18 pre-registered rules)
- power_simulation.py + power_results.txt

**This roadmap** (`docs/20260408-1118_borg_roadmap/`):
- BORG_TESTING_ROADMAP_20260408.md (this document)

**External artifacts:**
- GitHub Discussion #1: https://github.com/bensargotest-sys/guild-tools/discussions/1
- PyPI: https://pypi.org/project/agent-borg/3.2.3/
- Git tags: v3.2.2, v3.2.3
- Cron: borg-v323-dogfood-followup (fires 20260410-0700)
- Obsidian wiki: /root/obsidian-vaults/borg (58 nodes, 134 wikilinks, committed)
- Knowledge-wiki skill: /root/.hermes/skills/research/knowledge-wiki-compounding (backed up to obsidian-hermes)
- Lessons skill: /root/.hermes/skills/mlops/gepa-on-structured-artifacts-lessons

---

**END OF ROADMAP**

This document is the canonical priority-ranked spec for borg testing work from 20260408 forward. All downstream subagent tasks reference this document. Any deviation from this roadmap requires a written amendment in the same directory with a dated filename.
