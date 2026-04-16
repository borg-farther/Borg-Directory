# `causal_intervention` Backfill Plan (B4)

## Context

The `traces` table schema includes `causal_intervention TEXT`. Per `BORG_TRACE_FORMAT_v1` (draft), this column should record the concrete action that resolved the error (e.g., `"pip install flask"`, `"restart gunicorn"`, `"add Content-Type: application/json header"`). This is the field retrieval-consumers most want to surface to an agent  it's the "what actually worked" answer.

As of v3.4.0-honest, the 172 organic traces in `traces` have inconsistent population of this column. Agents writing traces did not reliably fill it.

## Current state (2026-04-16)

```sql
SELECT
  COUNT(*) AS total,
  COUNT(causal_intervention) AS populated,
  SUM(CASE WHEN causal_intervention = '' OR causal_intervention IS NULL THEN 1 ELSE 0 END) AS empty
FROM traces;
```

Run this on VPS to get the actual numbers. Expected pattern: majority empty, minority populated with unstructured free text.

## Approach  three-phase backfill

### Phase A  Audit (1 hour, read-only)

1. Count populated vs empty (query above).
2. For populated rows: inspect 10 samples. Are they structured? Are they useful? Is there a de-facto pattern?
3. Decide: does the field carry its intended signal, or is it noise?

Decision gate: if >50% empty AND populated ones are low-signal, proceed to Phase B. If populated ones are actually useful, skip to Phase C.

### Phase B  Regeneration via LLM (4-6 hours, one-shot script)

For each empty-`causal_intervention` row in `traces`:
1. Feed `task_description` + `approach_summary` + `files_modified` to an LLM with a strict schema prompt:
   > "Given this trace, extract the concrete intervention that resolved the problem as a single imperative sentence. If unclear, return `null`."
2. Write result back to `causal_intervention`.
3. Log to `docs/phase-1/causal_intervention_backfill_YYYYMMDD.log`.

Cost estimate: 172 rows  ~500 tokens each  Haiku pricing = ~$0.05. Trivial.

Script location: `borg/tools/backfill_causal_intervention.py` (not yet written).

### Phase C  Enforcement at write time (1 hour, code change)

Add a guard in `save_trace`:
- If `source = 'auto'` AND `causal_intervention` is empty/null, log a WARNING (not block  organic writes must not fail).
- Future: `BORG_TRACE_FORMAT_v1` schema validation makes this a hard requirement for Phase 2.

## Risk

- **LLM noise.** Regenerated `causal_intervention` is best-effort. Users should not treat it as authoritative.
- **Schema drift.** If `BORG_TRACE_FORMAT_v1` changes the semantics of this field, backfill needs redo.
- **Cost if scaled.** 172 rows is nothing. At 10,000+ rows, re-run cost matters. Batch via Haiku.

## Decision

Phase B deferred to Phase 1. Not a Phase 0 blocker. Recorded here so it doesn't get forgotten.

## Success criteria

- >80% of organic `traces` rows have a populated, non-trivial `causal_intervention`.
- Retrieval consumers start using the field (MCP response includes it in the primary "answer" rendering).
- `BORG_TRACE_FORMAT_v1` schema validation enforces presence for new writes.
