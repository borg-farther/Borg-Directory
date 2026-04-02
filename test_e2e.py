#!/usr/bin/env python
"""Test pack discovery: search, suggest, try."""
import json
import sys
sys.path.insert(0, '.')

from borg.core.search import borg_search, check_for_suggestion, borg_try

# Test 1: search
print("=== SEARCH ===")
r = borg_search('debugging')
d = json.loads(r)
print(f"  success: {d.get('success')}, matches: {len(d.get('matches', []))}")
for m in d.get('matches', [])[:3]:
    print(f"    - {m.get('name', m.get('id', '?'))}: tier={m.get('tier', '?')}, conf={m.get('confidence', '?')}")

# Test 2: suggest
print("\n=== SUGGEST ===")
r2 = check_for_suggestion('I keep getting TypeError and the test keeps failing', failure_count=3)
d2 = json.loads(r2)
print(f"  has_suggestion: {d2.get('has_suggestion')}, suggestions: {len(d2.get('suggestions', []))}")
for s in d2.get('suggestions', [])[:3]:
    print(f"    - {s.get('pack_name', '?')}: {s.get('why_relevant', '?')[:60]}")

# Test 3: try
print("\n=== TRY ===")
r3 = borg_try('borg://systematic-debugging')
d3 = json.loads(r3)
print(f"  success: {d3.get('success')}, pack: {d3.get('pack_name', 'none')}, phases: {d3.get('phase_count', '?')}")

# Test 4: MCP server via JSON-RPC
print("\n=== MCP SEARCH ===")
import borg.integrations.mcp_server as mcp
result = mcp.call_tool('borg_search', {'query': 'debugging', 'mode': 'text'})
d4 = json.loads(result)
print(f"  success: {d4.get('success')}, matches: {len(d4.get('matches', []))}")

print("\n=== DONE ===")
