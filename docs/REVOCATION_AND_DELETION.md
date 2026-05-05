# Borg Revocation and Deletion

**Rev:** 20260503-0846

## Tombstones

Borg suppresses revoked atoms using `atom_tombstones` in `borg/core/atom_store.py`.

A tombstone records:

- `atom_id`
- `revoked_at`
- `reason`
- `issuer_key_id`
- optional signature metadata

## Deletion vs revocation

Deletion removes local payload bytes. Revocation/tombstone prevents reimport and retrieval. Shared memory needs tombstones because deleted bad atoms may reappear from replicas or caches.

## Retrieval rule

Tombstone wins over all indexes. A revoked atom must not be returned by `get_atom()` or `search_atoms()`.

## Key compromise

If a signing key is compromised:

1. revoke affected atoms;
2. downgrade trust for key id;
3. publish tombstone bundle;
4. rotate key;
5. require revalidation before promotion.

## User privacy deletion request

If a user reports PII leakage:

1. revoke atom immediately;
2. preserve tombstone;
3. remove payload from local/org stores where legally required;
4. add scanner fixture to prevent recurrence.

## Verification

```bash
python -m pytest -q borg/tests/test_atom_store.py
```
