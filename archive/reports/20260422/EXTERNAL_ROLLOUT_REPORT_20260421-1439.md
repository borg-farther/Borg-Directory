# EXTERNAL_ROLLOUT_REPORT_20260421-1439

- Generated at (UTC): 2026-04-21T15:19:36.969911Z
- Run start (UTC): 2026-04-21T15:09:04.251216Z
- Logs directory: `/root/hermes-workspace/borg/eval/rollout_logs_20260421_1439`

## Command execution

### 1) `cd /root/hermes-workspace/borg && python -m pytest tests/test_e2e_verify.py -k "call_tool_round_trip or convert_tolerates_stale_signature" -q`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
..                                                                       [100%]
=============================== warnings summary ===============================
tests/test_e2e_verify.py::TestSystemHealth::test_call_tool_round_trip
  <frozen importlib._bootstrap>:488: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

tests/test_e2e_verify.py::TestSystemHealth::test_call_tool_round_trip
  <frozen importlib._bootstrap>:488: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 19 deselected, 2 warnings in 9.95s
```

### 2) `cd /root/hermes-workspace/borg && python -m pytest -q eval/tests/test_distribution_runtime_canary.py eval/tests/test_distribution_channels_uat.py eval/tests/test_readiness_gates.py`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
...........                                                              [100%]
11 passed in 0.11s
```

### 3) `cd /root/hermes-workspace/borg && python eval/run_distribution_runtime_canary.py`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
{
  "generated_at": "2026-04-21T15:09:18.121683+00:00",
  "overall_pass": true,
  "checks": [
    {
      "name": "runtime_fingerprint_tool",
      "passed": true,
      "details": "success=True error="
    },
    {
      "name": "schema_declares_output_dir",
      "passed": true,
      "details": "schema_has_output_dir=True"
    },
    {
      "name": "convert_openclaw_accepts_output_dir",
      "passed": true,
      "details": "success=True error="
    }
  ],
  "fingerprint": {
    "success": true,
    "package_version": "3.3.2",
    "module_path": "/root/hermes-workspace/borg/borg/integrations/mcp_server.py",
    "module_sha256": "cd152dcc13ccf2fb7e9f00da457bfa29b702c342724ec865a8619332abc4f077",
    "schema_sha256": "6964b8df3672fdcd16fffbd21118993ae7051f3a92043c36605898ee94ef9e74",
    "pid": 2669075,
    "process_start_ts": "2026-04-21T15:09:17.800987+00:00",
    "python_version": "3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]",
    "platform": "Linux-6.8.0-106-generic-x86_64-with-glibc2.39",
    "tool_count": 21
  },
  "convert_probe": {
    "success": true,
    "pack_count": 36,
    "output_dir": "/tmp/borg-runtime-canary-49w4q_s0/skills",
    "files_written": 36,
    "skill_md_lines": 116,
    "pack_slugs": [
      "quick-debug",
      "test-pack-xyz",
      "systematic-debugging",
      "my-test-e2e-pack",
      "my-skill",
      "fresh-pack",
      "test-driven-development",
      "smoke-test-pack-686293",
      "wf-test-apply",
      "test-call-tool",
      "plan",
      "smoke-test-pack-686891",
      "my-test-pack2",
      "my-pack",
      "smoke-test-pack-686695",
      "old-pack",
      "my-first-pack",
      "test-scaffold-pack",
      "code-review",
      "github-repo-management",
      "plan-rubric",
      "github-issues",
      "code-review-rubric",
      "jupyter-live-kernel",
      "ascii-art",
      "codebase-inspection",
      "requesting-code-review",
      "systematic-debugging-rubric",
      "subagent-driven-development",
      "github-auth",
      "github-pr-workflow",
      "writing-plans",
      "github-code-review",
      "excalidraw"
    ]
  }
}
```

### 4) `cd /root/hermes-workspace/borg && python eval/run_distribution_channels_uat.py`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
{
  "generated_at": "2026-04-21T15:09:18.893762+00:00",
  "overall_pass": true,
  "success_rate": 1.0,
  "threshold": {
    "required_success_rate": 1.0
  },
  "channels_covered": [
    "runtime_contract_canary",
    "cursor_rules",
    "cline_rules",
    "claude_cli_rules",
    "windsurf_rules",
    "openclaw_skill_distribution",
    "hermes_mcp_dispatch"
  ],
  "checks": [
    {
      "name": "distribution_runtime_canary",
      "passed": true,
      "details": "overall_pass=True generated_at=2026-04-21T15:09:18.121683+00:00"
    },
    {
      "name": "mcp_generate_all_formats",
      "passed": true,
      "details": "success=True keys=['.clinerules', '.cursorrules', '.windsurfrules', 'CLAUDE.md']"
    },
    {
      "name": "generator_api_all_formats",
      "passed": true,
      "details": "type=dict keys=['claude-md', 'clinerules', 'cursorrules', 'windsurfrules']"
    },
    {
      "name": "mcp_convert_openclaw",
      "passed": true,
      "details": "success=True error="
    },
    {
      "name": "mcp_dispatch_convert_openclaw",
      "passed": true,
      "details": "success=True error="
    },
    {
      "name": "openclaw_output_structure",
      "passed": true,
      "details": "output_dir=/tmp/borg-openclaw-uat-k3t576wg/openclaw-skills skill_md=True pack_index=True ref_count=34"
    },
    {
      "name": "local_pack_corpus_available",
      "passed": true,
      "details": "pack_count=8"
    }
  ]
}
```

### 5) `cd /root/hermes-workspace/borg && python eval/run_readiness_gates.py`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
[no output]
```

### 6) `cd /root/hermes-workspace/borg && python eval/uat_scoreboard.py`
- Exit code: `0`
- Stdout/stderr excerpt:
```text
/root/hermes-workspace/borg/PROJECT_STATUS.md
/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json
```

### 7) `cd /root/hermes-workspace/borg && borg publish list`
- Exit code: `1`
- Stdout/stderr excerpt:
```text
{
  "success": false,
  "error": "Artifact not found. Looked for: path=list, pack=, feedback=",
  "hint": "Use borg_publish(action='list') to see available artifacts."
}

Error (publish failed): Artifact not found. Looked for: path=list, pack=, feedback=
```

### 8) `cd /root/hermes-workspace/borg && borg publish systematic-debugging --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 9) `cd /root/hermes-workspace/borg && borg publish test-driven-development --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 10) `cd /root/hermes-workspace/borg && borg publish plan --repo borg-farther/Borg-Directory`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory
```

### 11) `cd /root/hermes-workspace/borg && borg generate systematic-debugging all`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: all
```

### 12) `cd /root/hermes-workspace/borg && borg generate test-driven-development all`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: all
```

### 13) `cd /root/hermes-workspace/borg && borg generate plan all`
- Exit code: `2`
- Stdout/stderr excerpt:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: all
```

## Final GO/NO-GO

- Verdict from `GO_NO_GO_DECISION.md`: **GO**
- Evidence line: `- Ready for 10 users: GO`
- Snapshot booleans:
  - `/root/hermes-workspace/borg/eval/distribution_channels_uat_snapshot.json.overall_pass` = `true`
  - `/root/hermes-workspace/borg/eval/distribution_runtime_canary_snapshot.json.overall_pass` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.scoreboard_gates.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.scoreboard_gates.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/gate_run_snapshot.json.scoreboard_gates.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.scoreboard_gates.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.scoreboard_gates.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/readiness_summary_latest.json.scoreboard_gates.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.derived.gate_ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.derived.gate_ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.derived.gate_ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.distribution_channels_uat_snapshot.payload.overall_pass` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.distribution_runtime_canary_snapshot.payload.overall_pass` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.scoreboard_gates.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.scoreboard_gates.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.execution_snapshots.snapshots.gate_run_snapshot.payload.scoreboard_gates.ready_for_1000` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.gates.ready_for_10` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.gates.ready_for_100` = `true`
  - `/root/hermes-workspace/borg/eval/uat_scoreboard_snapshot.json.gates.ready_for_1000` = `true`

## Publish outcomes

- `cd /root/hermes-workspace/borg && borg publish list` -> exit `1` (failure)
  - Exact error text:
```text
Error (publish failed): Artifact not found. Looked for: path=list, pack=, feedback=

```
- `cd /root/hermes-workspace/borg && borg publish systematic-debugging --repo borg-farther/Borg-Directory` -> exit `2` (failure)
  - Exact error text:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory

```
- `cd /root/hermes-workspace/borg && borg publish test-driven-development --repo borg-farther/Borg-Directory` -> exit `2` (failure)
  - Exact error text:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory

```
- `cd /root/hermes-workspace/borg && borg publish plan --repo borg-farther/Borg-Directory` -> exit `2` (failure)
  - Exact error text:
```text
usage: borg [-h] [--version]
            {search,pull,try,init,apply,publish,feedback,feedback-v3,debug,recall,convert,generate,list,observe,version,autopilot,setup-claude,setup-cursor,start}
            ...
borg: error: unrecognized arguments: --repo borg-farther/Borg-Directory

```

## Generated artifact file paths

- [none detected]

## Concise summary

- Executed 13 commands in order; failed commands: [7, 8, 9, 10, 11, 12, 13].
- Final decision: **GO**.
