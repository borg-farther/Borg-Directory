# Evidence gates and consequential-agent guardrails — 2026 landscape

## Executive synthesis

"AI guardrail" is not one product category. It spans at least five enforcement layers:

1. **Prompt/content moderation** — classify text before or after generation.
2. **Trajectory/action review** — judge whether an intended action is safe or policy-compliant.
3. **Tool-boundary enforcement** — intercept a named tool call and allow, rewrite, escalate, or deny it.
4. **System/OS enforcement** — observe and constrain subprocesses, filesystem, network, and cross-event state beneath the tool API.
5. **Epistemic/change-control gating** — test whether material operational claims are supported by fresh, scope-bound evidence before consequential effects are accepted.

Borg's credible wedge is layer 5, combined with organisation-specific prior-failure memory. It is not a substitute for layers 3–4. A complete safety architecture would use Borg above a deterministic permission layer and sandbox, never instead of them.

## What the strongest evidence says

### Persistent guidance is not enforcement

[Guardrails Beat Guidance](https://arxiv.org/abs/2604.11088) scraped 679 rule files containing 25,532 rules and ran more than 5,000 Claude Code trials on SWE-bench Verified. Random and curated rule bundles both improved the discriminative subset by 13.8 points, suggesting a large context-priming effect. Every individually beneficial rule in that study was a negative constraint, while every individually harmful one was a positive directive.

Implication for Borg: C0/C1/C2 separation is mandatory. If seeded memory beats no Borg but not empty Borg, the value is scaffold/priming—not accumulated experience. Relevant memory also needs a shuffled-memory control because irrelevant context can perform similarly.

### Learned negative constraints can help, but over-refusal is real

[AgentGuard](https://arxiv.org/abs/2609.16287) learned instruction-level constraints from 461 anomalous traces over 282 tasks and evaluated on a disjoint 100-task set with 600 Docker-isolated executions. It reported abnormal execution falling from 69.0% to 26.7%, successful completion rising from 21.7% to 35.0%, and a 19.3% guarded over-refusal rate.

Implication: prior failures can improve agent behavior, but false intervention is a first-class product cost. Borg must report both unsafe recall and safe false-intervention rate. "More cautious" is not automatically "better."

### Tool-level guardrails miss indirect execution

[ActPlane](https://arxiv.org/abs/2606.25189) argues that tool-call interception cannot see effects hidden in scripts, shell wrappers, or subprocesses. Its eBPF policy engine covers process trees and cross-event policies, reports 2.0–3.2× more resolved policy violations than compared baselines on its decision-compliance benchmark, prevents 74% of baseline-unsafe behavior on 361 personal-assistant tasks, and reports 1.9%–8.4% overhead.

Implication: even a perfect Borg decision packet is not a security boundary. Runtime claims must distinguish advisory review, host-enforced tool interception, and OS-enforced containment.

### Policy and evidence are different questions

[GuardAgent](https://proceedings.mlr.press/v267/xiang25a.html) generates executable checks for safety requests and reports more than 98% and 83% guardrail accuracy on healthcare access-control and web-safety benchmarks. [AgentSpec](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf) places deterministic guards at the tool-call boundary. [ToolSafe](https://arxiv.org/abs/2601.10156) evaluates step-level tool invocation safety and converts detection into corrective feedback.

These systems ask whether an action violates a policy. Borg's current core asks whether a structured claim references any verified evidence. Those are not equivalent. Evidence must be bound to the exact claim, scope, state, time, authority, and proposed effect; reference presence alone is not entailment.

### Evaluation must separate semantic, audit, and execution harm

[SafeClawBench](https://arxiv.org/abs/2606.18356) separates semantic failure from audit-evidence and sandbox harm across 600 adversarial cases. [GuardianAgentBench](https://arxiv.org/abs/2607.20982) evaluates tool choice, arguments, ordering, and omission on production agent frameworks. [ATBench](https://arxiv.org/abs/2604.02022) provides 1,000 complete tool-using trajectories—503 safe and 497 unsafe—with 8 risk-source, 14 failure-mode, and 10 harm categories plus full human audit.

Implication: Borg needs trajectory-level external labels and harm-stage reporting, not only hand-authored unit cases. The first reproducible shadow experiment therefore uses pinned ATBench data while clearly retaining its synthetic-corpus limitation.

## Borg's current mechanism

The current deterministic `deliberate` core has several strong properties:

- no model/API call and no chain-of-thought request;
- explicit standard/deep activation;
- structured claims and evidence references;
- conservative treatment of memory as advisory;
- prompt-injection scanning and suppression of retrieved memory;
- contradiction detection;
- deterministic permit/caution/block packet;
- verification plan and outcome-binding receipt.

Its decisive limitations are equally clear:

1. `verified=true` is a caller attestation, not independently authenticated evidence.
2. Claim support means a verified referenced artifact exists; semantic entailment is not checked.
3. Evidence is not bound to freshness, exact state, authority, or action scope.
4. A dangerous preflight with no claims can return `proceed`; review-stage structure is host-dependent.
5. A single prior failure memory is advisory and normally cannot change the decision.
6. `proceed_with_caution` exits successfully in the CLI unless the host maps it to human review.
7. The host must call Borg at the correct decision point and may ignore its answer.
8. Tool wrappers can be bypassed by indirect subprocess/system actions.

The experiment intentionally tests these boundaries rather than hiding them with task-specific handcrafted checks.

## Product architecture if—and only if—the mechanism earns it

A defensible future evidence gate would require four independent planes:

### 1. Trusted action envelope

Every proposed effect carries actor identity, user intent, tool and arguments, resource scope, reversibility, side-effect class, and authority provenance. Missing fields fail closed for consequential operations.

### 2. Evidence semantics

Evidence connectors independently fetch CI, Git, artifact, cloud, database, or policy state. Evidence is cryptographically or operationally bound to claim, commit/state, timestamp, environment, and scope. The proposing agent cannot mark its own evidence verified.

### 3. Prior-failure intelligence

Outcome-grounded failure memories retrieve relevant negative constraints and required checks. Memory may increase scrutiny or require discriminating evidence, but cannot relax higher-authority policy. Relevant memory must outperform both empty and shuffled memory on held-out tasks.

### 4. Enforcement below reasoning

A deterministic policy layer maps `allow`, `require_human`, and `block` into actual tool execution. Sandboxing/OS controls cover indirect effects. Every override and outcome is receipted. Borg remains a decision input, not the trusted computing base.

## Commercial positioning boundary

Bad positioning:

- "universal AI safety";
- generic prompt moderation;
- a security sandbox;
- a public collective memory network before private value is proven.

Potentially sharp positioning:

> Before an AI coding or operations agent deploys, publishes, migrates, deletes, or approves, Borg requires fresh evidence, checks relevant prior failures, and produces an auditable allow/review/block decision.

Likely buyer: platform engineering, DevSecOps, or regulated operations teams already allowing coding agents to touch consequential systems. The unproven assumptions are willingness to integrate, willingness to pay, and whether real organisation-specific memory adds enough lift beyond deterministic policy. The shadow experiment addresses only the last technical assumption.

## Primary sources

- ATBench dataset card and corpus: https://huggingface.co/datasets/AI45Research/ATBench
- ATBench paper: https://arxiv.org/abs/2604.02022
- Guardrails Beat Guidance: https://arxiv.org/abs/2604.11088
- AgentGuard: https://arxiv.org/abs/2609.16287
- ActPlane: https://arxiv.org/abs/2606.25189
- GuardAgent (ICML 2025): https://proceedings.mlr.press/v267/xiang25a.html
- AgentSpec: https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf
- ToolSafe: https://arxiv.org/abs/2601.10156
- SafeClawBench: https://arxiv.org/abs/2606.18356
- GuardianAgentBench: https://arxiv.org/abs/2607.20982
- OpenAI Agents SDK guardrails: https://openai.github.io/openai-agents-python/guardrails/
- NVIDIA NeMo Guardrails: https://docs.nvidia.com/nemo/guardrails/latest/user-guides/guardrails-library.html
