# Borg Privacy-Safe Collective Intelligence — Adversarial Spec Review

**File rev:** 20260503-0835 rev A  
**Reviewed artifacts:**

- `20260503-0835_borg-privacy-safe-collective-intelligence-master-build-spec.md`
- `20260503-0835_borg-privacy-safe-collective-intelligence-test-matrix.md`
- `20260503-0835_borg-privacy-safe-collective-intelligence-docs-checklist.md`

---

## 1. Review verdict

The spec is delivery-grade for M0 because it does three things correctly:

1. It chooses the right primitive: signed, sanitized, revocable learning atoms.
2. It builds on existing Borg modules instead of replacing them.
3. It defines hard safety/eval gates before scale claims.

It should not yet be treated as a full 10m-agent platform spec. It is correctly scoped as **M0/M1/M2 architecture with 10m-compatible seams**.

---

## 2. Red-team findings

### R1 — Semantic PII remains hard

**Severity:** HIGH  
**Issue:** deterministic scanner cannot reliably catch names, proprietary facts, or context-specific PII.  
**Spec coverage:** acknowledges this and restricts global atoms to minimized schema.  
**Required implementation discipline:** global atoms should avoid open-ended free text where possible; `learning.worked`, `learning.avoid`, and `learning.why` need max length and scanner pass.

### R2 — Prompt-injection scanner can be bypassed

**Severity:** HIGH  
**Issue:** deterministic phrase detectors miss obfuscated payloads.  
**Spec coverage:** includes hidden markdown/html/base64/zero-width checks and retrieval stripping.  
**Required implementation discipline:** never rely on retrieval warning alone. Strip dangerous classes before storage.

### R3 — Cross-tenant quorum is underspecified for M2

**Severity:** MEDIUM  
**Issue:** spec says independent tenants, but not how tenant identity is proven.  
**Resolution:** acceptable for M0. Add M2 requirement: tenant authority registry / verified org key / billing-domain proof / admin-issued tenant signing key.

### R4 — Utility preservation may fail

**Severity:** HIGH  
**Issue:** safe atoms could become generic and useless.  
**Spec coverage:** explicit >=80% utility preservation and C2 vs C1 eval gate.  
**Required implementation discipline:** do not ship global sharing if utility fails; keep local/org richer than global.

### R5 — Existing `publish.py` fallback no-op scanner is dangerous

**Severity:** CRITICAL  
**Issue:** current code has no-op fallback imports.  
**Spec coverage:** hard blocker says atom publish must fail if scanner unavailable.  
**Required implementation discipline:** learning_atom artifact path must import real modules or raise.

### R6 — Signing could be misunderstood as trust

**Severity:** MEDIUM  
**Issue:** signature proves integrity, not truth/safety.  
**Spec coverage:** docs checklist explicitly requires this wording.  
**Required implementation discipline:** UI/retrieval output should show trust separately from signature validity.

### R7 — Atom store could duplicate existing `AgentStore`

**Severity:** LOW  
**Issue:** another SQLite DB adds complexity.  
**Resolution:** acceptable for M0 because raw traces, packs, and atoms have different semantics. Later migration can consolidate after API stabilizes.

### R8 — Scope model needs config defaults

**Severity:** MEDIUM  
**Issue:** spec says local-only default but does not define config key.  
**Patch recommendation:** add `borg.collective.mode = local_only|org_opt_in|global_opt_in`, default `local_only`.

---

## 3. Blue-team validation

The architecture is coherent:

- raw traces stay in `traces.py` local path;
- atoms are a separate safe object;
- privacy scanner is upgraded rather than replaced;
- signing reuses `crypto.py`;
- reputation reuses `db/reputation.py` but does not overclaim;
- atom matcher parallels trace matcher instead of contaminating raw-trace semantics;
- publish path gets a new `learning_atom` branch with fail-closed semantics.

The separation between **local trace** and **shared atom** is the most important design choice and should not be compromised during implementation.

---

## 4. Green-team measurement critique

The eval plan is strong enough for product discipline, but implementation should create fixture corpora early:

- `privacy_cases.jsonl`
- `prompt_injection_cases.jsonl`
- `safe_learning_atom_cases.jsonl`

Without frozen corpora, thresholds will drift.

Utility eval must avoid Borg’s prior measurement mistakes:

- no fabricated tasks;
- no post-hoc task inclusion;
- no unpaired comparisons;
- no C2 vs C0 only; C2 vs C1 is the real knowledge effect;
- report negative transfer.

---

## 5. Required patch before implementation

Patch master spec during implementation planning to include explicit config defaults:

```text
borg.collective.mode = local_only | org_opt_in | global_opt_in
Default: local_only
```

And hard rule:

```text
No atom leaves the machine unless collective mode is org_opt_in or global_opt_in and policy passes.
```

---

## 6. Final score

| Dimension | Score |
|---|---:|
| problem definition | 9/10 |
| builds on existing code | 9/10 |
| privacy/security rigor | 8.5/10 |
| prompt-injection treatment | 8/10 |
| implementation clarity | 8.5/10 |
| eval discipline | 8.5/10 |
| risk honesty | 9/10 |
| anti-gold-plating | 8/10 |

Overall: **8.7/10 delivery-grade M0 spec**.

The spec is strong enough to hand to implementers. The only mandatory pre-implementation patch is explicit config defaults; otherwise implementers may accidentally make export opt-out instead of opt-in.
