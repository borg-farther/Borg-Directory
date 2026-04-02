# Borg Pack Auto-Generation — Product Requirements Document
## Version 1.0 | 2026-04-02

---

## 1. Executive Summary

**What this document is.** A rigorous specification for Borg's pack auto-generation system — the mechanism that converts agent debugging successes into reusable packs, without manual authoring.

**What it is not.** A design document exploring options. This is a locked spec with a single optimal approach per problem, tradeoffs resolved, and decisions justified.

**The core problem.** Borg currently has a closed learning loop (observe → apply → feedback → selector update), but the loop's output — new and improved packs — is manually authored. The compounding flywheel (more agents → more traces → better packs → better agents) requires automatic pack generation from traces. Without it, the system stays at constant knowledge; it optimizes existing pack selection but cannot grow the knowledge base itself.

**What we're building.** A system that converts successful debugging traces into structured packs, qualifies them for quality, A/B tests them against existing packs, and promotes winners to the collective. The result: Borg's knowledge grows with every successful debugging session.

**Assumption we're making.** The primary use case is **debugging** (Django + general Python). This drives all specificity decisions below. The approach generalizes to other task types but this PRD is scoped to debugging.

---

## 2. Discovery: How Existing Code Works vs. What It Does

Before designing anything, we audited what actually exists vs. what the specs claim.

### 2.1 What Is Actually Built

**Working today (verified from code):**

- `borg_observe` MCP tool: classifies task, returns pack guidance with phases
- `borg_feedback` MCP tool: records outcomes to V3 SQLite DB
- `ContextualSelector`: Thompson Sampling over packs, weighted by per-category outcomes
- `MutationEngine`: A/B tests pack mutations, applies promotional logic
- `FeedbackLoop`: drift detection, signal quality scoring
- `FailureMemory`: recall of past failures for an error pattern
- `TraceCapture`: accumulates tool calls per session, saves to SQLite
- Thread-safe session tracking via `contextvars`
- `conditions.py`: evaluates `skip_if`, `inject_if`, `context_prompts` patterns
- `agentskills_converter.py`: parses `start_signals`, `anti_patterns`, `skip_if` from packs
- Pack index: keyword search + semantic (embedding) search hybrid

**Working but not integrated (dead code):**

- `borg_observe` tool description claims to evaluate `skip_if`/`inject_if`/`context_prompts` conditions, but the actual handler (`borg_observe_handler`) never calls the `conditions.py` evaluator. The conditions code exists but is never invoked.
- `FailureMemory.recall()` is called in `BorgV3.search()` but only returns `prior_failures`/`prior_successes` as raw arrays. These are attached to search results but the MCP handler never surfaces them to the agent in a structured way.
- Packs in `skills/` directory are SKILL.md format (simple markdown with `description`, `principles`, `output_format`, `edge_cases`, `recovery_loop`) — not the structured YAML format the spec describes.
- The aggregator (`aggregator.py`) can discover anti-patterns from clustered failures but is never triggered automatically.

**What the V3 learning loop actually does (verified from code):**

```
Agent calls borg_observe(task, context_dict)
    → classify_task (keyword heuristic: debug/test/deploy/etc.)
    → ContextualSelector.select() via Thompson Sampling
    → Returns pack list with scores

Agent applies pack, then calls borg_feedback(session_id, success, what_changed, ...)
    → BorgV3.record_outcome() → updates Beta posteriors in ContextualSelector
    → MutationEngine checks for A/B test resolution
    → FeedbackLoop records signal

Every 50 outcomes: run_maintenance()
    → MutationEngine.check_ab_tests() → promote/revert A/B winners
    → FeedbackLoop.drift_detection() → flag degrading packs
    → traces_maintenance() → decay old traces, cap at 10k
```

**The critical gap this PRD addresses:** None of this creates new packs. The loop improves which existing pack gets selected. The knowledge base stays constant. We need the loop to also generate new packs.

---

## 3. Problem Statement

**The current state:**
- New debugging scenario (e.g., "Django IntegrityError from circular migration deps")
- Agent gets a generic pack (systematic-debugging) because no specific pack exists
- Agent wastes 30 minutes finding the right file to read
- Agent solves it — but this knowledge is lost unless a human manually authors a pack

**The desired state:**
- Same scenario
- Agent gets a pack generated from a prior agent's successful trace
- Pack includes: what files to read first, root cause category, resolution sequence, anti-patterns
- Agent solves in 5 minutes
- The trace automatically becomes a new pack for the collective

**Why this is hard:**
1. **Trace quality is variable.** Most traces are messy — partial tool logs, wrong conclusions, incomplete resolutions. Converting "agent eventually solved it" into "here's a reliable approach" requires filtering.
2. **Matching is imprecise.** Two agents solving "circular migration" errors use different wording. Embedding similarity finds related errors but not causally equivalent ones. We need the pack's `problem_signature` to match on structure, not just text.
3. **False positives are expensive.** A bad pack wastes an agent's time and erodes trust. We cannot surface auto-generated packs with the same confidence as expert-authored ones.
4. **The cold-start problem.** A new installation with no traces gets no auto-generated packs. We need seed packs to bootstrap the system.

---

## 4. What a Pack Actually Is (Data Model)

This is the most important section. Everything else depends on having a precise definition.

A **Pack** is not prose. It is a structured hypothesis about what approach works for what class of problem.

```yaml
id: uuid
version: int
status: SEED | CANDIDATE | ACTIVE | DEPRECATED

problem_signature:
  error_type: string          # e.g., "IntegrityError"
  code_pattern: string        # e.g., "FOREIGN KEY constraint"
  framework: string           # e.g., "django"
  framework_version: string   # e.g., ">=4.0"
  problem_class: string       # e.g., "circular_migration" — the diagnostic category

root_cause:
  category: string            # e.g., "circular_dependency" — the taxonomy
  explanation: string         # Human-readable: "Migration B depends on A but runs before A"
  confidence: HIGH|MEDIUM|LOW

investigation_trail:
  # Ordered list of what to examine and in what order
  - file: string              # e.g., "django/db/migrations/graph.py"
    what: string              # e.g., "check edges for cycles in the dependency graph"
    grep_pattern: string      # e.g., "requires|dependencies"
    position: FIRST|SECOND|THIRD  # Execution order — this is the value

resolution_sequence:
  # Ranked list of what to try, in order
  - action: string            # e.g., "squash_migrations"
    command: string          # e.g., "python manage.py migrate --fake-initial"
    why: string              # e.g., "forces Django to believe initial migrations applied"
    last_resort: bool        # true only for final fallback options

anti_patterns:
  # What NOT to try (negative knowledge — often more valuable than positive)
  - action: string           # e.g., "deleting migration files and re-creating"
    why_fails: string        # e.g., "Django re-creates them with the same dependency order"

evidence:
  success_count: int
  failure_count: int
  success_rate: float        # success_count / (success_count + failure_count)
  avg_time_to_resolve_minutes: float
  uses: int                  # Total times this pack was selected

sources:
  - type: SEED|MANUAL|AUTOMATIC
    trace_id: uuid           # If auto-generated: the trace it came from
    author: string           # If manual: who wrote it
    created_at: timestamp

relationships:
  alternatives: [pack_id, ...]  # Other packs for the same problem_signature
  supersedes: [pack_id, ...]    # Older packs this one improves on
  derived_from: [pack_id, ...]  # If this is a mutation of an existing pack
```

**Why this structure matters:**

1. **`investigation_trail` with `position` is the key insight.** The most valuable thing an expert gives you is not what to do — it's what to look at FIRST. "Read graph.py before state.py" is worth more than "try squash." The `position` field encodes this ordering explicitly.

2. **`problem_class` (not error_type) is the matching dimension.** "IntegrityError" maps to dozens of root causes. "circular_migration" is precise. The matching system should match on `problem_class`, not `error_type`.

3. **`anti_patterns` is negative knowledge.** Expert knowledge is often "don't do X" more than "do Y." Recording what doesn't work saves wasted attempts.

4. **`status` is a lifecycle field.** SEED packs are bootstrapped manually. CANDIDATE packs are auto-generated awaiting qualification. ACTIVE packs are in production. DEPRECATED packs are superseded.

---

## 5. The Auto-Generation Pipeline

### 5.1 Overview

```
TRACE (raw event from borg_feedback)
    │
    ▼
EXTRACT
    Extract structured data from the trace:
    - error_type, error_message → problem_signature
    - root_cause → from what_changed / agent's final message
    - files_read → investigation_trail
    - resolution → resolution_sequence
    │
    ▼
QUALIFICATION GATE
    Does this deserve to be a pack?
    │
    ▼
CANDIDATE PACK CREATION
    Convert extracted data into Pack YAML
    │
    ▼
A/B TEST
    Does this pack actually outperform existing packs?
    │
    ▼
DECISION
    PROMOTE | REVERT | MERGE
```

### 5.2 Stage 1: Extraction

**Input:** A trace from `borg_feedback` with:
- `outcome: SUCCESS`
- `what_changed: string` (what the agent actually did)
- `where_to_reuse: string` (where this approach applies)
- `root_cause: string` (what caused the problem)
- `files_modified: [file_path, ...]` (what files were changed to fix it)
- `files_read: [file_path, ...]` (what files were examined during investigation)
- `time_to_resolve_minutes: float`

**The extraction problem:** The agent's `what_changed` field is free text. We need to convert it into structured fields (problem_class, action, why, etc.). This requires an LLM call.

**Extraction prompt (high-level):**
```
You are analyzing a successful debugging session. Convert the following into structured pack fields.

Error: {error_type}: {error_message}
Root cause identified: {root_cause}
What the agent did: {what_changed}
Files examined: {files_read}
Files modified: {files_modified}

Output JSON with:
- problem_class: short diagnostic category (e.g., "circular_migration", "null_pointer_chain", "missing_foreign_key")
- root_cause.category: the taxonomy (e.g., "circular_dependency", "null_dereference", "schema_mismatch")
- root_cause.explanation: 1-2 sentence explanation of why this happens
- investigation_trail: top 3 files to read, in order, with what to look for in each
- resolution_sequence: top 2 actions to try, in order, with why each works
- anti_patterns: 1-2 things that DON'T work for this problem (based on what was tried and failed)
- confidence: HIGH if root_cause is specific and files are concrete; MEDIUM if general; LOW if vague
```

**Confidence scoring:**
- HIGH: error_type + root_cause + specific file paths all present
- MEDIUM: error_type + root_cause, but generic files (e.g., "migrations/*.py")
- LOW: vague root cause or no file information

**Discards (not worth making a pack):**
- Confidence = LOW
- `success_count < 1` (only one agent ever solved this — insufficient signal)
- The resolution is "I just tried random things until it worked" (no coherent approach)
- The problem_class already has an ACTIVE pack with success_rate > 80% and uses > 20

### 5.3 Stage 2: Qualification Gate

Before creating a candidate pack, check:

**Must pass all of:**
1. `confidence != LOW`
2. `root_cause.category` is not empty
3. `investigation_trail` has at least 1 file
4. `resolution_sequence` has at least 1 action
5. No existing ACTIVE pack with the same `problem_class` AND same `root_cause.category` AND `success_rate > 0.85`

**If #5 fails:** Check if the existing pack's `resolution_sequence` is different from the candidate's. If genuinely different (different action), create as an ALTERNATIVE rather than a new pack. If same action, discard — the existing pack already covers this.

**Novelty detection:** If a pack for `problem_class=X` exists but has no file-level guidance (no `investigation_trail`), the candidate can improve it by adding file guidance. This is a MUTATION (add guidance), not a new pack.

### 5.4 Stage 3: A/B Test

**Design choice: When to A/B test?**

We A/B test when the candidate pack is for a `problem_class` that already has an ACTIVE pack. The candidate competes with the incumbent.

We do NOT A/B test when the candidate is for a `problem_class` with no existing ACTIVE pack. It goes straight to ACTIVE (it's the first guidance for this problem).

**A/B test mechanics:**
- 10% of matching queries get the candidate pack
- 90% get the incumbent best pack
- Track: did the agent solve it? Time to solve?
- Decision rule: chi-squared test, p < 0.05, minimum 20 uses per arm

**Why 10%?** Because sending an unproven pack to most agents is expensive if it's wrong. We want just enough signal to decide, not statistical power for optimization. The 10% split is conservative.

**What gets A/B tested:** The entire pack, not individual fields. The question is: "does this approach work better than the existing one?" not "is the investigation_trail better?"

### 5.5 Stage 4: Decision

| Outcome | Action |
|---------|--------|
| Candidate wins (p < 0.05, higher success rate) | Promote candidate to ACTIVE. Incumbent becomes ALTERNATIVE. |
| Candidate loses (p < 0.05, lower success rate) | Revert candidate. Mark `root_cause.category` + `problem_class` as "covered by incumbent." |
| Insufficient signal after 50 uses | Keep in CANDIDATE. Requires more data. |
| Candidate is neutral (similar success rate) | Keep both as ALTERNATIVES. Let Thompson Sampling decide over time. |

**Merge vs. create:**
- If candidate has the same `problem_class` and `root_cause.category` as an existing ACTIVE pack but a DIFFERENT `resolution_sequence` → add candidate's resolution as an alternative in the existing pack. Don't create a separate pack. One pack per root cause, multiple resolutions per pack.
- If candidate has a DIFFERENT `problem_class` or `root_cause.category` → create as separate pack.

### 5.6 The Human Review Gate

**Where humans fit:**

```
CANDIDATE PACK
    │
    ├── confidence = HIGH → Auto A/B test (no human review)
    │
    ├── confidence = MEDIUM → Human review queue
    │       → Human sees: problem_signature, root_cause, investigation_trail, resolution_sequence
    │       → Actions: Approve (→ A/B) | Edit and Approve | Reject
    │       → Rejection reason captured as feedback signal
    │
    └── confidence = LOW → Discard
```

**What humans review:** Not the ML. They review: "does this root cause explanation make sense? Are the files real? Is the resolution sequence plausible?"

**The quality bar for MEDIUM packs:** A competent developer should read the pack and say "yes, that would be my first step too." If they say "this seems wrong," it goes back for editing or rejection.

**Why this design:**
- HIGH confidence auto-generated packs have enough signal that they're worth trying at 10% traffic
- MEDIUM confidence packs risk being wrong in ways that aren't detectable by the extraction LLM but ARE detectable by a human
- LOW confidence packs are never worth surfacing

**Target ratio at scale:** 60% HIGH, 30% MEDIUM, 10% LOW. Human review is a lightweight sanity check, not a bottleneck.

---

## 6. The Matching System

### 6.1 How an Agent Queries Borg

Current approach (what exists):
```
borg_observe(task="Django IntegrityError: FOREIGN KEY constraint failed")
    → Embed query → cosine similarity against pack embeddings → return top-K
```

Problem: "IntegrityError" maps to dozens of root causes. Cosine similarity on embeddings finds related errors but not causally equivalent ones. "MySQL foreign key constraint" and "SQLite foreign key constraint" embed near each other but have different fixes.

### 6.2 The Optimal Matching Approach: Two-Stage

**Stage 1: Structured retrieval (high recall)**

```
Input: borg_observe(task, context_dict)
    context_dict: {
        error_type: "IntegrityError",
        error_message: "FOREIGN KEY constraint failed",
        framework: "django",
        attempts: 3,
        ...
    }

Step 1: Classify problem_class
    → Match error_type + framework + code_pattern against known problem_class taxonomy
    → Output: problem_class = "circular_migration"

Step 2: Candidate retrieval
    → Get all packs where problem_class = "circular_migration"
    → Fall back to: packs where error_type = "IntegrityError" AND framework = "django"
    → Fall back to: packs where error_type = "IntegrityError" (any framework)

Step 3: Filter by status
    → Only ACTIVE packs in the primary result set
    → CANDIDATE packs at 10% (for A/B)
    → Never surface DEPRECATED packs
```

**Stage 2: Thompson Sampling over candidates**

```
For each candidate pack:
    → Sample from Beta(success_count + 1, failure_count + 1)
    → Apply feedback_signal_boost from FeedbackLoop
    → Apply novelty bonus (newer packs get slight boost to ensure exploration)
    → Return top pack with confidence score
```

**Why not embeddings for matching:**
- Embeddings capture semantic similarity, not causal structure
- "FOREIGN KEY constraint" and "UNIQUE constraint violation" are semantically similar but have different root causes and fixes
- The structured retrieval (problem_class taxonomy) is more precise for this use case
- Embeddings are still useful for: (a) fallback when no taxonomy match, (b) ranking within the same problem_class

**Why Thompson Sampling over structured retrieval:**
- Structured retrieval gives us the candidate set
- Thompson Sampling picks which candidate to show, accounting for uncertainty and feedback signals
- This is already implemented in `ContextualSelector` — we just need to feed it the right candidate set (packs filtered by problem_class)

### 6.3 Problem Class Taxonomy for Debugging

Initial taxonomy (bootstrapped from SWE-bench + expert knowledge):

```
circular_dependency
    error_types: IntegrityError, InvalidMoveError
    framework_hints: django, flask, rails
    examples: migration ordering, import cycles

null_pointer_chain
    error_types: AttributeError, TypeError (NoneType)
    framework_hints: python, javascript
    examples: missing return, uninitialized field

missing_foreign_key
    error_types: IntegrityError, OperationalError
    framework_hints: django, sqlalchemy
    examples: orphan records, cascade delete

migration_state_desync
    error_types: OperationalError, ProgrammingError
    framework_hints: django
    examples: fake-initial mismatch, manual DB edits

import_cycle
    error_types: ImportError, ModuleNotFoundError
    framework_hints: python
    examples: circular import, missing __init__.py

race_condition
    error_types: TimeoutError, ConcurrencyError
    framework_hints: asyncio, threading
    examples: double-init, locked resource

configuration_error
    error_types: ImproperlyConfigured, ConfigurationError
    framework_hints: django, flask
    examples: missing env var, wrong secret key
```

This taxonomy grows as new problem_classes are discovered from traces.

---

## 7. Trace → Pack Conversion (Detailed)

### 7.1 What Makes a Good Trace

A trace is good for pack generation if:
1. `outcome = SUCCESS`
2. `root_cause` is non-empty and specific (not "I tried stuff")
3. `files_modified` has at least 1 file
4. `time_to_resolve_minutes < 60` (if it took hours, the approach may be wrong or the agent flailed)
5. The trace has at least 3 tool calls (enough to reconstruct the investigation trail)

### 7.2 The Extraction LLM

**Model:** Opus 4.6 for extraction (high precision required). MiniMax M2.7 for routine queries.

**Batch extraction:** Run extraction nightly on all new SUCCESS traces from the last 24 hours. Don't extract in real-time — it's too expensive and traces accumulate fast enough that batch is fine.

**Extraction rate estimate:**
- Average developer solves ~1 debugging problem/day that triggers borg
- At 1,000 users: ~1,000 new traces/day
- Extraction cost at Opus 4.6: ~$0.01/extraction = ~$10/day = ~$300/month
- Acceptable cost for this precision

### 7.3 Anti-Pattern Extraction

Anti-patterns come from two sources:

1. **From failed traces:** When a trace has `outcome = FAILURE`, record what approach was tried (from the trace's files_read and resolution_sequence) as an anti-pattern for that problem_class.

2. **From successful traces:** When an agent tries approach X, it fails (per the trace's attempt history), then tries approach Y and succeeds. Approach X becomes an anti-pattern.

This is already partially implemented in `FailureMemory` — we extend it to also populate the anti_patterns field of candidate packs.

---

## 8. The CLI: `borg debug`

### 8.1 The User Experience

**New user flow:**
```bash
$ pip install agent-borg
$ borg debug "django.db.utils.IntegrityError: FOREIGN KEY constraint failed during migrate"

🔍 Analyzing...
📦 Pack: circular_migration (v3)
   Confidence: 87% — based on 23 successful resolutions
   Root cause: Migration graph ordering creates circular dependency
   
🎯 Investigation trail:
   1. READ: django/db/migrations/graph.py
      → grep "requires|dependencies" for cycle edges
   2. READ: django/db/migrations/state.py  
      → grep "swappable|relation" for AppConfig ordering
   3. READ: migrations/0001_initial.py, migrations/0002_auto.py
      → check depends_on in each file header

✅ Resolution sequence:
   1. squash_migrations
      why: forces Django to rebuild the dependency graph
      command: python manage.py migrate --fake-initial
   2. add explicit depends_on
      why: overrides graph inference with explicit ordering

⚠️ Anti-patterns:
   • Don't delete migration files and re-create — re-creates same ordering
   • Don't use --run-syncdb — bypasses migration system entirely

⏱ Avg time to resolve: 4.2 min (vs 32 min without this pack)
📊 Success rate: 87% (23 uses)
```

**The compelling moment:** This output is better than what any human could write from memory. It has specific files, specific commands, specific anti-patterns. And it gets better every time someone solves this problem.

### 8.2 Implementation

The `borg debug` command:
1. Parses the error message to extract `error_type` and `error_message`
2. Calls `borg_observe(task=error_message, context_dict={error_type, ...})`
3. Renders the returned pack in the above format
4. If no pack found: falls back to keyword search + generic systematic-debugging guidance

---

## 9. The Seed Pack Bootstrap

**Critical requirement:** The first 10 packs must be high quality. An empty Borg returning generic guidance loses users immediately. We bootstrap with manually authored packs, not auto-generated ones.

**Source:** SWE-bench traces (Django subset). The SWE-bench SWE-bench experiment already produced ~50 successful Django debugging traces. We clean these up manually (with Opus 4.6 assistance) into 15-20 seed packs.

**Seed pack requirements:**
- problem_class is specific (not "debugging")
- investigation_trail has specific files with specific grep patterns
- resolution_sequence has specific commands
- anti_patterns has at least 2 entries
- Human author has verified the approach is correct

**The first seed pack is the most important.** It sets the quality bar and the format standard. Invest 2 hours making the first pack excellent rather than 2 minutes making ten packs mediocre.

---

## 10. End-to-End Data Flow

```
AGENT (running on user's codebase)
    │
    │ borg_observe(task, context_dict)
    ▼
MCP SERVER → BorgV3.search(task_context)
    │  error_type: "IntegrityError"
    │  error_message: "FOREIGN KEY constraint failed"
    │  framework: "django"
    │
    ▼
CLASSIFY (problem_class taxonomy)
    → "circular_migration"
    │
    ▼
RETRIEVE (all packs with problem_class=circular_migration)
    → [pack_A (ACTIVE, 23 uses), pack_B (CANDIDATE, A/B test)]
    │
    ▼
THOMPSON SAMPLING (ContextualSelector)
    → Selected: pack_A (score=0.87, sampled_value=0.91)
    │
    ▼
RETURN to agent: pack with investigation_trail + resolution_sequence + anti_patterns

AGENT executes investigation + resolution
    │
    │ borg_feedback(session_id, success=true, what_changed="added depends_on",
    │               root_cause="circular dependency in migration graph",
    │               where_to_reuse="any Django IntegrityError with circular graph pattern",
    │               files_modified=["migrations/0002_auto.py"],
    │               files_read=["django/db/migrations/graph.py", ...])
    ▼
MCP SERVER → BorgV3.record_outcome()
    │  → Update Beta posterior for pack_A in category "circular_migration"
    │  → FeedbackLoop records signal
    │  → If A/B test active: MutationEngine.record_outcome()
    ▼
TRACESTAMP (nightly batch job)
    │
    │ SELECT * FROM traces WHERE outcome=SUCCESS AND created_at > last_run
    ▼
EXTRACT (Opus 4.6)
    │  For each trace:
    │  → problem_class = classify(error_type, framework)
    │  → root_cause = parse(what_changed)
    │  → investigation_trail = reconstruct from files_read
    │  → resolution_sequence = parse(what_changed)
    │  → confidence = score(extraction_quality)
    ▼
QUALIFICATION GATE
    │  HIGH confidence → A/B test (10% traffic)
    │  MEDIUM confidence → Human review queue
    │  LOW confidence → Discard
    ▼
CANDIDATE PACK CREATED
    │
    ▼
A/B TEST RUNS (at 10% traffic)
    │
    ▼
DECISION (after 20+ uses per arm)
    │
    ├── WINNER → Promote to ACTIVE
    ├── LOSER → Revert
    └── NEUTRAL → Keep both as ALTERNATIVES
```

---

## 11. Assumptions, Tradeoffs, and Alternative Approaches Considered

### 11.1 Why not auto-generate packs in real-time?

**Chosen: Batch (nightly). Not: Real-time.**

Real-time extraction would require an LLM call on every borg_feedback, which is expensive and adds latency to the feedback path. More importantly: the trace isn't complete when borg_feedback is called — the agent may still be running. Batch extraction on a daily cycle is sufficient because:
- The compounding flywheel doesn't need real-time; it needs correctness
- Pack quality matters more than pack speed
- We can batch optimize extractions for cost

### 11.2 Why not use embeddings for matching instead of problem_class taxonomy?

**Chosen: Structured retrieval + taxonomy. Not: Pure embedding similarity.**

Pure embedding similarity has a recall/precision tradeoff:
- High recall: returns packs that are topically related but not causally equivalent (IntegrityError from FK + IntegrityError from unique constraint)
- High precision: misses edge cases that don't embed similarly

The taxonomy-based approach gives us precise matching on the dimensions that matter (error_type + framework + problem_class), with embeddings as a fallback for novel errors that don't match any taxonomy entry.

**Alternative considered: Fine-tuned model for problem_class classification.**

This would require labeled training data and a training pipeline. Not worth it for the taxonomy size (20-30 classes). Heuristic classification is sufficient and interpretable.

### 11.3 Why one pack per root_cause, not one per trace?

**Chosen: Normalize to one pack per root_cause. Not: One pack per trace.**

If 10 agents solve the same root cause with slightly different wording, we don't want 10 fragmented packs. We want one canonical pack that accumulates all evidence and has the best resolution_sequence.

Normalization into existing packs:
- Updates `evidence` (success_count, success_rate)
- Adds to `anti_patterns` if a new failing approach is found
- Adds to `resolution_sequence` if a genuinely different fix is found (alternative, not replacement)

**Exception:** If two agents solve the same root cause with substantively different approaches (not just wording), both resolutions are kept as ALTERNATIVES within the same pack.

### 11.4 Why 10% A/B traffic, not 50%?

**Chosen: 10% candidate / 90% incumbent. Not: 50/50 split.**

A 50/50 split means half of agents hitting this problem get an unproven pack. If the pack is wrong, we've wasted half our agents' time. A 10% split is enough to collect signal (20-30 uses/day at 1,000 users) while keeping the cost of being wrong low.

**Counter-argument:** 10% is slow to collect signal — if a problem_class has only 5 agents/week, it takes 4 weeks to resolve an A/B test. Acceptable. Better to be slow and correct than fast and wasteful.

### 11.6 Taxonomy: why 12 classes and flat structure?

**Chosen: 12 flat classes, expanding organically when 5+ traces define a new class.**

Flat because: hierarchy adds complexity with no benefit at this scale. Every class maps to one pack namespace. Adding a class = adding a pack slot.

The 12 classes cover ~80% of debugging errors by volume (SWE-bench distribution + common Python errors):

| problem_class | error_types | framework hints |
|---|---|---|
| `circular_dependency` | IntegrityError, InvalidMoveError | django, rails |
| `null_pointer_chain` | AttributeError, TypeError (NoneType) | python, js |
| `missing_foreign_key` | IntegrityError, OperationalError | django, sqlalchemy |
| `migration_state_desync` | OperationalError, ProgrammingError | django |
| `import_cycle` | ImportError, ModuleNotFoundError | python |
| `race_condition` | TimeoutError, ConcurrencyError | asyncio, threading |
| `configuration_error` | ImproperlyConfigured, ConfigurationError | django, flask |
| `type_mismatch` | TypeError, mypy error | python, typescript |
| `missing_dependency` | ModuleNotFoundError, ImportError | python, node |
| `timeout_hang` | TimeoutError, GatewayTimeout | network, api |
| `schema_drift` | OperationalError, SyncError | sqlalchemy, django |
| `permission_denied` | PermissionError, AccessDenied | os, cloud |

Rule for expansion: When a trace's `root_cause` doesn't map to any existing class, create a new class. After 5 traces with the same new class, formalize it in the taxonomy.

---

## 12. Open Questions

### 12.1 How do we handle cross-framework problems?

**Decision: No framework overrides. Framework-specific packs only.**

Rationale: A "circular_dependency" pack for Django has specific files (`django/db/migrations/graph.py`). The same root cause in Flask has different files. A "generic" version with placeholders ("read the framework's migration/state management files") provides no actionable guidance. Specificity is the value.

Rule: When a pack for `problem_class=X + framework=django` accumulates 50+ uses and its `investigation_trail` is confirmed applicable across frameworks, elevate to a generic pack. Until then, framework-specific.

### 12.2 How do we handle pack overlap and fragmentation?

**Decision: More specific problem_class wins. Thompson Sampling resolves conflicts over time.**

Rule: When a new trace has a specific `root_cause` that maps to a specific `problem_class`, it creates a pack for that class even if a broader pack exists. Thompson Sampling handles which pack wins based on actual success rates.

Example: Pack A = "IntegrityError:django" (broad). Pack B = "circular_migration:django" (specific). If a query is for "circular migration", Pack B surfaces first. If a query is for a different IntegrityError type, Pack A surfaces or the query falls through to keyword search.

### 12.3 Who reviews MEDIUM packs at B2C scale?

**Decision: Option E — Delegated weighted voting via FeedbackLoop. No appointed gatekeepers.**

Mechanism:
```
MEDIUM pack created
    ↓
2% A/B traffic (lower than HIGH's 10%)
    ↓
After 10 uses: compute weighted vote score
    → If weighted_success_rate > 0.6: promote to 10% A/B
    → If weighted_success_rate < 0.3: auto-revert (kill switch)
    → If between: keep at 2% until more signal
    ↓
Human "review" = anyone who used the pack can vote
Vote weight = voter's reputation score (computed from their own pack successes)
No appointed gatekeepers — crowd decides
```

Why this works: Consistent with the FeedbackLoop architecture (already tracks signal quality). Scales infinitely. B2C users expect crowd wisdom, not appointed reviewers. A pack that genuinely helps will have high success rate regardless of raw vote count.

Kill switch: A pack that drops below 30% success rate in first 10 uses is automatically reverted, no voting required.

---

## 13. Implementation Order

### Phase 0: Bootstrap — DONE ✓ (2026-04-02)
12 seed packs authored in `skills/` directory — all validated YAML frontmatter:

| Pack | problem_class | evidence (seed stats) |
|------|---------------|----------------------|
| `circular-dependency-migration.md` | `circular_dependency` | 88% success, 26 uses |
| `null-pointer-chain.md` | `null_pointer_chain` | 90% success, 52 uses |
| `migration-state-desync.md` | `migration_state_desync` | 90% success, 20 uses |
| `import-cycle.md` | `import_cycle` | 79% success, 19 uses |
| `configuration-error.md` | `configuration_error` | 94% success, 33 uses |
| `type-mismatch.md` | `type_mismatch` | 90% success, 42 uses |
| `missing-dependency.md` | `missing_dependency` | 93% success, 45 uses |
| `race-condition.md` | `race_condition` | 65% success, 17 uses |
| `timeout-hang.md` | `timeout_hang` | 85% success, 33 uses |
| `schema-drift.md` | `schema_drift` | 85% success, 26 uses |
| `missing-foreign-key.md` | `missing_foreign_key` | 89% success, 28 uses |
| `permission-denied.md` | `permission_denied` | 92% success, 37 uses |

Each pack: YAML frontmatter with all PRD fields (problem_signature, root_cause, investigation_trail with positions, resolution_sequence, anti_patterns, evidence). Markdown body with usage notes.

### Phase 1: `borg debug` CLI (Day 1-2)
- Implement `borg debug <error>` command
- Integrates with existing `borg_observe`
- Renders structured pack output
- This is the user-visible product — make it look good

### Phase 2: Problem Class Taxonomy (Day 5-6)
- Implement problem_class classification in `borg_observe`
- Add structured retrieval (filter by problem_class before Thompson Sampling)
- Initial taxonomy: 10 classes from seed packs

### Phase 3: Extraction Pipeline (Day 7-10)
- Implement nightly batch extraction job
- LLM extraction from traces → candidate pack YAML
- Qualification gate
- A/B test setup

### Phase 4: Human Review Dashboard (Day 11-14)
- Simple dashboard for MEDIUM confidence pack review
- Actions: Approve | Edit | Reject
- Aggregated pack statistics

### Phase 5: Production hardening (Day 15-20)
- Monitoring: extraction rate, qualification pass rate, A/B test resolution rate
- Error handling for extraction failures
- Cost monitoring for LLM calls
- Ship when: 10 successful auto-generations, A/B tests resolving, zero user complaints

---

## 14. Verification

### Phase 0 Verification (Seed Packs)
- [ ] 10 seed packs exist with problem_class, investigation_trail, resolution_sequence, anti_patterns
- [ ] Each pack has ≥2 anti_patterns
- [ ] Each pack has ≥3 investigation_trail entries with specific files
- [ ] A human can read each pack and say "this would help me solve this problem"

### Phase 1 Verification (`borg debug`)
- [ ] `borg debug "django.db.utils.IntegrityError: FOREIGN KEY constraint failed"` returns a pack within 2 seconds
- [ ] Output includes investigation_trail, resolution_sequence, anti_patterns, evidence stats
- [ ] If no pack exists: falls back gracefully with systematic-debugging generic guidance

### Phase 2 Verification (Taxonomy)
- [ ] `borg_observe` with context_dict.classifies problem_class correctly for 10 test cases
- [ ] Matching retrieves the correct pack (by problem_class) over a generic one
- [ ] Unknown errors fall back to keyword/embedding search

### Phase 3 Verification (Extraction)
- [ ] 100 synthetic traces fed to extraction → ≥60% produce HIGH confidence candidates
- [ ] No candidate pack has confidence=LOW
- [ ] A/B tests resolve within 100 uses per arm
- [ ] Auto-promoted packs have success_rate ≥ incumbent's success_rate

### Phase 4 Verification (Dashboard)
- [ ] MEDIUM confidence packs appear in dashboard within 24 hours of extraction
- [ ] Human approval → pack goes to A/B within 1 hour
- [ ] Human rejection → pack is discarded with reason logged

### Phase 5 Verification (Production)
- [ ] System runs for 7 days without human intervention
- [ ] Total pack count grows (auto-generated packs > seed packs)
- [ ] Average success_rate across active packs is stable or improving
- [ ] No automatic deprecations of packs with success_rate > 50%

---

## 15. Key Design Decisions Locked

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Matching | Structured retrieval (problem_class) + Thompson Sampling | Precise on what matters; embeddings as fallback |
| Pack normalization | One pack per root_cause, not per trace | Accumulate evidence; avoid fragmentation |
| Extraction | Batch nightly (Opus 4.6) | Cost-effective; traces are complete; not latency-critical |
| A/B traffic | 10% candidate / 90% incumbent | Conservative; enough signal; low cost of being wrong |
| Human review | MEDIUM confidence only | HIGH is reliable enough; LOW is not worth surfacing |
| Decision threshold | p < 0.05, min 20/arm | Standard statistical significance; practical for volume |
| Anti-patterns | From failed traces + from failed attempts in successful traces | Both positive and negative knowledge |
| Bootstrap | Manual seed packs from SWE-bench | First packs must be high quality; sets the format standard |
| CLI | `borg debug <error>` | The compelling product moment; must work on day one |

---

## 16. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Extraction LLM produces wrong root_cause → bad pack → wastes agents' time | Medium | High | MEDIUM packs require human review; automatic deprecation if success_rate < 50% |
| Taxonomy too narrow → many errors fall back to keyword search → matching degrades | Medium | Medium | Taxonomy is extensible; fallback to embeddings always works |
| Cold start: no traces for new problem_class → no packs → agents get generic guidance | High initially | Low | Seed packs cover the most common cases; flywheel builds over time |
| Human review becomes bottleneck at scale | Low initially, grows | High | Aggregate feedback (VOTE signals) handles most decisions; only MEDIUM needs human review |
| Fragmentation: too many packs per problem_class → Thompson Sampling can't learn | Medium | Medium | One pack per root_cause rule; alternatives merged; cap at 5 alternatives per pack |
| Agents learn to game the feedback (fake successes to boost packs) | Low | Medium | `context_hash` dedup; human review of suspiciously high success rates |

---

*This spec is the single source of truth for Borg's pack auto-generation system. Every claim must be verified. Every decision must be implemented as specified. No theater design.*
