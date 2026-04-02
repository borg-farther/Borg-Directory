# E1b Real-Bugs Dogfood: Report

**Date:** 2026-04-02  
**Task:** Test borg guidance against real open-source Django/Flask bugs  
**Output:** `/root/hermes-workspace/borg/eval/e1b_real_bugs/`

---

## Executive Summary

E1b tests whether borg guidance helps on **real** open-source bugs (Django/GitHub), not synthetic SWE-bench tasks.

**Status:** ⚠️ BLOCKED — The borg `packs/` directory is empty, so `borg_search()` returns no matches. Cannot run the actual dogfood test.

---

## What Was Done

### 1. Bug Collection
Collected **15 real Django bugs** from SWE-bench lite in `/root/hermes-workspace/borg/dogfood/swebench_tasks/`:

| Instance ID | Problem | Error Type | Files Touched |
|------------|---------|------------|---------------|
| django__django-11095 | ModelAdmin.get_inlines() hook | AdminInline | admin/options.py |
| django__django-11477 | translate_url() URL routing bug | Regex, URLRouting | urls/resolvers.py |
| django__django-11728 | simplify_regexp() trailing groups | Regex | admindocs/utils.py |
| django__django-11790 | AuthenticationForm maxlength | Unknown | auth/forms.py |
| django__django-13315 | limit_choices_to duplicates | TypeError, Regex | forms/models.py |
| django__django-13809 | runserver --skip-checks | Unknown | management/commands/runserver.py |
| django__django-14500 | Squashed migration unapplied | Unknown | migrations/executor.py |
| django__django-14559 | bulk_update() return value | Unknown | models/query.py |
| django__django-14725 | Model formsets disallow new | Unknown | forms/models.py |
| django__django-15037 | Foreign key inspectdb | Unknown | management/commands/inspectdb.py |

### 2. Error Type Distribution
- **Unknown:** 11 bugs
- **Regex:** 3 bugs
- **AdminInline:** 1 bug
- **URLRouting:** 1 bug
- **Concurrency:** 1 bug
- **TypeError:** 1 bug

### 3. Component Distribution
- `django/db/` — 6 bugs (migrations, models, query)
- `django/contrib/admin/` — 4 bugs
- `django/forms/` — 2 bugs
- `django/core/` — 2 bugs (management commands)

---

## E1b Pre-Registered Pass Criteria

From `BORG_PACK_AUTO_GENERATION_PRD.md` Section E1b:

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| Guidance relevance | ≥ 2/3 devs find packs "helpful" or "very helpful" | ❌ CANNOT TEST |
| Investigation trail accuracy | ≥ 2/3 times, suggested files were actually relevant | ❌ CANNOT TEST |
| Resolution match | ≥ 1/3 times, suggested resolution was actual fix | ❌ CANNOT TEST |
| Would use again | 3/3 | ❌ CANNOT TEST |

---

## Infrastructure Issue

**Problem:** `borg_search()` returns `{"success": true, "matches": [], ...}` for all queries.

**Root Cause:** The borg packs directory is empty:
```
/root/hermes-workspace/borg/packs/    ← 0 packs (empty)
~/.hermes/skills/                     ← Has skills but NOT packs
```

**Search index:** The packs directory should contain pack YAML files that `borg_search()` indexes. Currently there are none.

---

## Files Created

| File | Purpose |
|------|---------|
| `eval/e1b_real_bugs/run_e1b.py` | Main E1b evaluation script (needs packs) |
| `eval/e1b_real_bugs/analyze_bugs.py` | Bug analysis without pack dependency |
| `eval/e1b_real_bugs/analyze_tasks.py` | Task data analysis helper |
| `eval/e1b_real_bugs/test_import.py` | Import verification |
| `eval/e1b_real_bugs/test_search.py` | Search functionality test |
| `eval/e1b_real_bugs/results/e1b_analysis.json` | Bug analysis data |

---

## Recommendation

To complete E1b, we need:
1. **Populate the packs directory** with seed packs for the error types found
2. **Re-run:** `python eval/e1b_real_bugs/run_e1b.py`

Priority error types to create packs for based on this analysis:
1. **Regex** (3 bugs) — highest signal
2. **URLRouting** (1 bug but clear pattern)
3. **TypeError** (1 bug)
4. **AdminInline** (1 bug)
5. **General "Unknown"** — need better classification

---

## Next Steps

1. Run `python eval/e1b_real_bugs/analyze_bugs.py` for full bug details
2. Create packs for high-priority error types
3. Populate `packs/` directory with pack YAML files
4. Re-run E1b evaluation
5. Results will be saved to `eval/e1b_real_bugs/results/e1b_results.json`