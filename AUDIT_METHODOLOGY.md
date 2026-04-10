# BORG V3 EXPERIMENTAL DESIGN — INDEPENDENT METHODOLOGY AUDIT

**Reviewer:** Independent Subagent (Methodologist)
**Date:** 2026-03-31
**Documents Reviewed:** EXPERIMENT_V3_SPEC.md, EXPERIMENT_REPORT.md
**Status:** CRITICAL FLAWS IDENTIFIED

---

## EXECUTIVE SUMMARY

The V3 spec addresses several V1/V2 failures, but introduces new methodological problems while failing to fix others. The experiment design has **14 critical flaws** across construct, internal, ecological, and statistical validity. The most serious issues could produce false positives that justify shipping a product that adds overhead rather than value.

---

## 1. CONSTRUCT VALIDITY: Are we measuring what we think we're measuring?

### 1.1 CACHE HIT ≠ Collective Intelligence

**CRITICAL FLAW:** The spec describes the cache providing:
```
"ROOT CAUSE: get_user_data() returns None, not {}
FIX: Change users.get(user_id) to users.get(user_id, {})
ALSO: Add None check in normalize_data()
TIME SAVED: Agent A spent 180s on wrong hypothesis"
```

This is **solution copy-paste**, not collective intelligence. Agent B receives the actual root cause and fix. If Agent B successfully solves the task, we cannot distinguish between:
- (a) Agent B reasoning about the solution and applying it (intelligence)
- (b) Agent B verbatim applying cached instructions (rote retrieval)

**The experiment conflates "having access to a correct solution" with "learning from a solution."** A true collective intelligence test would provide reasoning chains or failure patterns without revealing the fix.

### 1.2 FAILURE MEMORY = Prompt Injection, Not Knowledge Transfer

**CRITICAL FLAW:** The failure warning is literally:
```
"WARNING: Approach X was tried by another agent and failed because Y.
Do not try approach X."
```

This is **prompt injection** — instructing the agent to avoid a specific approach. The agent is being told what to do, not learning from failure. This tests **compliance with instructions**, not **knowledge transfer**.

A valid knowledge transfer test would:
- Provide the failure context (what happened, why it failed)
- Allow the agent to reason about alternative approaches
- NOT explicitly prohibit the failed approach

### 1.3 Token Count as Efficiency Proxy — Unresolved from V2

**CONTINUING ISSUE:** V2 Report (Finding 5) explicitly states: "Token measurement is noisy. We used subagent output token estimates, not actual API tokens."

V3 Spec claims: "Use actual API token counts from delegate_task metadata" (Section 0, V3 Fix column)

**PROBLEM:** This is a bare assertion. The spec provides no:
- Verification that delegate_task actually exposes accurate token counts
- Evidence that these are actual API tokens, not estimates
- Error bars on token measurement
- Comparison between reported and actual API tokens

Without empirical verification, token counts remain a noisy proxy.

### 1.4 check.sh Pass/Fail — Adequate But Underspecified

check.sh pass/fail is reasonable for code fix tasks IF:
- It validates correctness, not just syntax
- It handles partial solutions consistently
- Timeout behavior is well-defined
- It doesn't have false positives/negatives

**The spec never describes what check.sh does.** This is a black box. In V2, we saw tasks where treatment "fixed the bug" but the table shows both PASS and token counts — unclear if check.sh validated the fix or just syntax.

**Recommendation:** Define check.sh behavior explicitly, including edge cases.

---

## 2. INTERNAL VALIDITY: Are conclusions causally warranted?

### 2.1 ATTRIBUTION PROBLEM: Borg vs. Any Additional Context

**CRITICAL FLAW:** The shuffled cache control is supposed to isolate "cache knowledge" from "having any additional context." But this control is INSUFFICIENT.

**The Problem:** Both treatment and shuffled-cache give Agent B additional information beyond the task description. The shuffled cache still tells Agent B:
- That there is a cache
- That previous agents worked on similar tasks
- General domain information (even if wrong task)

**What this means:** If shuffled-cache produces improvement, we can't attribute the real cache's benefit to "correct knowledge." We can only say "any cache-like structure helps."

**A better control would be:** A task with NO cache information at all (neither correct nor shuffled). But this is already the control condition. The shuffled control should be computing the delta: shuffled vs. no-cache.

**Actually, looking at the design again:**
- Control: No cache access
- Treatment: Correct cache
- Shuffled: Wrong cache from different task

If shuffled helps at all vs. control, the interpretation is that ANY cache-like context helps. If shuffled helps 50% as much as correct cache, then correct cache's effect is only half attributable to actual knowledge.

**The shuffled control does NOT isolate the knowledge component — it isolates the INFORMATION component.**

### 2.2 Agent B Problem — Same Agent, Different Tasks?

**CRITICAL FLAW:** The spec says "Agent A solves tasks. Agent B gets the same tasks."

**But it never specifies whether Agent A and Agent B are:**
- The same model instance with different weights?
- Different model instances?
- Same model but different temperature/seed?
- The same agent at different times?

If Agent A and Agent B are the **same model** (e.g., both are "claude-3-opus"), then Agent B has already seen its own solutions during Phase 1 if we reuse tasks across experiments. The "cache hit" is just Agent B remembering its own work.

**Even if we reset the workspace**, the agent's weights are unchanged. Any pattern-learning from Phase 1 persists into Phase 2.

**This is a catastrophic confound.** The "collective intelligence" could just be "Agent B benefited from having solved the task before."

**The spec should explicitly state:** Agent A and Agent B are distinct model instances with no shared weights or context.

### 2.3 3 Runs Per Cell — Dangerously Underpowered

**SERIOUS FLAW:** AI agents have HIGH variance in behavior:
- Temperature produces different outputs
- Roaming attention (reading different files first)
- Different hypothesis orderings
- Tool call variations

V2 found that treatment used MORE tokens on 74% of individual tasks but the aggregate was +13%. This means the variance across tasks is ENORMOUS and the effect is inconsistent.

**With 3 runs per cell:**
- Median of 3 is used (good — robust to outliers)
- But 3 observations gives NO estimate of the distribution
- We can't tell if the effect is consistent or if it's driven by outliers
- We can't compute a reliable variance estimate

**For detecting d=0.58 (medium effect) with α=0.01:**
- n=10 tasks × 3 runs = 30 observations per condition
- But the unit of analysis is TASK (paired design)
- So we have n=10 paired observations after aggregation

**n=10 is marginal for detecting medium effects.** V2 showed that with n=19, p=0.96 for the token reduction hypothesis. With n=10, we'd need an even larger effect.

### 2.4 Counterbalancing — Incomplete Specification

**MINOR FLAW:** The spec mentions "Latin square counterbalancing" but never specifies:
- The actual Latin square structure
- How many sequences are used
- Which tasks are in which position
- How carryover/learning effects are handled

A Latin square with 10 tasks would have 10 rows and 10 columns. With 3 runs per cell, this becomes complex. The spec should provide the actual counterbalancing schedule.

---

## 3. ECOLOGICAL VALIDITY: Do these experiments reflect real-world use?

### 3.1 Synthetic Seeded-Bug Tasks — Ecologically Invalid

**CRITICAL FLAW:** V3 relies on 20 tasks with "seeded bugs" — artificial bugs planted by researchers who also know the wrong approaches and common traps.

**Problems with real-world agent work:**
1. **Real bugs have no "known wrong approaches."** The trap approaches in Experiment 2 are artificially created. Real agents encounter novel failures.

2. **Root causes are discovered, not known.** The cache assumes root causes are known and cached. But in reality, when an agent fails, we rarely know WHY it failed — only that it did.

3. **Anti-patterns are post-hoc generalizations.** The spec says anti-patterns come from "real failures." But how are these failures identified, classified, and verified? The experiment assumes perfect knowledge of failure patterns.

4. **Task difficulty is artificial.** Pre-calibration ensures 40-60% control success. Real agent tasks don't come with difficulty labels. The difficulty-gated intervention (Experiment 5) requires a difficulty selector — but how does the real system know task difficulty BEFORE running the agent?

### 3.2 Forced Protocol vs. Real-World Agent Behavior

**CRITICAL FLAW:** The spec imposes a forced protocol:
- Agent A MUST solve the task and cache the result
- Agent B MUST retrieve from cache (treatment) or not (control)
- Agents don't choose whether to use borg

**In V2:** "Agent voluntarily uses borg" was a failure — borg_search was never called. V3 ignores this and forces usage.

**Real-world problems this ignores:**
1. **When should agents WRITE to the cache?** The spec assumes all task solutions should be cached. But trivial solutions pollute the cache.

2. **When should agents READ from the cache?** The spec forces retrieval. But agents might waste time on stale or incorrect cache entries.

3. **Cache coherence.** If Agent A's solution is wrong, Agent B adopting it fails. There's no mechanism for cache invalidation.

4. **Selective trust.** Real agents would evaluate cache entries, not blindly apply them.

### 3.3 delegate_task as Proxy — Unvalidated Assumption

**SERIOUS FLAW:** The spec assumes `delegate_task` is a valid proxy for "real agent behavior." But:

1. What model is `delegate_task` using? If it's a lightweight model, results may not generalize.

2. `delegate_task` is a SUBAGENT mechanism — it spawns a child agent with a specific prompt. This is not how production agents work.

3. The spec provides no evidence that `delegate_task` behavior correlates with real-world agent behavior.

---

## 4. STATISTICAL VALIDITY: Is the analysis plan sound?

### 4.1 n=10 Tasks — Underpowered for Detection Claims

**CRITICAL FLAW:** Power analysis claims d=0.58 is detectable with 10 tasks. But:

**The math:**
- d = 0.58 = (μ_treatment - μ_control) / σ_pooled
- For d=0.58 with α=0.01 (Bonferroni-adjusted), power=0.80
- Required n ≈ 55 per group (Cohen's sample size tables)

**But the spec says 10 tasks × 3 runs = 30 observations per condition, yielding n=10 after median aggregation.**

**The problem:** The power analysis appears to assume 60 independent observations, not 10 paired observations. After aggregation to median-per-task, effective sample size is 10.

**With n=10, detectable effect is much larger:**
- For paired t-test with n=10, α=0.01
- To detect d=0.58 with power=0.80, you'd need much smaller error variance
- In practice, with AI agent variance, you'd need d > 1.0

### 4.2 Success Criteria Thresholds — All Arbitrary

| Criterion | Target | Arbitrary? |
|-----------|--------|------------|
| C1.1 Success rate improvement | ≥20 percentage points | YES — no justification |
| C1.2 Token reduction | ≥25% (p<0.05) | YES — pulled from V2's failed E2 target |
| C1.3 Cohen's d | ≥0.5 | YES — standard "medium" but not task-specific |
| C2.1 Avoidance rate | ≥70% | YES — why not 60% or 80%? |
| C2.2 Success rate improvement | ≥15 percentage points | YES |
| C3.1 Error rate reduction | ≤50% of control | YES |
| C4.1 Files read | ≥50% reduction | YES |
| C5.3 Easy task overhead | <5% | YES |

**None of these thresholds are derived from:**
- Task difficulty analysis
- Baseline variance estimation
- Minimum clinically/economically meaningful effect
- Cost-benefit analysis of borg overhead

**The 25% token reduction target came from V2's failed E2 criterion.** Reusing a failed target as a success criterion is circular reasoning.

### 4.3 Bonferroni Correction — Adequate But Power Concerns

**The Bonferroni correction is appropriate** (α=0.05/5 = 0.01). But:

**Combined with n=10, this leaves almost no power.** To detect a true medium effect (d=0.5) with α=0.01 and n=10, you'd need unrealistically low variance.

**The spec SHOULD:**
- Use Benjamini-Hochberg FDR correction (less conservative)
- Pre-specify a primary hypothesis per experiment (already done)
- Acknowledge power limitations explicitly

**Currently:** The spec claims detection power that the sample size cannot support.

### 4.4 Analysis Pipeline — Good on Paper, Untested in Practice

The 8-step analysis pipeline is comprehensive:
```
Step 1: Aggregate 3 runs → median
Step 2: Shapiro-Wilk normality test
Step 3: Parametric or non-parametric
Step 4: Permutation test
Step 5: Bayesian model
Step 6: Bootstrap CI
Step 7: Effect size
Step 8: Report everything
```

**Problems:**
1. **Step 2 (normality test) with n=10:** Shapiro-Wilk has low power with n<20. Non-normality won't be detected.

2. **Step 5 (Bayesian) requires priors:** No priors specified. Default priors could be informative.

3. **Step 6 (Bootstrap with n=10):** Bootstrap is unreliable with n<15-20.

---

## 5. MISSING EXPERIMENTS: What should we test that we're NOT testing?

### 5.1 NEGATIVE TRANSFER — Not Tested

**CRITICAL OMISSION:** The spec never tests when the cache HURTS performance.

**V2 showed:** Treatment used MORE tokens on 74% of tasks. This is negative transfer.

**V3 never studies:**
- When does cached information mislead agents?
- Can stale cache entries cause failure?
- Does wrong-context cache cause agents to waste time on irrelevant approaches?

**Required experiment:** Run agents on tasks where the cached approach is subtly wrong. Measure if agents are misled by bad cache.

### 5.2 LONG-TERM EFFECTS — Not Tested

**CRITICAL OMISSION:** The spec treats cache as static. But:

1. **Cache staleness:** When does cached information become harmful rather than helpful?

2. **Agent dependency:** Do agents that use cache repeatedly lose ability to solve tasks independently?

3. **Cache value decay:** How does the same cache entry perform over time?

4. **Repeated exposure effects:** Does seeing the same failure warning 5 times vs. 1 time change behavior?

### 5.3 AGENT HETEROGENEITY — Not Tested

**CRITICAL OMISSION:** The spec assumes borg works uniformly across agents. But:

1. **Different models:** Does borg help Claude vs. GPT vs. Codex differently?

2. **Same model, different sizes:** Does borg help more on smaller models (which need more guidance)?

3. **Agent skill levels:** Does borg help novice agents more than expert agents?

4. **Personality variation:** Some agents might distrust cached information. Does this vary?

**Required:** At minimum, run key experiments with 2-3 different agent models and compare effect sizes.

### 5.4 CACHE MAINTENANCE COST — Not Tested

**CRITICAL OMISSION:** The spec focuses on "does borg help?" but never asks "at what cost?"

**Missing analysis:**
1. **Storage cost:** How much disk/memory does the cache consume at scale?

2. **Write latency:** When does writing to cache add overhead vs. just solving?

3. **Read latency:** Does cache retrieval add meaningful latency to agent thinking?

4. **Curator overhead:** Who/what maintains cache quality? How much effort?

5. **Total cost of ownership:** V2 showed easy tasks have overhead. What's the break-even point where hard-task savings outweigh easy-task overhead?

### 5.5 DIFFICULTY SELECTOR ACCURACY — Not Validated

**CRITICAL OMISSION:** Experiment 5 tests "difficulty-gated intervention" but assumes we can accurately identify hard tasks BEFORE the agent runs.

**Problems:**
1. How does the system know task difficulty before running?
2. What happens when the selector is wrong?
3. What's the accuracy of the difficulty selector?
4. Is the selector better than random?

**Required:** Validate the difficulty selector independently. Report precision/recall for hard-task identification.

---

## 6. ADDITIONAL CRITICAL ISSUES

### 6.1 GO/NO-GO Decision Rule is Asymmetric

The spec says:
- ≥3 capabilities GO → ship with proven capabilities
- 1-2 GO → ship minimal
- 0 GO → kill product

**Problem:** This encourages shipping partial success even if each capability has marginal benefit. There's no minimum effect size threshold.

**Should be:** Each capability needs a minimum meaningful effect size (e.g., d ≥ 0.3 AND at least 15% token reduction on hard tasks).

### 6.2 V2 Result Ignored in V3 Design

V2 found:
- Treatment HURT on 74% of tasks
- Only 1/19 tasks showed clear benefit (DEBUG-002, where control failed)
- Easy tasks consistently showed overhead

**V3 doesn't address WHY V2 failed:**
- Is the structured workflow the problem (V2 Finding 1)?
- Does removing workflow phases fix the overhead issue?
- How does V3's "targeted hints" differ from V2's "structured phases"?

**The spec should explicitly analyze V2's failure mode and show how V3 addresses it.**

### 6.3 Calibration Is Circular

Section 7 describes pre-calibration: run each task 5×, keep only 30-70% success tasks.

**But this calibration uses the SAME AGENT that will run the experiment.** If the agent improves between calibration and experiment (learning), the calibration is invalid.

**More importantly:** Tasks are selected to be "hard enough" (40-60% success). This means we're specifically choosing tasks where the control barely works. This is a form of selection bias — we select tasks where there's room for improvement, then measure improvement.

**This systematically inflates effect estimates.**

### 6.4 No Human Baseline Comparison

The spec never compares agent performance to a human developer solving the same tasks.

**Without human baseline:**
- We don't know if borg brings agents to human level
- We don't know if borg helps agents exceed human performance
- We can't contextualize the token savings

**At minimum:** Have a human developer solve 3-5 of the hardest tasks. Compare token counts and success rates.

---

## 7. SUMMARY TABLE: Critical Flaws

| ID | Category | Severity | Issue |
|----|----------|----------|-------|
| 1 | Construct | CRITICAL | Cache hit measures retrieval, not collective intelligence |
| 2 | Construct | CRITICAL | Failure memory is prompt injection, not knowledge transfer |
| 3 | Construct | MAJOR | Token measurement not verified as actual API tokens |
| 4 | Internal | CRITICAL | Agent B may be same model remembering own solutions |
| 5 | Internal | CRITICAL | Shuffled control doesn't isolate knowledge component |
| 6 | Internal | MAJOR | n=10 underpowered for claimed detection (d=0.58) |
| 7 | Internal | MINOR | Counterbalancing schedule unspecified |
| 8 | Ecological | CRITICAL | Synthetic seeded bugs don't represent real work |
| 9 | Ecological | CRITICAL | Forced protocol ignores agent choice |
| 10 | Ecological | MAJOR | delegate_task as proxy is unvalidated |
| 11 | Statistical | CRITICAL | n=10 × Bonferroni α=0.01 = insufficient power |
| 12 | Statistical | MAJOR | All success thresholds are arbitrary |
| 13 | Missing | CRITICAL | No negative transfer experiments |
| 14 | Missing | CRITICAL | No long-term cache effects |
| 15 | Missing | CRITICAL | No agent heterogeneity analysis |
| 16 | Missing | CRITICAL | No cache maintenance cost analysis |
| 17 | Missing | CRITICAL | No difficulty selector validation |
| 18 | Design | MAJOR | GO/NO-GO lacks minimum effect size threshold |
| 19 | Design | MAJOR | V2 failure mode not addressed in V3 design |
| 20 | Design | MAJOR | Calibration is circular (uses same agent) |

---

## 8. RECOMMENDATIONS

### Must-Fix Before Execution:

1. **Validate token measurement:** Confirm delegate_task exposes actual API tokens, not estimates. Run a calibration experiment.

2. **Fix Agent A/B confound:** Explicitly state Agent A and Agent B are distinct model instances. Never reuse tasks across experiments without task pool expansion.

3. **Increase n or lower α:** Either increase to 20 tasks per experiment, or use α=0.05 without Bonferroni (accept family-wise error).

4. **Add negative transfer experiment:** Test when cache hurts. This is essential for understanding limits.

5. **Justify thresholds:** Either derive thresholds from cost-benefit analysis or use sequential analysis to determine thresholds empirically.

6. **Address V2 failure mode:** Explicitly explain how V3's "targeted hints" differs from V2's "structured phases" and why it won't add overhead.

### Should-Fix:

7. **Specify counterbalancing schedule:** Provide the actual Latin square.

8. **Add human baseline:** One human developer, 5 hard tasks.

9. **Validate difficulty selector:** Run classifier on tasks before experiment.

10. **Add long-term experiments:** Test cache staleness and repeated use effects.

### Consider:

11. **Use BH correction instead of Bonferroni:** Less conservative, maintains more power.

12. **Define check.sh behavior:** Document what it validates.

13. **Add agent heterogeneity:** Test with 2-3 model variants.

---

## 9. FINAL VERDICT

**The V3 spec is a significant improvement over V1/V2 in structure and rigor.** The separate experiments, pre-registration, and shuffled-cache controls address real problems.

**However, it has fundamental flaws that will produce misleading results:**

1. **Construct validity is broken for Exp 1 and 2** — cache hit is retrieval, not intelligence; failure memory is instruction, not learning.

2. **Statistical power is insufficient** — n=10 cannot support the claimed detection of medium effects at α=0.01.

3. **Ecological validity is lacking** — synthetic tasks and forced protocol don't reflect reality.

4. **Critical missing experiments** — negative transfer and long-term effects are essential but absent.

**If executed as specified, this experiment would likely produce false positives for some capabilities while missing the fundamental problem (cache overhead on easy tasks).**

**Proceed only after addressing the Must-Fix items.**

---

*Audit completed: 2026-03-31*
*This review followed the experimental design review protocol: find problems, not validate.*