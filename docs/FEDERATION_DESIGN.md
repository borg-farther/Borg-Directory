# Federation Design

**Status:** federation ships DARK (off by default, no sharing without explicit
opt-in) per the Phase-0 decision: local-first pilot, federation enabled only
after the pilot's counterfactual evidence clears the build bar in
`docs/PILOT_DECISION_PROTOCOL.md`. This document exists because the parts that
are catastrophic to retrofit — trust hierarchy, anti-rollback, schema
evolution, ingest gates — must be right BEFORE any atom crosses a machine
boundary, even in a dark launch.

## 1. What federates, and what never does

Federation moves **learning atoms** only: schema-minimized, redacted,
class-level debugging knowledge (`docs/LEARNING_ATOM_SCHEMA.md`). Things that
NEVER leave the machine:
- raw traces, raw error text, anything pre-redaction;
- value receipts (`value_receipts.db`) — local-only by contract; the
  counterfactual replay consumes user-exported, consented, redacted receipts
  operator-side, outside the federation path entirely;
- tenant identifiers (only HMAC pseudonyms appear in atoms).

Local-scope atoms are unshareable by construction: the registry quarantines
`scope: local` at ingest, and the sharing kill-switch
(`$BORG_HOME/SHARING_DISABLED`, `borg/core/sharing.py`) fail-closes every
sharing surface regardless of scope.

## 2. Trust hierarchy and key management

```
root key (offline) ──signs──> key directory (keys.signed.json)
                                 ├── trusted manifest keys (online, rotatable)
                                 └── revoked_key_ids (revocation wins)
manifest key ──signs──> manifest.signed.json (the ONLY thing clients trust)
submitter keys ──sign──> learning-atom envelopes
```

Clients pin ONE value — the root key id — and survive online-key rotation and
compromise without reconfiguration. Full operator procedures and fail-closed
rules: `docs/KEY_MANAGEMENT.md`. Implementation:
`borg/core/key_management.py`, `borg.core.atom_registry.sync_signed_registry_to_store`.

## 3. Anti-rollback / anti-replay (B1)

The signed manifest carries `channel`, monotonic `sequence`, `generated_at`,
`expires_at`, `previous_manifest_hash`, and per-file `sha256` + `size` for
every atom/tombstone/receipt. Clients:
1. verify the manifest signature against the trust anchors above;
2. reject channel mismatches, expired manifests, and any `sequence` lower than
   the persisted last-seen (or equal-sequence with a different hash — fork);
3. validate every referenced file's hash+size BEFORE mutating the store
   (no partial imports);
4. apply tombstones before atoms — revocation always wins;
5. persist `last_sequence` / `last_manifest_hash` (and the key-directory
   sequence/hash) in the sync state file; remote syncs REQUIRE a state path.

The key directory has the same protections independently (sequence, expiry,
hash-pinned fork detection), so a replayed old directory cannot resurrect a
revoked key. Tests: `tests/security/test_federated_atom_registry.py`,
`tests/security/test_key_management.py`.

## 4. Ingest pipeline (every atom, every time)

```
signed envelope
  → Ed25519 signature + canonical atom_id check        (verify_signed_atom)
  → scope gate (local quarantined; org/global only)
  → prompt-injection scan over EVERY payload string    (B6; score persisted
    in the registry receipt; blocked => quarantine)
  → privacy scan (secrets/PII => reject, fail closed)
  → schema validation (strict field allowlist)
  → quorum: global promotion requires registry-COMPUTED independent tenant
    quorum from signed outcome receipts — self-declared counts never count
  → accepted atom + receipt; manifest rebuilt
```

Retrieval treats every atom as `untrusted_advisory`: text is neutralized
(`neutralize_for_retrieval`) before an agent ever sees it — ingest scanning is
a registry-hygiene layer, not the only line of defense.

## 5. Atom schema evolution (B4)

`schema_version: "1.0"` with a strict top-level field allowlist. Four OPTIONAL
fields are reserved and shape-validated now because adding them post-launch
would re-sign the world (atom ids are canonical-payload hashes):

| Field | Purpose | Shape |
|---|---|---|
| `applicability` | targeting: where the learning applies | dict of `languages` / `frameworks` / `os` / `tool_versions` → list[str] |
| `outcome` | verified-outcome rollup for ranking | dict; `status ∈ {unknown, confirmed_helpful, confirmed_unhelpful, mixed}` |
| `signature_class` | crypto agility | `ed25519` (current) or `ed25519_pq_hybrid_reserved` (PQ migration slot) |
| `embedding_ref` | retrieval-embedding provenance | string ≤256 chars, no whitespace, e.g. `model@sha256:…` |

Compat contract (tested): v1 atoms without these fields stay valid; atoms with
them validate → sign → verify → ingest unchanged; malformed shapes are
rejected; unknown fields are still rejected.

## 6. Revocation

Three layers, all converging on sync:
1. **Atom tombstones** — registry-side `borg atom revoke`; applied before
   imports; convergence measurable against an SLO (`--revocation-slo-seconds`).
2. **Key revocation** — `revoked_key_ids` in the root-signed key directory;
   kills a manifest key (sync refuses) or a submitter key (its atoms skipped).
3. **Local kill-switch** — `SHARING_DISABLED` sentinel stops all sharing
   locally regardless of registry state.

## 7. Dark-launch posture and the enable path

Today: sharing defaults OFF; registry interactions are operator-driven; the
quorum rule makes single-tenant "global" promotion impossible (verified in
E-010: org-scope accepted, global REFUSED for a single tenant).

Enabling federation for real requires, in order:
1. pilot counterfactual_rate clears the BUILD bar (`docs/PILOT_DECISION_PROTOCOL.md`);
2. root key generated offline + key directory published (`docs/KEY_MANAGEMENT.md`);
3. clients configured root-anchored (`--root-key-id`), state paths persisted;
4. red-team evidence current: no-egress under secrets-laden input, stale
   manifest rejected, kill-switch fail-closed (engagement evidence E-012);
5. PART 10 federation gates green.

Anything less stays dark.
