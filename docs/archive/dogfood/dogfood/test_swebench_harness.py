#!/usr/bin/env python3
"""Test if we can use swebench to set up a single task environment."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

from swebench.harness.test_spec.test_spec import TestSpec, make_test_spec
from swebench.harness.constants import SWEbenchInstance
from datasets import load_dataset
import json

# Load one task
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

# Find a Django task
task = None
for t in ds:
    if t["repo"] == "django/django" and t.get("difficulty") == "15 min - 1 hour":
        task = t
        break

print(f"Task: {task['instance_id']}")
print(f"Version: {task.get('version')}")

# Try to create a test spec
try:
    spec = make_test_spec(task)
    print(f"Test spec created: {type(spec)}")
    print(f"Docker image: {spec.instance_image_key if hasattr(spec, 'instance_image_key') else 'N/A'}")
    print(f"Env script: {spec.env_script_list[:200] if hasattr(spec, 'env_script_list') else 'N/A'}")
except Exception as e:
    print(f"Error creating test spec: {e}")
    import traceback
    traceback.print_exc()
