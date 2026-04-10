# agent-borg v3.3.0 — Architecture Specification

| Field | Value |
|---|---|
| Spec ID | ARCHITECTURE_SPEC_v3.3.0 |
| Author | Team BLUE (subagent, MiniMax-M2.7) |
| Date | 2026-04-09 |
| Status | For AB review |
| Quality bar | Google SWE-L6 / PhD committee / HN front page |
| Target | One senior engineer can implement without further questions |

---

## 1. Problem Statement

On a clean install of `agent-borg`, every `borg search` returns `No packs found.` because the 17 frontmatter skill files shipped inside the wheel are never merged into the search index, leaving the local pack store (`~/.hermes/guild/`) and the trace database (`~/.borg/traces.db`) both empty on first use.

---

## 2. Formal Model for Cold-Start Seed Corpus

### 2.1 Pack Space

Let **P** be the space of all possible workflow packs, where a pack `p` is a 6-tuple:

```
p = (id, problem_class, framework, phases, provenance, evidence)
```

- `id`: unique identifier string (kebab-case)
- `problem_class`: category string (e.g., `null_pointer_chain`)
- `framework`: ecosystem string (e.g., `python`, `django`, `rust`)
- `phases`: ordered list of `{name, description, checkpoint, anti_patterns, prompts}`
- `provenance`: `{author, created, confidence, source_url, license}`
- `evidence`: `{success_count, failure_count, success_rate, avg_time_to_resolve_minutes, uses}`

### 2.2 Seed Corpus

The seed corpus **C** is a curated finite subset of **P**, shipped read-only inside the wheel at `borg/seeds_data/packs/`. C is static per release (immutable, versioned with the wheel).

### 2.3 Mutation Operator

The mutation operator **M** acts on the search query `q` and the corpus **C**:

```
M(q, C) = { p in C | match_score(p, q) >= tau }
```

where `match_score` is a token-overlap function over the concatenation of `p.id`, `p.problem_class`, and all `phase.name` strings. The threshold `tau = 1` (at least one token match). This is a deterministic, offline, zero-LLM operation.

### 2.4 Score Function

The ranking function **S** scores each candidate pack `p` returned by `M(q, C)`:

```
S(p, q) = relevance_score(p, q) + reputation_boost(p) + adoption_boost(p)
```

- `relevance_score`: binary (1 if any token overlap, else 0) — computed by `M`
- `relevance_boost`: 0.0 to 0.3 based on author access tier differential (see `borg/core/search.py` lines 329-366)
- `adoption_boost`: 0.0 to 0.2 based on `adoption_count` (capped at 20)

### 2.5 Coverage Target

Under a Zipf-distributed query vocabulary with alpha ~ 1.0-1.2 over software-engineering terms, and assuming per-pack coverage probability `p_cov = 0.01` (conservative), targeting 80% G1 and 95% G2 requires:

```
G1: P(at least 1 hit) >= 0.80  =>  K >= 161 packs
G2: P(at least 5 hits) >= 0.95 =>  K >= 299 packs
```

Therefore target **K = 500 packs** for v3.3.0, rounded up to account for correlated overlap between related problem classes (e.g., multiple null-pointer packs).

**Note**: K=500 is a starting target validated empirically by the prototype in Phase 7. The prototype must validate it before full curation spend is authorized.

---

## 3. Exact YAML Schema for Seed Packs

Every seed pack is a YAML file at `borg/seeds_data/packs/<id>.yaml` conforming to the `workflow_pack` schema.

### 3.1 Schema

```yaml
# =============================================================================
# REQUIRED TOP-LEVEL FIELDS
# =============================================================================

type:                     # string, MUST be "workflow_pack"
  type: string
  constraint: must equal "workflow_pack"
  example: "workflow_pack"

version:                  # string, MUST be "1.0"
  type: string
  constraint: must equal "1.0"
  example: "1.0"

id:                       # string, unique pack identifier (kebab-case)
  type: string
  constraint: regex ^[a-z0-9-]+$, max_length 64
  example: "null-pointer-chain"

problem_class:            # string, maps to PROBLEM_CLASSES list
  type: string
  constraint: must be in canonical PROBLEM_CLASSES list
  example: "null_pointer_chain"

# =============================================================================
# REQUIRED SECTION: phases
# =============================================================================

phases:                   # list[Phase], MUST have >= 3 phases
  type: list
  min_length: 3
  items:
    name:                 # string, kebab-case, unique within pack
      type: string
      example: "trace-none-returns"
    description:          # string, human-readable explanation
      type: string
      min_length: 10
      example: "Trace where None was produced, not where it was consumed"
    checkpoint:           # string, when this phase is considered done
      type: string
      example: "upstream_none_source_identified"
    anti_patterns:        # list[AntiPattern]
      type: list
      items:
        action:           # string, what NOT to do
          type: string
        why_fails:        # string, why this action fails
          type: string
          min_length: 10
    prompts:              # list[string], guidance prompts for the agent
      type: list[string]
      min_length: 1

# =============================================================================
# REQUIRED SECTION: provenance
# =============================================================================

provenance:
  author:                 # string, MUST be "agent-borg" for seed packs
    type: string
    constraint: must equal "agent-borg" for seeds
    example: "agent-borg"
  created:                # string, ISO-8601 UTC datetime
    type: string
    example: "2026-04-09T00:00:00Z"
  confidence:             # string, one of {tested, inferred, guessed}
    type: string
    enum: [tested, inferred, guessed]
    example: "tested"
  license:                # string, SPDX license identifier
    type: string
    constraint: MUST be on allowlist (MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause, CC0-1.0, CC-BY-4.0, Python-2.0)
    example: "MIT"
  source_url:             # string, URL to public source (MUST resolve, required for CI)
    type: string
    constraint: must be valid URL, required for seed packs
    example: "https://github.com/pallets/flask/blob/main/CHANGES.rst"

# =============================================================================
# OPTIONAL FIELDS
# =============================================================================

framework:                # string, primary ecosystem
  type: string
  example: "python"

mental_model:             # string, reasoning style
  type: string
  default: "fast-thinker"
  example: "slow-thinker"

evidence:                 # dict, success metrics
  success_count:           # int, >= 0
  failure_count:           # int, >= 0
  success_rate:            # float, 0.0 to 1.0
  avg_time_to_resolve_minutes:  # float, >= 0
  uses:                    # int, total uses

problem_signature:        # dict, error signature for classifier
  error_types:            # list[string], e.g. [AttributeError, TypeError]
  problem_description:   # string, human-readable description

root_cause:               # dict
  category:               # string, root cause category
  explanation:            # string, why this error occurs

investigation_trail:      # list[InvestigationStep], ordered
  - file:                 # string, file pattern to look at
    position:             # string, e.g. FIRST, SECOND, THIRD
    what:                 # string, what to look for
    grep_pattern:         # string, grep pattern (optional)

resolution_sequence:      # list[ResolutionStep], ordered
  - action:               # string, action name
    command:              # string, exact command to run
    why:                  # string, why this works

# =============================================================================
# FORBIDDEN FIELDS (seed packs specifically)
# =============================================================================
# - provenance.author may NOT be an individual's name or handle
# - No field may contain content from:
#   - ~/.hermes/sessions/ (private)
#   - ~/.claude/ (private)
#   - StackOverflow question/answer bodies (CC-BY-SA incompatible with MIT wheel)
#   - MDN CC-BY-SA sources
```

### 3.2 Example Seed Pack

```yaml
type: workflow_pack
version: "1.0"
id: null-pointer-chain
problem_class: null_pointer_chain
framework: python

phases:
  - name: identify-consumer-site
    description: Find the exact line that raised AttributeError or TypeError involving None
    checkpoint: consumer_file_and_line_identified
    anti_patterns:
      - action: "Reading the method that raised the error"
        why_fails: "The error occurs at the call site, not the definition. The method returned None upstream."
    prompts:
      - "Find the line: TypeError: 'NoneType' object has no attribute 'foo'"
      - "Identify which object is None"
  - name: trace-upstream-source
    description: Read the called method's return statement to find where None was produced
    checkpoint: upstream_none_source_identified
    anti_patterns:
      - action: "Adding 'if obj is not None' checks downstream"
        why_fails: "Hides the bug instead of fixing the source."
    prompts:
      - "Read the method that was called"
      - "Find the return statement"
      - "Identify which upstream value was None"
  - name: fix-at-source
    description: Fix the line that produces None, not the line that consumes it
    checkpoint: fix_verified
    anti_patterns:
      - action: "Wrapping in try/except pass"
        why_fails: "Masks the symptom, not the cause."
    prompts:
      - "Fix the return statement to return a valid value"
      - "Or add explicit None handling at the boundary"

provenance:
  author: agent-borg
  created: "2026-04-09T00:00:00Z"
  confidence: tested
  license: MIT
  source_url: "https://github.com/pallets/flask/blob/main/CHANGES.rst"

evidence:
  success_count: 47
  failure_count: 5
  success_rate: 0.90
  avg_time_to_resolve_minutes: 3.1
  uses: 52
```

---

## 4. `_load_seed_index()` Interface Contract

**File**: `borg/core/uri.py`

### 4.1 Signature

```python
def _load_seed_index(force_reload: bool = False) -> dict:
```

### 4.2 Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `force_reload` | `bool` | `False` | If True, bypass memoization cache and re-read from disk. Used by test fixtures. |

### 4.3 Return Value

```python
{
    "version": str,           # e.g. "1.0"
    "generated_at": str,       # ISO-8601 UTC, e.g. "2026-04-09T00:00:00Z"
    "pack_count": int,        # number of packs in index
    "packs": List[dict]       # list of pack summary dicts (see below)
}
```

Each pack summary dict in `packs` contains:

```python
{
    "id": str,                # pack identifier (kebab-case)
    "name": str,              # display name
    "problem_class": str,     # canonical problem class
    "framework": str,         # ecosystem, e.g. "python"
    "confidence": str,        # "tested" | "inferred" | "guessed"
    "tier": str,              # "seed" (all seed packs have tier=seed)
    "source": str,            # "seed" (all seed packs have source=seed)
    "phase_names": List[str], # names of phases for text search
    "phases": int,            # count of phases
    "license": str,           # SPDX identifier
    "source_url": str,        # resolvable public URL
}
```

### 4.4 Side Effects

- Reads `borg/seeds_data/index.json` from disk exactly once per process (memoized at import via `functools.lru_cache(maxsize=1)`).
- If `BORG_DISABLE_SEEDS=1` environment variable is set, returns `{"packs": [], "pack_count": 0}` without reading disk.
- Never writes to `~/.hermes/guild/` or any user-writable directory.
- Never makes network calls.

### 4.5 Error Handling

| Condition | Behavior |
|---|---|
| `borg/seeds_data/index.json` does not exist | Return `{"packs": [], "pack_count": 0}` — do NOT raise |
| File is malformed JSON | Log warning, return `{"packs": [], "pack_count": 0}` — do NOT raise |
| `borg/seeds_data/` directory not found (editable install without seeds) | Return `{"packs": [], "pack_count": 0}` — do NOT raise |
| `BORG_DISABLE_SEEDS=1` set | Return `{"packs": [], "pack_count": 0}` immediately |

### 4.6 Integration Point

`_load_seed_index()` is called inside `borg_search()` (in `borg/core/search.py`) immediately after `_fetch_index()` returns, and the resulting packs are merged into `all_packs` before deduplication. The exact call site is after line 108 of `search.py`:

```python
index = _fetch_index()
all_packs = list(index.get("packs", []))  # <- remote packs

# NEW: merge seed corpus
if not _seeds_disabled():
    seeds = _load_seed_index().get("packs", [])
    all_packs.extend(seeds)

# ... continue with local packs, deduplication, ranking
```

---

## 5. Complete Data Model

### 5.1 Storage Layout

```
site-packages/borg/
  seeds_data/
    index.json              # precomputed search index (created at build time)
    VERSION                 # "seeds-1.0.0-2026-04-09"
    packs/
      null-pointer-chain.yaml
      migration-state-desync.yaml
      import-cycle.yaml
      ... (500 packs in v3.3.0)
    .license_audit/
      null-pointer-chain.license.json
      migration-state-desync.license.json
      ...

~/.hermes/guild/           # user-local (read-write)
  <pack-name>/
    pack.yaml               # user-authored or pulled packs (preferred over seeds)
  packs/
    <pack-name>.yaml       # flat-pack format

~/.borg/
  traces.db                # SQLite, traces from borg observe

~/.hermes/guild/borg_v3.db  # SQLite, v3 feedback/outcomes
```

### 5.2 SQL Schema — Traces DB (`~/.borg/traces.db`)

```sql
CREATE TABLE traces (
    id          TEXT PRIMARY KEY,   -- UUID, e.g. "5410f519"
    task        TEXT NOT NULL,     -- task description
    context     TEXT,               -- optional context string
    error       TEXT,               -- optional error message
    agent_id    TEXT DEFAULT 'cli',
    created_at  TEXT NOT NULL,     -- ISO-8601 UTC
    outcome     TEXT                -- 'success' | 'failure' | null
);

CREATE INDEX idx_traces_task ON traces(task);
CREATE INDEX idx_traces_created ON traces(created_at);
```

### 5.3 SQL Schema — V3 Outcomes DB (`~/.hermes/guild/borg_v3.db`)

```sql
CREATE TABLE outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id         TEXT NOT NULL,
    task_context    TEXT,           -- JSON string
    success         INTEGER NOT NULL, -- 0 or 1
    tokens_used     INTEGER,
    time_taken      REAL,
    recorded_at     TEXT NOT NULL,   -- ISO-8601 UTC
    source          TEXT DEFAULT 'feedback-v3'
);

CREATE INDEX idx_outcomes_pack ON outcomes(pack_id);
CREATE INDEX idx_outcomes_success ON outcomes(success);
```

### 5.4 Pack YAML Schema (Full)

See Section 3 for the exact YAML schema. Packs in `~/.hermes/guild/<name>/pack.yaml` use the same `workflow_pack` schema as seed packs, with the following differences:

| Field | Seed Pack | User Pack |
|---|---|---|
| `provenance.author` | MUST be `agent-borg` | Any string |
| `provenance.license` | MUST be on allowlist | Recommended, not required |
| `tier` | Always `seed` | `community`, `author-validated`, or `core` |
| `source` | `seed` | `local`, `remote`, or `trace` |

### 5.5 Dedup Semantics

When a pack ID appears in multiple sources (seed, remote index, local), the priority order is:

1. **Local** (`~/.hermes/guild/<name>/pack.yaml`) — highest priority
2. **Remote index** (`guild-packs` GitHub repo)
3. **Seed corpus** (`borg/seeds_data/packs/`) — lowest priority, never overwrites local

This is enforced by the existing dedup loop in `search.py` lines 151-182.

---

## 6. Search Strategy Justification

### 6.1 Why Text Search (Not Bayesian, Not Evolutionary)

The corpus size at launch is **K = 500 packs**. This is a small enough search space that the overhead of Bayesian optimization or evolutionary algorithms is unjustified.

**Hill-climbing is sufficient**: The P1.1 experiment confirmed that the cold-start problem is not a ranking problem — it is a **coverage problem**. The query "debugging" returns 0 results not because the ranking algorithm is wrong, but because the index is empty. Adding 500 seed packs fixes the coverage. A hill-climbing search over 500 items with token-overlap scoring converges to optimal in O(K) time.

**Against Bayesian optimization**: Bayesian methods (e.g., Bayesian Optimization over embeddings) require:
- A differentiable surrogate model
- An acquisition function
- Multiple rounds of candidate generation

For K=500 with static pack content, this is over-engineered. The search is deterministic given the query — there is nothing to "optimize" across iterations.

**Against evolutionary algorithms**: Genetic algorithms, neuroevolution, or CMA-ES require:
- A fitness function measurable at the individual level
- Crossover and mutation operators
- Multiple generations

The fitness of a pack is not known at query time. Evolutionary search over pack rankings would require a feedback loop (which exists later in the pipeline via `feedback-v3`, but not at cold-start search time).

**Against semantic/embedding search**: Vector similarity search requires:
- An embedding model (sentence-transformers, OpenAI embeddings, etc.)
- An FAISS or QDrant index
- An embedding computation step for each new pack

Current implementation: `sentence-transformers>=2.2.0` is only loaded under `agent-borg[embeddings]`. Most users do not install this extra. The text search path is the default and must work without embeddings.

**Conclusion**: Text search via token overlap is the correct algorithm for cold-start. It is O(K) where K=500, sub-millisecond in practice, requires no external dependencies, works offline, and is deterministic. Embedding-based ranking is an optional enhancement for the `semantic` and `hybrid` modes, but it is not the primary search path and must never block the text path.

### 6.2 Future Directions (Out of Scope for v3.3.0)

- Embedding-based ranking (when `agent-borg[embeddings]` is installed)
- Thompson sampling for pack selection (v3_integration already has `BorgV3.record_outcome()`)
- Learning-to-rank via behavioral data from `feedback-v3`

---

## 7. Convergence and Stop Criteria

### 7.1 Search Convergence

The search algorithm (`M(q, C)` in Section 2) is deterministic and always terminates. There are no iterations.

```
convergence_time = O(K)  where K = number of packs in all_packs (seed + remote + local)
                    <= O(500 + remote_packs + local_packs)
                    <= O(1000)  [generous upper bound]
```

In practice, the inner loop at `search.py` lines 270-280 iterates over `all_packs` with a simple substring check. At K=500, this completes in < 1ms on any hardware.

### 7.2 Agent Loop Convergence (for the C3 replay)

The C3 replay experiment uses the following stop criteria:

| Criterion | Threshold |
|---|---|
| `borg_search` called | at least 1 time |
| `borg_search` returns | >= 1 match with `source == "seed"` |
| Agent loop | maximum 20 iterations (same as P1.1) |
| Per-run timeout | 900 seconds |
| Experiment budget | $5.00 hard cap |

The experiment is declared a **success** if `borg returned content rate >= 0.80` (>= 12 of 15 runs return >= 1 seed match).

### 7.3 Ship Gate Criteria

All 4 ship blockers (SB-01 through SB-04) must pass their acceptance criteria before the v3.3.0 tag is cut. These are binary pass/fail, no flexibility.

---

## 8. Multi-Objective Optimization

The system must balance seven goals simultaneously. They are not independent — tradeoffs are explicit.

### 8.1 Goal Definitions and Weights

| Goal | Metric | Target | Weight | Constraint Type |
|---|---|---|---|---|
| G1 | % of 50-query benchmark with >= 1 relevant result | >= 80% (>= 40/50) | CRITICAL | Hard floor |
| G2 | % of 50-query benchmark with >= 5 results | >= 95% (>= 47/50) | CRITICAL | Hard floor |
| G3 | Wheel size delta (uncompressed) | <= 5 MiB | CRITICAL | Hard constraint |
| G4 | `pytest borg/tests/` | 100% pass | HIGH | Regression gate |
| G5 | License audit | Every pack has allowlist license + source_url | HIGH | Compliance gate |
| G6 | `--no-seeds` opt-out flag | Exists and functional | MEDIUM | CLI UX |
| G7 | C3 replay "borg returned content" rate | >= 25/30 | HIGH | Evidence gate |

### 8.2 Tradeoff Rules

1. **G3 is a hard constraint**: if curation produces packs that exceed the 5 MiB budget, the curation team must reduce pack count or minify YAML (no exceptions, because wheel size affects install time and PyPI limits).
2. **G1 > G2**: G1 is the primary cold-start metric. We accept G2 being tight on edge cases if G1 is met.
3. **G7 is conditional**: G7 only runs if the C3 prototype passes. If the prototype fails, G7 becomes "prototype must be redesigned" (not a ship blocker, but a design revision gate).
4. **G4 is non-negotiable for any release**: a single pytest failure blocks the release tag.
5. **G5 is a license compliance gate**: a single un-audited or non-allowlist pack blocks inclusion. This is not a ship blocker for existing packs but is a hard gate for any new curation.

### 8.3 Optimization Procedure

For the curation of K=500 packs:
1. Sort candidate packs by `(license_allowlist_score DESC, evidence.success_rate DESC, evidence.uses DESC)`.
2. Accept packs in order until K is reached or budget is exhausted.
3. Drop any pack whose addition would cause total corpus size to exceed 5 MiB (pre-computed by summing YAML file sizes).
4. Minify YAML whitespace before final commit (remove unnecessary newlines, use compact YAML where safe).

---

## 9. ASCII Architecture Diagram

```
                           ┌─────────────────────────────────────────────────────┐
                           │                    USER SPACE                       │
                           │                                                     │
                           │  ~/.hermes/guild/          ~/.borg/traces.db         │
                           │  ┌─────────────────┐      ┌────────────────────┐   │
                           │  │ local packs/    │      │ traces table       │   │
                           │  │ <name>/pack.yaml│      │ (observe records)  │   │
                           │  └─────────────────┘      └────────────────────┘   │
                           │         ^                            ^              │
                           │         │                            │              │
                           │         │ borg_pull()                │ borg_observe │
                           │         │ (write)                     │ (write)      │
                           └─────────┼────────────────────────────┼──────────────┘
                                     │                            │
                           ┌─────────┴────────────────────────────┴──────────────┐
                           │              borg.core.search.borg_search()          │
                           │                                                       │
                           │  1. _fetch_index() ──────────────────────────────────┐ │
                           │     (remote guild-packs/index.json, 5-min cache)  │ │
                           │     Returns: {"packs": [...]}                        │ │
                           │                                                         │ │
                           │  2. _load_seed_index()  ──────────────────────────┐  │ │
                           │     (borg/seeds_data/index.json, memoized)        │  │ │
                           │     Returns: {"packs": [...], pack_count}         │  │ │
                           │     BORG_DISABLE_SEEDS=1 => {"packs": []}          │  │ │
                           │                                                         │ │
                           │  3. Extend all_packs with seed packs                │  │
                           │     (dedup: local > remote > seed)                   │  │
                           │                                                         │ │
                           │  4. Local pack scan                                   │  │
                           │     BORG_DIR/*/pack.yaml + BORG_DIR/packs/*.yaml     │  │
                           │     Append as source="local"                           │  │
                           │                                                         │ │
                           │  5. Trace surfacing (v3.2.4)                          │  │
                           │     TraceMatcher.find_relevant(query) → ~/.borg/     │  │
                           │     Append as source="trace"                          │  │
                           │                                                         │ │
                           │  6. Text search (mode=text, default)                  │  │
                           │     for pack in all_packs:                            │ │
                           │       searchable = name + problem_class + phases     │ │
                           │       if query in searchable: matches.append(pack)    │ │
                           │                                                         │ │
                           │  7. (Optional) Semantic search (mode=semantic/hybrid) │  │
                           │     SemanticSearchEngine.search(query)                │  │
                           │     Falls back to text if engine unavailable         │  │
                           │                                                         │ │
                           │  8. Reputation re-ranking (if requesting_agent_id)   │  │
                           │     Tier differential boost + adoption boost          │  │
                           │                                                         │ │
                           │  9. Return {"success": True, "matches": [...]}      │ │
                           │                                                       │ │
                           └───────────────────────────────────────────────────────┘
                                              ^
                                              │
                           ┌─────────────────┴────────────────────────┐
                           │  borg CLI / MCP server                    │
                           │                                           │
                           │  borg search <query> [--mode text|semantic│
                           │                     hybrid] [--no-seeds]│
                           │                                           │
                           │  borg CLI → _cmd_search()                  │
                           │  MCP → borg_search() in mcp_server.py     │
                           └───────────────────────────────────────────┘

  WHEEL CONTENTS (read-only, shipped with package):
  ┌─────────────────────────────────────────────────────────────────┐
  │  borg/seeds_data/                                               │
  │    index.json         # precomputed, created at build time     │
  │    VERSION             # "seeds-1.0.0-YYYY-MM-DD"              │
  │    packs/              # 500 YAML files (v3.3.0 target)        │
  │      <id>.yaml         # workflow_pack schema                  │
  │    .license_audit/     # one .license.json per pack             │
  └─────────────────────────────────────────────────────────────────┘

  DATA FLOW SUMMARY:
  ┌──────────┐     ┌───────────────┐     ┌──────────────┐     ┌──────────────┐
  │ seeds/   │────>│ _load_seed_    │────>│ all_packs    │────>│ text search  │
  │ index.json│    │ index()       │     │ (merged)     │     │ (token match)│
  └──────────┘     └───────────────┘     └──────────────┘     └──────┬───────┘
  ┌──────────┐     ┌───────────────┐     ┌──────────────┐            │
  │ remote/  │────>│ _fetch_index()│────>│ (dedup +    │            │
  │ index.json│    │ (5-min cache) │     │  local append)           │
  └──────────┘     └───────────────┘     └──────────────┘            │
  ┌──────────┐     ┌───────────────┐     ┌──────────────┐            │
  │ local/   │────>│ glob scan     │────>│ (dedup)      │            │
  │ pack.yaml│    │ BORG_DIR/     │     └──────────────┘            │
  └──────────┘     └───────────────┘                                 │
  ┌──────────┐     ┌───────────────┐     ┌──────────────┐            │
  │ traces/ │────>│ TraceMatcher   │────>│ trace hits    │──────────>┤
  │ traces.db│   │ .find_relevant │     │ (appended)    │            │
  └──────────┘     └───────────────┘     └──────────────┘            │
                                                                    │
                           ┌────────────────────────────────────────┘
                           │
                           v
                    ┌──────────────┐
                    │ JSON result │
                    │ to CLI/MCP  │
                    └──────────────┘
```

---

## 10. Implementation Roadmap

### Phase 0 — Ship Blockers (Day 1, ~2.5 hours)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| SB-01 | Fix `setup-claude` to emit `sys.executable` instead of `"python"` in MCP config | 30 min | None | `borg setup-claude` produces config with existing, valid `python` path; verified on Ubuntu 24 without `python` binary |
| SB-02 | Delete `docs/EXTERNAL_TESTER_GUIDE.md`; create `docs/TRYING_BORG.md` with correct `pip install agent-borg` commands | 1 hr | None | `grep -ri 'guild-packs\|guildpacks\|guild-mcp' docs/` returns 0 hits outside audit artifacts |
| SB-03 | Rename `--format` argparse choices to `{cursor, cline, claude, windsurf, all}` with backward-compatible aliases for old names | 45 min | None | All four `borg generate <pack> --format {cursor, cline, claude, windsurf}` exit 0 |
| SB-04 | Update all `pyproject.toml` `[project.urls]` to `agent-borg`; full-file grep for any remaining stale naming | 15 min | None | `pip show agent-borg \| grep -i url` shows zero `guild-packs` substrings |

**Exit gate**: All 4 SB acceptance tests pass. No code leaves this phase broken.

---

### Phase 1 — Seed Corpus Infrastructure (Day 1, ~6 hours)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| 1.1 | Create `borg/seeds_data/index.json` precomputed index over existing 17 `.md` frontmatter files; add `SEEDS_DIR` and `_load_seed_index()` to `borg/core/uri.py` | 2 hr | None | `_load_seed_index()` returns valid dict with `pack_count >= 17`; memoization works; `BORG_DISABLE_SEEDS=1` returns empty |
| 1.2 | Wire `_load_seed_index()` into `borg_search()` in `borg/core/search.py` after `_fetch_index()` | 1 hr | 1.1 | `pytest borg/tests/` green with and without seeds; seed packs appear in search results on empty HOME |
| 1.3 | Add `--no-seeds` flag to `borg search` subparser; plumb `BORG_DISABLE_SEEDS=1` env var through to `_load_seed_index()` | 1 hr | 1.2 | `borg search <query> --no-seeds` returns 0 seed hits; `BORG_DISABLE_SEEDS=1 borg search <query>` returns 0 seed hits |
| 1.4 | Mark seed rows in `borg search` output with `(seed)` suffix; update `borg list --seeds` to show only seeds | 1 hr | 1.2 | `borg search <query>` output distinguishes seed vs local vs remote packs |
| 1.5 | Create `borg/seeds_data/VERSION` file with `seeds-1.0.0-YYYY-MM-DD` | 30 min | None | `borg --version` includes seed version string |

**Exit gate**: Phase 1 tests (Section 11) all pass with the 17 existing packs. C3 prototype can now begin.

---

### Phase 2 — C3 Prototype (Day 1-2, ~8 hours including curation)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| 2.1 | Extract 50 seed packs from SWE-bench Verified gold patches (Django subset) | 4 hr | 1.1 | 50 YAML files in `borg/seeds_data/packs/` conforming to schema; every pack has valid `.license.json` sibling |
| 2.2 | Build `borg/seeds_data/index.json` over 50 packs; verify `_load_seed_index()` returns `pack_count=50` | 1 hr | 2.1 | `python -c "from borg.core.uri import _load_seed_index; print(_load_seed_index()['pack_count'])"` prints `50` |
| 2.3 | C3 replay: 15 runs x 20 iterations, MiniMax-M2.7, new condition C3_borg_seeded_public | 2 hr, ~$0.30 | 2.2 | Primary: "borg returned content" rate >= 12/15 runs return >= 1 seed match. If < 12/15, pause and redesign before proceeding |
| 2.4 | If C3 passes: run full curation to K=200 packs across 6 public sources (SWE-bench, GitHub Advisories, CPython issues, Django, Flask, SQLAlchemy) | 12 hr | 2.3 | 200 packs total; every pack has allowlist license + source_url + `.license.json`; corpus size <= 5 MiB |

**Exit gate**: C3 primary criterion >= 12/15. If fails: architecture review before continuing.

---

### Phase 3 — Integration and High-Priority Fixes (Day 2, ~6 hours)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| 3.1 | HIGH-02: Replace `guild://` with `borg://` in CLI help strings (keep parser accepting both) | 30 min | None | All help strings say `borg://`; `guild://` URIs still resolve |
| 3.2 | HIGH-03: Add `--success` validation to `feedback-v3` (reject non yes/no strings) | 15 min | None | `borg feedback-v3 --pack x --success garbage` exits 1 with error |
| 3.3 | HIGH-04: Fix `borg debug` exit code to return non-zero when no match | 15 min | None | `borg debug 'zzzzzzzzz'` exits 1 (not 0) |
| 3.4 | HIGH-05: Investigate `borg_suggest {}` returns empty; fix or remove from `tools/list` | 2 hr | None | `borg_suggest` with valid trigger returns non-empty or is removed |
| 3.5 | HIGH-06: `git mv borg/seeds_data/guild-autopilot borg/seeds_data/borg-autopilot` + content update | 45 min | None | All `guild` references in shipped `borg-autopilot/SKILL.md` replaced with `borg` |
| 3.6 | Run full `pytest borg/tests/` suite; fix any failures | 2 hr | 3.1-3.5 | 100% pass |

---

### Phase 4 — Acceptance Testing (Day 2-3, ~4 hours)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| 4.1 | Run 50-query cold-start benchmark (pre-registered, diverse: Python errors, bash, git, Docker) on fresh HOME | 2 hr | Phase 2 (K=200 minimum) | G1 >= 40/50, G2 >= 47/50 |
| 4.2 | Run ship-gate script (Section 12 of E2E audit) | 30 min | SB-01..SB-04 landed | All acceptance criteria exit 0 |
| 4.3 | Verify wheel size: `python -m build --wheel && ls -la dist/*.whl` | 15 min | Phase 2 complete | Wheel size delta <= 5 MiB |
| 4.4 | Run G4 (existing tests green) | 30 min | Phase 3.6 | `pytest borg/tests/` 100% pass |

---

### Phase 5 — Release (Day 3, ~2 hours)

| # | Task | Effort | Dependency | Success Criteria |
|---|---|---|---|---|
| 5.1 | Cut `3.3.0` tag; upload to TestPyPI | 30 min | Phase 4 complete | Wheel on TestPyPI, all G1-G7 metrics visible |
| 5.2 | Verify TestPyPI install: `pip install --index-url https://test.pypi.org/simple/ agent-borg==3.3.0` | 15 min | 5.1 | Installs cleanly; `borg search django` returns >= 1 seed hit |
| 5.3 | Promote to PyPI as `3.3.0` | 15 min | 5.2 | PyPI page clean; no `guild-packs` references remain |
| 5.4 | Update README.md to advertise cold-start fix + new MCP setup | 30 min | 5.3 | README reflects v3.3.0; `borg setup-claude` example works |

---

## 11. Design Decision Log

### D1 — Cold-start fix strategy: Option A (wheel-bundled) over Options B/C/D

**Decision**: Ship a curated seed corpus inside the wheel at `borg/seeds_data/packs/`, read-only, merged into search at query time.

**Reason**: The only option that ships a working product to an offline, cold, headless VM on the first `borg search` call. Option B requires a human to grant consent (headless installs cannot). Option C requires network on first run (breaks CI/air-gapped). Option D (LLM synthesis) fails the HN/PhD review bar and has contested license status.

**Alternatives considered**:
- Option B (first-run wizard scanning local history): rejected for privacy risk and zero cold-user coverage.
- Option C (federated fetch from signed repo): rejected for network dependency and signing key story with no current owner.
- Option D (LLM-synthesized packs): rejected for lying-confidently risk, license ambiguity, and cost.
- Option E (do nothing): rejected because the P1.1 experiment proved the problem exists and does not self-fix.

**Why not also bundle the existing 17 `.md` files as-is?**: The existing files in `borg/seeds_data/*.md` are YAML-frontmatter-only and the classifier path (`pack_taxonomy._get_skills_dir()`) already reads them. The cold-start gap is specifically that `borg_search` (the public search API) does not read from this directory — the classifier path is a different code path (`debug_error`, not `borg_search`). Adding the packs as proper YAML files under `seeds_data/packs/` and wiring `_load_seed_index()` into `borg_search` closes the exact gap.

---

### D2 — K = 500 packs (starting target, not a fixed commitment)

**Decision**: Target K=500 packs for v3.3.0 as a power-style back-of-envelope estimate, validated empirically by the Phase 2 prototype.

**Reason**: G1 requires K >= 161 at p_cov=0.01; G2 requires K >= 299. Rounding up to 500 accounts for correlated overlap between related problem classes. This is a starting estimate, not a statistically derived number. The prototype must validate it.

**Alternatives considered**:
- K=200: plausible if p_cov is higher than estimated. Fallback if curation exceeds budget.
- K=1000: excessive for the estimated vocabulary coverage; costs more curation time without proportional G1/G2 improvement.

**Open question**: If K=50 prototype shows 40/50 on G1, p_cov is ~0.03-0.05 and K=200 suffices. If K=50 prototype shows 10/50, K=500 is also too small and the design must be revised.

---

### D3 — Precomputed `index.json` instead of scanning YAML on every search

**Decision**: Build `borg/seeds_data/index.json` at package build time (in `setup.py` or a pre-build hook), containing an array of pack summary dicts. `_load_seed_index()` reads this file, not the YAML files.

**Reason**: Scanning 500 YAML files on every `borg search` call is unnecessary overhead. The index is static (seed packs do not change between releases), so precomputing it is free. The `_init_cache()` path in `pack_taxonomy.py` already does this for the classifier — we apply the same pattern to search.

**Alternatives considered**:
- Lazy YAML scan on first search: adds latency to the first call.
- SQLite FTS5 bundle: rejected because the existing search path is an in-memory list scan and 500 items is sub-millisecond. Revisit at N > 2,000.

---

### D4 — `--no-seeds` opt-out, not opt-in

**Decision**: Seeds are included by default. Users who want a pristine cache can opt out via `--no-seeds` or `BORG_DISABLE_SEEDS=1`.

**Reason**: The cold-start failure (G1=0% on first install) is the primary adoption blocker. Defaulting to empty results means the fix is invisible to users who don't know to opt in. Making seeds the default aligns with the user's mental model: "borg should work out of the box."

**Alternatives considered**:
- Opt-in (seeds behind a flag): rejected because it leaves the cold-start problem intact for the default case.
- Seeds always included, never removable: rejected because power users who want a clean community-only index should have an escape hatch.

---

### D5 — `_load_seed_index()` memoized at import, not lazily

**Decision**: Memoize `_load_seed_index()` with `functools.lru_cache(maxsize=1)` at module import time.

**Reason**: Seed packs are immutable for the lifetime of a process. Reading the JSON from disk on every `borg_search` call is wasteful. Memoization gives O(1) subsequent calls.

**Implementation note**: The test fixture must call `cache_clear()` on the memoized function to invalidate between test runs. This is handled by `conftest.py` fixture setup.

---

### D6 — MDN (CC-BY-SA 2.5) excluded from allowed seed sources

**Decision**: MDN Web JavaScript error references are explicitly excluded as a seed source.

**Reason**: CC-BY-SA at any version is incompatible with bundling into an MIT/Apache-licensed wheel. The design doc originally listed MDN as a candidate source, but the CC-BY-SA license propagates to derived works. The wheel would need to be CC-BY-SA to distribute MDN content, which conflicts with the MIT license of `agent-borg`.

**Alternatives considered**:
- Rewrite MDN entries from scratch (clean-room): possible but time-intensive. Deferred to future work if MDN coverage is deemed critical.
- Use MDN under "fair use" for snippets: not a viable legal argument for a distributed software package.

---

### D7 — MiniMax-M2.7 for C3 replay, not MiniMax-Text-01

**Decision**: The C3 prototype replay uses MiniMax-M2.7, not MiniMax-Text-01.

**Reason**: P1.1 confirmed that MiniMax-Text-01 floor-effected on every task (stopped after 1-2 iterations, never called `read_file` or `write_file`). Replaying the C3 condition with the same model would produce the same floor effect — the retrieval will work but the agent will still terminate before using anything it retrieves. MiniMax-M2.7 has longer agent loops and is the appropriate model for validating the cold-start fix.

**Alternatives considered**:
- MiniMax-Text-01: rejected because it already failed on the same task set in P1.1.
- Claude Opus 4.6: rejected because it ceiling-effects on this task set (solves tasks regardless of borg), invalidating the comparison.

---

### D8 — `tier="seed"` ranks below `community`, above `none`

**Decision**: Seed packs are displayed with `tier="seed"` and are ranked below user-validated and community packs.

**Reason**: Seeds are a cold-start floor, not a ceiling. They should appear when no better match exists, but should not crowd out packs that have been validated by real usage. The existing ranking already has `author-validated` above `community`; `seed` slots in below `community`.

**Alternatives considered**:
- Seeds ranked equal to community: rejected because it gives unvalidated content equal standing with packs that have real usage evidence.
- Seeds hidden by default: rejected because the primary goal is cold-start visibility.

---

## 12. Failure Modes Matrix

| ID | Feature | Failure Mode | Likelihood | Severity | Detection | Mitigation |
|---|---|---|---|---|---|---|
| F1 | Seed corpus | Corrupted `index.json` causes `_load_seed_index()` to return `{}`; all searches return empty | LOW | HIGH | Phase 1 test `test_seed_index_loads_from_wheel` | Function returns `{"packs": []}` on JSON parse error, never raises; existing pytest suite catches malformed index |
| F2 | Seed corpus | One seed pack has non-allowlist license (e.g., CC-BY-SA slipped through curation) | MEDIUM | CRITICAL | CI license audit check (every pack requires `.license.json` on allowlist) | Allowlist CI gate; rejected packs not included in index.json |
| F3 | Seed corpus | Seed pack actively misleads agent (wrong resolution for a real error class) | MEDIUM | HIGH | Phase 0 prototype + C3 replay; spot-check of 10% of corpus | Seed packs tagged `tier="seed"` and `source="seed"`; ranking deprioritizes; user can `--no-seeds` |
| F4 | Seed corpus | Wheel size exceeds 5 MiB (G3 violation) | LOW | HIGH | CI `test_wheel_size_under_budget` | Minify YAML whitespace; fall back to K=200 if size budget exceeded |
| F5 | Seed corpus | PyPI yanked wheel after bad seed pack is discovered | LOW | HIGH | PyPI page monitoring; user bug reports | Emergency v3.3.1 patch release; `BORG_DISABLE_SEEDS=1` as temporary user mitigation |
| F6 | Search integration | `_load_seed_index()` not called (code path skipped due to exception) | LOW | CRITICAL | Phase 1 test `test_borg_search_returns_seed_hits_on_empty_store` | Exception in `_load_seed_index()` caught at call site; returns `{"packs": []}` |
| F7 | Search integration | Duplicate pack IDs between seed and local packs (local not preferred) | LOW | MEDIUM | Phase 1 test `test_local_pack_shadows_seed_pack` | Existing dedup logic in `search.py` lines 151-182 already prefers local; explicit test covers |
| F8 | CLI | `--no-seeds` flag plumbed incorrectly; seeds still appear | LOW | MEDIUM | Phase 1 test `test_no_seeds_flag_disables_seeds` | Explicit test covers both env var and flag |
| F9 | Ship blockers | SB-01 fix (`sys.executable`) still fails on some Python installs | MEDIUM | HIGH | Manual test on Ubuntu 24, macOS Python.org, pyenv | `shutil.which("borg-mcp")` as first choice before falling back to `sys.executable` |
| F10 | Ship blockers | SB-03 (`--format`) aliases don't cover all README examples | LOW | MEDIUM | README example commands tested in CI | Full coverage of README examples; backward-compatible aliases for old names |
| F11 | C3 prototype | C3 prototype fails G7 (< 12/15 "borg returned content") | MEDIUM | HIGH | C3 replay metrics | Pause and redesign before full curation spend; report findings in revision of this spec |
| F12 | Trace surfacing | TraceMatcher fails on malformed `traces.db` | LOW | LOW | Phase 1 test covers; try/except in search.py lines 293-319 | Exception caught and logged; search still returns pack results |
| F13 | Reputation engine | ReputationEngine raises exception during re-ranking | LOW | LOW | `search.py` lines 321-369 have broad try/except | Reputation is optional; search continues with text-order ranking |
| F14 | MCP server | `borg-mcp` entry point broken on installs without `python` symlink | HIGH | CRITICAL | SB-01 | `borg-mcp` is a console script entry point; it uses `sys.executable` directly, not `python` string |

---

## 13. Binary Pass/Fail Per Feature (G1-G7)

| ID | Goal | Binary Pass/Fail | Measurement |
|---|---|---|---|
| **G1** | Clean install: `borg search` returns >= 1 relevant result for 80% of 50-query benchmark | **PASS** if >= 40/50 queries return >= 1 match; **FAIL** otherwise | Automated benchmark fixture `borg/tests/test_seed_corpus.py::test_cold_start_benchmark_80_percent` |
| **G2** | Clean install: `borg search` returns >= 5 results for 95% of benchmark | **PASS** if >= 47/50 queries return >= 5 matches; **FAIL** otherwise | Automated benchmark fixture `test_cold_start_benchmark_5_hits_95_percent` |
| **G3** | Seed corpus adds <= 5 MiB to wheel (uncompressed) | **PASS** if `ls -la dist/*.whl` shows delta <= 5 MiB; **FAIL** otherwise | `test_wheel_size_under_budget` |
| **G4** | Existing `pytest borg/tests/` still green | **PASS** if pytest exit code 0; **FAIL** otherwise | `pytest borg/tests/ --tb=short` |
| **G5** | Every seed pack has traceable public source + MIT/Apache-2.0/CC0-compatible license | **PASS** if every `packs/*.yaml` has matching `.license.json` with allowlist SPDX license and resolvable `source_url`; **FAIL** otherwise | `test_license_audit_completeness` |
| **G6** | `--no-seeds` opt-out flag exists and is functional | **PASS** if `borg search x --no-seeds` returns 0 seed hits AND `BORG_DISABLE_SEEDS=1 borg search x` returns 0 seed hits; **FAIL** otherwise | `test_no_seeds_flag_disables_seeds` |
| **G7** | C3 replay: per-run "borg returned content" rate rises from 0/30 to >= 25/30 | **PASS** if C3 replay (15 runs x MiniMax-M2.7) shows >= 12/15 runs returning >= 1 seed match; **FAIL** otherwise | C3 replay JSONL logs + `test_c3_content_rate` |

**G1-G7 are a conjunction gate**: ALL must PASS for the v3.3.0 release. Any single FAIL blocks the release tag.

---

## 14. Evaluation Framework

### 14.1 Instruments

| Instrument | What It Measures | Owner | When |
|---|---|---|---|
| `borg/tests/test_seed_corpus.py` — 10 pytest tests | G1, G2, G3, G4, G5, G6 compliance | Engineer implementing Phase 1 | After every code change; gate for Phase 4 |
| 50-query cold-start benchmark fixture | G1, G2 | Engineer implementing Phase 2 | Phase 4 acceptance testing |
| C3 replay JSONL logs | G7 | Engineer running Phase 2.3 | Within 2 hours of Phase 2.3 start |
| Ship-gate shell script (Section 12 of E2E audit) | SB-01 through SB-04 compliance | Hermes orchestrator | End of Day 1 |
| `pip show agent-borg` | PyPI metadata cleanliness (SB-04) | Engineer | After PyPI upload |
| Manual Ubuntu 24 test (no `python` symlink) | SB-01 effectiveness | Engineer | After SB-01 fix |
| `python -X importtime -c "from borg.core.search import borg_search"` | Search import overhead | Engineer | Regression check for F7 |

### 14.2 Who Measures

| Role | Responsibility |
|---|---|
| **Implementing engineer** | Runs pytest suite, benchmark fixture, ship-gate script after each Phase |
| **Hermes orchestrator** | Runs final ship-gate before PyPI upload |
| **External reviewer (optional)** | Manual Ubuntu 24 + macOS Python.org test for SB-01 |

### 14.3 When

- **After Phase 0 (SB fixes)**: Run ship-gate script.
- **After Phase 1 (seed infrastructure)**: Run `test_seed_corpus.py` tests.
- **After Phase 2.3 (C3 replay)**: Report G7 metrics before Phase 2.4 authorization.
- **After Phase 4 (acceptance testing)**: Full benchmark + pytest + ship-gate.
- **After Phase 5 (PyPI upload)**: `pip show` + manual smoke test.

### 14.4 How

**Automated testing**:
```bash
# G4: existing tests
pytest borg/tests/ --tb=short -q

# G1/G2: cold-start benchmark
pytest borg/tests/test_seed_corpus.py::test_cold_start_benchmark_80_percent
pytest borg/tests/test_seed_corpus.py::test_cold_start_benchmark_5_hits_95_percent

# G3: wheel size
python -m build --wheel
ls -la dist/*.whl | awk '{print $5}'  # must be < 5MiB delta

# G5: license audit
python -c "from borg.core.uri import _load_seed_index; packs = _load_seed_index()['packs']; print(all(p.get('license') in ALLOWLIST for p in packs))"

# G6: opt-out
BORG_DISABLE_SEEDS=1 python -c "from borg.core.search import borg_search; print(borg_search('django'))"
```

**C3 replay**:
```bash
cd /root/hermes-workspace/borg
python docs/20260408-1003_scope3_experiment/run_single_task.py \
  --tasks 15 \
  --condition C3_borg_seeded_public \
  --model minimax-m2.7 \
  --max-iters 20 \
  --output c3_replay_results.jsonl
```

### 14.5 Pre-Registration

The 50-query benchmark fixture is pre-registered in `borg/tests/fixtures/cold_start_queries.json`. It contains 50 diverse queries:

```
django migration error
flask import error
pytest fixture not found
git merge conflict
docker build failed
kubernetes pod crash
python type error
javascript null reference
rust borrow checker
go panic
async timeout
database connection refused
permission denied error
schema drift
circular import
missing dependency
null pointer exception
configuration error
race condition
migration state desync
... (30 more, see fixture file)
```

Queries must be diverse across: frameworks (Django, Flask, Python, JS, Rust, Go, Docker, K8s), error types (ImportError, TypeError, OperationalError, PermissionError, TimeoutError), and task types (debug, setup, migrate, test, deploy).

### 14.6 Statistical Rigor

- No statistical claims are made from the 50-query benchmark. It is a binary acceptance test, not a hypothesis test.
- G7 uses Clopper-Pearson 95% confidence intervals for the "borg returned content" rate, same method as P1.1.
- The pre-registered decision rule from P1.1 applies to G7: `>= 12/15 runs return >= 1 match` is the primary threshold.
- No p-hacking: the benchmark queries are fixed before the test runs, not selected post-hoc to favor a particular result.

---

## 15. Open Questions (Resolve in Review)

| ID | Question | Recommendation |
|---|---|---|
| O1 | Should seed packs be versioned independently from `agent-borg`? | No. Tied to minor release cadence (quarterly). Independent versioning adds release management overhead with no user benefit at K=500. |
| O2 | What is the maximum acceptable latency for first `borg search`? | Target: < 200ms on cold start (empty HOME). The `_load_seed_index()` memoization and 500-item scan should keep this well under 100ms. |
| O3 | Should seed pack `success_count` and `evidence` be pre-seeded with zero, or should the corpus ship with evidence from curation? | Ship with evidence from curation source (e.g., SWE-bench patch success rate). Zero evidence makes seeds appear untrusted. |
| O4 | Does `tier="seed"` affect reputation engine behavior? | Seeds should not appear in reputation calculations (they are not authored by agents). The reputation engine ignores `source=="seed"` packs. |

---

## 16. Related Documents

| Document | Relationship |
|---|---|
| `FIRST_USER_E2E_AUDIT_20260409.md` | Evidence base for ship blockers SB-01 through SB-04 |
| `COLD_START_SEED_CORPUS_DESIGN.md` | Detailed design of Option A; this spec references specific sections |
| `P1_MINIMAX_REPORT.md` | Evidence that cold-start is the dominant failure mode; floor-effect data |
| `SYNTHESIS_AND_SHIP_PLAN_20260409.md` | Ship plan, effort estimates, and team assignments |
| `CONTEXT_DOSSIER.md` | This session's orchestrator context document |
| `pyproject.toml` | Wheel size budget (G3 <= 5 MiB); package data declaration for `seeds_data/**` |
| `borg/core/search.py` | Primary search implementation; integration point for `_load_seed_index()` |
| `borg/core/uri.py` | URI resolution, index fetching, location of new `_load_seed_index()` |
| `borg/core/pack_taxonomy.py` | Existing seed-loading infrastructure (`_get_skills_dir()`) |

---

*Spec status: DRAFT — for AB review. Do not implement until approved.*
*Team BLUE — subagent, MiniMax-M2.7*
*Generated: 2026-04-09 14:35 UTC*
