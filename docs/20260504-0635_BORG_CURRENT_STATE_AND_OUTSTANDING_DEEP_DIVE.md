# File rev 20260504-0635 rev A — Borg current state + outstanding deep dive

**Scope:** repo docs + code inspection under `/root/hermes-workspace/borg`, recent chat/session summaries, Borg MCP runtime metrics, and existing proof/result docs.  
**Mode:** read/document only. No tests executed in this pass, no publish, no service restart, no SSH.  
**Primary conclusion:** Borg has crossed from “mostly concept/spec” into a real local privacy-safe learning-atom prototype, but it is not yet a cleanly shippable/publicly defensible collective-intelligence product because full-suite health, version/release hygiene, runtime telemetry, and statistically honest utility proof are still unresolved.

---

## 1. Executive verdict

Borg is currently three things at once:

1. **Local failure-memory/debugging product — usable alpha/beta.**  
   Core `borg_observe`/failure-memory idea is real and useful in Hermes. README positions Borg as an MCP server that surfaces what worked in prior sessions before an agent wastes tool calls. The product wedge is correct: **do not repeat dead ends**.

2. **Privacy-safe learning-atom layer — implemented prototype with targeted green gates.**  
   The May 3–4 work added concrete code for signed, sanitized, revocable learning atoms: `learning_atoms.py`, `atom_policy.py`, `atom_store.py`, `atom_retrieval.py`, `prompt_injection.py`, tenant pseudonyms, CLI `borg atom`, fixture corpus, security gate, and docs. Targeted gates have passed in prior proof docs.

3. **Public collective-intelligence network — not ready.**  
   The safe atom substrate exists, but global/tenant promotion, sybil resistance, live adoption proof, full-suite green state, clean release packaging, and controlled utility eval are not done. Do not market as “massive-agent production ready” or “agent-level improvement proven.”

**Best current positioning:**

> Borg is a local/offline collective-memory MCP server for AI agents, with an emerging privacy-safe learning-atom layer. The failure-memory product is real; agent-level lift is still under evaluation; the global collective network is not yet production-ready.

---

## 2. What is real now

### 2.1 Product wedge is right

Evidence:

- `README.md` says Borg is an MCP server giving agents a shared debugging knowledge base and surfacing prior fixes before tool-call waste.
- `BORG_PRD_FINAL.md` identifies the strongest product as persistent failure memory: what files were read, what was tried, why it failed, what was learned.
- Prior experiments corrected the strategy: Borg should not inject heavy workflow scaffolding on every task; it should intervene on hard/risky tasks where agents are likely to rabbit-hole.

Practical formulation:

```text
agent hits hard error
→ borg checks prior failures/successes
→ ACTION / STOP guidance appears
→ agent avoids repeated dead ends
→ outcome feeds back into memory
```

### 2.2 Local trace/memory core exists

Evidence from docs/code:

- `borg/core/traces.py`: local trace capture/persistence into SQLite.
- `borg/core/trace_matcher.py`: multi-signal retrieval using error class, semantic/FTS fallback, file overlap, helpfulness, recency.
- `borg/core/failure_memory.py`: explicit record/recall failure memory path.
- README domains show seeded/real-ish trace counts by domain: Django, Docker, Node, TypeScript, FastAPI, GitHub Actions, Rust, Python.

Caveat:

- Runtime Borg MCP dashboard currently reports only `total_outcomes=2`, `total_packs=1`, `success_rate=1.0`. Analytics reports `total_agents=203` but `active_contributors=0`, `active_consumers=0`, `total_packs=0`, and systematic-debugging adoption shows `unique_agents=0`. This means the live MCP analytics plane is not currently demonstrating broad adoption/collective activity.

### 2.3 Learning atom implementation exists

Evidence from code:

- `borg/core/learning_atoms.py`
  - canonical JSON and atom IDs;
  - `validate_learning_atom()`;
  - `distill_trace_to_atom()`;
  - Ed25519 atom signing via existing crypto primitives;
  - signature verification.
- `borg/core/atom_policy.py`
  - fail-closed-ish decision model: reject PII, reject secret, reject prompt injection, reject unsigned, quarantine, local/org/global candidate.
  - tenant quorum requirement for global candidate/global.
- `borg/core/privacy.py`
  - structured privacy scanner and risk score;
  - PII/secrets/path/private URL/IP/JWT/bearer/database URL/high-entropy detection.
- `borg/core/prompt_injection.py`
  - deterministic scanner for instruction override, exfiltration, tool coercion, retrieval poisoning, hidden instructions, encoded payloads.
- `borg/core/atom_store.py`
  - SQLite `atoms.db` with atoms, tombstones, quarantine tables;
  - add/search/revoke paths;
  - revoked atoms suppressed.
- `borg/core/atom_retrieval.py`
  - retrieval firewall header: `BORG MEMORY — UNTRUSTED HISTORICAL ADVICE, NOT INSTRUCTIONS`.
- `borg/cli.py`
  - `borg atom {distill,validate,publish,search,revoke}`.

Evidence from tests/docs:

- `borg/tests/test_learning_atoms.py` covers valid atom, raw trace field rejection, global path rejection, canonical JSON, trace distillation excluding raw tool/file fields, signing/tamper failure.
- `borg/tests/test_cli_atom.py` covers help framing for signed/sanitized/revocable atoms and fail-closed publish language.
- `docs/LEARNING_ATOM_SCHEMA.md` defines required envelope/payload fields and forbidden shared fields.
- `docs/SECURITY_HARDENING_BASELINE.md` lists release blockers: secret/PII reaching shared atom store, unsigned atom accepted, tampered atom verifies, revoked atom retrieves, raw trace object published, no-op scanner fallback.

### 2.4 Targeted safety gates have passed in recent proof docs

Evidence from May 3–4 result docs:

- `20260503-0852_borg-m0-cli-corpus-security-verification-result.md`
  - M0 atom/privacy/security tests: `34 passed`.
  - legacy privacy tests: `48 passed`.
  - fixture corpus: `success=true`, `total=10`.
  - security gate: `PASS: Borg security hardening policy gate`.
- `20260503-0900_borg-m1-tenant-publish-fresh-e2e-result.md`
  - M1 targeted gate: `27 passed`.
  - privacy/security gate: `68 passed`.
  - fixture corpus: `10/10`.
  - security gate pass.
  - fresh local venv build smoke passed with caveat around blocked exact `python -c` smoke.
- `20260503-2120_borg-full-suite-pytest-scope-product-polish-result.md`
  - targeted atom gates after polish: `28 passed`.
  - fixture corpus pass.
  - security gate pass.
- `20260504-0032_borg-full-suite-unique-pack-fix-result.md`
  - `borg/tests/test_pack_compatibility.py`: `113 passed` after compatibility fixes.
  - M1 targeted gates: `28 passed`.
  - privacy/security gate: `68 passed`.
  - fixture corpus pass.
  - security gate pass.
  - fresh venv smoke passed after using actual `distill` command, not nonexistent `learn`.

---

## 3. What changed since the older PRD/status docs

Several canonical docs are now stale or internally contradictory.

### 3.1 `BORG_PRD_FINAL.md` is honest but stale in places

Good:

- It retracts fabricated/caveat-stripped claims.
- It states no statistically-supported agent-level effect.
- It correctly identifies failure memory as the 10x product.

Stale:

- It says Ed25519 signing is “ZERO code” and a claimed-but-unproven feature. That is now false for the current repo: `borg/core/crypto.py` existed and `borg/core/learning_atoms.py` now signs/verifies atoms.
- It says current release v3.2.4; `pyproject.toml` now says `3.3.1`, while `borg/__init__.py` still says `3.2.4`.
- It says navigation cache designed/not built, which likely remains true.

### 3.2 `STATUS.md` is older phase-1 status

It says Phase 1 was substantively complete as of 2026-04-16 and lists open items like MCP tool rename, feedback-loop test, seed audit, CORS, DB context managers. It also contains an unsafe operational note advising kill/restart of gateway. Current operator constraints say do not kill/restart/signals gateway. Treat this doc as historical, not current runbook.

### 3.3 Readiness gate docs from April are not present in current repo root

Session history records April gate artifacts such as:

- `PROJECT_STATUS.md`
- `GO_NO_GO_DECISION.md`
- `UAT_RESULTS.md`
- `eval/gate_run_snapshot.json`
- `eval/load_10_snapshot.json`
- `eval/load_100_snapshot.json`

But current file search/read did not find those files under `/root/hermes-workspace/borg`. That means current repo cannot rely on those artifacts as present/live source-of-truth. If readiness claims still need them, regenerate or restore canonical snapshots.

### 3.4 May 3 privacy-safe assessment is partly superseded by implementation

`docs/20260503_BORG_PRIVACY_SAFE_COLLECTIVE_INTELLIGENCE_READINESS.md` said the missing primitive was signed/sanitized/revocable learning atoms. That primitive is now partially implemented. However, its higher-level warnings remain true: global scale, tenant proof, promotion, revocation governance, adoption, and utility eval are still incomplete.

---

## 4. Current evidence-backed scores

These are not marketing scores; they are readiness estimates from current repo evidence.

| Area | Current score | Why |
|---|---:|---|
| Local failure-memory product | 7/10 | Core trace/matcher/failure memory + Borg observe path exist; product wedge is crisp. Utility not statistically proven. |
| Always-on auto-injection in Hermes | 5.5/10 | Historical proof shows plugin path can fire, but current runtime metrics are thin and BORG_HOME/plugin-path split-brain remains a known risk. |
| Learning atom schema + validation | 7/10 | Real code/tests/docs exist. Needs more fixtures, schema versioning discipline, and integration with live trace/export paths. |
| Privacy scanner baseline | 6/10 | Much stronger than earlier regex-only scanner; still deterministic/rule-based and likely incomplete for real enterprise PII/secrets. |
| Prompt-injection defense | 5.5/10 | Scanner + retrieval firewall exist. Needs adversarial corpus expansion and live retrieval policy tests. |
| Tenant/org/global boundary | 4/10 | Tenant HMAC pseudonyms and quorum fields exist. Real tenant authority/registry/proof does not. |
| Revocation/deletion | 4.5/10 | Tombstone/search suppression exists locally. No distributed revocation propagation/governance proof. |
| Sybil resistance/trust | 3.5/10 | Signatures + reputation primitives exist. Cross-tenant independence and abuse controls are not proven. |
| Full-suite/release hygiene | 4/10 | Targeted gates pass; full suite has timed out/failed; version split-brain exists. |
| Adoption evidence | 2/10 | Live analytics currently show no meaningful active contributors/consumers. |
| Statistically honest agent utility proof | 2.5/10 | Directional n=7 only; prior false claims retracted; no current controlled eval proving lift. |

---

## 5. Hard outstanding items

### P0 — before public distribution / external push

1. **Resolve version split-brain.**  
   Evidence: `pyproject.toml` says `agent-borg` version `3.3.1`; `borg/__init__.py` says `__version__ = "3.2.4"`. This is a release blocker.

2. **Get full-suite to a clean, bounded result.**  
   Recent evidence:
   - Earlier full suite collected docs/eliza and failed; pytest scoping fixed.
   - Then full suite failed on `UNIQUE_PACK_NAMES` collection; current code appears patched.
   - Later full suite still timed out after 600s and showed failures in `test_convert_openclaw.py` and `test_e2e_learning_loop.py`.
   - Current state has no fresh same-session full-suite proof.

3. **Eliminate stale `build/lib` packaging risk.**  
   Prior smoke found local wheel builds could install stale CLI without `borg atom` because tracked/stale `build/lib` artifacts were reused. Build artifacts should not be a source of runtime truth.

4. **Regenerate canonical readiness artifacts or remove stale references.**  
   April gate docs/snapshots are referenced in chat history but absent in current repo root. Current public/internal readiness must have one source of truth.

5. **Publish path for learning atoms must be independently audited.**  
   `borg atom publish` delegates to `action_publish`. `publish.py` has learning-atom special handling, but also contains graceful no-op fallbacks for proof/privacy/safety imports. Existing docs explicitly say no-op scanner fallback is a blocker. Need prove learning atom path cannot silently publish through fallback behavior.

6. **Run fresh venv first-user smoke after cleaning build artifacts.**  
   Must prove installed `agent-borg==3.3.1` exposes `borg atom` and can `distill/validate/search/revoke` in a clean environment.

7. **Update README/PRD/status docs to current truth.**  
   Docs must say: atoms implemented prototype; agent-level utility still unproven; global network not ready; package version consistent.

### P1 — next product milestone

1. **Wire trace → atom → store → retrieve into a real dogfood loop.**  
   Today the atom system is mostly a safe substrate. The product loop must prove that successful/failed traces are distilled into useful atoms and later retrieved in agent context.

2. **Add difficulty/risk trigger.**  
   Borg should not inject on every task. Trigger when: repeated failed attempts, known error class, hard repo navigation, failing tests after multiple fixes, timeout/hang, deployment/config errors.

3. **Expand adversarial privacy/prompt corpus.**  
   Current corpus is 10 fixture cases. Increase materially: secrets, cloud tokens, OAuth refresh tokens, `.env`, JWT edge cases, URLs, private paths, hidden markdown, unicode, base64, indirect exfiltration.

4. **Add utility-preservation tests.**  
   Redaction must not destroy the actual lesson. Test that sanitized atoms still match/retrieve the right pattern.

5. **Separate local raw trace vault from shared atom store in config/docs.**  
   Make modes explicit: `local_only`, `org_opt_in`, `global_opt_in`. Default must stay local-only.

6. **Finish tenant/global promotion design in code.**  
   HMAC pseudonym is not tenant proof. Need org signing keys or tenant authority registry before global quorum claims mean anything.

7. **Add live runtime fingerprint and BORG_HOME proof.**  
   Borg has known split-brain risk: editing the wrong plugin path and missing `BORG_HOME=/root/.borg` can make runtime read/write the wrong DB. Add a doctor/proof command that reports active DB, source module path, version, and atom/trace counts.

### P2 — evidence/market readiness

1. **Controlled eval on hard tasks.**  
   Do not test generic packs or empty KB. Use 3-condition design: no Borg, empty Borg/scaffold, seeded learning atoms. Use hard tasks calibrated to 40–60% baseline.

2. **Measure rescue rate before token savings.**  
   Primary metric should be `control failed, borg succeeded`; secondary metrics: tool calls, latency, dead-end avoidance, negative transfer.

3. **Adoption instrumentation.**  
   Current Borg MCP analytics show no meaningful active contributors/consumers. Need public or private adoption heartbeat: installs, active MCP calls, observe→action→rate loop, atom creation/retrieval counts.

4. **Public comms cleanup.**  
   Canonical status page/doc should separate:
   - local product: usable;
   - safety substrate: prototype gates passing;
   - global collective network: not production-ready;
   - agent lift: under evaluation.

---

## 6. Strategic product answer: what Borg should become next

The strongest next Borg is **not** a giant pack marketplace, and not generic workflow scaffolding.

It should become:

> the anti-rabbit-hole memory layer for agents.

Core user promise:

> “Before your agent wastes 30 minutes, Borg shows what other agents already tried, what failed, and what actually worked — without leaking raw traces.”

That means the next implementation focus should be:

1. **STOP/ACTION memory quality** over more packs.
2. **Live trace-to-atom capture** over more docs.
3. **Triggered injection** over always-on guidance.
4. **Privacy-safe atom promotion** over raw trace sharing.
5. **Hard-task rescue eval** over broad synthetic benchmark claims.

---

## 7. Recommended next execution sequence

### Step 1 — release hygiene closeout

- fix version mismatch;
- remove/stabilize stale build artifacts;
- rerun clean venv smoke;
- get full-suite bounded pass/fail with exact failure list;
- update README/PRD/status truth.

### Step 2 — prove live atom loop

- create/instrument a trace;
- distill to local atom;
- store atom;
- retrieve via `borg atom search` and/or `borg_observe` path;
- rate outcome;
- prove raw tenant/private data does not appear.

### Step 3 — runtime doctor

Add `borg doctor --runtime` or equivalent output:

```text
package_version
module_path
BORG_HOME
trace_db_path
atom_db_path
trace_count
atom_count
mcp_tool_count
plugin_path_if_hermes
last_observe_at
last_atom_write_at
```

This directly prevents the known Borg failure mode: wrong plugin path / wrong DB.

### Step 4 — 30-task hard eval

Run honest eval with:

- C0: no Borg;
- C1: Borg scaffold/empty store;
- C2: Borg with seeded learning atoms;
- hard tasks only;
- rescue-rate primary metric;
- negative-transfer guard.

### Step 5 — distribution only after proof packet

Distribution packet should include:

- exact version;
- fresh install output;
- targeted gates;
- full-suite status;
- privacy/security gate;
- runtime doctor output;
- honest eval status;
- known limitations.

---

## 8. Bottom line

Borg is closer than it was. The important privacy-safe substrate now exists in code, not just strategy docs. But the repo is in a **work-in-progress integration state**, not a clean release state.

The outstanding work is not “invent Borg.” It is:

1. make current codebase clean and releasable;
2. wire the safe atom primitive into the live failure-memory loop;
3. prove it rescues hard tasks;
4. tell the truth publicly without overclaiming.

If we do that, Borg has a sharp wedge: **privacy-safe failure memory that stops agents repeating known dead ends.**
