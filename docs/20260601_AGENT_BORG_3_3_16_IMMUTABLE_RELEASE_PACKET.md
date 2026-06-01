# agent-borg 3.3.16 immutable release packet

> Historical/internal — not current product documentation. Operator release-preflight artifact only; do not treat this as a user-facing install/readiness page.

Generated: 2026-06-01T19:53Z
Package: `agent-borg`
Candidate next immutable version: `3.3.16`
Production PyPI upload status: **NO-GO / NOT EXECUTED**

## Executive verdict

Do **not** upload to production PyPI yet.

`agent-borg==3.3.16` is still the lowest safe next immutable version because PyPI already contains `3.3.15` and does not contain `3.3.16`, but the release boundary remains blocked by approval, version bump, release provenance, served-runtime, governance, and first-10 evidence gates.

## Current hard facts

- Source checkout: `/root/hermes-workspace/borg`
- Canonical remote: `https://github.com/borg-farther/Borg-Directory`
- Current base branch: `main`
- Current base HEAD / `origin/main`: `ea31144b78ba55628e32cb64d08f3fa542509887`
- Active reversible hardening branch at packet refresh: `fix/release-governance-codeowners-20260601`
- Source version: `pyproject.toml=3.3.15`, `borg/__init__.py=3.3.15`
- PyPI latest: `agent-borg==3.3.15`
- PyPI `3.3.15` upload times:
  - wheel: `2026-05-28T17:50:29.231332Z`
  - sdist: `2026-05-28T17:50:31.032755Z`
- PyPI version availability checked: `3.3.16` absent, `3.3.17` absent.
- Same-version artifact drift: **FAIL** — published `3.3.15` artifacts predate current source changes.
- Live GitHub `main` protection: **FAIL** — `protected=false`; `/branches/main/protection` returns `404 Branch not protected`.
- Live CODEOWNERS validation before this hardening PR: **FAIL** — `11` errors because `@borg-farther/maintainers` is invalid in a user-owned repo. Reversible fix in flight: use valid owner `@borg-farther` unless/until the repo moves to an organization with a visible write team.
- Actual GitHub Actions check-run contexts observed on current `main`: `test (3.10)`, `test (3.11)`, `test (3.12)`, `dependency-audit`, `policy-check`, `secret-scan`, `static-security`, `ops-readiness-watchdog`, `old-account-reference`.

## Why `3.3.15` cannot be reused

PyPI versions are immutable. The package already has `agent-borg==3.3.15`. Even though source metadata still says `3.3.15`, current source contains changes after the published artifact timestamp. Re-uploading or pretending the existing `3.3.15` represents current source would be a release-truth violation.

## Upload blockers

1. **No exact irreversible upload approval.** Production PyPI upload was not explicitly approved for `agent-borg==3.3.16`.
2. **Source version has not been bumped.** Current source still says `3.3.15`.
3. **No release commit/tag provenance.** There is no approved `3.3.16` release commit or tag.
4. **Same-version PyPI drift remains red.** Published `3.3.15` is stale relative to source; next publish must use a new immutable version.
5. **Main branch protection is red.** Live `main` is unprotected until GitHub admin settings are changed after the CODEOWNERS fix is merged.
6. **CODEOWNERS validation was red on current `main`.** The repo owner is a user account, so team owner `@borg-farther/maintainers` is invalid; this packet's hardening branch fixes the file but live validation must be rechecked after merge.
7. **Served runtime is stale.** Captured served Borg MCP runtime reports `borg_version=3.3.14` while source is `3.3.15`.
8. **First-10 evidence is zero.** Public self-serve and 100-user gates remain row-derived NO-GO.
9. **Existing `dist/` artifacts are `3.3.15` only.** They may pass `twine check`, but they are not uploadable for this release.

## Release-governance hardening now in scope

The reversible hardening branch upgrades release governance from a loose label check to an exact, fail-closed gate:

- validates exact required check-run contexts, not broad workflow names;
- rejects substring decoys such as `fake-test (3.11)-bypass`;
- requires strict status checks;
- requires CODEOWNERS review, at least one approval, stale-review dismissal, last-push approval, admin enforcement, and conversation resolution;
- fails if force pushes or branch deletion are allowed;
- fetches GitHub CODEOWNERS validation errors and fails closed if any owner/path is invalid;
- makes public/readiness gates prefer live GitHub governance data over stale committed snapshots when network checks are enabled.

## Exact branch-protection settings to apply after CODEOWNERS fix is merged

GitHub admin mutation is approval-bound. Do not apply these settings until the CODEOWNERS fix is on `main` and `gh api repos/borg-farther/Borg-Directory/codeowners/errors --jq '.errors'` returns `[]`.

Required status check contexts:

- `test (3.10)`
- `test (3.11)`
- `test (3.12)`
- `dependency-audit`
- `policy-check`
- `secret-scan`
- `static-security`
- `ops-readiness-watchdog`
- `old-account-reference`

Required protections:

- strict required status checks: `true`
- pull request reviews required: `true`
- CODEOWNERS review required: `true`
- required approving reviews: `>=1`
- dismiss stale approvals: `true`
- require last-push approval: `true` where available
- enforce admins: `true`
- require conversation resolution: `true`
- allow force pushes: `false`
- allow deletions: `false`

Single-maintainer caveat: if only `@borg-farther` has write/admin access, CODEOWNERS can be syntactically valid but does not provide independent review separation. Strong governance needs a second trusted write/admin maintainer or an organization/team model.

## Exact safe release sequence after approval

Only after explicit approval naming **`agent-borg==3.3.16`**:

1. Bump version in both places:
   - `pyproject.toml`: `3.3.15` → `3.3.16`
   - `borg/__init__.py`: `3.3.15` → `3.3.16`
2. Regenerate proof artifacts in dependency order:
   - PyPI/source gates expected to remain pre-upload NO-GO for `3.3.16`
   - cold-start trust gate
   - rollback/self-service ops gates
   - public and real-user gates
   - watchdog
   - public and real-user gates again after watchdog
   - final watchdog
   - inventory board
   - proof dashboard/status/value/impact
   - dashboard lint
3. Run proof gates:
   - focused readiness tests
   - full pytest
   - security gate
   - dashboard lint
   - `git diff --check`
4. Commit the release-prep diff.
5. Establish release provenance on the exact commit:
   - push branch / PR if required
   - verify CI on the exact commit
   - tag only after the approved release commit is fixed
6. Build clean artifacts for `3.3.16` from that exact commit into a fresh output directory.
7. Run `twine check` and inspect artifact metadata/version.
8. Verify PyPI JSON still does not contain `3.3.16` immediately before upload.
9. Cross the irreversible boundary only with explicit production PyPI approval:
   - `TWINE_USERNAME=__token__ TWINE_PASSWORD=[REDACTED] python -m twine upload ...`
10. Post-upload proof:
   - poll PyPI JSON until `3.3.16` appears
   - verify upload timestamps are after the release commit time
   - fresh install `agent-borg==3.3.16` from non-repo cwd with `PYTHONPATH=` cleared
   - run `borg --version`, `borg --help`, `borg rescue ... --json`, `borg-doctor --json`, Python import API, generated rules, OpenClaw conversion, and stdio MCP JSON-RPC canary
   - regenerate public proof/status artifacts
   - keep public self-serve NO-GO until first-10 rows pass

## Final hold line

`agent-borg==3.3.16` remains the correct next candidate, but production upload is blocked until the operator explicitly approves that exact package/version and the release commit/tag/CI/artifact preflight is green. Branch protection and served-runtime cutover are also separate approval-bound operations; do not fake them with local/source-only proof.
