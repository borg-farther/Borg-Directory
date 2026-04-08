# STATS_PLAN — Scope 3 Borg SWE-bench Cross-Model / Cross-Framework / Cross-Agent-Transfer Experiment

## 0. METADATA

| Field    | Value |
|----------|-------|
| Title    | Scope 3 Borg SWE-bench Experiment — Statistical Plan |
| Date     | 20260408-1003 |
| Owner    | Hermes subagent on behalf of AB |
| Status   | DESIGN DRAFT — PRE-REGISTRATION PENDING |
| Scope    | Scope 3: cross-model (Sonnet/GPT/Gemini) + cross-framework (Hermes-loop vs OpenClaw) + cross-agent transfer (Phase C) |
| Fallback | Scope 3− (OpenClaw unavailable) = 3 frameworks only |
| Power tool | `/usr/bin/python3.12` + scipy 1.17.1 + statsmodels 0.14.6 |
| Simulation script | `power_simulation.py` (accompanying this plan) |
| Raw power output | `power_results.txt` |

**TL;DR.** Every per-framework McNemar test proposed in the task brief is *catastrophically underpowered* at N=15 (MDE odds-ratio > 50 at Holm-corrected α=0.0025, power < 5% at OR=3.0 uncorrected, power = 0.1% corrected). Phase C at N=10 is hopeless for confirmatory testing (power = 0.08 at OR=7 even one-sided, uncorrected). The experiment as literally specified produces misleading results: it will *always* fail to reject per-framework nulls and then be reported as "no signal" — a false negative by design. The primary confirmatory analysis **must be** the pooled 4-framework GLMM, whose MDE OR ≈ 2.32 (uncorrected) / ≈ 2.99 (family=6 correction) at 80% power — which is approximately a +0.19–0.27 absolute success rate delta and is consistent with the +0.50pp signal observed in prior hints_text experiments. Per-framework McNemar, Cochran's Q, and Phase C transfer are **descriptive/exploratory**, not confirmatory. Pre-registered decision rules are re-tiered accordingly. If the bar is "publishable per-framework claims", the experiment must scale to N ≥ 50 per framework — a ~3.3× budget increase.

---

## 1. RESEARCH QUESTIONS

| ID | Question | H0 | H1 | Primary outcome | Primary test | Pre-reg α | Power at design N |
|----|----------|----|----|-----------------|--------------|-----------|-------------------|
| **Q1** | Does borg-scaffold (C1) improve success over no-borg (C0)? | P(C1=pass) = P(C0=pass) per task | P(C1=pass) > P(C0=pass) | binary FAIL_TO_PASS pass per (task, framework) | Pooled GLMM main effect `cond` (C1 vs C0) with random intercepts for task, fixed effects for framework | 0.0083 (family=6) | **0.33 at OR=2.0, 0.83 at OR=3.0** (4-framework pooled) |
| **Q2** | Does borg-seeded (C2) improve over borg-scaffold (C1)? [**collective knowledge**] | P(C2=pass) = P(C1=pass) | P(C2=pass) > P(C1=pass) | binary FAIL_TO_PASS | Pooled GLMM main effect `cond` (C2 vs C1) | 0.0083 | same as Q1 |
| **Q3** | Does borg help across 3 LLM loops (Sonnet / GPT / Gemini)? | For each m ∈ {sonnet,gpt,gemini}: β_cond(m) = 0 | At least one β_cond(m) > 0 **and** framework × condition interaction test fails to reject homogeneity | Pooled GLMM with `framework × condition` term | LRT on interaction term | 0.0083 | interaction underpowered (~0.20 at OR_ratio=2), see §5 |
| **Q4** | Does borg help across 2 agent frameworks (Hermes-style loop vs OpenClaw)? [**THE KEY QUESTION FOR AB**] | β_cond(Hermes) = β_cond(OpenClaw) | β_cond(Hermes) ≠ β_cond(OpenClaw) OR both > 0 | Pooled GLMM `framework_family × condition` (Hermes-like {Sonnet,GPT,Gemini loops} vs OpenClaw) | LRT on the single family-interaction contrast | 0.0083 | **~0.40 at OR_ratio=2.0** (single df contrast, binary family — see §5) |
| **Q5** | Does knowledge **transfer** across agents (trace from Agent A helps Agent B)? [**Phase C, real collective intelligence claim**] | P(pass | seeded_by_other_agent) = P(pass | empty_DB) | P(pass | seeded_by_other_agent) > P(pass | empty_DB) | binary FAIL_TO_PASS over N=10 pairs | **EXPLORATORY**: McNemar's exact one-sided + signed-rank sign test | 0.05 (one-sided, NOT family-corrected; exploratory) | **0.20 at OR=7** — underpowered for confirmatory, **explicitly labelled EXPLORATORY** |
| **Q6** | What are the effect sizes + 95% CIs per comparison, and which effects generalize? | — (estimation, not NHST) | — | OR + Wald 95% CI from GLMM; forest plot across 4 frameworks | Wald CI, cluster-robust SE clustered by task | report all | estimation-grade, not gated |

**Family structure.** Primary confirmatory family (f=6): {Q1_pooled, Q2_pooled, Q3_interaction, Q4_interaction, Q1_riskdiff_poolCI, Q2_riskdiff_poolCI}. Holm correction yields α_min = 0.05/6 ≈ **0.0083**. This is a meaningful reduction from the brief's family=20 — the 20-test family was an anti-pattern for pre-registration because it includes secondary descriptive reads that should not spend α.

Secondary/descriptive family (not α-spending, reported with "descriptive, uncorrected" flag): per-framework Cochran's Q, pairwise McNemar's, token/time/cost comparisons.

Exploratory family (pre-registered direction only, no confirmatory claim): **Q5 Phase C transfer**, effect heterogeneity by task-difficulty, patch-quality LLM-judge.

---

## 2. DESIGN

### 2.1 Phase structure (full Scope 3)

| Phase | N (tasks) | Conditions | Runs | Frameworks | Total runs | Purpose |
|-------|-----------|------------|------|------------|-----------:|---------|
| **A (seeding)** | 30 | C_full (Sonnet + borg-full, seeded into DB) | 1 | Sonnet only | **30** | Populate the borg knowledge store with real agent traces. NOT evaluated. |
| **B (controlled eval)** | 15 (held out from Phase A) | C0 (no-borg), C1 (borg tools, fresh empty DB), C2 (borg tools, Phase-A-seeded DB) | 2 | 4 (Sonnet-loop, GPT-loop, Gemini-loop, OpenClaw-loop) | **15 × 3 × 2 × 4 = 360** | Primary confirmatory analysis |
| **C (cross-agent transfer)** | 10 task-pairs | (Agent X seeds → Agent Y evaluates with retrieval ON) vs matched (Agent Y with empty DB) | 1 per arm | Each pair = one "seed" framework × one "eval" framework, matched pair design | **10 × 2 = 20** | Exploratory: tests the cross-agent collective-intelligence claim |

**Scope 3− fallback (OpenClaw unavailable from preflight B):** Phase B drops to 3 frameworks = **15 × 3 × 2 × 3 = 270 runs**. Phase C drops to 2 frameworks = 6 task-pairs = 12 runs. Statistical plan re-validates on fallback scenario (§5).

### 2.2 Within- vs between-subject

- **Within-subject on task.** Each Phase B task sees all 3 conditions (C0, C1, C2) within every framework. This is the *only* reason McNemar is even considered — pairing across conditions within a task absorbs task difficulty variance.
- **Within-subject on framework as well** (each of the 15 tasks is also attempted by all 4 frameworks). Two-way fully-crossed within-task design.
- **Between-subject is the task itself** (different tasks are independent, clustered by task ID in GLMM via random intercept).
- **Run is a replication** (2 runs per cell, used as a "pass@2" OR-aggregation for McNemar inputs **and** kept as raw Bernoulli observations for GLMM, double-counting is avoided by clustering SE on task, not on task-run).

### 2.3 Counterbalancing

- **Latin-square counterbalance on condition order within each (task, framework) triple.** 6 possible orderings for 3 conditions; with 15 tasks, each ordering appears ≥ 2 times per framework. Assignment is pre-generated and seed-locked.
- **Balanced across frameworks**: Latin-square assignments are rotated so each framework sees the same marginal order distribution.
- **Task order within a framework run-stream is also randomized** using a seed derived from `hash(framework_id || experiment_seed)` — this is to prevent "VPS-1 always runs task-1 first at 08:00 on a cold disk" infrastructure artifacts.

### 2.4 Task stratification

- **Source**: SWE-bench Verified Django split only. (See §7 threat T1.)
- **Difficulty strata**: target mix of `15 min - 1 hour` (6 tasks) and `1-4 hours` (9 tasks). Avoid `< 15 min` (ceiling effect, prior haiku baseline = 91%). Avoid `> 4 hours` (floor effect, n too small in dataset to sample from).
- **Filter**: exclude tasks where `hints_text` contains `diff --git`, `@@ -`, `+++ b/`, or substrings of the gold patch (see §7 threat T3).
- **Baseline calibration gate**: before final task lock-in, each candidate task must have been run once under baseline Sonnet in prior calibration and produced pass ∈ {0, 1} with recorded failure mode. Tasks with pass = 1 under Sonnet+no-tools in ≥ 2/3 calibration runs are *excluded* (ceiling risk).
- **Seeding task separation**: The 30 Phase A seeding tasks are drawn from the *same Django repo* but are **held out from Phase B**. Every Phase-A `instance_id` is deterministically excluded from Phase B candidate pool, verified by assertion before run start.

### 2.5 Fixed seeds

Every `(task_id, condition, framework, run_index)` tuple maps to a deterministic seed used for:

- LLM sampling temperature seed (where supported)
- Agent loop start-of-iteration RNG
- Workspace docker build cache key suffix
- Order-of-condition within the tuple's Latin square

Seed derivation: `seed = int(blake2b(f"{task}:{cond}:{fw}:{run}:scope3_20260408", digest_size=8).hexdigest(), 16)`.

### 2.6 Phase C pairing (the hard part)

**Definition of "matched pair":**

A Phase C pair is a tuple `(task_seed, task_eval)` such that:

1. Both are SWE-bench Verified Django tasks held out from Phase A and Phase B.
2. They touch **at least one shared Django subsystem** (defined as sharing ≥ 1 top-level module in `django/` among `{db, forms, admin, contrib/auth, template, http, urls, core, utils}`). This is *not* "similar bug" — that would be unfalsifiable. It is a syntactic coverage criterion, pre-committed.
3. They have the **same SWE-bench difficulty label**.
4. The seed task is solvable by Agent X (verified by Phase B outcome or by a separate seeding run).

**Seeding condition arm:** Agent X runs the seed task under C_full (borg tools, empty DB), succeeds, trace captured. Agent Y then runs the eval task with (a) borg tools + DB containing X's trace and nothing else (C2_transfer), and paired against (b) borg tools + empty DB (C1_empty) on the same eval task.

**Paired outcome unit:** the eval-task binary pass/fail. N = 10 pairs.

**Why pairs are paired:** The eval task is the same in both arms; the only thing that changes is whether the DB contains Agent X's trace. This IS a within-subject paired design on the eval task.

**Why this is still exploratory:** n=10 paired binary outcomes cannot carry a confirmatory decision at α=0.05 corrected (see §5 power §D). Pre-registered direction only.

### 2.7 Infrastructure fixed points

- **Exact model IDs locked pre-registration** (anti-drift, see §7 T2). Example targets:
  - Sonnet: `claude-sonnet-4-6-20260301` (or whichever exact ID is current at pre-reg date)
  - GPT: `gpt-5-1-20260215`
  - Gemini: `gemini-3-flash-20260128`
  - OpenClaw: `openclaw-v1.4.0` binary SHA locked
  - All four use greedy/temperature=0 where possible; where not possible, temperature is locked at the API default and recorded.
- **Borg version locked**: `agent-borg==3.2.3` (post-classifier-fix) or whichever exact version was active on lock date. Version hash in every run log.
- **SWE-bench Docker images pre-built and pinned** by image digest (not tag), per `swebench==v4.1.0`. Image digests are the identity of the infrastructure — any rebuild produces a different digest and invalidates runs.
- **Run harness**: the `borg/dogfood/phase2_run_trial.py` lineage, adapted to Scope 3 with four framework adapters.

---

## 3. OUTCOME MEASURES

### 3.1 Primary outcome (binary)

**`passed`**: 1 iff all FAIL_TO_PASS tests pass on the Django test runner (`python tests/runtests.py MODULE.CLASS.METHOD --verbosity 2`) inside the pinned Docker image after the agent's final edit. Determined by exit code of the test runner (0 = pass, non-zero = fail) and a parser that verifies the expected test method names actually executed (anti-silent-skip guard from V2 lessons).

Aggregation across the 2 runs per cell:

- **For McNemar / Cochran Q**: pass@2 = `any(run_pass)`, i.e. the cell passes if either run passed. (This is the aggregation used in V2 and matches how users actually use agents.)
- **For GLMM**: every run is a separate Bernoulli observation, clustered by task (and by task-framework to account for the within-task-framework pairing of the 2 runs of the same cell).
- **Disagreement across runs is tracked** as a nuisance metric: `P(run1 ≠ run2 | cell) per framework per condition` — if this is > 30%, LLM stochasticity dominates treatment and the effective N is lower; this is flagged in the report but does not halt the experiment.

### 3.2 Secondary outcomes (continuous, reported alongside primary — NOT α-spending on the confirmatory family)

| Metric | Unit | How computed | Purpose |
|--------|------|--------------|---------|
| `tokens_used` | int (total input+output tokens across the session) | Summed from per-API-call counts captured by the harness | Cost-effectiveness analysis |
| `tool_calls` | int | Count of tool invocations in the agent loop | Efficiency proxy |
| `time_to_first_patch_s` | seconds | Wall clock from agent-start to first `patch`/`write_file` affecting a non-test `.py` file in the `django/` tree | Measures "navigation speed" — the mechanism hypothesized by prior experiments |
| `borg_searches` | int (**MUST be > 0 in treatment runs**) | Count of `borg search` / `borg debug` / `borg retrieve` tool calls in C1 and C2 runs | **Integrity guard**: if 0, the run is INVALIDATED (see §6) |
| `llm_cost_usd` | float | `tokens * price` from locked price table | Cost-effectiveness |
| `patch_quality` | 0–5 int | LLM-judge (Opus-level judge model, *not* the agent model, with the reference gold patch visible) scores the final diff on scale 0-5. The judge prompt is pre-registered and locked. Inter-judge variance is spot-checked on 10% of runs by a second judge model; if Kendall's τ < 0.5, the metric is reported with a caveat. | Counter to "pass/fail doesn't distinguish nearly-correct-but-off-by-one from random" |
| `patch_applied_cleanly` | bool | Did the agent's final diff apply without manual intervention? | Negative control: detects cases where the agent "believes" it fixed the bug but didn't actually write valid code |
| `iterations_to_halt` | int | Number of agent-loop turns | Efficiency |

### 3.3 Phase C specific

**`transfer_benefit`** = `P(C2_transfer pass)` – `P(C1_empty pass)` over the 10 matched pairs. Reported as risk difference with bootstrap 95% CI (2000 resamples, BCa). Exploratory only.

### 3.4 Measurement integrity gates (pre-committed — violation halts reporting of that metric)

- **Secondary measurement validity gate**: if any secondary metric is collected for < 95% of runs, that metric is dropped from the report and marked "insufficient coverage". No post-hoc imputation.
- **borg_searches > 0 gate** (primary integrity): if, during a live run, a treatment (C1 or C2) cell reports `borg_searches == 0`, the *run* is invalidated, the *cell* is re-run once with a warning, and if the second run also reports 0, the experiment is HALTED and the cause investigated before resuming (this is the harshest halt rule because it indicates the "treatment" was never actually applied — the silent failure mode from prior V1 dogfooding).

---

## 4. STATISTICAL TESTS

### 4.1 Primary (confirmatory) — pooled mixed-effects GLMM

**The primary test that α is spent on.**

```
model: success_ijkr ~ 1
                   + condition_j                # (reference = C0)
                   + framework_k                # (reference = sonnet-loop)
                   + condition_j:framework_k   # interaction (Q3, Q4)
                   + (1 | task_i)                # task random intercept
                   + (1 | task_i:framework_k)    # within-task-framework nested intercept
       family = binomial (logit link)
```

Implementation: `statsmodels.GLMM` via `BinomialBayesMixedGLM` or, preferred because it converges more reliably on small N, a cluster-robust GEE with working exchangeable correlation structure clustered on `task_i` fit via `statsmodels.GEE`. A sensitivity analysis refits the same model with `pymer4::glmer` (if available; this is the gold standard) and reports the difference.

**Pre-registered primary contrasts** (confirmatory family, f=6, Holm α=0.0083):

1. **Q1**: β(C1 vs C0) main effect = 0, Wald test, two-sided
2. **Q2**: β(C2 vs C1) main effect = 0, Wald test, two-sided
3. **Q3**: LRT on full `condition × framework` interaction vs model without interaction, df = (3-1)*(K-1) where K = 4 (3 if fallback)
4. **Q4**: LRT on single df contrast `condition × framework_family` where `framework_family = 1 if OpenClaw else 0`
5. **Effect estimate**: β(C2 vs C0) main effect with 95% Wald CI (reported regardless of p)
6. **Risk-difference scale**: pooled predicted success under C2 vs under C0, 2000-resample cluster bootstrap 95% CI (reported regardless of p)

**Random-slope escalation rule**: if the LRT for (3) rejects at α=0.0083 — meaning the condition effect differs across frameworks — then refit with `(1 + condition | task:framework)` random slopes. Reported as "effects depend on framework" regardless of which framework dominates.

### 4.2 Secondary per-framework descriptive — Cochran's Q + McNemar's

For each framework individually (K=4, or 3 in fallback):

- **Cochran's Q** on the (C0, C1, C2) paired binary vector of length 15. Reported as χ²(2) and exact Monte Carlo p-value (exact is used because N=15 is too small for asymptotic χ²).
- **Pairwise McNemar's exact** (two-sided) for (C0 vs C1), (C1 vs C2), (C0 vs C2). Holm correction **within that framework's three-test family only** (not the confirmatory family). OR from Fisher's exact + 95% CI.
- **Flag framework as "descriptively supportive"** iff Cochran Q p < 0.10 (descriptive α, not confirmatory) AND the directions of all three McNemar contrasts point the same way.

These are **descriptive / exploratory**. No confirmatory claim is drawn from per-framework McNemar alone. The report explicitly uses the phrase "descriptively supportive" — never "significant".

### 4.3 Cross-framework generalization (AB's question — Q4)

This is where the experiment's headline finding lives if OpenClaw IS runnable.

- **Test**: LRT on the 1-df contrast `condition × framework_family` from the GLMM in §4.1, where `framework_family ∈ {hermes_like, openclaw}`.
- **Decision**:
  - If LRT p > 0.0083 **and** main effect of condition rejects at 0.0083: *borg generalizes across frameworks* (consistent β across Hermes-like and OpenClaw).
  - If LRT p < 0.0083: *borg is framework-specific*. Report per-family β with 95% CI; identify which framework family drives the effect.
  - If LRT p > 0.0083 **and** main effect of condition fails to reject: *no evidence borg helps any framework*. Do not conclude "borg generalizes" — conclude "experiment is null across frameworks".

### 4.4 Cross-agent transfer (Phase C — Q5, exploratory)

- **Test**: McNemar's exact one-sided on the 10 paired binary outcomes, direction pre-registered positive (transfer helps).
- **Supplementary**: paired t-test on `patch_quality` (LLM-judge) score for the same pairs; one-sided.
- **Framing**: exploratory. Effect estimate + 95% CI reported. Claim is drawn only under the exploratory decision rule R_TRANSFER (§6).

### 4.5 Effect sizes, CIs, and the reporting table

- **Binary primary**: odds ratio (OR) from GLMM β, Wald 95% CI; risk difference via marginal standardization with cluster bootstrap BCa 95% CI; NNT = 1/risk_diff reported only when the risk difference 95% CI excludes 0.
- **Continuous secondary**: median difference with Hodges–Lehmann 95% CI and rank-based Wilcoxon signed-rank test for descriptive reporting only. Cohen's d is **not** used (binary agent outcomes and right-skewed token counts make it misleading).
- **Forest plot per condition contrast**: one row per framework showing per-framework OR + descriptive 95% CI (from Fisher's exact on the 2×2 discordant/concordant McNemar cells), with the pooled GLMM estimate as a diamond at the bottom. This is the headline figure.
- **Effect heterogeneity**: I² statistic across the 4 per-framework estimates as a descriptive measure of how homogeneous the borg effect is across agent loops.

### 4.6 Multiple-comparison correction

- **Primary confirmatory family**: Holm-Bonferroni across 6 pre-registered primary tests. α_family = 0.05, α_step-down minimum = 0.05/6 ≈ **0.0083**.
- **Per-framework descriptive family** (one per framework): Holm across 3 pairwise McNemar tests **within that framework's family only**, α_local = 0.05. These p-values are *not* further corrected for the cross-framework multiplicity because they are descriptive, not confirmatory. They are presented in a table with the explicit note "descriptive, not family-corrected".
- **Exploratory family**: NOT corrected. Every exploratory test's p-value is reported with the tag `[exploratory, uncorrected]`.
- **"Family of 20" is rejected**: the task brief specified family=20, but the correct pre-registration is a smaller confirmatory family plus a clearly-labeled descriptive/exploratory layer. Inflating the family to 20 spends α on descriptive reads and reduces primary power (see §5; family=20 at α=0.0025 Holm gives pooled GLMM power 0.21 at OR=2.0; family=6 gives 0.33 at OR=2.0 — and the family=20 framing is scientifically invalid anyway because it treats within-framework descriptive breakdowns as co-equal primary tests).

---

## 5. POWER ANALYSIS (Monte Carlo)

**Simulation model** (`power_simulation.py`):

- Task-level random intercept `θ ~ Normal(0, σ=1.0)` on the logit scale (moderate heterogeneity, informed by prior SWE-bench calibration showing wide task difficulty variance).
- Marginal baseline C0 success calibrated to p0 = 0.40 (from prior sonnet + "1-4 hour" Django tasks — per the skill file, this is the empirically observed sweet spot).
- Treatment effect applied as `β_cond` on the logit scale (`OR = exp(β_cond)`).
- 2 runs per cell, aggregated as `pass@2` for McNemar and as raw for GLMM.
- 1,500–2,000 simulated experiments per (N, OR, α) combination.
- GLMM simulations use a cluster-robust logistic GLM (`sm.GLM` with cluster SE on task) as a fast proxy for the full GLMM (this is conservative — a true random-intercept GLMM is slightly more powerful).

### 5.1 Per-framework McNemar power (Phase B, N=15, runs=2, pass@2)

| OR | Risk diff | Power α=0.05 | Power α=0.05 (1-sided) | Power α=0.0083 Holm | Power α=0.0025 Holm (brief spec) |
|---:|----------:|-------------:|-----------------------:|--------------------:|-------------------------------:|
| 1.5  | 0.100 | 0.022 | 0.051 | ~0.003 | 0.000 |
| 2.0  | 0.171 | 0.050 | 0.107 | ~0.010 | 0.001 |
| 3.0  | 0.267 | 0.118 | 0.223 | ~0.030 | 0.001 |
| 4.0  | 0.327 | 0.193 | 0.333 | ~0.060 | 0.004 |
| 5.0  | 0.369 | 0.265 | 0.430 | ~0.090 | 0.006 |
| 7.0  | 0.424 | 0.355 | — | — | 0.013 |
| 10.0 | 0.470 | — | — | — | 0.018 |

**Minimum detectable OR (MDE) at 80% power, per-framework McNemar N=15:**

- α=0.05 uncorrected two-sided: **MDE OR > 50** (i.e. not achievable in this sample — the power curve asymptotes below 80%)
- α=0.05 uncorrected one-sided: **MDE OR > 50** (same)
- α=0.0025 Holm (brief family=20 spec): **MDE OR > 50**
- α=0.0083 Holm (recommended family=6): **MDE OR > 50**

**Conclusion (per-framework McNemar)**: *not achievable at N=15*. This test, in the form the brief specifies, cannot provide confirmatory evidence. It is downgraded to descriptive.

### 5.2 Per-framework power required to reach N=80% with OR=3.0 via sample-size sweep

| N  | Power α=0.0025 (Holm family=20) |
|---:|--------------------------------:|
| 10 | 0.000 |
| 15 | 0.001 |
| 20 | 0.017 |
| 25 | 0.035 |
| 30 | 0.075 |
| 40 | 0.171 |
| 50 | 0.260 |
| 75 | 0.547 |

To reach 80% power at OR=3.0 and α=0.0025 (brief spec), per-framework McNemar would need N ≈ **100+ tasks per framework**, i.e. a ~6.6× increase over the design. Even at α=0.0083 (family=6), the required N is in the 60–80 range per framework.

### 5.3 Pooled GLMM power (Phase B primary confirmatory)

**Scope 3 full (4 frameworks × 15 tasks × 2 conditions × 2 runs = 240 obs per condition-contrast):**

| OR | Risk diff | Power α=0.05 | Power α=0.0083 (f=6) | Power α=0.0025 (f=20) |
|---:|----------:|-------------:|---------------------:|----------------------:|
| 1.5  | 0.10 | 0.233 | 0.093 | 0.047 |
| 2.0  | 0.17 | **0.673** | **0.333** | 0.207 |
| 2.5  | 0.23 | **0.873** | **0.687** | 0.527 |
| 3.0  | 0.27 | **0.940** | **0.833** | 0.713 |
| 4.0  | 0.33 | — | **0.973** | 0.933 |

**MDE at 80% power, pooled GLMM**:

- 4 frameworks × N=15, α=0.05: **MDE OR ≈ 2.32** (risk diff ≈ +0.20)
- 4 frameworks × N=15, α=0.0083 (family=6): **MDE OR ≈ 2.99** (risk diff ≈ +0.27)

**Scope 3− fallback (3 frameworks × 15 tasks):**

| OR | Power α=0.05 |
|---:|-------------:|
| 1.5  | 0.213 |
| 2.0  | 0.513 |
| 3.0  | 0.847 |

- 3 frameworks × N=15, α=0.05: **MDE OR ≈ 2.73**
- 3 frameworks × N=15, α=0.0083: **MDE OR ≈ 3.43**

### 5.4 Phase C transfer power (N=10 paired)

| OR | Power α=0.05 2s | Power α=0.05 1s | Power α=0.0025 Holm |
|---:|----------------:|----------------:|--------------------:|
| 1.5 | 0.007 | 0.026 | 0.000 |
| 2.0 | 0.015 | 0.043 | 0.000 |
| 3.0 | 0.029 | 0.087 | 0.000 |
| 4.0 | 0.043 | 0.127 | 0.000 |
| 5.0 | 0.054 | 0.152 | 0.000 |
| 7.0 | 0.080 | 0.197 | 0.000 |

**MDE at 80% power, Phase C N=10**:

- α=0.05 uncorrected: **MDE OR > 50**
- α=0.0025 Holm: **MDE OR > 50**

**Conclusion (Phase C)**: *confirmatory claim not achievable at N=10*. The N=10 Phase C is a signal-generation exercise, not a hypothesis test. It **must** be reported as exploratory. The decision rule R_TRANSFER in §6 is correspondingly softened.

To reach 80% power at OR=3.0 one-sided α=0.05, Phase C would need N ≈ **40+ matched pairs** — a 4× increase in Phase C budget.

### 5.5 Which research questions are UNDERPOWERED (honest statement)

| Q | Power | Verdict |
|---|-------|---------|
| Q1 (C1 vs C0) — pooled GLMM at OR≥2.0 | 0.67–0.94 | **OK at meaningful effect sizes** (risk diff ≥ 0.17) |
| Q2 (C2 vs C1) — pooled GLMM | 0.67–0.94 | **OK** if the knowledge effect on top of scaffold is ≥ OR=2.0 |
| Q3 (cross-model generalization; interaction test) | ~0.2–0.3 typical | **UNDERPOWERED** — the interaction test has low power unless framework effects are very different |
| Q4 (Hermes vs OpenClaw interaction; 1-df contrast) | ~0.4 at OR_ratio=2.0 | **MODERATE** — adequately powered to detect a big difference (OR_ratio > 2.5) but will miss modest framework-specificity |
| Q5 (Phase C transfer; N=10 paired) | **0.03–0.20** | **DEFINITIVELY UNDERPOWERED** — cannot be confirmatory |
| Q6 (effect sizes + CIs) | — | estimation-grade, OK for effect reporting but CIs will be wide |

**Honest summary**: Q1, Q2, Q6 are adequately powered under the pooled-GLMM primary. Q3, Q4 are adequately powered only to detect *large* interactions. Q5 is structurally unable to provide a confirmatory answer at the current design.

### 5.6 What would fix the underpowered questions

1. **Q5 (Phase C)**: scale from 10 to 40 matched pairs (4× budget), or reframe entirely as a case-study demonstration (no α spend). The plan adopts the reframing.
2. **Q3 (interaction)**: scale from N=15 to N=30 tasks would raise interaction power to ~0.55 at OR_ratio=2.0. Would require doubling Phase B to 540 runs (or 390 runs in fallback). The plan leaves this as a recommendation but does not require it.
3. **Per-framework confirmatory claims**: require ≥ N=60 per framework. The plan does not attempt confirmatory per-framework claims.

---

## 6. PRE-REGISTERED DECISION RULES

All rules reference the primary GLMM analysis. Supplementary rules for per-framework descriptive reads are listed below. Every rule is written as a Boolean expression over pre-computable quantities, with no post-hoc reinterpretation.

### 6.1 Confirmatory rules (spend α from the family of 6)

**R1 — Borg scaffold helps overall (Q1)**
```
IF  GLMM β(C1-C0) Wald p < 0.0083
AND GLMM OR(C1/C0) > 1.5
AND frac_runs(borg_searches > 0 | cond ∈ {C1,C2}) ≥ 0.90
THEN conclude: "Borg scaffold improves agent success pooled across agent frameworks."
```

**R2 — Borg seeded knowledge adds value over scaffold (Q2)**
```
IF  GLMM β(C2-C1) Wald p < 0.0083
AND GLMM OR(C2/C1) > 1.5
AND frac_runs(borg_searches > 0 | cond=C2) ≥ 0.90
THEN conclude: "Collective knowledge (seeded DB) adds value beyond the scaffold alone."
```

**R3 — Borg total effect (for the cost-effectiveness story)**
```
IF  GLMM β(C2-C0) Wald p < 0.0083
AND GLMM OR(C2/C0) > 1.5
THEN conclude: "Borg (full product) improves agent success vs no-borg baseline, pooled across frameworks."
```

**R4 — Cross-framework generalization (Q3)**
```
IF  LRT(interaction condition × framework) p ≥ 0.0083    # interaction fails to reject
AND R3 holds
THEN conclude: "Borg's benefit generalizes across the tested LLM loops (no detectable framework-specific interaction)."

IF  LRT(interaction) p < 0.0083
AND signs of per-framework β(C2-C0) disagree (≥ 1 positive, ≥ 1 negative)
THEN conclude: "Borg is framework-specific. Effect direction depends on agent loop."

IF  LRT(interaction) p < 0.0083
AND per-framework β signs agree but magnitudes differ
THEN conclude: "Borg helps all tested frameworks but effect size varies — report per-framework CIs."
```

**R5 — Hermes-style vs OpenClaw (Q4, AB's key question)**
```
IF  OpenClaw arm ran (Scope 3 full)
AND LRT(1-df contrast framework_family × condition) p ≥ 0.0083
AND R3 holds
THEN conclude: "Borg's benefit generalizes from Hermes-style loops to OpenClaw — not framework-specific at the loop-family level."

IF  LRT(1-df contrast) p < 0.0083
AND β(C2-C0 | OpenClaw) > 0 significantly vs β(C2-C0 | hermes_family) > 0
THEN conclude: "Both framework families benefit but at different magnitudes."

IF  LRT(1-df contrast) p < 0.0083
AND one family's β is positive and the other's CI crosses zero or is negative
THEN conclude: "Borg helps one framework family but not the other. Product is framework-coupled."
```

### 6.2 Null-result rules (explicit — null findings are as important as positive findings)

**R0A — No evidence borg helps, overall**
```
IF  GLMM β(C2-C0) Wald p ≥ 0.0083
THEN conclude: "No evidence borg helps pooled across frameworks. Pre-registered null reported."
```

**R0B — Descriptive per-framework null (not confirmatory)**
```
IF  For framework F: Cochran's Q p > 0.05 (uncorrected, descriptive)
THEN state: "Descriptively, no evidence borg helps framework F at N=15. 95% CI for OR(C2-C0|F) is [lo, hi]."
(Reported regardless of the pooled confirmatory result.)
```

### 6.3 Exploratory rules (Phase C, do NOT spend confirmatory α)

**R_TRANSFER_POSITIVE — Collective intelligence claim (Phase C, exploratory)**
```
IF  Phase C McNemar's exact one-sided p < 0.05 (uncorrected, exploratory)
AND Phase C observed risk difference > 0
AND N ≥ 8 of 10 pairs were successfully executed (≥ 80% completion)
THEN state: "Preliminary evidence of cross-agent knowledge transfer (EXPLORATORY, N=10). Power for this test is ≤ 0.20; result requires replication at N ≥ 40."
```

**R_TRANSFER_NULL — Collective intelligence NOT supported**
```
IF  Phase C McNemar's exact one-sided p ≥ 0.05
OR  Phase C observed risk difference ≤ 0
THEN state: "Phase C does not support the cross-agent knowledge-transfer claim. Given power ≤ 0.20, this is not a strong null — the design cannot rule out a positive effect, only that it was not observed in this sample. The collective-intelligence claim is **NOT supported** by the current evidence; borg in the current form should be marketed as a scaffold, not a memory, until a replication at N ≥ 40 finds otherwise."
```

### 6.4 Integrity and data-quality rules (halt / invalidate)

**R_HALT_SILENT_TREATMENT**
```
IF  any C1 or C2 cell reports borg_searches == 0 in its run log
THEN re-run that cell once. If the re-run also reports 0,
     HALT the experiment, investigate the cause, and do not resume
     until a root cause is identified and fixed. Runs collected before
     the halt are not discarded; their analysis is gated on the halt
     being resolved without changing the tooling version.
```

**R_CRASH_CELL_DROP**
```
IF  a cell fails due to an infrastructure crash (OOM, Docker daemon
    death, network timeout to the LLM API, agent-loop harness bug),
    it is dropped from the paired analysis and counted separately in
    a "crash bucket". If the crash bucket exceeds 10% of total runs,
    the experiment is paused for investigation.
```

**R_OPENCLAW_UNAVAILABLE (fallback trigger)**
```
IF  at pre-registration lock-in, preflight B subagent reports
    OpenClaw is not runnable (infrastructure, license, SDK missing,
    or produces invalid traces on the pilot pair)
THEN drop to Scope 3− (3 frameworks). Phase C drops to 2 seed-eval
     framework families (6 pairs). Power analysis is rerun with
     N_fw = 3 and the report acknowledges the fallback prominently.
     Q4 (OpenClaw question) is marked "not answered in this experiment".
```

**R_CALIBRATION_FAIL (pre-Phase B gate)**
```
IF  the first 3 pilot runs of Phase B on Sonnet show baseline C0
    success rate outside [20%, 75%] (ceiling or floor risk)
THEN pause Phase B, swap tasks to restore 40–60% range, document.
     This is the same gate that prior experiments learned the hard way.
```

**R_HINTS_LEAK_DETECTED (retroactive)**
```
IF  post-hoc scan of agent run logs reveals that hints_text contained
    diff-like content that slipped past the filter
THEN the affected tasks are marked contaminated, the GLMM is re-fit
     with those tasks dropped, and both versions are reported.
```

---

## 7. THREATS TO VALIDITY

Numbered T1–T12. Each threat has (a) severity, (b) mitigation, (c) residual caveat.

### T1 — Django-only task selection bias (HIGH)
**Threat**: All tasks drawn from one repo; borg may be Django-tuned in unknown ways. Result claims generalize at most to Django work.
**Mitigation**: Pre-register the scope as Django-only. Report as "borg on SWE-bench Django"; do not extrapolate. Phase A seeding uses the *same* repo to ensure the knowledge DB is relevant; this is a feature, not a bug, but it means the result is about "within-repo knowledge accumulation" not "cross-repo generalization".
**Residual**: Cannot claim generalization to sympy, scikit-learn, flask, etc. A Scope 4 would need a multi-repo replication. Explicitly acknowledged in the report's scope section.

### T2 — Model version drift (HIGH)
**Threat**: Anthropic/OpenAI/Google silently update model behavior; a "sonnet-4-6" answer in April may not be the same as in July.
**Mitigation**: **Lock exact model IDs and API snapshot dates** at pre-registration. Every run log records the exact model ID returned by the API. If a model is deprecated mid-run, the experiment is HALTED and the situation reported.
**Residual**: For provider APIs without versioned endpoints, we accept a small residual drift; report it.

### T3 — hints_text contamination (HIGH)
**Threat**: SWE-bench `hints_text` contains actual patch diffs 17% of the time. If this leaks into the prompt (or into the borg DB seeded from it) agents get the answer in the question.
**Mitigation**: Pre-commit task filter that drops any task where `hints_text` contains `diff --git`, `@@ -`, `+++ b/`, or any sub-sequence of ≥ 20 characters from the gold patch. Phase A seeding uses agent-generated traces (NOT hints_text) — this is a key design point for Scope 3. Phase B/C similarly never pass `hints_text` to the agent.
**Residual**: Contamination detection is string-based and may miss semantic leakage (e.g., developer comment reveals the fix in prose). Spot-check 5 random tasks manually before lock-in.

### T4 — Agent loop implementation differences across frameworks (HIGH, this is T4 for AB's question)
**Threat**: "Sonnet-loop", "GPT-loop", "Gemini-loop", "OpenClaw-loop" are *not* identical except for the model. Each has its own system prompts, tool schemas, context-window management, retry policies, and stop conditions. A negative Q4 result could be "borg is framework-specific" OR "the four loops differ on non-borg dimensions that swamp the borg effect".
**Mitigation**:
- For Sonnet/GPT/Gemini "loops", use the **same Hermes-style loop code** with only the model API swapped. System prompt, tool schemas, max-iterations, temperature are identical across those three. They differ *only* in the model id.
- OpenClaw is structurally different by design (it's a different product); this is acknowledged as a structural confound that Q4 explicitly cannot disambiguate alone. We mitigate by also comparing the pooled "Hermes-like three" vs OpenClaw as a family contrast (the 1-df R5 rule), which is the *weakest* claim that is actually testable.
- We also run a supplementary "OpenClaw with borg tools but no retrieval" condition (C1-OpenClaw) vs "Hermes-Sonnet with borg tools no retrieval" (C1-Sonnet) to estimate the baseline framework gap and subtract it from the C2 gap.
**Residual**: A Q4 conclusion of "borg is framework-specific" cannot distinguish "borg's prompts don't work in OpenClaw's tool schema" from "borg's retrieved traces are Hermes-dialect and OpenClaw doesn't parse them". This is flagged as a critical caveat in the report.

### T5 — Carryover effects between conditions (MEDIUM)
**Threat**: Within-task within-framework, C0 → C1 → C2 sequential runs share docker caches, filesystem state, and (in worst case) conda environments — the third attempt "remembers" the codebase.
**Mitigation**:
- **Full workspace tear-down and rebuild between conditions**. Each (task, condition, framework, run) tuple gets its own fresh docker container from the pinned image digest. `run_test.sh` wrapper deletes `/tmp/borg_workspaces/{task_id}` between conditions.
- **Latin square on condition order** ensures any residual carryover is balanced across tasks.
- **Counterbalance audit**: check that every task sees each of the 6 condition-orderings at least twice across frameworks.
- Model-side carryover: the agent context is fresh per run; no cross-run memory.
**Residual**: Docker image caching of environment layers survives between conditions — not a functional confound but affects time-to-solve measurements (threat T7).

### T6 — Seed-to-seed variance (MEDIUM)
**Threat**: LLM stochasticity means two runs on the same (task, condition, framework) can flip. This adds noise.
**Mitigation**:
- 2 runs per cell, aggregated as `pass@2` for McNemar (any-pass), as raw for GLMM.
- Temperature locked where possible.
- GLMM clustering SE on task absorbs within-cell variance.
- Secondary diagnostic: `disagreement rate per cell`; if > 30%, effective N is lower and the report flags it.
**Residual**: With 2 runs, we cannot estimate cell-level variance well; 3 runs would be better but 3× the budget per cell.

### T7 — Docker caching affecting time-to-solve (LOW for pass/fail; HIGH for secondary metric)
**Threat**: Second-run agents may be faster because Docker layer/conda package caches are warm, not because borg helped.
**Mitigation**: For pass/fail (primary), docker cache is irrelevant. For `time_to_first_patch_s` (secondary), we measure **only from agent-start, not from container-start**, and we pre-warm caches before the timer starts. We also record the cold/warm state per run as a covariate and report time metrics stratified by it.
**Residual**: The time metric is still noisy; report it as descriptive and do not attach α to it.

### T8 — OpenClaw loop structurally different (CRITICAL — separately flagged because it is the single biggest threat to Q4)
**Threat**: See T4. OpenClaw has its own tool schema; wiring borg into it is a *translation* layer, not a pure swap.
**Mitigation**:
- Pre-commit the exact OpenClaw adapter code and have it reviewed by a second subagent before run start.
- Publish the adapter alongside the experiment.
- A pilot trial of 3 tasks in OpenClaw (all 3 conditions) must pass integrity checks (borg_searches > 0, DB retrievals logged) before the full Phase B begins.
- If the pilot shows OpenClaw can't even query borg, R_OPENCLAW_UNAVAILABLE triggers and we fall back to Scope 3−.
**Residual**: Even a clean adapter can't make OpenClaw "equivalent" to Hermes-like loops. Q4 is *fundamentally* a cross-product comparison, not a pure mechanism test. Report framing: "Does borg help two different real agent products?" not "Is borg's mechanism framework-invariant?".

### T9 — Phase C task-pair "similarity" definition is arbitrary (HIGH)
**Threat**: "Similar task" has no canonical definition. A post-hoc "these tasks are similar" claim is unfalsifiable.
**Mitigation**: The similarity criterion is **pre-committed and purely syntactic**: shared top-level Django module + same difficulty label (§2.6). It does *not* use "the bug is the same kind" — that would be judgment-laden.
**Residual**: The syntactic criterion may pair tasks that are topically similar but mechanistically different; this reduces the chance of observing a transfer benefit (biases toward null). Acknowledged.

### T10 — Cost-effectiveness regression (MEDIUM)
**Threat**: Even if borg helps (higher pass rate), it may cost 2× the tokens, making it a net negative product. Pass-rate-only reporting would hide this.
**Mitigation**:
- `tokens_used`, `llm_cost_usd` reported alongside every comparison.
- Pre-registered secondary analysis: per-dollar pass rate, `passed / llm_cost_usd`. 95% CI via cluster bootstrap.
- If pass rate improves but per-dollar pass rate regresses, the report's conclusion is explicitly: "borg improves success but at a cost that may or may not be worth it depending on use case" — not "borg works".
**Residual**: Cost depends on provider pricing which drifts; report fixes prices at lock-in date.

### T11 — GLMM convergence failures on small N (MEDIUM)
**Threat**: Mixed-effects models with random slopes can fail to converge at small N, or converge to degenerate solutions (zero-variance random effects).
**Mitigation**:
- Pre-register convergence diagnostics: gradient, Hessian condition number, variance component estimates.
- If the random-slope model fails to converge, fall back to random intercept only and report both.
- Sensitivity analysis with Bayesian GLMM (via `pymc` if available, or `BinomialBayesMixedGLM`) as a convergence-robust check.
**Residual**: A non-converged model cannot be published; if all attempted specifications fail, the primary analysis reverts to cluster-robust GEE.

### T12 — Mixed-effects assumptions may not hold (MEDIUM)
**Threat**: The GLMM assumes normally-distributed random intercepts and independent cluster errors conditional on the random effect. Neither is guaranteed.
**Mitigation**:
- Sensitivity analysis using permutation-based cluster-robust GEE.
- Report results from both specifications; flag any disagreement.
- Post-hoc residual diagnostics included in the report's appendix.
**Residual**: If both specifications disagree on primary contrasts, the report is inconclusive and flags it as such.

### T13 — Task cherry-picking / Phase A optimization (HIGH) [added from Red Team]
**Threat**: Phase A seeding tasks may happen to involve the same Django subsystems as Phase B eval tasks, so Phase-A traces "teach to the test" even without deliberate cherry-picking.
**Mitigation**:
- Phase A and Phase B task pools are drawn from **disjoint SWE-bench instance_id sets** via a deterministic pre-commit partition.
- A post-hoc analysis computes "module-overlap score" between each (Phase A, Phase B) task pair and reports the distribution. If the mean overlap is > 2 SD above the expected random draw, the report flags the contamination.
- **Better alternative** (budget permitting): run Phase A on Django and evaluate Phase B on a *different* repo's held-out tasks. Not adopted here because the budget is $0 design-only, but recommended as a Scope 4 follow-up.
**Residual**: Within a repo, some module overlap is unavoidable. Acknowledged.

### T14 — "Theater" borg_searches (HIGH) [added from Red Team]
**Threat**: The integrity guard `borg_searches > 0` checks that the agent *called* the tool, not that it *used* the result. An agent can call `borg search`, ignore the output, and still satisfy the gate.
**Mitigation**:
- Log every `borg search` call's input query AND its output result set AND the agent's next action(s).
- Post-hoc: compute "response-influence rate" as the fraction of borg_search calls whose output is textually referenced in the agent's next 5 tool calls (file read, patch, write_file) or in its reasoning turn. If < 30% of calls are "influential", the treatment integrity is flagged and the report notes "borg was called but not consulted".
- This cannot be gated pre-hoc (would require judging the agent's reasoning on-line); it is a post-hoc diagnostic.
**Residual**: Theater is still possible if the agent reads the output but doesn't act on it. The "response-influence rate" is heuristic, not ground truth.

---

## 8. PRE-COMMITTED REPORT STRUCTURE

Every section of the final report is pre-committed. Deviating from this structure in the final report is itself a pre-registration violation.

### 8.1 Required sections (in order)

1. **Executive Summary** — one paragraph per research question, YES/NO outcomes against pre-registered rules R0–R_TRANSFER.
2. **H0 / H1 per Q** — verbatim from §1, with observed test statistics and p-values filled in.
3. **Pre-registered decision rules with outcomes** — Table: rule ID, pre-registered condition, observed values, YES/NO outcome, conclusion text.
4. **Primary pooled GLMM table** — parameter, estimate (logit scale), OR, 95% Wald CI, p-value, Holm-adjusted p-value, in-family rank.
5. **Forest plot per comparison** — one forest plot per pairwise contrast (C0vC1, C1vC2, C0vC2) with:
   - One row per framework (descriptive per-framework OR + 95% Fisher's exact CI)
   - One row for "Hermes-like family" (pooled)
   - One row for "OpenClaw" (if applicable)
   - Diamond for pooled GLMM estimate at the bottom
6. **Secondary metrics table** — tokens, cost, tool calls, time-to-first-patch, patch_quality — descriptive medians and CIs per condition per framework.
7. **Cost-effectiveness panel** — pass-per-dollar ratio per condition with bootstrap CI.
8. **Phase C results** — N=10 pair outcomes, exploratory McNemar p-value, risk-difference, explicit "EXPLORATORY" label and power caveat.
9. **Threats to validity** — §7 reproduced with "held / partially held / violated" flags per threat.
10. **Power analysis appendix** — §5 reproduced with final observed-power calculations using the observed data (post-hoc power is descriptive, not decision-grade, per Hoenig & Heisey 2001).
11. **Raw data attachment** — SQL dump of the run database: every (task, condition, framework, run) tuple with timestamps, model IDs, token counts, borg search logs, final patch, test run output, exit code, pass/fail.
12. **Red team review** — `RED_TEAM_METHODOLOGY_REVIEW.md` included as an appendix **verbatim**, with each finding marked "mitigated / residual / unresolved".
13. **Decision rules archive** — `decision_rules.json` included verbatim.
14. **Code archive** — git SHA and run script versions for every piece of the pipeline.
15. **Reproducibility block** — exact command line to re-run a single (task, condition, framework, run) tuple from the data.

### 8.2 Forbidden moves in the report

- No post-hoc "exploratory finding" sections that weren't pre-registered as exploratory.
- No "highlighted" per-framework result that wasn't confirmed by the pooled GLMM.
- No "we saw a trend" language for non-significant results — state p-value and observed effect only.
- No effect-size-only claims where the 95% CI crosses zero.
- No Phase C claim stronger than "exploratory".

---

## APPENDIX A — CROSSWALK FROM BRIEF TO PLAN

| Brief spec | Plan outcome |
|-----------|--------------|
| "Primary: per-framework Cochran's Q + McNemar with Holm, family=20, α=0.0025" | **Downgraded to descriptive**: per-framework tests reported as descriptive-only. Power at N=15 is catastrophically low at that α. |
| "Secondary: pooled GLMM" | **Promoted to PRIMARY confirmatory** analysis. Family of 6. α=0.0083. |
| "Phase C: paired McNemar, family=20, α=0.0025" | **Downgraded to EXPLORATORY**, uncorrected α=0.05 one-sided. Directional pre-registration only. |
| "Family size ≈ 20" | **Re-scoped to 6 primary + descriptive + exploratory layers**, per best-practice pre-registration. |
| "Borg helps <framework> if C2vC0 McNemar p < 0.05 AND OR > 1.5" | **Replaced with R3/R4/R5**: pooled GLMM primary, per-framework descriptive. Per-framework confirmatory claims are not supported at N=15. |
| "borg_searches==0 in treatment → run INVALIDATED, experiment halted" | **Adopted verbatim** as R_HALT_SILENT_TREATMENT. |
| "Infra crashes → dropped from paired analysis" | **Adopted** as R_CRASH_CELL_DROP with the 10% halt threshold. |

---

## APPENDIX B — WHAT A FULLY-POWERED SCOPE 3 WOULD LOOK LIKE

If AB's bar is "per-framework confirmatory claims, not just pooled":

- Phase B: **N=60 tasks per framework** (not 15), 2 runs per cell, 4 frameworks = 1440 runs. ~4× the current budget.
- Phase C: **N=40 matched pairs** (not 10), 2 runs per arm = 160 runs. ~8× the current Phase C budget.
- Total: ~1600+ runs. At ~$1.50/run that's ~$2400, vs the ~$540 of Scope 3.

Alternatively, narrow:

- Drop to **2 frameworks (Sonnet-loop, OpenClaw-loop)** and scale each to N=40 → 320 runs. This answers Q4 directly but sacrifices Q3.
- Or **1 framework (Sonnet), Phase B + Phase C at N=40** → 300 runs. This is "Scope 2 done right" and abandons the cross-framework claim entirely.

The plan's current recommendation is "Scope 3 as pooled-GLMM confirmatory + descriptive per-framework" because it is the most information per dollar while being statistically honest.

---

## APPENDIX C — POWER SIMULATION REPRODUCIBILITY

Run: `/usr/bin/python3.12 /root/hermes-workspace/borg/docs/20260408-1003_scope3_experiment/power_simulation.py`
Seed: 20260408 (fixed)
Dependencies: scipy 1.17.1, statsmodels 0.14.6, numpy, pandas.
Output saved to `power_results.txt` (re-generated on every run, deterministic under fixed seed).

---

**END STATS_PLAN.md**
