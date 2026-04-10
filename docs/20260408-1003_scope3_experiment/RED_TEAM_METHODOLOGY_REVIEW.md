# RED TEAM METHODOLOGY REVIEW — Scope 3 Borg SWE-bench Experiment

## 0. POSTURE

I am the hostile committee. My job is to find every way this experiment, as designed in `STATS_PLAN.md`, produces misleading results. I am not friendly to the design and I am not friendly to the optimism the design author may have about the result. I assume the author is honest but human, and that an honest human can fool themselves with the wrong test, the wrong family, or the wrong N. I write up findings the way an external reviewer would for a top-tier venue, with severity and specific protocol mitigations.

**Findings tally**: 17 total findings (7 CRITICAL, 6 HIGH, 4 MEDIUM/LOW). 4 CRITICAL findings are pre-empted by the plan's own re-scoping (per-framework McNemar → descriptive, Phase C → exploratory, family=20 → family=6, GLMM as primary). 3 CRITICAL findings remain after that re-scoping and are listed below as **CRITICAL — open**. The plan should not run as-is until those 3 are addressed.

---

## 1. FINDINGS BY THE BRIEF'S OWN AUDIT POINTS

### (a) C1 vs C0 confound: borg's system-prompt change separable from retrieval?
**Severity: CRITICAL — open.**

**The attack.** C1 is "borg tools available, empty DB" — that is *not just* "no retrieval". It is also "your system prompt now says you have a knowledge base", "your tool list now contains `borg search`", "your token budget is partially eaten by tool descriptions", and "your reasoning style may be primed by the existence of those tools even when they return nothing". All of those are confounds for the C2-vs-C1 claim, because they are *common* between C1 and C2 (both have the prompt + tools), and they are *different* from C0 (which has neither). Therefore C1-C0 ≠ "scaffold effect" — it is "scaffold + tool description noise + token budget reallocation". And C2-C1 is sometimes interpreted as "pure knowledge effect" but if C1 already exhibits prompt-induced behavior change *that depends on whether the DB returns anything*, the comparison is corrupted.

Concretely: if `borg search` in C1 returns "no results, try X" and the agent updates its plan based on the structure of the empty response, that response itself is treatment.

**Mitigation in current plan.** Plan §3.4 sets up a "borg_searches > 0" gate but does NOT verify that the *content* differs between C1 and C2. The current plan does not separate "tool calls happened" from "tool calls returned different content".

**Required protocol fix.**
1. Pre-registered diagnostic: capture the **exact text returned** by every `borg search` call in C1 and C2. Compute the Levenshtein-normalized difference between C1 and C2 returns for the same task. If the average difference is < 0.5 (i.e., empty C1 returns are nearly identical to seeded C2 returns), then C2-C1 is mostly "presence of returned text" not "knowledge content"; report and downgrade the Q2 claim.
2. **Add a 4th condition C0.5**: borg-tools-available, empty DB, AND `borg search` is monkey-patched to return *fixed boilerplate* ("no relevant results in knowledge base"). C0.5 vs C1 then estimates the "is the structure of the empty response itself a treatment?" effect. This is a one-cell-per-task addition, not a full new arm — it can be opportunistically added on a subset of tasks without doubling Phase B.
3. Acknowledge in the report's Q2 caveat that C2-C1 is "knowledge content effect, conditional on the tool/prompt scaffold being shared". Do not interpret it as "pure knowledge". This is the most subtle confound and probably the most likely to cause an over-claim.

---

### (b) Task cherry-picking: are packs optimized for the exact Django files in the eval set?
**Severity: HIGH — partially mitigated.**

**The attack.** Phase A seeds borg's DB from 30 Django tasks; Phase B evaluates on 15 *different* Django tasks. But "different SWE-bench instance_id" does not mean "different code paths". If both pools touch `django/db/models/sql/query.py` heavily, Phase A's traces about that file will be exactly what Phase B's agents need. The "knowledge transfer" being measured is not "learning to debug Django" but "we happened to share files between pools". A skeptical reader will ask: "How do you know the result is general, vs an artifact of file overlap?"

**Mitigation in current plan.** Plan §7 T13 adds a post-hoc module-overlap diagnostic. Plan §2.4 partitions instance_ids deterministically.

**Residual attack.** Post-hoc diagnostic is descriptive; it cannot itself save the experiment if overlap turns out to be high. The plan does not pre-commit to a max-overlap exclusion threshold.

**Required protocol fix.**
1. **Pre-commit a maximum module-overlap threshold** (e.g., < 30% file overlap between Phase A pool and Phase B pool by union of touched files in gold patches). If exceeded, swap tasks until under the threshold. Done before lock-in.
2. As a stretch goal: report the GLMM stratified by per-task module-overlap quartile. If the borg effect is concentrated in the high-overlap quartile, the result is repo-overlap-bound, not "knowledge transfer".

---

### (c) Docker caching: does it mask borg operation overhead?
**Severity: MEDIUM — adequately mitigated for primary, residual for secondary.**

**The attack.** Time-to-first-patch and tool-call counts are sensitive to Docker layer cache state. If condition C2 happens to run after C1 on the same VPS, its container init is faster, making borg "look efficient". This biases secondary metrics in borg's favor.

**Mitigation in current plan.** Plan §7 T7 measures only from agent-start (not container-start) and records cold/warm cache state per run.

**Residual.** Even from agent-start, conda environment caching, swap warmup, and OS file cache survive across conditions. The mitigation reduces but does not eliminate the bias.

**Required protocol fix.**
1. Stratify time-metric reports by cache-warmth state.
2. **Drop a `flush_caches` step** (`echo 3 > /proc/sys/vm/drop_caches`, restart docker daemon between runs of the same task) on at least 1/3 of cells, used as a covariate. If the borg time advantage disappears in the cache-flushed subset, report it.
3. The pass/fail primary is unaffected; this is a caveat for secondary timing claims only.

---

### (d) Counterbalance carryover artifacts
**Severity: MEDIUM — partially mitigated.**

**The attack.** Latin-square counterbalance balances *first-order* order effects. It does not balance *higher-order* sequential effects (e.g., "having seen C2 first changes how you respond to C0 second"). With only 6 orderings spread over 15 tasks per framework, each ordering appears 2-3 times — too few to estimate carryover separately.

**Mitigation in current plan.** Plan §2.3 + §2.5 use Latin-square + workspace teardown.

**Residual.** Workspace teardown removes filesystem state; it does not remove model-side biases from the agent (within a *cell* the agent is fresh, but cross-cell on the same VPS, residual logging or rate-limit state could persist; in particular, if C0 hits the model rate limit, C1 may run with less aggressive sampling).

**Required protocol fix.**
1. Pre-register a covariate "trial position within VPS day" and include it in the GLMM as a fixed-effect control if the post-hoc residual analysis shows position-dependent variance.
2. Spread runs across enough VPS-time that no single VPS runs more than 6 tasks in sequence without a break.
3. Audit logs from all runs to confirm no rate-limit retry artifacts.

---

### (e) Theater borg_searches > 0 but agent ignores results
**Severity: CRITICAL — open.**

**The attack.** This is the most insidious failure mode: the integrity gate fires green ("borg searches > 0, treatment was applied"), the agent technically called the tool, but the agent's downstream behavior is unchanged because it ignored the response. This was already an observed failure mode in V2 calibration (the "borg empty cold-start" issue) — the agent calls borg, gets an empty or unhelpful response, and writes its own answer anyway. With Scope 3 expanding to 4 frameworks, the chance that *some* framework agents ignore borg responses goes up.

**Mitigation in current plan.** §7 T14 adds a "response-influence rate" post-hoc diagnostic.

**Residual.** Diagnostic is heuristic and post-hoc. It cannot save the data if it turns out 60% of "treated" runs were theater. Worse: a positive primary result combined with high theater rate is the worst case for AB — it looks like borg works but actually borg didn't actually do anything in the runs that "succeeded".

**Required protocol fix.**
1. **Pre-register a per-condition response-influence threshold**: if < 30% of `borg search` calls in C1 or C2 are influential (output text textually referenced in the next 5 tool calls), the cell is flagged and the result is marked "treatment integrity questionable".
2. If > 30% of *all* C2 cells are flagged, the C2 confirmatory claim is downgraded with the caveat "the treatment was nominally applied but appears to have been mostly ignored".
3. Pre-commit a small (n=20) human-spot-check of randomly-sampled C2 runs where a human rater answers: "Did the agent's solution use the content of the borg response, yes/no?" Disagreement with the automated heuristic > 25% means the heuristic is unreliable and the integrity claim is downgraded.

---

### (f) hints_text leakage despite filter
**Severity: HIGH — adequately mitigated for direct text but residual for semantic.**

**The attack.** The plan filters tasks where `hints_text` contains `diff --git`, `@@ -`, or substrings of the gold patch. But hints_text often contains *prose* descriptions of the fix that are not filtered: "the issue is that `_resolve_lookup` doesn't handle X — should add a check for Y". This prose, if leaked into Phase A traces (if the seeding agent saw it), or if leaked into Phase B prompts directly, contaminates the experiment.

The Scope 3 design says Phase A seeds from agent-generated traces, NOT hints_text. But the seeding agent itself may have read hints_text if it had access to the SWE-bench task object. And the seeding agent's *output trace* may now contain semantic snippets of the developer's prose.

**Mitigation in current plan.** §7 T3 specifies that hints_text is filtered from Phase B prompts and Phase A seeding uses agent-generated traces.

**Residual.** The seeding agent's traces may capture semantic content from hints_text indirectly if the seeding agent saw the original task. The plan does not pre-commit to running Phase A seeding on a *redacted* version of the task that strips hints_text.

**Required protocol fix.**
1. **Phase A seeding agents must be given the task with `hints_text` set to empty string**, identical to how Phase B agents see it. Pre-committed.
2. Post-hoc text-similarity check: for every Phase A trace, compute max n-gram overlap (n=4) with the original task's `hints_text`. If max overlap > 30 4-grams, the trace is contaminated and dropped from the seeding set.
3. The same n-gram check applies to Phase A traces vs Phase B `hints_text` — to catch the case where the seeding agent inadvertently produced trace text that resembles a hint for a *different* task in Phase B.

---

### (g) Interaction power: 4-way framework × 3-way condition at N=15 is not huge
**Severity: CRITICAL — open (and frankly disqualifying for the brief's original spec).**

**The attack.** This is the biggest "the experiment can't answer its own question" finding. The full interaction term in the GLMM is `condition × framework`, which has (3-1) × (4-1) = 6 interaction degrees of freedom. With 15 tasks × 4 frameworks × 2 conditions per pair × 2 runs = 240 obs per condition contrast, the *main* effect is well-powered, but the *interaction* test (the LRT in Q3) is severely underpowered. Even at OR_ratio=2.0 between frameworks, the interaction LRT power is around 0.20–0.30 (estimated from the GLMM simulation; not directly measured because the simulation models main effect only).

Specifically, the brief's Q3 ("does borg help across 3 LLM agent loops?") and Q4 ("does borg help across 2 agent frameworks?") are interaction questions, and the design's primary statistical machinery cannot reliably answer them.

**Mitigation in current plan.** §1 explicitly labels Q3 as power-limited (~0.20–0.30) and Q4 (1-df family contrast) as moderate-power (~0.40 at OR_ratio=2.0). §5.5 honestly lists Q3, Q4 as underpowered for small interactions.

**Residual.** Listing the underpoweredness honestly is necessary but not sufficient. AB asked "does it generalize across frameworks?" — the experiment cannot give a confident answer to that question at this N.

**Required protocol fix (one of the following must be chosen):**

(α) **Scale up Phase B**: increase to N=30 tasks per framework. Full Scope 3 = 720 runs. Approx doubles cost. Brings interaction power to ~0.50–0.60 at OR_ratio=2.0 — still not great but no longer disqualifying.

(β) **Narrow to a 1-df family contrast** (the R5 rule already does this for Q4 specifically): explicitly drop the full 6-df interaction LRT and replace with the single 1-df contrast. Power for the 1-df contrast is ~0.40 at OR_ratio=2.0, which is acceptable for an exploratory generalization claim.

(γ) **Reframe Q3 and Q4 as estimation, not testing**: report per-framework β with 95% CIs, and the I² heterogeneity statistic, and let the reader evaluate. Do not perform an LRT, do not draw a binary conclusion. This is the most defensible move statistically and the most cowardly rhetorically. **Recommended for a paper, not for AB's product decision.**

The current plan adopts a hybrid of (β) and (γ): R4 uses a 1-df contrast for the AB-relevant question, and the remaining cross-framework claim is estimation-only. **The hybrid is acceptable, but R4 (interaction) at N=15 with power ~0.40 cannot carry a *positive* claim — it can only carry a *null* "we did not detect a difference" claim. The plan should explicitly state that R4 producing a non-rejection is NOT evidence of generalization at this N.**

---

### (h) p-hacking via post-hoc condition redefinition
**Severity: HIGH — mitigated by pre-registration.**

**The attack.** The natural temptation: experiment runs, pooled GLMM is non-significant, the analyst notices that "if we redefine C2 as 'borg-seeded with > 5 retrieved items'", or "if we drop the 3 hardest tasks", the result becomes significant. This is a textbook garden-of-forking-paths failure.

**Mitigation in current plan.** Pre-registration of: exact task list, exact condition definitions, exact GLMM formula, exact decision rules. §6 rules are written as unambiguous Boolean expressions.

**Residual.** Pre-registration only works if it is enforced. There is no current plan provision for an external party to verify the pre-registration was followed.

**Required protocol fix.**
1. Pre-registration document is committed to git **before any Phase B runs** with a public hash.
2. Final report cites the git SHA of the pre-registration document.
3. Any deviation from the pre-registration is flagged in the report's "deviations" section, with reason. Deviations that change a statistical conclusion are flagged red.
4. (Stretch) An external subagent reviews the final report against the pre-registration and lists any deviations.

---

### (i) Negative-effect analysis: does borg HURT on some tasks?
**Severity: MEDIUM — under-emphasized in current plan.**

**The attack.** A pooled positive result hides task-level negative effects. If borg helps 8 tasks by +0.5 and hurts 7 tasks by -0.1, the pooled result is weakly positive but the product story is "borg hurts almost half the tasks". For a real product decision, the user wants to know "when does borg make it worse?".

**Mitigation in current plan.** Implicitly: GLMM with random task intercepts captures heterogeneity, but the plan does not mandate a per-task effect direction report.

**Required protocol fix.**
1. Pre-register a "negative-effect tasks table" in the report: per-task observed C2-C0 risk difference, sorted ascending. The bottom 5 tasks (where borg hurt the most) are described qualitatively.
2. Pre-register a "harm rate" metric: `frac(tasks where C2 < C0)`. This is reported alongside the pooled effect. If harm rate > 30%, the report's conclusion includes "borg helps on average but hurts a meaningful fraction of tasks".
3. Compute and report the **probability of a positive task-level effect** under the GLMM posterior (Bayesian sensitivity) — this is the "what is the chance borg helps a randomly chosen new task" number that AB actually wants for product decisions.

---

### (j) Mixed-effects assumptions: do we need random slopes?
**Severity: MEDIUM — adequately addressed.**

**The attack.** The default GLMM in §4.1 has a random intercept on task but a fixed slope for the condition effect. This assumes the borg effect is constant across tasks. If the effect actually varies by task (which is the whole point of "borg helps on some tasks more than others"), the random-intercept-only model underestimates SE and inflates test sizes.

**Mitigation in current plan.** §4.1 includes a random-slope escalation rule: if the LRT for interaction is significant, refit with random slopes.

**Residual.** The escalation rule fires only after a positive interaction. It does not handle the case where random slopes are needed but the LRT lacks power to detect it (false negative on the LRT).

**Required protocol fix.**
1. **Always fit both models** (random intercept, random intercept + random slope) and report both. The "random slope" model is the default for SE estimation; the "random intercept only" is the sensitivity check.
2. If the two models give materially different SE on the primary contrast, report both and use the *larger* SE for the confirmatory decision.
3. Convergence diagnostics from §7 T11 apply.

---

### (k) Phase C task similarity: who defines 'similar'?
**Severity: HIGH — partially mitigated.**

**The attack.** The plan §2.6 defines "similar" syntactically (shared top-level Django module, same difficulty). This is auditable but not necessarily *meaningful*: two tasks in the same Django module can require completely different bug-fix patterns, in which case the seeding trace is irrelevant.

A worse attack: the syntactic definition creates *too easy* pairs (highly overlapping module → trace is trivially relevant), inflating the transfer effect. Or *too hard* pairs (only the module is shared → trace is irrelevant), deflating it. Either way, the result depends on the definition.

**Mitigation in current plan.** §7 T9 acknowledges the syntactic criterion and notes it biases toward null.

**Residual.** Phase C is exploratory anyway, so this is less critical, but it should still be locked.

**Required protocol fix.**
1. The 10 Phase C task-pairs are pre-selected and locked at pre-registration. The exact (seed_instance_id, eval_instance_id) tuples are committed to git.
2. The "module overlap score" for each pair is reported alongside the result.
3. Phase C report explicitly includes the caveat: "the result depends on the syntactic similarity definition, which is module-overlap based; it does not generalize to arbitrary cross-task transfer".
4. If budget permits later, Phase C is re-run on a "no overlap" definition (different modules) as a robustness check.

---

### (l) OpenClaw comparison: is it apples:apples or different toolset?
**Severity: CRITICAL — open. Same root issue as T8 in the plan.**

**The attack.** OpenClaw is a different agent product. It has a different tool schema, different system prompts, different context-window management, different rate-limit behavior, possibly a different underlying model. Comparing "borg-on-Hermes-Sonnet" to "borg-on-OpenClaw" confounds "framework" with "everything else about the agent stack".

If OpenClaw shows a smaller borg effect, is it because:
(a) OpenClaw's tool integration for borg is buggy or incomplete?
(b) OpenClaw's underlying model is weaker/stronger and the effect curve is non-linear?
(c) OpenClaw genuinely doesn't benefit from borg's mechanism?
(d) OpenClaw's prompts conflict with borg's prompts in subtle ways?

The plan's R4/R5 cannot distinguish these. AB is asking a product question ("does this generalize to a competitor's framework?") which means (c) is the answer they care about, but the experiment is going to confound (c) with (a)+(b)+(d).

**Mitigation in current plan.** §7 T8 acknowledges this as the single biggest threat and proposes a pilot integrity check.

**Residual.** Acknowledgment + pilot are necessary but not sufficient.

**Required protocol fix.**
1. **Pre-publish the OpenClaw adapter code** before the experiment runs. Include it in a separate appendix. AB or another reviewer can audit it.
2. Pilot of 3 tasks × 3 conditions in OpenClaw must achieve baseline rates within 15pp of the Hermes-Sonnet pilot baseline (to rule out "OpenClaw is just much weaker") OR the Q4 conclusion must explicitly stratify by whether the OpenClaw baseline matches.
3. **Add a control condition**: OpenClaw with no borg tools at all (call it C0-OpenClaw, which is already in the design). Compare C0-OpenClaw vs C0-Hermes-Sonnet — if they differ significantly, the framework baselines are not comparable, and the borg-effect comparison must be on "delta from each framework's own C0", not on raw rates.
4. Report the "delta from own baseline" GLMM contrast as the primary cross-framework effect, NOT the raw cross-framework comparison.
5. Frame the Q4 result honestly: "Does borg help OpenClaw users when integrated as we integrated it?" — not "is borg framework-invariant?".

---

### (m) Cost-effectiveness: even if borg helps, if it costs 2× tokens, is it net useful?
**Severity: HIGH — partially addressed.**

**The attack.** Pass-rate is one half of the product story; cost is the other. A +20% pass rate that comes with +200% tokens may be worse than the baseline for any user with a budget. The plan reports cost as a secondary metric but does not pre-register a cost-effectiveness decision rule.

**Mitigation in current plan.** §7 T10 adds pre-registered cost reporting with `pass-per-dollar` and 95% CI.

**Residual.** Reporting is necessary but the *decision* is not yet pre-registered. AB will inevitably ask "is borg net useful at scale?" and we will not have a pre-committed answer.

**Required protocol fix.**

Add a confirmatory rule **R6 (cost-effectiveness)** to the family:

```
R6: Borg is net cost-effective.
IF  GLMM β(C2-C0) Wald p < 0.0083                            (borg helps at all)
AND pass_per_dollar(C2) > pass_per_dollar(C0) by ≥ 1.10 (10% efficiency improvement)
AND 95% bootstrap CI on the ratio excludes 1.0
THEN conclude: "Borg is net cost-effective at current prices."

R6': Borg is helpful but not cost-effective.
IF  R3 holds (borg helps on success)
AND pass_per_dollar(C2) ≤ pass_per_dollar(C0)
THEN conclude: "Borg improves success at the cost of increased tokens. Net cost-effectiveness depends on the user's price/quality trade-off."
```

If R6 is added, the family grows from 6 to 7 → α_min ≈ 0.0071 (Holm). Power impact is small.

---

## 2. ADDITIONAL FINDINGS NOT IN THE BRIEF'S AUDIT POINTS

### (n) Type I error inflation across Q3/Q4 if the LRT is run after a non-significant main effect
**Severity: MEDIUM.**

**The attack.** If the analyst runs Q3's interaction LRT only after seeing the main effect significant, that conditioning inflates the family-wise error rate. The plan does not say whether the LRT is conditional on a positive main effect.

**Mitigation.** Pre-register the order: LRT for interaction is performed *unconditionally* on the main effect, and both p-values enter the Holm step-down across the family of 6.

### (o) Per-framework token-cost variance is not modeled
**Severity: LOW.**

**The attack.** Different frameworks charge differently and use different amounts of tokens for "the same" work. Pooling tokens across frameworks in cost-effectiveness analysis is misleading.

**Mitigation.** Report cost-effectiveness per framework as well as pooled.

### (p) The "30 seeding tasks" Phase A is itself underpowered for "is borg trace generation working?"
**Severity: MEDIUM.**

**The attack.** Phase A runs 30 tasks under one model (Sonnet) with one config. If the seeding pipeline has a bug (traces silently empty, semantic content garbled), Phase B's C2 condition is testing a broken DB and the entire experiment is invalid. The plan has a §3.4 borg_searches > 0 gate but no Phase A-specific quality gate.

**Required protocol fix.**
1. Pre-Phase-B gate: after Phase A, manually inspect 5 randomly-sampled traces from the borg DB and verify (a) they contain agent reasoning, (b) they are retrievable by `borg search` with relevant queries, (c) the retrieved content is not boilerplate.
2. Quantitative check: count the number of unique tokens / unique file references across all 30 traces. If < 500 distinct file references or < 5000 distinct tokens, the seeding is suspiciously sparse and is investigated.
3. **Halt the experiment** before Phase B if the seeding gate fails.

### (q) Run order and parallelization confounds
**Severity: LOW.**

**The attack.** Running 360 cells across 4 VPS over multiple days exposes the experiment to time-of-day effects on LLM API providers (e.g., GPT-5 is slower or stupider during peak hours) and provider outages.

**Mitigation.** Random run-order assignment across providers (already in §2.3); record timestamps; if any provider has > 5% timeout rate during the run window, flag the affected cells.

---

## 3. SEVERITY-RANKED SUMMARY TABLE

| # | Finding | Severity | Mitigation in plan? | Required protocol fix |
|---|---------|----------|---------------------|------------------------|
| (a) | C1/C0 system-prompt confound | **CRITICAL — open** | Partial | C0.5 boilerplate-response control + Levenshtein diagnostic |
| (b) | Task cherry-picking via Phase A/B file overlap | HIGH | Partial (post-hoc only) | Pre-commit max overlap threshold + stratified report |
| (c) | Docker caching biases secondary timing metrics | MEDIUM | Adequate | Cache-flush covariate stratification |
| (d) | Higher-order carryover not balanced by Latin square | MEDIUM | Adequate | Position-in-day covariate; spread across VPS |
| (e) | Theater borg_searches (called but ignored) | **CRITICAL — open** | Heuristic post-hoc only | Response-influence threshold + human spot-check |
| (f) | hints_text semantic leakage via Phase A | HIGH | Direct text only | Phase A redacts hints_text + n-gram overlap check |
| (g) | Interaction power for Q3/Q4 at N=15 | **CRITICAL — open** | Acknowledged | Either scale to N=30 or constrain claim to 1-df contrast + estimation |
| (h) | p-hacking via post-hoc redefinition | HIGH | Pre-reg | Git-hash the pre-reg; external audit of deviations |
| (i) | Per-task harm hidden in pooled positive | MEDIUM | Implicit | Pre-register harm-rate + per-task table |
| (j) | Random slopes not always fit | MEDIUM | Adequate | Always fit both, use larger SE |
| (k) | Phase C similarity definition arbitrary | HIGH | Acknowledged | Lock pairs at pre-reg; report module-overlap; report robustness |
| (l) | OpenClaw not apples:apples | **CRITICAL — open** | Acknowledged | Pre-publish adapter; pilot baseline match; "delta from own C0" framing |
| (m) | Cost-effectiveness decision not pre-registered | HIGH | Reporting only | Add R6 cost rule to confirmatory family |
| (n) | LRT conditional on main effect inflates Type I | MEDIUM | Implicit | Pre-reg unconditional LRT |
| (o) | Cost variance unmodeled across frameworks | LOW | None | Per-framework cost-effectiveness |
| (p) | Phase A trace quality not gated | MEDIUM | None | Pre-Phase-B trace inspection gate |
| (q) | Time-of-day API variance | LOW | Adequate | Random ordering already in plan |

**CRITICAL — open**: 4 findings — (a), (e), (g), (l). All four require protocol amendments before the experiment runs.

---

## 4. BOTTOM LINE FOR THE COMMITTEE

This experiment, as designed in `STATS_PLAN.md` (which already aggressively reframes the brief's underpowered per-framework McNemar analysis), is:

- **Statistically defensible for the pooled GLMM primary** at OR ≥ 2.0 (risk diff ≥ 0.17). This is the main signal it can produce.
- **Statistically indefensible for confirmatory per-framework McNemar claims** at N=15 (no realistic effect size achieves 80% power even uncorrected). The plan correctly downgrades these to descriptive.
- **Statistically indefensible for confirmatory cross-agent transfer claims** at N=10. The plan correctly downgrades to exploratory.
- **Critically vulnerable to four open methodological issues** that should be fixed before run:
  1. C1 prompt-confound with C2 (add a boilerplate-response control or accept the caveat in the report's headline)
  2. Theater borg_searches gate is heuristic, not enforced
  3. Q3/Q4 interaction tests are underpowered even after the 1-df contrast simplification
  4. OpenClaw is not apples-to-apples with Hermes-style loops, and the design cannot disentangle "framework difference" from "borg failure in OpenClaw"

The recommendation to AB is **PROCEED WITH MODIFICATIONS** — accept the pooled GLMM as the primary analysis, accept the per-framework descriptive read, accept the Phase C exploratory framing, and adopt the four protocol amendments above. **Do not run as a literal interpretation of the brief** — the brief's family=20 / per-framework McNemar / Phase C confirmatory framing produces a guaranteed-null experiment that wastes the budget.

If AB's actual question is "does borg generalize to OpenClaw users?" and they need a confident answer, **scale Phase B to N=30 per framework** (~720 runs) and Phase C to N=40 pairs. Otherwise, accept that this experiment is a *generalization probe*, not a confirmatory cross-framework claim.

---

**END RED_TEAM_METHODOLOGY_REVIEW.md**
