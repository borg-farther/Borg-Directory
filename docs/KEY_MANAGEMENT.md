# Key Management (Federated Registry)

**Audience:** registry operators. Clients only ever need ONE pinned value: the
root key id.

## Trust hierarchy

```
root key (OFFLINE — never on the registry host)
  └── signs keys.signed.json (the "key directory")
        ├── manifest keys (online, rotatable) — sign manifest.signed.json
        └── revoked_key_ids — keys that must never be trusted again
atom submitter keys (per tenant) — sign learning-atom envelopes;
  revocable via the same revoked_key_ids list
```

Why the separation exists: before it, clients pinned the online manifest key
directly. Compromise of the registry host then meant re-configuring every
client — catastrophic to retrofit after launch. With root-key separation a
manifest-key compromise is survivable: revoke it in the directory, trust a new
one, sign with the root key that never touched the host. Client config does
not change.

## Key roles

| Key | Lives | Signs | Rotation |
|---|---|---|---|
| **Root** | Offline (operator hardware, never the VPS) | `keys.signed.json` only | Effectively never; compromise = full re-pin of all clients (treat like a CA root) |
| **Manifest** | Registry host | `manifest.signed.json` | Routine; revoke + re-issue via key directory |
| **Submitter** | Each tenant's machine | learning-atom envelopes | Tenant-initiated; operator can revoke a compromised tenant key |

All keys are Ed25519 (`signature_class: ed25519`;
`ed25519_pq_hybrid_reserved` is reserved in the atom schema for a post-quantum
hybrid migration — see `docs/FEDERATION_DESIGN.md`).

## Operator procedures

### Initial setup
```bash
# 1. Generate the root key OFFLINE (operator laptop / HSM, not the VPS):
python -c "from borg.core.crypto import generate_signing_key, store_signing_key; store_signing_key(generate_signing_key(), 'registry-root')"

# 2. Generate the online manifest key (on the registry host):
python -c "from borg.core.crypto import generate_signing_key, store_signing_key; store_signing_key(generate_signing_key(), 'registry-manifest-1')"

# 3. Root-sign the key directory (offline machine, with both verify keys):
borg atom sign-key-directory --registry-dir ./registry --root-agent registry-root \
  --manifest-agent registry-manifest-1 --sequence 1 --channel global

# 4. Publish keys.signed.json with the registry files. Tell users the ROOT key id.
```

### Routine manifest signing (online, frequent)
```bash
borg atom sign-manifest --registry-dir ./registry --sign-agent registry-manifest-1 \
  --sequence <monotonic> --channel global --expires-in 300
```

### Rotating / revoking a manifest key (root, offline)
```bash
borg atom sign-key-directory --registry-dir ./registry --root-agent registry-root \
  --manifest-agent registry-manifest-2 \
  --revoke-key-id <old-key-id> \
  --sequence <previous+1> --channel global
```
Rules:
- `--sequence` MUST strictly increase; clients persist the last-seen sequence
  and reject replays (an attacker cannot resurrect a directory that still
  trusted the compromised key).
- Revocation wins: a key id in `revoked_key_ids` is untrusted even if also
  listed under `manifest_keys`.
- The directory has an `expires_at` (default 24h); a stale mirror eventually
  fails closed. Re-sign on a schedule shorter than the expiry.

### Revoking a compromised tenant (submitter) key
Add its key id to `--revoke-key-id` in the next key directory. On sync,
clients skip every atom envelope signed by a revoked submitter key
(`skipped_revoked_key` in the sync result). Also tombstone the specific
known-bad atoms (`borg atom revoke`) so already-synced stores converge.

## Client configuration

Root-anchored (recommended):
```bash
borg atom sync-remote https://registry.example \
  --root-key-id <root-key-id> --channel global --state ~/.borg/registry-sync.json
```
Direct pin (legacy, still supported): `--registry-key-id <manifest-key-id>`.
If both are given, the manifest key must satisfy BOTH (pinned AND
directory-trusted AND unrevoked).

## Fail-closed behavior (tested in tests/security/test_key_management.py)
- No trust anchor → refuse to sync.
- Key directory: bad signature / wrong root / wrong channel / expired /
  replayed-older-sequence / aliased key id → refuse to sync ANYTHING.
- Manifest signed by a revoked or unlisted key → refuse.
- Atoms from revoked submitter keys → skipped, counted, reported.
