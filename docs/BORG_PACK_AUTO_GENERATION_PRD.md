# Borg Pack Auto-Generation — Product Requirements Document
## Version 1.0 | 2026-04-02

---

## 1. Executive Summary

**What this PRD defines:** The complete success criteria framework for Borg's pack auto-generation system — what to build, how to verify it works, and the pre-launch experiments that validate the approach before investing in building.

**Critical design principle:** We validate the approach before building the pipeline. The extraction pipeline is worthless if structured pack guidance doesn't help agents. Run the dogfood experiment first.

**Two-track outcomes:**
1. **Immediate value:** borg debug CLI + seed packs help agents solve debugging problems faster/better
2. **Compounding value:** the collective gets smarter as more agents use it

---

## 2. Success Criteria Framework

All criteria are binary-go or no-go. No "mostly working."

### 2.1 Track 1: Immediate Value (Pre-Build Experiments)

These experiments validate the approach before building the full pipeline.

#### E1: Dogfood A/B — Does structured guidance help?

**Question:** Does giving an agent structured pack guidance (investigation_trail + resolution_sequence + anti_patterns) improve task outcomes vs. no guidance?

**Protocol:**
```
Tasks: 20 SWE-bench Django Verified tasks (difficulty: 1-4 hours)
Agent: MiniMax M2.7 subagent
Environment: Docker containers with correct Django versions

TREATMENT: Agent receives borg_observe(task, context_dict) output before starting
  → Structured pack with investigation_trail (files in order), resolution_sequence, anti_patterns
CONTROL: Same agent, same tasks, no borg access

Metrics (per task):
  - Task outcome: PASS / FAIL
  - Tokens used (subagent output)
  - Time to first relevant file read (seconds)
  - Guidance adherence: did agent read a suggested file first? (trace analysis)
  - Resolution adherence: did agent try a suggested resolution? (trace analysis)
```

**Pre-registered success criteria (set before running):**
| Metric | Target | Rationale |
|--------|--------|----------|
| Task success rate (treatment) | ≥ 80% | vs 43% baseline from prior experiment; 80% = practical usefulness threshold |
| Guidance adherence | ≥ 50% | If agents ignore guidance, the packs are wrong or the UX is wrong |
| Time to first relevant file | < 60 seconds | investigation_trail ordering is the core value prop |
| Token cost (treatment vs control) | ≤ 50% of control | If structured guidance costs more tokens, it's overhead not value |
| Task success rate delta | ≥ +20pp vs control | Meaningful improvement over control |

**Pass:** All 5 criteria met → proceed to Phase 1
**Fail:** Any criterion unmet → iterate on packs, rerun E1

**Outlier handling:**
- If 3+ tasks fail due to environment issues (not guidance quality) → exclude from analysis, re-run those tasks
- If treatment success < 60% on any single hard task (1-4 hour difficulty) → investigate specific pack deficiency

#### E2: CLI Usability — Does the output make sense?

**Question:** Can a developer understand and use the `borg debug` output without training?

**Protocol:**
```
Participants: 5 developers (not the borg team)
Task: Use `borg debug` on 3 real bugs from their codebase
Method: Think-aloud protocol; note confusions and misunderstandings

Metrics:
  - Time to first relevant file read: < 2 minutes from CLI output
  - Correct problem_class understood: ≥ 4/5 participants
  - Would use again: ≥ 4/5 participants
```

**Pass:** All 3 criteria → UX is acceptable
**Fail:** Iterate on CLI output format, rerun

### 2.2 Track 2: Compounding Value (Post-Launch Experiments)

These measure whether the system gets smarter over time.

#### E3: First-User Dogfood — Does it work for new users?

**Protocol:**
```
Participants: 5 external developers (B2C, not team members)
Task: Install borg and use it on a real debugging problem in their codebase
Constraints: No instructions beyond README; < 30 minutes to first value

Metrics:
  - Installation success rate: 5/5
  - Time to first useful guidance: < 10 minutes
  - Would recommend: ≥ 4/5
```

**Pass:** All 3 criteria → ready for broader launch
**Fail:** Installation or onboarding issue → fix before broader launch

#### E4: Longitudinal Cohort Study

**Question:** Does Thompson Sampling precision@1 improve over time as posteriors update?

**Design:**
```
Cohort A: First 50 tasks (weeks 1-2)
Cohort B: Tasks 51-150 (weeks 3-8)

Compare per cohort:
  - Thompson Sampling precision@1 (% of tasks where selected pack = correct pack)
  - Task success rate
  - Time to first relevant file

Statistical test:
  H0: precision@1(Cohort A) = precision@1(Cohort B)
  H1: precision@1(Cohort B) > precision@1(Cohort A)
  Test: one-tailed t-test, α = 0.05

  Additional: linear regression on precision@1 over all tasks.
  Reject H0 if slope > 0 and p < 0.05.
```

**Pass:** Cohort B precision ≥ Cohort A + 10pp → compounding is real
**Fail:** No improvement → the flywheel is not compounding; investigate why

#### E5: Auto-Generation Audit (Monthly)

**Question:** Is the auto-generation pipeline producing valid, useful packs?

**Metrics (measured monthly):**
| Metric | Target | What it measures |
|--------|--------|-----------------|
| Extraction yield | ≥ 20% of successful traces → CANDIDATE packs | Pipeline is working |
| Qualification pass rate | ≥ 60% of extractions pass confidence gate | Extraction quality |
| A/B resolution rate | ≥ 80% of A/B tests resolve within 100 uses | Learning loop closing |
| Pack growth | ≥ 2 new ACTIVE packs per week | Knowledge base growing |
| Promoted pack success rate | ≥ 85% (promoted packs perform ≥ seed packs) | Quality control working |

**Pass:** All 5 metrics met for 3 consecutive months → system is compounding
**Fail:** Any metric below threshold for 2 consecutive months → investigate and fix

### 2.3 Ongoing Monitoring (Production)

These run continuously after launch. Alerts fire if thresholds breached.

| Metric | Alert threshold | Action |
|--------|----------------|--------|
| Feedback capture rate | < 20% of borg debug runs | Add one-click feedback button; investigate UX |
| Posterior collapse | Any pack α > 10 × β | Increase exploration budget ε; investigate dominance |
| A/B test stuck | Any test running > 200 uses without resolution | Auto-revert; flag for human review |
| Pack quality decay | Rolling 50 success rate drops > 15pp vs baseline | Deprecate pack; investigate root cause |
| Installation failure rate | > 5% of pip install attempts fail | Fix install; test on clean VMs |

---

## 3. The Problem Space

### 3.1 What Exists Today

- 12 seed packs (validated YAML frontmatter, all fields per PRD data model)
- V3 learning loop: Thompson Sampling + MutationEngine + FeedbackLoop
- `borg_observe` MCP tool (exists but conditions.py is dead code — never called)
- `borg_feedback` MCP tool (records outcomes to V3 SQLite)
- `TraceCapture` with session-level isolation
- `FailureMemory` (recall of prior failures for an error pattern)

### 3.2 What Doesn't Exist Yet

| Component | Status | Priority |
|-----------|--------|----------|
| `borg debug` CLI | Doesn't exist | P0 |
| problem_class matching in search | Doesn't exist (only keyword/embedding) | P0 |
| conditions.py wired into borg_observe | Dead code | P1 |
| `borg_feedback` CLI | Partially exists (MCP tool, not CLI) | P1 |
| MiniMax M2.7 extraction pipeline | Doesn't exist | P2 |
| A/B test infrastructure for packs | Exists in MutationEngine | P2 |
| Human review dashboard | Doesn't exist | P2 |

### 3.3 The Critical Unknown

**Do seed packs actually help?** The prior experiment (+43pp with traces) proved that investigation trails help. But that was with traces from successful agents. We haven't proven that the seed packs — written from SWE-bench data by us — produce the same benefit.

**This is why E1 (Dogfood A/B) must run before Phase 1.** If seed packs don't help, the entire pipeline is built on an untested assumption.

---

## 4. Pack Data Model

A **Pack** is a structured hypothesis: this approach works for this class of problem.

```yaml
id: uuid
version: int
status: SEED | CANDIDATE | ACTIVE | DEPRECATED

problem_signature:
  error_types: [string, ...]
  framework: string
  problem_description: string

root_cause:
  category: string  # The taxonomy class
  explanation: string  # 1-2 sentences

investigation_trail:
  - file: string
    position: FIRST | SECOND | THIRD  # The key ordering signal
    what: string
    grep_pattern: string

resolution_sequence:
  - action: string
    command: string
    why: string

anti_patterns:
  - action: string
    why_fails: string

evidence:
  success_count: int
  failure_count: int
  success_rate: float
  avg_time_to_resolve_minutes: float
  uses: int

sources:
  - type: SEED | MANUAL | AUTOMATIC
    trace_id: uuid
    created_at: timestamp
```

---

## 5. The Auto-Generation Pipeline

### 5.1 Overview

```
TRACE (from borg_feedback)
    │
    ▼
EXTRACT (MiniMax M2.7, batch nightly)
    │
    ▼
QUALIFICATION GATE
    │  HIGH → A/B (10% traffic)
    │  MEDIUM → Human review / weighted voting
    │  LOW → Discard
    ▼
CANDIDATE PACK
    │
    ▼
A/B TEST (10% candidate / 90% incumbent)
    │
    ▼
DECISION
    │  WIN → Promote to ACTIVE
    │  LOSE → Revert
    │  NEUTRAL → Keep both as ALTERNATIVES
    ▼
ACTIVE PACK
```

### 5.2 Extraction Prompt

```python
EXTRACTION_PROMPT = """
You are analyzing a successful debugging session. Convert to structured pack fields.

Error: {error_type}: {error_message}
Root cause: {root_cause}
What agent did: {what_changed}
Files examined: {files_read}
Files modified: {files_modified}

Output JSON:
- problem_class: short diagnostic category (e.g., "circular_migration", "null_pointer_chain")
- root_cause.category: the taxonomy (e.g., "circular_dependency", "null_dereference")
- root_cause.explanation: 1-2 sentence explanation
- investigation_trail: top 3 files, in order, with what to look for in each
- resolution_sequence: top 2 actions, in order, with why each works
- anti_patterns: 1-2 things that DON'T work for this problem
- confidence: HIGH if error_type + root_cause + specific files present; MEDIUM if general; LOW if vague
"""
```

### 5.3 Confidence Scoring

- **HIGH:** error_type + root_cause + ≥2 specific file paths
- **MEDIUM:** error_type + root_cause, but generic files (e.g., "migrations/*.py")
- **LOW:** vague root cause or no file information

### 5.4 A/B Test Mechanics

- 10% of matching queries get CANDIDATE pack
- 90% get best existing ACTIVE pack
- Decision rule: chi-squared, p < 0.05, minimum 20 uses per arm
- Neutral outcome (similar success rates): keep both as ALTERNATIVES

### 5.5 Decision Thresholds

| Outcome | Action |
|---------|--------|
| Candidate wins (p < 0.05, higher success rate) | Promote to ACTIVE |
| Candidate loses (p < 0.05, lower success rate) | Revert; mark root_cause as covered |
| Insufficient signal after 50 uses | Keep in CANDIDATE pool |
| Neutral (similar rates) | Keep both as ALTERNATIVES |

---

## 6. Problem Class Taxonomy

12 classes covering ~80% of debugging errors:

| problem_class | error_types | framework |
|---|---|---|
| `circular_dependency` | IntegrityError, InvalidMoveError | django |
| `null_pointer_chain` | AttributeError, TypeError (NoneType) | python |
| `missing_foreign_key` | IntegrityError, OperationalError | django |
| `migration_state_desync` | OperationalError, ProgrammingError | django |
| `import_cycle` | ImportError, ModuleNotFoundError | python |
| `race_condition` | TimeoutError, ConcurrencyError | python |
| `configuration_error` | ImproperlyConfigured, ConfigurationError | django |
| `type_mismatch` | TypeError, mypy error | python |
| `missing_dependency` | ModuleNotFoundError, ImportError | python |
| `timeout_hang` | TimeoutError, GatewayTimeout | python |
| `schema_drift` | OperationalError, SyncError | python |
| `permission_denied` | PermissionError, AccessDenied | python |

Expansion rule: new class when 5+ traces define the same unmapped root_cause.

---

## 7. Implementation Phases

### Phase 0: Seed Packs — DONE ✓ (2026-04-02)
- 12 validated packs in `skills/`
- All YAML frontmatter valid per PRD data model

### Phase 0.5: Pre-Build Validation — RUN BEFORE BUILDING

**Critical principle:** E1 experiments validate the approach before any building. If the approach doesn't work, we fix it before investing in infrastructure.

**Sequence:** E1a → E1b → E1c. Each must pass before proceeding.

#### E1a: Format Validation (Day 1)
**Question:** Does structured guidance from seed packs match what actually worked on held-out SWE-bench tasks?

**Protocol:**
```
Test harness: Python script calling borg_observe() directly (no CLI needed)
Tasks: 5 held-out SWE-bench Django Verified tasks (NOT in seed pack source data)
  → Select tasks where the patch reveals the actual fix
  → Compare: does borg_observe's investigation_trail include the files modified in the patch?

Pre-registered pass criteria (ALL must pass):
  - Investigation trail relevance: ≥ 2 of top 3 suggested files appear in actual fix
  - Resolution match: suggested resolution_sequence includes the actual fix approach
  - Root cause alignment: classified problem_class matches the actual root cause
```

**Pass:** All 3 criteria → E1a passes → proceed to E1b
**Fail:** Iterate on packs; rerun E1a

#### E1b: Real-Bug Dogfood (Days 2-3)
**Question:** Does borg guidance help on real bugs (not SWE-bench)?

**Protocol:**
```
Participants: 3 internal developers (not the borg team)
Task: Use borg_observe on a real debugging problem in their codebase
Method: Retrospective after using guidance: "Did the guidance match what actually worked?"

Pre-registered pass criteria (ALL must pass):
  - Guidance relevance: ≥ 2/3 developers say guidance was "helpful" or "very helpful"
  - Investigation trail accuracy: ≥ 2/3 times, suggested files were actually relevant
  - Resolution match: ≥ 1/3 times, a suggested resolution was the actual fix
  - Would use again: 3/3
```

**Pass:** All 4 criteria → E1b passes → proceed to E1c
**Fail:** Investigate why packs don't generalize; fix packs; rerun E1b

#### E1c: CLI Usability (Day 4)
**Question:** Can a developer use `borg debug` CLI output without training?

**Protocol:**
```
Participants: 3 from E1b + 2 new developers
Task: Install borg and use `borg debug` on a real bug
Method: Think-aloud; note confusions

Pre-registered pass criteria (ALL must pass):
  - Time to first relevant file read: < 2 minutes from CLI output
  - Correct problem_class understood: ≥ 4/5 participants
  - Would recommend: ≥ 4/5
```

**Pass:** All 3 criteria → Phase 0.5 complete → proceed to Phase 1
**Fail:** Redesign CLI output; retest

---

### Phase 1: CLI + Core Experience (Week 2-3)
**Prerequisite:** Phase 0.5 (E1a + E1b + E1c all passed)

**Deliverable:** `borg debug <error>` CLI + `borg feedback` + problem_class matching

```
Day 5-6: `borg debug <error>` CLI
  - Parse error message → extract error_type, error_message
  - Classify problem_class via taxonomy
  - Retrieve matching seed packs
  - Render: investigation_trail, resolution_sequence, anti_patterns, evidence
  - Fallback: systematic-debugging generic guidance if no match

Day 7: `borg feedback` CLI
  - "Did this help? [yes/no/maybe]"
  - Records: problem_class, pack_id, success, time_to_resolve
  - Writes to V3 SQLite outcomes table

Day 8-10: problem_class matching in BorgV3.search
  - Filter packs by problem_class before Thompson Sampling
  - Thompson Sampling ranks within matching set
  - Unknown errors fall back to keyword/embedding search
```

**Verification:**
- E3 (First-user dogfood) — run after Phase 1

### Phase 2: Intelligence Layer (Week 4-5)
**Prerequisite:** Phase 1 shipped

**Deliverable:** conditions.py wired + FailureMemory surfaced + Thompson Sampling update

```
Day 11-13: Wire conditions.py into borg_observe
  - skip_if: skip reproduce phase for deterministic errors (TypeError, ImportError)
  - inject_if: inject "trace upstream" message for NoneType errors
  - context_prompts: cross-reference error with recent git changes

Day 14-16: FailureMemory surfaced in CLI output
  - "23 agents tried X and failed. Try Y instead."
  - Anti-patterns from FailureMemory populate anti_patterns section

Day 17-18: Thompson Sampling update
  - ContextualSelector gets FeedbackLoop signals
  - Pack posteriors update from borg_feedback outcomes
```

### Phase 3: Extraction Pipeline (Week 6-7)
**Prerequisite:** Phase 2 shipped; first traces accumulated

**Deliverable:** Nightly batch extraction → CANDIDATE packs → A/B test

```
Day 19-22: Extraction pipeline
  - Batch job: SELECT * FROM traces WHERE outcome=SUCCESS AND created_at > last_run
  - MiniMax M2.7 extraction (batch, not real-time)
  - Qualification gate: HIGH → A/B, MEDIUM → voting queue, LOW → discard

Day 23-26: A/B test wiring
  - 10% traffic to CANDIDATE packs
  - MutationEngine.record_outcome() wired (was broken — now fixed)
  - Auto-resolution at p < 0.05

Day 27-28: Human review dashboard (simple)
  - List of CANDIDATE packs awaiting review
  - Approve / Reject / Edit
  - Weighted voting for MEDIUM confidence packs
```

### Phase 4: Production Hardening (Week 8)
**Prerequisite:** Phase 3 shipped

**Deliverable:** Monitoring, error handling, pip install

```
Day 29-32: Monitoring
  - Feedback capture rate dashboard
  - Thompson Sampling precision tracking
  - A/B test resolution rate
  - Alert thresholds per Section 2.3

Day 33-35: Error handling
  - Extraction failures: retry with exponential backoff
  - Malformed error messages: graceful fallback
  - Batch job: idempotent, resumable

Day 36: pip install agent-borg end-to-end test
```

---

## 8. Success Criteria Summary

| Experiment | When | Pre-registered criteria | Binding gate |
|------------|------|----------------------|------------|
| E1a: Format validation | Day 1 | 3/3 | All pass → E1b; fail → fix packs |
| E1b: Real-bug dogfood | Days 2-3 | 4/4 | All pass → E1c; fail → fix packs |
| E1c: CLI usability | Day 4 | 3/3 | All pass → Phase 1; fail → redesign CLI |
| E3: First-user dogfood | After Phase 1 | 3/3 | All pass → broaden; fail → fix onboarding |
| E4: Longitudinal cohort | 8 weeks post-launch | precision@1 slope > 0, p < 0.05 | Compounding real? |
| E5: Auto-generation audit | Monthly | 5/5 metrics for 3 months | System compounding? |

**No-go conditions (binding):**
- E1a fail → don't build extraction pipeline; fix seed packs
- E1b fail → don't build Phase 3; fix pack quality or taxonomy
- E1c fail → don't ship CLI; redesign output format
- E3 fail → don't broaden launch; fix onboarding
- E4 (Longitudinal cohort) — begins after launch, runs 8 weeks

---

## 9. Assumptions and Tradeoffs

### A: Why batch extraction (not real-time)?
Traces aren't complete when borg_feedback is called. Batch nightly is sufficient — the compounding flywheel doesn't need real-time; it needs correctness. Real-time extraction also costs more (LLM call per feedback event).

### B: Why MiniMax M2.7 for extraction (not Opus 4.6)?
Cost at scale: 1,000 traces/day × $0.01 = $10/day. MiniMax M2.7 is ~50x cheaper per token. Extraction is classification and structure extraction (not hard reasoning) — M2.7 is sufficient. Opus 4.6 reserved for: human review of ambiguous cases, complex pack authoring.

### C: Why 10% A/B traffic?
Conservative. Being wrong on 50% of traffic is expensive. At 1,000 users, 10% gives ~100 uses/day for the most common problem_class — enough to resolve A/B tests in days, not weeks.

### D: Why Thompson Sampling (not a learned ranker)?
Already implemented in ContextualSelector. Adding a learned ranker requires training data, training pipeline, and maintenance. Thompson Sampling + structured retrieval handles this use case — the problem is not complex enough to warrant a learned ranker yet.

### E: Why one pack per root_cause?
10 agents solving the same root cause should produce one canonical pack, not 10 fragmented ones. Evidence accumulates on one pack (success_rate converges faster), Thompson Sampling has more signal per pack.

---

## 10. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| E1a fails — seed packs don't help on held-out SWE-bench | Medium | High | Iterate on packs; rerun before building pipeline |
| E1b fails — seed packs don't generalize to real bugs | Medium | High | Expand taxonomy; add more problem_classes |
| E1c fails — CLI output is confusing | Medium | Medium | Redesign output format; user test again |
| Feedback loop doesn't close — nobody submits feedback | High | High | One-click feedback in CLI; measure capture rate |
| Posterior collapse — one pack dominates | Medium | Medium | ε ≥ 5% exploration budget; monitor α/β ratio |
| Cold start — new problem_class has no pack | High initially | Low | Systematic-debugging fallback; seed packs cover common cases |
| A/B tests never resolve — insufficient traffic per problem_class | Medium | Medium | Reduce min samples to 15 for low-traffic classes; merge rare classes |
| Anti-pattern inflation — packs accumulate low-quality entries | Low | Medium | Quarterly pack audit; human review for MEDIUM confidence |
| Extraction LLM produces wrong root_cause | Medium | Medium | MEDIUM confidence → human review gate; auto-revert if success_rate < 50% |

---

## 10. Verification Summary

| Experiment | When | Pre-registered criteria | Binding gate |
|------------|------|----------------------|------------|
| E1a: Format validation | Day 1 | 3/3 | All pass → E1b; fail → fix packs |
| E1b: Real-bug dogfood | Days 2-3 | 4/4 | All pass → E1c; fail → fix packs |
| E1c: CLI usability | Day 4 | 3/3 | All pass → Phase 1; fail → redesign CLI |
| E3: First-user dogfood | After Phase 1 | 3/3 | All pass → broaden; fail → fix onboarding |
| E4: Longitudinal cohort | 8 weeks post-launch | precision@1 slope > 0, p < 0.05 | Compounding real? |
| E5: Auto-generation audit | Monthly | 5/5 metrics for 3 months | System compounding? |

**No-go conditions (binding):**
- E1a fail → don't build extraction pipeline; fix seed packs
- E1b fail → don't build Phase 3; fix pack quality or taxonomy
- E1c fail → don't ship CLI; redesign output format
- E3 fail → don't broaden launch; fix onboarding

---

*This PRD is the source of truth. All experiments are pre-registered with success criteria defined before running. No post-hoc rationalization.*
