# Borg Privacy-Safe Collective Intelligence — Documentation Checklist

**File rev:** 20260503-0835 rev A  
**Companion spec:** `20260503-0835_borg-privacy-safe-collective-intelligence-master-build-spec.md`

---

## 1. Documentation standard

Every doc must be explicit enough that a skeptical first user can answer:

1. What does Borg collect?
2. What does Borg never collect?
3. What stays local?
4. What can leave the machine?
5. How is PII blocked?
6. How is prompt injection blocked?
7. How are atoms signed and revoked?
8. What claims are proven vs unproven?
9. How do I disable export/sync?
10. How do I delete/revoke submitted knowledge?

No vague privacy language. No “we take privacy seriously.” Concrete mechanisms only.

---

## 2. Required docs

### 2.1 `docs/PRIVACY_MODEL.md`

Must include:

- raw trace lifecycle;
- local-only default;
- distinction between raw traces and learning atoms;
- fields allowed in shared atoms;
- fields forbidden in shared atoms;
- scanner classes;
- quarantine behavior;
- deletion/revocation behavior;
- threat model summary;
- user/operator controls.

Required exact sentence:

> Borg does not upload raw agent conversations, raw traces, tool outputs, source files, screenshots, or environment variables to shared collective memory. Shared collective memory accepts only signed, sanitized, revocable learning atoms.

Acceptance checks:

- contains “raw traces are local-only”;
- contains “learning atoms”;
- contains “revocation”;
- contains “prompt injection”;
- contains “secrets”;
- does not imply agent-level utility is proven.

### 2.2 `docs/LEARNING_ATOM_SCHEMA.md`

Must include:

- canonical JSON schema;
- example safe atom;
- example rejected raw trace;
- example quarantined atom;
- signature envelope schema;
- lifecycle statuses;
- atom ID calculation;
- canonicalization rules;
- compatibility/versioning policy.

Acceptance checks:

- every field has type + allowed values;
- forbidden fields listed explicitly;
- example includes `privacy`, `safety`, `trust`, and `lifecycle` sections;
- schema maps to implementation in `borg/core/learning_atoms.py`.

### 2.3 `docs/PROMPT_INJECTION_THREAT_MODEL.md`

Must include:

- ingestion attacks;
- retrieval attacks;
- poisoning attacks;
- indirect prompt injection examples;
- policy override examples;
- exfiltration examples;
- how scanner detects them;
- why retrieval wrapper is defense-in-depth, not primary control;
- test command proving coverage.

Acceptance checks:

- contains examples for “ignore previous instructions”, “exfiltrate credentials”, “future agent must”, and hidden markdown/html payloads;
- explains all memory is untrusted advisory data;
- links to `borg/tests/test_prompt_injection.py`.

### 2.4 `docs/TRUST_AND_PROMOTION.md`

Must include:

- Ed25519 signing model;
- what signatures prove and do not prove;
- reputation model reuse;
- tenant pseudonym/HMAC model;
- cross-tenant quorum requirement;
- promotion statuses: local → org → global_candidate → published;
- sybil risk and mitigations;
- rate limits;
- manual review path;
- rollback/revocation.

Acceptance checks:

- explicitly says “signature proves integrity, not truth”;
- explicitly says “agent count does not equal tenant independence”;
- includes global promotion rule requiring independent tenants.

### 2.5 `docs/REVOCATION_AND_DELETION.md`

Must include:

- atom tombstones;
- who can revoke;
- revocation reasons;
- how retrieval suppresses revoked atoms;
- deletion vs tombstone distinction;
- reimport suppression;
- key compromise flow;
- user privacy deletion request flow.

Acceptance checks:

- links to `atom_tombstones` table;
- includes test command for revoked atom retrieval suppression.

### 2.6 `docs/EVAL_PLAN_FAILURE_MEMORY.md`

Must include:

- C0/C1/C2 design;
- hypotheses;
- null/alternative;
- task calibration;
- randomization;
- repeated runs;
- power notes;
- metrics: solve rate, tool calls, tokens, negative transfer, retrieval precision;
- required thresholds;
- reporting template.

Acceptance checks:

- C2 vs C1 is named as pure knowledge value;
- no utility claim without statistical evidence;
- includes minimum sample sizes and confidence intervals.

### 2.7 `docs/SECURITY_HARDENING_BASELINE.md`

Must include:

- threat model;
- secrets policy;
- prompt-injection controls;
- atom policy controls;
- CI gates;
- static/dependency/secret scan commands;
- release blocker list;
- exact test commands.

Acceptance checks:

- references `.github/workflows/security-gates.yml`;
- references `scripts/security_gate_check.py`;
- references `eval/security_hardening_baseline.json`.

---

## 3. README / marketing claim edits

Update top-level README or product docs to avoid overclaiming.

Allowed language:

> Borg is building privacy-safe collective memory for agents using signed, sanitized learning atoms. Raw traces remain local by default. Agent-level utility is under active evaluation.

Forbidden language until eval passes:

- “proven 30% improvement”;
- “learns from every agent” without privacy qualifier;
- “collects traces” as a central/shared claim;
- “zero risk”;
- “fully anonymous”;
- “validated at scale”;
- “10m-agent ready” before M2 gates.

---

## 4. User-facing FAQ

Required FAQ entries:

### Q: Does Borg upload my prompts or files?

Answer must say: no raw prompts/files to shared memory; local raw traces may exist depending on config; shared memory uses learning atoms.

### Q: What is a learning atom?

Answer must explain: minimal reusable lesson with error pattern, worked/avoid approach, evidence, privacy metadata, safety metadata, signature, lifecycle.

### Q: Can I inspect what would be shared?

Answer must include CLI command once implemented:

```bash
borg atom distill --trace-id <id> --dry-run
```

### Q: Can I disable sharing?

Answer must include config flag once implemented. Default should be local-only.

### Q: How do I delete/revoke an atom?

Answer must include revoke command:

```bash
borg atom revoke <atom-id> --reason "privacy request"
```

### Q: Can prompt injection poison Borg?

Answer must explain deterministic scanner, quarantine, signed atoms, retrieval firewall, reputation/quorum.

---

## 5. Docs-to-code consistency checks

Add to `scripts/security_gate_check.py` or a dedicated docs check:

- docs mention files that exist;
- CLI commands mentioned either exist or are marked “planned” until implemented;
- docs do not make forbidden claims;
- docs include required exact privacy sentence;
- schema examples validate against `validate_learning_atom()`;
- test commands execute or are marked not-yet-implemented in pre-M0 branch.

---

## 6. Signoff gate

Docs are complete only when:

- all required docs exist;
- README/product claims are scrubbed;
- schema examples validate;
- FAQ answers are explicit;
- docs link to tests/evidence;
- docs say what is unproven;
- docs do not imply raw central trace collection.

---

## 7. Binary checklist

- [ ] `docs/PRIVACY_MODEL.md`
- [ ] `docs/LEARNING_ATOM_SCHEMA.md`
- [ ] `docs/PROMPT_INJECTION_THREAT_MODEL.md`
- [ ] `docs/TRUST_AND_PROMOTION.md`
- [ ] `docs/REVOCATION_AND_DELETION.md`
- [ ] `docs/EVAL_PLAN_FAILURE_MEMORY.md`
- [ ] `docs/SECURITY_HARDENING_BASELINE.md`
- [ ] README claim scrub complete
- [ ] FAQ complete
- [ ] docs check script passes
- [ ] no forbidden claim remains

Docs status is **COMPLETE** only when every box is checked by testable file existence/content checks, not manual vibes.
