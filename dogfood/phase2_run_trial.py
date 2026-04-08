#!/usr/bin/env python3
"""Phase 2 A/B Experiment - Trial Runner

Takes task_id, condition (A or B), vps_ip.
SSHs to VPS and runs agent with appropriate prompt.
Condition A: baseline (no Borg tools)
Condition B: with Borg tools
Captures outcome and secondary metrics, records to results JSON.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESULTS_PATH = Path(__file__).parent / "phase2_results.json"
MANIFEST_PATH = Path(__file__).parent / "phase2_task_manifest.json"
WORKSPACES_DIR = Path("/root/hermes-workspace/borg/dogfood/workspaces")

SSH_KEY = os.environ.get("SSH_KEY_PATH", "~/.ssh/id_rsa")
SSH_USER = os.environ.get("SSH_USER", "root")
SSH_TIMEOUT = 1800  # 30 min per trial

# Agent prompts
PROMPT_CONDITION_A = """You are a software engineering agent. You must fix a failing test in this repository.

Repository: {repo}
Task: {instance_id}

The failing test(s) are:
{fail_to_pass}

The testbed is at /testbed. Investigate the failing test(s), understand the bug, and write a fix.
Do NOT modify the test files. Only modify source code to make the failing tests pass
while keeping existing passing tests working.

You have standard tools: file reading, editing, terminal access.
"""

PROMPT_CONDITION_B = """You are a software engineering agent. You must fix a failing test in this repository.

Repository: {repo}
Task: {instance_id}

The failing test(s) are:
{fail_to_pass}

The testbed is at /testbed. Investigate the failing test(s), understand the bug, and write a fix.
Do NOT modify the test files. Only modify source code to make the failing tests pass
while keeping existing passing tests working.

You have standard tools: file reading, editing, terminal access.
Additionally, you have access to Borg memory tools that let you search for similar
previously-solved issues and retrieve relevant context. Use borg_search to find
similar past fixes, and borg_recall to retrieve detailed context about specific
past solutions. These can help you understand patterns and find the right approach faster.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_results() -> dict:
    """Load existing results or create new."""
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            return json.load(f)
    return {
        "experiment": "phase2_borg_ab",
        "started": datetime.now(timezone.utc).isoformat(),
        "trials": []
    }


def save_results(results: dict):
    """Save results to JSON."""
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)


def load_task_from_manifest(instance_id: str) -> dict:
    """Load task entry from manifest."""
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    for task in manifest["tasks"]:
        if task["instance_id"] == instance_id:
            return task
    return None


def docker_image_name(instance_id: str) -> str:
    return f"sweb.eval.x86_64.{instance_id}:latest"


def build_agent_command(task_id: str, condition: str, workspace_dir: str) -> str:
    """Build the command to run the agent on the VPS."""
    # This constructs the agent invocation command
    # Adjust based on actual agent CLI
    if condition == "A":
        borg_flag = "--no-borg"
    else:
        borg_flag = "--with-borg"
    
    cmd = (
        f"cd {workspace_dir} && "
        f"timeout {SSH_TIMEOUT} python3 -m agent.run "
        f"--task-id {task_id} "
        f"--testbed {workspace_dir}/testbed "
        f"{borg_flag} "
        f"2>&1"
    )
    return cmd


def run_trial_ssh(task_id: str, condition: str, vps_ip: str,
                  workspace_dir: Path, task_info: dict) -> dict:
    """Run a trial by SSHing to VPS and executing the agent."""
    
    repo = task_info.get("repo", task_id.rsplit("-", 1)[0])
    fail_to_pass = task_info.get("fail_to_pass", "")
    image_name = docker_image_name(task_id)
    
    # Build prompt
    if condition == "A":
        prompt = PROMPT_CONDITION_A.format(
            repo=repo, instance_id=task_id, fail_to_pass=fail_to_pass
        )
    else:
        prompt = PROMPT_CONDITION_B.format(
            repo=repo, instance_id=task_id, fail_to_pass=fail_to_pass
        )
    
    # Save prompt to workspace
    prompt_file = workspace_dir / f"prompt_{condition}.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)
    
    trial_result = {
        "task_id": task_id,
        "condition": condition,
        "vps_ip": vps_ip,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "outcome": None,  # PASS or FAIL
        "exit_code": None,
        "duration_seconds": None,
        "agent_log": None,
        "error": None,
        # Secondary metrics
        "num_edits": None,
        "num_tool_calls": None,
        "tokens_used": None,
        "borg_queries": None,  # Only for condition B
        "files_modified": [],
    }
    
    start_time = time.time()
    
    try:
        # SSH command to run agent on VPS
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=30",
            "-i", os.path.expanduser(SSH_KEY),
            f"{SSH_USER}@{vps_ip}",
            build_agent_command(task_id, condition, str(workspace_dir))
        ]
        
        print(f"Running trial: {task_id} condition={condition} on {vps_ip}")
        print(f"SSH command: {' '.join(ssh_cmd)}")
        
        # For now, if VPS is localhost, run directly
        if vps_ip in ("localhost", "127.0.0.1"):
            agent_cmd = build_agent_command(task_id, condition, str(workspace_dir))
            result = subprocess.run(
                ["bash", "-c", agent_cmd],
                capture_output=True, timeout=SSH_TIMEOUT,
                cwd=str(workspace_dir)
            )
        else:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True, timeout=SSH_TIMEOUT + 60  # extra buffer
            )
        
        end_time = time.time()
        trial_result["exit_code"] = result.returncode
        trial_result["duration_seconds"] = round(end_time - start_time, 2)
        trial_result["agent_log"] = result.stdout.decode()[-5000:]  # Last 5k chars
        
        if result.returncode != 0:
            trial_result["error"] = result.stderr.decode()[-2000:]
        
    except subprocess.TimeoutExpired:
        trial_result["error"] = f"Timeout after {SSH_TIMEOUT}s"
        trial_result["duration_seconds"] = SSH_TIMEOUT
    except Exception as e:
        trial_result["error"] = str(e)
    
    trial_result["end_time"] = datetime.now(timezone.utc).isoformat()
    
    # Run evaluation: check if FAIL_TO_PASS tests now pass
    print("Evaluating result...")
    trial_result["outcome"] = evaluate_trial(task_id, workspace_dir, fail_to_pass, image_name)
    
    # Extract secondary metrics from agent log
    extract_secondary_metrics(trial_result)
    
    return trial_result


def evaluate_trial(task_id: str, workspace_dir: Path, fail_to_pass: str, image_name: str) -> str:
    """Evaluate whether the agent's changes make the failing tests pass."""
    testbed_dir = workspace_dir / "testbed"
    
    if isinstance(fail_to_pass, str):
        try:
            tests = json.loads(fail_to_pass)
        except (json.JSONDecodeError, TypeError):
            tests = [fail_to_pass] if fail_to_pass else []
    else:
        tests = fail_to_pass if fail_to_pass else []
    
    if not tests:
        return "UNKNOWN"
    
    repo = task_id.rsplit("-", 1)[0]
    
    for test in tests:
        if "django" in repo.lower():
            test_cmd = f"cd /testbed && python tests/runtests.py {test} --verbosity 2"
        elif "::" in test:
            test_cmd = f"cd /testbed && python -m pytest {test} -xvs"
        else:
            test_cmd = f"cd /testbed && python -m pytest {test} -xvs"
        
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{testbed_dir}:/testbed",
                    image_name,
                    "bash", "-c", test_cmd
                ],
                capture_output=True, timeout=300
            )
            
            if result.returncode != 0:
                print(f"  Test FAIL: {test}")
                return "FAIL"
            else:
                print(f"  Test PASS: {test}")
        except subprocess.TimeoutExpired:
            print(f"  Test TIMEOUT: {test}")
            return "FAIL"
        except Exception as e:
            print(f"  Test ERROR: {test}: {e}")
            return "ERROR"
    
    return "PASS"


def extract_secondary_metrics(trial_result: dict):
    """Extract secondary metrics from agent log."""
    log = trial_result.get("agent_log", "") or ""
    
    # Count tool calls (heuristic: look for common patterns)
    trial_result["num_tool_calls"] = log.count("Tool call:") + log.count("tool_use")
    
    # Count edits
    trial_result["num_edits"] = log.count("file_edit") + log.count("write_file") + log.count("patch")
    
    # Count borg queries (condition B only)
    if trial_result["condition"] == "B":
        trial_result["borg_queries"] = log.count("borg_search") + log.count("borg_recall")
    
    # Try to find files modified
    # Look for common patterns in agent logs
    import re
    files = re.findall(r'(?:Editing|Modified|Writing|Patching)\s+(?:file\s+)?["\']?([^\s"\']+\.\w+)', log)
    trial_result["files_modified"] = list(set(files))


def run_trial_local(task_id: str, condition: str, workspace_dir: Path, task_info: dict) -> dict:
    """Run trial locally (for testing without SSH)."""
    print(f"LOCAL TRIAL: {task_id} condition={condition}")
    print("This is a dry-run. In production, this would invoke the agent.")
    
    return {
        "task_id": task_id,
        "condition": condition,
        "vps_ip": "localhost",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "outcome": "DRY_RUN",
        "exit_code": None,
        "duration_seconds": 0,
        "agent_log": "Dry run - no agent invoked",
        "error": None,
        "num_edits": 0,
        "num_tool_calls": 0,
        "tokens_used": 0,
        "borg_queries": 0 if condition == "B" else None,
        "files_modified": [],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run a Phase 2 A/B trial")
    parser.add_argument("task_id", help="SWE-bench instance ID")
    parser.add_argument("condition", choices=["A", "B"], help="Experiment condition (A=baseline, B=borg)")
    parser.add_argument("vps_ip", help="VPS IP address (or 'localhost' for local)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually run agent")
    parser.add_argument("--results-file", type=str, default=str(RESULTS_PATH))
    args = parser.parse_args()

    # Load manifest task info
    task_info = load_task_from_manifest(args.task_id)
    if not task_info:
        print(f"WARNING: Task {args.task_id} not found in manifest, using defaults.")
        task_info = {"instance_id": args.task_id, "repo": args.task_id.rsplit("-", 1)[0]}
    
    workspace_dir = WORKSPACES_DIR / args.task_id
    if not workspace_dir.exists():
        print(f"ERROR: Workspace not set up at {workspace_dir}")
        print(f"Run: python phase2_setup_workspace.py {args.task_id}")
        sys.exit(1)

    # Check for duplicate trial
    results = load_results()
    for trial in results["trials"]:
        if trial["task_id"] == args.task_id and trial["condition"] == args.condition:
            print(f"WARNING: Trial already exists for {args.task_id} condition {args.condition}")
            resp = input("Overwrite? (y/N): ").strip().lower()
            if resp != "y":
                print("Aborted.")
                sys.exit(0)
            results["trials"] = [
                t for t in results["trials"]
                if not (t["task_id"] == args.task_id and t["condition"] == args.condition)
            ]

    # Run trial
    if args.dry_run:
        trial_result = run_trial_local(args.task_id, args.condition, workspace_dir, task_info)
    else:
        trial_result = run_trial_ssh(
            args.task_id, args.condition, args.vps_ip, workspace_dir, task_info
        )

    # Record result
    results["trials"].append(trial_result)
    results["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    results_path = Path(args.results_file)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nTrial result: {trial_result['outcome']}")
    print(f"Duration: {trial_result['duration_seconds']}s")
    print(f"Results saved to {results_path}")


if __name__ == "__main__":
    main()
