# Borg Security Hardening Baseline

**Rev:** 20260930-1141

## Scope

Security baseline for privacy-safe failure memory, epistemic packets, and opt-in learning atoms.

## Controls

- raw traces local-only by default;
- shared memory accepts only signed learning atoms;
- structured privacy scanner blocks PII/secrets;
- prompt-injection scanner blocks poisoned memory;
- priming/setup surfaces forbid promoting retrieved text into system/developer instructions;
- every epistemic memory lane is scanned before packet emission; blocked payload text is not echoed;
- atom policy rejects/quarantines unsafe payloads;
- tombstones suppress revoked atoms;
- retrieval firewall marks memory as untrusted historical advice;
- similarity never authorizes action and all packet memory remains advisory;
- local/seed metadata cannot spoof verified-collective evidence;
- high-risk unsupported material claims block pending verification;
- unavailable retrieval lanes emit `retrieval_degraded`, never a false `NO_CONFIDENT_MATCH`;
- duplicate evidence ids are downgraded to unverified and cannot support a claim;
- epistemic packets request/store decision artifacts, never private chain-of-thought;
- publish path for learning atoms fails closed.

## Implemented CI gates

- secret scan: `gitleaks/gitleaks-action`
- dependency audit: `pip-audit`
- static security scan: `bandit`
- policy enforcement: `python scripts/security_gate_check.py`
- M0 tests:

```bash
python -m pytest -q tests/security/test_privacy_structured.py tests/security/test_prompt_injection.py tests/security/test_learning_atoms.py tests/security/test_atom_policy.py tests/security/test_atom_retrieval_firewall.py tests/security/test_atom_store.py tests/security/test_learning_atom_publish.py
python -m pytest -q tests/core/test_epistemic_guardrail.py tests/mcp/test_borg_deliberate.py
```

## Release blockers

- any secret reaches shared atom store;
- any high-risk PII reaches shared atom store;
- unsigned shared atom accepted;
- tampered atom verifies;
- revoked atom retrieves;
- raw trace object published;
- unsafe memory content appears in an epistemic packet;
- any priming surface tells an agent to inject retrieved text as a system/developer message;
- seed/local/forged metadata is labelled verified collective;
- high-risk unsupported material claim receives `proceed`;
- a retrieval failure is reported as `no_confident_match`;
- any surface requests or persists private chain-of-thought;
- atom publish path uses no-op scanner fallback;
- docs imply agent-level utility is proven before eval.

## Required machine files

- `.github/workflows/security-gates.yml`
- `scripts/security_gate_check.py`
- `eval/security_hardening_baseline.json`
