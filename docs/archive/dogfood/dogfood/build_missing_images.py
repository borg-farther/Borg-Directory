#!/usr/bin/env python3
"""Build Docker images for tasks missing from the final selection."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import docker
import json
import time
import logging
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.docker_build import build_env_images, build_instance_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_missing")

# Tasks we still need
missing = [
    "django__django-11087",
    "django__django-11265",
    "django__django-12754",
    "django__django-13315",
    "django__django-15252",
    "django__django-15732",
    "django__django-16560",
]

# Check which are already built
client = docker.from_env()
existing = set()
for img in client.images.list():
    for tag in img.tags:
        if 'sweb.eval' in tag:
            # Extract task id from tag
            parts = tag.split('.')
            for p in parts:
                if 'django__django' in p:
                    tid = p.split(':')[0]
                    existing.add(tid)

still_missing = [t for t in missing if t not in existing]
print(f"Already built: {len(missing) - len(still_missing)}")
print(f"Still need: {len(still_missing)}")
for t in still_missing:
    print(f"  {t}")

if not still_missing:
    print("All images built!")
    sys.exit(0)

# Load dataset
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}

# Build
specs = []
for tid in still_missing:
    if tid in task_map:
        spec = make_test_spec(task_map[tid])
        specs.append((tid, spec))
    else:
        print(f"WARNING: {tid} not in dataset!")

print(f"\nBuilding env images...")
build_env_images(client, [s for _, s in specs], force_rebuild=False)
print("Env images done.")

results = {"success": [], "failed": []}
for tid, spec in specs:
    print(f"\nBuilding instance: {tid}...")
    start = time.time()
    try:
        build_instance_image(spec, client, logger=logger, nocache=False)
        elapsed = time.time() - start
        print(f"  OK ({elapsed:.0f}s)")
        results["success"].append(tid)
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED ({elapsed:.0f}s): {e}")
        results["failed"].append({"id": tid, "error": str(e)})

print(f"\nRESULTS: {len(results['success'])} built, {len(results['failed'])} failed")

with open("/root/hermes-workspace/borg/dogfood/v2_data/missing_build_results.json", "w") as f:
    json.dump(results, f, indent=2)
