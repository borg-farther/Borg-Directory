> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Borg M0 Auto Mode Continuation Status

**File rev:** 20260503-0848 rev A

## Status

Auto mode continued beyond the first primitive slice.

## Added in this continuation

### Publish hardening

Modified:

- `borg/core/publish.py`

Behavior added:

- `type: learning_atom` artifacts now use a dedicated fail-closed path.
- publish requires signed atom envelope.
- tampered signature is rejected.
- payload schema validation must pass.
- atom policy must allow the decision.
- safe learning atoms save as `.learning-atom.yaml`.

### Envelope metadata

Modified:

- `borg/core/learning_atoms.py`

Behavior added:

- signed atom envelopes now include:
  - `type: learning_atom`
  - `id: <atom_id>`

### Publish tests

Created:

- `borg/tests/test_learning_atom_publish.py`

Tests:

- unsigned envelope rejected;
- tampered signature rejected;
- signed safe atom saves to outbox when GitHub PR unavailable.

### Required docs created

Created:

- `docs/PRIVACY_MODEL.md`
- `docs/LEARNING_ATOM_SCHEMA.md`
- `docs/PROMPT_INJECTION_THREAT_MODEL.md`
- `docs/TRUST_AND_PROMOTION.md`
- `docs/REVOCATION_AND_DELETION.md`
- `docs/EVAL_PLAN_FAILURE_MEMORY.md`
- `docs/SECURITY_HARDENING_BASELINE.md`

### Security gate created

Created:

- `scripts/security_gate_check.py`
- `eval/security_hardening_baseline.json`
- `.github/workflows/security-gates.yml`

## Verification status

Verification cron job queued/rerun:

- job id: `cf86e70ba491`
- command set includes targeted M0 tests, publish hardening tests, and legacy privacy regression.

Because the current main toolset has no direct terminal tool, exact stdout/stderr is pending from cron delivery.

## Remaining gates after tests

- fix any test failures from cron output;
- add CLI `borg atom ...` commands;
- add fixture corpora runner;
- run full suite;
- run first-user E2E from clean install before any release claim.

## Current honest status

M0 is now materially implemented through publish fail-closed + docs/security gate scaffolding, but not COMPLETE until verification output is green.
