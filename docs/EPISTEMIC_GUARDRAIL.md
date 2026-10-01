# Borg epistemic guardrail and selective deep mode

## Purpose

Borg is not a replacement reasoning model. A capable host model still proposes hypotheses, writes code, and makes decisions. Borg controls the evidence boundary around that reasoning:

- retrieve prior failure/success memory without presenting similarity as truth;
- keep local/private experience separate from verified collective evidence;
- expose assumptions, unsupported claims, dangling evidence references, and conflicting memories;
- stop consequential action when material claims remain unsupported;
- require independent verification;
- bind the observed outcome back to the exact intervention so only verified, privacy-safe learning can compound.

The output is a bounded **epistemic packet**, not private chain-of-thought.

## When to use it

Use `borg rescue` / `error_lookup` for a concrete error or failing command.

Use `borg deliberate` when any of these apply:

- the user explicitly asks for deep or adversarial review;
- the task is production, security, privacy, deployment, migration, release, financial, legal, destructive, or otherwise high-risk;
- two or more attempts have failed;
- a draft contains material claims that must be audited before action;
- remembered approaches may conflict or may have gone stale.

Do not force deep mode onto trivial work. In `auto` mode, easy tasks remain `standard` and receive only the smallest decisive-test obligation.

## Lifecycle

```text
preflight -> host work/reasoning -> review -> independent verification -> borg_record_outcome
```

### 1. Preflight

```bash
borg deliberate "plan a production database migration" --mode auto --json
```

The packet selects `standard` or `deep`, retrieves advisory memory, lists uncertainty and stop conditions, and supplies a verification plan.

Memory status is explicit: `no_confident_match`, `retrieval_degraded`, `advisory_only`, `verified_collective`, or `conflicted`. `retrieval_degraded` is deliberately different from `no_confident_match`: an unavailable lane is not evidence that no prior result exists.

### 2. Review

The host submits structured material claims. Borg does not infer hidden reasoning from prose.

```bash
borg deliberate "approve production release" \
  --stage review --risk high \
  --claims-json '[
    {"id":"suite","text":"The full suite passes","material":true,"evidence_refs":["ci-run"]}
  ]' \
  --evidence-json '[
    {"id":"ci-run","type":"test_result","source":"ci://run/123","summary":"exit 0","verified":true}
  ]' \
  --json
```

Decision values:

- `proceed`
- `proceed_with_caution`
- `block_pending_verification`
- `invalid_input`

The CLI exits `2` for `block_pending_verification`, `1` for invalid input, and `0` for other valid decisions.

### 3. Close the loop

CLI and MCP adapters store a privacy-redacted local intervention by default and return its `intervention_id`. After executing the verification plan, call `borg_record_outcome` with that exact id and the observed result. Side-effect-free probes can disable this with CLI `--no-record` or MCP `record_intervention: false`.

A verified outcome is not automatically shareable collective proof. Existing signed-receipt, trusted-tenant, verification-output, quorum, privacy, prompt-injection, revocation, and promotion gates still apply.

## Activation policy

| Requested mode | Selection |
|---|---|
| `standard` | Always standard |
| `deep` | Always deep |
| `auto` | Deep only for repeated failures, high/critical risk, or deterministic high-stakes/deep language |

The policy is deterministic and inspectable. It does not use an LLM to decide whether an LLM should think harder.

## Evidence tiers

| Tier | Meaning | May it authorize action? |
|---|---|---|
| `seed_only` | Bundled/static guidance | No |
| `observed_local` | Local trace or failure memory | No |
| `unverified` | Imported/incomplete evidence | No |
| `verified_collective` | Store-verified provenance plus at least three verified tenants, at least three helpful outcomes, and no negative majority | No; still advisory |

Only trusted local adapters can mark store provenance as verified. MCP callers cannot inject arbitrary `memory_items` into `borg_deliberate`.

A top-ranked retrieval is not proof. Borg applies a separate lexical relevance boundary before collective or local memory enters the packet.

## Claim contract

Claims are explicit objects:

```json
{
  "id": "claim-1",
  "text": "The full regression suite passes",
  "kind": "material",
  "material": true,
  "evidence_refs": ["ci-run-123"]
}
```

Evidence is explicit too:

```json
{
  "id": "ci-run-123",
  "type": "test_result",
  "source": "ci://run/123",
  "summary": "exit 0",
  "locator": "https://ci.example/runs/123",
  "verified": true
}
```

Borg reports:

- `unsupported_claims`: no evidence references, or dangling references;
- `unverified_support_claims`: references resolve only to advisory memory/evidence;
- `invalid_evidence_refs`: exact claim-to-missing-reference mapping.

At high/critical risk, an unsupported material claim returns `block_pending_verification`.

Deterministically recognized production/security/release/destructive language is consequential even when the caller omits `risk_level`; unsupported material claims still block. Duplicate evidence ids are downgraded to unverified, and duplicate/empty claims fail closed.

`verified: true` is a caller attestation at the review boundary, not cryptographic proof. The final outcome path is stricter: shareable verification requires an intervention-bound signed receipt, verification procedure, exit/result evidence, output hash, and trusted tenant identity.

## Contradictions

Borg compares each memory's `worked`/summary path against other memories' `avoid` paths. A material overlap produces:

- `memory_status=conflicted`;
- `decision=proceed_with_caution` or stricter;
- an explicit contradiction object with source ids and overlap terms;
- a stop condition requiring a discriminating check.

Borg does not vote between conflicting memories.

## Prompt-injection boundary

Every retrieved memory item is scanned before packet emission. Blocked content is omitted. The packet exposes only finding classes, scores, and evidence hashes; it does not echo the unsafe payload.

This protects against stored instructions such as prompt overrides, credential exfiltration, tool coercion, hidden instructions, and retrieval poisoning. The scanner is deterministic and conservative; a suppressed memory does not become evidence.

## Verification plan

Deep/review/high-risk packets always contain all four categories:

1. `scope` — reproduce or bound exact current state;
2. `independent_evidence` — inspect a primary source or direct system artifact;
3. `decisive_test` — execute the smallest falsifying check;
4. `disconfirm` — search for counterexamples, regressions, or changed conditions.

Caller-supplied steps are retained and missing categories are appended. Borg does not invent a project-specific shell command when none was provided.

## Python API

```python
import borg

packet = borg.deliberate(
    "review a production deployment",
    context="rollback is expensive",
    mode="auto",
    stage="preflight",
    risk_level="high",
    assumptions=["The schema is backward-compatible"],
)

assert packet.mode_selected == "deep"
print(packet.decision)
print(packet.to_dict())
```

The public Python API is read-only by default. CLI and MCP adapters add local intervention recording by default, with explicit no-record modes for probes.

## MCP API

Tool: `borg_deliberate`

Inputs mirror the Python core except for `memory_items`, which is deliberately not exposed. `record_intervention` defaults to `true`; set it to `false` for a side-effect-free call. The response contains:

```json
{
  "success": true,
  "epistemic_packet": {"...": "..."},
  "text": "concise human rendering"
}
```

The packet's `outcome_capture` includes a locally recorded `intervention_id` when recording is enabled and the local store is available. If recording degrades, the packet remains usable but reports `recording_unavailable`; if disabled, it reports `not_recorded_by_request` without an intervention id. Neither state may pretend the learning loop closed.

## Packet schema summary

Required top-level fields:

- identity: `schema_version`, `packet_id`, `status`, `stage`;
- activation: `mode_requested`, `mode_selected`, `activation_reasons`;
- decision: `decision`, `stop_conditions`, `verification_plan`;
- memory: `memory_status`, `memory_items`, `contradictions`, `safety_findings`;
- review: `claims`, `unsupported_claims`, `unverified_support_claims`, `invalid_evidence_refs`, `assumptions`, `evidence`;
- uncertainty: `uncertainties`, `challenges`, `claim_boundaries`;
- provenance/learning: `provenance`, `outcome_capture`.

Serialization and rendering are deterministic for identical inputs and memory.
The deterministic `packet_id` binds the normalized claims, evidence, assumptions, verification plan, memory content references, and a SHA-256 digest of the reviewed draft; changing any decision-relevant artifact changes the id without persisting the draft itself.

## Evaluation

Run the frozen contract corpus:

```bash
python eval/epistemic_guardrail_eval.py
```

Hard gates cover:

- zero false-confidence on labelled high-risk unsupported cases;
- zero unsafe-memory emission;
- complete `NO_CONFIDENT_MATCH` honesty;
- complete contradiction detection;
- complete deep verification plans;
- activation on labelled deep cases and non-activation on labelled trivial cases.

These are **contract tests**, not evidence of external agent-performance lift. The controlled product experiment remains:

- C0: frontier agent without Borg;
- C1: same agent with guardrail but empty memory;
- C2: same agent with guardrail and relevant outcome-grounded memory.

C2 vs C1 measures memory value; C1 vs C0 measures guardrail overhead. Until held-out external evidence exists, Borg does not claim improved task success, token savings, adoption, or network effects.

## Security and privacy guarantees

- No private chain-of-thought requested, returned, or persisted.
- Raw local traces stay local.
- Intervention guidance is privacy-redacted before local persistence.
- Stored memory is prompt-injection scanned before retrieval use.
- Similarity and rank never authorize action.
- Seed/local experience never becomes collective proof by field spoofing.
- Collective promotion retains signed artifacts, verified outcomes, trusted-tenant quorum, revocation, and kill-switch controls.
- Remote HTTP tool exposure remains separately allowlisted; this feature is local CLI and stdio MCP first.

## Known boundary

Borg can verify that a claim references an evidence artifact and that the caller attests it was verified. It cannot independently know whether a human or host fabricated that artifact. Consequential systems must retain their own authentication, authorization, sandboxing, approval, and audit controls. Borg is an epistemic guardrail, not a security permission system.
