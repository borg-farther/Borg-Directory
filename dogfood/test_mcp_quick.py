#!/usr/bin/env python3
"""Quick MCP tool test."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
sys.path.insert(0, '/root/hermes-workspace/borg')
import json
from borg.integrations.mcp_server import call_tool

# Test borg_observe with correct param name
print("=== borg_observe ===")
result = call_tool("borg_observe", {"task": "Fix a failing test in Django auth module"})
print(f"  Type: {type(result)}")
print(f"  Length: {len(result) if result else 0}")
print(f"  Content: {result[:200] if result else '(empty)'}")

print("\n=== borg_suggest ===")
result = call_tool("borg_suggest", {"context": "I keep getting ImportError after 3 attempts"})
parsed = json.loads(result)
print(f"  Success: {parsed.get('success')}")
if parsed.get('suggestion'):
    print(f"  Suggestion: {parsed['suggestion'][:200]}")
else:
    print(f"  Keys: {list(parsed.keys())}")

print("\n=== borg_apply ===")
result = call_tool("borg_apply", {"action": "start", "pack_name": "systematic-debugging", "task": "Fix auth bug"})
parsed = json.loads(result)
print(f"  Success: {parsed.get('success')}")
print(f"  Session: {parsed.get('session_id', 'none')}")
print(f"  Phase: {parsed.get('current_phase', 'none')}")
