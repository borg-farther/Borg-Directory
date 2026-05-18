#!/usr/bin/env python3
"""Phase 2 A/B Experiment - Workspace Setup

Takes a task ID, builds/pulls SWE-bench Docker image, extracts testbed
to host directory (host-mount pipeline), applies test_patch, and
verifies the gold patch makes tests pass (pre-verification).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WORKSPACES_DIR = Path("/root/hermes-workspace/borg/dogfood/workspaces")
MANIFEST_PATH = Path(__file__).parent / "phase2_task_manifest.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def docker_image_name(instance_id: str) -> str:
    return f"sweb.eval.x86_64.{instance_id}:latest"


def load_task_from_manifest(instance_id: str) -> dict:
    """Load task entry from manifest JSON."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        for task in manifest["tasks"]:
            if task["instance_id"] == instance_id:
                return task
    return None


def load_task_from_hf(instance_id: str) -> dict:
    """Load full task data from HuggingFace dataset."""
    try:
        from datasets import load_dataset
        ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
        for row in ds:
            if row["instance_id"] == instance_id:
                return dict(row)
    except ImportError:
        pass
    return None


def ensure_docker_image(image_name: str) -> bool:
    """Check if Docker image exists, return True if available."""
    result = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True, timeout=30
    )
    if result.returncode == 0:
        print(f"Docker image {image_name} found locally.")
        return True
    
    # Try pulling (in case it's in a registry)
    print(f"Docker image {image_name} not found. Attempting to build...")
    print("NOTE: You may need to build the image using SWE-bench tooling:")
    print(f"  python -m swebench.harness.run_evaluation --instance_ids {image_name.split('.')[3].split(':')[0]}")
    return False


def extract_testbed(image_name: str, workspace_dir: Path) -> bool:
    """Extract /testbed from Docker image to host workspace directory."""
    testbed_dir = workspace_dir / "testbed"
    
    if testbed_dir.exists():
        print(f"Testbed already exists at {testbed_dir}, removing...")
        shutil.rmtree(testbed_dir)
    
    testbed_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary container and copy /testbed out
    container_name = f"swe_extract_{os.getpid()}"
    
    try:
        # Create container (don't start it)
        print(f"Creating container from {image_name}...")
        subprocess.run(
            ["docker", "create", "--name", container_name, image_name, "/bin/true"],
            check=True, capture_output=True, timeout=60
        )
        
        # Copy /testbed from container to host
        print(f"Extracting /testbed to {testbed_dir}...")
        subprocess.run(
            ["docker", "cp", f"{container_name}:/testbed/.", str(testbed_dir)],
            check=True, timeout=300
        )
        
        print(f"Testbed extracted successfully ({sum(1 for _ in testbed_dir.rglob('*'))} files)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR extracting testbed: {e}")
        print(f"stderr: {e.stderr.decode() if e.stderr else 'N/A'}")
        return False
    finally:
        # Remove temporary container
        subprocess.run(
            ["docker", "rm", container_name],
            capture_output=True, timeout=30
        )


def apply_patch(workspace_dir: Path, patch_content: str, patch_name: str = "patch") -> bool:
    """Apply a patch to the testbed directory."""
    testbed_dir = workspace_dir / "testbed"
    
    if not patch_content or not patch_content.strip():
        print(f"No {patch_name} to apply (empty).")
        return True
    
    # Write patch to temp file
    patch_file = workspace_dir / f"{patch_name}.diff"
    with open(patch_file, "w") as f:
        f.write(patch_content)
    
    # Apply with git apply
    print(f"Applying {patch_name}...")
    result = subprocess.run(
        ["git", "apply", "--verbose", str(patch_file)],
        cwd=str(testbed_dir),
        capture_output=True, timeout=60
    )
    
    if result.returncode != 0:
        # Try with patch command as fallback
        print(f"git apply failed, trying patch -p1...")
        result = subprocess.run(
            ["patch", "-p1", "-i", str(patch_file)],
            cwd=str(testbed_dir),
            capture_output=True, timeout=60
        )
    
    if result.returncode == 0:
        print(f"{patch_name} applied successfully.")
        return True
    else:
        print(f"ERROR applying {patch_name}:")
        print(f"stdout: {result.stdout.decode()}")
        print(f"stderr: {result.stderr.decode()}")
        return False


def run_tests_in_docker(image_name: str, workspace_dir: Path, test_specs: str, instance_id: str) -> bool:
    """Run FAIL_TO_PASS tests using docker run with host-mounted testbed."""
    testbed_dir = workspace_dir / "testbed"
    
    # Parse test specs
    if isinstance(test_specs, str):
        try:
            tests = json.loads(test_specs)
        except (json.JSONDecodeError, TypeError):
            tests = [test_specs] if test_specs else []
    else:
        tests = test_specs if test_specs else []
    
    if not tests:
        print("No FAIL_TO_PASS tests specified, skipping verification.")
        return True
    
    # Determine test runner based on repo
    repo = instance_id.rsplit("-", 1)[0]
    container_name = f"swe_verify_{os.getpid()}"
    
    all_passed = True
    for test in tests:
        print(f"Running test: {test}")
        
        if "django" in repo.lower():
            # Django test runner
            test_cmd = f"cd /testbed && python tests/runtests.py {test} --verbosity 2"
        elif "pytest" in str(test) or "::" in str(test):
            test_cmd = f"cd /testbed && python -m pytest {test} -xvs"
        else:
            # Generic: try pytest first
            test_cmd = f"cd /testbed && python -m pytest {test} -xvs"
        
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--name", container_name,
                "-v", f"{testbed_dir}:/testbed",
                image_name,
                "bash", "-c", test_cmd
            ],
            capture_output=True, timeout=300
        )
        
        if result.returncode != 0:
            print(f"  FAIL (exit code {result.returncode})")
            print(f"  stdout (last 20 lines): {chr(10).join(result.stdout.decode().split(chr(10))[-20:])}")
            print(f"  stderr (last 10 lines): {chr(10).join(result.stderr.decode().split(chr(10))[-10:])}")
            all_passed = False
        else:
            print(f"  PASS")
    
    return all_passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Set up workspace for a Phase 2 task")
    parser.add_argument("task_id", help="SWE-bench instance ID")
    parser.add_argument("--skip-verify", action="store_true", help="Skip gold patch verification")
    parser.add_argument("--workspace-dir", type=str, help="Override workspace directory")
    parser.add_argument("--manifest", type=str, default=str(MANIFEST_PATH), help="Manifest JSON path")
    args = parser.parse_args()

    instance_id = args.task_id
    image_name = docker_image_name(instance_id)
    workspace_dir = Path(args.workspace_dir) if args.workspace_dir else WORKSPACES_DIR / instance_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    print(f"=" * 60)
    print(f"Setting up workspace for: {instance_id}")
    print(f"Docker image: {image_name}")
    print(f"Workspace: {workspace_dir}")
    print(f"=" * 60)

    # Step 1: Ensure Docker image
    if not ensure_docker_image(image_name):
        print("ABORT: Docker image not available.")
        sys.exit(1)

    # Step 2: Load full task data (need patches)
    print("\nLoading task data...")
    task_data = load_task_from_hf(instance_id)
    if not task_data:
        print("ERROR: Could not load task data from HuggingFace.")
        sys.exit(1)
    
    # Save task data for reference
    with open(workspace_dir / "task_data.json", "w") as f:
        json.dump({k: v for k, v in task_data.items() if isinstance(v, (str, int, float, bool, list))}, f, indent=2)

    # Step 3: Extract testbed
    print("\nExtracting testbed...")
    if not extract_testbed(image_name, workspace_dir):
        print("ABORT: Failed to extract testbed.")
        sys.exit(1)

    # Step 4: Apply test_patch
    test_patch = task_data.get("test_patch", "")
    if test_patch:
        print("\nApplying test_patch...")
        if not apply_patch(workspace_dir, test_patch, "test_patch"):
            print("WARNING: test_patch application failed.")
    
    # Step 5: Pre-verification with gold patch
    if not args.skip_verify:
        print("\n--- Pre-verification: applying gold patch and running tests ---")
        gold_patch = task_data.get("patch", "")
        
        if gold_patch:
            if not apply_patch(workspace_dir, gold_patch, "gold_patch"):
                print("ABORT: Gold patch application failed.")
                sys.exit(1)
            
            fail_to_pass = task_data.get("FAIL_TO_PASS", "")
            passed = run_tests_in_docker(image_name, workspace_dir, fail_to_pass, instance_id)
            
            if passed:
                print("\nPre-verification PASSED: Gold patch makes tests pass.")
            else:
                print("\nWARNING: Pre-verification FAILED: Gold patch did not make all tests pass.")
                print("This task may have environment issues.")
            
            # Revert gold patch for actual experiment
            print("\nReverting gold patch (restoring clean testbed with test_patch only)...")
            # Re-extract and re-apply test patch
            extract_testbed(image_name, workspace_dir)
            if test_patch:
                apply_patch(workspace_dir, test_patch, "test_patch")
        else:
            print("No gold patch available, skipping verification.")
    
    # Write setup status
    status = {
        "instance_id": instance_id,
        "workspace_dir": str(workspace_dir),
        "docker_image": image_name,
        "setup_complete": True,
        "testbed_dir": str(workspace_dir / "testbed"),
    }
    with open(workspace_dir / "setup_status.json", "w") as f:
        json.dump(status, f, indent=2)
    
    print(f"\nWorkspace setup complete: {workspace_dir}")
    print(f"Testbed at: {workspace_dir / 'testbed'}")


if __name__ == "__main__":
    main()
