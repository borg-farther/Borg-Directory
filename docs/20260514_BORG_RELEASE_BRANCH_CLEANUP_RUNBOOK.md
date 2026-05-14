# Borg release branch cleanup runbook

Generated: 2026-05-14T18:26:13Z

## What the safe runner did

- Backed up preflight git status/diff/cached diff to `eval/20260514_fix_all_preflight.json`.
- Ran `git reset` to unstage only.
- Ran `git restore -- build/lib dist` to restore generated side effects from HEAD.
- Removed only untracked generated `dist/agent_borg-3.3.1*` package outputs.
- Ran verification gates and source canaries.
- Staged only allowlisted public-readiness files when gates passed.

## Remaining human cleanup

1. Review `git diff --cached` and `git diff --cached --check`.
2. Keep unrelated unstaged source/docs/eval modifications out of the release branch unless separately reviewed.
3. Do not push until the release branch owner approves.
4. Do not restart live Hermes/MCP except under explicit human supervision.

## Allowed stage candidates used by runner

```text
borg/core/confidence_gate.py
borg/integrations/mcp_server.py
borg/tests/test_confidence_gate.py
docs/BORG_PROOF_DASHBOARD.md
docs/BORG_PROOF_DASHBOARD.html
docs/public/proof-dashboard/index.html
docs/20260514_BORG_GOOGLE_TIER_READINESS_CONTINUATION.md
docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md
docs/20260514_BORG_PUBLIC_LAUNCH_IMPLEMENTATION_REPORT.md
docs/20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md
docs/20260514_BORG_RELEASE_BRANCH_CLEANUP_RUNBOOK.md
eval/borg_proof_dashboard.json
eval/first_user_release_gate_snapshot.json
eval/20260514_borg_google_tier_readiness_continuation.json
eval/20260514_borg_public_launch_readiness.json
eval/20260514_borg_public_launch_command_log.json
eval/20260514_borg_public_launch_outstanding_blockers.json
eval/first_10_user_scoreboard.json
eval/tests/test_borg_proof_dashboard.py
scripts/build_borg_proof_dashboard.py
scripts/borg_proof_dashboard_lint.py
scripts/fix_public_launch_blockers_safe.py
```
