# R001 — Collective Prompt Intelligence: Design Document

**Project:** agent-borg  
**Spec:** R001 — Collective Prompt Intelligence ("the Borg")  
**Goal:** When one agent solves a problem, all connected agents benefit automatically.  
**Status:** Design — not yet implemented  
**Last Updated:** 2026-03-29

---

## 1. Overview

The Collective Prompt Intelligence system is the core R001 moonshot for agent-borg. It transforms the current manual pack economy into a living collective intelligence where successful problem-solving approaches are automatically captured, generalized, and propagated to all connected agents in near-real-time.

### 1.1 Current State vs. Vision

| Aspect | Today (Manual) | Vision (Automatic) |
|--------|---------------|-------------------|
| Pack creation | Human authors write SKILL.md | Agents auto-generate packs |
| Pattern discovery | Manual review of feedback | Continuous extraction from agent sessions |
| Propagation | Pack publish/pull workflow | Real-time insight broadcast |
| Quality control | Proof gates + manual review | Multi-layered quality scoring |
| Privacy | privacy_redact on logs | Differential privacy + PII guardrails |

### 1.2 High-Level Data Flow

```
Agent Session (task, phases, evidence)
       │
       ▼
┌─────────────────────────────────┐
│  OBSERVATION CAPTURE LAYER     │  ← hooks into apply.py session events
│  on_phase_complete()            │
│  on_session_complete()          │
└───────────────┬─────────────────┘
                │ sanitized, structured observation
                ▼
┌─────────────────────────────────┐
│  EXTRACTION & GENERALIZATION   │  ← CPI Core Engine
│  extract_patterns()             │
│  generalize_to_template()        │
│  score_quality()               │
└───────────────┬─────────────────┘
                │ scored, generalized insight
                ▼
┌─────────────────────────────────┐
│  QUALITY GATING                 │  ← proof_gates.py + new CPI gates
│  privacy_check()                │
│  toxicity_check()               │
│  quality_score >= threshold      │
└───────────────┬─────────────────┘
                │ approved insight
                ▼
┌─────────────────────────────────┐
│  PROPAGATION LAYER              │  ← insight store + broadcast
│  broadcast_to_agents()          │
│  update_collective_index()      │
└───────────────┬─────────────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐  ┌─────────────────┐
│ Agent A      │  │ Agent B         │
│ (learned     │  │ (discovers new  │
│  new pattern)│  │  insight via    │
└─────────────┘  │  borg_search)    │
                 └─────────────────┘
```

---

## 2. Architecture

### 2.1 Module Structure

```
borg/
  core/
    collective/              # NEW: Collective Prompt Intelligence
      __init__.py
      observer.py            # Observation capture (hooks into session events)
      extractor.py           # Pattern extraction & generalization
      quality_gates.py       # Quality scoring & gating
      propagation.py         # Broadcast & subscription
      insight_store.py       # SQLite-backed insight storage
      types.py               # Observation, Insight, Pattern type definitions
      config.py              # CPI configuration constants
    search.py                # [EXISTING] borg_search — extended for CPI
    apply.py                 # [EXISTING] — hooks added for observation capture
    session.py               # [EXISTING] — events augmented for CPI
    safety.py                # [EXISTING] — reused for CPI safety gates
    privacy.py               # [EXISTING] — privacy_redact reused
    proof_gates.py           # [EXISTING] — extended with CPI tier
```

### 2.2 Core Types (types.py)

```python
# ============================================================================
# Observation — raw, unprocessed record from an agent session
# ============================================================================

@dataclass
class Observation:
    session_id: str
    agent_id: str              # anonymized — hash of agent identity
    pack_id: str               # workflow pack used (if any)
    task_description: str      # original task (privacy-scanned)
    problem_class: str         # e.g., "debugging", "code-review"
    phase_results: List[PhaseResult]
    outcome: str               # "success" | "partial" | "failure"
    duration_seconds: int
    timestamp: str             # ISO UTC
    execution_log_hash: str   # SHA-256 of execution JSONL
    observations_source: str   # "apply-session" | "manual-submission"


@dataclass
class PhaseResult:
    phase_name: str
    status: str                # "passed" | "failed" | "skipped"
    evidence: str              # what the agent said/did (privacy-redacted)
    attempts: int
    anti_patterns_triggered: List[str]


# ============================================================================
# ExtractedPattern — generalization from one or more observations
# ============================================================================

@dataclass
class ExtractedPattern:
    pattern_id: str            # sha256 of normalized content
    problem_class: str
    trigger_context: str      # when to apply this pattern
    insight_text: str         # the actionable insight (e.g., "adding 'think step by step' improves code review")
    trigger_phrase: str       # natural language trigger for search
    phase_target: str          # which phase this applies to
    confidence: str            # "emerging" | "probable" | "confirmed"
    supporting_observations: List[str]  # observation_ids
    agent_count: int           # number of distinct agents supporting this
    first_seen: str
    last_updated: str


# ============================================================================
# Insight — a quality-gated, propagation-ready unit
# ============================================================================

@dataclass
class Insight:
    insight_id: str            # unique, stable ID
    pattern: ExtractedPattern
    quality_score: float       # 0.0–1.0
    quality_tier: str           # "EXPERIMENTAL" | "PROBABLE" | "CONFIRMED"
    privacy_flags: List[str]   # any PII categories detected (even if redacted)
    toxicity_flags: List[str]  # any problematic patterns detected
    propagation_tags: List[str] # for targeted propagation (e.g., ["python", "debugging"])
    adoption_count: int        # agents that have applied this insight
    decay_ttl_days: int
    created_at: str
    expires_at: str
    approved: bool             # passed all quality gates
    rejection_reason: Optional[str]
```

---

## 3. Component Design

### 3.1 Observation Capture Layer (observer.py)

**Responsibility:** Intercept agent session lifecycle events and emit structured, privacy-sanitized Observations.

**Integration Points:**

1. **apply.py `action_complete()`** — after session completes, the existing `_generate_feedback()` call is supplemented with a call to `observer.on_session_complete(session)`. The observation is emitted asynchronously (non-blocking) so it does not slow down the apply flow.

2. **apply.py `action_checkpoint()`** — after each phase checkpoint, `observer.on_phase_complete(session_id, phase_result)` is called to capture per-phase learnings. This feeds the pattern extractor even when a session ultimately fails.

3. **hermes-plugin lifecycle hooks** — `on_task_start_hook` and `on_consecutive_failure_hook` emit lightweight observations for context classification.

**Key Functions:**

```python
def on_session_complete(session: dict) -> None:
    """Called by apply.py action_complete after generating feedback.
    Emits a session-level observation to the observation queue."""

def on_phase_complete(session_id: str, phase_result: PhaseResult) -> None:
    """Called after each phase checkpoint. Emits phase-level observation."""

def on_task_start(task_description: str, agent_id: str) -> Observation:
    """Called by hermes-plugin on_task_start_hook. Captures task context."""

def capture_observation(obs: Observation) -> str:
    """Queue an observation for async processing.
    Returns observation_id for tracking.
    Privacy: all text fields are privacy_redact()'d before storage."""

def flush_observations() -> List[str]:
    """Process all queued observations through extraction.
    Returns list of insight_ids that were produced (if any)."""
```

**Privacy at Capture:**
- `privacy_redact()` from `borg.core.privacy` is applied to all text fields at capture time
- `agent_id` is a one-way hash — the original identity is never stored
- `execution_log_hash` provides provenance without storing the full log
- Task descriptions are scanned with `privacy_scan_text()` and any findings are flagged but not stored

**What is NOT captured:**
- User identity, project names, file paths outside the session context
- API keys, tokens, secrets (caught by credential patterns in privacy.py)
- The raw execution log (only the hash is stored)

---

### 3.2 Pattern Extraction & Generalization (extractor.py)

**Responsibility:** Transform Observations into generalized ExtractedPatterns that are actionable across multiple agents.

**Algorithm: Insight Generalization Pipeline**

```python
def extract_patterns(observations: List[Observation]) -> List[ExtractedPattern]:
    """Multi-stage pipeline:
    
    Stage 1: Group by problem_class + outcome
        → cluster observations sharing same problem_class and outcome
        → minimum 2 observations required to generalize
    
    Stage 2: Extract common elements
        → For each cluster, identify repeated phrase patterns in evidence
        → Extract shared phase success/failure sequences
        → Identify common anti_patterns_triggered
    
    Stage 3: Generate trigger phrase
        → Build a natural-language trigger using the task description pattern
        → e.g., "adding 'think step by step' improves code review"
        → Stored as trigger_phrase for borg_search integration
    
    Stage 4: Compute confidence
        → "emerging": 1 observation OR single agent
        → "probable": 2-4 observations OR 2+ agents  
        → "confirmed": 5+ observations AND 3+ agents
    """
```

**Trigger Phrase Generation:**
The trigger phrase is a short (≤150 char) natural-language statement of the discovered improvement. Example patterns:

| Evidence Pattern | Generated Trigger |
|-----------------|-------------------|
| Agent added "think step by step" in code review | "Adding 'think step by step' improves code review thoroughness" |
| Agent used systematic-diagnose before fixing | "Running systematic-diagnose before fixing reduces re-work" |
| Breaking down complex PR into checkpoints reduced failures | "Breaking complex PRs into smaller checkpoints prevents review fatigue" |

**Generalization Safety:**
- Only patterns with confidence ≥ "probable" are eligible for propagation
- Patterns are checked against anti_patterns in safety.py before propagation
- Toxicity check runs before any pattern leaves the extractor

**Pattern Normalization:**
Before generating the pattern_id, the insight_text is normalized:
- Lowercased, punctuation removed
- Whitespace collapsed to single spaces
- Equivalent phrases (e.g., "step by step" ≈ "step-by-step") are canonicalized
- This ensures the same insight discovered independently produces the same pattern_id

---

### 3.3 Quality Gating (quality_gates.py)

**Responsibility:** Ensure only high-quality, safe, privacy-preserving insights propagate. This layer exists between extraction and propagation.

**Multi-Layer Quality Model:**

```python
def score_insight(insight: Insight) -> QualityScore:
    """Composite quality score (0.0–1.0) based on:
    
    signal_strength (0.0–0.35):
        - observation_count: more observations = higher score
        - agent_diversity: more distinct agents = higher score
        - cross_problem_transfer: did it help in different problem_classes?
    
    provenance_quality (0.0–0.30):
        - derived from proof_gates.py confidence ladder
        - validated evidence carries most weight
        - session outcome (success > partial > failure for positive insights)
    
    decay_freshness (0.0–0.15):
        - newer observations score higher
        - TTL-based: decay starts at half-life of 30 days
    
    privacy_cleanliness (0.0–0.20):
        - no PII flags = full score
        - any PII flag = 0.0 (rejected before scoring)
        - only after successful privacy_check() proceeds
    
    Quality Tiers:
        EXPERIMENTAL: 0.0–0.39 — not propagated, stored for learning
        PROBABLE:     0.40–0.69 — propagated to same problem_class
        CONFIRMED:    0.70–1.0  — propagated broadly with elevated priority
    """
```

**Privacy Gate:**

```python
def privacy_check(insight: Insight) -> Tuple[bool, List[str]]:
    """Pre-propagation privacy validation.
    
    Checks:
    1. All insight text fields against _PRIVACY_PATTERNS
    2. No PII flags present (any flag = automatic rejection)
    3. Trigger phrase is free of task-specific context
    
    Returns: (passed, list_of_flags)
    """
```

**Toxicity Gate:**

```python
def toxicity_check(insight: Insight) -> Tuple[bool, List[str]]:
    """Check for problematic patterns before propagation.
    
    Uses existing _INJECTION_PATTERNS from safety.py
    Plus CPI-specific checks:
    - Hallucination indicators: "always", "never", "guaranteed"
    - Overconfidence markers: score = 1.0, certainty language
    - Manipulation signals: "you must", "always do this"
    
    Returns: (passed, list_of_flags)
    """
```

**Anti-entropy Gate:**

```python
def anti_entropy_check(insight: Insight) -> Tuple[bool, str]:
    """Prevent garbage/proliferation attacks.
    
    Checks:
    1. Minimum useful content: trigger_phrase must be ≥ 10 chars
    2. Maximum frequency: no more than 3 insights per (agent_id, problem_class, day)
       → excess insights are queued for batch review, not auto-propagated
    3. Duplicate detection: pattern_id must be unique
       → if duplicate found, increment supporting_observations, don't create new
    4. Content diversity: new insight must differ by ≥ 40 chars from existing
       → too-similar insights are merged rather than duplicated
    """
```

---

### 3.4 Propagation Layer (propagation.py)

**Responsibility:** Get approved insights to the agents that need them, using the existing borg_search infrastructure.

**Propagation Mechanisms:**

```python
# Mechanism 1: Proactive Suggestion (push)
# Agent receives insight at task-start based on problem_class match

def suggest_insights_for_task(
    task_description: str,
    problem_class: str,
    agent_id: str,
) -> List[Insight]:
    """Called by borg_autosuggest (hermes-plugin) at task start.
    Returns top N insights matching the problem_class.
    Insights are ranked by quality_score DESC, decay_freshness ASC.
    
    The insight's trigger_phrase is injected as a prompt hint
    into the agent's context — NOT as a强制 directive."""


# Mechanism 2: Searchable Discovery (pull)
# Agent actively searches for relevant insights via borg_search

def search_insights(
    query: str,
    problem_class: Optional[str] = None,
    min_quality: float = 0.4,
    mode: str = "hybrid",
) -> List[Insight]:
    """Search approved insights using existing SemanticSearchEngine.
    Integrates with borg_search via an 'insights' search target.
    Results include insight_id, trigger_phrase, quality_tier, adoption_count."""
```

**Insight Index Structure:**

Insights are stored in a SQLite table (`insights.db`) alongside the pack index:

```sql
CREATE TABLE insights (
    insight_id      TEXT PRIMARY KEY,
    pattern_id     TEXT NOT NULL,
    problem_class  TEXT NOT NULL,
    trigger_phrase TEXT NOT NULL,
    insight_text   TEXT NOT NULL,
    quality_score  REAL NOT NULL,
    quality_tier   TEXT NOT NULL,   -- EXPERIMENTAL|PROBABLE|CONFIRMED
    adoption_count INTEGER DEFAULT 0,
    agent_count    INTEGER DEFAULT 0,
    created_at     TEXT NOT NULL,
    expires_at     TEXT NOT NULL,
    approved       INTEGER DEFAULT 0,
    decay_ttl_days INTEGER DEFAULT 30,
    
    -- Search optimization
    embedding      BLOB,            -- vector embedding of trigger_phrase
    fts_phrase     TEXT,            -- FTS5-indexed trigger_phrase
    
    -- Metadata
    propagation_tags TEXT,          -- JSON array of tags
    supporting_obs  TEXT,           -- JSON array of observation_ids
);

CREATE INDEX idx_insights_problem_class ON insights(problem_class);
CREATE INDEX idx_insights_quality ON insights(quality_score DESC);
CREATE INDEX idx_insights_tier ON insights(quality_tier);
```

**Broadcast Protocol:**

When an insight is approved:

1. `insight_store.insert(insight)` — persist to SQLite
2. `update_collective_index()` — append insight to `~/.hermes/guild/collective-index.jsonl` (append-only log, used for sync)
3. If `quality_tier == "CONFIRMED"`:
   - Push notification to connected agents via Hermes plugin hook
   - Increment `adoption_count` on the source pack (if insight was derived from a pack)
4. If `quality_tier == "PROBABLE"`:
   - Available via search, no push

---

### 3.5 Insight Store (insight_store.py)

**Responsibility:** Durable, append-only storage for observations and insights. Backed by SQLite.

**Schema:**

```python
# Main tables

CREATE TABLE observations (
    observation_id  TEXT PRIMARY KEY,
    agent_id_hash   TEXT NOT NULL,     # anonymized
    problem_class   TEXT NOT NULL,
    task_hash       TEXT NOT NULL,      # hash of task_description (not raw text)
    outcome         TEXT NOT NULL,      # success|partial|failure
    session_hash    TEXT NOT NULL,      # hash of session_id
    log_hash        TEXT NOT NULL,      # execution_log_hash
    raw_evidence    TEXT,               -- privacy_redacted evidence JSON
    phase_count     INTEGER,
    duration_s      INTEGER,
    timestamp       TEXT NOT NULL,
    observation_source TEXT NOT NULL,   -- apply-session|manual
    processed       INTEGER DEFAULT 0,  -- fed through extraction
);

CREATE TABLE patterns (
    pattern_id      TEXT PRIMARY KEY,
    problem_class   TEXT NOT NULL,
    trigger_phrase  TEXT NOT NULL,
    insight_text    TEXT NOT NULL,
    confidence      TEXT NOT NULL,      -- emerging|probable|confirmed
    agent_count     INTEGER DEFAULT 0,
    observation_ids TEXT NOT NULL,      -- JSON array
    first_seen      TEXT NOT NULL,
    last_updated    TEXT NOT NULL,
);

CREATE TABLE insights (
    -- (as defined in §3.4)
);

CREATE TABLE adoption_log (
    insight_id      TEXT NOT NULL,
    agent_id_hash   TEXT NOT NULL,
    applied_at      TEXT NOT NULL,
    session_id      TEXT,               -- session where agent applied insight
    outcome         TEXT,               -- did it help?
    PRIMARY KEY (insight_id, agent_id_hash)
);
```

**Storage Rules:**
- Observations are stored for 90 days, then purged (GDPR compliance)
- Insights expire per `decay_ttl_days` (default 30, configurable)
- All raw evidence is privacy_redacted before storage
- The store is append-only for insights (never deleted, only expires/archived)

---

## 4. Integration with Existing Modules

### 4.1 borg_search Integration

The `borg_search()` function in `search.py` is extended to support an optional `insights` target:

```python
def borg_search(query: str, mode: str = "text", target: str = "packs") -> str:
    """New target parameter:
        target="packs"    — existing pack search (default)
        target="insights" — search collective insights
        target="all"      — both packs and insights
    """
```

When `target="insights"`:
- Uses `SemanticSearchEngine` with the insights FTS5 table
- Reranks by quality_score * decay_freshness_factor
- Only returns insights where `approved=True` and `quality_score >= 0.4`

### 4.2 apply.py Integration

The `action_complete()` function is augmented:

```python
# In action_complete(), after generating feedback:
try:
    obs = observer.on_session_complete(session)
    # Non-blocking — fire-and-forget to extraction queue
    _collective_queue.put(obs)
except Exception as e:
    logger.warning("CPI observation capture failed: %s", e)
    # Never break the apply flow
```

### 4.3 hermes-plugin Integration

The existing `borg_on_task_start()` hook is extended to suggest relevant insights:

```python
# In borg_on_task_start() in hermes-plugin/__init__.py:
insights = propagation.suggest_insights_for_task(
    task_description=task_description,
    problem_class=classify_task(task_description),
    agent_id=agent_id,
)
if insights:
    insight_hints = "\n".join(
        f"  • {i.trigger_phrase} (confidence: {i.quality_tier})"
        for i in insights[:3]
    )
    # Injected into agent context as non-binding hint
```

### 4.4 Reusing Existing Safety Infrastructure

The CPI quality_gates module reuses:
- `borg.core.safety.scan_pack_safety()` — for injection pattern detection
- `borg.core.privacy.privacy_redact()` — for PII scrubbing
- `borg.core.privacy.privacy_scan_text()` — for privacy validation
- `borg.core.proof_gates.compute_pack_tier()` — for provenance quality
- `borg.core.proof_gates.check_confidence_decay()` — for freshness scoring

---

## 5. Algorithms

### 5.1 Pattern Generalization Algorithm

```
Input: List[Observation] clustered by (problem_class, outcome)

FOR each cluster:
    1. Collect all evidence strings
    2. Run TF-IDF on evidence phrases (tokenized on sentence boundaries)
    3. Extract top-K high-TF-IDF phrases (K=5)
    4. For each high-TF-IDF phrase:
       a. Check if phrase appears in ≥ 50% of observations in cluster
       b. If yes → candidate insight
    5. For candidate insights:
       a. Verify not already generalized (pattern_id deduplication)
       b. Generate trigger_phrase using template:
          "[action] [context] improves [outcome_type]"
       c. Assign confidence based on agent_count and observation_count
    6. Return ExtractedPattern list
```

### 5.2 Quality Scoring Algorithm

```
Input: ExtractedPattern + supporting observations

quality_score = (
    signal_strength(observations)   * 0.35
  + provenance_quality(pattern)     * 0.30
  + decay_freshness(pattern)        * 0.15
  + privacy_cleanliness(pattern)   * 0.20
)

WHERE:

signal_strength = min(1.0, (
    log(1 + observation_count) / log(21)  * 0.5
  + min(1.0, agent_diversity / 5)        * 0.3
  + cross_problem_bonus                    * 0.2
))

provenance_quality = {
    "confirmed":  1.0,
    "probable":  0.6,
    "emerging":  0.3,
}[pattern.confidence]

decay_freshness = max(0, 1.0 - (age_days / (decay_ttl_days * 2)))

privacy_cleanliness = 1.0 if no_privacy_flags else 0.0
```

### 5.3 Anti-Entropy Algorithm

```
Input: New insight candidate, existing insight store

1. RATE_LIMIT_CHECK:
   Count insights from same agent_id_hash today
   If count >= 3: queue for manual review, reject propagation

2. DUPLICATE_CHECK:
   If pattern_id exists in store:
     Merge supporting_observations
     Update agent_count += 1
     Update last_updated
     Do NOT create duplicate insight
     Return existing insight_id

3. SIMILARITY_CHECK:
   Compute Jaccard similarity of trigger_phrase tokens
   against existing insights in same problem_class
   If similarity > 0.6:
     Merge into most-established insight
     Return existing insight_id
   Else:
     Proceed with new insight_id

4. CONTENT_QUALITY_CHECK:
   If len(trigger_phrase) < 10: reject
   If insight_text is generic (matches generic_patterns list): reject
```

---

## 6. Privacy & Safety Guardrails

### 6.1 Privacy Architecture

The privacy architecture is defense-in-depth across all layers:

| Layer | Mechanism | Protects Against |
|-------|-----------|-----------------|
| **Capture** | `privacy_redact()` on all text | PII in agent evidence |
| **Storage** | Hashes for IDs, not raw data | Re-identification risk |
| **Extraction** | Token-level privacy scan | Token leakage in patterns |
| **Propagation** | `privacy_check()` gate | PII in trigger phrases |
| **Agent Context** | Redacted hints only | Agents don't see raw PII |

### 6.2 PII Categories Guarded

All patterns from `borg.core.privacy._PRIVACY_PATTERNS` are blocked:

- File paths (`/home/*`, `/root/*`, `~/.hermes/*`, `C:\`)
- IP addresses (v4 and v6)
- Email addresses
- API keys / tokens (OpenAI, Slack, GitHub, Google, AWS, GitLab)
- Any future patterns added to `_PRIVACY_PATTERNS`

### 6.3 Toxicity Categories Guarded

Using extended patterns from `borg.core.safety._INJECTION_PATTERNS` plus:

- **Hallucination markers**: "always works", "never fails", "guaranteed to"
- **Manipulation patterns**: "you must", "always do this", "never do that"
- **Overgeneralization**: single-example conclusions
- **Confidence inflation**: "100% sure", "certain", "definitely"

### 6.4 Differential Privacy (Future)

For Phase 3, we add stochastic privacy:

- When `agent_count < 3`, add calibrated noise to trigger phrases
- No insight is propagated with fewer than 2 independent agents
- Adoption counts are rounded to nearest 5 to prevent timing attacks

---

## 7. Quality Scoring to Prevent Garbage Propagation

### 7.1 Garbage Patterns Prevented

The quality gates specifically block:

| Garbage Type | Detection Method |
|--------------|-----------------|
| **Spam** | Rate limit: max 3 insights/agent/day |
| **Duplicates** | Pattern ID deduplication |
| **Near-duplicates** | Jaccard similarity > 0.6 merge |
| **PII leakage** | privacy_check gate |
| **Toxic patterns** | toxicity_check gate |
| **Hallucinations** | Overconfidence language detector |
| **Low-value** | quality_score < 0.40 threshold |
| **Expired insights** | TTL decay + freshness check |

### 7.2 Quality Score Thresholds

```
┌─────────────────────────────────────────────────────┐
│  quality_score  │  quality_tier  │  Propagation     │
├─────────────────┼────────────────┼──────────────────┤
│  0.70 – 1.00    │  CONFIRMED     │  Broad push +    │
│                 │                │  elevated search │
├─────────────────┼────────────────┼──────────────────┤
│  0.40 – 0.69    │  PROBABLE      │  Search only,    │
│                 │                │  no push         │
├─────────────────┼────────────────┼──────────────────┤
│  0.00 – 0.39    │  EXPERIMENTAL  │  Stored locally, │
│                 │                │  not propagated  │
└─────────────────┴────────────────┴──────────────────┘
```

### 7.3 Adoption Feedback Loop

Over time, `adoption_log` provides a secondary quality signal:

```python
def boost_insight_quality(insight_id: str) -> None:
    """Called when an agent reports applying an insight successfully."""
    insight = store.get_insight(insight_id)
    insight.adoption_count += 1
    
    # If adoption_count crosses milestone thresholds, boost quality_score
    if insight.adoption_count in (10, 25, 50, 100):
        insight.quality_score = min(1.0, insight.quality_score * 1.05)
        insight.quality_tier = recompute_tier(insight.quality_score)
```

This creates a flywheel: the best insights get better over time as more agents adopt and validate them.

---

## 8. Phased Implementation Plan

### Phase 1: Foundation (Weeks 1–4) — MVP Collective

**Goal:** Basic observation capture + manual insight submission + search

**Deliverables:**
1. `borg/core/collective/types.py` — Observation, ExtractedPattern, Insight dataclasses
2. `borg/core/collective/insight_store.py` — SQLite storage, CRUD for insights
3. `borg/core/collective/observer.py` — observation capture hooks (no-op first)
4. `borg/core/collective/extractor.py` — stub with manual submission path
5. `borg/core/collective/quality_gates.py` — threshold-based gate (quality_score >= 0.4)
6. Extend `borg_search()` with `target="insights"` search mode
7. Integration test: observation captured → stored → searchable

**Gates:**
- Privacy: `privacy_redact()` applied at capture
- No toxicity checking in P1 (deferred)
- No propagation push (pull-only)

**Success Criteria:**
- Manual insight submission creates a searchable insight
- `borg_search(query, target="insights")` returns results
- Quality gate correctly rejects insights with quality_score < 0.4

---

### Phase 2: Auto-Capture & Quality (Weeks 5–8) — Learning Loop

**Goal:** Automatic observation capture from apply sessions + full quality gates

**Deliverables:**
1. `observer.py` fully integrated with `apply.py` action_complete
2. Per-phase observation capture via `action_checkpoint`
3. `extractor.py` — full pattern generalization pipeline
4. Full `quality_gates.py` — privacy_check, toxicity_check, anti_entropy
5. `propagation.py` — push suggestions at task start
6. `decay_ttl_days` freshness scoring integrated into search ranking
7. End-to-end test: agent uses pack → observation captured → pattern extracted → insight approved → searchable

**Gates:**
- Full privacy_check before propagation
- Full toxicity_check
- Anti-entropy rate limiting (max 3/agent/day)
- Duplicate detection via pattern_id

**Success Criteria:**
- A successful apply session produces a searchable insight within 5 minutes
- No PII-leaking insights propagate
- Duplicate patterns merge correctly

---

### Phase 3: Scale & Resilience (Weeks 9–14) — Production Collective

**Goal:** Multi-agent sync, differential privacy, advanced quality signals

**Deliverables:**
1. `collective-index.jsonl` sync protocol for multi-agent coordination
2. Differential privacy: noise injection for agent_count < 3 insights
3. Adoption feedback loop: `adoption_log` + quality boost on milestone adoption
4. Cross-agent collaborative filtering: "agents like you also used..."
5. Insight expiration + archival system
6. CPI dashboard: insight pipeline metrics, quality distributions
7. Hermes plugin push notification for CONFIRMED-tier insights
8. Advanced toxicity detection using embedding similarity

**Gates:**
- All Phase 2 gates plus
- Stochastic privacy for small-cell insights
- Cross-validation: at least 2 agents must report success before CONFIRMED

**Success Criteria:**
- After 2 agents successfully apply the same pattern, it escalates to CONFIRMED
- CONFIRMED insights are pushed proactively to relevant agents
- System handles 100+ agents without degradation

---

### Phase 4: Intelligence Maturation (Weeks 15–20) — Self-Improving Collective

**Goal:** The collective gets smarter over time; autonomous pack improvement

**Deliverables:**
1. **Autonomous pack evolution**: Insights from collective feed back into pack refinement
   - When a pattern is confirmed across 10+ agents, it automatically generates a pack version update
   
2. **Predictive suggestion**: ML model predicts which insights will help given:
   - Current task context
   - Agent's historical success patterns
   - Time-of-day / problem_class trends
   
3. **Collective immune system**: Automatic detection and quarantine of:
   - Concept drift (insights becoming outdated)
   - Adversarial gaming attempts
   - Cascading failures from bad insights

4. **Pack generation from insights**: 
   - Confirmed insights with 20+ adoptions auto-generate new workflow packs
   - New packs go through proof_gates validation before publishing

**Success Criteria:**
- Collective accuracy (validated by human review) ≥ 85%
- False positive rate (bad insights reaching agents) < 5%
- System uptime ≥ 99.5%

---

## 9. Configuration

### 9.1 CPI Configuration Constants (config.py)

```python
# Observation capture
OBSERVATION_ENABLED: bool = True
CAPTURE_PHASE_LEVEL: bool = True           # capture per-phase observations
CAPTURE_SESSION_LEVEL: bool = True         # capture per-session observations
MAX_EVIDENCE_LENGTH: int = 2000            # chars (privacy + storage)

# Quality thresholds
QUALITY_THRESHOLD_PROPAGATE: float = 0.40  # minimum quality to propagate
QUALITY_THRESHOLD_CONFIRMED: float = 0.70  # minimum for CONFIRMED tier
ADOPTION_BOOST_THRESHOLDS: List[int] = [10, 25, 50, 100]

# Anti-entropy
MAX_INSIGHTS_PER_AGENT_PER_DAY: int = 3
MIN_INSIGHT_LENGTH_CHARS: int = 10
DUPLICATE_SIMILARITY_THRESHOLD: float = 0.6

# Storage & decay
OBSERVATION_RETENTION_DAYS: int = 90
INSIGHT_DEFAULT_TTL_DAYS: int = 30
INSIGHT_HALF_LIFE_DAYS: int = 30           # for freshness decay scoring

# Propagation
PUSH_ENABLED: bool = True
PUSH_MAX_INSIGHTS_PER_TASK: int = 3
CONFIRMED_PUSH_BROADCAST: bool = True
```

---

## 10. Error Handling & Resilience

### 10.1 Failure Modes

| Component | Failure Mode | Mitigation |
|-----------|-------------|------------|
| Observation capture | apply.py fails | Non-blocking, logged, never breaks apply flow |
| Extraction pipeline | Crash or OOM | Per-observation try/except, failed obs logged for retry |
| Privacy check | False positive (legitimate text flagged) | Insights land in manual review queue |
| Quality gate | Score gaming | Anti-entropy checks + human audit sample |
| Storage | SQLite corruption | Append-only log + rebuild from observations |
| Propagation | Agent offline | Insights available on next agent connection via sync |

### 10.2 Graceful Degradation

If the CPI system is unavailable:
- `borg_search` continues to work (pack search is independent)
- `apply.py` completes normally (observation is best-effort)
- Agents operate with existing pack knowledge only
- On recovery, queued observations are flushed in order

---

## 11. Security Considerations

### 11.1 Attack Vectors & Mitigations

| Attack | Description | Mitigation |
|--------|-------------|------------|
| **PII Injection** | Attacker embeds PII in evidence to poison patterns | `privacy_redact()` at capture; `privacy_check()` gate |
| **Insight Spam** | Rapid submission of low-value insights | Rate limit: 3/agent/day; quality threshold |
| **Pattern Poisoning** | Manipulate pattern generalization | Anti-entropy similarity check; multi-agent validation |
| **Trust Tier Elevation** | Fake adoption feedback to boost tier | Adoption requires valid session_hash; audit sampling |
| **Privacy Timing Attack** | Infer PII presence from observation count | Noise injection for agent_count < 3 |
| **Collective Partition** | Isolate agents to fragment collective | collective-index.jsonl sync with hash validation |

### 11.2 Agent Anonymization

The `agent_id` stored in all CPI tables is a one-way hash:
```python
import hashlib
agent_id_hash = hashlib.sha256(
    f"{agent_id}:{salt}".encode()
).hexdigest()[:16]
```
The salt is stored separately and not recoverable from stored data. This ensures:
- No agent can be identified from stored observations
- Even the system operator cannot reverse agent_id_hash without the salt
- Compliance with data minimization principles

---

## 12. Metrics & Observability

### 12.1 Key Metrics

```
# Pipeline health
observations.captured         — counter (per day)
observations.processed         — counter
observations.failed           — counter (with reason labels)
extractions.generated         — counter
extractions.duplicates       — counter (merged, not new)
insights.approved             — counter
insights.rejected             — counter (with rejection_reason)
insights.quality_distribution — histogram [0.0-1.0 buckets]

# Propagation
insights.pushed               — counter
insights.searched             — counter
insights.adopted              — counter (with insight_id, outcome)
adoption.boost_events         — counter (milestone crossings)

# System health
cpi.queue_depth               — gauge (observations pending extraction)
cpi.store.size_bytes         — gauge
cpi.errors                    — counter (with component label)
```

### 12.2 Logging

CPI operations are logged at `INFO` level with structured fields:
```python
logger.info(
    "Insight approved",
    insight_id=insight.insight_id,
    quality_tier=insight.quality_tier,
    quality_score=insight.quality_score,
    agent_count=insight.pattern.agent_count,
    propagation_tags=insight.propagation_tags,
)
```

---

## 13. Dependencies

### 13.1 Existing Modules Reused

- `borg.core.search` — extended for insight search
- `borg.core.apply` — observation capture hooks added
- `borg.core.session` — session events extended for CPI
- `borg.core.safety` — pattern detection reused in quality gates
- `borg.core.privacy` — redaction and scanning reused
- `borg.core.proof_gates` — provenance quality reused
- `borg.core.semantic_search` — SemanticSearchEngine reused for insight search

### 13.2 New Dependencies

- `borg.db.store` — existing GuildStore extended with insights table
- SQLite (stdlib) — insight_store backing
- `hashlib` (stdlib) — agent anonymization, pattern IDs
- `dataclasses` (stdlib) — type definitions

No new external dependencies beyond what borg already requires.

---

## 14. File Manifest

```
borg/core/collective/
  __init__.py                 # Module exports
  types.py                    # Observation, ExtractedPattern, Insight dataclasses
  config.py                   # CPI configuration constants
  insight_store.py            # SQLite-backed insight storage
  observer.py                 # Observation capture hooks
  extractor.py                # Pattern extraction & generalization
  quality_gates.py            # Quality scoring & gating
  propagation.py              # Push/pull insight distribution
  metrics.py                  # CPI observability (Phase 3)

borg/core/search.py            # [MODIFIED] target="insights" support
borg/core/apply.py             # [MODIFIED] observer.on_session_complete call
borg/hermes-plugin/__init__.py # [MODIFIED] insight suggestion at task start

tests/
  borg/tests/test_collective_observer.py
  borg/tests/test_collective_extractor.py
  borg/tests/test_collective_quality.py
  borg/tests/test_collective_propagation.py
  borg/tests/test_insight_store.py
```

---

## 15. Open Questions & Future Considerations

1. **Cross-organizational sharing**: How should insights propagate between agents on different deployments? Requires identity federation or fully anonymized collective-index.

2. **Insight attribution**: When a CONFIRMED insight comes from multiple agents, how is credit assigned? (For community metrics, not enforcement.)

3. **Insight revocation**: If an insight is later found to be harmful, how is it retracted across all agents? (Append-only log allows revert but requires protocol.)

4. **Regulatory compliance**: GDPR "right to erasure" for observations — since observations are anonymized by hash, this may be satisfiable without full deletion.

5. **Resource consumption**: At scale (1000+ agents), observation volume may require batching or streaming aggregation rather than per-observation processing.

These are left as open questions for future design iterations.

---

*End of Collective Prompt Intelligence Design Document*
