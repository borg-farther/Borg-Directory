# Borg Security Hardening Baseline

**Rev:** 20260503-0846

## Scope

Security baseline for privacy-safe collective memory and learning atoms.

## Controls

- raw traces local-only by default;
- shared memory accepts only signed learning atoms;
- structured privacy scanner blocks PII/secrets;
- prompt-injection scanner blocks poisoned memory;
- atom policy rejects/quarantines unsafe payloads;
- tombstones suppress revoked atoms;
- retrieval firewall marks memory as untrusted historical advice;
- publish path for learning atoms fails closed.

## CI gates to add

- secret scan: `gitleaks/gitleaks-action`
- dependency audit: `pip-audit`
- static security scan: `bandit`
- policy enforcement: `python scripts/security_gate_check.py`
- M0 tests:

```bash
python -m pytest -q borg/tests/test_privacy_structured.py borg/tests/test_prompt_injection.py borg/tests/test_learning_atoms.py borg/tests/test_atom_policy.py borg/tests/test_atom_retrieval_firewall.py borg/tests/test_atom_store.py borg/tests/test_learning_atom_publish.py
```

## Release blockers

- any secret reaches shared atom store;
- any high-risk PII reaches shared atom store;
- unsigned shared atom accepted;
- tampered atom verifies;
- revoked atom retrieves;
- raw trace object published;
- atom publish path uses no-op scanner fallback;
- docs imply agent-level utility is proven before eval.

## Required machine files

- `.github/workflows/security-gates.yml`
- `scripts/security_gate_check.py`
- `eval/security_hardening_baseline.json`
