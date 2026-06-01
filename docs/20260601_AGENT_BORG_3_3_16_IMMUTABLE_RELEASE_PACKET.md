# agent-borg 3.3.16 immutable release packet

> Historical/internal — not current product documentation. Operator release-preflight artifact only; do not treat this as a user-facing install/readiness page.

Generated: 2026-06-01T08:51Z  
Package: `agent-borg`  
Candidate next immutable version: `3.3.16`  
Production PyPI upload status: **NO-GO / NOT EXECUTED**

## Executive verdict

Do **not** upload to production PyPI yet.

`agent-borg==3.3.16` is the lowest safe next immutable version because PyPI already contains `3.3.15` and does not contain `3.3.16`, but the release boundary is still blocked by provenance and approval gates.

## Current hard facts

- Source checkout: `/root/hermes-workspace/borg`
- Branch: `main`
- HEAD: `a7f5e769016ac83f249d57fe8e36b34f020dda3b`
- `origin/main`: `a7f5e769016ac83f249d57fe8e36b34f020dda3b`
- Source version: `pyproject.toml=3.3.15`, `borg/__init__.py=3.3.15`
- PyPI latest: `agent-borg==3.3.15`
- PyPI `3.3.15` upload times:
  - wheel: `2026-05-28T17:50:29.231332Z`
  - sdist: `2026-05-28T17:50:31.032755Z`
- HEAD commit time: `2026-05-31T20:14:30+01:00`
- Same-version artifact drift: **FAIL** — the published `3.3.15` artifacts predate the current source commit.
- PyPI version availability checked: `3.3.16` absent, `3.3.17` absent.

## Why `3.3.15` cannot be reused

PyPI versions are immutable. The package already has `agent-borg==3.3.15`. Even though source metadata still says `3.3.15`, the current source contains changes after the published artifact timestamp. Re-uploading or pretending the existing `3.3.15` represents current source would be a release-truth violation.

## Upload blockers

1. **No exact irreversible upload approval.** Production PyPI upload was not explicitly approved for `agent-borg==3.3.16`.
2. **Source version has not been bumped.** Current source still says `3.3.15`.
3. **Working tree is dirty.** The watchdog/proof changes and generated artifacts are uncommitted.
4. **No release commit/tag provenance.** There is no `3.3.16` release commit or tag at the current proof state.
5. **Main branch protection is red.** Captured release governance says `main` is not protected.
6. **Served runtime is stale.** Captured served Borg MCP runtime reports `borg_version=3.3.14` while source is `3.3.15`.
7. **First-10 evidence is zero.** Public self-serve and 100-user gates remain row-derived NO-GO.
8. **Existing `dist/` artifacts are `3.3.15` only.** They pass `twine check`, but they are not uploadable for this release.

## Proof already green in this workstream

- Permanent watchdog semantics fixed: stale PyPI fresh-install snapshots are only tolerated when package/PyPI proof is already red; green package claims require a fresh canary.
- Scheduled workflow now refreshes the PyPI fresh-install canary before fail-closed public/readiness gates.
- Proof dashboard now requires fresh PyPI canary plus stdio MCP pass before package-current gate can be green.
- Generated public status is honest: `NO-GO public self-serve; source/local release-candidate only`.
- Ops watchdog after regeneration: `passed=True`, blockers `[]`.
- Full local test suite: `2515 passed, 40 skipped, 4 xfailed, 1 xpassed`.
- Focused readiness/public/dashboard tests: `70 passed`.
- Security hardening policy gate: `PASS`.
- Dashboard lint: `PASS`.
- `git diff --check`: `PASS`.

## Exact safe release sequence after approval

Only after explicit approval naming **`agent-borg==3.3.16`**:

1. Bump version in both places:
   - `pyproject.toml`: `3.3.15` → `3.3.16`
   - `borg/__init__.py`: `3.3.15` → `3.3.16`
2. Regenerate proof artifacts in dependency order:
   - PyPI/source gates expected to remain pre-upload NO-GO for `3.3.16`
   - inventory board
   - proof dashboard/status/value/impact
   - watchdog/lint
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

`agent-borg==3.3.16` is the correct candidate, but production upload is blocked until the operator explicitly approves that exact package/version and the release commit/tag/CI/artifact preflight is green.
