# Borg outstanding work — eval-loop framing and production path

**Historical/internal — not current product documentation.** Operator planning artifact; current public truth remains in `README.md`, `PROJECT_STATUS.md`, `GO_NO_GO_DECISION.md`, `docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md`, and `docs/public/status.json`.

**Generated:** 2026-05-31 22:34 UTC  
**Repo inspected:** `/root/hermes-workspace/borg`  
**Canonical repo:** `https://github.com/borg-farther/Borg-Directory`  
**Current local branch/head:** `main` @ `a7f5e769016ac83f249d57fe8e36b34f020dda3b`  
**Current package/source version:** `agent-borg==3.3.15`  
**Current verdict:** **NO-GO** for controlled first-10, broad public self-serve, served/remote MCP launch, 100-user rollout, and measured external-lift claims.  
**Current cap:** `0` real users.

This artifact answers the operator question: **what Borg work is still outstanding after reviewing the recent chat history and current repo truth?** It also reframes the product direction around the cleanest public thesis:

> **Borg is the eval loop for agents.**  
> Not “memory.” Not “better prompts.”  
> Borg is quality control after generation: every bad answer becomes failure memory, then a regression case, then a pack/update candidate.

## 1. Evidence sources used

### 1.1 Recent chat archaeology

I mined the last 100 non-empty Telegram user/assistant messages from `/root/.hermes/state.db` read-only. The reviewed range was approximately `2026-05-30T20:11:48Z` through `2026-05-31T19:46:02Z`, then cross-checked against current files and live gates because compaction summaries can preserve stale intermediate truth.

Key recent-session signals:

- PR43 closed earlier proof-dashboard/watchdog/readiness hardening.
- PR44 closed security/runtime/governance gate hardening work.
- PR45 closed same-version PyPI drift fail-closed detection.
- PR46 closed the durable production-ready prioritized todo, stale-doc corrections, Smithery metadata correction, and public claim-guard tests.
- The repeated remaining blockers were consistent: package provenance, served runtime freshness, GitHub governance, first-10 evidence, and later real-user/lift proof.

### 1.2 Current live/repo checks

Read-only checks performed in this pass:

- `git status --short` → clean at the time of inspection before writing this artifact.
- `git rev-parse HEAD` → `a7f5e769016ac83f249d57fe8e36b34f020dda3b`.
- `pyproject.toml` and `borg/__init__.py` → `3.3.15`.
- PyPI JSON → latest `agent-borg==3.3.15`; wheel/sdist uploaded `2026-05-28T17:50:29Z` / `2026-05-28T17:50:31Z`.
- GitHub branch protection API → `Branch not protected` / HTTP 404 for `main` protection.
- Stored served runtime fingerprint → served `borg_version=3.3.14`, source `3.3.15`, `version_matches_source=false`, `reload_status=reload_or_patch_required`.
- Public and real-user rollout snapshots → max recommended users `0`, first-10 evidence `0/10`.
- Latest scheduled Self-service readiness watchdog run at current head failed: run `26722566535`, event `schedule`, failure in `Run ops readiness watchdog`.
- Local reproduction of that watchdog command failed because `eval/pypi_fresh_install_snapshot.json` was older than the 24-hour freshness limit.

## 2. What is already implemented / no longer the main open problem

### 2.1 Source-level hardening is substantial

Already implemented across recent PRs:

- untrusted pack ingestion/export hardening;
- generated rule prompt-injection fail-closed checks;
- safety scanning for V1 and V2 phase structures and rendered metadata fields;
- unsafe embedding-cache pickle removal/replacement with safe JSON cache format;
- HTTP MCP auth-before-body-parse, body-size bound, JSON-RPC schema validation, and narrower unauth read-only surface;
- served-runtime freshness gate;
- release-governance gate;
- same-version PyPI upload-time/source-time drift gate;
- docs claim guard for stale package/readiness claims;
- Smithery metadata correction to source-truth MCP tool count;
- proof dashboard/status/watchdog artifacts and tests around these boundaries.

### 2.2 The user-facing first-rescue path exists

Existing wedge components:

- `borg rescue` → ACTION / STOP / VERIFY packet;
- MCP `error_lookup` / `borg_rescue` / `borg_observe` paths;
- `borg rescue-eval` → rescue-packet eval taskset runner;
- `borg feedback-v3`, `borg_record_outcome`, `borg_record_failure`, `borg_recall`;
- `borg optimize-pack` → bounded local pack optimization candidate workflow;
- `borg atom` / `borg collective` → privacy-safe learning atom and outcome-ledger utilities;
- dashboards/status JSON that already track some value/evidence fields.

### 2.3 Some older E2E learning-loop gaps appear partly closed

`docs/E2E_LEARNING_LOOP_PRD.md` is historical and still lists several old P0/P1 learning-loop gaps. Current source appears to have closed or partly closed several of them:

- `BorgV3.search()` forwards `error_type` to classification.
- `BorgV3.search()` injects prior `FailureMemory.recall()` results into returned items when an error message is present.
- `ContextualSelector.feedback_signal_boost()` reads feedback signals.
- `BorgV3.record_outcome()` updates selector, feedback loop, failure memory on failure, and mutation A/B context when available.
- Trace maintenance hooks exist in current `BorgV3`.

Remaining risk: historical docs can still mislead product planning unless they are explicitly reconciled or marked superseded with current-source evidence.

## 3. Current P0 production blockers — in execution order

### P0.0 — scheduled watchdog is currently red because proof freshness expired

**Current status:** open, reversible, immediate.  
**Evidence:** latest scheduled Self-service readiness watchdog run `26722566535` failed at `a7f5e769016ac83f249d57fe8e36b34f020dda3b`; local reproduction of:

```bash
python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule
```

failed because `eval/pypi_fresh_install_snapshot.json` was ~26.9 hours old.

**Why this matters:** previous exact-head CI was green, but the latest scheduled watchdog is now red. Production readiness cannot cite “CI green” without qualifying which run and whether freshness gates have expired.

**Required work:**

1. Decide the intended policy for `pypi_fresh_install_snapshot` freshness while package proof is already red due same-version PyPI drift.
2. Either regenerate the stale snapshot as part of the recurring watchdog process, or adjust the watchdog policy so stale package-canary snapshots do not fail the scheduled ops gate during a pre-package-release red state.
3. Preserve fail-closed behavior: if package proof is being claimed green, stale PyPI canary must remain a hard failure.
4. Add/refresh regression tests for the pre-package-red freshness case.
5. Re-run scheduled-equivalent watchdog locally and verify latest GitHub scheduled/manual run passes or fails for only intentional reasons.

**Disproves closure if:** scheduled watchdog remains red for accidental stale-artifact reasons, or watchdog passes while stale package proof is presented as green.

### P0.1 — publish a new immutable PyPI version after explicit approval

**Current status:** blocked by required operator approval.  
**Why:** PyPI `3.3.15` artifacts were uploaded before current source hardening. PyPI is immutable, so `3.3.15` cannot be made current.

**Likely target:** `agent-borg==3.3.16`, but do not publish without exact approval naming package and version.

**Required work:**

1. Bump package/runtime version from `3.3.15` to approved new version.
2. Update changelog/docs only where tied to the new release truth.
3. Build clean wheel/sdist from clean release commit/tag.
4. Run `twine check`, manifest checks, local smoke, and package metadata checks.
5. Publish only after explicit approval such as: `approve agent-borg==3.3.16 to production PyPI`.
6. Poll PyPI until new artifacts exist.
7. Verify PyPI upload time is after the claimed source commit.
8. Fresh-install from non-repo cwd with `PYTHONPATH=` cleared.
9. Verify CLI, stdio MCP, generated rules, OpenClaw conversion, import API, rescue/search/doctor smoke.
10. Regenerate gates/status/dashboard from the new package truth.

**Disproves package readiness if:** same version string matches but upload predates source; fresh install imports checkout; `borg-mcp` reports wrong version; generated rules/OpenClaw fail from installed package; docs still mention stale 3.3.15 truths as current.

### P0.2 — cut over served runtime under operator supervision

**Current status:** blocked by operator-supervised runtime action.  
**Evidence:** served MCP path still reports `borg_version=3.3.14` while source/package is `3.3.15`; `version_matches_source=false`.

**Required work:**

1. Inventory each served channel: Hermes/gateway MCP, any HTTP/remote MCP, local stdio path, marketplace draft surfaces.
2. Operator reloads/cuts over served runtime after package/source are current.
3. Capture before/after runtime fingerprints through each exact served channel.
4. Verify loaded version, source version, code hashes, schema hash, PID/start time, `BORG_HOME`, and behavior canaries.
5. Ensure stale runtime reports upgrade-required state if mismatch recurs.

**Approval boundary:** agents must not restart, kill, signal, or reload Hermes/gateway processes.

**Disproves served readiness if:** any served process reports stale version/path/hash; runtime can only be fingerprinted in a source subprocess; behavior canaries pass only outside the served channel.

### P0.3 — enforce GitHub release governance on `main`

**Current status:** blocked by GitHub admin/maintainer approval.  
**Evidence:** branch protection API returns `Branch not protected`; required checks are empty/off.

**Required work:**

1. Enable branch protection or ruleset for `main`.
2. Require PRs before merge.
3. Require CI, Borg Security Gates, Self-service readiness watchdog, and Account Reference Firewall.
4. Require CODEOWNERS review for readiness/security/release surfaces.
5. Require conversation resolution and stale-approval dismissal where supported.
6. Re-run release-governance gate against live GitHub API.

**Disproves governance readiness if:** `protected=false`, required contexts are empty, CODEOWNERS exists but review is not enforced, or direct pushes can bypass release/security gates.

### P0.4 — regenerate exact-head proof artifacts after package/runtime/governance changes

**Current status:** open.  
**Evidence:** some committed artifacts still carry `bd68c957...+dirty` provenance while current HEAD is `a7f5e769...`. This may be tolerated as honest ancestor+dirty provenance, but it is not ideal for final production proof.

**Required work:**

1. Regenerate public self-serve gate, real-user rollout gate, ops watchdog, proof dashboard, public status/value/impact, and inventory board after the release/cutover/governance changes.
2. Ensure source revision/provenance is exact-head or intentionally marked dirty with a documented reason.
3. Run claim guards and dashboard lint.
4. Verify latest GitHub Actions on exact head, including any scheduled/watchdog run relevant to launch claims.

**Disproves proof readiness if:** public artifacts cite stale source revision, status JSON contradicts gates, or scheduled freshness gates have expired.

### P0.5 — run controlled first-10 only after package/runtime/governance/ops gates pass

**Current status:** evidence absent; do not start yet.  
**Evidence:** first-10 rows are zero: verified users `0/10`, installs `0/8`, useful rescues `0/6`, critical incidents `0`.

**Required work:**

1. Invite exactly 10 consented external users only after P0.0–P0.4 pass.
2. Use the same approved package version and documented first-user smoke path.
3. Capture install success/failure, time to first useful rescue, useful ACTION/STOP/VERIFY, no-match behavior, bad guidance, privacy/security incidents, maintainer handholding, and measured savings fields.
4. Count internal/synthetic/duplicate/unconsented/maintainer-handheld rows as invalid.
5. Preserve negative evidence.

**Pass thresholds:**

- verified external users >= 10;
- real users >= 10;
- install successes >= 8;
- useful rescue moments >= 6;
- critical privacy/security incidents == 0.

**Disproves first-10 readiness if:** useful rescues < 6/10, installs < 8/10, any critical privacy/security incident occurs, or invalid rows are counted as real users.

## 4. P1 product work — make the eval-loop framing real

These are not prerequisites for fixing the immediate launch gates, but they are the product wedge that turns Borg from “failure memory” into the agent QA/eval loop.

### P1.1 — add first-class `borg eval init` and `borg eval run`

**Current status:** missing as first-class CLI. Existing pieces are scattered:

- `borg rescue-eval <taskset.json>` exists;
- benchmark package exists under `borg/benchmarks/`;
- eval tasksets exist;
- dashboards can consume outputs;
- but there is no obvious `borg eval init` / `borg eval run` happy path.

**Recommended wedge:**

```bash
borg eval init ./borg-evals
borg eval add-bad-answer --input bad_answer.md --expected-stop "..." --expected-verify "..."
borg eval run ./borg-evals --target rescue --json
borg eval promote-failure ./borg-evals/cases/<id>.json --pack systematic-debugging
```

**Minimal implementation order:**

1. Define a small eval-case schema:
   - `input`;
   - expected `ACTION` qualities;
   - forbidden `STOP`/bad-answer patterns;
   - required `VERIFY` command or verification shape;
   - expected confidence/no-match behavior;
   - privacy classification.
2. `borg eval init` scaffolds `cases/`, `taskset.json`, and README.
3. `borg eval run` wraps `rescue_packet_eval` and emits stable JSON + markdown.
4. `borg eval add-bad-answer` converts a bad answer into a regression case.
5. `borg eval promote-failure` optionally records failure memory and creates a bounded pack-update candidate.
6. Add tests that a bad rescue becomes a failing eval before the pack update and passes after update.

**Disproves product wedge readiness if:** users still need to understand internal `eval/tasksets/*`, or a bad answer cannot become a regression case with one obvious command.

### P1.2 — make `rescue` / `observe` the runtime QA layer

**Current status:** partly present. Borg already returns `ACTION / STOP / VERIFY`, explicit confidence, and no-match behavior. It does not yet present itself as the runtime QA envelope around arbitrary agent answers.

**Required product behavior:**

- `borg observe` / MCP `borg_observe` should be positioned as pre-answer QA: “before finalizing a technical answer, check if known failure patterns apply.”
- `borg rescue` should be positioned as post-failure rescue: “when the agent hits a concrete error, produce the testable correction packet.”
- The user-visible receipt should say what was caught:
  - known dead end avoided;
  - unsafe guidance blocked;
  - no confident match, so no forced advice;
  - verification required before value is counted.

**Disproves readiness if:** Borg claims it helped before VERIFY/outcome receipt, or injects weak/unrelated guidance for meta/product/readiness prompts.

### P1.3 — connect bad answer → failure memory → regression case → pack update

**Current status:** components exist, but no single closed-loop UX.

Existing pieces:

- `borg_record_failure` and `borg_recall`;
- `borg_record_outcome` with verified/helpful fields;
- `rescue_packet_eval`;
- `optimize-pack` local candidate workflow;
- learning atoms and collective ledger.

Missing loop:

1. capture bad answer / bad guidance;
2. redact and classify it;
3. write failure memory;
4. create regression eval case;
5. run eval against current rescue/observe behavior;
6. create bounded pack update candidate;
7. rerun eval;
8. record verified outcome;
9. update dashboard trend.

**Recommended first command surface:**

```bash
borg qa capture --bad-answer bad.md --task task.md --expected "should say NO_CONFIDENT_MATCH"
borg eval run .borg/evals --changed-only
borg optimize-pack systematic-debugging --from-failing-eval .borg/evals/cases/<id>.json --local-only
```

This can be implemented later as `borg eval add-bad-answer` if `borg qa` feels too large.

**Disproves loop readiness if:** a bad answer only becomes an anecdote or a memory record, not a regression that can fail/passing-gate future behavior.

### P1.4 — dashboard: caught slop, avoided dead ends, quality trend

**Current status:** partially instrumented, mostly unmeasured.

Existing dashboard data has measured-savings fields, but current values are zero. Session history also shows the system was deliberately changed not to claim “Borg helped” or “dead ends avoided” until VERIFY/outcome receipt.

Required dashboard metrics:

- `caught_slop_count`: bad guidance blocked by confidence/no-match/claim guard/rescue eval;
- `dead_ends_avoided_verified`: STOP item surfaced and user verified it avoided a failed path;
- `quality_trend`: rescue eval pass rate and verified helpfulness over time;
- `no_confident_match_rate`: must not be treated as failure if it prevented hallucinated advice;
- `pack_update_regressions_added`: count of bad answers converted into eval cases;
- `pack_update_regressions_fixed`: count passing after pack update;
- negative guidance / harmful guidance count.

**Disproves dashboard readiness if:** counters are aggregate-only, synthetic-only, or increment before verification.

### P1.5 — reconcile historical learning-loop docs with current source

**Current status:** historical docs contain stale gap statements that are partly no longer true.

Required work:

1. Add a current-source reconciliation section to `docs/E2E_LEARNING_LOOP_PRD.md`.
2. Mark which historical gaps are closed, partly closed, or still open.
3. Link to tests proving each closure.
4. Move still-open gaps into this eval-loop roadmap.

**Disproves docs readiness if:** future agents use stale historical gap lists as current truth.

## 5. P1/P2 distribution and scale work

### P1 — remote MCP / marketplace distribution

Current status: Smithery remains draft/local. That is correct.

Required before remote/marketplace claims:

- remote-safe tool allowlist;
- auth/rate limits;
- audit redaction;
- per-tenant storage isolation;
- request/body limits and incident logging;
- endpoint fingerprint and tools/list policy proof;
- MCP host compatibility tests.

### P1 — cross-platform first-user matrix

Required before broad public self-serve:

- Linux/macOS/Windows;
- Python 3.10/3.11/3.12;
- pipx and isolated pip;
- major claimed MCP hosts;
- wrong-package confusion guard against BorgBackup;
- fresh install with no checkout leakage.

### P1 — federation / recursive learning productionization

Current status: protocol/internal/manual proof only.

Required before production federation claims:

- hosted registry monitoring;
- backups and restore drill;
- key rotation and key-compromise drill;
- signed manifests and replay/rollback rejection;
- abuse/quarantine workflow;
- revocation/tombstone propagation proof;
- independent tenant quorum promotion.

### P2 — measured external-lift experiment

Required before external lift claims:

- predeclared comparison: no Borg, empty Borg, seeded Borg, optionally served collective;
- completion rate, time, token use, dead ends avoided, negative guidance, no-match outcomes;
- row-derived external evidence only;
- include failures and harmful guidance.

## 6. Recommended next execution order

### Immediate reversible repo work

1. Fix or refresh the scheduled watchdog freshness red state around `pypi_fresh_install_snapshot`.
2. Re-run scheduled-equivalent watchdog locally.
3. Update status/proof artifacts if regenerated.
4. Add tests for the exact freshness policy.
5. Commit/PR/merge the reversible fix and verify latest scheduled/manual GitHub watchdog is green or intentionally red for a launch-blocking reason.

### Approval-bound release work

6. Get exact approval for production PyPI target/version.
7. Publish new immutable package version and run fresh package canaries.
8. Operator cuts over served runtime and captures live fingerprints.
9. Apply approved GitHub branch protection/ruleset.
10. Regenerate exact-head proof artifacts and verify all source/package/runtime/governance/ops gates.

### Controlled evidence work

11. Start controlled first-10 only after the above gates are green.
12. Collect row-derived evidence and negative outcomes.
13. If first-10 passes, move to 25 → 50 → 100 with support/privacy gates.

### Product wedge work

14. Add `borg eval init` / `borg eval run`.
15. Add bad-answer-to-regression workflow.
16. Connect regression failures to bounded pack-update candidates.
17. Update dashboard to show verified caught slop, avoided dead ends, quality trend, and eval regressions.

## 7. Final synthesis

The outstanding work is now mostly **not** “write more random code.” Borg already has a lot of real source hardening and proof machinery. The biggest gap is that production truth is split across four systems that must all agree:

1. package provenance;
2. served runtime;
3. release governance;
4. real-user evidence.

The clean product strategy is to make that same discipline visible to users:

- Borg checks agent output quality before confidence turns into damage.
- Borg refuses weak matches instead of pretending.
- Borg turns every bad answer into a regression.
- Borg turns repeated regressions into pack updates.
- Borg only counts value after VERIFY/outcome receipt.

That is the strongest public framing: **Borg is the eval loop for agents.**
