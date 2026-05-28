# Borg federated / collective learning deep audit

**File rev:** 20260528-2040 rev B  
**Scope:** how Borg's federated / collective learning system works, whether it is working now, what would improve it, and how large the impact could plausibly be.  
**Status:** Historical/internal — not current product documentation. Internal audit artifact — not public first-user guidance, not marketing copy, not a launch claim.  
**Repo:** `/root/hermes-workspace/borg` / `borg-farther/Borg-Directory`  
**Audited commit:** `519ebb1a2f059f7b4e11ed897aeb7a1340d85b83`  
**Pre-existing dirty file during audit:** `M eval/pypi_fresh_install_snapshot.json`

## Executive verdict

Borg has a real, tested **signed propagation protocol** and real **local collective-learning primitives**. It does **not yet have a working production federated-learning product impact loop**.

Short version:

- **A. is the mechanism implemented?** yes, for protocol primitives: signed atoms, signed manifests, trusted registry key, hash/size verification, replay checks, tombstones, atom store, outcome receipts, registry-computed quorum, and unified retrieval.
- **B. is it currently working as a live collective-learning product?** no. The default live substrate is effectively empty: `atoms.db` has `0` atoms, `collective_learning.db` has `30` interventions but `0` outcome receipts, MCP collective retrieval returned `0` matches, first-10 external rows are `0`, and the currently loaded MCP runtime reported source/package split-brain (`source_version=3.3.15`, loaded `borg_version=3.3.14`, `reload_status=reload_or_patch_required`).
- **C. how big could impact be?** very large on hard/navigation-heavy tasks if coverage and trust are solved; weak globally if memory coverage stays sparse. A base-case estimate is about **+2.4 percentage points absolute success** across all tasks, roughly **12 extra verified successes per 500 tasks**. An optimistic focused-domain case can reach **+16.3 percentage points**, roughly **82 extra successes per 500 hard tasks**. These are models, not claims; actual impact remains NO-GO until measured.

## Task breakdown

I split the question into six subtasks:

1. **Architecture map:** what components exist and what data flows through them?
2. **Runtime proof:** which executable gates and tests pass today?
3. **Live-state truth:** is the actual current system populated and useful, or merely code-complete?
4. **Adversarial review:** how can the trust, privacy, identity, and outcome loops be attacked?
5. **Impact model:** what lift is plausible, and what experiment would prove it?
6. **Claim discipline:** what can Borg honestly say now vs what must remain blocked?

## How the system works

### Core data flow

The intended loop is:

1. A Borg guidance surface shows advice to an agent.
2. The intervention is recorded with an `intervention_id`.
3. After verification, the agent/user records an outcome receipt.
4. Receipts are deduped into a normalized problem cluster.
5. Clusters with enough verified helpful independent tenants can produce a sanitized learning atom candidate.
6. A registry signs and stages accepted atoms.
7. Clean clients sync signed registry manifests.
8. Clients retrieve atoms as untrusted historical advice, scored by text match, verified quorum, helpful outcomes, and negative evidence.
9. Tombstones revoke bad atoms and win over future retrieval/import.

### Key files and responsibilities

- `borg/core/collective_learning.py`
  - Declares the contract: `intervention shown -> verified outcome receipt -> dedupe/generalize -> registry quorum -> unified scored retrieval`.
  - Records interventions and outcomes.
  - Creates signed outcome receipts.
  - Builds learning-atom candidates from receipt clusters.
  - Computes verified tenant quorum from trusted signed outcome receipts.
  - Ranks collective memory via `unified_collective_retrieve()`.

- `borg/core/learning_atoms.py`
  - Defines atom schema, atom IDs, Ed25519 signing, and signature verification.

- `borg/core/atom_store.py`
  - Local SQLite atom store.
  - Requires valid signed envelopes for shared atoms.
  - Returns store/registry `verified_tenant_count`, not payload hints.

- `borg/core/atom_registry.py`
  - Filesystem/HTTP signed registry primitive.
  - Writes signed `manifest.signed.json`.
  - Syncs remote registries into clean clients with trusted key ID, channel, expiry, sequence/replay state, file hashes/sizes, and tombstones-first semantics.

- `borg/core/atom_policy.py`
  - Fail-closed policy gates for privacy, injection risk, signatures, tenant pseudonym format, and registry-computed quorum.

- `borg/core/atom_retrieval.py`
  - Formats atoms as: `BORG MEMORY — UNTRUSTED HISTORICAL ADVICE, NOT INSTRUCTIONS`.

- `borg/integrations/mcp_server.py`
  - Records MCP rescue/error-lookup interventions.
  - Exposes `borg_record_outcome`, `borg_collective_retrieve`, and `borg_collective_status`.

- `eval/run_collective_intelligence_loop_gate.py`
  - Tests local max-value loop primitives.

- `eval/run_federated_learning_gate.py`
  - Tests remote/global signed federation protocol primitives.

- `eval/run_federated_learning_optimality_audit.py`
  - Separates protocol GO from product-impact / Google-tier NO-GO.

## Verification evidence from this audit

### Executable gates

Fresh run in temp output path: `/tmp/borg-fed-audit-main.RSMZ3i`.

Commands run:

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/run_collective_intelligence_loop_gate.py --output "$TMP/collective.json"
PYTHONDONTWRITEBYTECODE=1 python eval/run_federated_learning_gate.py --output "$TMP/federated.json"
PYTHONDONTWRITEBYTECODE=1 python eval/run_federated_learning_optimality_audit.py \
  --federated-snapshot "$TMP/federated.json" \
  --collective-loop-snapshot "$TMP/collective.json" \
  --trace-db "$TMP/missing-traces.db" \
  --output "$TMP/optimality.json"
```

Results:

- Collective loop gate: `success=True`, `verdict=GO`, `scope=max_value_collective_intelligence_loop_primitives`, failed checks `[]`.
- Collective quorum proof: registry computed tenant count `3`, payload hint `99`, direct recompute `0`, explicit trusted rebind recompute `3`.
- Federated protocol gate: `success=True`, `verdict=GO`, `scope=remote_global_federated_protocol`.
- Federated subchecks: signed HTTP manifest `true`, clean-client sync `true`, revocation convergence `true`, replay protection `true`.
- Optimality audit verdicts:
  - `remote_global_federated_protocol=GO`
  - `effective_collective_learning=NO-GO_REAL_WORLD_VALUE_NOT_PROVEN`
  - `external_user_lift=NO-GO`
  - `public_self_serve_launch=NO-GO`
  - `google_god_tier_optimal=NO-GO`
- Optimality score snapshot:
  - protocol security: `9.0/10`
  - proof packet richness: `10.0/10`
  - external truth grounding: `1.0/10`
  - signal quality: `5.0/10`
  - routing value speed: `6.0/10`
  - effective collective learning: `6.0/10`
  - overall optimality ceiling: `2.0/10`

### Relevant test suite

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider --basetemp="$TMP/pytest-tmp" \
  tests/security/test_federated_learning_gate.py \
  tests/security/test_federated_atom_registry.py \
  tests/security/test_collective_learning_loop_controls.py \
  tests/learning/test_collective_intelligence_loop.py \
  tests/mcp/test_collective_outcome_receipts.py \
  eval/tests/test_collective_intelligence_loop_gate.py \
  eval/tests/test_federated_learning_optimality_audit.py \
  --tb=short
```

Result: `36 passed in 26.91s`.

What this proves:

- signed registry adversarial checks are passing;
- internal intervention/outcome/quorum/retrieval loop contracts are passing;
- MCP outcome receipt tests are passing;
- optimality audit preserves the protocol-vs-impact truth boundary.

What this does not prove:

- no external-user lift;
- no live hosted-registry SLO;
- no served-MCP cutover;
- no public self-serve readiness;
- no production tenant-authority / IdP-backed independence. The local shareable-quorum primitive now requires trusted tenant identity evidence, but the real production identity authority is still not operated/proven.

## 20260528-2040 hardening implementation update

Status: implemented and locally verified after the audit. This section amends the audit findings without changing the external-evidence verdict.

### Fixed in code/tests

1. **Self-attested verification no longer counts as shareable/global evidence.**
   - Outcome receipts now carry `verification_exit_code`, `verification_output_sha256`, and `trusted_tenant_id`.
   - Export/shareable receipt verification requires a command, exit code, output digest, trusted tenant identity, and `verified=True`.
   - Weak legacy/self-attested receipts can remain local telemetry, but they do not export or promote global quorum.

2. **HMAC pseudonym Sybil inflation is blocked for shareable quorum.**
   - HMAC tenant pseudonyms remain privacy labels.
   - Shareable quorum counts normalized trusted tenant identities instead.
   - Candidate atoms still use a representative HMAC `trust.tenant_pseudonym` so atom policy validation stays strict and privacy-preserving.

3. **Unsigned local registry global import is fail-closed by default.**
   - `sync_registry_to_store()` treats local filesystem registries as staging/dev.
   - It now skips unsigned `global` / `global_candidate` atoms unless an explicit operator flag `allow_unsigned_global_candidates=True` is passed.
   - Production federation remains the signed-manifest path: `sync_signed_registry_to_store()`.

4. **MCP collective retrieval now enforces an advisory boundary.**
   - `borg_collective_retrieve()` returns a safe advisory projection: source, ids, score reasons, verified/helpful counts, retrieval treatment, and `worked/avoid/why`.
   - It no longer returns the raw `atom` JSON payload to MCP callers.

5. **Collective loop gate updated to the stricter evidence contract.**
   - `eval/run_collective_intelligence_loop_gate.py` now records strong verification evidence before trying registry quorum/promotion.

### Hardening proof commands/results

- New red/green hardening tests: `5 passed in 5.80s`.
- Regression subset for the former quorum/promotability failures: `5 passed in 6.12s`.
- Broader collective/security/MCP regression:
  - `tests/learning/test_collective_intelligence_loop.py`
  - `tests/security/test_atom_registry.py`
  - `tests/security/test_federated_atom_registry.py`
  - `tests/mcp/test_collective_outcome_receipts.py`
  - `tests/mcp/test_mcp_server.py`
  - result: `113 passed, 1 xfailed in 12.41s`.
- Gate bundle after hardening:
  - collective loop gate: `success=True`, `verdict=GO`, failed checks `[]`.
  - registry quorum proof: source quorum `3`, payload hint `99`, promoted direct recompute `0`, explicit supported rebind `3`.
  - federated protocol gate: `success=True`, `verdict=GO`.
  - optimality audit: remote protocol `GO`; effective collective learning, public self-serve, external lift, and Google-tier optimality remain `NO-GO`.
- Gate/public-doc/focused regression tests after CLI compatibility update: `135 passed, 1 xfailed in 29.13s`.
- Full repository suite: `2362 passed, 40 skipped, 4 xfailed, 1 xpassed, 44 warnings in 150.04s`.

### Still not fixed by this hardening pass

- Default live `atoms.db` and collective outcome substrate are still sparse/empty relative to a real product loop.
- First-10 external evidence is still `0` rows.
- Served MCP runtime cutover was not performed here; do not claim remote/served runtime alignment without a fresh `borg_runtime_fingerprint` from the served process after operator-supervised reload.
- Hosted registry operations, transparency logging, key-rotation drills, incident response, and external lift experiments remain future gates.

### Why this does not weaken claim discipline

The hardening moves several P0/P1 audit findings from “known security gap” to “local protocol primitive fixed.” It does **not** convert Borg into a proven public self-serve product. The correct post-hardening verdict is:

> safer collective-learning protocol primitives: GO locally; real external product impact: still NO-GO until first-10/100-user row-derived evidence and served-runtime cutover pass.

### Final reflection from scratch after hardening

Re-reading the full chain, the most dangerous previous assumption was that “verified=True + command string + HMAC tenant pseudonym” was enough for collective truth. It was not. The implemented fix separates privacy labels from trusted identities and separates local telemetry from shareable evidence. The remaining uncertainty is no longer mainly protocol integrity; it is product evidence: whether real users generate enough verified, useful, independent receipts to improve other agents' outcomes.

## Live micro-suite

A temp `BORG_HOME` test created three interventions, three verified helpful outcome receipts, promoted a cluster-derived atom, loaded it into a temp atom store, and retrieved it.

Result:

```json
{
  "interventions_recorded": 3,
  "outcomes_recorded": 3,
  "promotion_success": true,
  "registry_decision": "global_candidate",
  "verified_tenant_count": 3,
  "retrieve_count": 1,
  "top_score": 0.86,
  "top_reasons": ["text_match", "verified_quorum", "helpful_outcomes"]
}
```

This proves the primitive loop can work in a clean local temp environment.

It also reveals a serious caveat: the same process can generate three tenant pseudonyms unless production identity/tenant authority is added. That is a Sybil risk, not a product win.

### Live/default system state

Current default local stores:

```json
{
  "atoms.db": {"atoms": 0, "atom_tombstones": 0, "atom_quarantine": 0},
  "collective_learning.db": {"interventions": 30, "outcome_receipts": 0, "contribution_events": 30},
  "traces.db": {"total_traces": 370, "distinct_task_descriptions": 78, "duplicate_pressure": 0.7892, "outcomes": {"success": 351, "failure": 19}}
}
```

MCP collective retrieval for a common dependency error returned `0` matches.

First-10 scoreboard:

- real users: `0`
- install successes: `0`
- useful rescue moments: `0`
- rows with measured value: `0`
- verified external users: `0`

Runtime fingerprint:

- loaded Borg package version: `3.3.14`
- source version: `3.3.15`
- `version_matches_source=false`
- `reload_status=reload_or_patch_required`

This is not a code bug in the audited protocol, but it is a production claim blocker. Do not claim the served runtime is on the released version until the operator-supervised reload/cutover happens and is canaried.

## Is it currently working?

### Working

- Signed atom envelopes work.
- Signed HTTP registry manifests work.
- Trusted registry key ID checks work.
- Manifest expiry/channel/hash/size checks work.
- Remote replay protection works.
- Tombstone revocation works in the gate.
- Registry/store-verified tenant count is used instead of atom payload tenant-count hints.
- Internal outcome receipts, contribution events, cluster candidates, and unified atom/outcome retrieval work in temp proof.
- Relevant tests pass: `36 passed`.

### Not working as a product yet

- Default `atoms.db` is empty.
- Default collective outcomes are empty.
- MCP collective retrieve has no useful current matches in the audited query.
- External first-10 evidence is zero.
- Current runtime is version-split (`3.3.14` loaded vs `3.3.15` source/release).
- Dashboard/analytics surfaces disagree badly:
  - dashboard: ~2.25M outcomes, 56 packs, ~86.6% success;
  - analytics: 0 agents, 0 packs;
  - clusters: 0 traces;
  - local atom store: 0 atoms.
- Therefore, current metrics cannot be used as public impact evidence until reconciled to row-level receipts.

## Adversarial review

### P0 risks

1. **Sybil-able tenant quorum (partially fixed in rev B).**
   - HMAC tenant pseudonyms protect privacy but do not prove independent users.
   - Rev B fix: shareable/global quorum now counts normalized trusted tenant identities instead of HMAC pseudonyms.
   - Remaining gap: production tenant authority / IdP-backed identity is not operated or externally proven.
   - Next fix: authenticate tenant/org/user identities or operator-verified signer anchors in production.

2. **Verified outcome was self-attested (shareable export fixed in rev B).**
   - Rev A code required `verification_command` when `verified=True`, but did not bind to executed command output, exit code, transcript hash, or independent verifier signature.
   - Rev B fix: shareable/exported receipts require exit code, verification output digest, and trusted tenant identity.
   - Remaining gap: production verifier signatures, environment hashes, and anomaly checks are still future work.

3. **Runtime split-brain blocks production claims.**
   - Source/release is `3.3.15`; loaded runtime reports `3.3.14`.
   - Fix: readiness gates must fail production-served claims when runtime fingerprint does not match exact released source/package.

4. **No real external value evidence.**
   - Without first-10 rows, any impact claim is speculative.
   - Fix: consented external rows with install/usefulness/measured lift.

### P1 risks

1. **Local registry sync trusts local receipt files more than remote signed sync (default fail-closed in rev B).**
   - `sync_signed_registry_to_store()` is strong.
   - Rev B fix: `sync_registry_to_store()` now treats local filesystem registries as staging and skips unsigned `global` / `global_candidate` atoms by default.
   - Explicit operator override remains available for dev/manual staging: `allow_unsigned_global_candidates=True`.

2. **MCP collective retrieval returned raw match JSON (fixed in rev B).**
   - The standalone atom formatter has an explicit untrusted-advice header.
   - Rev B fix: `borg_collective_retrieve()` now returns a sanitized advisory projection and omits raw `atom` JSON from MCP callers.

3. **Privacy/prompt-injection scanners need adversarial expansion.**
   - Existing scanner gates are good, but should be fuzzed against modern token formats, obfuscation, homoglyphs, spaced text, encoded payloads, and secret-like dict keys.

4. **Sharing mode needs central enforcement.**
   - Docs say local-only should not leak.
   - Export/publish/promote paths need one central policy gate so local atoms cannot leave via an alternate path.

5. **Hosted-registry ops are not yet proven.**
   - Need uptime/SLO monitoring, key rotation, backup/restore, incident response, transparency/audit log, revocation drills, and abuse triage.

### P2 risks

- Result enumeration via broad LIKE queries should be constrained.
- Local DB file permissions should be forced to `0600` even if parent dir is `0700`.
- Dashboard/analytics/cluster counts need a single reconciled provenance model.
- Contribution metrics need anti-gaming caps on minutes/tokens/dead-ends saved.

## Impact model

### Formula

System-wide absolute success lift is approximately:

```text
net lift = task coverage × useful-hit precision × lift when useful
```

Where:

- **task coverage** = fraction of tasks where Borg has relevant guidance;
- **useful-hit precision** = fraction of retrieved guidance that is actually applicable and safe;
- **lift when useful** = extra pass probability when applicable memory is shown.

### Scenarios

- **Skeptical global:** `coverage=10%`, `precision=35%`, `lift_when_useful=10%`
  - net absolute lift: `0.35pp`
  - extra successes per 500 tasks: `1.7`

- **Base global:** `coverage=20%`, `precision=60%`, `lift_when_useful=20%`
  - net absolute lift: `2.4pp`
  - extra successes per 500 tasks: `12.0`

- **Optimistic global:** `coverage=30%`, `precision=80%`, `lift_when_useful=34%`
  - net absolute lift: `8.16pp`
  - extra successes per 500 tasks: `40.8`

- **Focused hard-domain:** `coverage=60%`, `precision=80%`, `lift_when_useful=34%`
  - net absolute lift: `16.32pp`
  - extra successes per 500 hard tasks: `81.6`

### Why the upside is real

External benchmark context supports a navigation-memory thesis:

- SWE-bench Verified has frontier agents around the mid/high-70% resolved range, meaning there is still a large failure tail.
- SWE-EVO reports best-model performance around 25% on long-horizon release-sized tasks, where navigation, file localization, and accumulated repo knowledge matter more.
- Borg's prior internal pilot was directionally promising: 3 treatment-favoring discordant pairs and 0 control-favoring pairs. But exact one-sided McNemar p-value was `0.125`, not significant.

The plausible high-value wedge is not generic “reasoning traces.” It is **navigation and failure-memory transfer**:

- where to look first;
- which dead ends to avoid;
- which file/method/pattern mattered last time;
- which apparent fix was harmful;
- what verification command proved the fix.

### Why the impact is not proven

- Prior pilot is underpowered.
- First-10 external rows are empty.
- Current default atom/outcome stores are empty.
- Current dashboard metrics are not reconciled to row-level truth.
- Treatment usage/influence is not yet measured: calling Borg is not the same as the agent using Borg guidance.

### Statistical guardrails

Exact McNemar check:

- 3 all-treatment-favoring discordant pairs: one-sided p=`0.125`.
- Need at least 5 all-treatment-favoring discordant pairs for one-sided p<0.05.
- Need at least 6 all-treatment-favoring discordant pairs for stricter two-sided p<0.05.

Power intuition from exact calculations:

- With 20 discordant pairs and true treatment-favor probability 0.80, power is about `0.804`.
- With 30 discordant pairs and true treatment-favor probability 0.75, power is about `0.894`.
- With 60 discordant pairs and true treatment-favor probability 0.70, power is about `0.937`.

So the next serious impact test needs enough tasks/runs to generate at least 20-30 discordant pairs, not just 10 demos.

## Experiment that would actually prove impact

### Arms

- **C0:** no Borg.
- **C0.5:** Borg prompt/tool scaffold, fixed boilerplate/no-result response.
- **C1:** Borg installed, empty DB.
- **C2:** Borg installed, seeded with validated collective memory.
- **C3 optional:** same as C2, but memory comes through remote signed federated registry.

This separates:

- scaffold effect;
- tool availability effect;
- actual knowledge effect;
- remote federation overhead/failure effect.

### Design

- Pre-register exact Borg version, model IDs, task set, budget, stopping rules, exclusions, and claim language.
- Use real tasks: SWE-bench Verified for isolated fixes, SWE-EVO or equivalent for long-horizon tasks.
- Freeze held-out task IDs and source commits.
- Use within-task paired/factorial design with randomized order.
- Equal token/time/tool budget across arms.
- Fresh containers/workspaces.
- No hints/gold patches in prompts or memory.
- Disjoint training/eval tasks for seeded memory.
- Measure treatment influence: did the agent reference/use the memory?

### Primary endpoint

Verified pass/fail on deterministic task tests.

### Secondary endpoints

- wall-clock time;
- tokens;
- tool calls;
- cost per pass;
- dead ends avoided;
- harmful guidance rate;
- no-confident-match correctness;
- privacy/security incidents;
- outcome receipt coverage;
- time from intervention to verified receipt;
- transfer success from Agent A's learning to Agent B's result.

### Statistics

- Binary pass/fail: exact McNemar for paired two-arm claims, or mixed-effects logistic regression / GEE for multi-arm repeated runs.
- Continuous metrics: Wilcoxon signed-rank or mixed models.
- Multiple comparisons: Holm correction.
- Report absolute risk difference, odds ratio, confidence intervals, and pass-per-dollar.
- Do not claim impact if C2 only beats C0 but not C1; that would show scaffold/tool effect, not memory effect.

### Product gates

- **First-10 usability gate:** 10 consented real users, at least 8 installs, at least 6 useful rescue moments, 0 critical incidents.
- **Collective loop gate:** at least 60% of interventions receive verified outcome receipts within 24h; at least 3 independent trusted tenants per promoted atom; negative evidence retained.
- **Impact gate:** C2 beats C1 by a pre-set margin with CI excluding zero; harmful-guidance rate below threshold.
- **100-user gate:** row-derived adoption + retention + incident metrics, not synthetic dashboards.

## Improvement plan

### P0 — make current claims true in production

1. **Runtime alignment gate.**
   - Block served-MCP/federated readiness claims until runtime fingerprint matches exact release version and source hash.
   - Current state: loaded `3.3.14`, source `3.3.15`.

2. **External evidence capture.**
   - Start first-10 external cohort with consented rows.
   - Record install success, rescue usefulness, verification result, measured minutes/tokens/dead-ends, privacy incidents.

3. **Automatic outcome closure.**
   - Every `rescue`, `error_lookup`, `observe`, CLI, and MCP guidance path should emit a stable `intervention_id`.
   - Verification commands should offer one-click / one-command outcome receipt recording.

4. **Real tenant independence.**
   - Replace local HMAC-only tenant quorum with trusted tenant signer anchors, org/user verification, or operator-reviewed first-10 identity.

5. **Verification-bound receipts.**
   - Include command hash, exit code, stdout/stderr hash, environment hash, timestamp, and verifier signer ID.

### P1 — harden federation

1. **Signed manifest everywhere.**
   - Treat legacy local registry sync as dev-only or require the same signed manifest/receipt validation as remote sync.

2. **Transparency log.**
   - Add Rekor-like append-only manifest/receipt anchoring or at least an append-only transparency ledger with consistency proofs.

3. **TUF-like key model.**
   - Add root/targets/snapshot/timestamp role separation or equivalent.
   - Add key rotation drills and threshold signing for production registry metadata.

4. **Revocation operations.**
   - Track live revocation convergence SLO across clients.
   - Drill poisoned-atom recall and measure time-to-suppression.

5. **MCP retrieval firewall.**
   - Make `borg_collective_retrieve()` return formatted untrusted-advisory output by default, not raw payload JSON.

6. **Scanner expansion.**
   - Add frozen tests for modern secrets (`github_pat_`, `sk-proj-`, AWS secret keys), dict-key PII, obfuscated injection, homoglyphs, and encoded payloads.

### P2 — increase useful coverage

1. **Seed the atom store.**
   - Convert known good traces and failure memories into reviewed atoms.
   - Prioritize high-frequency, high-cost error classes.

2. **Fold traces/failure memory into unified retrieval.**
   - Current unified retrieval focuses atom/outcome lane.
   - Add packs, traces, failure memory, recency, project context, and negative evidence behind one scoring contract.

3. **Navigation memory.**
   - Capture file/method localization and dead-end paths from real fixes.
   - Navigation is likely the highest-value Borg memory class for hard codebase tasks.

4. **Telemetry reconciliation.**
   - Dashboard, analytics, clusters, atom DB, trace DB, and first-10 scoreboard must reconcile to provenance-labeled rows.
   - Synthetic/internal rows must never appear as external adoption.

5. **UX.**
   - Make contribution nearly automatic: after verification, ask for one-tap receipt confirmation.
   - Show users concrete saved-dead-end examples, not protocol jargon.

## Alternative views deliberately considered

### “Protocol GO means federated learning is working.”

Rejected. Protocol GO proves safe movement of signed learning atoms. It does not prove populated memory, useful guidance, real external lift, or runtime cutover.

### “No external users means Borg is worthless.”

Rejected. The mechanism is real and valuable infrastructure. The correct verdict is not “fake”; it is “mechanism green, impact unproven.”

### “Dashboard says millions of outcomes, so it is working.”

Rejected. The dashboard conflicts with analytics, clusters, atom store, collective retrieval, and first-10 rows. Until reconciled, it is not impact evidence.

### “Signatures prove truth.”

Rejected. Signatures prove origin/integrity. They do not prove that advice helped. That requires verified outcome receipts and independent tenant trust.

### “The next fix is more docs.”

Rejected. Docs are now mainly claim-boundary and runbook tools. The next real fix is data-plane closure: outcomes, identity, verification evidence, populated atoms, and external rows.

## Final reflection from scratch

Starting over from first principles: a federated learning system should let one user's verified experience safely improve another user's future outcome. Borg currently proves the safety skeleton: signed atoms can move, clients can reject bad metadata, tombstones work, and local receipts can become candidate memory. But the actual production value loop requires three additional facts: there must be useful memory, it must come from independent verified users, and downstream users must measurably do better because of it.

The audit found the first piece partially true, and the second/third not yet true. The cleanest honest sentence is:

> Borg's federated learning protocol works as a tested primitive; Borg's federated learning product is not yet working in the market because the live memory/outcome/evidence loop is empty and runtime-cutover/external-user proof is incomplete.

That is a strong position because it is falsifiable. The path to change the verdict is also clear: align runtime, collect real receipts, enforce tenant identity, seed/retrieve useful atoms, and run a controlled C0/C1/C2 experiment that proves seeded collective memory beats the empty Borg scaffold.

## Final channel verdicts

- **Local signed protocol primitives:** GO.
- **Remote signed registry gate:** GO in test harness.
- **Internal outcome/receipt/quorum/retrieval primitives:** GO in test harness.
- **Current default live collective retrieval:** NO-GO / empty.
- **Served MCP runtime version alignment:** NO-GO until runtime fingerprint matches release.
- **Production hosted federation ops:** NO-GO / not proven.
- **First-10 external-user lift:** NO-GO / zero rows.
- **100-user rollout:** NO-GO.
- **Measured agent success impact:** NO-GO until controlled experiment passes.

## Raw command/result index

- `date -u +%Y%m%d-%H%M`: `20260528-1931`
- `git status --short`: `M eval/pypi_fresh_install_snapshot.json`
- `git rev-parse HEAD`: `519ebb1a2f059f7b4e11ed897aeb7a1340d85b83`
- `eval/run_collective_intelligence_loop_gate.py`: pass / GO primitives.
- `eval/run_federated_learning_gate.py`: pass / GO protocol.
- `eval/run_federated_learning_optimality_audit.py`: protocol GO, product-impact NO-GO.
- focused pytest: `36 passed in 26.91s`.
- temp micro-suite: 3 interventions, 3 outcomes, promotion success, verified tenant count 3, retrieval score 0.86.
- current local stores: atom count 0, outcome receipt count 0.
- first-10 scoreboard: 0 real users / 0 installs / 0 useful rescues / 0 measured rows.
