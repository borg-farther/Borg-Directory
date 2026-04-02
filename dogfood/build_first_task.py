#!/usr/bin/env python3
"""Build env + instance images for a single SWE-bench task."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import docker
import logging
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.docker_build import build_env_images, build_instance_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("swebench_build")

# Load one task
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task = None
for t in ds:
    if t["instance_id"] == "django__django-16631":  # SECRET_KEY_FALLBACKS
        task = t
        break

if not task:
    print("Task not found!")
    sys.exit(1)

print(f"Task: {task['instance_id']}")
spec = make_test_spec(task)
print(f"Env image: {spec.env_image_key}")
print(f"Instance image: {spec.instance_image_key}")

client = docker.from_env()

# Step 1: Build environment image
print("\nBuilding environment image...")
try:
    build_env_images(client, [spec], force_rebuild=False)
    print("Environment image built!")
except Exception as e:
    print(f"Error building env image: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Build instance image
print("\nBuilding instance image...")
try:
    build_instance_image(spec, client, logger=logger, nocache=False)
    print("Instance image built!")
except Exception as e:
    print(f"Error building instance image: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test — start container and verify tests fail
print("\nStarting test container...")
try:
    container = client.containers.run(
        spec.instance_image_key,
        "bash -c 'cd /testbed && python -m pytest tests/sessions_tests/tests.py::SessionPatchTests::test_session_load_does_not_create_record -x --no-header -q 2>&1; echo EXIT:$?'",
        detach=False,
        remove=True,
        mem_limit="4g",
    )
    print(f"Test output: {container.decode()[:500]}")
except Exception as e:
    print(f"Error running tests: {e}")

print("\nDone!")
