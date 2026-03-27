#!/usr/bin/env python3
"""Test script for guild-packs quickstart commands."""
import sys
import json
import subprocess

sys.path.insert(0, '/root/hermes-workspace/guild-v2')

def run_guild_cmd(cmd_args):
    """Run guild command and return output."""
    result = subprocess.run(
        [sys.executable, '-c', f'''
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
from borg.cli import main
sys.argv = ['guild'] + {cmd_args!r}
main()
'''],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr, result.returncode

# Test: guild --help
print("=== Testing: guild --help ===")
stdout, stderr, rc = run_guild_cmd(['--help'])
print(f"stdout: {stdout[:500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test: guild version
print("\n=== Testing: guild version ===")
stdout, stderr, rc = run_guild_cmd(['version'])
print(f"stdout: {stdout[:500]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test: guild search
print("\n=== Testing: guild search ===")
stdout, stderr, rc = run_guild_cmd(['search', 'debugging'])
print(f"stdout: {stdout[:1000]}")
print(f"stderr: {stderr[:500]}")
print(f"returncode: {rc}")

# Test MCP server
print("\n=== Testing MCP server ===")
mcp_proc = subprocess.Popen(
    [sys.executable, '-c', f'''
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
from borg.integrations.mcp_server import main
main()
'''],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
init_msg = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
}) + "\n"
tools_msg = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
mcp_proc.stdin.write(init_msg.encode())
mcp_proc.stdin.write(tools_msg.encode())
mcp_proc.stdin.flush()
mcp_proc.stdin.close()
stdout = mcp_proc.stdout.read().decode()
print(f"MCP responses:\n{stdout[:2000]}")
mcp_proc.wait(timeout=5)
