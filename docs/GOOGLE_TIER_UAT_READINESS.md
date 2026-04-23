# Google-Tier UAT Readiness (New Home)

This is the production UAT system for Borg after migration to the new git home.

## Objective

Prove (with machine-verifiable evidence) that Borg is:

1. Running from the new canonical repository (`borg-farther/Borg-Directory`)
2. Safe from split-brain writes (legacy remote is backup/fetch-only)
3. Ready to scale (10 / 100 / 1000 readiness gates)
4. Delivering utility and savings (higher completion, lower token cost)
5. Reporting readiness through canonical, consistent artifacts

## Hard Gate Runner

`python3 scripts/google_tier_uat_runner.py`

The runner emits canonical artifacts:

- `eval/google_tier_uat_snapshot.json` (full machine evidence)
- `eval/google_tier_uat_scoreboard.json` (compact machine gate board)
- `PROJECT_STATUS.md` (canonical status)
- `GO_NO_GO_DECISION.md` (binary operator decision)
- `UAT_RESULTS.md` (human-readable UAT report)

Exit code contract:

- `0` => PASS / GO
- `1` => FAIL / NO-GO

## Required Input Evidence

- `.git/config`
- `eval/new_home_governance_enforcement.json`
- `eval/new_home_readiness_report.json`
- `eval/new_home_test_gate_report.json`
- `eval/uat_scoreboard_snapshot.json`
- `eval/experiment_packet.json`
- `docs/20260422-0909_NEW_HOME_PRODUCTION_CLOSURE.md`
- `eval/gate_run_snapshot.json`

## Anti-Theater Rule

Required artifacts must be:

- present
- non-empty
- free of placeholder markers (`TODO`, `TBD`, `placeholder`, `coming soon`)

If this fails, status is NO-GO.

## Utility/Savings Rule

`eval/experiment_packet.json` must prove both:

- completion lift is positive and at least +0.05
- treatment token mean is lower than control token mean

If either fails, status is NO-GO.

## Legacy Backup Policy

Legacy repo is kept for backup/recovery only. Production write path is origin-only.

- origin: `https://github.com/borg-farther/Borg-Directory.git`
- legacy: `external-archival-remote (owner redacted)`
- legacy pushurl must remain disabled in local config

## Operator Runbook

1. Run `python3 scripts/google_tier_uat_runner.py`
2. Confirm `eval/google_tier_uat_snapshot.json` has `overall_status: pass`
3. Confirm `PROJECT_STATUS.md`, `GO_NO_GO_DECISION.md`, and `UAT_RESULTS.md` all show the same verdict
4. If any mismatch exists, treat as NO-GO and rerun after fixing source evidence
