# Federated learning optimality audit

**Date:** 2026-05-28 05:34 UTC
**Scope:** Borg remote/global/federated learning mechanism, value path, truth discipline, and agent impact.
**Verdict:** **NO-GO for Google/God-tier product optimality today. GO for the signed remote protocol slice and GO for internal outcome-grounded loop primitives.**

## Task breakdown

The question was not simply “does sync work?” It splits into five subtasks:

1. **Protocol correctness:** can a clean agent sync signed learning from a remote registry and reject tamper/replay/stale/revoked data?
2. **Truth grounding:** is the propagated learning backed by verified outcomes rather than self-reported confidence or synthetic traces?
3. **Agent value speed:** does Borg put high-value guidance in front of agents fast, without noisy or harmful matches?
4. **Collective learning effectiveness:** do independent agents improve each other through outcome-grounded feedback, promotion, demotion, and revocation?
5. **Claim discipline:** do docs and dashboards separate protocol proof from public launch, external lift, and 100-user readiness?

## Executive answer

**No — Borg is not yet Google/God-tier in the market because external outcome rows are still zero.**

It is **strong, safety-first infrastructure** for remote signed propagation, and the follow-up max-value loop work now adds **internal outcome-grounded primitives**: contribution ledger events, signed outcome receipts, trusted receipt signer allowlists, intervention `source_refs` binding for atom-bound receipts, dedupe clusters, sanitized atom candidates, registry-computed quorum from trusted receipts, cluster-derived promotion with explicit supporting receipt IDs and trusted candidate atom id, and unified scored retrieval. Those are mechanism GO, not product-impact GO.

Current machine verdict from `eval/federated_learning_optimality_audit.json`:

- `remote_global_federated_protocol`: **GO**
- `google_god_tier_optimal`: **NO-GO**
- `effective_collective_learning`: **NO-GO_REAL_WORLD_VALUE_NOT_PROVEN**
- `external_user_lift`: **NO-GO**
- `public_self_serve_launch`: **NO-GO**

## Scorecard

- **Protocol security:** 9.0 / 10
  - Signed manifests, trusted key id, expiry, channel check, per-file hash/size verification, replay protection, tombstone-first revocation, and clean-client sync are proven.
- **Proof packet richness:** 10.0 / 10
  - Snapshot now includes timestamp, git state, manifest/atom/receipt/tombstone hashes, runtime fingerprint, revocation get/search/reimport facts, and adversarial coverage.
- **External truth grounding:** 1.0 / 10
  - First-10 evidence rows are empty: 0 real users, 0 installs, 0 useful rescues, 0 measured-value rows.
- **Signal quality:** 4.0 / 10 after internal-loop proof
  - Local trace DB still has duplicate pressure; outcome receipts and dedupe clusters give the value loop a first-class truth signal, but the machine audit keeps this score conservative until real external rows and duplicate-pressure reduction improve it.
- **Routing value/speed:** 6.0 / 10 after internal-loop proof
  - `unified_collective_retrieve()` now combines atom text match, verified quorum, helpful outcomes, and negative evidence for the atom/outcome lane. Packs/traces/failure memory can still be folded into the same ranker later.
- **Effective collective learning:** 6.0 / 10 after internal-loop proof
  - Signed propagation plus signed outcome receipts and registry-computed quorum exist; real external cross-agent improvement is not yet proven.
- **Overall optimality ceiling today:** 2.0 / 10
  - The ceiling is forced down by zero external outcome evidence and weak truth grounding. A beautiful protocol does not prove useful learning.

## What is genuinely strong

1. **Remote signed sync is real.**
   - `eval/run_federated_learning_gate.py` proves HTTP-served signed manifest sync into a clean client.
2. **Tamper/replay/revocation coverage is strong.**
   - Gate proves replay rejection.
   - Tests cover unsigned manifests, payload tamper, untrusted keys, expired manifests, channel mismatch, hash mismatch, tenant-count inflation, and revoked atom search/get/reimport blocking.
3. **Revocation semantics are correct for the tested protocol.**
   - Tombstone wins over atom import.
   - Revocation convergence observed: 0.6566s under a 2.0s SLO in the latest gate run.
4. **The system now refuses to overclaim external lift.**
   - Snapshot says `external_user_lift_claimed: false`.
   - Public self-serve remains `NO-GO`.
5. **Agent-facing safety posture is better than most prototypes.**
   - Atom retrieval labels memory as untrusted historical advice.
   - Privacy and prompt-injection gates are fail-closed.
   - The user-facing communication path was already quieted to fire only when useful.

## Internal gaps closed after the follow-up max-value loop pass

### Resolved internally — outcome grounding and contribution ledger primitives

`docs/20260526-2230_MAX_VALUE_COLLECTIVE_INTELLIGENCE_LOOP.md`, `eval/run_collective_intelligence_loop_gate.py`, and the focused security/MCP/retrieval regressions now prove the internal path:

- Borg rescue/error-lookup guidance gets an `intervention_id`;
- contribution events record interventions, outcome receipts, atom candidates, and registry promotions without raw tenants or private paths;
- `borg_record_outcome` records worked/failed, helpful, verified, redacted verification command, time/tokens/dead-end fields;
- atom-bound outcome receipts must match the recorded intervention `source_refs`; unshown atoms and no-source interventions cannot mint exact atom-bound quorum receipts;
- exported outcome receipts are signed `borg_outcome_receipt` envelopes;
- unsigned/tampered receipt files and self-signed receipts from untrusted signer keys do not count toward registry quorum.

### Resolved internally — quorum is registry-computed from signed receipts

Current gates prevent trusting `independent_tenant_count` from the atom payload, normal registry ingestion ignores direct caller-supplied `verified_tenant_count`, direct public ingestion rejects source-atom and cluster-only receipt piggybacking, atom-bound receipts cannot be minted for atoms outside the intervention `source_refs`, and org/local payload tenant-count hints are not relabeled as verified in clean-client retrieval. Global candidate promotion now uses signed exported outcome receipts only when their signer key IDs come from the trusted local/export boundary and the local promotion path supplies explicit receipt lineage plus a trusted candidate atom id. The remaining production caveat is Sybil-resistant external identity, which belongs to first-10/hosted-registry operations, not this internal mechanism proof.

### Resolved internally — duplicate wording and trace-like repeats collapse into clusters

Interventions now normalize into a stable `cluster_id` from task type, technology, error class, and normalized error pattern. Duplicate tenant receipts do not increase helpful quorum.

### Resolved internally — atom/outcome retrieval is unified

`unified_collective_retrieve()` ranks learning atoms by text match, verified tenant quorum, helpful outcome receipts, and negative evidence. The current ranker covers the atom/outcome lane; packs, traces, failure memory, recency, and project context can be added behind the same score contract.

## Still not Google/God-tier

### P0 — external value is still zero rows

`eval/first_10_user_scoreboard.json` still has:

- real users: 0
- installs: 0
- useful rescue moments: 0
- measured value rows: 0

So public launch, 100-user rollout, and measured lift remain **NO-GO**.

## Alternative views considered

### View A: “Protocol GO means collective learning GO.”
Rejected. Protocol GO proves safe movement of learning atoms, not that the atoms improve agents.

### View B: “No external users means it is worthless.”
Rejected. The protocol, safety gates, revocation model, and local rescue path are real engineering value. They are necessary foundations.

### View C: “If signatures pass, truth passes.”
Rejected. Signatures prove origin/integrity, not correctness/usefulness. Bad advice can be signed.

### View D: “Synthetic clean-client sync is enough for launch.”
Rejected. It proves mechanics only. External-user lift requires consented rows.

### View E: “The next fix is more docs.”
Rejected. Docs are now useful mainly as gates. The next true value leap is row-derived external proof, production hosted-registry operations, and measured lift from consented first-10 users.

## External anchors used

- **TUF:** signed metadata, target hashes, expiry, replay/rollback/freeze protection.
- **Sigstore/Rekor:** append-only tamper-resistant transparency log. Borg does not yet have this layer.
- **SLSA provenance:** proof packets need where/when/how metadata, not just a pass/fail result.
- **Federated-learning Sybil/poisoning literature:** independent identities can overpower honest clients; Borg needs outcome-derived tenant independence and poisoning resistance.

## Final reflective pass

I re-ran the reasoning chain from scratch:

- If the question is “can Borg safely sync a signed remote registry?” the answer is **yes, GO**.
- If the question is “is the mechanism optimally designed to maximize agent value and truth fast?” the answer is **no, not yet**.
- If the question is “is it effectively collectively learning in the market?” the answer is **not proven** because external rows are zero.
- If the question is “is this worth continuing?” the answer is **yes**, because the hard trust substrate is now good enough to support the real value loop.

## Next hard gates to become truly Google-tier

1. Fill first-10 external-user evidence rows honestly.
2. Measure minutes/tokens/dead-end lift from consented external rows, not synthetic gates.
3. Run the 3-condition knowledge-system experiment:
   - no Borg;
   - empty Borg scaffold;
   - seeded Borg knowledge.
4. Operate a production hosted registry with monitoring, key rotation, backup/restore, incident response, revocation SLO telemetry, and abuse/anomaly review.
5. Add transparency-log anchoring before high-trust public federation claims.

## Bottom line

**Borg has a credible signed remote learning protocol and internal outcome-grounded loop primitives.**

**Borg does not yet have Google-tier proven product impact.**

The next job is not more protocol theater. The next job is proving that external users' agents get better, faster, and more truthful through verified outcomes.
