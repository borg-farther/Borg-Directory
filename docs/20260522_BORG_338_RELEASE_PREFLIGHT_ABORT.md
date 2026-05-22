# Borg 3.3.8 production PyPI release preflight

Generated: 2026-05-22T11:44:21Z

## Verdict

**ABORT_UPLOAD** — do not upload `agent-borg==3.3.8` to production PyPI yet.

This is the correct hard stop. The code-side and package-side gates are green; the release provenance gates are not.

## Green gates already proven

- Source version consistency: `pyproject=3.3.8 runtime_fallback=3.3.8`.
- Full suite: `2174 passed, 40 skipped, 4 xfailed, 1 xpassed, 44 warnings`.
- Public/readiness/docs tests: `74 passed`.
- Security gate: `PASS: Borg security hardening policy gate`.
- MCP/CLI/apply targeted gates: `107 passed, 1 xfailed`.
- Proof dashboard: build + lint + tests passed.
- Local first-user release gate: PASS.
  - Built `agent_borg-3.3.8` wheel/sdist locally.
  - Fresh local wheel install passed.
  - `borg --version` returned `borg 3.3.8`.
  - `borg rescue` returned ACTION / STOP / VERIFY.
  - `borg-doctor --json` passed.
- Artifact metadata check: `twine check` passed for both `dist/agent_borg-3.3.8-py3-none-any.whl` and `dist/agent_borg-3.3.8.tar.gz`.
- PyPI absence: `agent-borg==3.3.8` is absent; latest is `3.3.7`.
- Docs claim guard: PASS; checked docs plus public proof-dashboard artifacts and found no unsupported public-launch/lift claims.

## Blocking release gates

- Remote branch: FAIL — `production-readiness-hardening-20260522` is not present on origin.
- Default branch provenance: FAIL — 3.3.8 changes are not merged into `origin/main`.
- Tag: FAIL — no local/remote `v3.3.8` tag was observed.
- CI: FAIL — no GitHub Actions run can exist for an unpushed/unmerged release commit.
- PyPI fresh-install canary: expected FAIL before upload — isolated `pip install --index-url https://pypi.org/simple agent-borg==3.3.8` cannot find the version.
- Public self-serve gate: NO-GO — PyPI latest/fresh-install and first-10 evidence gates are blocked.
- First-10 external evidence: BLOCKED — `verified=0/10`, `installs=0/8`, `useful=0/6`, `critical_incidents=0/0`.

## Non-negotiable upload sequence

1. Push branch `production-readiness-hardening-20260522` to origin.
2. Open a release PR against `main` with the verified gate evidence.
3. Require GitHub Actions success on the exact PR head and merge commit.
4. Merge to `main` according to repo policy.
5. Create/push `v3.3.8` on the CI-green `main` commit.
6. Rebuild wheel/sdist from a clean checkout of the tagged commit.
7. Re-run `twine check` and a local fresh-install wheel smoke.
8. Confirm PyPI absence again.
9. Upload only:
   - `dist/agent_borg-3.3.8-py3-none-any.whl`
   - `dist/agent_borg-3.3.8.tar.gz`
10. Post-upload, run:
   - `python eval/run_pypi_fresh_install_canary.py`
   - `python eval/public_self_serve_launch_gate.py`
11. Keep public self-serve NO-GO until row-derived first-10 external evidence passes.

## Boundary

The repo-side 3.3.8 release candidate is ready for PR review. Production PyPI upload is blocked by release provenance and external evidence gates. No upload was attempted.
