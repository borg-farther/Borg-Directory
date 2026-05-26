# Federated learning optimality audit

**Date:** 2026-05-26 21:15 UTC  
**Scope:** Borg remote/global/federated learning mechanism, value path, truth discipline, and agent impact.  
**Verdict:** **NO-GO for Google/God-tier optimality today. GO only for the signed remote protocol slice.**

## Task breakdown

The question was not simply “does sync work?” It splits into five subtasks:

1. **Protocol correctness:** can a clean agent sync signed learning from a remote registry and reject tamper/replay/stale/revoked data?
2. **Truth grounding:** is the propagated learning backed by verified outcomes rather than self-reported confidence or synthetic traces?
3. **Agent value speed:** does Borg put high-value guidance in front of agents fast, without noisy or harmful matches?
4. **Collective learning effectiveness:** do independent agents improve each other through outcome-grounded feedback, promotion, demotion, and revocation?
5. **Claim discipline:** do docs and dashboards separate protocol proof from public launch, external lift, and 100-user readiness?

## Executive answer

**No — the mechanism is not yet optimal or Google/God-tier.**

It is **strong, safety-first infrastructure** for remote signed propagation. That is real progress. But it is not yet the maximal-value collective-learning machine.

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
- **Signal quality:** 3.0 / 10
  - Local trace DB exists, but current stats show 342 traces, 78 distinct task descriptions, duplicate pressure 0.7719. That is useful for debugging the system, not proof of clean collective intelligence.
- **Routing value/speed:** 5.0 / 10
  - Borg has useful fail-closed rescue/observe mechanics, but atoms, traces, packs, failure memory, negative evidence, recency, project context, and semantic signals are not unified behind one production ranker.
- **Effective collective learning:** 4.0 / 10
  - Signed propagation exists; outcome-grounded cross-agent improvement is not yet proven.
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

## What is not yet Google/God-tier

### P0-1 — outcome grounding is missing

The global path can move a signed atom. It does not yet prove the atom came from a verified fix.

Needed:
- guidance event id when Borg speaks;
- exact guidance shown;
- exact command/test used to verify the result;
- worked/failed outcome;
- time/tokens/dead ends avoided;
- link that outcome back to trace helpfulness, atom helpfulness, selector posterior, promotion, demotion, and revocation.

### P0-2 — quorum is safer, but not truth-complete

Current gates prevent trusting `independent_tenant_count` from the atom payload. Good.

But the registry still accepts `verified_tenant_count` at ingestion as an input. For a production Google-tier registry, tenant independence should be computed from signed receipts/outcomes, not caller-supplied as a decisive value.

### P0-3 — duplicate traces can inflate the feeling of learning

Latest trace stats:

- total traces: 342
- distinct task descriptions: 78
- duplicate pressure: 0.7719

This means repeated/seed-like records can dominate local memory unless dedup/generalization becomes first-class.

Needed:
- cluster repeated traces;
- create one canonical atom per failure signature;
- support counts and negative counts live on the atom;
- repeated seed imports never inflate global confidence.

### P0-4 — retrieval is fragmented

Today, value can come from packs, traces, rescue rules, failure memory, and learning atoms. That is powerful but fragmented.

Google-tier design needs one scored retrieval/routing API combining:

- exact error class and stack context;
- technology and project path;
- semantic similarity;
- verified helpfulness;
- tenant quorum;
- recency/decay;
- negative evidence/dead ends;
- no-match precision.

### P0-5 — external value is still zero rows

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
Rejected. Docs are now useful mainly as gates. The next true value leap is outcome-grounded feedback and unified retrieval.

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

1. Build guidance-event receipts and outcome-grounded atom promotion/demotion.
2. Deduplicate/generalize trace memory before sharing or confidence scoring.
3. Make registry tenant quorum computed from signed independent outcome receipts.
4. Unify all memory sources behind one scored routing API.
5. Run the 3-condition knowledge-system experiment:
   - no Borg;
   - empty Borg scaffold;
   - seeded Borg knowledge.
6. Fill first-10 external-user evidence rows honestly.

## Bottom line

**Borg now has a credible signed remote learning protocol.**

**Borg does not yet have a Google-tier optimal collective learning system.**

The next job is not more protocol theater. The next job is proving that the network makes agents better, faster, and more truthful through verified outcomes.
