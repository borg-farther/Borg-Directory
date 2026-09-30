# Red-team review — epistemic guardrail pivot

> **Historical/internal — not current product documentation.** This is a dated implementation review; use `docs/EPISTEMIC_GUARDRAIL.md` for the current contract.

Status: manual degraded-mode review. Independent delegated agents were unavailable because the configured child model was unsupported. Findings below are grounded in direct source inspection and live tool behavior.

## Executive finding

The pivot is justified, but the dangerous failure is **memory steering**, not missing reasoning capability. Borg must never become another verbose thinker. It should decide when remembered experience is relevant enough to show, expose why, identify conflicts, demand verification, and abstain otherwise.

## CRITICAL

### R1 — Existing `borg_observe` can return confident irrelevant guidance

Live reproduction while asking for Borg project status returned npm-global permission advice. The current observe path combines embedding, BM25, trace, negative-trace, pack, and optional synthesis logic in `borg/integrations/mcp_server.py`; broad similarity can survive before the final wrapper. A deep-thinking product built directly on this text path would amplify the defect.

Required control:
- New core must consume normalized evidence, not `borg_observe` prose.
- Retrieval results remain advisory.
- No relevance/evidence means `NO_CONFIDENT_MATCH`.
- Regression: a release-status/product-strategy task must never receive npm/permission guidance.

### R2 — Experience-following propagates bad memory

ACL 2026 reports that agents often imitate highly similar retrieved executions, including erroneous or misaligned experience. Borg already emits imperative `ACTION`/`STOP` text. Treating local traces or seed packs as authority can therefore reproduce and amplify errors.

Required control:
- Separate `seed_only`, `observed_local`, and `verified_collective`.
- Never label a memory verified from similarity or a single local success.
- Conflicting memories force caution and independent verification.

### R3 — No shared claim/evidence contract exists

Existing rescue/observe outputs provide guidance and outcome capture, but there is no common schema for claims, assumptions, evidence references, contradictions, uncertainty, and verification obligations. An agent can produce a polished conclusion with no machine-detectable support.

Required control:
- One shared packet across Python, CLI, and MCP.
- Unsupported and dangling evidence references are explicit.
- High-risk unsupported material claims block action.

## HIGH

### R4 — `unified_collective_retrieve` ranking is not an authorization decision

The ranker combines text, helpfulness, quorum, and atom presence. A result can have a nonzero score even without strong textual evidence. Callers must impose explicit relevance and evidence-tier rules rather than equating top rank with permission to steer.

### R5 — Local helpfulness is vulnerable to sparse-data overinterpretation

Trace helpfulness defaults and shown/helped counters are useful ranking signals but not proof. One prior success or a default score must remain `observed_local`.

### R6 — Optional synthesis can add unsupported prose

`borg_observe` optionally calls synthesis over retrieved detail. The guardrail core must remain deterministic and model-free; the host model may reason after receiving the bounded packet.

### R7 — Prompt injection can be stored as experience

Learning atoms have scanners, but local traces/failure memory may contain imperative or adversarial text. Every memory lane must be scanned and neutralized before packet emission; blocked content is reported as a safety finding, not forwarded.

### R8 — Deep mode can become process theatre

Past Borg experiments found generic structured phases added token overhead and sometimes reduced performance. Deep mode must be selective and bounded. Explicit deep/high-risk/repeated-failure tasks activate it; easy tasks do not.

### R9 — No contradiction semantics

One memory can say an approach worked while another says to avoid it. Current retrieval can show both without a machine-readable conflict state. Contradiction must downgrade the decision and prevent an authoritative recommendation.

### R10 — Cross-surface drift risk

CLI `observe` records a trace; MCP `borg_observe` retrieves guidance. Rescue, public API, and collective retrieval use different contracts. The new product needs one core function with thin surface adapters and semantic equality tests.

## Required adversarial tests

1. Irrelevant npm trace vs release-status task -> no confident match.
2. Seed guidance -> never verified collective.
3. One local success -> observed only.
4. Three independently verified helpful collective receipts -> may be labelled verified collective, still advisory.
5. Prompt-injection payload in memory -> suppressed.
6. Worked-vs-avoid overlap -> conflict and caution.
7. High-risk unsupported claim -> block pending verification.
8. Low-risk unsupported claim -> caution, not false certainty.
9. Dangling evidence reference -> explicit invalid reference.
10. Easy task in auto mode -> no deep overhead.
11. Same request through Python/CLI/MCP -> same core packet fields.
12. No raw chain-of-thought requested or stored.

## Ship boundary

Passing these tests proves contract integrity, not agent-performance lift. Public claims remain limited until controlled external evidence exists.
