# Architecture specification — Borg as an epistemic control plane

> **Historical/internal — not current product documentation.** This is a dated design artifact; use `docs/EPISTEMIC_GUARDRAIL.md` for the current contract.

## Product decision

Do **not** pivot Borg into a competing deep-thinking model. Pivot it into the evidence-and-experience control plane around frontier models.

> The host model proposes and reasons. Borg retrieves prior experience, classifies its evidential strength, exposes conflicts and unsupported claims, requires verification, abstains when evidence is weak, and converts verified outcomes into privacy-safe collective memory.

This unifies four useful roles without pretending Borg generates superior raw reasoning:

1. memory for the deep thinker;
2. brake on confident unsupported output;
3. verified collective learning between agents;
4. selective ultra-deep workflow for consequential tasks.

## Research grounding

- The 2026 agent-memory survey frames memory as a `write -> manage -> read` loop and identifies contradiction handling, write filtering, privacy, and downstream evaluation as open production problems.
- Xiong et al. (ACL 2026) show experience-following can propagate errors and replay misaligned memories; future outcome evaluation is needed as a quality label.
- CoMem (2026) separates private experience from curated collective wisdom and promotes only repeatedly verified knowledge, reducing memory pollution.
- Chain-of-Verification shows checking should be factored from generation to reduce confirmation bias.
- SWE-Explore (2026) separates repository exploration from patch synthesis; retrieved navigation evidence is valuable without replacing the solver.

Primary sources:
- https://arxiv.org/abs/2603.07670
- https://aclanthology.org/2026.acl-long.27/
- https://arxiv.org/abs/2609.15009
- https://arxiv.org/abs/2606.07297

## System boundary

```text
User task / draft / structured claims
                |
                v
      Selective activation policy
   standard | auto | explicit deep
                |
                v
       PRIVATE MEMORY LANE                 COLLECTIVE MEMORY LANE
 local traces + failure memory      signed atoms + verified receipts/quorum
                |                                  |
                +-------- scan + normalize --------+
                                   |
                         relevance/evidence tiers
                                   |
                   claim + assumption + conflict audit
                                   |
                    machine-readable epistemic packet
                                   |
                     frontier host model acts/revises
                                   |
                         independent verification
                                   |
                   intervention-bound outcome receipt
                                   |
                    local learning -> curated promotion
```

## Activation policy

Modes:

- `standard`: bounded packet, no deep workflow.
- `auto`: deep only for deterministic signals: repeated failures, high/critical risk, explicit deep/adversarial/production/security/release language, or a review containing material unsupported claims.
- `deep`: explicit activation.

The policy is intentionally deterministic and inspectable. It does not call an LLM to decide whether an LLM needs more reasoning.

## Stages

### Preflight

Before work:
- classify activation;
- retrieve and tier memory;
- expose known dead ends and conflicts;
- list assumptions and uncertainty;
- provide bounded disconfirming questions;
- require a verification plan.

### Review

After a draft:
- ingest host-supplied structured claims;
- resolve evidence references;
- mark unsupported or dangling references;
- detect memory contradiction;
- return `proceed`, `proceed_with_caution`, or `block_pending_verification`.

### Close

Reuse the existing `borg_record_outcome` receipt path. The epistemic packet is recorded as an intervention; the outcome must bind back to that intervention and include verification evidence before it can influence collective promotion.

## Packet contract

Required top-level fields:

- `schema_version`
- `status`
- `stage`
- `mode_requested`
- `mode_selected`
- `decision`
- `activation_reasons`
- `task`
- `memory_status`
- `memory_items`
- `claims`
- `unsupported_claims`
- `invalid_evidence_refs`
- `assumptions`
- `contradictions`
- `uncertainties`
- `challenges`
- `stop_conditions`
- `verification_plan`
- `safety_findings`
- `provenance`
- `claim_boundaries`
- `outcome_capture`

Decision vocabulary:
- `proceed`
- `proceed_with_caution`
- `block_pending_verification`
- `invalid_input`

Memory vocabulary:
- `no_confident_match`
- `advisory_only`
- `verified_collective`
- `conflicted`

## Evidence tiers

- `seed_only`: bundled/static knowledge; no measured collective proof.
- `observed_local`: local trace/failure history; useful but not independently verified.
- `unverified`: imported or incomplete evidence.
- `verified_collective`: outcome-grounded evidence meeting existing conservative quorum semantics.

All tiers remain advisory. `verified_collective` changes confidence and prioritization, not permission to bypass verification.

## Contradiction semantics

A contradiction exists when a normalized worked/recommendation statement materially overlaps another memory's avoid/dead-end statement. Consequences:

1. `memory_status=conflicted`;
2. `decision>=proceed_with_caution`;
3. no authoritative recommended action;
4. verification plan must discriminate between the conflicting conditions.

## Claim semantics

The host supplies claims as structured artifacts; Borg does not extract private reasoning or invent claims.

A claim is unsupported when:
- it has no `evidence_refs`; or
- a reference does not resolve to an evidence item or normalized memory source ID.

For high/critical risk, unsupported material claims block action. For lower risk, they force caution.

## Security and privacy

- No raw chain-of-thought required, exposed, or persisted.
- Memory text is prompt-injection scanned and neutralized before use.
- Blocked memory is omitted and reported as a safety finding.
- Raw private traces remain local.
- Collective promotion continues to require sanitized signed artifacts, trusted-tenant outcome evidence, quorum, and revocation.
- Remote HTTP exposure remains governed by its stricter allowlist; this feature is local CLI/stdio MCP first.

## Compatibility

- Existing rescue/observe APIs remain available.
- New surfaces are thin adapters around one core module.
- Existing `borg_record_outcome` remains the close-loop tool.
- No new external dependency or model API is required.

## Anti-goals

- Generic chain-of-thought generation.
- Mandatory verbose phases on every task.
- Majority vote presented as truth.
- Similarity presented as evidence.
- Synthetic/test telemetry presented as adoption.
- One-agent experience promoted as collective consensus.
