# Phase 0 Day 1  State after migration

**Date:** 2026-04-16
**Branch:** phase-0-honest
**Backup:** ~/.borg/traces.db.pre-phase0.20260416 (528 KB)

## DB state

| Table | Count | Sources |
|---|---|---|
| traces | 172 | auto (171), feedback-v3 (1) |
| seed_traces | 156 | seed_pack (91), golden_seed (20), curated (45) |

## Invariants

- **I3 (no synthetic in traces):** PASS (0 leaked)
- **I4 (no PII in DB):** not yet asserted  Day 2 task
- **I1, I2, I5:** Phase 1 (require borg-bench harness)

## What was not done in Day 1 (Day 2 tasks)

1. Application-layer seed guard in save_trace (raise on source IN seed_pack/golden_seed/curated)
2. find_relevant() tiered retrieval (query traces first, fall back to seed_traces, label source_tier)
3. test_invariants.py committed to borg/tests/
4. README updated to remove unverified performance claims
5. PRD v4, Build Spec v2, Design Review committed to docs/
6. Tag v3.4.0-honest

## Schema spec corrections applied

- Primary key is `id`, not `trace_id`  applied inline, Build Spec v2 3 needs revision
- `causal_intervention` column already exists  no need to add `intervention_type` (spec revision)
- Two new source categories discovered: `curated` (treated as non-organic in migration) and `feedback-v3` (treated as organic)

## Incident

- Pre-existing trigger `cascade_delete_trace_index` blocked DELETE due to `OLD.trace_id` reference (column is `id`)
- Dropped the trigger (was functionally dead  always deleted 0 rows)
- Phase 1: reintroduce with corrected `OLD.id` reference
