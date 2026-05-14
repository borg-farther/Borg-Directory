# Borg public/self-serve launch readiness plan

Generated: 2026-05-14 14:36 UTC

## Goal
Move Borg from **supervised first-user beta** to **public/self-serve launch readiness** without hype, without unsafe service restarts, and with hard binary gates.

## Current state

Known green evidence:
- Supervised first-user gate: `26/26` pass, `0` fail, snapshot `2026-05-14T14:28:18Z`.
- Targeted confidence/runtime tests: `23 passed`.
- Proof dashboard build/lint/tests pass.
- Fresh-process `borg_observe` canary proves source/next-load behavior: unrelated readiness prompt returns `NO_CONFIDENT_MATCH`; real permission prompt still returns permission guidance.

Known gaps:
- Live long-running MCP has not been reloaded; live `borg_observe` fix is not claimable until supervised reload + live canary.
- Repo working tree has unrelated dirty noise and generated/staged build artifacts need human review before commit.
- GitHub push/privacy/admin path has previously failed with 403.
- Verified external users: `0`.
- Public/self-serve install proof from PyPI/pipx and external-machine path is not yet proven.
- Security posture has local artifacts but needs fresh public-release gate: secrets/remotes, dependency/static scan, privacy/redaction/revocation, docs claim scrub.

## Public readiness binary gates

### Gate 1 — live MCP/runtime identity
**Pass when:**
- Supervised reload window completed, with explicit approval.
- `borg_runtime_fingerprint` after reload shows intended source path/hash.
- Live served `mcp_borg_observe` unrelated readiness canary returns `NO_CONFIDENT_MATCH` and no stale plugin/BORG_HOME guidance.
- Live served permission canary still returns permission guidance.

**Do not do automatically:** restart/kill/signal gateway/MCP.

### Gate 2 — repo hygiene / release branch
**Pass when:**
- One release branch contains only public-readiness changes.
- `git status --short` is explainable: no unrelated dirty files in release diff.
- `git diff --cached --stat` excludes accidental `build/lib` mass-adds unless intentionally generated and reviewed.
- Old dist/build deletion side effects restored or deliberately ignored.
- GitHub auth against `borg-farther/Borg-Directory` can push and edit visibility as required, or an explicit owner-token blocker is documented.

### Gate 3 — self-serve install proof
**Pass when:**
- Fresh environment executes exact docs path, preferably:
  - `pipx install agent-borg`
  - `borg --version`
  - `borg rescue "ModuleNotFoundError: No module named flask"`
  - `borg rescue "ModuleNotFoundError: No module named flask" --json`
  - `borg-doctor --json`
- Version is consistent (`pyproject`, runtime, installed CLI).
- Output includes `ACTION / STOP / VERIFY`, `agent_instruction`, `human_receipt`.
- No hidden editable-install assumptions or stale wheel/cache.

### Gate 4 — public security baseline
**Pass when:**
- `python scripts/security_gate_check.py` passes.
- Security tests pass, including privacy/redaction/revocation/prompt injection.
- Secret scan and credential-bearing remotes check pass.
- Dependency/static scan either passes or records reviewed false positives with owner/date.
- Public docs make consent/redaction/revocation boundaries explicit before trace sharing.

### Gate 5 — claims/docs scrub
**Pass when:**
- README, quickstart, docs, dashboards, package metadata contain no unsupported claims:
  - no “proven collective intelligence”
  - no “hundreds of users” unless verified
  - no “public production ready” before Gate 6
- Docs state current truth: controlled beta, local security/readiness green, external utility under validation.
- First-user path is copy-paste exact and short.

### Gate 6 — first 10 real users
**Pass when:**
- First-10 scoreboard has real rows, not simulations.
- Minimum thresholds:
  - ≥8/10 install success
  - ≥6/10 report `borg rescue` useful
  - 0 critical privacy/security failures
  - blocker taxonomy recorded for all failures
  - at least one repeat-use or follow-up signal before investor-grade claim

## Implementation sequence

1. Create durable gate spec/docs and machine-readable public readiness board.
2. Add/refresh tests or lint for gate contracts where missing.
3. Run source/next-load canaries and readiness gates.
4. Run repo hygiene audit and produce a surgical staging/commit recommendation.
5. Run public security checks available in repo; mark external scans or GitHub permission issues as blockers if credentials/tools unavailable.
6. Generate first-10 scoreboard template if missing; do not fabricate user rows.
7. Produce `GO/NO-GO` decision:
   - `PUBLIC_WAITLIST_NARROW_BETA`: allowed after Gates 1–5 pass.
   - `PUBLIC_SELF_SERVE_LAUNCH`: allowed only after Gates 1–6 pass.

## Files likely to change

- `.hermes/plans/2026-05-14_1436-borg-public-launch-readiness.md`
- `docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md`
- `docs/20260514_BORG_PUBLIC_LAUNCH_IMPLEMENTATION_REPORT.md`
- `eval/20260514_borg_public_launch_readiness.json`
- potentially existing dashboard/readiness JSON/MD if regenerated by repo scripts.

## Verification commands

Run non-destructive gates only:
- `python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_runtime_fingerprint.py`
- `python scripts/build_borg_proof_dashboard.py`
- `python scripts/borg_proof_dashboard_lint.py`
- `python -m pytest -q eval/tests/test_borg_proof_dashboard.py`
- `python eval/run_first_user_release_gate.py`
- `python scripts/security_gate_check.py` if present
- repo hygiene: `git status --short`, `git diff --stat`, `git diff --cached --stat`

## Risks

- Live MCP can only be proven after supervised reload; source green is not live green.
- Public launch cannot be claimed without real first-10 users.
- GitHub token/admin failures may block public repo hygiene/visibility workflow.
- Running build/first-user gates can mutate `dist/` and `build/`; restore accidental side effects before staging.

## Open decisions

- Who approves/reloads live MCP?
- Which external first-user channel starts the first-10 scoreboard?
- Should public launch mean public waitlist/narrow beta or fully self-serve PyPI/GitHub launch?
