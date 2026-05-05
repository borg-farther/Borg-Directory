# Learning Atom Schema

**Rev:** 20260503-0846

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
    "key_id": "ed25519:...",
    "verify_key": "base64url",
    "signature_b64url": "base64url",
    "signed_at": "2026-05-03T00:00:00Z"
  }
}
```

## Required payload sections

- `schema_version`: currently `1.0`
- `atom_id`: canonical SHA-256 over payload excluding `atom_id`
- `scope`: `local | org | global_candidate | global`
- `task`: type, technology, error class, error pattern, difficulty
- `learning`: root cause class, worked, avoid, why
- `evidence`: type, strength, support count
- `privacy`: risk score, scanner version, finding classes, redaction count, raw trace retained=false
- `safety`: prompt injection score, injection classes, retrieval treatment
- `trust`: submitter key id, tenant pseudonym, reputation, independent tenant count
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

## Example safe payload

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
