#!/usr/bin/env python3
"""Test all MCP tools to verify they work before user onboarding."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

import json

# Import the MCP handler directly
sys.path.insert(0, '/root/hermes-workspace/borg')
from borg.integrations.mcp_server import call_tool, TOOLS

print(f"MCP Server has {len(TOOLS)} tools:")
for t in TOOLS:
    print(f"  - {t['name']}")

print("\n" + "=" * 50)
print("TESTING EACH TOOL:")
print("=" * 50)

tests = [
    ("borg_search", {"query": "debugging"}),
    ("borg_search", {"query": "fix TypeError"}),
    ("borg_search", {"query": "error"}),
    ("borg_suggest", {"context": "I've been trying to fix this bug for 3 attempts and keep failing"}),
    ("borg_observe", {"task_description": "Fix a failing test in Django auth module"}),
    ("borg_try", {"uri": "systematic-debugging"}),
    ("borg_convert", {"source_path": "/root/hermes-workspace/borg/QUICKSTART.md"}),
]

results = []
for tool_name, args in tests:
    try:
        result = call_tool(tool_name, args)
        data = json.loads(result) if isinstance(result, str) else result
        success = data.get("success", False) if isinstance(data, dict) else bool(data)
        
        # Check if it returned meaningful content
        if isinstance(data, dict):
            has_content = bool(data.get("matches") or data.get("pack") or data.get("suggestion") or data.get("guidance") or data.get("yaml"))
        else:
            has_content = bool(data)
        
        status = "PASS" if success else "WARN" if has_content else "FAIL"
        detail = ""
        if isinstance(data, dict):
            if "matches" in data:
                detail = f"{len(data['matches'])} matches"
            elif "error" in data:
                detail = data["error"][:80]
            elif "pack" in data:
                detail = f"pack preview OK"
            elif "suggestion" in data:
                detail = data["suggestion"][:80] if data["suggestion"] else "empty suggestion"
        
        results.append((tool_name, args.get("query") or args.get("context", "")[:30] or args.get("task_description", "")[:30] or args.get("uri", ""), status, detail))
        print(f"  {status}: {tool_name}({list(args.values())[0][:40]}...) → {detail}")
        
    except Exception as e:
        results.append((tool_name, str(args)[:30], "ERROR", str(e)[:80]))
        print(f"  ERROR: {tool_name} → {e}")

print(f"\n{'='*50}")
passed = sum(1 for _, _, s, _ in results if s == "PASS")
warned = sum(1 for _, _, s, _ in results if s == "WARN")
failed = sum(1 for _, _, s, _ in results if s in ("FAIL", "ERROR"))
print(f"Results: {passed} PASS, {warned} WARN, {failed} FAIL out of {len(results)}")
