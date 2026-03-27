#!/usr/bin/env python3
import ast, sys

# Check plugin syntax
with open("hermes-plugin/__init__.py") as f:
    src = f.read()
ast.parse(src)
print("hermes-plugin/__init__.py: syntax OK")

# Check plugin.yaml
import yaml
with open("hermes-plugin/plugin.yaml") as f:
    data = yaml.safe_load(f)
print(f"hermes-plugin/plugin.yaml: {data['name']} v{data['version']} YAML OK")

# Check agent_hook imports
sys.path.insert(0, ".")
from borg.integrations import agent_hook
print(f"guild_on_failure: {agent_hook.guild_on_failure.__doc__.strip().split(chr(10))[0]}")
print(f"guild_on_task_start: {agent_hook.guild_on_task_start.__doc__.strip().split(chr(10))[0]}")

print("\nAll checks passed.")
