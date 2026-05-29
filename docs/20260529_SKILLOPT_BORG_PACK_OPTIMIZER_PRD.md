# SkillOpt-Inspired Borg Pack Optimizer PRD + Build Spec

Historical/internal — not current product documentation. This is an operator implementation spec and makes no public self-serve, first-10, global promotion, or measured lift claim.

Date: 2026-05-29
Status: implemented on feature branch as local-only operator candidate optimizer
Repo: Borg canonical repository checkout
Canonical package: `agent-borg`
Canonical CLI: `borg`

## 1. Executive decision

Build a **Borg-native local pack optimizer** inspired by SkillOpt.

Do **not** vendor SkillOpt, do **not** add it as a runtime dependency, and do **not** allow automatic global pack mutation.

The product should use SkillOpt's strongest idea — treating compact skill/pack text as trainable state — but keep Borg's stricter evidence model:

- local-only candidate generation first
- bounded diffs, not freeform rewritten packs
- train / selection / hidden-test separation
- privacy and prompt-injection scans before evaluation
- rejected-edit buffer as durable negative evidence
- first-10 real-user evidence remains the product gate
- signed provenance + trusted-tenant verified quorum required before any global promotion

## 2. Why this matters

Borg already has the ingredients of a learning system:

- `borg_observe` / `borg_rescue` produce ACTION / STOP / VERIFY guidance
- `CollectiveLearningStore` records interventions and verified outcome receipts
- learning atoms encode reusable lessons
- atom policy gates privacy, injection, signatures, and quorum
- Dojo analyzes sessions and skill gaps
- first-10 gates define real user readiness

The missing piece is a systematic path from **verified outcomes** to **safe pack improvements**.

Today, pack improvement is mostly manual. The optimizer should make pack improvement repeatable, testable, and auditable without weakening Borg's trust model.

## 3. Problem statement

Agents and users need Borg guidance to get better over time, but current improvement paths are incomplete:

1. Successful and failed outcomes are recorded, but not systematically transformed into candidate pack edits.
2. Rejected / harmful / irrelevant guidance is not treated as first-class training signal.
3. Current mutation infrastructure exists, but it is too generic and old-style A/B oriented for SkillOpt-like bounded text optimization.
4. Public/global learning has strict privacy/provenance constraints that raw trajectory optimization would violate.
5. First-10 evidence is still the gating truth; benchmark-only gains cannot substitute for real user outcomes.

## 4. Product goal

Create a local-only `borg optimize-pack` workflow that proposes, tests, and records bounded candidate edits to Borg workflow packs using only privacy-safe verified evidence.

The output is a candidate patch + evidence bundle. It never auto-publishes, never mutates global packs by default, and never claims external lift without first-10 evidence.

## 5. Non-goals

The first release must not do any of these:

- no SkillOpt runtime dependency
- no automatic mutation of published packs
- no cross-tenant raw message/tool/observation sharing
- no optimizer-generated system-prompt injection
- no global promotion without signed provenance and trusted-tenant quorum
- no marketing claim of lift from offline experiments alone
- no broad public self-serve unlock
- no replacement of ACTION / STOP / VERIFY with generated longform instructions

## 6. Primary users

### 6.1 Borg maintainer

Wants a safe, testable way to improve packs from verified outcome evidence.

### 6.2 Agent using Borg

Wants fewer irrelevant hits, better STOP guidance, and more confident NO_CONFIDENT_MATCH behavior.

### 6.3 First-10 beta user

Wants Borg to help on real failures without leaking data, fabricating evidence, or overclaiming readiness.

## 7. Product principles

1. **Evidence before architecture**: run small real trials before building heavy automation.
2. **Local first**: candidate optimization starts on one installation and one pack.
3. **Bounded edits**: add / replace / delete small sections; never rewrite the entire pack by default.
4. **Negative evidence is signal**: preserve rejected edits, failed advice, bad STOP guidance, and irrelevant matches.
5. **NO_CONFIDENT_MATCH is a feature**: optimize for silence when confidence is weak.
6. **Privacy by construction**: optimizer consumes sanitized summaries, not raw trajectories.
7. **Policy gates are non-negotiable**: privacy, injection, provenance, and quorum gates run before promotion.
8. **First-10 remains the truth**: offline success can justify a beta candidate, not a public claim.

## 8. User experience

### 8.1 CLI: dry-run candidate generation

```bash
borg optimize-pack systematic-debugging \
  --taskset eval/tasksets/systematic_debugging_selection.json \
  --local-only \
  --max-edits 4 \
  --json
```

Expected behavior:

- reads the current `systematic-debugging` pack
- loads sanitized local verified outcomes
- creates train / selection split
- proposes bounded candidate diff
- scans candidate for privacy and prompt-injection risk
- evaluates baseline vs candidate on the selection taskset
- writes artifacts under `eval/pack_optimizer/<candidate_id>/`
- prints candidate summary
- does not modify the live pack unless a separate explicit apply command is used

### 8.2 CLI: inspect candidate

```bash
# artifact-only inventory; not source-verified and not eligible for manual review
borg optimize-pack inspect <candidate_id> --json

# source-bound inspection; required before manual-review eligibility
borg optimize-pack inspect <candidate_id> --pack-file <target_pack_path> --taskset <selection_taskset_path> --examples-file <source_examples_path> --json
```

Shows:

- pack name
- candidate diff summary
- edits proposed
- evidence used
- rejected edits avoided
- train / selection split hashes
- baseline score
- candidate score
- safety scan result
- recommendation: `reject`, `keep_local_candidate`, or `eligible_for_manual_review`

### 8.3 CLI: apply local candidate only after explicit approval

```bash
borg optimize-pack apply <candidate_id> --scope local --pack-file <target_pack_path> --taskset <selection_taskset_path> --examples-file <source_examples_path>
```

Hard rules:

- default command is dry-run only
- `apply` requires candidate score strictly better than baseline, candidate artifact re-verification, matching target pack id, and target file hash equal to the candidate baseline hash
- `apply` cannot set `scope global`
- global promotion remains controlled by atom/publish/provenance/quorum gates

### 8.4 Agent-facing change

`borg_observe` and `borg_rescue` should eventually benefit indirectly:

- fewer irrelevant pack matches
- sharper ACTION / STOP / VERIFY
- better explicit NO_CONFIDENT_MATCH behavior
- safer advisory summaries

The optimizer itself should not inject hidden optimizer memory into agent prompts.

## 9. Functional requirements

### R1. Optimizer artifacts

Implement candidate output artifacts:

- `candidate_pack.patch`
- `accepted_edits.json`
- `rejected_edits.json`
- `training_manifest.json`
- `selection_score.json`
- `privacy_scan.json`
- `prompt_injection_scan.json`
- `optimizer_run.json`

### R2. Sanitized training examples only

Training examples may include:

- error/task class
- pack selected
- ACTION / STOP / VERIFY shown
- intervention id
- verified outcome
- helpful flag
- dead ends avoided
- verification command redacted
- verification exit code
- verification output sha256
- trusted tenant hash
- privacy/prompt-injection summary

Training examples must not include:

- raw user chat
- raw tool stdout/stderr
- raw secrets
- raw file contents
- raw tenant identity
- full raw trajectory

### R3. Bounded edit operations

Candidate edits must use one of:

- `add_section`
- `replace_section`
- `delete_section`
- `tighten_stop_rule`
- `tighten_no_confident_match_rule`
- `add_verification_step`
- `add_antipattern`

Each candidate must declare:

- target pack
- target section id or anchor text
- before hash
- after hash
- rationale
- supporting receipts
- expected metric impact

### R4. Train / selection / hidden-test discipline

Optimizer must support three splits:

- train: used to propose edits
- selection: used to accept/reject candidate
- hidden test: used only after candidate freeze

Minimum first implementation:

- deterministic split by hashed task id
- train and selection required
- hidden test optional but schema-supported
- artifacts record split hashes so the split cannot be silently changed later

### R5. Selection gate

A candidate passes local selection only if all are true:

- candidate score > baseline score on primary metric
- no privacy scan failure
- no prompt-injection scan failure
- no regression on NO_CONFIDENT_MATCH controls
- no regression on unrelated task controls
- no increase in unsafe command recommendations
- candidate edits are within `--max-edits`
- candidate pack still validates

### R6. Rejected-edit buffer

Every rejected proposal must be stored with:

- edit operation
- target pack
- reason rejected
- score delta
- safety result
- supporting evidence ids
- timestamp

This prevents the optimizer from repeatedly proposing the same bad edit.

### R7. Policy integration

Use existing Borg safety primitives where possible:

- privacy scanner from `borg.core.privacy`
- prompt-injection scanner from `borg.core.prompt_injection`
- atom/quorum policy from `borg.core.atom_policy`
- outcome receipt evidence from `borg.core.collective_learning`

### R8. Local-only first release

The first implementation must be explicitly local-only.

Any global/shareable path must remain blocked until:

- signed candidate provenance exists
- trusted-tenant verified quorum exists
- first-10 evidence has real rows
- public self-serve gate passes
- operator explicitly approves promotion

### R9. First target pack

First target: `systematic-debugging`.

Reasons:

- clear verification surface
- high usage
- direct ACTION / STOP / VERIFY fit
- measurable failure classes
- better than subjective code-review packs

## 10. Objective function

Do not optimize only for task success.

Use a weighted score:

```text
score =
  0.30 * verified_success_delta
+ 0.20 * action_stop_verify_relevance_delta
+ 0.15 * dead_ends_avoided_delta
+ 0.15 * no_confident_match_precision_delta
+ 0.10 * verification_quality_delta
+ 0.10 * token_or_tool_efficiency_delta
- safety_penalty
- privacy_penalty
- irrelevant_guidance_penalty
```

Hard fail overrides:

- privacy leak
- prompt injection risk above block threshold
- raw trajectory exposure
- untrusted global promotion
- unsafe command recommendation
- worsened NO_CONFIDENT_MATCH controls

## 11. Metrics

### Primary local metrics

- verified success delta vs baseline
- ACTION / STOP / VERIFY relevance rate
- irrelevant-guidance rate
- NO_CONFIDENT_MATCH precision on weak/unrelated inputs
- dead ends avoided per verified outcome
- safety/privacy pass rate

### Secondary metrics

- token count
- tool calls
- time to solution
- voluntary Borg query rate
- candidate edit count
- rejected repeat rate

### Product readiness metrics

- first-10 real users with useful verified rescue
- first-10 install success
- first-10 MCP/setup success
- public self-serve gate
- measured external lift

## 12. Architecture

### 12.1 Existing components to reuse

- `borg/core/collective_learning.py`
  - source of interventions and outcome receipts
  - already enforces strong shareable evidence fields
- `borg/core/atom_policy.py`
  - privacy, injection, signature, quorum classification
- `borg/core/mutation_engine.py`
  - historical mutation concepts; reuse cautiously, do not rely on old z-test as final gate
- `borg/dojo/pipeline.py`
  - session analysis and skill gap signals
- `borg/core/prompt_injection.py`
  - prompt-injection scan
- `borg/core/privacy.py`
  - privacy scan
- `borg/cli.py`
  - add CLI command surface
- `tests/learning/`, `tests/security/`, `tests/mcp/`
  - patterns for evidence gates and Borg-specific tests

### 12.2 New components

Create:

- `borg/core/pack_optimizer.py`
- `borg/core/pack_optimizer_schemas.py`
- `borg/core/pack_optimizer_scoring.py`
- `eval/pack_optimizer_gate.py`
- `tests/optimizer/test_pack_optimizer_contract.py`
- `tests/optimizer/test_pack_optimizer_security.py`
- `tests/optimizer/test_pack_optimizer_cli.py`
- `eval/tasksets/systematic_debugging_selection.json`

Optional later:

- `borg/core/pack_optimizer_llm.py`
- `borg/core/pack_optimizer_rejected_buffer.py`
- `docs/20260529_SKILLOPT_BORG_PACK_OPTIMIZER_REPORT.md`

### 12.3 Data flow

```text
verified outcome receipts
  -> sanitize + redact
  -> build examples
  -> deterministic train/selection split
  -> propose bounded candidate edits
  -> scan candidate diff
  -> evaluate baseline vs candidate
  -> write evidence artifacts
  -> manual local apply only
  -> first-10 / public gates remain separate
```

## 13. Data schemas

### 13.1 `training_manifest.json`

```json
{
  "schema_version": "1.0",
  "pack_id": "systematic-debugging",
  "created_at": "2026-05-29T00:00:00Z",
  "source": "local_collective_learning_store",
  "split_method": "sha256(task_id + seed) modulo buckets",
  "seed_hash": "sha256:<64 hex>",
  "train_example_ids": [],
  "selection_example_ids": [],
  "hidden_example_ids": [],
  "privacy_policy": "no raw chat/tool output/file contents",
  "first_10_claim": false
}
```

### 13.2 `accepted_edits.json`

```json
{
  "schema_version": "1.0",
  "candidate_id": "packopt-sha256:<64 hex>",
  "pack_id": "systematic-debugging",
  "edits": [
    {
      "op": "tighten_stop_rule",
      "anchor": "NO_CONFIDENT_MATCH",
      "before_hash": "sha256:<64 hex>",
      "after_hash": "sha256:<64 hex>",
      "rationale": "reduce weak unrelated guidance",
      "supporting_receipt_ids": [],
      "risk": "low"
    }
  ]
}
```

### 13.3 `rejected_edits.json`

```json
{
  "schema_version": "1.0",
  "pack_id": "systematic-debugging",
  "rejections": [
    {
      "op": "add_antipattern",
      "reason": "selection_score_regressed",
      "score_delta": -0.07,
      "safety_result": "passed",
      "supporting_receipt_ids": []
    }
  ]
}
```

### 13.4 `selection_score.json`

```json
{
  "schema_version": "1.0",
  "candidate_id": "packopt-sha256:<64 hex>",
  "baseline_score": 0.61,
  "candidate_score": 0.68,
  "score_delta": 0.07,
  "primary_metric": "weighted_verified_guidance_score",
  "hard_failures": [],
  "recommendation": "eligible_for_manual_review"
}
```

## 14. Validation strategy

### 14.1 Phase A — one-task end-to-end smoke before infrastructure

Before heavy buildout, run one real local candidate flow by hand:

- one pack
- one tiny taskset
- one sanitized input fixture
- one bounded candidate diff
- one selection score artifact

Gate: every artifact exists, no live pack mutation, no raw trajectory content.

### 14.2 Phase B — deterministic test suite

Focused commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/optimizer/test_pack_optimizer_contract.py \
  tests/optimizer/test_pack_optimizer_security.py \
  tests/optimizer/test_pack_optimizer_cli.py \
  -p no:cacheprovider --tb=short
```

Expected: all pass.

### 14.3 Phase C — Borg regression suite

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/learning/test_collective_intelligence_loop.py \
  tests/security/test_atom_policy.py \
  tests/security/test_atom_registry.py \
  tests/mcp/test_collective_outcome_receipts.py \
  tests/mcp/test_mcp_server.py \
  -p no:cacheprovider --tb=short
```

Expected: all pass or only pre-existing known xfails.

### 14.4 Phase D — full suite before PR

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider --tb=short
```

Expected: no new failures.

### 14.5 Phase E — readiness gates

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/run_first_user_release_gate.py
PYTHONDONTWRITEBYTECODE=1 python eval/run_readiness_gates.py
PYTHONDONTWRITEBYTECODE=1 python eval/real_user_rollout_gate.py
```

Expected:

- first-user release/readiness gates must not regress
- real-user rollout gate may remain NO-GO until first-10 rows exist
- report must preserve that boundary honestly

## 15. Security and privacy test requirements

Tests must prove:

1. raw chat strings do not appear in artifacts
2. raw tool outputs do not appear in artifacts
3. secrets are redacted
4. prompt-injection strings in source evidence cannot become pack instructions
5. candidate cannot apply globally
6. candidate cannot pass selection with privacy failure
7. candidate cannot pass with unsigned/untrusted global promotion
8. tenant identity remains hashed/pseudonymous
9. no raw learning atom JSON is exposed through MCP advisory surfaces
10. unsafe commands are penalized or blocked

## 16. Implementation plan

### Task 1 — add optimizer contract tests

Files:

- Create: `tests/optimizer/test_pack_optimizer_contract.py`

Tests:

- `test_optimizer_dry_run_writes_required_artifacts`
- `test_optimizer_does_not_modify_live_pack_by_default`
- `test_optimizer_requires_train_and_selection_split`
- `test_optimizer_rejects_candidate_without_strict_selection_improvement`
- `test_optimizer_records_rejected_edit_buffer`

Run RED:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/optimizer/test_pack_optimizer_contract.py -p no:cacheprovider --tb=short
```

Expected: fail because module does not exist.

### Task 2 — add optimizer security tests

Files:

- Create: `tests/optimizer/test_pack_optimizer_security.py`

Tests:

- `test_training_examples_exclude_raw_chat_and_tool_output`
- `test_candidate_fails_on_secret_leak`
- `test_candidate_fails_on_prompt_injection_payload`
- `test_global_apply_is_blocked`
- `test_untrusted_receipts_do_not_count_for_shareable_candidate`

Run RED:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests/optimizer/test_pack_optimizer_security.py -p no:cacheprovider --tb=short
```

Expected: fail because sanitizer/optimizer do not exist.

### Task 3 — implement schemas and sanitizer

Files:

- Create: `borg/core/pack_optimizer_schemas.py`
- Create: `borg/core/pack_optimizer.py`

Minimum API:

```python
@dataclass(frozen=True)
class OptimizerExample:
    example_id: str
    pack_id: str
    task_class: str
    intervention_id: str
    action_summary: str
    stop_summary: str
    verify_summary: str
    outcome: str
    helpful: bool
    verified: bool
    verification_exit_code: int | None
    verification_output_sha256: str
    trusted_tenant_id: str

@dataclass(frozen=True)
class CandidateEdit:
    op: str
    anchor: str
    before_hash: str
    after_hash: str
    rationale: str
    supporting_receipt_ids: tuple[str, ...]

class PackOptimizer:
    def build_examples(self) -> list[OptimizerExample]: ...
    def split_examples(self, examples: list[OptimizerExample]) -> SplitManifest: ...
    def propose_candidate(self, pack_id: str, examples: list[OptimizerExample]) -> Candidate: ...
    def evaluate_candidate(self, candidate: Candidate, taskset_path: Path) -> SelectionScore: ...
    def write_artifacts(self, candidate: Candidate, score: SelectionScore, output_dir: Path) -> Path: ...
```

Run GREEN:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/optimizer/test_pack_optimizer_contract.py \
  tests/optimizer/test_pack_optimizer_security.py \
  -p no:cacheprovider --tb=short
```

### Task 4 — implement deterministic scoring

Files:

- Create: `borg/core/pack_optimizer_scoring.py`
- Modify: `borg/core/pack_optimizer.py`

Minimum scoring API:

```python
def weighted_verified_guidance_score(metrics: dict) -> float: ...
def hard_failures(metrics: dict) -> list[str]: ...
def compare_baseline_candidate(baseline: dict, candidate: dict) -> SelectionScore: ...
```

Tests:

- candidate with better verified success but worse NO_CONFIDENT_MATCH is rejected
- candidate with privacy hard failure is rejected
- candidate with strict weighted improvement and no hard failures passes

### Task 5 — add CLI surface

Files:

- Modify: `borg/cli.py`
- Create: `tests/optimizer/test_pack_optimizer_cli.py`

Commands:

```bash
borg optimize-pack <pack> --taskset <path> --pack-file <path> --local-only --max-edits 4 --json
borg optimize-pack inspect <candidate_id> --json  # artifact-only; reports source_verification_required
borg optimize-pack inspect <candidate_id> --pack-file <target_pack_path> --taskset <selection_taskset_path> --examples-file <source_examples_path> --json
borg optimize-pack apply <candidate_id> --scope local --pack-file <target_pack_path> --taskset <selection_taskset_path> --examples-file <source_examples_path> --json
```

Hard expectations:

- dry-run default
- global scope rejected
- JSON output stable
- non-JSON output human-readable

### Task 6 — add evaluation gate

Files:

- Create: `eval/pack_optimizer_gate.py`
- Create: `eval/tasksets/systematic_debugging_selection.json`

Gate behavior:

- runs baseline vs candidate selection scoring
- checks required artifacts
- checks no raw trajectory leakage
- exits nonzero on privacy, injection, global, or score regression failure

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/pack_optimizer_gate.py --candidate <candidate_id> --json
```

### Task 7 — docs and public-boundary wording

Files:

- Create: `docs/20260529_SKILLOPT_BORG_PACK_OPTIMIZER_REPORT.md`
- Update if needed: `docs/README.md`

Required wording:

- local-only candidate optimizer
- no SkillOpt runtime dependency
- no public lift claim
- first-10 remains the gate
- global promotion remains blocked without signed provenance and trusted-tenant verified quorum

### Task 8 — full verification closeout

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/optimizer/test_pack_optimizer_contract.py \
  tests/optimizer/test_pack_optimizer_security.py \
  tests/optimizer/test_pack_optimizer_cli.py \
  -p no:cacheprovider --tb=short

PYTHONDONTWRITEBYTECODE=1 python -m pytest -q \
  tests/learning/test_collective_intelligence_loop.py \
  tests/security/test_atom_policy.py \
  tests/security/test_atom_registry.py \
  tests/mcp/test_collective_outcome_receipts.py \
  tests/mcp/test_mcp_server.py \
  -p no:cacheprovider --tb=short

PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider --tb=short
```

Closeout only if all pass.

## 17. Experiment plan

### 17.1 Pilot

Run 3 real candidate trials before building more infra.

Gate:

- at least one candidate generated
- at least one candidate rejected for a real reason
- no raw data leakage
- no pack auto-mutation
- artifacts complete

### 17.2 Offline selection experiment

Compare:

- baseline pack
- optimized candidate pack
- manual expert edit
- one-shot LLM edit

Primary question:

Does the optimized candidate improve verified guidance quality without increasing irrelevant guidance or safety risk?

### 17.3 First-10 integration

Only after offline gate passes:

- expose candidate to controlled first-10 beta path
- record verified outcome receipts
- compare baseline vs candidate on real user rows
- keep broad public self-serve NO-GO until row-derived evidence passes

## 18. Go / no-go gates

### Build GO

Go if:

- implementation is local-only
- tests prove no raw trajectory leakage
- candidate artifacts are deterministic and auditable
- dry-run default is enforced
- global apply is blocked

### Local candidate GO

Go if:

- selection score strictly improves
- all hard gates pass
- unrelated-task and NO_CONFIDENT_MATCH controls do not regress
- rejected-edit buffer records rejected proposals

### First-10 beta GO

Go only if:

- package/readiness gates pass
- first-10 path is controlled
- user-facing docs preserve no public claim boundary
- operator approves beta exposure

### Public/self-serve NO-GO until

No-go remains until:

- first-10 real evidence rows pass
- 100-user rollout evidence exists
- measured external lift exists
- public gates and CI are green for the same released version

## 19. Failure modes

### FM1. Optimizer overfits to local quirks

Mitigation:

- train / selection split
- unrelated controls
- hidden-test support
- no public claims from local evidence

### FM2. Optimizer turns malicious source text into instructions

Mitigation:

- prompt-injection scan source evidence and candidate diff
- sanitize summaries
- candidate text remains advisory pack content
- tests with explicit injection payloads

### FM3. Privacy leak through artifacts

Mitigation:

- artifacts store hashes and summaries only
- security tests scan artifacts for raw sentinel strings
- fail closed on scanner error where possible

### FM4. Global poisoning through fake tenants

Mitigation:

- local-only first release
- trusted tenant identity required for shareable quorum
- signed provenance required for global
- HMAC tenant pseudonym not counted as quorum identity

### FM5. Worse UX from overactive guidance

Mitigation:

- NO_CONFIDENT_MATCH precision as primary score component
- unrelated controls
- hard fail on weak-match regression

### FM6. Statistical theatre

Mitigation:

- separate offline selection from product claims
- first-10 remains true product gate
- publish exact n, confidence, and limitations

## 20. Open decisions before implementation

1. Where should candidate artifacts live permanently?
   - default proposed path: `eval/pack_optimizer/<candidate_id>/`
2. Should the first taskset be committed as JSON fixtures or generated from existing tests?
   - recommended: committed JSON fixtures first, generator later
3. Should candidate proposals be LLM-generated in v1?
   - recommended: no. Start deterministic/rule-based to prove pipeline safety. Add LLM proposer later behind same gates.
4. Should `mutation_engine.py` be reused or bypassed?
   - recommended: reuse concepts only. Build `pack_optimizer.py` fresh because old mutation engine uses generic z-test mechanics and broad mutation types.

## 21. Final acceptance criteria

The PR is complete only when all are true:

- `borg optimize-pack` exists and is dry-run local-only by default
- candidate generation writes all required artifacts
- sanitizer excludes raw chat/tool/file content
- privacy and prompt-injection hard-fail tests pass
- global apply is impossible from the optimizer command
- rejected-edit buffer is recorded
- selection gate rejects non-improving candidates
- `systematic-debugging` can produce at least one candidate artifact on a tiny verified taskset
- focused optimizer tests pass
- relevant collective/security/MCP regressions pass
- full pytest passes
- docs clearly state first-10 remains the gate and no SkillOpt runtime dependency exists

## 22. Recommended first implementation branch

```bash
git checkout -b feat/local-pack-optimizer-skillopt
```

First commit should be RED tests only.

Suggested commit order:

1. `test: add pack optimizer contract and safety red tests`
2. `feat: add local pack optimizer schemas and sanitizer`
3. `feat: add candidate scoring and artifact ledger`
4. `feat: add optimize-pack cli dry-run`
5. `test: add pack optimizer gate and taskset fixture`
6. `docs: document SkillOpt-inspired local pack optimizer boundary`

## 23. Bottom line

The right integration is not SkillOpt-the-package.

The right integration is **SkillOpt-style optimization discipline**, implemented as a Borg-native, local-only, evidence-gated pack optimizer.

Start with `systematic-debugging`, preserve NO_CONFIDENT_MATCH discipline, treat rejected edits as valuable negative evidence, and keep first-10 real-user evidence as the only product-readiness gate.
