# Repository Hygiene Policy

This repository keeps **runtime + canonical artifacts in place** and archives generated rollout/readiness reports by date.

## Canonical artifacts (stay in-place)

- `PROJECT_STATUS.md`
- `GO_NO_GO_DECISION.md`
- `UAT_RESULTS.md`
- `eval/gate_run_snapshot.json`
- `eval/uat_scoreboard_snapshot.json`
- `eval/new_home_*.json`
- `eval/tests/**`
- `scripts/**`
- `borg/**`

These remain in their current locations because they are active operational truth, contracts, test surfaces, and runtime code.

## Archival artifacts (move out of root)

Root-level generated reports:

- `READINESS_PROOF_*.md`
- `READINESS_FINAL_PROOF_*.md`
- `EXTERNAL_ROLLOUT_REPORT_*.md`
- `EXTERNAL_ROLLOUT_EXECUTION_*.md`
- `UNBLOCK_EXTERNAL_PUBLISH_RUNBOOK_*.md`

Store them under:

- `archive/reports/<YYYYMMDD>/`
- `archive/reports/<YYYYMMDD>/eval/` for:
  - `eval/rollout_logs_*`
  - `eval/rollout_run_summary_*.json`

## Browsing guidance

1. Start with canonical docs for current decisions/readiness.
2. Use `archive/reports/<date>/` for historical forensic context only.
3. Archived files must not be imported into runtime logic or gate decisions.
