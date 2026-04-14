#!/usr/bin/env python3
"""Check failure memory for recent errors - detailed report."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.failure_memory import FailureMemory
from pathlib import Path
import yaml

# Check both __uat__ and __uat_backup__
for agent_id in ['__uat__', '__uat_backup__']:
    fm = FailureMemory(agent_id=agent_id)
    stats = fm.get_stats()
    print(f'Agent: {agent_id}')
    print(f'  Stats: {stats}')
    
    # Walk failures directory for this agent
    fail_dir = fm.memory_dir / agent_id
    if fail_dir.exists():
        for pack_dir in fail_dir.iterdir():
            if pack_dir.is_dir():
                for yfile in pack_dir.glob('*.yaml'):
                    data = yaml.safe_load(yfile.read_text())
                    if data.get('wrong_approaches'):
                        for wa in data['wrong_approaches']:
                            if wa.get('failure_count', 0) > 0:
                                print(f'  FAILURE: {data["error_pattern"][:50]} | pack={data["pack_id"]} | phase={data["phase"]} | approach={wa["approach"][:40]}')
print('=== TASK 4 DONE ===')
