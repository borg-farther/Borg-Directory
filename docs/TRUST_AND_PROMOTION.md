# Borg Trust and Promotion

**Rev:** 20260503-0846

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
independent_tenant_count >= 3
```

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
python -m pytest -q borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py
```
