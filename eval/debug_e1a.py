#!/usr/bin/env python3
"""Debug script to understand E1a matching"""
import json
import yaml
from pathlib import Path

# Check migration-state-desync pack
pack_file = Path("/root/hermes-workspace/borg/skills/migration-state-desync.md")
text = pack_file.read_text()
yaml_text = text[3:text.find('\n---')]
data = yaml.safe_load(yaml_text)
print('Pack ID:', data.get('id'))
print('problem_class:', data.get('problem_class'))
print('investigation_trail:', data.get('investigation_trail'))

# Check django__django-12754 task
task_file = Path("/root/hermes-workspace/borg/dogfood/swebench_experiment/django__django-12754/task_data.json")
task = json.loads(task_file.read_text())
print('\nTask instance_id:', task.get('instance_id'))
print('problem_statement (first 200 chars):', task.get('problem_statement', '')[:200])
print('patch (first 300 chars):', task.get('patch', '')[:300])