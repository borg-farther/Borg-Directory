# Context dossier — Borg epistemic guardrail and ultra-deep mode

> **Historical/internal — not current product documentation.** This is a dated research dossier; use `docs/EPISTEMIC_GUARDRAIL.md` for the current contract.

Captured: 2026-09-30T11:41:05Z
Branch: `feature/epistemic-guardrail-3.4.0`
Base: `4832dfe9af614c722cb0ea80f7628679c893bd35` (`agent-borg` 3.3.21 release commit)

## 1. Product question

Should Borg pivot from a narrow failure-memory product into a unified system that serves as:

1. memory for frontier-model deep thinkers;
2. a brake on confident unsupported output;
3. verified collective learning between agents; and
4. a selective ultra-deep-thinking workflow?

The implementation must be complete across core code, public Python API, CLI, MCP, tests, evaluation, documentation, and release proof. It must not claim external value that has not been measured.

## 2. Non-negotiables

- Search and inspect before building.
- Reuse existing Borg primitives rather than build a second disconnected subsystem.
- Do not turn Borg into a generic chain-of-thought generator or force verbose process on every task.
- Fail closed when memory is weak, contradictory, stale, unsafe, or unverified.
- Preserve privacy boundaries: no raw private traces are shared by default.
- Every actionable claim must expose provenance, confidence, and verification.
- Keep local seed knowledge distinct from verified collective evidence.
- Build RED→GREEN tests before claiming success.
- External-user utility remains unproven until row-derived evidence exists.
- Do not publish a new immutable package without exact version approval after release preflight.

## 3. Current product reality

### Proven software paths

- `agent-borg==3.3.21` exists on PyPI.
- Fresh non-repo install, CLI rescue, doctor, import, and stdio MCP canary passed for 3.3.21.
- Configured full suite passed: 2,780 tests, 40 skipped, 4 xfailed, 1 xpassed.
- Live served Borg fingerprint reports version/source 3.3.21 and current confidence-gate behavior.
- Synthetic logical-user load snapshots passed at 10, 100, and 1,000 logical users.

### Unproven product paths

- Verified external users: 0/10.
- Verified installs: 0/8.
- Verified useful rescues: 0/6.
- GitHub stars/forks: 0/0 at capture time.
- Borg ecosystem adoption metrics: 0 active agents, contributors, and consumers.
- The V3 dashboard's multi-million outcome count is contaminated by generated/test rows and is not adoption evidence.
- GitHub PR #84 is open and review-blocked. Account email verification also blocked authenticated pushes earlier in the release flow.

## 4. What already exists in source

### Memory and retrieval

- `borg/core/traces.py` — local trace capture and persistence.
- `borg/core/trace_matcher.py` — FTS/error/file/helpfulness retrieval.
- `borg/core/failure_memory.py` — explicit failure-memory storage and recall.
- `borg/core/search.py` — pack, semantic, and trace retrieval.
- `borg/core/contextual_selector.py` — evidence-aware selection and contextual scoring.

### Confidence and injection safety

- `borg/core/confidence_gate.py` — query normalization, overlap gates, weak-match rejection, prompt-injection boundary, `NO_CONFIDENT_MATCH`.
- `borg/core/rescue.py` — shared `ACTION / STOP / VERIFY / CONFIDENCE` packet for CLI and MCP.
- `eval/cold_start_trust_gate.py` — first-answer trust checks.

### Outcome and collective learning

- `borg/core/collective_learning.py` — interventions, signed outcome receipts, tenant binding, quorum, sanitized learning-atom candidates, contribution ledger.
- `borg/core/learning_atoms.py`, `atom_policy.py`, `atom_store.py`, `atom_registry.py`, `atom_retrieval.py` — signed/revocable/privacy-scanned collective artifacts.
- `borg/core/feedback_loop.py`, `v3_integration.py`, `mutation_engine.py` — outcome and optimization plumbing.

### Surfaces

- `borg/cli.py` — rescue, observe, recall, collective, receipts, agent priming.
- `borg/integrations/mcp_server.py` — rescue, observe, collective retrieve/status, record failure/outcome, runtime fingerprint.
- `borg/core/agent_priming.py` — managed agent instructions and outcome-capture contract.
- `borg/__init__.py` — public package API.

## 5. Evidence from prior Borg experiments

- Generic structured workflow phases added overhead on easy/medium tasks.
- Targeted reasoning traces showed directional benefit on difficult tasks, but the honest paired result was small and not statistically significant (`n=7`, control 3/7 vs treatment 6/7, McNemar p=0.125).
- Rich guidance can degrade smaller models; ultra-compact relevant guidance performed better.
- Retrieval relevance and delivery mechanism matter more than verbose content.
- Empty-memory A/B tests measure scaffold effect, not collective knowledge.
- The correct evaluation needs control, empty-memory, and seeded-memory conditions on held-out hard tasks.

## 6. Core design risk

The repo already contains most primitives. The likely failure is not missing infrastructure; it is fragmentation and the absence of one public, machine-readable contract that turns them into a selective epistemic preflight/review loop.

A bad implementation would:

- duplicate retrieval stores;
- force generic step-by-step scaffolding;
- expose private reasoning/chain-of-thought;
- turn memories into instructions without provenance;
- call weak similarity a confident match;
- confuse local seed guidance with verified collective proof;
- claim collective intelligence from synthetic/test telemetry;
- add a new API that is not wired through CLI, MCP, priming, tests, and docs.

## 7. Candidate product nucleus

> Borg is the evidence and experience control plane for frontier agents: it retrieves relevant prior outcomes, exposes contradictions and known dead ends, requires explicit assumptions and verification, abstains when evidence is weak, and converts verified outcomes into privacy-safe collective memory.

Borg does not replace the host model's reasoning. It constrains and improves the epistemic process around that reasoning.

## 8. Required adversarial questions

### Red team

- Can irrelevant or adversarial memory steer the agent?
- Can a single success be promoted as truth?
- Can evidence be forged or detached from the intervention that produced it?
- Does deep mode leak private chain-of-thought or demand it from models?
- Can the system reward verbosity instead of correctness?
- Does it make strong models worse on easy tasks?
- Are CLI/MCP/public API outputs inconsistent?

### Blue team

- What is the smallest shared contract all surfaces can use?
- How are claims, assumptions, evidence, conflicts, uncertainties, and verification represented?
- What are the state transitions from hypothesis to observed to verified to collective?
- How does selective activation avoid universal overhead?
- How does the host model remain the thinker while Borg remains the control plane?

### Green team

- Which existing data paths are real and which are synthetic/test-contaminated?
- What can be measured deterministically now?
- What corpus catches false confidence and negative transfer?
- What thresholds can be justified rather than invented?
- How will control/empty/seeded experiments distinguish scaffold from memory value?

### Skeptic

- Is this a useful product pivot or architecture theatre?
- Would a frontier-model user understand the first value moment in one command?
- Is this better than ordinary memory/RAG/checklists?
- What is the cheapest falsification test?
- What claims must remain forbidden after implementation?

## 9. Candidate acceptance contract

A finished implementation must demonstrate all of the following:

1. One shared core produces a machine-readable epistemic packet.
2. Packet includes decision, activation reason, claims/assumptions, relevant memory, contradictions, STOP conditions, verification plan, provenance, uncertainty, and outcome-capture instruction.
3. Weak/irrelevant/conflicting evidence never becomes an authoritative action.
4. No-match is a first-class successful abstention state.
5. Simple/easy/nontechnical inputs do not trigger expensive deep mode by default.
6. Technical high-stakes/ambiguous/repeated-failure inputs can trigger deep mode deterministically.
7. CLI, MCP, and Python API return semantically identical packets.
8. Verified outcome receipts can strengthen future memory; unverified feedback cannot masquerade as collective proof.
9. Tests cover false-confidence, prompt-injection, contradiction, stale evidence, source disagreement, verification completeness, privacy, and cross-agent transfer.
10. A frozen evaluation corpus reports false-confident rate, abstention, coverage, contradiction detection, and packet completeness.
11. Public docs explain the host-model/Borg boundary and do not claim external lift.
12. Full suite, security gates, build, fresh install, CLI, Python API, and stdio MCP pass on the final tree.

## 10. Files to prioritize

Read and trace:

- `borg/core/confidence_gate.py`
- `borg/core/rescue.py`
- `borg/core/trace_matcher.py`
- `borg/core/failure_memory.py`
- `borg/core/contextual_selector.py`
- `borg/core/collective_learning.py`
- `borg/core/agent_priming.py`
- `borg/integrations/mcp_server.py`
- `borg/cli.py`
- `borg/__init__.py`
- current tests under `tests/core`, `tests/mcp`, `tests/learning`, `tests/security`

Ignore as current product truth:

- archived marketing claims;
- synthetic dashboard counts;
- historical experimental reports unless raw evidence and correction notices are followed;
- unrelated prototype repos.
