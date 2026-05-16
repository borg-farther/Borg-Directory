# 20260514 Borg production rebuild master plan

**file rev:** 20260514-0938 rev A  
**scope:** `/root/hermes-workspace/borg` plus known Borg ecosystem paths and prior audit docs/session evidence.  
**mode:** architecture / production plan from evidence. This pass did not run terminal tests; it uses current files, docs, Borg/session recall, and recent MCP/runtime probes.  
**decision:** Borg is **not yet a production-clean app**. It is **controlled-go for supervised first-user beta** if operated from the canonical `agent-borg` source/wheel, but **NO-GO for broad unattended production** until the P0 gates below are closed.

---

## 0. Executive answer

Borg should become one boring, sharp product first:

> **A local-first, privacy-safe failure-memory layer for AI coding agents that returns ACTION / STOP / VERIFY only when it can prove relevance, and otherwise fails closed as NO_CONFIDENT_MATCH.**

Everything else — federation, marketplace, reputation, Dojo, DeFi, dashboards, multi-agent analytics, OpenClaw conversion, installer packages — must be treated as optional modules around that kernel, not parallel products with their own runtime truth.

The current system has real value, but it is carrying too much historical mass:

- multiple runtime copies;
- duplicate CLI ownership;
- stale docs and proof artifacts mixed with current ones;
- build/lib and installed package drift;
- a live MCP process that can still serve stale observe behavior after source patches;
- federation/backend pieces that are not locally reproducible yet;
- product claims ahead of external-user evidence.

The production rebuild is therefore **not** “add more features.” It is:

1. freeze the product kernel;
2. remove split-brain;
3. make confidence/security gates executable and impossible to bypass silently;
4. make install/runtime/CLI ownership singular;
5. then run first-10 external beta with evidence.

---

## 1. What is real and worth preserving

### 1.1 Core local product

Evidence:

- `README.md` positions Borg as `pip install agent-borg`, CLI `borg`, MCP `borg-mcp`.
- `borg/core/traces.py`, `trace_matcher.py`, `failure_memory.py`, `search.py`, `rescue.py`, and `pack_taxonomy.py` implement the local memory / retrieval / rescue surface.
- `borg/integrations/mcp_server.py` exposes the MCP tool surface.
- `borg/__init__.py` exposes `borg.check(...)`, no longer a placeholder.
- `PROJECT_STATUS.md` says controlled rollout PASS from local 3.3.1 wheel/source.
- `GO_NO_GO_DECISION.md` says `Decision: CONTROLLED GO` and explicitly withholds broad public production GO.

Preserve as kernel:

```text
input: exact error / failing output / technical task
  -> privacy + prompt-injection neutralization where content is persisted/shared
  -> retrieval confidence gate
  -> ACTION / STOP / VERIFY / CONFIDENCE or NO_CONFIDENT_MATCH
  -> outcome feedback
  -> local trace/failure memory update
```

### 1.2 Privacy-safe learning atom substrate

Evidence:

- `borg/core/learning_atoms.py`
- `borg/core/atom_policy.py`
- `borg/core/atom_store.py`
- `borg/core/atom_retrieval.py`
- `borg/core/atom_tenant.py`
- `borg/core/privacy.py`
- `borg/core/prompt_injection.py`
- `borg/core/crypto.py`
- tests: `test_learning_atoms.py`, `test_atom_policy.py`, `test_atom_store.py`, `test_atom_retrieval_firewall.py`, `test_privacy_structured.py`, `test_prompt_injection.py`.

This is a useful security substrate. Keep it, but do not let it define the day-one product. It should serve the kernel.

### 1.3 Readiness machinery

Evidence:

- `eval/run_first_user_release_gate.py`
- `eval/borg_day_one_readiness.py`
- `eval/run_readiness_gates.py`
- `eval/uat_scoreboard.py`
- `eval/load_soak.py`
- `scripts/security_gate_check.py`
- docs: `FIRST_10_BETA_READINESS.md`, `20260504-1123_BORG_PRODUCTION_1000_READINESS_STATUS.md`.

Keep, but rationalize into one release gate command and one scoreboard truth source.

---

## 2. Current outstanding issues, ranked

### P0.1 — Runtime split-brain / stale live MCP behavior

**Evidence:**

- Current known code paths include:
  - `/root/hermes-workspace/borg/borg/integrations/mcp_server.py`
  - `/usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py`
  - `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`
  - `/home/user/guild-tools/borg/integrations/mcp_server.py`
  - Hermes plugin paths under `/root/.hermes/hermes-agent/.../borg_auto_trace`.
- Recent live `mcp_borg_observe` probes still returned unrelated `PACK GUIDANCE` after source/runtime patching, which implies stale in-memory served code or a different loaded path.
- `20260513_BORG_MULTI_REPO_PRODUCTION_CLEANUP_CUTOVER_PROPOSAL.md` calls this a trust blocker.

**Why it matters:**

Borg’s core trust promise is “do not inject misleading guidance.” If live runtime can leak stale or unrelated advice, production readiness is impossible.

**Fix:**

- [x] Add runtime fingerprint endpoint/tool output for MCP server: module path, file hash, package version, BORG_HOME, loaded module hashes, and confidence-gate canary.
  - Canonical source: `borg/core/runtime_fingerprint.py` + MCP `borg_runtime_fingerprint` schema/dispatch.
  - Installed runtime: `/usr/local/lib/python3.12/dist-packages/borg/core/runtime_fingerprint.py` + installed MCP dispatch delegation.
  - Defensive mirror schemas/dispatch patched in `guild-v2` and `/home/user/guild-tools`.
- [ ] On MCP startup, run contract self-check: schema ↔ dispatcher kwargs ↔ callable signatures ↔ helper version hash.
- [ ] Refuse to serve or expose `runtime_status=degraded` if fingerprint/hash does not match canonical expected version.
- Make `borg-doctor --json` compare:
  - import path;
  - console script path;
  - installed package version;
  - source version;
  - MCP served fingerprint if accessible.
- Deprecate hand-maintained mirror paths; runtime copies must be generated artifacts or installed wheels only.

**Exit criteria:**

- Known unrelated prompts return `NO_CONFIDENT_MATCH` or no injected advice through:
  1. direct source import,
  2. installed console script,
  3. served MCP process,
  4. Hermes plugin injection path.
- Known real permission-denied task still returns permission guidance.
- Evidence includes raw stdout/stderr and runtime fingerprint.

---

### P0.2 — Multi-repo / namespace collision

**Evidence:**

- Manifest shows `agent-borg` owns `borg`, `borg-mcp`, `borg-doctor`, `borg-install`.
- `borg-collective-py` also exposes public `borg` and `borg-mcp` entrypoints.
- `20260513_borg_ecosystem_manifest.prelim.json` lists this as a blocker.

**Why it matters:**

A user can install two Borg packages and get different behavior depending on PATH and install order. That is not production-grade.

**Decision:**

- `agent-borg` owns public local user commands:
  - `borg`
  - `borg-mcp`
  - `borg-doctor`
  - `borg-install`
- `borg-collective-py` becomes SDK/library only or renames commands:
  - `borg-collective`
  - `borg-collective-mcp`
- `borg-collective-v1` owns hosted backend only.
- `borg-init` owns installer/onboarding only; it verifies canonical `agent-borg`, not a fork.
- `guild-v2`, `/home/user/guild-tools`, and `build/lib` are not source-of-truth.

**Exit criteria:**

- Clean venv with `agent-borg`: `which borg`, `borg version`, `python -c 'import borg; print(borg.__file__)'` all point to canonical package.
- Clean venv with federation SDK cannot shadow `borg`.
- Docs use one install story.

---

### P0.3 — Dirty canonical repo / no-loss cleanup incomplete

**Evidence:**

- Prior raw audit found `/root/hermes-workspace/borg` with 237 dirty/untracked entries.
- Current docs include many generated artifacts, historical clones under `docs/`, build artifacts, proof reports, and readiness files.

**Why it matters:**

Production releases require a clean, reviewable tree. Dirty trees hide accidental generated files, stale docs, duplicate test artifacts, and unreviewed code.

**Fix:**

Create `docs/repo-manifest/20260514_borg_no_loss_cleanup_manifest.json` with every changed/untracked path classified:

- `commit_product_code`
- `commit_test`
- `commit_doc`
- `archive_readonly`
- `generated_ignore`
- `delete_after_archive`
- `external_repo_do_not_include`

No deletion until archive/diff harvesting is complete.

**Exit criteria:**

- `git status --short` is empty or contains only explicitly allowed local files.
- `.gitignore` excludes generated `build/`, `dist/`, caches, and vendored clone junk unless intentionally committed.
- No product code lives only in `build/lib` or installed site-packages.

---

### P0.4 — Confidence gate semantics are still too brittle

**Evidence:**

- Recent Borg guidance leak showed unrelated pack guidance in current conversation.
- Guard was patched to strip embedded `=== BORG GUIDANCE ===`, suppress `Real traces: 0 + PACK GUIDANCE`, and require concrete permission signals.
- Shared source module now exists at `borg/core/confidence_gate.py` with focused regression tests.
- Runtime fingerprint/canary module now exists at `borg/core/runtime_fingerprint.py` and reports whether the loaded confidence gate suppresses stale pasted guidance, synthetic pack guidance, and unrelated permission guidance.
- But live served MCP still needs reload/fingerprint proof; no process restart/signal has been performed.

**Production rule:**

Borg must be conservative. It is better to say “I do not know” than to inject confident-looking junk.

**Fix:**

Implement a single shared confidence-gate module, e.g. `borg/core/confidence_gate.py`, used by:

- `mcp_server.py`
- CLI `observe` / `rescue` path if applicable
- Hermes plugin
- public `borg.check()` if result rendering happens there
- any future federation retrieval path

The module should own:

- embedded guidance stripping;
- no-match detection;
- synthetic-only suppression;
- permission-signal matching;
- minimum trace thresholds;
- pack lexical/domain overlap;
- output shape contract.

**Exit criteria:**

- No duplicated private implementations in four runtime files.
- Tests import the same module, not copy-pasted plugin helpers.
- Golden tests cover:
  - unrelated audit prompt;
  - pasted stale Borg guidance;
  - real permission-denied task;
  - real high-confidence trace;
  - synthetic seed pack only;
  - no trace / no pack.

---

### P0.5 — Federation backend and SDK are not production-reproducible

**Evidence:**

- `borg-collective-py` test collection failed from missing `respx` and `hypothesis` in audit.
- `borg-collective-v1` local tests failed due Wrangler remote-mode/login/config issues.

**Fix:**

- Add declared test extras to SDK.
- Add deterministic local Worker test mode with no interactive auth.
- Split remote migration commands from local tests; require explicit environment gates for D1 mutation.
- Add CI jobs per repo with exact setup.

**Exit criteria:**

- SDK: clean env `pip install -e '.[test]' && pytest` passes.
- Worker: `npm test` or `npm run test:local` passes without login.
- Backend deploy/migration path has dry-run and explicit production confirmation.

---

### P0.6 — Security claims need enforcement at every user-facing path

**Evidence:**

- `PARTIAL_IMPLEMENTATIONS_STATUS.md` says Ed25519 primitives exist but universal signed-pack trust is not proven.
- `README.md` correctly warns not to interpret Ed25519 primitives as every pack being trusted.
- Learning atoms are safer than earlier designs, but federation/global trust remains unproven.

**Fix:**

Every retrieval/publish/apply path must expose a security state:

```text
source_scope: local | org | global | seed | unknown
signature_state: verified | unsigned_local | invalid | unavailable
privacy_state: scanned_pass | scanned_warn | rejected | not_applicable
prompt_injection_state: pass | warn | reject
revocation_state: active | revoked | tombstoned_unknown
confidence_state: high | medium | low | no_confident_match
```

**Exit criteria:**

- `borg search`, `borg rescue --json`, MCP `borg_observe`, atom search, and pack apply outputs carry these fields or explicit omission reason.
- Invalid signature cannot be silently downgraded in global/shared contexts.
- Revoked atoms cannot retrieve.

---

### P0.7 — External utility proof is still missing

**Evidence:**

- `README.md`, `GO_NO_GO_DECISION.md`, and `PARTIAL_IMPLEMENTATIONS_STATUS.md` all say external user utility/lift is unproven.
- First-10 beta success metric is 6/10 users receiving one relevant ACTION/STOP/VERIFY moment without maintainer handholding.

**Fix:**

Do not broaden launch until first-10 evidence exists.

**Exit criteria:**

- 10 user/task records with:
  - install path;
  - exact task/error;
  - Borg output;
  - relevance rating;
  - whether it prevented a dead end;
  - final outcome;
  - `borg_rate` or equivalent feedback record.
- At least 6/10 relevant moments.
- Every miss classified as `NO_CONFIDENT_MATCH`, weak match, or bug with regression test.

---

## 3. Target production architecture

```text
                          ┌──────────────────────────────┐
                          │        agent / user           │
                          │ CLI, MCP client, Hermes, etc. │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────┐
│                         agent-borg package                         │
│ canonical local product; owns borg / borg-mcp / borg-doctor         │
│                                                                    │
│  ┌─────────────────────┐   ┌────────────────────────────────────┐  │
│  │ User-facing surfaces │   │ Shared production kernel            │  │
│  │ - borg CLI           │──▶│ - rescue engine                     │  │
│  │ - borg-mcp           │──▶│ - confidence gate                   │  │
│  │ - borg.check()       │──▶│ - retrieval + failure memory        │  │
│  │ - borg-doctor        │──▶│ - privacy / injection scanners      │  │
│  └─────────────────────┘   │ - trace/outcome recorder             │  │
│                            │ - runtime fingerprint + contract CI  │  │
│                            └───────────────┬────────────────────┘  │
│                                            │                       │
│                                            ▼                       │
│                            ┌────────────────────────────────────┐  │
│                            │ Local stores under BORG_HOME        │  │
│                            │ - traces.db                         │  │
│                            │ - failure memory                    │  │
│                            │ - atoms.db                          │  │
│                            │ - readiness/fingerprint snapshots   │  │
│                            └───────────────┬────────────────────┘  │
└────────────────────────────────────────────┼───────────────────────┘
                                             │ optional, explicit
                                             ▼
                         ┌────────────────────────────────────┐
                         │ borg-collective-py SDK             │
                         │ library only / borg-collective CLI │
                         └────────────────┬───────────────────┘
                                          ▼
                         ┌────────────────────────────────────┐
                         │ borg-collective-v1 Worker + D1     │
                         │ hosted federation backend          │
                         └────────────────────────────────────┘

                         ┌────────────────────────────────────┐
                         │ borg-init                          │
                         │ installer/orchestrator only        │
                         └────────────────────────────────────┘
```

### Architectural principles

1. **Local-first always.** Borg must work offline with no federation.
2. **Fail closed.** No confident-looking guidance without evidence.
3. **One kernel.** CLI, MCP, plugin, and Python API call the same confidence/security/retrieval modules.
4. **No runtime forks.** Mirrors are generated artifacts or archived.
5. **Security state visible.** Every shared/retrieved artifact reports trust/privacy/revocation state.
6. **Federation optional.** Hosted backend cannot be required for day-one value.
7. **Claims tied to gates.** Docs cannot claim more than current machine snapshots and beta evidence prove.

---

## 4. What to delete, keep, archive, or refactor

### Keep canonical

- `/root/hermes-workspace/borg`
- `agent-borg` package
- `borg/cli.py`
- `borg/integrations/mcp_server.py`
- `borg/core/rescue.py`
- `borg/core/trace_matcher.py`
- `borg/core/failure_memory.py`
- learning atom modules
- eval/readiness/security scripts
- current first-user docs and proof dashboard docs after reconciliation

### Keep, but rename/re-scope

- `borg-collective-py`: SDK/library; remove `borg` / `borg-mcp` collisions.
- `borg-collective-v1`: backend only; no local user product claims.
- `borg-init`: installer only; verify canonical package.

### Archive after no-loss diff harvest

- `/root/hermes-workspace/guild-v2`
- `/home/user/guild-tools`
- duplicate plugin path if packaging does not require it
- old audit docs that are superseded but historically useful
- vendored clones under `docs/` if not needed for current public docs

### Remove from source-of-truth

- hand-edited `build/lib`
- installed site-packages patches as product code
- stale docs claiming old versions or obsolete status
- duplicate confidence gate helper implementations after shared module extraction

---

## 5. Production rebuild execution plan

### Phase 0 — freeze and prove current state

**Goal:** no more ambiguity.

Tasks:

1. Generate full current manifest:
   - repos;
   - package versions;
   - entrypoints;
   - git remotes/branches/dirty counts;
   - runtime module paths/hashes;
   - proof artifact status.
2. Save as `docs/repo-manifest/20260514_borg_ecosystem_manifest.json`.
3. Generate dirty-tree classification manifest.
4. Run read-only security scan on diffs/docs.

Gate:

- No deletion.
- No service restart.
- No release.
- Artifact exists and covers every known path.

---

### Phase 1 — make one canonical runtime

**Goal:** source edits equal runtime behavior.

Tasks:

1. Build `borg/core/runtime_fingerprint.py`.
2. Add MCP `borg_runtime_status` or include fingerprint in `borg_doctor`/existing doctor JSON.
3. Add startup contract validation for MCP tools.
4. Add served-process canary script:
   - starts `python -m borg.integrations.mcp_server` in a subprocess;
   - calls initialize/tools/list/tools/call;
   - verifies known no-match and permission-positive controls.
5. Convert runtime mirrors into generated artifacts or archive-only.

Gate:

- Served MCP canary proves the same file hash/version as canonical.
- Live operator-approved reload then proves current gateway/MCP behavior.

---

### Phase 2 — extract shared guidance safety module

**Goal:** no duplicated confidence/injection logic.

Tasks:

1. Create `borg/core/confidence_gate.py`.
2. Move into it:
   - strip embedded Borg guidance;
   - permission signal matching;
   - synthetic/zero-real suppression;
   - pack match confidence;
   - trace confidence;
   - no-match response builder.
3. Update:
   - MCP server;
   - Hermes plugin;
   - CLI observe/rescue rendering if applicable;
   - public API if needed.
4. Add golden regression suite.

Gate:

- All user-facing surfaces use shared module.
- No grep hits for duplicate `_guidance_is_safe_to_inject` outside tests/compat shims.

---

### Phase 3 — clean repo and packaging

**Goal:** reproducible install.

Tasks:

1. Classify all dirty/untracked files.
2. Delete only after archive and explicit manifest approval.
3. Remove generated artifacts from committed source unless required.
4. Update `.gitignore`.
5. Rebuild wheel/sdist from clean tree.
6. Fresh venv install and smoke:
   - `borg version`
   - `borg-doctor --json`
   - `borg rescue ... --json`
   - `borg first-10 --json`
   - `python -c 'import borg; print(borg.__version__, borg.check(...))'`.

Gate:

- Clean tree.
- Fresh install passes.
- Build artifact contains no stale `build/lib` code.

---

### Phase 4 — resolve ecosystem package boundaries

**Goal:** no public namespace collisions.

Tasks:

1. Update `borg-collective-py` entrypoints.
2. Add test extras.
3. Add CI for SDK.
4. Add local no-auth Worker tests.
5. Make `borg-init` verify canonical package paths.
6. Update all docs to show the target architecture.

Gate:

- Installing all packages in one test environment does not shadow `borg`.
- Backend/SDK tests are deterministic.

---

### Phase 5 — harden security and trust path

**Goal:** security state is explicit, not implied.

Tasks:

1. Define `SecurityState` / `TrustEnvelope` schema.
2. Add it to shared outputs.
3. Ensure global/shared publishing rejects invalid/unsigned/unsafe atoms.
4. Expand privacy/prompt-injection fixture corpus.
5. Add adversarial retrieval tests: historical advice cannot become instructions.
6. Add revocation propagation test for local and future federated paths.

Gate:

- Security gate fails on missing trust fields.
- Public docs cannot overclaim cryptographic trust.

---

### Phase 6 — first-10 supervised beta

**Goal:** prove actual human/agent value.

Tasks:

1. Recruit 10 supervised users/tasks.
2. Run exact install/onboarding flow.
3. Capture transcript/log evidence.
4. Record every outcome.
5. Add regression tests for every miss.
6. Publish a machine-readable first-10 scoreboard.

Gate:

- 6/10 relevant ACTION/STOP/VERIFY without maintainer handholding.
- 0 hidden misses.
- Any severe wrong guidance blocks rollout until fixed.

---

### Phase 7 — broad production decision

Only after Phases 0–6 pass.

Gate for broad launch:

- no runtime split-brain;
- no CLI collisions;
- clean repo;
- fresh install green;
- security/trust fields enforced;
- federation/SDK/backend deterministic tests green;
- first-10 beta pass;
- docs and package metadata match current truth;
- no unsupported success-rate claims.

---

## 6. Immediate next sprint checklist

### Day 1: stop the bleeding

Progress 20260514-0955:

- [x] Selected P0.4 shared confidence gate as the first implementation target because stale guidance injection is the highest trust risk.
- [x] Added `borg/core/confidence_gate.py` as the canonical dependency-light module for no-match, synthetic/zero-real suppression, pasted-guidance stripping, permission-signal matching, trace confidence, and pack confidence.
- [x] Added `borg/tests/test_confidence_gate.py` covering the exact stale `=== BORG GUIDANCE === ... PACK GUIDANCE (bash-permission-denied)` failure mode, zero-real pack guidance, no-match suppression, real high-confidence allowance, and real permission-positive control.
- [x] Refactored canonical `borg/integrations/mcp_server.py` compatibility wrappers to delegate to `borg.core.confidence_gate`.
- [x] Refactored both Hermes plugin paths to call `borg.core.confidence_gate` when available, retaining local fallback for stale installs.
- [x] Added defensive `confidence_gate.py` copies to installed/runtime mirror candidates.
- [ ] Finish terminal verification job for current confidence gate patches.
- [ ] Add MCP/runtime fingerprint canary.
- [ ] Run served-process canary.
- [ ] Get operator-approved reload only after fingerprint proof.

### Day 2: clean source of truth

- [ ] Generate no-loss dirty tree manifest.
- [ ] Archive old mirrors and docs clones after diff harvest.
- [ ] Remove `build/lib` from production truth.
- [ ] Clean `.gitignore`.
- [ ] Reconcile README / status / go-no-go docs.

### Day 3: install and namespace

- [ ] Fresh wheel/sdist install smoke.
- [ ] Resolve `borg-collective-py` CLI collisions.
- [ ] Add SDK test extras.
- [ ] Add Worker local/no-auth tests.
- [ ] Verify `borg-init` installs/verifies canonical `agent-borg`.

### Day 4: security/trust hardening

- [ ] Add explicit trust/security envelope to outputs.
- [ ] Expand adversarial privacy/injection corpus.
- [ ] Enforce invalid-signature failure for shared/global paths.
- [ ] Add revocation no-retrieval tests.

### Day 5: first-user beta packet

- [ ] Generate first-10 scoreboard template.
- [ ] Run 2 internal dry-runs.
- [ ] Fix all misses.
- [ ] Start 10 supervised user/task run.

---

## 7. Hard gates / exact verification commands

These are the commands the implementation phase should run from clean environments. They are included here as the contract; raw stdout/stderr must be captured when executed.

```bash
# canonical tests
cd /root/hermes-workspace/borg
python -m pytest -q borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py borg/tests/test_rescue.py borg/tests/test_prompt_injection.py borg/tests/test_privacy_structured.py borg/tests/test_distribution_readiness.py borg/tests/test_version_consistency.py borg/tests/test_runtime_doctor.py

# readiness/security gates
python eval/borg_day_one_readiness.py
python eval/run_first_user_release_gate.py
python scripts/security_gate_check.py
python eval/run_readiness_gates.py

# fresh build/install
rm -rf build dist *.egg-info
python -m build
python -m venv /tmp/borg-prod-verify-venv
/tmp/borg-prod-verify-venv/bin/pip install dist/agent_borg-*.whl
/tmp/borg-prod-verify-venv/bin/borg version
/tmp/borg-prod-verify-venv/bin/borg-doctor --json
/tmp/borg-prod-verify-venv/bin/borg rescue 'ModuleNotFoundError: No module named flask' --json
/tmp/borg-prod-verify-venv/bin/borg first-10 --json
/tmp/borg-prod-verify-venv/bin/python - <<'PY'
import borg, json
print(borg.__version__)
print(json.dumps(borg.check('ModuleNotFoundError: No module named flask', top_k=1), indent=2))
PY

# served MCP canary, should be implemented in repo
python scripts/mcp_served_canary.py --expect-module borg.integrations.mcp_server --json

# ecosystem package boundaries, after fixes
cd /root/hermes-workspace/borg-collective-py
python -m venv /tmp/borg-sdk-verify-venv
/tmp/borg-sdk-verify-venv/bin/pip install -e '.[test]'
/tmp/borg-sdk-verify-venv/bin/python -m pytest -q

cd /root/hermes-workspace/borg-collective-v1
npm ci
npm run test:local
```

---

## 8. Product/claim language after rebuild

### Allowed after P0 close + first-10 pass

- “Borg is a local-first collective memory layer for AI coding agents.”
- “Borg helps agents avoid previously observed dead ends by surfacing ACTION / STOP / VERIFY guidance.”
- “Borg fails closed when it cannot prove relevance.”
- “Shared learning atoms are privacy-scanned, prompt-injection scanned, signed/revocable where applicable, and carry explicit trust state.”

### Not allowed until controlled eval proves it

- “Borg improves success rate by X%.”
- “Borg is production-proven at global scale.”
- “All packs are cryptographically trusted.”
- “Fully autonomous broad public launch ready.”
- “Safe for arbitrary secret-bearing enterprise traces.”

---

## 9. Bottom line

Borg is close, but not because every subsystem is ready. Borg is close because the right nucleus is now obvious:

```text
local-first failure memory + fail-closed confidence + privacy-safe persistence + honest outcome feedback
```

The production rebuild should cut everything else down to clear boundaries around that nucleus. If we do that, Borg becomes a product I would be proud to ship: boring install, singular runtime, no misleading guidance, explicit trust state, clean proof gates, and real first-user evidence.

Until then, the honest status remains:

> **Controlled-go for supervised first-user beta. NO-GO for broad unattended production.**
