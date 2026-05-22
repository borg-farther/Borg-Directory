> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 20260423-1333 Claude CLI Telegram UAT Closure

## Decision
**status: NO-GO** for external sharing right now.

## What was completed
1. Created explicit UAT contract with binary acceptance gates:
   - `eval/claude_cli_telegram_uat_contract.json`
2. Created operator runbook for this channel:
   - `docs/CLAUDE_CLI_TELEGRAM_UAT.md`
3. Added automated contract tests:
   - `eval/tests/test_claude_cli_telegram_uat_contract.py`
4. Executed RED→GREEN proof loop:
   - RED evidence: `session_cron_9c6214ac3d60_20260423_132349.json`
   - GREEN evidence: `session_cron_6672c0603a9a_20260423_132613.json`

## Test evidence snapshot
- RED: **5 failed, 1 passed** (expected before artifacts existed)
- GREEN: **6 passed**
- Regression: **1 failed, 52 passed** in `borg/tests/test_search.py`
  - failing case: `TestBorgSearch::test_search_with_matching_packs`
  - observed mismatch: expected `total==1`, actual `total==3`

## Why this is NO-GO
A regression test failed in adjacent core search behavior. Even though UAT contract artifacts are green, shipping to external Claude CLI users with known regression risk violates release discipline.

## Permanent-close actions (next run)
1. Fix/triage `borg/tests/test_search.py::TestBorgSearch::test_search_with_matching_packs`.
2. Run regression suite again to green.
3. Capture runtime smoke artifact for `borg --version`, `borg-mcp --help`, and Claude MCP config detection.
4. Flip report from NO-GO to GO only after all gates are green with session proof.

## Artifacts
- `eval/20260423_claude_cli_telegram_uat_report.json`
- `eval/claude_cli_telegram_uat_contract.json`
- `docs/CLAUDE_CLI_TELEGRAM_UAT.md`
- `eval/tests/test_claude_cli_telegram_uat_contract.py`
