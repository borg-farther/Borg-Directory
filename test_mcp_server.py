#!/usr/bin/env python3
"""
Smoke-test script for borg MCP server.
Sends JSON-RPC 2.0 requests via stdin/stdout pipe and verifies all 13 tools
return valid JSON with a 'success' field.
"""

import subprocess
import json
import sys
import os
import time

WORKSPACE = "/root/hermes-workspace/guild-v2"
SERVER_PATH = os.path.join(WORKSPACE, "borg/integrations/mcp_server.py")

TOOLS = [
    "borg_search",
    "borg_pull",
    "borg_try",
    "borg_observe",
    "borg_suggest",
    "borg_recall",
    "borg_context",
    "borg_publish",
    "borg_feedback",
    "borg_init",
    "borg_convert",
    "borg_reputation",
    "borg_apply",  # must be last — uses session state
]

RESULTS = []


def send_request(proc, method, params, req_id=1):
    """Send a JSON-RPC request and return the parsed response."""
    request = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params,
    }
    line = json.dumps(request) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()

    # Read response line
    resp_line = proc.stdout.readline()
    if not resp_line:
        return None, "No response received"
    try:
        return json.loads(resp_line.strip()), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"


def send_tool_call(proc, tool_name, arguments, req_id=1):
    """Send a tools/call request and return (result_text, error)."""
    request = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    line = json.dumps(request) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()

    resp_line = proc.stdout.readline()
    if not resp_line:
        return None, "No response received"
    try:
        resp = json.loads(resp_line.strip())
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON response: {e}"

    # Extract result content
    if "result" in resp:
        content = resp["result"].get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"], None
        return json.dumps(resp["result"]), None
    elif "error" in resp:
        return None, f"JSON-RPC error: {resp['error']}"
    return None, f"Unexpected response shape: {resp}"


def check_result_text(tool_name, result_text, error):
    """Check that result_text is valid JSON with a 'success' field."""
    if error:
        return False, error

    if not result_text:
        return False, "Empty result text"

    try:
        parsed = json.loads(result_text)
    except json.JSONDecodeError as e:
        return False, f"Result is not valid JSON: {e}"

    if "success" not in parsed:
        return False, f"No 'success' field in response: {list(parsed.keys())}"

    return True, None


def run_tests():
    # Start the MCP server
    proc = subprocess.Popen(
        [sys.executable, SERVER_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=WORKSPACE,  # workspace contains the borg/ package
        env={**os.environ, "PYTHONPATH": WORKSPACE},
        text=True,
        bufsize=1,
    )

    try:
        # Give server a moment to start
        time.sleep(0.3)

        # Send initialize
        resp, err = send_request(proc, "initialize", {}, req_id=0)
        if err or resp is None:
            print("FAIL: initialize failed:", err)
            return
        if resp.get("result", {}).get("serverInfo", {}).get("name") != "borg-mcp-server":
            print("FAIL: wrong server name in initialize response")
            return
        print("OK   initialize")

        # Send notifications/initialized (no response expected)
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        proc.stdin.write(json.dumps(notif) + "\n")
        proc.stdin.flush()

        # Send tools/list
        resp, err = send_request(proc, "tools/list", {}, req_id=0)
        if err or resp is None:
            print("FAIL: tools/list failed:", err)
            return
        tools_list = resp.get("result", {}).get("tools", [])
        print(f"OK   tools/list — {len(tools_list)} tools registered")

        # Test each tool
        for i, tool_name in enumerate(TOOLS):
            req_id = i + 1
            result_text = None
            error = None

            # Build minimal args for each tool
            if tool_name == "borg_search":
                args = {"query": "test"}
            elif tool_name == "borg_pull":
                args = {"uri": ""}  # empty — will return error but still valid JSON
            elif tool_name == "borg_try":
                args = {"uri": ""}
            elif tool_name == "borg_apply":
                args = {"action": ""}  # empty action — will return error but valid JSON
            elif tool_name == "borg_observe":
                args = {"task": "fix a bug in auth module"}
            elif tool_name == "borg_suggest":
                args = {"context": "TypeError: cannot import name 'auth' from 'django.contrib'"}
            elif tool_name == "borg_recall":
                args = {"error_message": "TypeError: 'NoneType' object has no attribute 'strip'"}
            elif tool_name == "borg_context":
                args = {"project_path": WORKSPACE, "hours": 1}
            elif tool_name == "borg_publish":
                args = {"action": "list"}
            elif tool_name == "borg_feedback":
                args = {"session_id": "test-nonexistent-session"}
            elif tool_name == "borg_init":
                args = {"pack_name": f"smoke-test-pack-{os.getpid()}"}
            elif tool_name == "borg_convert":
                args = {"path": "/nonexistent/file.md"}
            elif tool_name == "borg_reputation":
                args = {"action": "get_profile", "agent_id": "test-agent"}

            result_text, error = send_tool_call(proc, tool_name, args, req_id=req_id)
            ok, msg = check_result_text(tool_name, result_text, error)

            status = "PASS" if ok else "FAIL"
            display = result_text[:120] + "..." if result_text and len(result_text) > 120 else result_text
            print(f"{status} {tool_name}")
            if not ok:
                print(f"      Error: {msg}")
                if result_text:
                    print(f"      Response: {display}")
            elif result_text:
                # Try parsing and show success value
                try:
                    parsed = json.loads(result_text)
                    print(f"      success={parsed.get('success')} — {display}")
                except:
                    print(f"      {display}")

            RESULTS.append({
                "tool": tool_name,
                "ok": ok,
                "error": msg,
                "response_preview": display,
            })

    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
        proc.wait(timeout=10)


def main():
    print("=" * 60)
    print("BORG MCP SERVER SMOKE TEST")
    print("=" * 60)
    print()

    run_tests()

    print()
    print("=" * 60)
    passed = sum(1 for r in RESULTS if r["ok"])
    total = len(RESULTS)
    print(f"RESULTS: {passed}/{total} tools passed")
    print("=" * 60)

    for r in RESULTS:
        status = "PASS" if r["ok"] else "FAIL"
        print(f"  [{status}] {r['tool']}")
        if not r["ok"]:
            print(f"         → {r['error']}")

    # Write results to file
    output_path = os.path.join(WORKSPACE, "MCP_SMOKE_TEST_RESULTS.md")
    with open(output_path, "w") as f:
        f.write("# BORG MCP Server Smoke Test Results\n\n")
        f.write(f"**Date:** 2026-03-28\n\n")
        f.write(f"**Server:** `{SERVER_PATH}`\n\n")
        f.write(f"**Result:** {passed}/{total} tools passed\n\n")
        f.write("---\n\n")
        for r in RESULTS:
            status = "✅ PASS" if r["ok"] else "❌ FAIL"
            f.write(f"## {status}: `{r['tool']}`\n\n")
            if r["ok"]:
                f.write(f"Response preview: `{r['response_preview']}`\n\n")
            else:
                f.write(f"**Error:** {r['error']}\n\n")
                if r["response_preview"]:
                    f.write(f"**Response:** `{r['response_preview']}`\n\n")
            f.write("---\n\n")

    print(f"\nResults saved to: {output_path}")

    # Exit with error code if any test failed
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
