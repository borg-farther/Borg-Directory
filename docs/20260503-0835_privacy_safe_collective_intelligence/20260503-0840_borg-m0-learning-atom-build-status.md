# Borg M0 Privacy-Safe Learning Atom Build Status

**File rev:** 20260503-0840 rev A  
**Build start:** 20260503-0840  
**Spec source:** `docs/20260503-0835_privacy_safe_collective_intelligence/20260503-0835_borg-privacy-safe-collective-intelligence-master-build-spec.md`

---

## 1. Status

**Status:** PARTIAL BUILD STARTED — M0 core primitives implemented, verification running asynchronously because the current main toolset has no direct terminal tool.

Verification job:

- cron job id: `6f4a0b1f317f`
- name: `20260503-0839 borg m0 atom test verification`
- workdir: `/root/hermes-workspace/borg`

---

## 2. Implemented files

### New tests

- `borg/tests/test_privacy_structured.py`
- `borg/tests/test_prompt_injection.py`
- `borg/tests/test_learning_atoms.py`
- `borg/tests/test_atom_policy.py`
- `borg/tests/test_atom_retrieval_firewall.py`
- `borg/tests/test_atom_store.py`

### New/modified implementation

- modified: `borg/core/privacy.py`
  - added structured privacy scanner
  - added `PrivacyFinding`
  - added `PrivacyScanResult`
  - added `privacy_scan_structured()`
  - added `privacy_risk_score()`
  - preserved legacy APIs

- created: `borg/core/prompt_injection.py`
  - deterministic injection scanner
  - neutralizer for retrieval

- created: `borg/core/learning_atoms.py`
  - atom schema validation
  - trace-to-atom distillation
  - canonical atom JSON
  - atom id generation
  - signed atom envelope
  - verification wrapper using existing Ed25519 code

- created: `borg/core/atom_policy.py`
  - reject/quarantine/local/org/global-candidate policy decisions

- created: `borg/core/atom_retrieval.py`
  - retrieval firewall formatter
  - untrusted advisory header
  - strips/redacts unsafe material

- created: `borg/core/atom_store.py`
  - local SQLite atom store
  - tombstone revocation
  - search suppression for revoked atoms

---

## 3. Predefined success criteria coverage

| Criterion | Current status |
|---|---|
| raw traces not shared directly | implemented in atom path; publish integration not yet wired |
| structured PII/secret detection | implemented + tests written |
| prompt-injection detection | implemented + tests written |
| learning atom schema | implemented + tests written |
| signed atom envelopes | implemented + tests written |
| retrieval firewall | implemented + tests written |
| revocation/tombstones | implemented + tests written |
| publish/sync hardening | not yet implemented |
| CLI/MCP atom commands | not yet implemented |
| full fixture corpus | not yet implemented |
| security CI baseline | not yet implemented |
| utility C0/C1/C2 eval | not yet implemented |

---

## 4. Verification commands queued

```bash
python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_atom_store.py
python -m pytest -q borg/tests/test_privacy.py
```

The cron verification result will return exact stdout/stderr to origin.

---

## 5. Next required build steps after test output

1. Fix any RED/GREEN failures from the verification job.
2. Add `learning_atom` branch to `borg/core/publish.py` and fail closed if structured scanner imports fail.
3. Add `borg atom ...` CLI commands.
4. Add JSONL fixture corpora and corpus runner.
5. Add docs required by checklist.
6. Add CI/security gate files.
7. Run full targeted + regression suite.

---

## 6. Honest closeout

This is not M0 COMPLETE yet. It is the first systematic implementation slice:

- tests written first;
- core code implemented against tests;
- verification job launched;
- remaining gates explicitly listed.

M0 can only be marked COMPLETE after targeted tests, publish hardening, docs, and security gates pass.
