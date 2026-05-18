#!/usr/bin/env python3
"""Phase 2 A/B Experiment - Task Selector

Loads SWE-bench Verified, filters for Docker-available tasks,
excludes prior pilot Django tasks, stratifies by difficulty/repo,
selects 30 tasks in counterbalanced blocks, outputs manifest JSON.
"""

import json
import os
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PILOT_EXCLUDE = {
    "django__django-10554",
    "django__django-11087",
    "django__django-11138",
    "django__django-11265",
    "django__django-11400",
    "django__django-12708",
    "django__django-12754",
    "django__django-13315",
    "django__django-13344",
    "django__django-13212",
}

NUM_TASKS = 30
BLOCK_SIZE = 6  # 5 blocks of 6 => 30 tasks; each block balanced A-first/B-first
SEED = 42
OUTPUT_PATH = Path(__file__).parent / "phase2_task_manifest.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_swebench_verified():
    """Load SWE-bench Verified from HuggingFace datasets library."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' package not installed. Install with: pip install datasets")
        sys.exit(1)

    print("Loading SWE-bench Verified from HuggingFace...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    return list(ds)


def docker_image_name(instance_id: str) -> str:
    """Derive the expected SWE-bench Docker image name."""
    return f"sweb.eval.x86_64.{instance_id}:latest"


def check_docker_image_exists(image_name: str) -> bool:
    """Check if Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def estimate_difficulty(task: dict) -> str:
    """Heuristic difficulty estimate based on patch size and test count.
    
    Categories: easy, medium, hard
    """
    patch = task.get("patch", "")
    patch_lines = len(patch.strip().split("\n")) if patch else 0
    
    fail_to_pass = task.get("FAIL_TO_PASS", "")
    if isinstance(fail_to_pass, str):
        try:
            ftests = json.loads(fail_to_pass)
        except (json.JSONDecodeError, TypeError):
            ftests = [fail_to_pass] if fail_to_pass else []
    else:
        ftests = fail_to_pass if fail_to_pass else []
    
    num_tests = len(ftests)
    
    # Simple heuristic: small patches with few tests = easy
    if patch_lines <= 15 and num_tests <= 2:
        return "easy"
    elif patch_lines <= 50 and num_tests <= 5:
        return "medium"
    else:
        return "hard"


def get_repo(instance_id: str) -> str:
    """Extract repo name from instance_id (e.g., 'django__django-11087' -> 'django__django')."""
    parts = instance_id.rsplit("-", 1)
    return parts[0] if len(parts) == 2 else instance_id


def select_stratified(candidates: list, n: int, rng: random.Random) -> list:
    """Select n tasks stratified by difficulty and repo.
    
    Strategy: bucket by (repo, difficulty), sample proportionally,
    fill remainder randomly.
    """
    # Group by repo x difficulty
    buckets = defaultdict(list)
    for t in candidates:
        key = (get_repo(t["instance_id"]), t["_difficulty"])
        buckets[key].append(t)
    
    # Sort buckets by size descending for proportional sampling
    bucket_keys = sorted(buckets.keys(), key=lambda k: len(buckets[k]), reverse=True)
    
    selected = []
    selected_ids = set()
    
    # First pass: take at least 1 from each bucket (up to n)
    for key in bucket_keys:
        if len(selected) >= n:
            break
        pick = rng.choice(buckets[key])
        selected.append(pick)
        selected_ids.add(pick["instance_id"])
    
    # Second pass: fill remaining proportionally
    remaining_pool = [t for t in candidates if t["instance_id"] not in selected_ids]
    rng.shuffle(remaining_pool)
    
    while len(selected) < n and remaining_pool:
        selected.append(remaining_pool.pop())
    
    return selected[:n]


def assign_counterbalanced_blocks(tasks: list, block_size: int, rng: random.Random) -> list:
    """Assign tasks to counterbalanced blocks.
    
    Each block has block_size tasks. Within a block, half get A-first order,
    half get B-first order. Both conditions run on every task (within-subjects).
    """
    rng.shuffle(tasks)
    
    manifest = []
    block_num = 0
    
    for i in range(0, len(tasks), block_size):
        block_tasks = tasks[i:i + block_size]
        block_num += 1
        
        # Within block, first half = A-first, second half = B-first
        mid = len(block_tasks) // 2
        
        for j, task in enumerate(block_tasks):
            first_condition = "A" if j < mid else "B"
            second_condition = "B" if j < mid else "A"
            
            entry = {
                "instance_id": task["instance_id"],
                "repo": get_repo(task["instance_id"]),
                "difficulty": task["_difficulty"],
                "block": block_num,
                "run_order": [first_condition, second_condition],
                "docker_image": docker_image_name(task["instance_id"]),
                "patch_lines": len(task.get("patch", "").strip().split("\n")),
                "fail_to_pass": task.get("FAIL_TO_PASS", ""),
                "pass_to_pass": task.get("PASS_TO_PASS", ""),
            }
            manifest.append(entry)
    
    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Select tasks for Phase 2 A/B experiment")
    parser.add_argument("--num-tasks", type=int, default=NUM_TASKS, help="Number of tasks to select")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed")
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH), help="Output manifest path")
    parser.add_argument("--check-docker", action="store_true", help="Only include tasks with Docker images available locally")
    parser.add_argument("--docker-available-file", type=str, help="File listing available Docker images (one per line)")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Load dataset
    tasks = load_swebench_verified()
    print(f"Loaded {len(tasks)} tasks from SWE-bench Verified")

    # Exclude pilot tasks
    tasks = [t for t in tasks if t["instance_id"] not in PILOT_EXCLUDE]
    print(f"After excluding pilot tasks: {len(tasks)}")

    # Optionally filter by Docker availability
    if args.docker_available_file:
        with open(args.docker_available_file) as f:
            available = {line.strip() for line in f if line.strip()}
        tasks = [t for t in tasks if docker_image_name(t["instance_id"]) in available]
        print(f"After Docker image filter (from file): {len(tasks)}")
    elif args.check_docker:
        print("Checking Docker image availability (this may take a while)...")
        tasks = [t for t in tasks if check_docker_image_exists(docker_image_name(t["instance_id"]))]
        print(f"After Docker image filter: {len(tasks)}")

    if len(tasks) < args.num_tasks:
        print(f"WARNING: Only {len(tasks)} tasks available, need {args.num_tasks}")
        args.num_tasks = len(tasks)

    # Add difficulty estimates
    for t in tasks:
        t["_difficulty"] = estimate_difficulty(t)

    # Difficulty distribution
    diff_counts = defaultdict(int)
    for t in tasks:
        diff_counts[t["_difficulty"]] += 1
    print(f"Difficulty distribution: {dict(diff_counts)}")

    # Repo distribution
    repo_counts = defaultdict(int)
    for t in tasks:
        repo_counts[get_repo(t["instance_id"])] += 1
    print(f"Top repos: {dict(sorted(repo_counts.items(), key=lambda x: -x[1])[:10])}")

    # Select stratified sample
    selected = select_stratified(tasks, args.num_tasks, rng)
    print(f"Selected {len(selected)} tasks")

    # Assign counterbalanced blocks
    manifest = assign_counterbalanced_blocks(selected, BLOCK_SIZE, rng)

    # Summary
    print(f"\nManifest summary:")
    print(f"  Total tasks: {len(manifest)}")
    blocks = set(e["block"] for e in manifest)
    print(f"  Blocks: {len(blocks)}")
    a_first = sum(1 for e in manifest if e["run_order"][0] == "A")
    b_first = sum(1 for e in manifest if e["run_order"][0] == "B")
    print(f"  A-first: {a_first}, B-first: {b_first}")
    
    diff_sel = defaultdict(int)
    for e in manifest:
        diff_sel[e["difficulty"]] += 1
    print(f"  Difficulty: {dict(diff_sel)}")

    repo_sel = defaultdict(int)
    for e in manifest:
        repo_sel[e["repo"]] += 1
    print(f"  Repos: {dict(repo_sel)}")

    # Write manifest
    output_data = {
        "experiment": "phase2_borg_ab",
        "seed": args.seed,
        "num_tasks": len(manifest),
        "block_size": BLOCK_SIZE,
        "tasks": manifest,
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nManifest written to {args.output}")


if __name__ == "__main__":
    main()
