# Borg production-readiness final todo

**Generated:** 2026-05-28 08:35 UTC
**Repo:** `https://github.com/borg-farther/Borg-Directory`
**Branch under review:** `fix/runtime-freshness-federated-learning-plan`
**Reviewed head:** `1964cbd18fb52b47af5c3d148c840e9c5b770029`
**PyPI package:** `agent-borg==3.3.14`

## Executive verdict

Borg is **controlled first-10 beta ready** for the published local CLI / stdio MCP package path, capped at **10 consented external users**.

Borg is **not yet broad-public-production ready**. The remaining blockers are not mostly code mechanics; they are launch evidence, served-runtime proof, and production-ops proof.

Current split:

- **Local source/package health:** GO.
- **PyPI fresh-install path:** GO.
- **Local stdio MCP path:** GO.
- **Internal collective-learning primitives:** GO.
- **Signed hosted-registry sync/revocation protocol:** GO for the scoped protocol gate.
- **Controlled first-10 beta:** GO / CONDITIONAL, max 10 consented users.
- **Served/remote MCP production channel:** NO-GO until the actual served process is fingerprinted after operator-approved cutover.
- **Broad public self-serve:** NO-GO until first-10 row-derived external evidence passes.
- **100 real users:** NO-GO until first-10 evidence passes and the rollout gate raises the cap.
- **Measured external lift / “Google-tier” product impact:** NO-GO until real external outcomes and counterfactual evaluation exist.

## Method / verification sources

This todo is based on four independent evidence paths:

1. **Session-history archaeology**
   - Prior chats consistently identify these blockers: first-10 evidence, served runtime freshness, broad public/100-user NO-GO, and external measured lift.
   - Key historical states: PR #37 controlled-beta gates; collective learning hardening; PR #39 final green branch; scoped federated protocol GO.

2. **Current repo inspection**
   - Clean branch at `1964cbd18fb52b47af5c3d148c840e9c5b770029` before this follow-up patch.
   - PR #39 open, mergeable, clean, all GitHub checks green.
   - PyPI latest is `agent-borg==3.3.14` with current canonical URLs.

3. **Live gate probes**
   - Ops watchdog: pass.
   - Public self-serve gate: expected fail-closed on first-10 evidence `0/10`.
   - Real-user rollout gate: expected fail-closed on first-10 evidence `0/10`.
   - Federated gate: scoped protocol GO.
   - Collective intelligence loop gate: scoped internal primitives GO.

4. **Adversarial challenge review**
   - Product/security/operator review found two repo-fixable issues and several non-code production blockers.
   - Repo-fixable issues fixed in this follow-up:
     - `eval/real_user_rollout_gate.py --no-write` now truly avoids rewriting artifacts.
     - Smithery draft metadata now says local stdio, Borg contributors, no remote listing, no unsupported measured-savings claim.

## Final production-readiness todo list

### P0. Merge the green hardening branch and verify main

**Why:** PR #39 contains the current trust-boundary, runtime-freshness, public-proof, and CI fixes. Until merged, main is not the production source of truth.

**Do:**

1. Get final human review on PR #39.
2. Merge PR #39.
3. Fetch/checkout `main`.
4. Verify local `main` equals the GitHub merge SHA.
5. Wait for post-merge main workflows.
6. Confirm every required workflow on the merge SHA is success:
   - CI Python 3.10 / 3.11 / 3.12.
   - Borg Security Gates: secret scan, dependency audit, static security, policy check.
   - Self-service readiness watchdog.
   - Account reference firewall.
7. Regenerate proof snapshots/dashboards from the clean merge SHA if any generated artifact still references a pre-merge dirty ancestor.

**Hard gate:**

```bash
gh pr view 39 --json state,mergeCommit,headRefOid,statusCheckRollup,mergeStateStatus,mergeable
git fetch origin main
git checkout main
git pull --ff-only origin main
gh api "repos/:owner/:repo/actions/runs?head_sha=$(git rev-parse HEAD)&per_page=50"
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider --tb=short
PYTHONDONTWRITEBYTECODE=1 python eval/ops_readiness_watchdog.py --mode pr --json --no-write --max-snapshot-age-hours 24 --allow-public-blocker first_10_external_evidence --require-ci-schedule
git status --short
```

**Stop if:** PR is not reviewed, main CI is pending/failing, generated dashboards reference stale proof, or tree is dirty after verification.

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
4. If stale, expose only fingerprint/upgrade guidance or keep that channel out of beta traffic until an operator-approved reload/cutover completes.

**Hard gate:**

- `borg_version == source_version == PyPI version`.
- `version_matches_source == true`.
- loaded function hashes exist for confidence gate and MCP server functions.
- meta/readiness prompt returns fail-closed `NO_CONFIDENT_MATCH`.
- concrete error prompt still returns specific guidance.
- no raw session IDs/secrets in logs.

**Stop if:** the process is stale, un-fingerprintable, writing to unexpected BORG_HOME, missing hashes, or serving write/network tools remotely without explicit auth/policy.

---

### P0. Run the first-10 external beta and fill real evidence rows

**Why:** This is the main blocker to broad production. Current verified external users are `0/10`.

**Do:**

1. Recruit 10 consented external users.
2. Give each user the same published-package path:
   - `pipx install agent-borg` or isolated `pip install agent-borg==3.3.14`.
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

1. Keep public docs/status saying controlled first-10 beta only.
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

**Why:** Operators need to inspect readiness without rewriting release artifacts. One discovered gap was fixed here: `real_user_rollout_gate.py --no-write` now has a real no-write path.

**Do:**

1. Add/keep `--no-write` support for every status/gate/watchdog command that operators use for read-only verification.
2. Add tests that pre-seed sentinel snapshot/report files and prove no-write leaves them unchanged.
3. Run each no-write command from a clean tree and assert `git status --short` remains empty.

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
- `pipx install agent-borg` and isolated `pip install agent-borg==3.3.14`.
- At least two MCP hosts beyond the local stdio canary.

**Hard gate for each environment:**

```bash
borg --version
borg-doctor --json
borg rescue "ModuleNotFoundError: No module named flask" --json
borg-mcp < initialize/tools-list/borg_rescue stdio canary >
```

**Stop if:** package name confusion with BorgBackup, console scripts fail, import path points to checkout instead of installed package, or MCP host cannot discover value tools.

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

- `deploy/smithery/smithery.yaml` says `remote: false` unless hosted runtime proof exists.
- `authorName` is `Borg contributors` or canonical org identity.
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

- signed manifest sequence monotonicity.
- trusted registry key verification.
- replay/rollback rejection.
- hash/size verification before import.
- tombstone-first revocation convergence.
- clean-client sync from empty state.
- backup/restore drill succeeds.
- compromised-key rotation drill succeeds.

**Stop if:** any operator can self-promote, revocation loses to import, manifests are mutable without audit, or compromised keys cannot be rotated without breaking clients.

---

### P1. Security/privacy review before public self-serve

**Why:** Prompt-injection, PII leakage, quorum inflation, and bad guidance are the product’s existential risks.

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

- 25-user status doc and machine snapshot.
- 50-user retention/reuse snapshot.
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

- ≥10 first-user rows before broad claims.
- sufficient sample for the selected effect size before statistical claims.
- raw/redacted evidence retained privately with consent.
- public dashboard shows measured savings only from row-derived before/after fields.

**Stop if:** lift is inferred from seed-pack success counts, synthetic users, internal dogfood, aggregate-only counters, or anecdotes.

## Current final blocker hierarchy

1. **Merge PR #39 and prove post-merge main.**
2. **Served runtime fingerprint/cutover for any live served channel.**
3. **Run first-10 external beta and collect real row-derived evidence.**
4. **Keep public self-serve and 100-user gates blocked until those rows pass.**
5. **Only then expand to public listing/marketplaces/100 users/measured-lift claims.**

## Final reflective challenge pass

I tried to disprove each likely conclusion:

- **Could green CI mean production ready?** No. CI proves source quality, not first-user adoption, served runtime freshness, or external lift.
- **Could PyPI fresh install mean public self-serve ready?** No. It proves the package path, not usefulness for real external users.
- **Could signed federated gate mean public collective learning ready?** Only for the scoped protocol. A production hosted registry still needs ops, monitoring, key rotation, abuse handling, backups, and transparency/audit story.
- **Could controlled first-10 beta be unsafe because evidence is still zero?** It is safe only as a supervised evidence-collection phase capped at 10, with ops/watchdog/rollback gates green and privacy/security incidents pausing immediately.
- **Could runtime freshness be considered solved?** Only for local/fresh-process probes. Any long-lived served process must be fingerprinted through the actual served channel.
- **Could the todo list hide repo-fixable blockers as future work?** Two repo-fixable blockers discovered during this review were fixed immediately: no-write semantics for real-user rollout and stale Smithery metadata.

Bottom line: Borg is ready to collect its first real external evidence under supervision. It is not ready to claim broad public production until those rows, served runtime proof, and post-merge/main proof are complete.
