# Borg production-ready prioritized todo — current truth after PR45

**Historical/internal — not current product documentation.** This artifact preserved the 2026-05-31 post-PR45 state. Current public truth for the 2026-06-02 `agent-borg==3.3.16` release branch lives in `README.md`, `docs/READINESS.md`, `docs/CHANNELS_AND_INSTALL_METHODS.md`, generated go/no-go reports, and the final PR/release proof.

**Date:** 2026-05-31  
**Canonical repo:** `https://github.com/borg-farther/Borg-Directory`  
**Current source head verified:** `bd68c95733f545cc7a3cfd2700fb98734a4d3e91`  
**Source version at generation:** `agent-borg==3.3.15` (superseded; current release branch targets `agent-borg==3.3.16`)
**Current rollout verdict:** **NO-GO for controlled first-10, public self-serve, served/remote MCP, 100-user rollout, and measured external lift**  
**Current cap:** `0` real users

This is the durable production-readiness todo for Borg after the latest hardening work. It intentionally separates source health, package provenance, served runtime, release governance, ops, external-user evidence, remote/marketplace distribution, federation, and measured value. A green result in one lane cannot make another lane green.

## 1. Task outline and decomposition

The task is not “write a nicer roadmap.” The task is to make Borg production-ready without letting claims outrun proof.

Subtasks:

1. **Establish current truth** — repo head, PyPI latest, live served runtime, GitHub governance, first-10 evidence, CI, and generated proof artifacts.
2. **Challenge the obvious blockers** — verify whether PyPI drift, served runtime, branch protection, and first-10 evidence are necessary/sufficient blockers, not just convenient narratives.
3. **Find hidden blockers** — stale generated snapshots, stale public docs, stale Smithery metadata, wrong local shell resolution, remote MCP policy gaps, and federation/learning overclaims.
4. **Separate fix classes**:
   - reversible repo fixes: docs, gates, snapshots, tests, dashboards;
   - approval-bound irreversible fixes: production PyPI publish, GitHub branch protection/rulesets, served runtime reload/cutover, real-user invites;
   - evidence-only blockers: first-10 rows, measured lift, production federation operations.
5. **Define proof gates for each stage** — exact commands, expected pass/fail semantics, and disproof conditions.
6. **Keep public wording fail-closed** — every current public surface must say package proof is stale and user cap is 0 until gates pass.

## 2. Evidence ledger

### 2.1 Source and CI

- `git status --short --branch` showed clean `main` before this todo work began.
- `git rev-parse HEAD` and `git rev-parse origin/main` both verified `bd68c95733f545cc7a3cfd2700fb98734a4d3e91`.
- GitHub Actions for the exact head were green: CI, Borg Security Gates, Self-service readiness watchdog, Account Reference Firewall.
- There were no open PRs at the start of this pass.

### 2.2 PyPI/package provenance

- PyPI latest from `https://pypi.org/pypi/agent-borg/json`: `3.3.15`.
- PyPI release files:
  - wheel upload: `2026-05-28T17:50:29.231332Z`
  - sdist upload: `2026-05-28T17:50:31.032755Z`
- Current source commit time: `2026-05-31T14:32:23Z`.
- Mathematical drift: the newest PyPI artifact predates the current source commit by `2 days, 20:41:51.967245` (`247311.967245` seconds).
- Therefore `latest_version == source_version` is not enough; the artifact cannot contain current hardening.

### 2.3 Served runtime

Live `borg_runtime_fingerprint` through the served Borg MCP path reported:

- served `borg_version`: `3.3.14`
- source version: `3.3.15`
- `version_matches_source`: `false`
- `reload_status`: `reload_or_patch_required`
- behavior canaries: pass, but on stale loaded code.

Conclusion: the live served runtime is functional enough to fingerprint itself, but it is not current and cannot authorize served-runtime readiness.

### 2.4 Release governance

Live GitHub branch data for `main` reported:

- `protected=false`
- required status checks: empty / enforcement off
- `.github/CODEOWNERS` exists, but is not enforced by branch protection.

Conclusion: CODEOWNERS text alone is not governance. Enforcement must be live in GitHub branch protection/rulesets.

### 2.5 External-user evidence

Current row-derived first-10 evidence remains zero:

- verified external users: `0/10`
- real users: `0/10`
- install successes: `0/8`
- useful rescues: `0/6`
- critical privacy/security incidents: `0`
- measured savings rows: `0`

Conclusion: synthetic/load/local proof cannot substitute for external rows.

### 2.6 Independent adversarial findings incorporated in this update

Three independent review lanes agreed on the P0 blockers and found extra repo-fixable drift:

- stale generated proof artifacts after PR45;
- stale `docs/CHANNELS_AND_INSTALL_METHODS.md` wording that still implied package proof green;
- stale Smithery metadata/tool count (`24`) while source exposes `27` MCP tools;
- older docs/snapshots that can confuse current-state readers if not clearly treated as historical;
- local shell split-brain risk (`borg` on operator PATH can resolve to old/non-source runtime) even though fresh PyPI canary is isolated.

The repo-fixable parts are included in this follow-up: current generated snapshots are refreshed, channel docs are corrected, Smithery tool count is derived from source reality, and tests now guard these claims.

## 3. Prioritized todo to make Borg production-ready

### P0. Keep launch frozen until package, runtime, governance, and evidence are green

**Current status:** active blocker.  
**Current cap:** `0` real users.

Required state before lifting cap above 0:

- new immutable PyPI version current for source;
- fresh PyPI install + stdio MCP + generated rules + OpenClaw + import API canaries pass;
- served runtime fingerprint matches source/package;
- branch protection/rulesets enforce required checks and CODEOWNERS review;
- ops/watchdog/proof dashboard are green for current artifacts;
- first-10 external evidence process is ready and consent-safe.

Alternative view considered: “Could first-10 run using only local stdio and ignore served runtime?”  
Rejected for current production standard: a stale served Borg MCP path creates split-brain support, stale guidance risk, and false public confidence. The current gates intentionally block controlled first-10 on stale served runtime and release governance.

Disproves readiness if any public doc/status/dashboard says controlled beta can start while package provenance, served runtime, release governance, or first-10 evidence is red.

### P0. Publish a new immutable package version after explicit approval

**Current status:** approval-bound irreversible work.  
**Why first:** PyPI immutability means `3.3.15` cannot be made current; the next real package proof must use a new version such as `3.3.16`.

Required work:

1. Bump version in package metadata and runtime version source.
2. Update public docs/status to the new version only after release proof is ready.
3. Build clean wheel/sdist from a clean release commit/tag.
4. Run `twine check` and package manifest checks.
5. Publish only after explicit exact target/version approval.
6. Poll PyPI JSON until the new version and release files appear.
7. Verify PyPI upload time is after the source commit being claimed.
8. Run fresh install from non-repo cwd with `PYTHONPATH=` cleared.
9. Verify CLI, doctor, rescue, search, generate, OpenClaw convert, Python import API, and stdio MCP JSON-RPC.
10. Regenerate public gates, proof dashboards, inventory, status/value/impact JSON, watchdog, and docs.
11. Commit regenerated artifacts through PR and verify exact-head CI on `main`.

Approval boundary:

- production PyPI upload requires explicit user/operator approval naming package and version;
- do not ask for or echo tokens;
- do not re-upload the same version.

Disproves package readiness if:

- PyPI latest equals source version but upload predates source;
- fresh install imports from checkout instead of site-packages;
- `borg-mcp` reports a mismatched `serverInfo.version`;
- generated rules/OpenClaw fails from installed package;
- docs or proof artifacts still mention stale version truths.

### P0. Cut over served runtime under operator supervision

**Current status:** approval-bound runtime work.  
**Why second:** package/source can be green while served MCP remains stale. Production users will judge the live channel, not the repository.

Required work:

1. Inventory served Borg channels: Hermes/gateway MCP, any HTTP/remote MCP, Docker/Smithery draft, local stdio path.
2. Operator reloads/cuts over served runtime after package is current.
3. Capture before/after `borg_runtime_fingerprint` through each exact served channel.
4. Confirm loaded version, source version, function hashes, schema hash, PID/start time, `BORG_HOME`, and behavior canaries.
5. Verify stale runtime refuses or clearly reports upgrade-required state if version mismatch recurs.

Approval boundary:

- agents must not restart, kill, signal, or reload Hermes/gateway processes;
- operator performs runtime cutover and rollback.

Disproves served readiness if:

- any served process reports stale version/path/hash;
- runtime cannot be fingerprinted through the actual channel;
- behavior canaries pass only in source subprocess but not served process;
- remote tools expose write/network side effects without policy/auth.

### P0. Enforce release governance on GitHub `main`

**Current status:** approval-bound GitHub admin work.

Required work:

1. Enable branch protection/ruleset for `main`.
2. Require PRs for protected branches.
3. Require these exact GitHub Actions check-run contexts (not broad workflow display names):
   - `test (3.10)`
   - `test (3.11)`
   - `test (3.12)`
   - `dependency-audit`
   - `policy-check`
   - `secret-scan`
   - `static-security`
   - `ops-readiness-watchdog`
   - `old-account-reference`
4. Require CODEOWNERS review for readiness/security/release surfaces. In the current user-owned repo, `.github/CODEOWNERS` must use the valid owner `@borg-farther`; `@borg-farther/maintainers` is invalid unless the repo is transferred to an organization with that visible write team.
5. Require strict status checks, at least one approving review, stale-review dismissal, last-push approval, admin enforcement, conversation resolution, no force pushes, and no branch deletion where GitHub policy supports it.
6. Define release tag/provenance expectation before PyPI publish.

Approval boundary:

- GitHub admin/maintainer approval required for branch-protection mutation;
- agents may produce exact settings and verify API state, but should not mutate settings unless explicitly authorized.

Disproves governance readiness if:

- `protected=false`;
- required contexts/checks are empty;
- CODEOWNERS exists but review is not required;
- direct pushes can bypass release/security gates.

### P0. Keep public docs, generated artifacts, and marketplace metadata synchronized

**Current status:** repo-fixable; this update closes known stale truth drift and adds tests.

Required work:

1. Current docs must say `agent-borg==3.3.15` is stale relative to current source.
2. Channel docs must not say package proof green until a new immutable version is published and canaried.
3. Smithery metadata must not hard-code stale MCP tool count; current source exposes `27` tools.
4. Public claim guard must include channel docs and Smithery metadata.
5. Generated snapshots/dashboards must be regenerated after gate changes and committed cleanly.

Disproves docs readiness if:

- any current public doc says the package path is green while PyPI drift exists;
- Smithery `mcpTools` differs from `len(borg.integrations.mcp_server.TOOLS)`;
- public status/dashboard JSON source revision is stale or dirty after final commit;
- archived/historical docs are presented as current readiness.

### P0. Run controlled first-10 only after release controls pass

**Current status:** evidence absent; do not start yet.

Required work after package/runtime/governance/ops gates pass:

1. Invite exactly 10 consented external users.
2. Use the same approved package version and first-user smoke path.
3. Capture install success/failure, time-to-first-rescue, useful ACTION/STOP/VERIFY, no-match behavior, bad guidance, privacy/security incidents, maintainer handholding, and optional measured savings fields.
4. Count internal/synthetic/duplicate/unconsented rows as invalid.
5. Preserve negative evidence instead of hiding it.

Pass criteria:

- verified external users >= 10;
- real users >= 10;
- install successes >= 8;
- useful rescue moments >= 6;
- critical privacy/security incidents == 0.

Disproves first-10 readiness if:

- useful rescues < 6/10;
- installs < 8/10;
- any critical privacy/security incident occurs;
- any row is internal, synthetic, duplicate, unconsented, or maintainer-handheld but counted as self-service.

### P1. Harden remote MCP and marketplace distribution separately

**Current status:** blocked downstream; Smithery remains draft/local stdio.

Required work before remote/marketplace claims:

1. Define remote-safe tool allowlist.
2. Decide whether unauth remote exposes `error_lookup` safely or remains disabled.
3. Add auth, rate limits, audit redaction, per-tenant storage isolation, request/body limits, and incident logging.
4. Verify remote endpoint fingerprint and `tools/list` policy.
5. Test MCP protocol compatibility across claimed hosts.

Disproves remote readiness if:

- remote endpoint cannot be fingerprinted;
- unauthenticated users can mutate state or trigger network/write tools;
- marketplace metadata implies official/verified/deployed status before served proof;
- listed transport lacks the first-user value path.

### P1. Prove cross-platform first-user matrix

**Current status:** not complete enough for public self-serve.

Required environments:

- Linux, macOS, Windows;
- Python 3.10, 3.11, 3.12;
- pipx and isolated pip;
- major MCP hosts where claimed.

Required checks per environment:

- `borg --version`;
- `borg-doctor --json`;
- `borg rescue "ModuleNotFoundError: No module named flask" --json`;
- `borg generate systematic-debugging --format all`;
- OpenClaw conversion;
- stdio MCP initialize/tools/list/`error_lookup`;
- wrong-package confusion guard against BorgBackup.

Disproves cross-platform readiness if any supported OS/host cannot install, resolve the right `borg`, or run the first-user rescue path without maintainer handholding.

### P1. Productionize federation/recursive learning only after first-10 proves value

**Current status:** protocol/internal/manual proof only.

Required work:

1. Hosted registry monitoring, backups, restore drill, key rotation, key compromise drill.
2. Signed manifests, append-only or transparency/audit story, replay/rollback rejection.
3. Abuse/quarantine workflow and revocation/tombstone propagation proof.
4. Independent tenant promotion/quorum proof.
5. Clean-client sync from empty state.

Disproves federation readiness if only local protocol tests exist or revoked/poisoned atoms can propagate.

### P1. Stage rollout 10 → 25 → 50 → 100 only with row-derived evidence

**Current status:** blocked until first-10 passes.

Required staging:

- 10-user pass first, then 25;
- 50 only after repeat-use/support metrics;
- 100 only after support loop and privacy/security gates survive prior stages.

Disproves 100-user readiness if first-10 has not passed, repeat use is absent, support queue is overloaded, or any privacy/security incident remains unresolved.

### P2. Earn measured external-lift claims with predeclared experiment design

**Current status:** no measured external lift.

Required work:

1. Pre-register comparison: no Borg, empty Borg, seeded Borg, optionally served collective path.
2. Measure completion rate, time, tokens, dead ends avoided, negative guidance, and no-match outcomes.
3. Include failures and negative evidence.
4. Publish only row-derived claims.

Disproves lift readiness if claims rely on synthetic gates, internal dogfood, anecdotes, pack counts, aggregate-only counters, or unconsented rows.

## 4. Triple-verification model used for this todo

Each P0 was checked from at least three angles:

- **PyPI drift:** PyPI JSON upload timestamps; public gate source-upload-alignment blocker; web/PyPI project page showing latest `3.3.15`; commit-time math showing a 247,311.967245-second lag.
- **Served runtime:** MCP `borg_runtime_fingerprint`; stored served-runtime snapshot; public/real-user gates that consume served-runtime blocker text.
- **Governance:** GitHub branch API; release-governance gate; CODEOWNERS file existence plus enforcement absence.
- **First-10:** first-10 contract; public gate derived counts; status/value/impact JSON showing zero measured rows.
- **Docs/marketplace drift:** adversarial subagent review; direct file inspection; regression tests and claim guard coverage.

## 5. Assumptions deliberately challenged

1. **Assumption: version match means package current.** Rejected. Upload timestamp predates source by almost three days.
2. **Assumption: green CI means production ready.** Rejected. CI proves source checks, not PyPI freshness, served runtime, governance enforcement, or external users.
3. **Assumption: CODEOWNERS file means governance.** Rejected. Enforcement is off while `main.protected=false`.
4. **Assumption: served runtime behavior canary pass means runtime ready.** Rejected. Canary passed on stale `3.3.14`; freshness is a separate gate.
5. **Assumption: self-service ops pass means users can start.** Rejected. Ops can be ready while package/runtime/governance/evidence gates are red.
6. **Assumption: synthetic/load users count toward 100 users.** Rejected. Only consented external rows count.
7. **Assumption: Smithery draft is harmless.** Partially rejected. Draft status is correct, but stale tool count is still public-surface drift and is fixed by tests.
8. **Assumption: first-10 can start using only local stdio.** Rejected under current standard because split-brain served runtime and unprotected release controls create production-support ambiguity.

## 6. Final reflection from scratch

If starting from zero, the shortest honest path to production is not more feature work. Borg already has substantial source hardening, CI, gates, docs, and local/package canary machinery. The remaining blockers are mostly release discipline and real-world evidence:

1. publish a new immutable version from the current hardened source;
2. prove that exact version from a fresh install and stdio MCP;
3. cut over the served runtime and prove it by fingerprint;
4. enforce GitHub release governance;
5. invite only controlled first-10 users and capture row-derived outcomes;
6. then expand gradually.

Any path that skips one of those is not production readiness; it is either a local source proof, a packaging proof, a runtime proof, or a marketing claim. The current priority order is therefore correct because each stage removes a different class of false confidence before exposing real users.
