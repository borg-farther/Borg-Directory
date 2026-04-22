# EXTERNAL_ROLLOUT_REPORT_20260421-1436

Generated at: 2026-04-21T14:57Z  
Working directory: `/root/hermes-workspace/borg`

## Command Execution Log

### 1) `python -m pytest tests/test_e2e_verify.py -k "call_tool_round_trip or convert_tolerates_stale_signature" -q`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
..                                                                       [100%]
2 passed, 19 deselected, 2 warnings in 11.44s
```

### 2) `python -m pytest -q eval/tests/test_distribution_runtime_canary.py eval/tests/test_distribution_channels_uat.py eval/tests/test_readiness_gates.py`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
...........                                                              [100%]
11 passed in 0.13s
```

### 3) `python eval/run_distribution_runtime_canary.py`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
{
  "generated_at": "2026-04-21T14:46:28.199730+00:00",
  "overall_pass": true,
  "checks": [
    {"name": "runtime_fingerprint_tool", "passed": true},
    {"name": "schema_declares_output_dir", "passed": true},
    {"name": "convert_openclaw_accepts_output_dir", "passed": true}
  ]
}
```

### 4) `python eval/run_distribution_channels_uat.py`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
{
  "generated_at": "2026-04-21T14:46:31.860031+00:00",
  "overall_pass": true,
  "success_rate": 1.0,
  "channels_covered": [
    "runtime_contract_canary",
    "cursor_rules",
    "cline_rules",
    "claude_cli_rules",
    "windsurf_rules",
    "openclaw_skill_distribution",
    "hermes_mcp_dispatch"
  ]
}
```

### 5) `python eval/run_readiness_gates.py`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
(no stdout/stderr emitted)
```

### 6) `python eval/uat_scoreboard.py`
- Exit code: `0`
- Output excerpt (stdout/stderr):
```text
/root/hermes-workspace/borg/PROJECT_STATUS.md
/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json
```

### 7) `borg publish list`
- Exit code: `1`
- Output excerpt (stdout/stderr):
```text
Error (publish failed): Artifact not found. Looked for: path=list, pack=, feedback=
{
  "success": false,
  "error": "Artifact not found. Looked for: path=list, pack=, feedback=",
  "hint": "Use borg_publish(action='list') to see available artifacts."
}
```

### 8) `borg publish systematic-debugging --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 9) `borg publish test-driven-development --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 10) `borg publish plan --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 11) `borg generate systematic-debugging all`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: all
```

### 12) `borg generate test-driven-development all`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: all
```

### 13) `borg generate plan all`
- Exit code: `2`
- Output excerpt (stdout/stderr):
```text
usage: borg [-h] [--version] {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start} ...
borg: error: unrecognized arguments: all
```

---

## Snapshot booleans and decision basis

### GO_NO_GO_DECISION.md (authoritative decision document)
- `Ready for 10 users: GO`
- `Ready for 100 users: GO`
- `Ready for 1000 users: GO`

### `eval/gate_run_snapshot.json`
- `all_pass: true`
- `ready_for_10: true`
- `ready_for_100: true`
- `ready_for_1000: true`

### `eval/distribution_runtime_canary_snapshot.json`
- `overall_pass: true`

### `eval/distribution_channels_uat_snapshot.json`
- `overall_pass: true`
- `success_rate: 1.0`

## Final GO/NO-GO

**GO** (based strictly on `GO_NO_GO_DECISION.md` and snapshot booleans, all true).

---

## Publish outcomes (exact errors)

- `borg publish list` failed with exact error:
  - `Error (publish failed): Artifact not found. Looked for: path=list, pack=, feedback=`
- `borg publish systematic-debugging --repo borg-farther/Borg-Directory` failed:
  - `borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory`
- `borg publish test-driven-development --repo borg-farther/Borg-Directory` failed:
  - `borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory`
- `borg publish plan --repo borg-farther/Borg-Directory` failed:
  - `borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory`

## Generated artifact file paths (from successful steps)

- `/root/hermes-workspace/borg/GO_NO_GO_DECISION.md`
- `/root/hermes-workspace/borg/PROJECT_STATUS.md`
- `/root/hermes-workspace/borg/eval/gate_run_snapshot.json`
- `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json`
- `/root/hermes-workspace/borg/eval/distribution_runtime_canary_snapshot.json`
- `/root/hermes-workspace/borg/eval/distribution_channels_uat_snapshot.json`

### Generate commands (11-13)
- No new generated rule artifacts were produced by commands 11-13 due CLI argument parsing failures (`unrecognized arguments: all`).
