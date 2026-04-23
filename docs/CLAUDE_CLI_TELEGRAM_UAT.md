# Claude CLI Telegram UAT Runbook

## Scope
This runbook validates Borg for first-use acceptance when a user runs Claude CLI with Borg MCP integration and receives operational updates in Telegram.

## Preflight
1. Confirm target repo/workspace is current and test artifacts are writable.
2. Confirm Claude CLI environment has access to `borg` and `borg-mcp` binaries.
3. Confirm Claude config file is present at `~/.config/claude/claude_desktop_config.json`.
4. Confirm Telegram destination is the intended operator channel for UAT updates.

## Execution
### Phase A — Local command readiness
- Run `borg --version`
- Run `borg-mcp --help`
- Gate pass only if both commands return exit code 0.

### Phase B — Claude MCP wiring
- Open `~/.config/claude/claude_desktop_config.json`.
- Verify `mcpServers.borg` exists with either:
  - `"command": "borg-mcp"`
  - or `"command": "python3"` + `"-m", "borg.integrations.mcp_server"`
- Gate pass only if JSON is valid and entry is present.

### Phase C — Functional lifecycle
- Run a cold search (`borg search debugging`) and verify non-empty results.
- In Claude CLI, execute:
  - `borg_observe` with a realistic bug/task string.
  - `borg_apply` start/checkpoint/complete on a known pack.
  - `borg_feedback` for the finished session.
- Gate pass only if all calls return structured success.

### Phase D — Telegram acceptance for this channel
- Send one concise canary status message.
- Send one failure-mode remediation message (simulated known error).
- Send one completion summary.
- Gate pass only if markdown renders safely and messages stay concise + clear.

### Phase E — Release seal
- Confirm no UAT-critical docs point to retired legacy-home dependencies.
- Confirm all acceptance gates G1..G9 are green in the contract artifact.

## Pass/Fail Rubric
- **PASS**: Every gate in `eval/claude_cli_telegram_uat_contract.json` passes with session evidence.
- **FAIL**: Any gate fails OR any gate lacks hard evidence.

## Evidence Capture
Store and reference:
- RED session (initial failing state)
- GREEN session (target test suite passes)
- Regression session (adjacent suites still pass)
- Final closure memo with explicit GO/NO-GO decision

## Rollback
If any gate fails after a recent change:
1. Freeze external sharing.
2. Revert only the offending change set.
3. Re-run full gate suite.
4. Re-open sharing only when all gates are green again.

## Operator-facing Completion Format
Use this exact output structure in Telegram:
1. `status: GO` or `status: NO-GO`
2. `gates: <passed>/<total>`
3. `blocking_gate_ids: [...]` (empty if GO)
4. `evidence: <session_paths or artifact_paths>`
5. `next_action: <single deterministic action>`
