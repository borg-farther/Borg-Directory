# 20260408-0623 Borg Debug Classifier — Context Dossier

This is the SHARED CONTEXT every team (Red / Blue / Green / Chief Architect)
reads before producing their report. Treat it as ground truth.

## Background
- Product: `agent-borg` v3.2.1 on PyPI (775+ downloads, 2862 tests).
- Killer feature being marketed: `borg debug "<error message>"` — returns
  structured guidance (root cause, investigation trail, resolution sequence,
  anti-patterns, evidence stats) for any error a developer hits.
- Phase A focus is winning SWE-bench-style Python/Django problems. 9/10 there.
- Reality check from 3 dogfood teams that came back today:
    1. CRITICAL BUG: `borg debug` gives WRONG advice for non-Python errors.
       Rust `borrow of moved value` and Docker `no space left on device`
       both get matched to `schema_drift` → tells the user to run
       `python manage.py makemigrations`. Worse than no answer.
    2. React/TypeScript: 0/3 errors matched. Total blind spot for the
       biggest frontend ecosystem on the planet.
    3. Reputation risk: anyone trying borg right now who isn't a
       Python/Django dev gets actively harmful output.

## Reproductions captured 20260408-0623 (run on the live wheel, v3.2.1)

```
$ borg debug "error[E0382]: borrow of moved value: \`x\`"
[schema_drift] (python)
ROOT CAUSE: schema_mismatch — The Python model and the actual database schema have diverged …
RESOLUTION SEQUENCE: 1. create_migration  Command: python manage.py makemigrations …
```

```
$ borg debug "Error: ENOSPC: no space left on device"
[schema_drift] (python)  ← same wrong answer
```

```
$ borg debug "TS2322: Type 'string' is not assignable to type 'number'"
No matching problem class found.
```

```
$ borg debug "Hydration failed because the initial UI does not match what was rendered on the server"
No matching problem class found.
```

## Root cause of the bug (one line)
`borg/borg/core/pack_taxonomy.py` line 83:
```python
("Error", "schema_drift"),   # GENERIC FALLBACK
```
A bare substring `"Error"` is the LAST entry in `_ERROR_KEYWORDS` — virtually
every error message in any language contains the substring `"Error"`, so
classification short-circuits to `schema_drift` with **no confidence score
and no language gating**. There is also no language detection step at all
and no per-language pack catalogue.

## Current taxonomy (full list of problem_classes)
```
circular_dependency, null_pointer_chain, missing_foreign_key,
migration_state_desync, import_cycle, race_condition,
configuration_error, type_mismatch, missing_dependency,
timeout_hang, schema_drift, permission_denied
```
Every pack is Python/Django flavoured.

## Pipeline (today)
```
error_message ──► classify_error()  ──► first substring hit wins, returns problem_class str | None
                ──► load_pack_by_problem_class()  ──► dict | None
                ──► render_pack_guidance()  ──► CLI text
```
Notes:
- No confidence score returned anywhere.
- No language inference. No framework inference.
- No "I don't know" gracefully wrapped pack.
- No telemetry on miss / mis-fire — bad answers are silent.
- `seeds_data/` ships only Python packs in the wheel.

## Constraints / non-negotiables from AB
1. VERIFY-BEFORE-SHIP: every claim must be backed by a measurable test.
2. Multi-agent adversarial review → spec → implement to PhD/Google level.
3. Cost-derived thresholds. No vanity metrics.
4. Statistical rigour, academic eval methodology.
5. Confidence gating + more problem classes (JS/TS, Rust, Go, Docker, K8s).
6. Don't ship features whose accuracy we haven't measured.
7. Backwards compatible — Python/Django path stays at >= current quality.
8. Reputation matters more than coverage. A confident wrong answer is the
   worst outcome. Better to say "we don't know yet" than to mis-route.

## Ecosystem reality (rough envelope, AB has not asked us to verify these — just for sizing)
- Python ≈ 1 of the top 3 languages on Stack Overflow tags.
- JavaScript/TypeScript dominate frontend. React is the #1 framework by usage.
- Rust adoption is small in absolute LOC but very high among the kind of
  developers most likely to install a CLI like borg.
- Docker/K8s errors are platform-agnostic and hit every backend dev at least
  weekly.

## Files the teams need to read
- `borg/borg/core/pack_taxonomy.py`         (the broken classifier)
- `borg/borg/cli.py`                         (entrypoint, lines 12, 362, 393, 978, 1119–1121)
- `borg/borg/seeds_data/*.md`                (12 Python seed packs)
- `borg/borg/eval/e1a_seed_pack_validation.py`  (existing eval harness)
- `borg/eval/e1b_evaluation.py`              (existing simulation eval)
- `borg/borg/core/`                          (rest of the core package)
- `borg/tests/`                              (2862 tests — find what's tested
                                               about classification)
- `borg/docs/eliza_cloned/`, `docs/agenti/` are vendored corpora — IGNORE.

## What the deliverable PRD must answer
1. Exactly how does classification become CONFIDENCE-AWARE end to end?
2. What is the "I don't know" path and how does the CLI communicate it?
3. How do we add new languages WITHOUT regressing Python/Django?
4. How is per-language coverage measured and reported (precision, recall,
   false-confident-rate, calibration)?
5. What is the minimum labelled error corpus we need, and how do we build it?
6. What's the schema/pack format change (if any) for non-Python packs?
7. What's the rollout plan, with phases and explicit success criteria?
8. What are we explicitly NOT doing in v1?

## Tone and format
- Numbers > vibes.
- Cite line numbers when criticising code.
- Use severity tags CRITICAL / HIGH / MEDIUM / LOW.
- No bullshit. Honest readiness scores.
- Markdown only. No emojis except severity badges if needed.
