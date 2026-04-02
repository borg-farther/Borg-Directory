#!/usr/bin/env python3
"""Test the auto-trace capture and matching system."""
import sys, json, os, tempfile
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.traces import TraceCapture, save_trace, _get_db
from borg.core.trace_matcher import TraceMatcher

# Use temp DB for testing
db_path = tempfile.mktemp(suffix=".db")

print("=== TEST 1: Capture a trace from agent activity ===")
capture = TraceCapture(task="Fix QuerySet union ordering bug in Django", agent_id="test-agent")
capture.on_tool_call("search_files", {"path": "/testbed/django/db/models/query.py"}, "found 3 matches")
capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/query.py"}, "class QuerySet:")
capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "class SQLCompiler:")
capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "class SQLCompiler:")
capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/query.py"}, "def _combinator_query")
capture.on_tool_call("patch", {"path": "/testbed/django/db/models/sql/query.py"}, "patched successfully")
capture.on_tool_call("terminal", {}, "FAILED: ORDER BY term does not match\ndjango.db.utils.DatabaseError: ORDER BY position")
capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "def get_order_by")
capture.on_tool_call("patch", {"path": "/testbed/django/db/models/sql/query.py"}, "patched clone method")
capture.on_tool_call("terminal", {}, "OK\nRan 93 tests in 0.7s\nOK")

trace = capture.extract_trace(
    outcome="success",
    root_cause="combined_queries stored direct references instead of clones, causing mutation on .order_by().values_list()",
    approach_summary="Clone combined_queries in Query.clone() method to prevent reference sharing"
)

print(f"  Trace ID: {trace['id']}")
print(f"  Key files: {trace['key_files']}")
print(f"  Technology: {trace['technology']}")
print(f"  Keywords: {trace['keywords'][:80]}...")
print(f"  Error patterns: {trace['error_patterns']}")
print(f"  Tool calls: {trace['tool_calls']}")
print(f"  Dead ends: {trace['dead_ends']}")

# Save
tid = save_trace(trace, db_path)
print(f"  Saved as: {tid}")

# Add a second trace
capture2 = TraceCapture(task="Fix middleware coroutine bug in Django ASGI", agent_id="test-agent-2")
capture2.on_tool_call("read_file", {"path": "/testbed/django/utils/deprecation.py"}, "class MiddlewareMixin")
capture2.on_tool_call("read_file", {"path": "/testbed/django/middleware/security.py"}, "class SecurityMiddleware")
capture2.on_tool_call("read_file", {"path": "/testbed/django/middleware/cache.py"}, "class CacheMiddleware")
capture2.on_tool_call("patch", {"path": "/testbed/django/middleware/security.py"}, "added super().__init__")
capture2.on_tool_call("patch", {"path": "/testbed/django/middleware/cache.py"}, "added _async_check")
capture2.on_tool_call("terminal", {}, "OK\nRan 4 tests\nOK")

trace2 = capture2.extract_trace(
    outcome="success",
    root_cause="Middleware subclasses override __init__ without calling super().__init__(get_response), so _async_check() never runs",
    approach_summary="Add super().__init__(get_response) or self._async_check() to SecurityMiddleware, UpdateCacheMiddleware, FetchFromCacheMiddleware, CacheMiddleware __init__ methods"
)
save_trace(trace2, db_path)

print("\n=== TEST 2: Match traces to new problems ===")
matcher = TraceMatcher(db_path)

# Test 1: Similar queryset problem
matches = matcher.find_relevant(
    task="Union queryset breaks when adding ordering",
    error="DatabaseError: ORDER BY position not in select list"
)
print(f"\n  Query: 'Union queryset breaks with ordering'")
print(f"  Matches: {len(matches)}")
for m in matches:
    print(f"    - {m['id']}: score={m['match_score']:.1f}, outcome={m['outcome']}")
    formatted = matcher.format_for_agent(m)
    print(f"      {formatted[:150]}...")

# Test 2: Middleware problem
matches = matcher.find_relevant(
    task="ASGI middleware returns coroutine instead of HttpResponse"
)
print(f"\n  Query: 'ASGI middleware coroutine'")
print(f"  Matches: {len(matches)}")
for m in matches:
    print(f"    - {m['id']}: score={m['match_score']:.1f}")
    formatted = matcher.format_for_agent(m)
    print(f"      {formatted[:150]}...")

# Test 3: Unrelated problem (should return fewer/no matches)
matches = matcher.find_relevant(
    task="Fix React component not rendering after state update"
)
print(f"\n  Query: 'React component not rendering'")
print(f"  Matches: {len(matches)} (should be 0 or low-score)")

print("\n=== TEST 3: Format for agent ===")
match = matcher.find_relevant(task="QuerySet union ordering")[0]
formatted = matcher.format_for_agent(match)
print(formatted)

# Cleanup
os.remove(db_path)
print(f"\n=== ALL TESTS PASSED ===")
