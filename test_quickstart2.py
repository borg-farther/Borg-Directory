#!/usr/bin/env python3
"""Extended test script for guild-packs quickstart commands."""
import sys
import json
import subprocess
import os
import tempfile

sys.path.insert(0, '/root/hermes-workspace/guild-v2')

def run_guild_cmd(cmd_args):
    """Run guild command and return output."""
    result = subprocess.run(
        [sys.executable, '-c', f'''
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
from guild.cli import main
sys.argv = ['guild'] + {cmd_args!r}
main()
'''],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr, result.returncode

def run_mcp_cmd(messages):
    """Run MCP server with JSON-RPC messages."""
    proc = subprocess.Popen(
        [sys.executable, '-c', f'''
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
from guild.integrations.mcp_server import main
main()
'''],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    for msg in messages:
        proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()
    proc.stdin.close()
    stdout = proc.stdout.read().decode()
    proc.wait(timeout=10)
    return stdout

# Test: guild try
print("=== Testing: guild try ===")
stdout, stderr, rc = run_guild_cmd(['try', 'guild://hermes/systematic-debugging'])
print(f"stdout: {stdout[:1500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test: guild pull
print("\n=== Testing: guild pull ===")
stdout, stderr, rc = run_guild_cmd(['pull', 'guild://hermes/systematic-debugging'])
print(f"stdout: {stdout[:1500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test: guild list
print("\n=== Testing: guild list ===")
stdout, stderr, rc = run_guild_cmd(['list'])
print(f"stdout: {stdout[:1500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test MCP guild_search tool
print("\n=== Testing MCP: guild_search tool ===")
init_msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}
search_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
    "params": {"name": "guild_search", "arguments": {"query": "debugging"}}}
resp = run_mcp_cmd([init_msg, search_msg])
print(f"Response: {resp[:2000]}")

# Test MCP guild_try tool
print("\n=== Testing MCP: guild_try tool ===")
try_msg = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "guild_try", "arguments": {"uri": "guild://hermes/systematic-debugging"}}}
resp = run_mcp_cmd([init_msg, try_msg])
print(f"Response: {resp[:2000]}")

# Test convert - create a CLAUDE.md and convert it
print("\n=== Testing: guild convert ===")
with tempfile.TemporaryDirectory() as tmpdir:
    claude_md = os.path.join(tmpdir, "CLAUDE.md")
    with open(claude_md, "w") as f:
        f.write("""# CLAUDE.md
You are a code reviewer.

## Guidelines
- Check for security issues
- Check for performance issues
- Provide constructive feedback
""")
    stdout, stderr, rc = run_guild_cmd(['convert', claude_md])
    print(f"stdout: {stdout[:2000]}")
    print(f"stderr: {stderr[:500]}")
    print(f"returncode: {rc}")

# Test apply (should fail because task is required)
print("\n=== Testing: guild apply ===")
stdout, stderr, rc = run_guild_cmd(['apply', 'systematic-debugging', '--task', 'fix login bug'])
print(f"stdout: {stdout[:1500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")
