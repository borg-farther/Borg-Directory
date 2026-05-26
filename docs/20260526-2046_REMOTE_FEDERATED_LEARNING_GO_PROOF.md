# Remote/global/federated learning GO proof

**File rev:** 20260526-2046 rev B
**Scope:** Borg remote/global/federated *protocol* readiness.
**Verdict:** GO for signed hosted-registry propagation and revocation.
**Explicit non-claim:** This is not a public self-serve launch GO, not Google/God-tier optimality, and not a real external-user utility/lift claim.

## What changed

Borg now has an executable remote federation path:

1. A registry signs `manifest.signed.json` with Ed25519.
2. The manifest lists atom, tombstone, and receipt files with content hashes and sizes.
3. A clean client fetches the manifest over a remote HTTP boundary.
4. The client verifies:
   - manifest signature;
   - trusted registry key id;
   - expected channel;
   - expiry;
   - monotonic sequence/replay state;
   - every listed file hash and size.
5. The client applies tombstones before atoms.
6. The client imports only signed atom envelopes accepted by `AtomStore`.
7. Retrieval uses registry/store `verified_tenant_count`, not payload `independent_tenant_count`.
8. A tombstone converges to the clean client within the declared revocation SLO and removes the atom from search/get/reimport.

## GO boundary

GO means:

- remote HTTP signed-manifest sync works from a hosted registry directory;
- a clean client starts empty and receives a global candidate atom;
- replayed or tampered registry metadata is rejected fail-closed;
- revocation propagates and wins over retrieval/reimport;
- runtime freshness canaries pass while the gate runs;
- no external-user lift is claimed.

GO does **not** mean:

- 100-user rollout is ready;
- public self-serve launch is ready;
- real external users got statistically significant benefit;
- a production hosted registry service and monitoring stack already exists.

Those remain separate release gates.

## Why this is the right security shape

This mirrors the parts of proven supply-chain designs that Borg needs without pretending to implement their full ecosystems:

- TUF: signed metadata, target file hashes, expiry, and rollback/replay resistance.
  - Source: https://theupdateframework.github.io/specification/latest/
- Sigstore/Rekor: signed metadata plus tamper-resistant/auditable records as the long-term production direction.
  - Source: https://docs.sigstore.dev/logging/overview/
- SLSA attestations: authenticated metadata about artifacts, not just raw artifact signatures.
  - Source: https://slsa.dev/attestation-model

Borg's current gate implements the minimum viable equivalent for learning atoms: signed manifest metadata, content-addressed files, expiry, sequence state, trusted registry key, and explicit machine-readable proof.

## Executable proof artifact

Run:

```bash
python eval/run_federated_learning_gate.py --output eval/federated_learning_gate_snapshot.json
```

Expected snapshot facts:

- `success: true`
- `verdict: GO`
- `scope: remote_global_federated_protocol`
- `remote_http_signed_manifest.passed: true`
- `remote_http_signed_manifest.manifest_hash`, `atom_envelope_hash`, `receipt_hash`, and `tombstone_hash` are populated
- `proof_provenance.git.commit` is populated and `proof_provenance.git.dirty` records whether the proof included working-tree changes
- `runtime_freshness.fingerprint.loaded_function_hashes` is populated
- `clean_client_sync.before_matches: 0`
- `clean_client_sync.after_matches: 1`
- `revocation_convergence.passed: true`
- `revocation_convergence.post_revocation_get_atom_is_none: true`
- `revocation_convergence.reimport_suppressed: true`
- `replay_protection.passed: true`
- `runtime_freshness.passed: true`
- `broad_public_self_serve: NO-GO`
- `external_user_lift_claimed: false`

## Optimality audit artifact

Protocol GO is now paired with an explicit optimality/value audit:

```bash
python eval/run_federated_learning_optimality_audit.py --output eval/federated_learning_optimality_audit.json
```

Current expected truth:

- `remote_global_federated_protocol: GO`
- `google_god_tier_optimal: NO-GO`
- `effective_collective_learning: NO-GO_REAL_WORLD_VALUE_NOT_PROVEN`
- `external_user_lift: NO-GO`
- `public_self_serve_launch: NO-GO`

## Negative/adversarial cases covered

The tests intentionally try to break the claim:

- unsigned manifest is rejected;
- manifest payload tampering without re-signing is rejected;
- untrusted registry key is rejected;
- expired manifest is rejected;
- channel mismatch is rejected by manifest verification;
- replayed older sequence is rejected;
- signed manifest with bad file hash is rejected before partial import;
- payload-inflated `independent_tenant_count` cannot override registry/store `verified_tenant_count`;
- tombstone sync removes atom from clean client retrieval.

## Current proof commands

Focused remote/federated protocol:

```bash
python -m pytest -q tests/security/test_federated_atom_registry.py tests/security/test_federated_learning_gate.py tests/cli/test_cli_atom.py
```

Security collective-learning gate:

```bash
python -m pytest -q tests/security/test_atom_registry.py tests/security/test_federated_atom_registry.py tests/security/test_federated_learning_gate.py tests/security/test_collective_learning_loop_controls.py tests/security/test_learning_atoms.py tests/security/test_atom_policy.py tests/security/test_atom_retrieval_firewall.py tests/security/test_atom_store.py tests/security/test_privacy_structured.py tests/security/test_prompt_injection.py tests/security/test_learning_atom_publish.py tests/cli/test_cli_atom.py tests/learning/test_failure_memory.py
```

Security policy gate:

```bash
python scripts/security_gate_check.py
```

Full suite:

```bash
python -m pytest -q
```

## Production caveats still separate from this GO

- Hosted registry deployment still needs uptime monitoring, key rotation, and backup/restore operations.
- Transparency-log anchoring is recommended before public high-trust claims.
- Public self-serve launch still depends on first-10 external-user evidence.
- 100-user rollout still depends on public launch gates plus support/incident readiness.
- External-user lift is still not claimed by this protocol gate; it requires consented outcome rows.
