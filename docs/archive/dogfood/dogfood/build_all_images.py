#!/usr/bin/env python3
"""Build Docker images for all selected SWE-bench tasks."""
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
logger = logging.getLogger("build")

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
client = docker.from_env()

# Select 15 hard Django tasks, filtered for clean hints
tasks = []
for t in ds:
    if t["repo"] != "django/django":
        continue
    if t.get("difficulty") != "1-4 hours":
        continue
    hints = t.get("hints_text", "") or ""
    if "diff --git" in hints or "@@ -" in hints or "+++b/" in hints:
        print(f"SKIP {t['instance_id']}: hints contain patch diffs")
        continue
    if len(hints) < 50:
        print(f"SKIP {t['instance_id']}: hints too short ({len(hints)} chars)")
        continue
    tasks.append(t)

print(f"\n{len(tasks)} tasks to build")

# Build env images first (shared across tasks with same env)
specs = []
for t in tasks:
    spec = make_test_spec(t)
    specs.append((t, spec))

print("\nBuilding environment images...")
build_env_images(client, [s for _, s in specs], force_rebuild=False)
print("Environment images done.")

# Build instance images
results = {"success": [], "failed": []}
for t, spec in specs:
    tid = t["instance_id"]
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

print(f"\n\nRESULTS: {len(results['success'])} built, {len(results['failed'])} failed")
for tid in results["success"]:
    print(f"  OK: {tid}")
for f in results["failed"]:
    print(f"  FAIL: {f['id']}: {f['error'][:80]}")

with open("/root/hermes-workspace/borg/dogfood/v2_data/docker_build_results.json", "w") as f:
    json.dump(results, f, indent=2)
