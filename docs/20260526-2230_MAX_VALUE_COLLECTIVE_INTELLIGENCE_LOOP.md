# Max-value collective intelligence loop proof

**File rev:** 20260527-2225 rev D
**Scope:** Borg outcome-grounded value loop primitives.
**Verdict:** **GO for internal max-value loop primitives; NO-GO for external-user lift until first-10 rows exist.**

## Task breakdown

The requested loop is:

1. **Outcome receipts tied to MCP Borg rescue/error-lookup interventions**
   - MCP `borg_rescue` / `error_lookup` now emit an `intervention_id` in the JSON payload and `value_receipt`; CLI `borg rescue --json` remains a guidance packet and uses legacy `feedback-v3` unless/until it is explicitly wired into this receipt path.
   - `borg_record_outcome` records verified helpfulness/failure receipts against that exact intervention.
   - A privacy-safe contribution ledger records intervention/outcome/atom-candidate/registry-promotion events with HMAC tenant pseudonyms and redacted metadata.
   - Receipts are exported as signed `borg_outcome_receipt` envelopes; unsigned hand-written JSON, tampered envelopes, and self-signed envelopes from untrusted receipt signer keys do not count toward registry quorum.
   - Outcome tenant pseudonyms must be HMAC-shaped and must match the intervention tenant; one intervention cannot mint multiple tenant outcomes.

2. **Verified helpfulness**
   - Outcome receipts store `outcome`, `helpful`, `verified`, redacted verification command, tenant pseudonym, time saved, tokens saved, and dead ends avoided.
   - Conservative scoring uses verified helpful and unhelpful outcomes; unverified praise does not count as truth.

3. **Dedupe/generalize**
   - Interventions normalize to a stable `cluster_id` from task type, technology, error class, and normalized error pattern.
   - Case/punctuation variants like `ModuleNotFoundError: No module named flask` and `modulenotfounderror no module named flask` collapse to the same problem family.

4. **Registry-computed quorum**
   - Registry promotion computes tenant quorum from signed exported verified helpful outcome receipts in `registry/outcomes/`.
   - Payload `trust.independent_tenant_count` remains advisory and is ignored for global quorum.
   - Direct caller-supplied `verified_tenant_count` is ignored unless trusted operator/test code explicitly opts into the bypass; normal ingestion fails closed to registry-computed receipts.
   - Cluster-derived atom promotion may rebind receipts from an older source atom only through the local promotion path, only when the candidate evidence names an explicit same-cluster supporting receipt allowlist, the receipt signer keys are trusted by the local/export boundary, and the candidate atom id is explicitly trusted. Direct public ingestion cannot piggyback on another atom's receipts.

5. **Sanitized atom candidate and promotion path**
   - `build_learning_atom_candidate()` distills a cluster into a sanitized global-candidate atom only after independent verified-helpful tenant quorum.
   - `promote_cluster_to_registry()` exports supporting signed receipts, signs the candidate atom, stages it in the registry, rebuilds the manifest, and records a promotion ledger event.
   - Unsafe or under-quorum clusters return blockers instead of producing a shareable atom.

6. **Unified scored retrieval**
   - `unified_collective_retrieve()` ranks learning atoms using text match, verified tenant quorum, helpful outcome receipts, and negative evidence.
   - Retrieval returns score reasons so agents can see why a memory was ranked.

7. **First-10 measured lift boundary**
   - Internal loop proof does **not** mutate first-10 evidence.
   - First-10/public launch remains blocked until consented external-user rows show real installs, useful rescues, measured value, and zero critical privacy/security incidents.

## Implemented files

- `borg/core/collective_learning.py`
  - `CollectiveLearningStore`
  - `record_intervention()`
  - `record_outcome()`
  - `sign_outcome_receipt_payload()`
  - `verify_outcome_receipt_envelope()`
  - `cluster_stats()`
  - `atom_outcome_stats()`
  - `export_verified_outcomes()`
  - `compute_verified_tenant_count_from_outcomes()`
  - `unified_collective_retrieve()`
  - `recent_contribution_events()`
  - `contribution_summary()`
  - `build_learning_atom_candidate()`
  - `promote_cluster_to_registry()`

- `borg/cli.py`
  - `borg collective summary --json`
  - `borg collective events --json`
  - `borg collective candidate <cluster-id> --json`
  - `borg collective promote <cluster-id> --registry-dir <dir> --sign-agent <agent-id> --json`

- `borg/integrations/mcp_server.py`
  - MCP `borg_rescue` / `error_lookup` attach `intervention_id`
  - new `borg_record_outcome`
  - new `borg_collective_retrieve`
  - new `borg_collective_status` for `summary`, `events`, and `candidate`

- `borg/core/atom_registry.py`
  - `ingest_atom_envelope()` computes quorum from exported verified outcome receipts when explicit quorum is absent
  - direct ingestion keeps cross-atom receipt rebinding disabled; local cluster promotion enables it only with same-cluster supporting receipt IDs, trusted receipt signer keys, and an explicit trusted candidate atom id

- `borg/core/atom_store.py`
  - `AtomStore.search_atoms()` exposes store/registry-verified tenant counts only; org/local payload tenant-count hints remain visible as hints but are not labeled verified

- `eval/run_collective_intelligence_loop_gate.py`
  - executable end-to-end gate for the full internal loop

## Proof command

```bash
python eval/run_collective_intelligence_loop_gate.py --output eval/collective_intelligence_loop_gate.json
```

Expected summary:

```json
{
  "verdict": "GO",
  "scope": "max_value_collective_intelligence_loop_primitives",
  "public_external_lift": "NO-GO_REAL_FIRST_10_ROWS_REQUIRED"
}
```

## Gate invariants

The executable gate asserts:

- interventions are recorded;
- verified outcome receipts are exported as signed envelopes;
- dedupe cluster is stable;
- registry computes quorum from trusted-signer receipts;
- cluster-derived promotion stages a signed atom from same-cluster supporting receipt IDs;
- payload tenant-count inflation is ignored and org/local payload hints are not exposed as verified quorum;
- unified retrieval ranks the promoted atom;
- retrieval explains verified quorum and helpful outcomes;
- negative evidence is retained;
- first-10 external-user rows are not faked.

## Adversarial assumptions challenged

### Could fake payload quorum inflate promotion?

No. The gate deliberately sets payload `independent_tenant_count` to `99`; registry quorum remains `3` because it is computed from signed verified helpful outcome receipts. A direct caller-provided `verified_tenant_count` is also ignored on normal ingestion.

### Could a new atom steal quorum from an unrelated old atom?

No. Direct registry ingestion cannot count receipts tied to another atom. The only allowed cross-atom case is the local cluster-promotion path: the candidate must carry same-cluster evidence plus exact supporting receipt IDs, the caller must provide the trusted candidate atom id, receipt signer keys must be in the trusted export allowlist, and quorum is still recomputed by reading and verifying those signed receipts.

### Could duplicate wording inflate learning?

The dedupe key collapses common error text variants into one cluster. Duplicate tenant receipts do not increase independent tenant quorum.

### Could unhelpful history vanish?

No. Negative evidence is retained and appears as `negative_evidence_present` in retrieval score reasons.

### Could this fake external lift?

No. The gate checks first-10 rows remain zero and emits `NO-GO_REAL_FIRST_10_ROWS_REQUIRED` for external lift.

## Current GO/NO-GO

- **GO:** signed intervention/outcome receipt primitive for Borg rescue/error-lookup paths.
- **GO:** verified helpfulness receipt primitive.
- **GO:** dedupe/generalization primitive.
- **GO:** registry-computed quorum from trusted signed receipts.
- **GO:** sanitized contribution ledger and cluster-derived atom promotion path.
- **GO:** unified scored retrieval over atoms + outcome evidence.
- **GO:** internal synthetic E2E value-loop proof.
- **NO-GO:** Google/God-tier optimality until external lift is measured.
- **NO-GO:** public self-serve launch until first-10 row-derived evidence passes.

## What remains for true Google-tier learning

The mechanism is now present, but real-world optimality still requires:

1. first-10 external-user rows with consented evidence;
2. measured minutes/tokens/dead-end lift;
3. repeated use within 7 days;
4. cross-agent retrieval A/B tests;
5. production hosted registry operations and abuse monitoring.

Until those pass, Borg can claim **max-value loop primitives built**, not **proven max-value product impact**.
