#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

from borg.integrations import mcp_server as mcp_module

print('Testing call_tool for borg_init...')
try:
    result = mcp_module.call_tool('borg_init', {'pack_name': 'test', 'problem_class': 'reasoning'})
    print(f'Result: {result}')
except Exception as e:
    print(f'Error: {e}')

print()
print('Looking for guild_ in mcp_module...')
for name in dir(mcp_module):
    if 'guild' in name.lower():
        print(f'  {name}')