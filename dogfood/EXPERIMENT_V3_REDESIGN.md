# Borg v3.1.0 Evaluation — V3 Redesign
## Post-Adversarial Review Synthesis

Date: 2026-04-07
Status: REDESIGNED after 3-team adversarial review

---

## What the Reviews Found (Consensus)

### FATAL FLAW: Testing an empty knowledge base
All 3 reviewers flagged the same thing: Borg's value proposition is
**collective intelligence** (accumulated traces help future agents).
Testing with an empty DB tests the SCAFFOLD not the INTELLIGENCE.
It's like testing Google Search with an empty index.

### Statistical Issues
- N=30 underpowered (need 50+ for realistic correlation structure)
- 1 run per task-condition conflates LLM stochasticity with treatment effect
- Node assignment confounded with condition ordering
- Within-subject carryover risk

### Product Alignment
- Any positive result attributable to system prompt bias, not knowledge retrieval
- No baselines beyond with/without
- Current experiment cannot answer "does Borg add value?"

---

## V3 Redesigned Protocol

### The Three-Phase Accumulation Design

This design tests the REAL product: does accumulated knowledge help?

#### PHASE A: Knowledge Seeding (Day 1-2)
- Run 30 SWE-bench tasks through borg-enabled sonnet agents
- ALL feedback and traces are captured into borg's DB
- These are "training" tasks — not part of evaluation
- After Phase A, borg has 30 real agent traces in its knowledge base
- Task selection: Django + scikit-learn + sympy (repos with most SWE-bench tasks)

#### PHASE B: Controlled Evaluation (Day 3-5)  
Three conditions, 20 NEW tasks from SAME repos (held out):

| Condition | Description | What it tests |
|-----------|-------------|---------------|
| C0: No Borg | Sonnet with standard tools only | Baseline |
| C1: Borg Empty | Sonnet with borg tools, FRESH empty DB | Scaffold effect |
| C2: Borg Seeded | Sonnet with borg tools, DB from Phase A | Knowledge effect |

- **C2 vs C0** = total borg value (scaffold + knowledge)
- **C1 vs C0** = scaffold-only value (prompt/UX effect)
- **C2 vs C1** = pure knowledge value (the actual product differentiator)

Each task run 3x per condition (majority vote) → 20 tasks × 3 conditions × 3 runs = 180 runs

#### PHASE C: Cross-Agent Transfer (Day 6)
- 5 task pairs: Agent A solves task, trace stored
- Agent B gets similar task, borg retrieves A's trace
- Tests the "team learning" story

### Statistical Plan

**Primary analysis** (C2 vs C0):
- Cochran's Q for 3 conditions (omnibus test)
- Pairwise McNemar's with Holm correction (C2vC0, C2vC1, C1vC0)
- 20 tasks × 3 runs → majority-vote binary outcome per task-condition

**Power** (conservative):
- 20 tasks, expect 10 discordant between C2 and C0
- If 8/10 favor C2: McNemar's p = 0.055 (borderline)
- If 9/10 favor C2: McNemar's p = 0.011 (significant)
- Supplementary: GLMM on all 180 raw binary runs for more power

**Effect sizes**: Odds ratio + 95% CI for each pairwise comparison

### Node Assignment
- Fully randomized per task (not per block)
- Each VPS runs a mix of all 3 conditions
- Latin square ensures each condition runs on each node roughly equally

### Cost Estimate
- Phase A: 30 runs × ~$1.50/run = $45
- Phase B: 180 runs × ~$1.50/run = $270
- Phase C: 10 runs × ~$1.50/run = $15
- Total: ~$330

### Budget Decision: Scale Down to Fit
If $330 is too much, reduce to:
- Phase A: 20 seeding tasks ($30)
- Phase B: 15 eval tasks × 3 conditions × 2 runs = 90 runs ($135)
- Total: ~$180

### VPS Allocation
- KVM8: Orchestrator + Phase A seeding (has most disk)
- VPS1-4: Phase B evaluation (parallelized, 4 nodes × ~45 runs each)

### Go/No-Go Gates
1. After Phase A: Verify borg DB has 20+ searchable traces
2. After 5 Phase B tasks: Check C0 baseline is 40-70% (if >80%, switch to harder tasks)
3. After Phase B: Run analysis, gate Phase C on having results

### Timeline
- Day 1: Phase A seeding (automated, overnight)
- Day 2: Phase A continues + verify DB
- Day 3-5: Phase B evaluation (distributed across fleet)
- Day 6: Phase C + analysis
- Day 7: Report writing

---

## What This Design Fixes

1. ✅ Tests accumulated knowledge, not empty scaffold
2. ✅ Three conditions isolate scaffold vs knowledge effects
3. ✅ 3 runs per cell handles LLM stochasticity
4. ✅ Randomized node assignment
5. ✅ Attention-matched: C1 has same borg tools as C2, just empty DB
6. ✅ Same repos in seeding and eval (knowledge is relevant)
7. ✅ Honest about what's being tested at each level

## What's Still Weak (Acknowledged)

- N=20 eval tasks is still small for top-venue publication
- Single model (sonnet) — no generalization to other models
- No cost-effectiveness analysis built in (could add)
- No ablation of individual borg tools
- Budget may force Phase B reduction

## Recommendation

Build Phase A seeding automation FIRST. Run overnight tonight.
Then assess trace quality before committing to Phase B budget.
