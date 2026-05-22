> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Partial implementations status report

File rev: `20260504-1131 rev B`
Repository: `/root/hermes-workspace/borg/`

## Executive summary

This file supersedes the 2026-03-29 audit. Several items previously called “zero code” or “not wired” are no longer accurate. The remaining product risk is not that the local first-user runtime is missing; it is claim discipline, external-user proof, and making trust/signature state explicit in every user-facing path.

## Current status by feature

| Area | Current state | Severity | Action |
|---|---|---:|---|
| Ed25519 signing | Implemented primitives in `borg/core/crypto.py`; learning atoms use signed envelopes in `borg/core/learning_atoms.py`; learning atom publish fails closed on missing/invalid signature in `borg/core/publish.py`. | Medium | Do not claim universal signed-pack trust unless pull/apply/publish UI reports `signature_state` and trusted/global sources enforce invalid-signature failure. |
| V2 pack execution | Implemented. `borg/core/apply.py` normalizes V2 `structure[]`; `borg/core/schema.py` and `borg/core/proof_gates.py` accept V1 `phases[]` or V2 `structure[]`. | Low | Keep regression tests green. |
| Sybil / reputation | Reputation engine and tests exist; publish path includes access-tier checks/rate limiting; search includes reputation-aware ranking hooks. | Medium | Before open public publishing, add explicit scoreboard metrics for rejected publishes, false positives, and first-user contribution path. |
| Adoption/readiness metrics | `eval/uat_scoreboard.py`, `eval/run_readiness_gates.py`, load snapshots, and `PROJECT_STATUS.md` now provide machine-readable readiness. | Low | Make the scoreboard the single source of public rollout truth. |
| Public import API | Previously placeholder: `borg.check()` returned `[]` “until M3”. Fixed in rev B: it now delegates to real search and has `borg/tests/test_public_api_check.py`. | Low | Keep as first-user smoke test. |

## Proof points now present

- Version consistency: `3.3.1` across package/runtime/build lib.
- Security baseline gate: `scripts/security_gate_check.py` passes in the 1000-user gate run.
- Atom/privacy/prompt-injection tests: `87 passed` in proof run.
- Readiness 10/100/1000 logical-user gate: green in `eval/gate_run_snapshot.json` and `eval/uat_scoreboard_snapshot.json`.
- 1000-user snapshot: `success_rate=1.0`, `failures=0`, `total_requests=66838`, `p95_ms=0.5817607045173645`, `p99_ms=0.613755825906992`.

## Still not proven

- Statistically significant agent-level success lift.
- Real external-user network effects.
- Global/federated multi-node reliability.
- Broad non-Python generalization.
- Navigation cache as a shipped first-user feature.

## Required claim language

Allowed:

- “Borg is a local/offline collective-memory aid for agents.”
- “The current local security/readiness gates are green.”
- “Learning atoms are signed, privacy-scanned, and prompt-injection neutralized before shared publication.”

Not allowed until proven:

- “Borg improves agent success rate by X%.”
- “Borg’s global network is production-proven.”
- “All packs are cryptographically trusted.”
- “DeFi collective intelligence is validated on real users.”

## Next hard gate

External first-user closure: a non-us user completes install → observe/search/check → useful action → rate/record outcome, with a privacy-safe artifact and exact transcript/log evidence.
