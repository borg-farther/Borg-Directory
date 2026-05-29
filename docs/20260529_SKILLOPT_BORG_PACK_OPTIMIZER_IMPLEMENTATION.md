# SkillOpt-Inspired Local Pack Optimizer Implementation Report

Historical/internal — not current product documentation. This is an operator implementation report and makes no public self-serve, first-10, global promotion, or measured lift claim.

Date: 2026-05-29
Status: implemented on feature branch, local-only candidate optimizer
Scope: Borg-native pack optimizer; no SkillOpt runtime dependency

## Summary

Borg now has a local-only pack optimizer path for turning privacy-safe verified outcome evidence into bounded candidate pack diffs.

Implemented surfaces:

- `borg.core.pack_optimizer_schemas`
- `borg.core.pack_optimizer_scoring`
- `borg.core.pack_optimizer`
- `borg optimize-pack ...`
- `eval/pack_optimizer_gate.py`
- `eval/tasksets/systematic_debugging_selection.json`
- `eval/tasksets/systematic_debugging_examples.json`
- `eval/tasksets/systematic_debugging_pack.yaml`
- optimizer contract, security, CLI, and gate tests

## Boundary

This is not a public lift claim.

- first-10 claim: false
- public self-serve claim: false
- global promotion allowed: false
- SkillOpt dependency: none
- raw trajectory sharing: blocked by schema and tests
- global apply: blocked by CLI/core tests

## What the optimizer does

1. Loads a pack, normally `systematic-debugging`.
2. Loads sanitized examples from a local examples file or strong local collective-learning receipts.
3. Builds a deterministic train/selection split.
4. Proposes bounded local edits:
   - `tighten_no_confident_match_rule`
   - `add_verification_step`
   - `tighten_stop_rule`
5. Scans candidate text for privacy and prompt-injection risk.
6. Compares baseline/candidate metrics on a deterministic selection taskset.
7. Writes auditable artifacts:
   - `candidate_pack.patch`
   - `candidate_pack.preview`
   - `accepted_edits.json`
   - `rejected_edits.json`
   - `training_manifest.json`
   - `selection_score.json`
   - `privacy_scan.json`
   - `prompt_injection_scan.json`
   - `candidate_integrity.json`
   - `optimizer_run.json`
8. Allows explicit local apply only when the candidate passes selection, the artifact bundle re-verifies, the target pack id matches, and the target file hash still equals the candidate baseline hash.

## What remains blocked by design

- automatic mutation of live packs
- global/org/global_candidate apply through optimizer
- global promotion without signed provenance + trusted-tenant verified quorum
- use of raw chat/tool/file trajectories
- any claim that offline optimizer selection proves first-10 or public product lift

## Example commands

```bash
borg optimize-pack systematic-debugging \
  --taskset eval/tasksets/systematic_debugging_selection.json \
  --pack-file eval/tasksets/systematic_debugging_pack.yaml \
  --examples-file eval/tasksets/systematic_debugging_examples.json \
  --local-only \
  --json
```

```bash
python eval/pack_optimizer_gate.py --json
```

## Acceptance gates

Focused optimizer tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/optimizer/test_pack_optimizer_contract.py \
  tests/optimizer/test_pack_optimizer_security.py \
  tests/optimizer/test_pack_optimizer_cli.py \
  tests/optimizer/test_pack_optimizer_gate.py \
  -p no:cacheprovider --tb=short
```

Relevant regression tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/learning/test_collective_intelligence_loop.py \
  tests/security/test_atom_policy.py \
  tests/security/test_atom_registry.py \
  tests/mcp/test_collective_outcome_receipts.py \
  tests/mcp/test_mcp_server.py \
  -p no:cacheprovider --tb=short
```

Full suite before merge:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider --tb=short
```

## Evidence standard

This implementation is allowed to prove only:

- the optimizer pipeline is wired
- candidate artifacts are generated
- privacy and prompt-injection scans gate candidates
- local-only apply semantics hold, including candidate-id validation, artifact re-verification, target pack-id guard, and baseline-hash guard
- rejected-edit buffer exists
- deterministic selection gate works

It is not allowed to prove:

- external user value
- first-10 completion
- public self-serve readiness
- global Borg learning quality
- benchmark superiority over SkillOpt or any frontier baseline
