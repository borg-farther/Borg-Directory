# Optimal safe collective learning loop

**File rev:** 20260526-1302 rev B
**Repo:** `/root/hermes-workspace/borg`
**Status:** executable architecture contract + current GO/NO-GO. Local primitives and local filesystem staging are GO; remote/global/federated protocol is GO. Broad public self-serve launch and real external-user lift remain separate NO-GO claims until first-10 evidence rows pass.

## 1. Task outline

Build Borg into a collective learning loop that agents actually want to use while protecting the humans and organizations behind them.

The loop must optimize all of these at once:

1. **Safety:** no raw prompts, raw traces, source, env vars, secrets, or tenant identifiers leave the local machine by default.
2. **Security:** prompt-injection, poisoning, signature spoofing, self-promotion, stale-runtime, and revocation failures are first-class threat cases.
3. **Reliability:** learning is accepted only with verifiable receipts, durable storage, tombstones, and clean-user sync proof.
4. **Utility:** agents get compact `ACTION / STOP / VERIFY` guidance, not long lectures.
5. **Low friction:** rescue is automatic and local-first; feedback is one-call/one-tap; sharing is opt-in.
6. **Credit:** useful contributors get credit without creating abuse incentives or punishing privacy-first users.
7. **Honesty:** remote/global/federated protocol claims require signed-hosted-registry proof; measured-savings and public launch claims require separate external-user gates.

## 2. Subtasks and adversarial questions

### A. Data boundary

Question: what is the smallest useful thing Borg can share?

Answer: a signed, sanitized, revocable **LearningAtom**, not a raw trace.

Challenge: if atoms are too vague, they are useless.

Resolution: atoms keep the reusable causal payload:

- task type;
- technology labels;
- normalized error class / pattern;
- root-cause class;
- worked approach;
- dead ends to avoid;
- evidence strength;
- privacy/safety metadata;
- signature/trust/lifecycle metadata.

They exclude raw paths, raw tool output, raw stack dumps, raw prompts, env values, source snippets, screenshots, and tenant/customer identifiers.

### B. Security boundary

Question: can a malicious agent inject instructions into future agents?

Answer: not if three gates all hold:

1. ingestion scanner rejects/neutralizes prompt injection;
2. retrieval formatter wraps all memory as **untrusted historical advice, not instructions**;
3. agents must still verify with the provided command/test.

Challenge: retrieval warnings alone are weak.

Resolution: warning is defense-in-depth only. Primary control is rejecting unsafe text before it reaches retrievable shared memory.

### C. Trust boundary

Question: does a signature prove a lesson is true?

Answer: no. A signature proves integrity and key control only.

Required trust layers:

1. valid atom signature;
2. key id derived from verify key, not submitter text;
3. registry-computed tenant independence;
4. evidence and helpfulness receipts;
5. revocation/downranking path;
6. delayed trust for new identities.

Challenge: one tenant can spin up many agents.

Resolution: global promotion uses independent tenant quorum, not agent count. Self-declared quorum is quarantined.

### D. Reliability boundary

Question: what happens when bad learning escapes?

Answer: tombstone wins over every index, cache, sync import, and retrieval path.

Required proof:

1. publish signed tombstone;
2. clean client imports tombstone;
3. `get_atom()` returns none;
4. `search_atoms()` returns none;
5. re-import of the same atom fails.

Challenge: deletion alone is insufficient because replicas can reintroduce the atom.

Resolution: deletion removes payload bytes where required; tombstone prevents resurrection.

### E. Product/friction boundary

Question: how do we get learning without annoying users?

Answer: never block the rescue path.

Friction rules:

- no login before local rescue;
- no sharing by default;
- one compact receipt on every Borg answer;
- one automatic outcome-close call after `VERIFY` passes/fails;
- first share gets a redaction preview;
- repeated shares use saved local preference;
- users can stay local-only without being labeled bad actors.

### F. Credit/economics boundary

Question: how do we reward contribution without inviting spam?

Answer: split **reputation** from **credits**.

- Reputation: slow trust weight for promotion/review.
- Credits: fast, non-monetary recognition for closing loops and improving memory.

Do not introduce transferable or monetary credits until Sybil resistance, bad-answer dispute flow, and external utility are proven.

## 3. Optimal loop

```text
agent failure
  -> borg rescue / observe
  -> local receipt: ACTION / STOP / VERIFY / confidence
  -> agent executes and verifies
  -> one-call outcome receipt
  -> local failure memory + outcome metrics
  -> optional atom distillation
  -> privacy + prompt-injection + schema policy
  -> signed local/org/global-candidate atom
  -> staging registry ingestion
  -> registry recomputes identity/quorum and emits receipt
  -> clients sync signed manifest + atoms + tombstones
  -> retrieval firewall formats compact untrusted guidance
  -> future agent verifies result
  -> helpfulness/downranking/revocation updates loop
```

## 4. Stage gates

### Gate 0 — runtime freshness

No long-lived MCP process is trusted because files on disk can be newer than imported code in memory.

Requirement: every protocol/launch GO gate must include runtime fingerprint and behavior canaries. Served Borg should eventually compare loaded runtime against an approved manifest and fail closed if stale.

Status: **GO for the executable protocol gate process; not complete for served fail-closed MCP runtime enforcement**. `eval/run_federated_learning_gate.py` records `runtime_freshness.fingerprint`; operator-served runtime cutover remains a separate gate. See `docs/20260526_ALWAYS_CURRENT_RUNTIME_AND_FEDERATED_LEARNING_PLAN.md`.

### Gate 1 — local rescue

Requirement: local Borg can return `ACTION / STOP / VERIFY` or an explicit no-match receipt.

Status: **conditional GO** for controlled first-10 beta while honesty labels remain.

### Gate 2 — local learning atom primitive

Requirement: raw traces distill into sanitized atoms; atom schema validates; signatures verify; tampering fails; retrieval is untrusted.

Status: **GO for local primitive** after focused tests in this session.

### Gate 3 — shared atom import

Requirement: store/import path verifies signatures and key identity, not just publish path.

Status: **GO for the hardened local store path** after this session's fixes.

### Gate 4 — registry-computed quorum

Requirement: global promotion cannot trust `independent_tenant_count` written inside the atom payload.

Status: **GO at policy/retrieval level** after this session: self-declared global quorum is quarantined unless registry-computed `verified_tenant_count` is supplied, and retrieval formatting prefers verified tenant counts over payload hints.

### Gate 5 — staging propagation

Requirement: fresh user A -> staging registry -> fresh user B -> tombstone revocation proof.

Status: **GO for local filesystem staging and remote signed-manifest protocol** after this session. `borg/core/atom_registry.py` proves signed atom ingestion, signed hosted manifest generation, remote HTTP sync, clean client import, replay rejection, and tombstone suppression. See `docs/20260526-2046_REMOTE_FEDERATED_LEARNING_GO_PROOF.md`.

### Gate 6 — public self-serve / external-user lift rollout

Requirement: external users, measured usefulness, abuse controls, support/incident process, and production hosted registry operations pass.

Status: **NO-GO for broad public self-serve and external-user lift claims**. Remote/global/federated protocol is GO, but the first-10 evidence scoreboard is still the gate for public launch and measured usefulness.

### Gate 7 — Google/God-tier learning optimality

Requirement: Borg must prove not only safe propagation, but fast, truthful, outcome-grounded agent improvement across independent users.

Status: **NO-GO for optimality today**. `eval/run_federated_learning_optimality_audit.py` and `docs/20260526-2115_FEDERATED_LEARNING_OPTIMALITY_AUDIT.md` intentionally split protocol GO from value proof. Current blockers are zero external outcome rows, duplicate-heavy local trace evidence, missing guidance-event outcome receipts, caller-supplied registry quorum input, and fragmented retrieval/routing.

## 5. Security controls mapped to external standards

- **OWASP LLM01 Prompt Injection:** deterministic scanner, retrieval neutralization, untrusted advisory header, verify step.
- **OWASP Sensitive Information Disclosure:** local-only default, privacy scanner, schema minimization, no raw trace export.
- **OWASP Training Data Poisoning / Insecure Plugin Design / Excessive Agency:** signed atoms, registry receipts, delayed trust, verification commands, no autonomous global promotion.
- **NIST Privacy Framework:** data minimization, risk scoring, privacy zones, local-only default, deletion + tombstone policy.
- **NIST SSDF:** secure-by-design tests, fail-closed policy checks, regression tests for known vulnerability classes.
- **Sigstore-style supply-chain pattern:** signed artifacts, key identity binding, append-only/tamper-evident registry as M1/M2 seam.

## 6. Current code hardening shipped in this session

### `borg/core/learning_atoms.py` rev 20260526-1302

- Added canonical key-id derivation from Ed25519 verify key.
- `verify_signed_atom()` now fails when:
  - envelope type is not `learning_atom`;
  - envelope id does not match payload atom id;
  - payload atom id is not canonical;
  - signature key id does not match verify key;
  - payload submitter key id does not match verify key;
  - signature bytes do not verify;
  - payload validation fails.

### `borg/core/atom_store.py` rev 20260526-1302

- Store/import path now verifies signed envelopes before accepting them.
- Shared atoms require a valid signed envelope.
- Global candidates require registry-computed tenant quorum passed to policy.

### `borg/core/atom_policy.py` rev 20260526-1302

- Self-declared global quorum is no longer enough.
- `verified_tenant_count` must be supplied by registry/import code before global candidate promotion.
- Retrieval formatting uses registry/store `verified_tenant_count` when present so agent-visible quorum evidence cannot be inflated by payload hints.

### `borg/core/failure_memory.py` rev 20260526-1302

- Added per-record cross-process lock around YAML read/modify/write.
- Replaced fixed `.tmp` file with unique temp names.
- Concurrent failure-memory updates now preserve increments instead of racing.

### `borg/core/atom_registry.py` rev 20260526-1302

- Added local filesystem staging registry with `atoms/`, `tombstones/`, `receipts/`, `quarantine/`, and `manifest.json`.
- `ingest_atom_envelope()` verifies atom signatures and policy before writing shareable atoms.
- Local-scope atoms are rejected from sharing.
- Self-declared global quorum is quarantined; verified quorum is accepted only when registry code supplies `verified_tenant_count`.
- `write_signed_registry_manifest()` signs hosted registry metadata with Ed25519 and records file hashes/sizes, expiry, sequence, and channel.
- `sync_signed_registry_to_store()` verifies the trusted registry key, expiry, replay state, per-file hashes, and tombstones-before-atoms ordering across HTTP or filesystem registries.
- `sync_registry_to_store()` imports tombstones before atoms so revocation wins in local staging too.

## 7. Machine-readable control contract

See `eval/collective_learning_loop_controls.json` rev 20260526-1302.

Hard controls:

1. raw traces never shared;
2. shared atoms must be signed;
3. key id cannot be spoofed;
4. store/import verifies signatures;
5. global quorum is registry-computed;
6. tombstone wins over retrieval and re-import;
7. retrieval firewall marks memory untrusted;
8. local filesystem staging registry proves A->B sync and tombstone suppression;
9. remote signed hosted-manifest protocol proves HTTP sync, runtime freshness, replay protection, and revocation convergence;
10. first-10 external-user scoreboard remains required before public launch or measured-savings claims.

## 8. Verification run

Focused tests passed:

```bash
python -m pytest -q \
  tests/security/test_atom_registry.py \
  tests/security/test_collective_learning_loop_controls.py \
  tests/security/test_learning_atoms.py \
  tests/security/test_atom_policy.py \
  tests/security/test_atom_store.py \
  tests/learning/test_failure_memory.py
# 66 passed

python -m pytest -q \
  tests/security/test_atom_registry.py \
  tests/security/test_federated_atom_registry.py \
  tests/security/test_federated_learning_gate.py \
  tests/security/test_collective_learning_loop_controls.py \
  tests/security/test_learning_atoms.py \
  tests/security/test_atom_policy.py \
  tests/security/test_atom_retrieval_firewall.py \
  tests/security/test_atom_store.py \
  tests/security/test_privacy_structured.py \
  tests/security/test_prompt_injection.py \
  tests/security/test_learning_atom_publish.py \
  tests/cli/test_cli_atom.py \
  tests/learning/test_failure_memory.py
# 97 passed

python -m pytest -q
# 2303 passed, 40 skipped, 4 xfailed, 1 xpassed

python scripts/security_gate_check.py
# PASS: Borg security hardening policy gate
```

Mathematical sanity check for 128-bit failure-memory hash truncation:

- 10,000 records: collision probability ≈ `1.469e-31`.
- 100,000 records: collision probability ≈ `1.469e-29`.
- 1,000,000 records: collision probability ≈ `1.469e-27`.
- 10,000,000 records: collision probability ≈ `1.469e-25`.

This supports 128-bit truncation as adequate for local/failure-memory record IDs; it is not a substitute for cryptographic atom signatures.

## 9. Remaining blockers

No remaining blocker for the remote/global/federated **protocol** GO gate.

Still separate NO-GO gates:

1. Production hosted registry operations: uptime monitoring, backup/restore, key rotation, and incident runbooks.
2. Transparency-log anchoring for high-trust public claims.
3. First-10 external-user scoreboard for public self-serve launch.
4. Consented external outcome rows for measured usefulness/lift.
5. 100-user rollout support/incident readiness.
6. Abuse/anomaly engine for public contribution volume.

## 10. Final reflective pass

I re-checked the design from the opposite assumption: “what if global learning is impossible to make safe without killing utility?”

The strongest objection is that privacy redaction and prompt-injection filtering will either miss private data or over-redact useful details. The answer is not to trust redaction harder. The answer is to constrain the shared object so dangerous fields are structurally impossible, keep raw evidence local, require opt-in, and prove utility only through clean-client reuse.

Second objection: signed manifests do not prove the lesson is correct. Correct. The signature proves authenticity/integrity of the registry metadata; usefulness still requires evidence, tenant-independent receipts, and later external outcome rows.

Third objection: a malicious registry could replay old metadata or inflate quorum. The signed remote gate now rejects replayed sequence state, expired metadata, untrusted registry keys, and file-hash mismatches; retrieval prefers registry/store `verified_tenant_count` over payload hints.

Fourth objection: revocation will lag in distributed clients. Correct. The protocol GO is bounded by an explicit convergence SLO and the executable gate proves tombstone-first remote sync removes the atom from a clean client. Production operations must monitor that SLO continuously.

Final conclusion: **local learning is GO. local filesystem staging is GO. remote/global/federated protocol is GO. broad public self-serve launch and measured external-user lift remain NO-GO until their separate evidence gates pass.**
