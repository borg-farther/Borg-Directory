> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# Fix-all public launch blockers report

Generated: 2026-05-14T18:26:13Z

## Verdicts

- **PUBLIC_WAITLIST_NARROW_BETA:** YES_WITH_CAVEATS
- **PUBLIC_SELF_SERVE_LAUNCH:** NO

## FIXED autonomously

- Safe generated build/dist hygiene performed (`git reset`; `git restore -- build/lib dist`; removal of untracked `dist/agent_borg-3.3.1*`).
- First-10 scoreboard validated without fabricating users (`verified_external_users=0`).
- Blocker board and cleanup runbook updated.
- Local verification/security/claims-adjacent gates executed with full rc/stdout/stderr in `eval/20260514_fix_all_public_launch_blockers.json`.
- Source canaries executed: unrelated readiness -> NO_CONFIDENT_MATCH; permission denied -> permission guidance.
- External-ish install proof executed: pipx status `PASS`, clean venv status `NOT_RUN_PIPX_AVAILABLE`.
- GitHub identity/remotes/heads diagnosed read-only; no push/publish/visibility mutation attempted.

## STILL HARD-BLOCKED

- `live_mcp_runtime_identity`: HUMAN_BLOCKED until an approved human-supervised live reload/canary.
- `first_10_real_users`: HUMAN_BLOCKED; verified external users remain 0.
- `github_admin_push_path`: READ_ONLY_DIAGNOSED only; human must use correct PAT and approve any push/admin mutation.

## Artifact paths

- `eval/20260514_fix_all_preflight.json`
- `eval/20260514_fix_all_public_launch_blockers.json`
- `docs/20260514_FIX_ALL_PUBLIC_LAUNCH_BLOCKERS_REPORT.md`
- `docs/20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md`
- `docs/20260514_BORG_RELEASE_BRANCH_CLEANUP_RUNBOOK.md`
- `eval/first_10_user_scoreboard.json`

## Exact human actions needed

1. Review `git diff --cached` and run `git diff --cached --check`.
2. If acceptable, push the staged release branch with the correct borg-farther GitHub token/PAT; do not push unrelated unstaged work.
3. Human-supervised reload of live Hermes/MCP, then run live canaries: `borg_runtime_fingerprint`, unrelated `borg_observe`, permission-denied `borg_observe`.
4. Recruit 10 consented external beta users; record redacted evidence in `eval/first_10_user_scoreboard.json`; require ≥8 install successes, ≥6 useful rescues, and 0 critical privacy/security failures.
5. Final human copy/claims review before any public announcement.
