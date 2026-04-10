# Cold-Start 50-Query Benchmark Results

**Date:** 2026-04-09
**Model:** MiniMax-M2.7 via MiniMax provider
**Environment:** ZERO-STATE (fresh HERMES_HOME)
**Borg Version:** 3.2.4

---

## Summary

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| G1 (>=1 result) | 0/50 | >=40/50 | **FAIL** |
| G2 (>=5 results) | 0/50 | >=47/50 | **FAIL** |

---

## Verdict

**COLD-START GAP CONFIRMED BY EMPIRICAL DATA.**

In a ZERO-STATE environment (fresh HERMES_HOME, no pre-existing packs), ALL 50 queries returned 0 results. The borg search command returns "No packs found." for every query, regardless of content.

### Root Cause
The seed packs located at `/root/hermes-workspace/borg/borg/seeds_data/` are **NOT automatically loaded** into a fresh HERMES_HOME. When HERMES_HOME is set to a new empty directory, borg has:
- No local packs
- No guild references
- Nothing to search

### Evidence
- Default HERMES_HOME (`~/.hermes`): `borg search "django circular dependency"` → 10 packs found
- Fresh HERMES_HOME (`/tmp/borgtest`): `borg search "django circular dependency"` → "No packs found"
- `borg list` in fresh HERMES_HOME: shows 0 local packs
- Seeds data exists at `borg/seeds_data/` but is never initialized/loaded

---

## Raw Query Results

| QID | Category | Difficulty | Expected Problem Class | Hits | G1 | G2 |
|-----|----------|------------|------------------------|------|----|----|
| 1 | django | easy | circular_dependency | 0 | FAIL | FAIL |
| 2 | django | easy | configuration_error | 0 | FAIL | FAIL |
| 3 | django | medium | migration_state_desync | 0 | FAIL | FAIL |
| 4 | django | medium | missing_foreign_key | 0 | FAIL | FAIL |
| 5 | django | easy | null_pointer_chain | 0 | FAIL | FAIL |
| 6 | django | medium | schema_drift | 0 | FAIL | FAIL |
| 7 | django | hard | circular_dependency | 0 | FAIL | FAIL |
| 8 | django | hard | migration_state_desync | 0 | FAIL | FAIL |
| 9 | django | medium | type_mismatch | 0 | FAIL | FAIL |
| 10 | django | easy | permission_denied | 0 | FAIL | FAIL |
| 11 | django | medium | timeout_hang | 0 | FAIL | FAIL |
| 12 | django | hard | schema_drift | 0 | FAIL | FAIL |
| 13 | python | easy | missing_dependency | 0 | FAIL | FAIL |
| 14 | python | medium | import_cycle | 0 | FAIL | FAIL |
| 15 | python | easy | null_pointer_chain | 0 | FAIL | FAIL |
| 16 | python | easy | type_mismatch | 0 | FAIL | FAIL |
| 17 | python | easy | missing_dependency | 0 | FAIL | FAIL |
| 18 | python | medium | import_cycle | 0 | FAIL | FAIL |
| 19 | python | medium | null_pointer_chain | 0 | FAIL | FAIL |
| 20 | python | medium | null_pointer_chain | 0 | FAIL | FAIL |
| 21 | python | easy | permission_denied | 0 | FAIL | FAIL |
| 22 | python | hard | race_condition | 0 | FAIL | FAIL |
| 23 | python | medium | timeout_hang | 0 | FAIL | FAIL |
| 24 | python | easy | missing_dependency | 0 | FAIL | FAIL |
| 25 | python | medium | type_mismatch | 0 | FAIL | FAIL |
| 26 | python | hard | import_cycle | 0 | FAIL | FAIL |
| 27 | python | easy | null_pointer_chain | 0 | FAIL | FAIL |
| 28 | git | medium | schema_drift | 0 | FAIL | FAIL |
| 29 | docker | hard | configuration_error | 0 | FAIL | FAIL |
| 30 | bash | easy | permission_denied | 0 | FAIL | FAIL |
| 31 | git | medium | race_condition | 0 | FAIL | FAIL |
| 32 | docker | medium | timeout_hang | 0 | FAIL | FAIL |
| 33 | bash | easy | permission_denied | 0 | FAIL | FAIL |
| 34 | git | hard | timeout_hang | 0 | FAIL | FAIL |
| 35 | docker | hard | timeout_hang | 0 | FAIL | FAIL |
| 36 | flask | medium | type_mismatch | 0 | FAIL | FAIL |
| 37 | pytest | medium | null_pointer_chain | 0 | FAIL | FAIL |
| 38 | flask | medium | import_cycle | 0 | FAIL | FAIL |
| 39 | pytest | easy | missing_dependency | 0 | FAIL | FAIL |
| 40 | celery | hard | timeout_hang | 0 | FAIL | FAIL |
| 41 | sqlalchemy | medium | null_pointer_chain | 0 | FAIL | FAIL |
| 42 | fastapi | medium | configuration_error | 0 | FAIL | FAIL |
| 43 | pytest | hard | schema_drift | 0 | FAIL | FAIL |
| 44 | celery | medium | timeout_hang | 0 | FAIL | FAIL |
| 45 | flask | easy | timeout_hang | 0 | FAIL | FAIL |
| 46 | race | hard | race_condition | 0 | FAIL | FAIL |
| 47 | python | easy | timeout_hang | 0 | FAIL | FAIL |
| 48 | bash | easy | permission_denied | 0 | FAIL | FAIL |
| 49 | python | hard | race_condition | 0 | FAIL | FAIL |
| 50 | database | hard | race_condition | 0 | FAIL | FAIL |

---

## Technical Details

### What Returned Nothing
**ALL 50/50 queries returned 0 results.**

### Environment Setup
- HERMES_HOME: Fresh temp directory (`/tmp/borg_baseline_xxx`)
- HOME: Same as HERMES_HOME
- No pre-existing borg data
- Seeds data at `borg/seeds_data/` exists but is NOT automatically loaded

### Contrast: With Existing Hermes Home
When using the default `~/.hermes` (which has been used/populated), the same queries return results:
- `borg search "django circular dependency"` → 10 packs found

### Conclusion
The cold-start gap is 100% confirmed. A fresh borg installation with zero-state is completely non-functional for search. The seeds data exists but is never initialized, leaving the system dead on first use.