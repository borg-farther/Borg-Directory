#!/usr/bin/env python3
"""Build Docker images for expansion tasks."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import docker, json, time, logging
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.docker_build import build_env_images, build_instance_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_expansion")

with open("/root/hermes-workspace/borg/dogfood/v2_data/expansion_tasks.json") as f:
    task_ids = json.load(f)["tasks"]

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}
client = docker.from_env()

specs = []
for tid in task_ids:
    task = task_map[tid]
    spec = make_test_spec(task)
    specs.append((tid, spec))

print(f"Building env images for {len(specs)} tasks...")
build_env_images(client, [s for _, s in specs], force_rebuild=False)
print("Env images done.")

results = {"success": [], "failed": []}
for tid, spec in specs:
    print(f"\nBuilding: {tid}...")
    start = time.time()
    try:
        build_instance_image(spec, client, logger=logger, nocache=False)
        print(f"  OK ({time.time()-start:.0f}s)")
        results["success"].append(tid)
    except Exception as e:
        print(f"  FAILED: {e}")
        results["failed"].append(tid)

print(f"\nRESULTS: {len(results['success'])} built, {len(results['failed'])} failed")
with open("/root/hermes-workspace/borg/dogfood/v2_data/expansion_build_results.json", "w") as f:
    json.dump(results, f, indent=2)
