# Learning Atom Schema

**Rev:** 20260526-1302

A learning atom is the minimal shared-safe unit of Borg collective memory: a
signed, sanitized, revocable learning atom, not a raw trace.

CLI framing:

- `borg atom --help` presents atoms as signed, sanitized, revocable learning atoms.
- `borg atom publish --help` states publication uses fail-closed policy gates and
  never publishes raw traces.

## Required envelope

```json
{
  "type": "learning_atom",
  "id": "sha256:...",
  "envelope_version": "1.0",
  "payload": {},
  "signature": {
    "algorithm": "ed25519",
    "key_id": "ed25519:<sha256 verify-key prefix>",
    "verify_key": "base64url",
    "signature_b64url": "base64url",
    "signed_at": "2026-05-03T00:00:00Z"
  }
}
```

Verification must fail unless:

- `type == "learning_atom"`;
- envelope `id` matches `payload.atom_id`;
- `payload.atom_id` matches canonical payload hash;
- `signature.key_id` equals the key id derived from `signature.verify_key`;
- `payload.trust.submitter_key_id` equals the same derived key id;
- the Ed25519 signature verifies over canonical payload JSON including `atom_id`.

## Required payload sections

- `schema_version`: currently `1.0`
- `atom_id`: canonical SHA-256 over payload excluding `atom_id`
- `scope`: `local | org | global_candidate | global`
- `task`: type, technology, error class, error pattern, difficulty
- `learning`: root cause class, worked, avoid, why
- `evidence`: type, strength, support count
- `privacy`: risk score, scanner version, finding classes, redaction count, raw trace retained=false
- `safety`: prompt injection score, injection classes, retrieval treatment
- `trust`: submitter key id, tenant pseudonym, reputation, independent tenant count hint; registry/store may attach `verified_tenant_count` for trusted quorum display
- `lifecycle`: status, created day, expiry, revocation fields

## Forbidden shared fields

- `tool_calls`
- `calls`
- `files_read`
- `files_modified`
- `key_files` for global scope unless generalized
- raw stack traces
- raw tool results
- raw user prompts
- `.env` values

## Partial example safe payload

This snippet shows the human-readable core only. A validating payload must also include `atom_id`, `evidence`, `privacy`, `safety`, `trust`, and `lifecycle` as listed above; executable tests in `tests/security/test_learning_atoms.py` cover full valid payloads.

```json
{
  "schema_version": "1.0",
  "scope": "global_candidate",
  "task": {
    "type": "debug",
    "technology": ["python", "django"],
    "error_class": "db-migration-error",
    "error_pattern": "migration state mismatch",
    "difficulty": "unknown"
  },
  "learning": {
    "root_cause_class": "schema_state_mismatch",
    "worked": "Use migration framework with fake-initial when tables already match models.",
    "avoid": ["Manual schema edits without migration state reconciliation."],
    "why": "Runtime schema and migration history diverged."
  }
}
```

Validation implementation: `borg/core/learning_atoms.py`.
