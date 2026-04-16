# Phase 0 Migration Log  2026-04-16

## What happened

1. Backup: ~/.borg/traces.db.pre-phase0.20260416 (528 KB)
2. Initial migration SQL failed on DELETE due to pre-existing broken trigger `cascade_delete_trace_index` which referenced OLD.trace_id (non-existent column; real column is `id`).
3. Fix: dropped the broken trigger (it was functionally dead anyway  would silently delete 0 rows). Re-ran DELETE.

## Final state

- traces: 172 organic (source IN ('auto','feedback-v3'))
- seed_traces: 156 non-organic (source IN ('seed_pack','golden_seed','curated'))
- Invariant I3 holds: 0 non-organic rows in traces table

## Known limitations

- trace_file_index may have orphaned references to traces now in seed_traces. Phase 1 cleanup.
- retrieval path (find_relevant) still queries traces only  seed_traces fallback is Day 2.
- cascade_delete_trace_index trigger dropped. Reintroduce with correct column name (OLD.id) in Phase 1.
