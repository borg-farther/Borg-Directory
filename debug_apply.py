#!/usr/bin/env python
import json
import os
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

from borg.integrations import mcp_server as mcp_module

# Init
init_result = mcp_module.call_tool('borg_init', {
    'pack_name': 'wf-test-apply',
    'problem_class': 'reasoning',
})
print('Init:', init_result[:300])

# Start apply
start_result = mcp_module.call_tool('borg_apply', {
    'action': 'start',
    'pack_name': 'wf-test-apply',
    'task': 'Solve a reasoning problem',
})
print('Start:', start_result[:500])
