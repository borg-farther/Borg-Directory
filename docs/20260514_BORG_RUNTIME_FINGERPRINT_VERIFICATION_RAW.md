> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 20260514 Borg runtime fingerprint verification raw output

generated_at_utc: 2026-05-14T11:36:05Z
passed: True
json: `/root/hermes-workspace/borg/docs/repo-manifest/20260514_runtime_fingerprint_verification_raw.json`

## borg_pytest_confidence_runtime_first10

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `9.575`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -m pytest -q borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_runtime_fingerprint.py borg/tests/test_first_10_readiness.py
```

### stdout
```
...............................                                          [100%]
31 passed in 6.31s

```

### stderr
```

```

## hermes_plugin_guidance_filter_pytest

cwd: `/root/.hermes/hermes-agent`
returncode: `0`
duration_sec: `12.626`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -m pytest -q tests/test_borg_auto_trace_guidance_filter.py
```

### stdout
```
bringing up nodes...
bringing up nodes...

.........                                                                [100%]
9 passed in 12.02s

```

### stderr
```

```

## local_import_and_call_tool_fingerprint_smoke

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `0.058`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -c 
import json
from borg.core.runtime_fingerprint import runtime_fingerprint
from borg.integrations import mcp_server
fp = runtime_fingerprint()
print('LOCAL_FP_SUCCESS=', fp.get('success'))
print('LOCAL_FP_CANARY_PASSED=', fp.get('confidence_gate_canary', {}).get('passed'))
print('LOCAL_FP_RELOAD_STATUS=', fp.get('reload_status'))
print('LOCAL_FP_BORG_HOME=', fp.get('borg_home'))
print('LOCAL_FP_MCP_PATH=', fp.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))
print('LOCAL_FP_MCP_SHA256=', fp.get('modules', {}).get('borg.integrations.mcp_server', {}).get('sha256'))
print('LOCAL_FP_CONFIDENCE_PATH=', fp.get('modules', {}).get('borg.core.confidence_gate', {}).get('path'))
print('LOCAL_FP_CONFIDENCE_SHA256=', fp.get('modules', {}).get('borg.core.confidence_gate', {}).get('sha256'))
print('LOCAL_FP_RUNTIME_PATH=', fp.get('modules', {}).get('borg.core.runtime_fingerprint', {}).get('path'))
print('LOCAL_FP_RUNTIME_SHA256=', fp.get('modules', {}).get('borg.core.runtime_fingerprint', {}).get('sha256'))
parsed = json.loads(mcp_server.call_tool('borg_runtime_fingerprint', {}))
print('CALL_TOOL_SUCCESS=', parsed.get('success'))
print('CALL_TOOL_CANARY_PASSED=', parsed.get('confidence_gate_canary', {}).get('passed'))
print('CALL_TOOL_RELOAD_STATUS=', parsed.get('reload_status'))
print('CALL_TOOL_MCP_PATH=', parsed.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))
print('TOOL_SCHEMA_HAS_FP=', any(t.get('name') == 'borg_runtime_fingerprint' for t in mcp_server.TOOLS))

```

### stdout
```
LOCAL_FP_SUCCESS= True
LOCAL_FP_CANARY_PASSED= True
LOCAL_FP_RELOAD_STATUS= loaded_code_has_confidence_gate
LOCAL_FP_BORG_HOME= /root/.hermes/guild
LOCAL_FP_MCP_PATH= /root/hermes-workspace/borg/borg/integrations/mcp_server.py
LOCAL_FP_MCP_SHA256= 64c7c94b698098ac9b789aead3f17643887babfc101df70f88c522ce5694600f
LOCAL_FP_CONFIDENCE_PATH= /root/hermes-workspace/borg/borg/core/confidence_gate.py
LOCAL_FP_CONFIDENCE_SHA256= 76e8912a345d5912ed6c5b4b5014fb908d03a2d443f5cf7761ee6970bc5c6372
LOCAL_FP_RUNTIME_PATH= /root/hermes-workspace/borg/borg/core/runtime_fingerprint.py
LOCAL_FP_RUNTIME_SHA256= cd774ab9cbb0419ccc991b5ee987d47b129fec18792640d5588933f0e14b52a0
CALL_TOOL_SUCCESS= True
CALL_TOOL_CANARY_PASSED= True
CALL_TOOL_RELOAD_STATUS= loaded_code_has_confidence_gate
CALL_TOOL_MCP_PATH= /root/hermes-workspace/borg/borg/integrations/mcp_server.py
TOOL_SCHEMA_HAS_FP= True

```

### stderr
```

```

## needle_scan_all_known_paths

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `0.035`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -c 
from pathlib import Path
needles = ['borg_runtime_fingerprint', 'confidence_gate_canary', 'runtime_fingerprint_json']
paths = [
'/root/hermes-workspace/borg/borg/integrations/mcp_server.py',
'/usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py',
'/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py',
'/home/user/guild-tools/borg/integrations/mcp_server.py',
'/root/hermes-workspace/borg/borg/core/runtime_fingerprint.py',
'/usr/local/lib/python3.12/dist-packages/borg/core/runtime_fingerprint.py',
'/root/hermes-workspace/guild-v2/borg/core/runtime_fingerprint.py',
'/home/user/guild-tools/borg/core/runtime_fingerprint.py',
'/root/hermes-workspace/borg/build/lib/borg/core/runtime_fingerprint.py',
]
for p in paths:
    text = Path(p).read_text()
    print('NEEDLE', p, {n: (n in text) for n in needles}, 'bytes=', len(text))

```

### stdout
```
NEEDLE /root/hermes-workspace/borg/borg/integrations/mcp_server.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': False, 'runtime_fingerprint_json': True} bytes= 136117
NEEDLE /usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': False, 'runtime_fingerprint_json': True} bytes= 140009
NEEDLE /root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': False, 'runtime_fingerprint_json': True} bytes= 105780
NEEDLE /home/user/guild-tools/borg/integrations/mcp_server.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': False, 'runtime_fingerprint_json': True} bytes= 74755
NEEDLE /root/hermes-workspace/borg/borg/core/runtime_fingerprint.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': True, 'runtime_fingerprint_json': True} bytes= 5645
NEEDLE /usr/local/lib/python3.12/dist-packages/borg/core/runtime_fingerprint.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': True, 'runtime_fingerprint_json': True} bytes= 5645
NEEDLE /root/hermes-workspace/guild-v2/borg/core/runtime_fingerprint.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': True, 'runtime_fingerprint_json': True} bytes= 5645
NEEDLE /home/user/guild-tools/borg/core/runtime_fingerprint.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': True, 'runtime_fingerprint_json': True} bytes= 5645
NEEDLE /root/hermes-workspace/borg/build/lib/borg/core/runtime_fingerprint.py {'borg_runtime_fingerprint': True, 'confidence_gate_canary': True, 'runtime_fingerprint_json': True} bytes= 5645

```

### stderr
```

```

## fresh_stdio_mcp_fingerprint_canary

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `0.113`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -c 
import json, subprocess, sys
reqs = [
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
 {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'borg_runtime_fingerprint','arguments':{}}},
]
proc = subprocess.Popen([sys.executable, '-m', 'borg.integrations.mcp_server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdin = ''.join(json.dumps(r)+'\n' for r in reqs)
out, err = proc.communicate(stdin, timeout=25)
print('FRESH_MCP_EXIT=', proc.returncode)
print('FRESH_MCP_STDERR_START')
print(err)
print('FRESH_MCP_STDERR_END')
print('FRESH_MCP_STDOUT_START')
print(out)
print('FRESH_MCP_STDOUT_END')
for line in out.splitlines():
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('id') == 2:
        names = [t.get('name') for t in obj.get('result', {}).get('tools', [])]
        print('FRESH_MCP_SCHEMA_HAS_FP=', 'borg_runtime_fingerprint' in names)
    if obj.get('id') == 3:
        txt = obj.get('result', {}).get('content', [{}])[0].get('text', '')
        parsed = json.loads(txt)
        print('FRESH_MCP_CALL_SUCCESS=', parsed.get('success'))
        print('FRESH_MCP_CANARY_PASSED=', parsed.get('confidence_gate_canary', {}).get('passed'))
        print('FRESH_MCP_RELOAD_STATUS=', parsed.get('reload_status'))
        print('FRESH_MCP_PATH=', parsed.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))

```

### stdout
```
FRESH_MCP_EXIT= 0
FRESH_MCP_STDERR_START
borg-mcp-server v3.3.1 ready (stdio transport)

FRESH_MCP_STDERR_END
FRESH_MCP_STDOUT_START
{"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "borg-mcp-server", "version": "1.0.0"}, "capabilities": {"tools": {}}}}
{"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "borg_search", "description": "Search for borg workflow packs by keyword or semantic similarity. Searches local packs and the remote index. Returns matching packs with their metadata (name, problem class, tier, confidence). Use mode='semantic' or mode='hybrid' for semantic search when embeddings are available. When task_context is provided, uses the V3 contextual search path.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query (keywords to match against pack names, descriptions, problem classes). Empty returns all packs."}, "mode": {"type": "string", "enum": ["text", "semantic", "hybrid"], "description": "Search mode: 'text' for keyword matching, 'semantic' for vector similarity search, 'hybrid' for combined text + semantic. Defaults to 'text'.", "default": "text"}, "task_context": {"type": "object", "description": "V3 task context for contextual search. Keys: task_type (str), keywords (list of str), agent_id (str, optional).", "properties": {"task_type": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}, "agent_id": {"type": "string"}}}}, "required": ["query"]}}, {"name": "borg_pull", "description": "Fetch, validate, and store a borg pack locally. Downloads from URI, runs safety scan, and saves to ~/.hermes/guild/. Returns pack metadata and proof gate status.", "inputSchema": {"type": "object", "properties": {"uri": {"type": "string", "description": "Guild pack URI (guild://domain/name, https://..., or /local/path)"}}, "required": ["uri"]}}, {"name": "borg_try", "description": "Preview a borg workflow pack without saving it. Shows pack metadata, phases, proof gates, safety scan results, and trust tier. Use before guild_pull to check if a pack is worth adopting.", "inputSchema": {"type": "object", "properties": {"uri": {"type": "string", "description": "Guild pack URI (guild://domain/name, https://..., or /local/path)"}}, "required": ["uri"]}}, {"name": "borg_init", "description": "Scaffold a new borg workflow pack in the local borg directory. Creates the directory structure and a minimal pack.yaml template.", "inputSchema": {"type": "object", "properties": {"pack_name": {"type": "string", "description": "Unique name for the new pack (used as directory name)."}, "problem_class": {"type": "string", "description": "Problem class (e.g. classification, extraction, reasoning).", "default": "general"}, "mental_model": {"type": "string", "description": "Mental model (e.g. fast-thinker, slow-thinker).", "default": "fast-thinker"}}, "required": ["pack_name"]}}, {"name": "borg_apply", "description": "Execute a borg workflow pack with phase tracking. Multi-action: action='start' loads a pulled pack and returns an approval summary; action='checkpoint' logs a phase result (passed/failed); action='complete' finalizes and generates feedback.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["start", "checkpoint", "complete"], "description": "Action: start, checkpoint, or complete"}, "pack_name": {"type": "string", "description": "Name of the pack (must be pulled first, for action='start')"}, "task": {"type": "string", "description": "Task description \u2014 what you're applying the pack to (for action='start')"}, "session_id": {"type": "string", "description": "Active session ID from guild_apply_start (for checkpoint/complete)"}, "ab_test": {"type": "object", "description": "A/B test info if selected pack is a variant (for action='start')", "properties": {"test_id": {"type": "string"}, "variant": {"type": "string"}}}, "phase_name": {"type": "string", "description": "Phase name to checkpoint, or '__approval__' to approve execution (for action='checkpoint')"}, "status": {"type": "string", "enum": ["passed", "failed"], "description": "Checkpoint result (for action='checkpoint')"}, "evidence": {"type": "string", "description": "Evidence supporting the checkpoint result (optional, for action='checkpoint')"}, "outcome": {"type": "string", "description": "Final outcome description (optional, for action='complete')"}}, "required": ["action"]}}, {"name": "borg_publish", "description": "Publish a guild artifact (workflow pack or feedback) for validation and publishing. Validates proof gates and safety, then creates a GitHub PR. Falls back to local outbox if gh CLI is unavailable.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["list", "publish"], "description": "Action: 'list' to show available artifacts, 'publish' to publish one"}, "pack_name": {"type": "string", "description": "Name of the pack to publish (for action='publish')"}, "feedback_name": {"type": "string", "description": "Name of the feedback to publish (for action='publish')"}, "path": {"type": "string", "description": "Explicit path to artifact file (for action='publish')"}, "repo": {"type": "string", "description": "Target GitHub repo (defaults to <OLD_ACCT>/guild-packs)"}}, "required": ["action"]}}, {"name": "borg_feedback", "description": "Generate a feedback draft for a completed pack execution. Reads the execution session log and produces a structured feedback artifact. When task_context is provided, also records outcome to V3.", "inputSchema": {"type": "object", "properties": {"session_id": {"type": "string", "description": "Session ID of the completed pack execution."}, "what_changed": {"type": "string", "description": "Brief description of what changed in this execution vs. the original pack.", "default": ""}, "where_to_reuse": {"type": "string", "description": "Guidance on where this feedback can be reused.", "default": ""}, "success": {"type": "boolean", "description": "Whether the pack execution was successful (V3 parameter)."}, "tokens_used": {"type": "integer", "description": "Number of tokens used in the execution (V3 parameter)."}, "time_taken": {"type": "number", "description": "Time taken for the execution in seconds (V3 parameter)."}, "task_context": {"type": "object", "description": "V3 task context for outcome recording.", "properties": {"task_type": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}, "agent_id": {"type": "string"}}}}, "required": ["session_id"]}}, {"name": "borg_suggest", "description": "Auto-suggest a borg workflow pack based on frustration signals and task context. Triggers when failure_count >= 2 or when frustration keywords are detected. Searches borg packs by classified task terms and returns top matches.", "inputSchema": {"type": "object", "properties": {"context": {"type": "string", "description": "Recent conversation context (messages, errors, task description)."}, "failure_count": {"type": "integer", "description": "Number of consecutive failed attempts. Suggestion triggers at >= 2.", "default": 0}, "task_type_hint": {"type": "string", "description": "Optional explicit task type hint (e.g. 'debug', 'test', 'review')."}, "tried_packs": {"type": "array", "items": {"type": "string"}, "description": "List of pack names already tried (excluded from suggestions)."}}, "required": ["context"]}}, {"name": "borg_rescue", "description": "Agent-ready day-one rescue packet. Given an error, failing command output, or agent transcript, returns ACTION, STOP, VERIFY, human receipt, automation policy, and optional full guidance. Use this when the agent is about to debug or has hit a technical failure.", "inputSchema": {"type": "object", "properties": {"input": {"type": "string", "description": "Error, failing command output, task text, or recent agent transcript."}, "source": {"type": "string", "description": "Caller provenance tag (default: mcp).", "default": "mcp"}, "show_guidance": {"type": "boolean", "description": "Include full legacy guidance block (default: true).", "default": true}}, "required": ["input"]}}, {"name": "borg_first_10", "description": "Machine-readable first-10 beta readiness contract: seven gates, clean-user smoke path, agent priming paragraph, feedback fields, and GO/NO-GO success metric.", "inputSchema": {"type": "object", "properties": {}}}, {"name": "borg_runtime_fingerprint", "description": "Report the exact loaded Borg MCP runtime path, source hashes, BORG_HOME, process id, and a confidence-gate canary. Use this before any reload/cutover to prove what code the served process is actually running. It performs no restart and no mutation.", "inputSchema": {"type": "object", "properties": {}}}, {"name": "borg_observe", "description": "Silent observation: analyzes the current task and returns structural guidance from proven approaches. Call this at the start of any task to get battle-tested strategies. Returns specific phase-by-phase guidance if a relevant pack exists, or general best practices if not. Supports conditional phases: when context includes error_message, error_type, attempts, has_recent_changes, or error_in_test, skip_if/inject_if/context_prompts conditions are evaluated.", "inputSchema": {"type": "object", "properties": {"task": {"type": "string", "description": "Task description \u2014 what you're about to work on."}, "context": {"type": "string", "description": "Optional additional context (environment, language, constraints)."}, "context_dict": {"type": "object", "description": "Optional runtime context for conditional phase evaluation. Keys: error_message (str), error_type (str), attempts (int), has_recent_changes (bool), error_in_test (bool).", "properties": {"error_message": {"type": "string"}, "error_type": {"type": "string"}, "attempts": {"type": "integer"}, "has_recent_changes": {"type": "boolean"}, "error_in_test": {"type": "boolean"}}}, "project_path": {"type": "string", "description": "Optional path to the project directory for change awareness. If provided, cross-references the error with recently changed files."}}, "required": ["task"]}}, {"name": "borg_convert", "description": "Convert a SKILL.md, CLAUDE.md, or .cursorrules file into a borg workflow pack. Auto-detects format from filename or allows explicit format specification. Use format='openclaw' to convert the entire pack registry to OpenClaw skill format.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string", "description": "Path to the source file (SKILL.md, CLAUDE.md, or .cursorrules). Not needed for format='openclaw'."}, "format": {"type": "string", "enum": ["auto", "skill", "claude", "cursorrules", "openclaw"], "description": "Format of the source file. 'auto' detects from filename. 'openclaw' converts entire registry.", "default": "auto"}, "output_dir": {"type": "string", "description": "Output directory for OpenClaw conversion (default: ./openclaw-skills/). Only used when format='openclaw'."}}, "required": ["format"]}}, {"name": "borg_generate", "description": "Generate platform-specific rules files from a borg workflow pack. Takes a pack name or pack data and outputs rules in the specified format native to each AI IDE platform (Cursor, Cline, Claude Code, Windsurf).", "inputSchema": {"type": "object", "properties": {"pack": {"type": "string", "description": "Pack name (e.g. 'systematic-debugging') or pack identifier. The pack must be available in the local registry."}, "format": {"type": "string", "enum": ["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"], "description": "Output format. 'cursorrules' \u2192 .cursorrules (Cursor), 'clinerules' \u2192 .clinerules (Cline), 'claude-md' \u2192 CLAUDE.md (Claude Code), 'windsurfrules' \u2192 .windsurfrules (Windsurf), 'all' \u2192 all four formats at once.", "default": "cursorrules"}}, "required": ["pack", "format"]}}, {"name": "borg_generate", "description": "Generate platform-specific rules files from a borg workflow pack. Takes a pack name and outputs rules in the specified format native to each AI IDE platform (Cursor, Cline, Claude Code, Windsurf).", "inputSchema": {"type": "object", "properties": {"pack": {"type": "string", "description": "Pack name (e.g. 'systematic-debugging'). Must be available in local registry."}, "format": {"type": "string", "enum": ["cursorrules", "clinerules", "claude-md", "windsurfrules", "all"], "description": "Output format. 'cursorrules' -> .cursorrules (Cursor), 'clinerules' -> .clinerules (Cline), 'claude-md' -> CLAUDE.md (Claude Code), 'windsurfrules' -> .windsurfrules (Windsurf), 'all' -> all four formats at once.", "default": "cursorrules"}}, "required": ["pack", "format"]}}, {"name": "borg_context", "description": "Detect recent git changes in a project directory. Returns recently changed files, uncommitted changes, and recent commit messages. Use this to understand what changed in the codebase recently when debugging errors.", "inputSchema": {"type": "object", "properties": {"project_path": {"type": "string", "description": "Path to the git repository. Defaults to '.' (current directory).", "default": "."}, "hours": {"type": "integer", "description": "Look for changes in the last N hours. Defaults to 24.", "default": 24}}, "required": ["project_path"]}}, {"name": "borg_recall", "description": "Recall collective failure memory for an error. Returns approaches that other agents tried and failed, as well as approaches that succeeded. Use this before attempting a fix to avoid known wrong paths.", "inputSchema": {"type": "object", "properties": {"error_message": {"type": "string", "description": "The error message to look up in failure memory."}, "agent_id": {"type": "string", "description": "Agent namespace to search. Defaults to 'default'.", "default": "default"}}, "required": ["error_message"]}}, {"name": "borg_record_failure", "description": "Record a failure or success outcome for an error pattern in collective failure memory. This writes to the failure memory store so other agents can benefit from the learning. Call this after attempting a fix \u2014 record 'success' if it worked, 'failure' if it did not.", "inputSchema": {"type": "object", "properties": {"error_pattern": {"type": "string", "description": "The error message or pattern encountered (e.g. \"NoneType has no attribute 'split'\")."}, "pack_id": {"type": "string", "description": "The borg pack being used (e.g. 'systematic-debugging')."}, "phase": {"type": "string", "description": "The phase being executed when the error occurred (e.g. 'investigate_root_cause')."}, "approach": {"type": "string", "description": "What the agent tried to fix the error (e.g. 'Added if val is not None check')."}, "outcome": {"type": "string", "enum": ["success", "failure"], "description": "Result of the approach: 'success' or 'failure'."}, "agent_id": {"type": "string", "description": "Agent namespace to write to. Defaults to 'default'.", "default": "default"}}, "required": ["error_pattern", "pack_id", "phase", "approach", "outcome"]}}, {"name": "borg_delete_failure", "description": "Delete a failure memory record for an error pattern. Use this to retract wrong entries or clear test data. Returns success=True if deleted, success=True with found=False if not found.", "inputSchema": {"type": "object", "properties": {"error_pattern": {"type": "string", "description": "The error pattern whose record should be deleted."}, "agent_id": {"type": "string", "description": "Agent namespace to delete from. Defaults to 'default'.", "default": "default"}}, "required": ["error_pattern"]}}, {"name": "borg_reputation", "description": "Query agent reputation and trust information from the ReputationEngine. Provides access to contribution scores, access tiers, free-rider status, and pack trust. Use this to understand an agent's standing in the guild before consuming their packs.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["get_profile", "get_pack_trust", "get_free_rider_status"], "description": "Action to perform: 'get_profile' for agent reputation, 'get_pack_trust' for pack trust, 'get_free_rider_status' for free-rider info"}, "agent_id": {"type": "string", "description": "Agent ID to query (for get_profile and get_free_rider_status actions)."}, "pack_id": {"type": "string", "description": "Pack ID to query (for get_pack_trust action)."}}, "required": ["action"]}}, {"name": "borg_analytics", "description": "Query ecosystem health metrics and analytics from the AnalyticsEngine. Returns ecosystem-wide health, pack usage statistics, adoption metrics, and time-series data. Use this to understand the overall state of the guild ecosystem.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["ecosystem_health", "pack_usage", "adoption", "timeseries"], "description": "Action: 'ecosystem_health' for overall ecosystem metrics, 'pack_usage' for a specific pack's stats, 'adoption' for adoption metrics, 'timeseries' for time-series data."}, "pack_id": {"type": "string", "description": "Pack ID to query (for pack_usage and adoption actions)."}, "metric": {"type": "string", "description": "Metric name for timeseries action: 'pack_publishes', 'executions', 'avg_quality_score', or 'active_agents'."}, "period": {"type": "string", "description": "Time period for timeseries: 'daily', 'weekly', or 'monthly'. Defaults to 'daily'."}, "days": {"type": "integer", "description": "Number of days to look back for timeseries. Defaults to 30."}}, "required": ["action"]}}, {"name": "borg_dashboard", "description": "Query the Borg V3 dashboard \u2014 aggregated stats from the V3 outcomes database. Returns total outcomes, success rates, quality scores per pack, drift alerts, mutation stats, and A/B test status. Use this to monitor pack performance and system health.", "inputSchema": {"type": "object", "properties": {}}}, {"name": "borg_dojo", "description": "Borg Dojo \u2014 training improvement pipeline. Run session analysis, view learning curves, generate reports, and check system health. Actions: 'analyze' runs session analysis over the last N days; 'report' generates a formatted improvement report (cli, telegram, or discord format); 'history' shows the learning curve with historical snapshots; 'status' returns a quick health summary with error rates and weakest tools.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["analyze", "report", "history", "status"], "description": "Action to perform: 'analyze' runs session analysis, 'report' generates formatted report, 'history' shows learning curve, 'status' returns health summary."}, "days": {"type": "integer", "description": "Number of days to look back for analysis (default: 7).", "default": 7}, "report_format": {"type": "string", "enum": ["cli", "telegram", "discord"], "description": "Report format for 'report' action: 'cli', 'telegram', or 'discord'. Defaults to 'telegram'.", "default": "telegram"}}, "required": ["action"]}}, {"name": "borg_clusters", "description": "Discover problem clusters in Borg's trace database. Uses KMeans clustering when sklearn is available, keyword grouping as fallback. Finds: common failure patterns, related error types, recurring problems. Returns clusters with size, success/failure counts, root causes, and sample traces.", "inputSchema": {"type": "object", "properties": {"action": {"type": "string", "enum": ["discover", "detail", "by_technology"], "description": "'discover' finds problem clusters; 'detail' gets traces in a cluster; 'by_technology' groups by tech stack.", "default": "discover"}, "cluster_id": {"type": "string", "description": "Cluster ID for 'detail' action (e.g. 'cluster_0' or 'tech:python')."}, "n_clusters": {"type": "integer", "description": "Target number of clusters for 'discover' (default: 8).", "default": 8}, "min_trace_count": {"type": "integer", "description": "Minimum traces per cluster for 'discover' (default: 3).", "default": 3}}, "required": ["action"]}}]}}
{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "{\"borg_home\": \"/root/.hermes/guild\", \"borg_version\": \"3.3.1\", \"confidence_gate_canary\": {\"passed\": true, \"real_permission_positive_control_safe\": true, \"stale_guidance_stripped\": true, \"stale_permission_match\": false, \"stale_permission_safe\": false, \"synthetic_pack_safe\": false}, \"cwd\": \"/root/hermes-workspace/borg\", \"executable\": \"/root/.hermes/hermes-agent/venv/bin/python\", \"modules\": {\"borg\": {\"exists\": true, \"mtime\": 1777894092.9358246, \"mtime_iso_utc\": \"2026-05-04T11:28:12Z\", \"path\": \"/root/hermes-workspace/borg/borg/__init__.py\", \"sha256\": \"e96fdfa7cd6352a2df70a102a03bc091dd47c5d075895fd6c45e51193d299f15\", \"size\": 1862}, \"borg.core.confidence_gate\": {\"exists\": true, \"mtime\": 1778752458.7060368, \"mtime_iso_utc\": \"2026-05-14T09:54:18Z\", \"path\": \"/root/hermes-workspace/borg/borg/core/confidence_gate.py\", \"sha256\": \"76e8912a345d5912ed6c5b4b5014fb908d03a2d443f5cf7761ee6970bc5c6372\", \"size\": 6510}, \"borg.core.runtime_fingerprint\": {\"exists\": true, \"mtime\": 1778754569.1213543, \"mtime_iso_utc\": \"2026-05-14T10:29:29Z\", \"path\": \"/root/hermes-workspace/borg/borg/core/runtime_fingerprint.py\", \"sha256\": \"cd774ab9cbb0419ccc991b5ee987d47b129fec18792640d5588933f0e14b52a0\", \"size\": 5645}, \"borg.integrations.mcp_server\": {\"exists\": true, \"mtime\": 1778754599.319455, \"mtime_iso_utc\": \"2026-05-14T10:29:59Z\", \"path\": \"/root/hermes-workspace/borg/borg/integrations/mcp_server.py\", \"sha256\": \"64c7c94b698098ac9b789aead3f17643887babfc101df70f88c522ce5694600f\", \"size\": 136165}}, \"pid\": 99527, \"python\": \"3.11.15\", \"reload_status\": \"loaded_code_has_confidence_gate\", \"schema_version\": 1, \"success\": true, \"sys_path_head\": [\"/root/hermes-workspace/borg\", \"/root/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/lib/python311.zip\", \"/root/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/lib/python3.11\", \"/root/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/lib/python3.11/lib-dynload\", \"/root/.hermes/hermes-agent/venv/lib/python3.11/site-packages\", \"__editable__.hermes_agent-0.11.0.finder.__path_hook__\", \"/root/.hermes/hermes-agent/mini-swe-agent/src\", \"__editable__.tinker_atropos-0.1.0.finder.__path_hook__\"], \"tool\": \"borg_runtime_fingerprint\"}"}], "isError": false}}

FRESH_MCP_STDOUT_END
FRESH_MCP_SCHEMA_HAS_FP= True
FRESH_MCP_CALL_SUCCESS= True
FRESH_MCP_CANARY_PASSED= True
FRESH_MCP_RELOAD_STATUS= loaded_code_has_confidence_gate
FRESH_MCP_PATH= /root/hermes-workspace/borg/borg/integrations/mcp_server.py

```

### stderr
```

```

## no_loss_manifest_generation

cwd: `/root/hermes-workspace/borg`
returncode: `0`
duration_sec: `0.114`

### command
```
/root/.hermes/hermes-agent/venv/bin/python -c 
import json, subprocess, time
from pathlib import Path
root = Path('/root/hermes-workspace/borg')
proc = subprocess.run(['git','status','--porcelain=v1','-z'], cwd=root, capture_output=True, text=False)
raw = proc.stdout.decode('utf-8', 'replace')
entries = []
parts = [p for p in raw.split('\0') if p]
for item in parts:
    if len(item) < 4:
        continue
    status = item[:2]
    path = item[3:]
    p = path
    if p.startswith('build/lib/') or p.startswith('dist/') or p.endswith(('.egg-info', '.pyc')) or '/__pycache__/' in p:
        classification = 'generated_ignore'; reason = 'generated build/dist/cache artifact; not source of truth'
    elif p.startswith('docs/repo-manifest/'):
        classification = 'commit_doc'; reason = 'cleanup/source-of-truth audit artifact'
    elif p.startswith('docs/') or p in {'README.md','PROJECT_STATUS.md','GO_NO_GO_DECISION.md','LOAD_TEST_REPORT_10.md','LOAD_TEST_REPORT_100.md','LOAD_TEST_REPORT_1000.md','UAT_RESULTS.md'}:
        classification = 'commit_doc'; reason = 'documentation/readiness/proof artifact'
    elif p.startswith('borg/tests/') or p.startswith('eval/tests/') or '/tests/' in p:
        classification = 'commit_test'; reason = 'test coverage or verification artifact'
    elif p.startswith('borg/') or p.startswith('scripts/') or p.startswith('eval/') or p == 'pyproject.toml':
        classification = 'commit_product_code'; reason = 'product/runtime/eval source under canonical repo'
    elif p.startswith('tmp_'):
        classification = 'archive_readonly'; reason = 'temporary audit output; archive before possible deletion'
    else:
        classification = 'review_required'; reason = 'not matched by automatic classifier; human review required before deletion/commit'
    entries.append({'status': status, 'path': p, 'classification': classification, 'reason': reason})
summary = {}
for e in entries:
    summary[e['classification']] = summary.get(e['classification'], 0) + 1
manifest = {'schema_version': 1, 'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'repo': str(root), 'command': 'git status --porcelain=v1 -z', 'returncode': proc.returncode, 'policy': 'no deletion, move, or commit from this manifest alone; archive/diff first', 'summary': summary, 'entries': entries}
out = root / 'docs/repo-manifest/20260514_borg_no_loss_cleanup_manifest.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print('MANIFEST_PATH=', out)
print('GIT_STATUS_RETURN_CODE=', proc.returncode)
print('ENTRY_COUNT=', len(entries))
print('SUMMARY=', json.dumps(summary, sort_keys=True))
print('GIT_STATUS_STDERR=', proc.stderr.decode('utf-8', 'replace'))

```

### stdout
```
MANIFEST_PATH= /root/hermes-workspace/borg/docs/repo-manifest/20260514_borg_no_loss_cleanup_manifest.json
GIT_STATUS_RETURN_CODE= 0
ENTRY_COUNT= 250
SUMMARY= {"archive_readonly": 1, "commit_doc": 18, "commit_product_code": 22, "commit_test": 8, "generated_ignore": 201}
GIT_STATUS_STDERR= 

```

### stderr
```

```

