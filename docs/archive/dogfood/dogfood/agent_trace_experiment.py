#!/usr/bin/env python3
"""
Agent-Generated Trace Experiment

Protocol:
1. Agent A tries to fix a bug (Condition A) and FAILS
2. We extract Agent A's investigation as a "trace" 
3. Agent B gets the bug report + Agent A's trace
4. Does Agent B succeed more often than a fresh Agent A?

This tests whether Borg's ACTUAL product (agent-to-agent knowledge transfer)
works, not just developer-to-agent hints.
"""

# Agent A's investigation notes for django__django-10554 (consistently fails without trace)
AGENT_A_TRACE_10554 = """
AGENT INVESTIGATION NOTES (from a prior failed attempt):

I investigated this Django bug about Union querysets breaking when ordering 
is applied with derived querysets.

WHAT I FOUND:
- The bug is in django/db/models/query.py in the _combinator_query() method
- When union() is called, combined_queries stores REFERENCES to original Query objects
- When you later call .order_by().values_list() on the union result, it mutates the
  combined queries through these shared references
- The mutations (via set_values, get_order_by) corrupt the original querysets

WHERE TO LOOK:
- django/db/models/query.py, around line 930-940, the _combinator_query method
- The line: clone.query.combined_queries = (self.query,) + tuple(qs.query for qs in other_qs)
- This stores direct references instead of clones

WHAT I TRIED:
- I tried cloning the queries: clone.query.combined_queries = (self.query.clone(),) + tuple(...)
- This fixed one test but the ORDER BY position issue remained
- The compiler (django/db/models/sql/compiler.py) has get_order_by() that resolves
  ORDER BY positions — this may also need fixing when dealing with combined queries

WHAT DIDN'T WORK:
- Just cloning the queries in _combinator_query wasn't sufficient
- The ORDER BY handling in the compiler needs to account for value_list() narrowing
  the select clause

I ran out of iterations before finding the complete fix.
"""

# Agent A's investigation notes for django__django-13344 (consistently fails without trace)
AGENT_A_TRACE_13344 = """
AGENT INVESTIGATION NOTES (from a prior failed attempt):

I investigated the Django middleware coroutine bug where process_response() 
receives a coroutine instead of an HttpResponse when using ASGI.

WHAT I FOUND:
- The issue is in how MiddlewareMixin handles async middleware chains
- Several middleware subclasses override __init__ without calling super().__init__()
- This means _async_check() never runs on those middleware instances
- Without _async_check(), _is_coroutine is never set
- Django's ASGI handler then can't detect the middleware is async-capable

WHERE TO LOOK:
- django/utils/deprecation.py — MiddlewareMixin class, __acall__ method
- django/middleware/security.py — SecurityMiddleware.__init__
- django/middleware/cache.py — UpdateCacheMiddleware, FetchFromCacheMiddleware, CacheMiddleware
- Each of these overrides __init__ but doesn't call super().__init__(get_response)

WHAT I TRIED:
- I tried modifying __acall__ to await coroutines before passing to process_response
- This partially worked but the tests still showed 4 failures

WHAT DIDN'T WORK:
- Modifying __acall__ alone wasn't sufficient
- The root fix needs to be in the middleware subclasses' __init__ methods

I ran out of iterations before applying the fix to all middleware files.
"""

if __name__ == "__main__":
    import os
    
    # Save agent-generated traces
    os.makedirs("/tmp/agent_traces", exist_ok=True)
    
    with open("/tmp/agent_traces/10554_agent_trace.txt", "w") as f:
        f.write(AGENT_A_TRACE_10554)
    
    with open("/tmp/agent_traces/13344_agent_trace.txt", "w") as f:
        f.write(AGENT_A_TRACE_13344)
    
    print("Agent-generated traces saved to /tmp/agent_traces/")
    print("Ready for Condition C experiment (agent trace instead of developer trace)")
