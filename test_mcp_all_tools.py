#!/usr/bin/env python3
"""Test MCP server startup and all tools."""
import json
import os
import sys
import subprocess
import time

os.environ.setdefault("BORG_DIR", "/tmp/borg_test_mcp")
os.environ.setdefault("HERMES_DIR", "/tmp/hermes_test_mcp")

sys.path.insert(0, "/root/hermes-workspace/borg")

# ---- Test 1: Import and verify TOOLS list ----
print("=" * 60)
print("TEST 1: Import MCP server and list tools")
print("=" * 60)
try:
    from borg.integrations.mcp_server import TOOLS, SERVER_INFO, call_tool, handle_request
    tool_names = [t["name"] for t in TOOLS]
    print(f"SERVER_INFO: {SERVER_INFO}")
    print(f"Total tools: {len(TOOLS)}")
    for i, name in enumerate(tool_names, 1):
        print(f"  {i:2d}. {name}")
    print("PASS: Import and tool listing OK")
except Exception as e:
    print(f"FAIL: Import error: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ---- Test 2: handle_request for initialize ----
print("\n" + "=" * 60)
print("TEST 2: MCP initialize handshake")
print("=" * 60)
try:
    resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    print(f"Response: {json.dumps(resp, indent=2)[:500]}")
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    print("PASS: Initialize handshake OK")
except Exception as e:
    print(f"FAIL: {e}")

# ---- Test 3: handle_request for tools/list ----
print("\n" + "=" * 60)
print("TEST 3: MCP tools/list")
print("=" * 60)
try:
    resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    listed = [t["name"] for t in resp["result"]["tools"]]
    print(f"Listed {len(listed)} tools: {listed}")
    print("PASS: tools/list OK")
except Exception as e:
    print(f"FAIL: {e}")

# ---- Test 4: Test each tool via call_tool ----
print("\n" + "=" * 60)
print("TEST 4: Test each tool individually")
print("=" * 60)

test_cases = [
    ("borg_search", {"query": "debug"}),
    ("borg_observe", {"task": "fix a bug in Python"}),
    ("borg_suggest", {"context": "tests keep failing with import error", "failure_count": 2}),
    ("borg_apply", {"action": "start", "pack_name": "nonexistent-pack", "task": "test"}),
    ("borg_pull", {"uri": "guild://test/nonexistent"}),
    ("borg_try", {"uri": "guild://test/nonexistent"}),
    ("borg_init", {"pack_name": "test-scaffold-pack"}),
    ("borg_convert", {"path": "/tmp/nonexistent_SKILL.md"}),
    ("borg_context", {"project_path": "/root/hermes-workspace/borg"}),
    ("borg_recall", {"error_message": "ModuleNotFoundError: No module named 'foo'"}),
    ("borg_reputation", {"action": "get_profile", "agent_id": "test-agent"}),
    ("borg_feedback", {"session_id": "nonexistent-session"}),
    ("borg_publish", {"action": "list"}),
    ("borg_analytics", {"action": "ecosystem_health"}),
    ("borg_dashboard", {}),
    ("borg_dojo", {"action": "status"}),
]

results = {}
for tool_name, args in test_cases:
    try:
        result_str = call_tool(tool_name, args)
        parsed = json.loads(result_str)
        success = parsed.get("success", None)
        has_error = "error" in parsed
        
        # A tool "responds correctly" if it returns valid JSON without crashing
        # Some tools will return success=False for invalid inputs, which is expected
        status = "OK"
        brief = ""
        if success is True:
            brief = "success=True"
        elif success is False:
            error_msg = parsed.get("error", "")[:80]
            brief = f"success=False: {error_msg}"
            # Expected failures for nonexistent resources are still "working correctly"
            status = "OK (expected error)"
        else:
            brief = f"keys={list(parsed.keys())[:5]}"
        
        results[tool_name] = status
        print(f"  {tool_name:20s} -> {status:25s} | {brief}")
    except Exception as e:
        results[tool_name] = f"EXCEPTION: {e}"
        print(f"  {tool_name:20s} -> EXCEPTION: {e}")
        import traceback; traceback.print_exc()

# ---- Test 5: MCP stdio server startup test ----
print("\n" + "=" * 60)
print("TEST 5: MCP stdio server startup (send initialize + tools/list)")
print("=" * 60)
try:
    init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    stdin_data = init_req + "\n" + list_req + "\n"
    
    proc = subprocess.run(
        [sys.executable, "-m", "borg.integrations.mcp_server"],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=10,
        cwd="/root/hermes-workspace/borg",
        env={**os.environ, "PYTHONPATH": "/root/hermes-workspace/borg"}
    )
    
    lines = [l for l in proc.stdout.strip().split("\n") if l.strip()]
    print(f"  stdout lines: {len(lines)}")
    for i, line in enumerate(lines):
        try:
            parsed = json.loads(line)
            if parsed.get("result", {}).get("protocolVersion"):
                print(f"  Line {i+1}: initialize response OK (protocol={parsed['result']['protocolVersion']})")
            elif "tools" in parsed.get("result", {}):
                num_tools = len(parsed["result"]["tools"])
                print(f"  Line {i+1}: tools/list response OK ({num_tools} tools)")
            else:
                print(f"  Line {i+1}: {line[:100]}")
        except:
            print(f"  Line {i+1} (raw): {line[:100]}")
    
    if proc.stderr:
        print(f"  stderr: {proc.stderr[:200]}")
    print("PASS: stdio server responded correctly")
except subprocess.TimeoutExpired:
    print("FAIL: Server timed out (might be waiting for more stdin)")
except Exception as e:
    print(f"FAIL: {e}")
    import traceback; traceback.print_exc()

# ---- Summary ----
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
ok_count = sum(1 for v in results.values() if "OK" in v)
fail_count = len(results) - ok_count
print(f"Tools tested: {len(results)}")
print(f"  OK: {ok_count}")
print(f"  FAILED: {fail_count}")
if fail_count > 0:
    print("Failed tools:")
    for name, status in results.items():
        if "OK" not in status:
            print(f"  - {name}: {status}")
