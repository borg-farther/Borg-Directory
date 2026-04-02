# PEER REVIEW: BORG V3 EXPERIMENT SPEC
## Academic Evaluation for Top-Tier Venue Submissions (ICSE / NeurIPS / ICML / CHI)
**Reviewer:** Academic Subagent | **Date:** 2026-03-31
**Document reviewed:** EXPERIMENT_V3_SPEC.md (V3, 404 lines) + EXPERIMENT_REPORT.md (V1/V2, 123 lines)

---

## OVERALL RATING: **BORDERLINE**

This experiment program asks an interesting question with genuine practical stakes, but has critical methodological weaknesses that would likely result in rejection at top-tier venues. The V1/V2 report demonstrates honest reporting—which is commendable—but the design choices exposed in V3 raise concerns that are not fully addressed by the proposed 420-run program.

---

## 1. NOVELTY

### 1.1 Is the Research Question Interesting?
**Yes, conditionally.** The question—"Can agents benefit from collective intelligence via shared caches?"—is practically motivated and worth studying. The V1/V2 finding that structured workflow phases add overhead but targeted hints help on hard tasks is a genuine and non-obvious insight.

### 1.2 Has Collective Intelligence for AI Agents Been Studied Before?
**Partially.** This is not a novel research area, but the specific instantiation is underexplored.

**Related work the authors should engage with:**

- **SWE-bench** (Zheng et al., 2023): Real-world software engineering task benchmark. The cache-hit concept maps to this space but is not evaluated on SWE-bench tasks.
- **ToolBench** (Qin et al., 2024): API-augmented LLM evaluation. Similar caching ideas but no collective intelligence framing.
- **CodeAgent** / **AgentBoard** (Microsoft / multiple groups, 2024): Multi-agent code generation evaluation. Collective intelligence not a primary focus.
- **Retrieval-Augmented Generation (RAG)** — Lewis et al. (2020): The cache-hit model is adjacent to RAG but different: it's not retrieving documents but cached *reasoning traces* (root cause, fix approach, time savings). This is an important distinction the spec does not make explicit.
- **Agent memory systems** — MemGPT, etc. No strong connection.
- **Collective intelligence in human teams** — Well-studied but not applicable here.

**The specific claims that need differentiation:**
- The spec does not cite RAG or distinguish the cache from standard retrieval. This is a weakness: reviewers will ask "why is this not just RAG?"
- The "failure memory" and "anti-pattern injection" concepts are more novel. Warning agents away from failed approaches is closer to defensive reasoning but has no strong prior art in this form.

### 1.3 Is the Cache-Hit Model Novel?
**Marginal novelty.** The authors correctly note the cache provides *reasoning traces* (root cause + fix + meta-info), not just documents. However:
- The mechanism is essentially retrieval of past solutions—comparable to **example-based learning** or **case-based reasoning** (Kolodner, 1993) in a new domain.
- The "TIME SAVED" meta-field is a genuinely novel twist that distinguishes it from standard RAG.
- The claim of novelty is defensible but will require strong framing in the paper.

**Novelty verdict:** The *instantiation* is novel enough for a good workshop or mid-tier venue. For top-tier (ICSE/NeurIPS/ICML), the framing and related work section will need substantial work.

---

## 2. RIGOR

### 2.1 Sample Size Adequacy (Power Analysis)

**Power analysis is present but flawed.**

The stated detectable effect sizes (d=0.58 for Experiments 1-4, d=0.40 for Experiment 5) are computed internally but the assumptions are not externalized. Problems:

1. **The power analysis assumes paired, not independent, samples.** This is correct for within-subject designs, but the spec does not justify *why* within-subject is appropriate for these AI agent experiments. Agents solving the same task twice could exhibit carry-over learning effects even with fresh workspaces. The V1/V2 report explicitly flagged "familiarity with task structure" effects (Section 4, Finding 4). This is a serious threat.

2. **Effect size assumptions are optimistic.** d=0.58 is a medium-large effect. For token reduction in production AI systems, the true effect is likely smaller. V1/V2 found a *negative* mean effect (treatment used 13.3% *more* tokens). The V3 design calibrates tasks to 40-60% control success, which introduces additional variance that is not accounted for in the power analysis.

3. **Experiment 5 (Difficulty-Gated)** uses 20 tasks with only 3 runs each = 180 runs total. This is the largest and most critical experiment for the product decision. With 20 tasks × 3 runs, the effective N is small for a between-subject comparison (Treatment-GATED vs Treatment-ALL vs Control). The power calculation for d=0.40 at N=60 per condition seems optimistic.

**Verdict: Adequate but optimistic. The power analysis exists (commendable) but rests on assumptions that may not hold.**

### 2.2 Control Conditions

**Good.** The spec includes three levels of controls:
- **No-cache control:** isolates the cache effect
- **Shuffled cache control:** isolates retrieval overhead from knowledge benefit (EXPERIMENTAL BRILLIANCE — this is a strong design element)
- **Fresh workspace per run:** prevents contamination

The shuffled cache control in Experiment 1 is the best methodological element in the spec. It directly addresses the confound between "having any cache" vs "having the correct cache."

**However, problems remain:**
- Experiment 3 (Anti-Patterns) lacks a shuffled anti-pattern control. If anti-pattern warnings are too specific, the treatment is doing pattern matching, not reasoning.
- Experiment 4 (Start-Here) has no control for the signal itself—just showing "here's a hint" without content.

### 2.3 Confound Management

**Partially addressed.** The spec lists threats and mitigations, but several are not fully addressed:

| Threat | Listed Mitigation | Adequacy |
|--------|-------------------|----------|
| Model stochasticity | 3 runs per cell | Acceptable |
| Task selection bias | Pre-calibration | **Untested** — the calibration protocol is described but has not been validated |
| Order effects | Latin square | Good, but the spec does not describe the Latin square implementation |
| Learning/carry-over | Fresh workspace | **Insufficient** — agents may recognize task structure even with fresh code copies |
| Prompt sensitivity | Canonical prompts | **No sensitivity analysis described** |
| Cache quality | Shuffled cache control | Good |

**The calibration step is circular:** Tasks are calibrated with the *same agent* that will be used in experiments. If the agent changes (different version, temperature), calibration is invalid.

### 2.4 Statistical Test Selection

**Good on paper, concerning in practice.**

The spec calls for:
- Wilcoxon signed-rank (paired, non-parametric) ✓
- Exact permutation test ✓
- Bayesian paired model ✓
- Bootstrap BCa 95% CI ✓
- Cohen's d + odds ratio ✓
- Bonferroni correction for 5 experiments ✓

This is a *sophisticated* statistical pipeline that exceeds most industry A/B testing and matches academic standards. **However:**

1. The V1/V2 report used a Wilcoxon test and reported p=0.96 (one-sided). This is a real finding from real data, but it reveals high variance in the primary metric (tokens). If tokens have high variance across runs, the non-parametric test is appropriate but statistical power will be low.

2. **No pre-registration is mentioned.** At ICSE/CHI, pre-registration is increasingly expected. At NeurIPS, it is strongly recommended. The spec should include a link to a pre-registered analysis plan (e.g., on OSF).

3. **The success criteria thresholds are arbitrary.** C1.1 (>= 20pp improvement), C1.2 (>= 25% token reduction), C1.3 (Cohen's d >= 0.5). These are not derived from the power analysis—they appear to be round numbers that "feel right." This is a significant weakness: the authors are essentially defining their own significance thresholds without justification.

### 2.5 Effect Size Reporting

**Commendable.** Cohen's d for continuous metrics, odds ratio for binary metrics, Bayes factor for the Bayesian model, bootstrap CIs. This exceeds typical industry practice and meets academic standards.

---

## 3. SIGNIFICANCE

### 3.1 Is a 25% Token Reduction Meaningful?

**Yes, in context.** At scale, 25% token reduction on hard tasks translates to:
- Lower API costs (significant at production scale)
- Faster task completion
- Reduced compute carbon footprint

However, the V1/V2 data suggests the *net* effect across all tasks is negative due to overhead on easy tasks. V3's Experiment 5 (Difficulty-Gated) is the only one designed to test whether selective intervention achieves net positive effect.

**The practical significance claim depends entirely on Experiment 5 succeeding.** Without Experiment 5, even positive results on Experiments 1-4 are inconclusive about real-world value.

### 3.2 Who Would Use These Results?

1. **Product teams building AI coding agents** — the direct audience. The Borg product decision framework makes this explicit.
2. **Researchers studying multi-agent systems** — the collective intelligence framing is academically interesting.
3. **ML infrastructure teams** — token reduction has direct cost implications.

### 3.3 What Would Change in the Field?

**Limited field-wide impact without stronger novelty claims.** If the results are positive:
- It would validate that collective reasoning traces (not just RAG) help agents on hard tasks
- It would shift product thinking from "structured workflows" to "targeted intervention only when needed"
- It would NOT create a paradigm shift unless the cache mechanism is shown to generalize beyond the specific task set

**The 420-run program is scoped for a product decision, not for a generalizable scientific contribution.** The task set (20 custom repos) is not a published benchmark, making comparison to prior work impossible.

---

## 4. REPRODUCIBILITY

### 4.1 Are the Task Repos Sufficient for Replication?

**No.** The spec describes a task calibration protocol but does not provide the 30 candidate hard tasks. The current dogfood repos (DEBUG-001 through DEBUG-008, TEST-001 through TEST-004, etc.) are too easy (V1/V2 found 18/19 control tasks solved). A new task set must be created, calibrated, and published for full reproducibility.

**For a top-tier submission, the task set must be:**
- Publicly released (archived with DOI)
- Benchmarked against prior systems (SWE-bench, etc.)
- Shown to generalize beyond the specific bug patterns used

### 4.2 Is the Protocol Detailed Enough?

**Partially.** The spec (404 lines) is detailed for a product experiment but would need substantial expansion for an academic paper. Missing:
- Exact prompt templates used
- Model version, temperature, seed settings
- Hardware specs for the 5 machines
- The counterbalancing procedure (which tasks in which order across runs)
- How "fresh workspace" is implemented (git clone? docker reset?)
- How Agent A's cache is constructed and stored

### 4.3 Are Analysis Scripts Provided?

**Unknown.** The search found statistical code in `borg/core/mutation_engine.py` (z-tests for A/B testing) but not the specific Wilcoxon/permutation/bootstrap pipeline described in V3. This is a red flag: the spec describes an analysis pipeline that may not be implemented.

**Recommendation:** Before running V3, implement the full analysis pipeline as a standalone script and verify it on the V1/V2 data.

---

## 5. RECOMMENDATIONS

### 5.1 What Changes Would Make This Publishable?

**For ICSE (Software Engineering):**
1. Publish the full task set on an archival venue (Zenodo with DOI)
2. Pre-register the analysis plan on OSF before running experiments
3. Add a comparison to at least one published baseline (e.g., SWE-bench Lite)
4. Replace arbitrary success thresholds with thresholds derived from the power analysis
5. Expand the related work section to include RAG, case-based reasoning, and collective intelligence in multi-agent systems

**For NeurIPS/ICML (ML/Systems):**
1. The framing needs tightening: what is the *learning* happening? (Case-based reasoning? Transfer learning? Procedural memory?)
2. Ablation: which part of the cache entry matters most? (Root cause? Fix? Time savings?)
3. Generalization: does the cache help on tasks from *different* domains than the training set?
4. The shuffled cache control is strong but needs a mechanistic explanation

### 5.2 Minimum Viable Experiment to Answer the Core Question

The core question is: **"Does selective intervention (failure memory + targeted hints) improve agent efficiency on hard tasks without adding overhead on easy tasks?"**

**MVP = Experiment 5 (Difficulty-Gated) + Experiment 1 (Cache Hits)**

- Experiment 5 directly tests the product hypothesis (selective intervention beats uniform intervention)
- Experiment 1 validates the mechanism (cache hits reduce tokens)
- This is 240 runs (60 + 180), not 420

Experiments 2, 3, and 4 are ablations that increase confidence but are not required to answer the core question.

### 5.3 Should Some Experiments Be Dropped?

**Yes, to focus resources.**

| Experiment | Drop? | Rationale |
|-----------|-------|-----------|
| Exp 1 (Cache Hits) | **Keep** | Validates the mechanism |
| Exp 2 (Failure Memory) | Drop | Overlaps conceptually with Exp 3 (anti-patterns) |
| Exp 3 (Anti-Patterns) | Keep | More specific than Exp 2 |
| Exp 4 (Start-Here) | Drop | Least novel; "which file" hints are obvious |
| Exp 5 (Difficulty-Gated) | **Keep** | Core product hypothesis |

**Recommended: Focus on Exp 1 + Exp 3 + Exp 5 = 300 runs. Reallocate saved resources to task calibration and replication.**

### 5.4 Other Priority Fixes

1. **Implement the analysis pipeline before running experiments.** The V1/V2 report's statistical analysis was minimal (Wilcoxon + sign test). V3's pipeline (Bayesian + bootstrap + permutation) is more sophisticated but not yet implemented.

2. **Justify success criteria thresholds.** The 20pp, 25%, d=0.5 targets are arbitrary. Either derive them from existing literature or run a pilot to calibrate.

3. **Add pre-registration.** At minimum, a static document with hypotheses, primary metrics, and analysis plan published before data collection begins.

4. **Reduce variance.** V1/V2 showed high per-task variance. Consider:
   - More runs per cell (5 instead of 3) for critical experiments
   - Stricter task calibration (5 runs is minimum; 10 would be better)
   - Report variance components (between-task vs within-task)

---

## SUMMARY VERDICT

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Novelty | Borderline | Instantiated concept is novel; framing needs work |
| Rigor | Borderline | Good controls, but power analysis is optimistic and success criteria are arbitrary |
| Significance | Weak Accept | Real practical value; limited scientific field impact |
| Reproducibility | Weak Reject | Task set not published; analysis scripts not confirmed |
| Overall | **BORDERLINE** | Publishable at workshop level; needs significant work for top-tier |

**Bottom line:** The V3 spec is a significant improvement over V1/V2 in methodology (shuffled controls, power analysis, calibration protocol). However, for top-tier venue acceptance, it needs: (1) a published task set, (2) pre-registration, (3) justified thresholds, (4) a mechanistic framing that connects to related work on RAG and case-based reasoning, and (5) a focused MVP that answers the core question with 300 runs rather than 420.

**For the product decision:** The experiment program is adequate to guide the Borg product decision. The independent review protocol (Teams A/B/C/D) is good practice. However, do not mistake "passes product review" for "publishable at top-tier academic venue."

---

*This audit was produced by an academic subagent applying top-tier venue standards (ICSE, NeurIPS, ICML, CHI) to the V3 experiment spec. The document reflects rigorous evaluation of methodological quality, novelty, and reproducibility.*