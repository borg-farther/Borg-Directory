# borg new-home production closure — 2026-04-22 10:32 utc

## status

**pass criteria defined; currently tied to automated gate execution.**

this closure document defines the canonical production checks for the repo migration from legacy home (`legacy-home/borg`) to new home (`borg-farther/Borg-Directory`).

## canonical remotes

- active origin: `https://github.com/borg-farther/Borg-Directory.git`
- legacy archive: `external-archival-remote (owner redacted)`
- legacy push posture: **removed** from active local config

## production closure gates

1. **remote wiring gate**
   - `.git/config` must contain origin URL above.
   - `.git/config` must not contain any legacy remote section.

2. **metadata/docs canonicalization gate**
   - canonical public surfaces must point to new home:
     - `pyproject.toml` `[project.urls]`
     - `docs/QUICKSTART.md`
     - `docs/TRYING_BORG.md`
     - `docs/GETTING_STARTED.md`
   - canonical surfaces must not include legacy canonical URL.

3. **artifact integrity gate**
   - required artifacts must exist:
     - `eval/tests/test_git_home_migration_consistency.py`
     - `eval/tests/test_new_home_scale_hardening_plan.py`
     - `eval/tests/test_new_home_readiness_contract.py`
     - `scripts/new_home_readiness_gate_check.py`
     - `eval/new_home_scale_hardening_plan.json`

4. **test gate**
   - `pytest` must pass for new-home migration/readiness suite.

## operator decision

- keep legacy repo as **private backup/archive** only.
- perform all active development + release from `origin` (new home) only.

## non-goals

- no dual-write.
- no release or governance authority from legacy repo.
