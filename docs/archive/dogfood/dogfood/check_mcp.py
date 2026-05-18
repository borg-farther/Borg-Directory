#!/usr/bin/env python3
try:
    from borg.integrations.mcp_server import BorgMCPServer
    s = BorgMCPServer()
    tools = [t.name for t in s.tools] if hasattr(s, 'tools') else dir(s)
    print(f"MCP Server OK: {len(tools)} tools")
    for t in tools:
        if not t.startswith('_'):
            print(f"  - {t}")
except Exception as e:
    print(f"MCP Server FAILED: {e}")
    import traceback
    traceback.print_exc()
