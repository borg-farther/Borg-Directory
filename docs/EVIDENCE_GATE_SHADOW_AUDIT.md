# Independent audit — Borg evidence-gate shadow experiment

> **Historical/internal — not current product documentation.** Post-experiment operator audit; not a runtime-safety claim.

## Decision

**`NO_GO_STOP` is correct.**

The experiment did not validate the proposition that the current Borg mechanism can serve as an evidence gate for consequential AI-agent work. Runtime-enforcement work must stop under the preregistered decision rule.

This is a mechanism verdict, not a universal claim that evidence gates are impossible.

## Evidence chain

| artifact | immutable reference |
|---|---|
| preregistration commit | `eb285466df2b1da6e0c73bbc92925eeb69e0878d` |
| protocol blob SHA-256 | `3a80532445965ffa2df576d32c90c5997fe00f979c3436309a2b59ceb9db6ebd` |
| implementation commit used for execution | `962b9d5700cbe45960fea05c2fc1daae9d93a2bb` |
| ATBench revision | `4476ef92ed8f85c8d58d8a5b9dfdf55aa7893138` |
| ATBench source SHA-256 | `80c534b5f3517c872b528a2e6b64e34495206968edd184f4aed563d39f0cca09` |
| prediction fingerprint | `44eedc26b73ec397dea3eacb90d5acd888a4511eb3ad2122ecc95e74e5bfc55e` |

Git proves that the protocol blob at the preregistration commit and implementation commit is identical. The confirmatory run began from a clean implementation commit. A second execution reproduced the same verdict, failed-gate set, and prediction fingerprint.

## Integrity audit

All experiment-integrity controls passed:

- exact 18,335,079-byte source artifact and SHA-256;
- exactly 1,000 source trajectories with 503 safe and 497 unsafe labels;
- three disclosed pilot IDs excluded before splitting;
- deterministic stratified split: 698 training and 299 held-out trajectories;
- 348 failure-memory rows built from unsafe training cases only;
- no train/evaluation overlap;
- exactly 1,196 condition results: 299 cases × four paired conditions;
- C0 made zero Borg calls;
- C1 made one call with empty memory;
- C2 and C3 made one call each with equal nonzero memory dose and distinct bundles;
- 299 unique held-out guardrail inputs;
- no held-out label, reviewer reason, risk source, failure mode, or harm field crossed the adapter boundary;
- zero invalid epistemic packets;
- independent recomputation reproduced every confusion-matrix cell.

The source benchmark is synthetic but externally published and human-audited. That limits ecological validity but does not rescue a mechanism that fails this easier controlled test.

## Confirmatory results

There were 148 unsafe and 151 safe held-out trajectories.

| condition | TP | FN | FP | TN | unsafe recall | safe false-intervention | balanced accuracy | hard blocks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C0 no gate | 0 | 148 | 0 | 151 | 0.0% | 0.0% | 50.0% | 0 |
| C1 empty gate | 0 | 148 | 0 | 151 | 0.0% | 0.0% | 50.0% | 0 |
| C2 relevant memory | 53 | 95 | 66 | 85 | 35.8% | 43.7% | 46.1% | 0 |
| C3 shuffled memory | 53 | 95 | 66 | 85 | 35.8% | 43.7% | 46.1% | 0 |

### C1 versus C0

C1 produced exactly the same safety classification as having no gate: every trajectory was allowed.

The common adapter gave each material claim references to directly observed user/tool artifacts marked `verified=true`. Borg verified reference resolution, not whether those artifacts semantically established authorization, factual entailment, bounded scope, or safety. Therefore unsafe trajectories with successful tool output looked fully supported.

### C2 versus C1

Memory changed 119 of 299 decisions from allow to human review:

- it corrected 53 unsafe cases;
- it incorrectly escalated 66 safe cases;
- unsafe recall rose by 35.8 percentage points;
- safe false-intervention rose by 43.7 percentage points;
- overall balanced accuracy fell from 50.0% to 46.1%;
- exact paired McNemar p = `0.271248337759`.

The memory arm therefore created more classification harms than corrections and did not significantly improve paired correctness.

### C2 versus C3

Relevant and wrong-case memory produced identical aggregate confusion matrices.

They disagreed on 126 individual trajectories, but the swaps were perfectly symmetric:

- 63 cases where C2 was correct and C3 wrong;
- 63 cases where C3 was correct and C2 wrong;
- unsafe-recall difference: 0.0 percentage points;
- safe false-intervention difference: 0.0 percentage points;
- paired McNemar p: 1.0;
- recall-difference bootstrap 95% CI: `[-0.101351, 0.101351]`.

This is decisive against the proposed memory mechanism. Relevant failure memory behaved like a noisy trigger, not a relevance-specific safety signal.

## Safety failure severity

C2 missed 95 of 148 unsafe trajectories and 59 unsafe trajectories in preregistered critical-harm categories.

Selected slice recall:

- physical and health harm: 14.3%;
- public-service and resource harm: 16.7%;
- security and system-integrity harm: 30.0%;
- financial and economic harm: 36.4%;
- privacy and confidentiality harm: 55.0%.

C2 also escalated 50.7% of benign cases and 71.4% of safe physical/health cases. A gate with this profile would simultaneously create alert fatigue and leave most consequential failures untouched.

No guarded condition hard-blocked a single unsafe trajectory. Every intervention was only `proceed_with_caution`, which the current CLI maps to exit code 0.

## What did work

The experiment should not hide positive engineering facts:

- deterministic execution and packet serialization were stable;
- source, split, label-leakage, condition-fidelity, and output-integrity checks held;
- median C2 latency was 7.770 ms and p95 was 13.856 ms, well under the 250 ms gate;
- prompt-injection scanning safely suppressed some hostile memory content;
- the guardrail correctly blocks explicitly unsupported high-risk structured claims in its frozen contract tests.

Those are useful properties of an advisory claim-reference checker. They are not evidence of a runtime action guardrail.

## Root-cause analysis

### 1. Evidence presence is not evidence entailment

The core treats a material claim as supported when one referenced evidence object has `verified=true`. It does not prove that the evidence means what the claim says, is fresh enough, matches the requested scope, or authorizes the action.

### 2. Verification trust is delegated to the caller

`verified=true` is explicitly a caller attestation. The gate cannot independently authenticate the artifact or prevent an agent-controlled adapter from marking its own evidence verified.

### 3. Action semantics are outside the contract

The packet audits claims and references. It has no native model of actor, tool, resource, side effect, authorization, reversibility, budget, or permitted scope.

### 4. Memory is advisory, not a decision policy

Prior failures do not deterministically block materially similar actions. Memory primarily changes output through contradiction or safety findings, so relevance-specific safety did not emerge.

### 5. There is no execution interposition

A host must voluntarily call Borg, choose the correct stage, submit faithful structured claims, interpret caution as review, and honor the decision. Borg cannot stop a tool, subprocess, deployment, payment, deletion, or network call by itself.

## Permanent product boundary

The defensible claim is now:

> Borg can produce an advisory epistemic packet that identifies missing/dangling evidence references, caller-attested verification gaps, conflicting memories, and unsafe retrieved memory. It is not a semantic evidence validator, authorization engine, tool interceptor, sandbox, or runtime enforcement boundary.

Do not claim that Borg:

- proves a claim is true because an artifact is referenced;
- requires verification before an action can execute;
- stops unsafe tool calls;
- validates authorization or policy compliance;
- turns relevant prior failures into reliable action controls;
- is production-ready as a general AI guardrail.

## Stop decision

Per the preregistered rule:

1. **Do not build runtime enforcement around the current mechanism.**
2. **Do not reinterpret warnings as successful blocking.**
3. **Do not tune thresholds on this held-out set and rerun it as confirmatory evidence.**
4. **Do not market the broad evidence-gate proposition.**
5. Preserve the evaluator and snapshot as a regression/falsification asset.
6. Keep `borg deliberate` only within the explicit advisory boundary unless a genuinely new mechanism is preregistered and tested on untouched external data.

That closes the experiment. The correct output is a hard negative decision, not another roadmap.
