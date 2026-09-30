# Synthesis — one Borg product, not four pivots

> **Historical/internal — not current product documentation.** This is a dated decision record; use `docs/EPISTEMIC_GUARDRAIL.md` for the current contract.

## Decision

Build Borg as an **epistemic control plane for frontier agents**.

Do not position it as the deep thinker. The host model remains responsible for novel reasoning. Borg supplies governed memory, contradiction detection, uncertainty and claim boundaries, verification obligations, and privacy-safe outcome learning.

## Why this wins

- It matches Borg's existing strongest assets: failure memory, trace retrieval, confidence gates, `ACTION / STOP / VERIFY`, signed outcomes, and learning atoms.
- It addresses the observed live defect: irrelevant retrieved guidance can steer an answer.
- It respects prior experiment results: generic workflow scaffolding adds overhead; selective relevant intelligence can help hard tasks.
- It differentiates from generic memory products: provenance, negative memory, abstention, intervention-bound verification, and governed collective promotion.
- It is testable without fabricating adoption or lift.

## Conflict resolution

| Tension | Resolution |
|---|---|
| Deep mode completeness vs token overhead | Selective activation; bounded artifacts, not verbose prose |
| Useful memory vs memory pollution | Private/local and collective lanes remain separate; promotion requires verified quorum |
| Model self-review vs confirmation bias | Structured claims and independent evidence references; verification factored from generation |
| Fast shipping vs proof | Ship contract tests and fresh-install proof now; keep external-lift claims blocked |
| Automatic learning vs privacy | Local by default; sanitized signed atoms only for sharing |
| Similarity vs truth | Similarity ranks; it never authorizes |

## Delivery slices

### Slice 1 — shared core

- deterministic activation;
- normalized evidence tiers;
- injection suppression;
- claim/reference audit;
- contradiction detection;
- bounded verification plan;
- explicit decisions and claim boundaries.

### Slice 2 — surfaces

- Python `borg.deliberate(...)`;
- CLI `borg deliberate`;
- MCP `borg_deliberate`;
- intervention recording and existing `borg_record_outcome` close loop;
- agent-priming updates.

### Slice 3 — proof

- frozen contract corpus/evaluator;
- targeted RED→GREEN tests;
- cross-surface semantic equality;
- security/readiness gates;
- full suite;
- build and non-repo fresh-install CLI/Python/MCP canary.

### Slice 4 — honest release

- public documentation and architecture/security boundaries;
- no external-lift or viral claims;
- controlled first-10 only after repository/release gates are green;
- exact immutable version approval before package upload.

## Binary acceptance

The feature is implementation-complete only when:

- [ ] one core packet powers Python, CLI, and MCP;
- [ ] irrelevant/unsafe/conflicting memory fails closed;
- [ ] high-risk unsupported claims block;
- [ ] easy tasks avoid deep overhead;
- [ ] outcome receipts bind to the exact intervention;
- [ ] no chain-of-thought is requested or stored;
- [ ] eval corpus passes every hard gate;
- [ ] full configured suite passes;
- [ ] wheel builds;
- [ ] fresh isolated install proves CLI, Python, and stdio MCP;
- [ ] public claims remain within measured evidence;
- [ ] final branch is committed and ready for review.

## Product sentence

> Borg gives capable AI agents memory with standards: prior experience is retrieved with provenance, conflicting or unsupported guidance is stopped, verification is mandatory, and only outcomes that survive evidence and privacy gates can become collective knowledge.
