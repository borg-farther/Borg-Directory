# SkillOpt-inspired Borg rescue interaction loop

> Historical/internal — not current product documentation. This operator note describes local implementation mechanics and proof commands; it is not a first-user guide, public launch claim, or product-lift claim.

Date: 2026-05-29
Status: internal/operator implementation report
Scope: Borg-native, local-only, no SkillOpt runtime dependency

## Why this exists

The first local pack optimizer proved Borg can safely propose bounded pack edits.
The next highest-impact SkillOpt lesson is broader than pack text: optimize the
agent/user interaction loop that determines whether Borg is called, whether weak
matches are rejected, whether `VERIFY` is actually run, and whether outcome
receipts come back into the collective memory.

This document covers the Borg-native implementation of that loop. It is not a
public lift claim. It does not change first-10/public launch gates.

## Implemented priorities

### 1. Executable rescue-packet eval harness

New module: `borg/core/rescue_packet_eval.py`

New CLI:

```bash
borg rescue-eval eval/tasksets/rescue_packet_smoke.json --json
```

New fixture:

```text
eval/tasksets/rescue_packet_smoke.json
```

The harness evaluates user-visible rescue packets against explicit cases:

- `ACTION` content
- `STOP` content
- `VERIFY` content
- problem-class match
- `NO_CONFIDENT_MATCH` precision
- unsafe-guidance rate
- human-visible no-match behavior
- outcome-capture prompt presence
- train / selection / hidden split handling

Hidden cases are reported as diagnostics with `used_for_candidate=false` and
`holdout_only=true`; hidden failures do not make a candidate eligible or
ineligible by themselves, preserving the holdout boundary.

### 2. Persistent rejected-edit memory

New module: `borg/core/pack_optimizer_rejections.py`

Rejected candidate edits are now negative evidence, not discarded output. The
optimizer writes an append-only local JSONL ledger and consults it before
re-proposing the same `(pack_id, op, anchor)` edit.

The memory stores:

- pack id
- edit op
- anchor
- rejection reason
- prior candidate id
- sanitized supporting receipt ids
- deterministic `prevent_repeat_key`

It rejects symlink memory paths and redacts secret-shaped strings before write.
This memory is maintainer-side only; it is not injected into runtime user prompts.

### 3. Agent priming optimizer artifacts

New module: `borg/core/agent_priming.py`

New CLI:

```bash
borg agent-priming claude-code --json
borg agent-priming codex
```

The generated priming block teaches the actual Borg interaction rule:

- task-start debug/test/review/deploy work -> call `borg_observe`
- concrete error/failing command -> call `error_lookup` / `borg_rescue`
- weak match -> say `NO_CONFIDENT_MATCH`
- after `VERIFY` -> call `borg_record_outcome`

The scorer blocks priming text that omits required calls or claims local first-10,
public-lift, or global-promotion proof.

### 4. Outcome-capture automation in rescue surfaces

MCP rescue/error-lookup responses now include an explicit `outcome_capture`
scaffold and append an agent instruction:

```text
AFTER VERIFY: call borg_record_outcome with this intervention_id; if VERIFY was
not rerun, set verified=false.
```

The scaffold names required fields and gives a safe payload shape:

- `template_payload.intervention_id`
- `template_payload.outcome` defaulting to `unknown`
- `template_payload.helpful` defaulting to `false`
- `template_payload.verified` defaulting to `false`
- verification command/output fields that stay empty until VERIFY actually runs

This makes receipt closure part of the runtime interaction, not a separate
operator memory.

### 5. Maintainer review queue packets

New module: `borg/core/optimizer_review_queue.py`

New CLI:

```bash
borg optimize-pack review <candidate_id> --pack-file ./pack.yaml --taskset eval/tasksets/systematic_debugging_selection.json --examples-file eval/tasksets/systematic_debugging_examples.json --json
```

The review packet collects:

- candidate id and pack id
- decision / manual-review eligibility
- score delta, baseline, candidate score, hard failures
- patch/preview hashes and patch line count
- privacy and prompt-injection scan results
- accepted and rejected edit counts/ops
- provenance hashes
- reviewer checklist
- next actions

The review queue is deliberately manual. It does not promote candidates globally
and does not claim first-10 or public lift.

## Safety boundaries preserved

- no SkillOpt runtime dependency
- no global mutation
- no public lift claim
- no first-10 claim
- no hidden-set tuning
- no raw trace or secret storage in rejected-edit memory
- source-bound inspect/apply remains required for candidate eligibility
- artifact-only inventory still cannot make a candidate eligible
- outcome capture requires actual `VERIFY`; unverified outcomes must record
  `verified=false`

## Verification commands

Focused contract proof:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/core/test_rescue_packet_eval.py \
  tests/core/test_agent_priming_outcome_capture.py \
  tests/core/test_cli_rescue_eval_and_priming.py \
  tests/optimizer/test_pack_optimizer_rejected_memory.py \
  tests/optimizer/test_optimizer_review_queue.py \
  tests/optimizer/test_pack_optimizer_cli.py \
  -p no:cacheprovider --tb=short
```

Broader regression proof:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/optimizer \
  tests/core/test_rescue_packet_eval.py \
  tests/core/test_agent_priming_outcome_capture.py \
  tests/core/test_cli_rescue_eval_and_priming.py \
  tests/mcp/test_collective_outcome_receipts.py \
  -p no:cacheprovider --tb=short
```

Executable rescue-packet smoke:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m borg.cli rescue-eval eval/tasksets/rescue_packet_smoke.json --json
```

## Non-claims

This implementation improves Borg's learning loop infrastructure. It does not by
itself prove external-user lift, public self-serve readiness, or global pack
promotion. Those remain gated by real first-10 evidence and the existing proof
dashboard/readiness process.
