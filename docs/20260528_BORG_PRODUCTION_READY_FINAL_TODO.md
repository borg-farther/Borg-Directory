# Borg production-readiness final todo

**Generated:** 2026-05-28 10:08 UTC; updated 2026-05-30 for current package/readiness truth
**Repo:** `https://github.com/borg-farther/Borg-Directory`
**Current branch under review:** `feat/borg-rescue-skillopt-priorities`
**Current reviewed head:** PR #43 follow-up branch with additional local hardening under proof
**Remote `origin/main`:** not asserted by this branch-local todo
**Source target version:** `agent-borg==3.3.15`
**Published PyPI latest observed:** `agent-borg==3.3.15`
**Current public-package verdict:** package/fresh-install/canary proof is green for `agent-borg==3.3.15`, but controlled first-10 beta is NO-GO until served-runtime freshness, release governance, ops/watchdog, and proof-dashboard gates are all green; broad public self-serve remains NO-GO until row-derived first-10 external-user evidence passes.

## Executive verdict

Borg has **`agent-borg==3.3.15` package/local stdio proof green**, but controlled first-10 beta is currently **NO-GO** because release controls are red: the served runtime is stale and GitHub `main` is unprotected in the captured governance snapshot. Broad public self-serve remains **NO-GO** and the 100-real-user rollout remains **NO-GO**.

Earlier channel-completeness bugs were fixed and shipped in `agent-borg==3.3.15`. The current PR #43 follow-up work is about keeping that proof chain honest while hardening rescue truth-boundaries, local priming install safety, and public/readiness documentation.

The honest current state is:

- **Source/local 3.3.15 release candidate:** CONDITIONAL GO — local gate and regression proof must remain green for the final PR head.
- **GitHub `main`:** not claimed by this branch-local todo until merge/post-merge proof refresh runs.
- **Published PyPI:** package/local stdio proof green for `agent-borg==3.3.15`; controlled first-10 beta is blocked until served-runtime freshness, release governance, ops/watchdog, and proof dashboards are all green.
- **Local stdio MCP from current package/source:** CONDITIONAL GO while fresh-install/MCP/proof dashboards remain green for the exact version.
- **Generated rules / OpenClaw path:** shipped in `3.3.15`; keep covered by first-user gates.
- **Served/remote MCP production channel:** NO-GO until the actual served process is fingerprinted after operator-approved cutover.
- **Controlled first-10 beta:** NO-GO right now; tester cap is 0 until package/fresh-install/stdio MCP/generated-rules/OpenClaw/cold-start trust/self-service ops/watchdog/proof-dashboard, served-runtime freshness, and release-governance gates are all green.
- **Broad public self-serve:** NO-GO until first-10 row-derived external evidence passes.
- **100 real users:** NO-GO until first-10 evidence passes and the staged rollout gate raises the cap.
- **Measured external lift / “Google-tier” product impact:** NO-GO until real external outcomes and counterfactual evaluation exist.

## Method / verification sources

This todo is based on four independent evidence paths:

1. **Session-history archaeology**
   - Prior chats and closeout reports consistently split readiness into source/package, PyPI, stdio MCP, served runtime, first-10 evidence, public self-serve, 100-user, and measured-lift lanes.
   - Stable conclusion across sessions: public production remains blocked by row-derived external-user evidence; served/remote MCP remains blocked by runtime fingerprint/cutover proof.
   - New conclusion from the channel-completeness session: the pre-3.3.15 package was stale and broken for a documented secondary first-user channel (`borg generate systematic-debugging --format all --output ...`).

2. **Current repo / package truth inspection**
   - Branch: `feat/borg-rescue-skillopt-priorities`.
   - Branch-local PR proof is pending until final commit/push/CI for PR #43.
   - Working tree may contain follow-up hardening changes until this PR is committed.
   - `pyproject.toml` version: `3.3.15`.
   - `borg.__version__`: `3.3.15`.
   - PyPI latest: `3.3.15`.

3. **Current machine artifacts / reports**
   - `eval/first_user_release_gate_snapshot.json`: 3.3.15 local release gate passed; latest snapshot must be regenerated from the final PR head before claiming PR-ready.
   - Important historical/stale proof artifacts must not be treated as current proof unless regenerated for the final PR head:
     - `eval/pypi_fresh_install_snapshot.json`
     - `eval/real_user_rollout_gate_snapshot.json`
     - `eval/ops_readiness_watchdog_snapshot.json`
     - `eval/borg_proof_dashboard.json`
     - `eval/uat_scoreboard_snapshot.json`
     - `docs/BORG_PROOF_DASHBOARD.md`
     - `docs/public/status.json`
     - `eval/public_self_serve_launch_gate_snapshot.json`
     - `eval/gate_run_snapshot.json`
     - `eval/cold_start_trust_gate_snapshot.json`
     - `eval/federated_learning_gate_snapshot.json`
   - Current public status JSON should say the package path is blocked by same-version PyPI artifact drift when the published upload predates the claimed source revision. It may only say `NO-GO public self-serve; public package proof green, release controls blocked` after a new immutable package release is freshly canaried while served-runtime freshness or release governance is still red. It should only say `controlled first-10 beta CONDITIONAL GO while gates remain green` after package provenance, release controls, and ops gates are green; stale clean-source or stale-package revisions must fail the watchdog.

4. **Adversarial challenge review**
   - A green source gate can hide PyPI drift.
   - A green PyPI basic smoke can hide secondary channel failures like generated rules and OpenClaw export.
   - A green fresh-process stdio MCP canary does not prove a long-lived served MCP process.
   - A generated dashboard can become worse than useless if it embeds stale `source_revision`, stale package version, or stale controlled-beta state.
   - A final todo is not enough unless the repo has tests/gates that keep the todo and public surfaces honest.

## Final production-readiness todo list

### P0. Keep `agent-borg==3.3.15` channel-completeness release proof green

**Why:** The pre-3.3.15 package had a documented first-user export bug. The permanent fix is only useful if the current GitHub/PyPI/proof chain stays synchronized and fresh-install verified.

**Do:**

1. Resolve all current/stale pre-3.3.15 references in current public surfaces and machine snapshots.
   - Regenerate snapshots after every proof-affecting change where the value must come from real PyPI or a fresh local wheel.
   - Preserve historical references only inside clearly historical/internal docs.
2. Inspect the full diff for accidental bulk replacement damage.
3. Run focused tests for the changed surfaces:
   - `tests/cli/test_first_user_cli_contract.py`
   - `tests/core/test_generate.py::TestLoadPack`
   - `tests/packaging/test_public_presentation_contract.py`
   - relevant eval tests for first-user/PyPI/readiness/channel gates.
4. Build a clean 3.3.15 wheel/sdist from the branch.
5. Verify package contents include bundled seed data:
   - `borg/seeds_data/packs/systematic-debugging.workflow.yaml`
   - `borg/seeds_data/systematic-debugging.md`
6. Install the built wheel in a non-repo fresh venv with `PYTHONPATH=` cleared.
7. Run fresh wheel smokes:
   - `borg --version`
   - `borg rescue "ModuleNotFoundError: No module named yaml" --json`
   - `borg search systematic-debugging`
   - `borg try systematic-debugging`
   - `borg generate systematic-debugging --format all --output <tmpdir>`
   - `borg convert . --format openclaw --all --output <tmpdir>`
   - Python API `import borg; borg.check(...)`
   - stdio MCP initialize / tools/list / `borg_rescue`
8. Run full pytest and all readiness/proof gates that are expected to pass pre-release.
9. Commit and push the branch.
10. Open PR and verify GitHub Actions on the branch head.
11. Merge only after checks are green.
12. Verify post-merge `main` on the exact merge/follow-up SHA.
13. Publish production PyPI only after irreversible-release preflight passes and operator approval is explicit for `agent-borg==3.3.15`.
14. Poll PyPI JSON until latest is `3.3.15` and files are listed.
15. Run the PyPI fresh-install canary against actual PyPI `3.3.15`.
16. Regenerate proof dashboard/status/value/impact snapshots from the final clean source and PyPI state.
17. Commit post-release proof artifacts, push, and verify main-branch CI again.

**Hard gate:**

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/cli/test_first_user_cli_contract.py tests/core/test_generate.py::TestLoadPack tests/packaging/test_public_presentation_contract.py --tb=short
PYTHONDONTWRITEBYTECODE=1 python eval/run_first_user_release_gate.py
python -m build
python -m twine check dist/agent_borg-3.3.15*
# after explicit PyPI approval and upload:
PYTHONDONTWRITEBYTECODE=1 python eval/run_pypi_fresh_install_canary.py
PYTHONDONTWRITEBYTECODE=1 python scripts/build_borg_proof_dashboard.py
PYTHONDONTWRITEBYTECODE=1 python scripts/borg_proof_dashboard_lint.py
git diff --check HEAD~1..HEAD
git status --short
```

**Stop if:** PyPI latest is not a fresh immutable version built after the claimed source revision, generated rules fail from a clean install, OpenClaw files are missing, stdio MCP serverInfo/version is stale, proof dashboards reference a dirty/pre-release SHA, or public status says controlled-beta GO before the current-source PyPI canary is green.

---

### P0. Prove every served MCP/runtime channel is current

**Why:** Source/PyPI/local stdio passing does not prove a long-lived served MCP or gateway process is running the same code.

**Do:**

1. Inventory every channel that could serve Borg to real users:
   - local CLI / stdio MCP from PyPI;
   - Hermes/gateway-served MCP, if enabled;
   - remote Streamable HTTP MCP, if deployed;
   - Docker/Smithery/MCP registry draft paths;
   - any installed plugin/runtime mirror.
2. For each served process, run `borg_runtime_fingerprint` through that exact channel.
3. Record PID, path, package version, source version, function hashes, schema hash, BORG_HOME, and behavior canaries.
4. If stale, keep that channel out of beta traffic until an operator-approved reload/cutover completes.

**Hard gate:**

- served version equals source version equals PyPI latest;
- loaded module path is the expected installed/canonical path;
- schema/function hashes match the approved release;
- meta/readiness prompt returns fail-closed `NO_CONFIDENT_MATCH`;
- concrete error prompt still returns specific guidance;
- no raw session IDs/secrets in logs.

**Stop if:** the process is stale, un-fingerprintable, writing to unexpected BORG_HOME, missing hashes, or serving write/network tools remotely without explicit auth/policy.

---

### P0. Keep controlled first-10 beta tied to current package proof

**Why:** Earlier proof dashboards used stale package evidence. The 3.3.15 package path has earned the package-path verdict from PyPI and fresh-install proof, but that verdict must remain conditional on current proof.

**Do:**

1. Keep current public/user-facing status at controlled first-10 package beta GO-with-constraints while PyPI/latest, fresh-install, stdio MCP, generated-rules/OpenClaw, cold-start trust, self-service ops, watchdog, and public presentation tests remain green.
2. After any package/docs/proof change, rerun:
   - PyPI fresh-install canary;
   - stdio MCP canary;
   - cold-start trust gate;
   - self-service ops gate;
   - ops readiness watchdog;
   - public presentation/doc claim tests.
3. Only then keep controlled first-10 beta at conditional GO.

**Hard gate:**

- PyPI latest is `3.3.15`.
- Fresh install from PyPI uses site-packages, not checkout source.
- `borg generate systematic-debugging --format all` works from that install.
- OpenClaw conversion writes `SKILL.md`, `references/pack-index.md`, and `references/packs/systematic-debugging.md`.
- Stdio MCP serverInfo version is `3.3.15`.
- No stale pre-3.3.15 current-proof artifacts remain.

**Stop if:** controlled-beta language is reintroduced before package proof is current.

---

### P0. Run the first-10 external beta and fill real evidence rows

**Why:** This is the main blocker to broad production. Current verified external users are `0/10`.

**Do after a new immutable package version is published and current-source package proof is green:**

1. Recruit 10 consented external users.
2. Give each user the same published-package path:
   - `pipx install agent-borg==3.3.15` or isolated `pip install agent-borg==3.3.15`.
   - `borg --version` / `borg-doctor --json`.
   - `borg rescue "<real error>" --json`.
   - MCP stdio setup and `tools/list` / `borg_rescue` where relevant.
3. Capture a row in `eval/first_10_user_scoreboard.json` only after consent and evidence.
4. Record negative outcomes too: install failure, confusing guidance, `NO_CONFIDENT_MATCH`, privacy concerns, support handholding, and time lost.
5. Rerun evidence compiler, public gate, rollout gate, watchdog, dashboards.

**Hard gate:**

- `verified_external_users >= 10`.
- `real_users >= 10`.
- `install_successes >= 8`.
- `useful_rescue_moments >= 6`.
- `critical_privacy_security_failures == 0`.
- rows are unique, external, consented, redacted, and evidence-backed.

**Stop if:** any row is synthetic/internal/maintainer-only, duplicate, unconsented, secret-bearing, or requires maintainer handholding but is counted as self-service.

---

### P0. Keep public self-serve blocked until the row-derived gate flips

**Why:** The package can be good enough for controlled beta while still not being broad-public ready.

**Do:**

1. Keep public docs/status saying controlled first-10 package beta only while package proof stays green; never imply broad public self-serve until row-derived first-10 evidence passes.
2. Run public self-serve gate after every evidence update.
3. Let the gate, not vibes, decide when broad public self-serve is allowed.
4. Regenerate proof dashboard/status/value/impact JSON only after gate snapshots are current.

**Hard gate:**

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/first_10_evidence.py --input eval/first_10_user_scoreboard.json --write
PYTHONDONTWRITEBYTECODE=1 python eval/public_self_serve_launch_gate.py
PYTHONDONTWRITEBYTECODE=1 python eval/real_user_rollout_gate.py
PYTHONDONTWRITEBYTECODE=1 python scripts/build_borg_proof_dashboard.py
PYTHONDONTWRITEBYTECODE=1 python scripts/borg_proof_dashboard_lint.py
```

**Stop if:** public status says GO while first-10 evidence is blocked, measured value is derived from aggregate/synthetic/internal data, or stale dashboards disagree with snapshots.

---

### P0. Lock read-only verification semantics

**Why:** Operators need to inspect readiness without rewriting release artifacts.

**Do:**

1. Keep `--no-write` support for every status/gate/watchdog command that operators use for read-only verification.
2. Keep sentinel tests that pre-seed snapshot/report files and prove no-write leaves them unchanged.
3. Run each no-write command from a clean tree and assert `git status --short` remains unchanged.

**Hard gate:**

```bash
git status --short
PYTHONDONTWRITEBYTECODE=1 python eval/public_self_serve_launch_gate.py --no-write || true
PYTHONDONTWRITEBYTECODE=1 python eval/real_user_rollout_gate.py --no-write || true
PYTHONDONTWRITEBYTECODE=1 python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker first_10_external_evidence --require-ci-schedule
git status --short
```

**Stop if:** any read-only command mutates tracked files.

---

### P1. Finish production ops for first-10

**Why:** Controlled beta is only safe if bad answers, privacy incidents, install failures, and rollback have a real operating loop.

**Do:**

1. Assign explicit owner/on-call for the first-10 window.
2. Verify issue templates and intake paths:
   - bad answer;
   - install/MCP support;
   - first-10 evidence;
   - privacy/security incident.
3. Run rollback/comms dry-run before inviting users.
4. Define pause criteria and communication templates.
5. Review every P0/P1 beta issue before adding more users.

**Hard gate:**

```bash
PYTHONDONTWRITEBYTECODE=1 python eval/self_service_ops_gate.py
PYTHONDONTWRITEBYTECODE=1 python eval/rollback_comms_drill.py --dry-run
PYTHONDONTWRITEBYTECODE=1 python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker first_10_external_evidence --require-ci-schedule
```

**Stop if:** no owner, stale rollback snapshot, issue intake is missing, privacy/security incident exists, or public status cannot be updated quickly.

---

### P1. Cross-platform clean-install/client matrix

**Why:** Linux-only source and CI are not enough for self-serve users.

**Do:**

Run first-user smoke on:

- Linux, macOS, Windows.
- Python 3.10, 3.11, 3.12.
- `pipx install agent-borg==3.3.15` and isolated `pip install agent-borg==3.3.15`.
- At least two MCP hosts beyond the local stdio canary.

**Hard gate for each environment:**

```bash
borg --version
borg-doctor --json
borg rescue "ModuleNotFoundError: No module named flask" --json
borg generate systematic-debugging --format all --output /tmp/borg-rules
borg-mcp < initialize/tools-list/borg_rescue stdio canary >
```

**Stop if:** package name confusion with BorgBackup, console scripts fail, import path points to checkout instead of installed package, generated rules fail, or MCP host cannot discover value tools.

---

### P1. Marketplace / remote listing readiness

**Why:** Listing Borg in remote MCP marketplaces before remote/server posture is proven creates a trust and support problem.

**Do:**

1. Keep Smithery draft as local stdio until remote HTTP is actually deployed and fingerprinted.
2. Generate listing metadata from the actual tool list/version, not hand-maintained counts.
3. Ensure all marketplace surfaces use canonical `borg-farther` identity and no stale personal/org names.
4. Remove unsupported measured savings or adoption claims.
5. For remote HTTP listing, require auth/rate limiting, remote-safe tool allowlist, audit-log redaction, and served runtime fingerprint.

**Hard gate:**

- `deploy/smithery/smithery.yaml` says local stdio / not remote-listed unless hosted runtime proof exists.
- author identity is `Borg contributors` or canonical org identity.
- no unverified measured savings/lift claim.
- tool count/version match `borg-mcp tools/list` and `pyproject.toml`.

**Stop if:** stale account name, remote/stdout mismatch, unauthenticated remote write tools, or “token savings” is presented as measured.

---

### P1. Production hosted registry / federated learning ops

**Why:** The signed protocol gate proves a scoped local HTTP manifest sync/revocation path, not an operated public registry.

**Do:**

1. Stand up a production registry with monitoring, backups, restore drill, and incident response.
2. Add key-rotation and key-compromise runbooks.
3. Add transparency-log anchoring or signed append-only audit record before high-trust public federation claims.
4. Add abuse/quarantine workflow for poisoned atoms or malicious tenants.
5. Track revocation convergence SLOs with telemetry, not just one local gate.

**Hard gate:**

- signed manifest sequence monotonicity;
- trusted registry key verification;
- replay/rollback rejection;
- hash/size verification before import;
- tombstone-first revocation convergence;
- clean-client sync from empty state;
- backup/restore drill succeeds;
- compromised-key rotation drill succeeds.

**Stop if:** any operator can self-promote, revocation loses to import, manifests are mutable without audit, or compromised keys cannot be rotated without breaking clients.

---

### P1. Security/privacy review before public self-serve

**Why:** Prompt-injection, PII leakage, quorum inflation, stale runtime, and bad guidance are the product’s existential risks.

**Do:**

1. Independent review of learning atom signing, outcome receipts, quorum, tenant pseudonymization, tombstones, privacy scanning, prompt-injection scanning, and MCP remote policy.
2. Verify no raw traces/secrets/env paths enter shared atoms or public docs.
3. Verify forged/self-signed receipts, mismatched atom IDs, local/org tenant hints, cluster-only public ingestion, and stale runtime all fail closed.
4. Run dependency/security gates on the exact release branch.

**Hard gate:**

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/security tests/mcp eval/tests/test_security_hardening_baseline.py --tb=short
python scripts/security_gate_check.py
```

**Stop if:** unsigned/tampered/revoked atoms retrieve, tenant quorum can be inflated, raw PII is exported, or remote MCP exposes write tools before auth/policy.

---

### P2. 25 → 50 → 100 user staged rollout

**Why:** 100 real users is a separate gate, not a scaled-up first-10 assumption.

**Do after first-10 passes:**

1. Invite 25 users.
2. Require install success ≥80%, useful rescue ≥60%, no unresolved P0, support load manageable.
3. Invite 50 users only after repeat-use within 7 days is measured.
4. Invite 100 users only after public self-serve gate passes and rollback/support process survives earlier stages.

**Hard gate:**

- 25-user status doc and machine snapshot;
- 50-user retention/reuse snapshot;
- 100-user rollout snapshot with `ready_for_100_real_users=true`.

**Stop if:** repeat use is absent, bad-answer rate rises, support queue grows faster than maintainer capacity, or any privacy/security incident remains untriaged.

---

### P2. Measured value / Google-tier impact proof

**Why:** Current gates prove mechanics and safety. They do not prove external lift.

**Do:**

1. Design controlled evaluation:
   - no Borg;
   - empty Borg / scaffolding only;
   - seeded Borg with current knowledge;
   - optionally served collective path.
2. Collect task-completion, time, token, dead-end, and user-confirmed usefulness data.
3. Pre-register success metrics and stop rules.
4. Analyze negative guidance, false positives, and `NO_CONFIDENT_MATCH` quality.
5. Publish only row-derived, statistically honest claims.

**Hard gate:**

- ≥10 first-user rows before broad claims;
- sufficient sample for the selected effect size before statistical claims;
- raw/redacted evidence retained privately with consent;
- public dashboard shows measured savings only from row-derived before/after fields.

**Stop if:** lift is inferred from seed-pack success counts, synthetic users, internal dogfood, aggregate-only counters, or anecdotes.

## Current final blocker hierarchy

1. **Keep PR #43 and the 3.3.15 proof chain green on the exact final head.** This includes CI, first-user release gate, fresh-install/canary proof, and regenerated proof artifacts.
2. **Remove stale proof split-brain.** Current dashboards/status/snapshots must represent the final PR head or clearly identify themselves as historical/internal artifacts.
3. **Fingerprint every actual served MCP/runtime channel.** Local stdio proof is not served-runtime proof.
4. **Run controlled first-10 external beta only while package/ops/watchdog gates remain green.** Current verified external users are `0/10`.
5. **Keep public self-serve and 100-user rollout blocked until row-derived evidence passes.**
6. **Only then expand to public listing/marketplaces/remote MCP/100 users/measured-lift claims.**

## Final reflective challenge pass

I tried to disprove each likely conclusion:

- **Could we say Borg is broad-production ready because package and PR gates are green?** No. Package/source gates support only constrained first-10 beta; broad public self-serve still requires row-derived external-user evidence.
- **Could we say controlled first-10 beta is unconditional GO because dashboards say GO?** No. The correct state is conditional GO while package/ops/watchdog gates remain green and the cap stays at 10 consented testers.
- **Could we avoid fresh package proof by documenting a workaround?** No. First-user channels need clean wheel/PyPI-style testing and generated proof artifacts on the final head.
- **Could local source tests prove PyPI users are safe?** No. The exact bug was invisible until clean wheel/PyPI-style channel testing.
- **Could fresh stdio MCP prove served runtime?** No. Long-lived served processes can be stale in memory; they need runtime fingerprint and operator-approved cutover proof.
- **Could generated proof dashboards be trusted if they are stale?** No. Stale proof artifacts are blockers, not evidence.
- **Could external lift be claimed from internal or synthetic gates?** No. Lift requires consented external rows and a counterfactual evaluation.

Bottom line: Borg now has a clear final path. The next real milestone is PR #43 green on the exact final head plus constrained first-10 beta evidence collection. Broad public production remains blocked until those rows and served-runtime proof exist.
