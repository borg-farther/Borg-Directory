# Borg Trust and Promotion

**Rev:** 20260526-1302

## Principle

A signature proves integrity, not truth.

Ed25519 signatures prove a learning atom was not modified after signing by a key holder. They do not prove the atom is useful, safe, or honest.

## Promotion ladder

```text
local draft
→ local_safe
→ org_safe
→ global_candidate
→ published
→ revoked if needed
```

## Trust signals

- valid Ed25519 signature;
- privacy scan pass;
- prompt-injection scan pass;
- submitter reputation;
- evidence strength;
- helpfulness feedback;
- independent tenant count.

## Global promotion rule

Agent count does not equal tenant independence.

Global candidates require independent tenant support. Default M0/M2 target:

```text
verified_tenant_count >= 3
```

The atom payload may carry `trust.independent_tenant_count` as a hint for local display or compatibility, but it is **not trusted for promotion or retrieval evidence**. Policy must receive registry-computed `verified_tenant_count`; otherwise the atom is quarantined. Retrieval should display registry/store verified counts when present. Same tenant, same machine, same signing key, same billing/org proof, or same operator cannot count twice.

Future M2 tenant independence can be proven by verified org key, admin-issued tenant signing key, billing-domain proof, or registry membership.

## Sybil mitigations

- signed atoms;
- rate limits;
- reputation weighting;
- delayed trust;
- quorum by tenant, not agent;
- revocation/tombstones;
- anomaly detection in later phases.

## Verification

```bash
python -m pytest -q tests/security/test_learning_atoms.py tests/security/test_atom_policy.py tests/security/test_atom_store.py
```
