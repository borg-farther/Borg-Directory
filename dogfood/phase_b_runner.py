#!/usr/bin/env python3
"""Phase B Evaluation Runner — Borg 3-Condition Experiment.

Usage:
    # Run all conditions for all tasks (local):
    python phase_b_runner.py --manifest tasks.json --condition all

    # Run single condition:
    python phase_b_runner.py --manifest tasks.json --condition C2

    # Dry-run (validate only):
    python phase_b_runner.py --manifest tasks.json --condition all --dry-run

    # Distribute across VPS nodes:
    python phase_b_runner.py --manifest tasks.json --condition all --distribute

Conditions:
    C0 — baseline: standard tools only (no borg)
    C1 — borg tools + FRESH empty borg DB
    C2 — borg tools + SEEDED borg DB (from Phase A)
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = SCRIPT_DIR / "phase_b_results.jsonl"
RUNS_PER_CELL = 3
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 16384
SSH_USER = os.environ.get("SSH_USER", "root")
SSH_KEY = os.environ.get("SSH_KEY_PATH", "~/.ssh/id_rsa")
SSH_TIMEOUT = 2400  # 40 min per trial
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# VPS nodes for distribution
VPS_NODES = [
    "147.93.72.73",
    "72.61.53.248",
    "76.13.198.23",
    "76.13.209.192",
]

# Seeded DB location (Phase A output on KVM8)
SEEDED_DB_PATH = Path(os.environ.get("SEEDED_DB_PATH", "~/.hermes/guild/"))
FRESH_DB_SENTINEL = "/tmp/borg_fresh_db"

CONDITIONS = ["C0", "C1", "C2"]

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_BASE = """\
You are a software engineering agent. Fix the failing test(s) in this repository.

Repository: {repo}
Task: {instance_id}

The failing test(s):
{fail_to_pass}

The testbed is at /testbed. Investigate the failing test(s), understand the bug,
and write a fix. Do NOT modify test files. Only modify source code to make
the failing tests pass while keeping existing passing tests working.
"""

BORG_ADDENDUM = """
You also have access to Borg collective-memory tools:
  - borg_search: search for similar previously-solved issues and patterns
  - borg_recall: retrieve detailed context about a specific past solution
Use these to find relevant prior fixes and accelerate your diagnosis.
"""

TOOL_DEFS_STANDARD = [
    {
        "name": "bash",
        "type": "bash_20250124",
    },
    {
        "name": "text_editor",
        "type": "text_editor_20250124",
    },
]

# Borg MCP tool definitions (added for C1/C2)
BORG_MCP_SERVER = {
    "type": "url",
    "url": "http://localhost:8100/mcp",  # local borg MCP endpoint
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str, level: str = "INFO"):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def load_manifest(path: str) -> list[dict]:
    """Load task manifest JSON. Expects list of task objects."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict) and "tasks" in data:
        return data["tasks"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Manifest must be a list or dict with 'tasks' key, got {type(data)}")


def append_result(result: dict, path: Path = RESULTS_PATH):
    """Append one JSON line to results file."""
    with open(path, "a") as f:
        f.write(json.dumps(result, default=str) + "\n")


def load_results(path: Path = RESULTS_PATH) -> list[dict]:
    """Load all results from JSONL file."""
    results = []
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    return results


def get_completed_keys(path: Path = RESULTS_PATH) -> set:
    """Return set of (instance_id, condition, run_idx) already completed."""
    keys = set()
    for r in load_results(path):
        keys.add((r["instance_id"], r["condition"], r["run_idx"]))
    return keys


def make_run_seed(instance_id: str, condition: str, run_idx: int) -> str:
    """Deterministic seed for reproducibility logging."""
    raw = f"{instance_id}|{condition}|{run_idx}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def reset_workspace(workspace: str):
    """Reset workspace to clean state via git."""
    subprocess.run(
        ["git", "checkout", "--", "."],
        cwd=workspace, capture_output=True, timeout=60
    )
    subprocess.run(
        ["git", "clean", "-fd"],
        cwd=workspace, capture_output=True, timeout=60
    )


def setup_borg_db(condition: str, workspace: str = "/testbed"):
    """Set up borg DB for the given condition.
    C0: no borg DB needed
    C1: create fresh empty borg DB
    C2: copy seeded borg DB from Phase A
    """
    guild_path = Path.home() / ".hermes" / "guild"

    if condition == "C0":
        # Remove borg DB if present (no borg access)
        if guild_path.exists():
            shutil.rmtree(guild_path)
        return

    if condition == "C1":
        # Fresh empty DB
        if guild_path.exists():
            shutil.rmtree(guild_path)
        guild_path.mkdir(parents=True, exist_ok=True)
        # Create empty index files so borg doesn't crash
        (guild_path / "index.json").write_text("[]")
        log("Created fresh empty borg DB for C1")
        return

    if condition == "C2":
        # Copy seeded DB
        seeded = Path(os.path.expanduser(str(SEEDED_DB_PATH)))
        if guild_path.exists():
            shutil.rmtree(guild_path)
        if seeded.exists():
            shutil.copytree(str(seeded), str(guild_path))
            log(f"Copied seeded borg DB from {seeded}")
        else:
            log(f"WARNING: Seeded DB not found at {seeded}, using empty", "WARN")
            guild_path.mkdir(parents=True, exist_ok=True)
            (guild_path / "index.json").write_text("[]")


def build_prompt(task: dict, condition: str) -> str:
    """Build the system prompt for a given task and condition."""
    prompt = SYSTEM_PROMPT_BASE.format(
        repo=task.get("repo", "unknown"),
        instance_id=task.get("instance_id", "unknown"),
        fail_to_pass=json.dumps(task.get("FAIL_TO_PASS", task.get("fail_to_pass", [])), indent=2),
    )
    if condition in ("C1", "C2"):
        prompt += BORG_ADDENDUM
    return prompt


def build_tools(condition: str) -> list[dict]:
    """Build tool list for condition."""
    tools = list(TOOL_DEFS_STANDARD)
    # Borg MCP tools added for C1/C2 via server config, not inline
    return tools


def build_mcp_servers(condition: str) -> list[dict]:
    """Build MCP server list — include borg only for C1/C2."""
    if condition in ("C1", "C2"):
        return [BORG_MCP_SERVER]
    return []


# ---------------------------------------------------------------------------
# Agent execution via Anthropic API
# ---------------------------------------------------------------------------

def run_agent_api(task: dict, condition: str, run_idx: int,
                  workspace: str = "/testbed", dry_run: bool = False) -> dict:
    """Run a single agent trial via the Anthropic API.

    Returns a result dict with outcome and metrics.
    """
    instance_id = task.get("instance_id", "unknown")
    seed = make_run_seed(instance_id, condition, run_idx)

    result = {
        "instance_id": instance_id,
        "repo": task.get("repo", "unknown"),
        "condition": condition,
        "run_idx": run_idx,
        "seed": seed,
        "model": MODEL,
        "timestamp_start": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        log(f"[DRY-RUN] Would run {instance_id} / {condition} / run {run_idx}")
        result["outcome"] = None
        result["dry_run"] = True
        result["timestamp_end"] = datetime.now(timezone.utc).isoformat()
        result["wall_seconds"] = 0
        result["tool_calls"] = 0
        result["files_modified"] = []
        result["error"] = None
        return result

    # 1. Reset workspace
    log(f"Resetting workspace for {instance_id}/{condition}/run{run_idx}")
    reset_workspace(workspace)

    # 2. Setup borg DB
    setup_borg_db(condition, workspace)

    # 3. Build prompt and tools
    system_prompt = build_prompt(task, condition)
    tools = build_tools(condition)

    # 4. Track files before
    try:
        before = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=30
        )
        files_before = set(before.stdout.strip().split("\n")) if before.stdout.strip() else set()
    except Exception:
        files_before = set()

    # 5. Run agent via API
    t0 = time.monotonic()
    tool_call_count = 0
    error_msg = None
    outcome = 0  # default: fail

    try:
        import anthropic

        client = anthropic.Anthropic()

        # Build messages
        messages = [{"role": "user", "content": system_prompt}]

        # Agentic loop
        max_turns = 80
        for turn in range(max_turns):
            kwargs = {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": messages,
                "tools": tools,
            }
            # Add MCP servers for borg conditions
            mcp_servers = build_mcp_servers(condition)
            if mcp_servers:
                kwargs["mcp_servers"] = mcp_servers

            response = client.messages.create(**kwargs)

            # Count tool use
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_call_count += len(tool_uses)

            # If stop reason is end_turn or no tool use, done
            if response.stop_reason == "end_turn" or not tool_uses:
                # Append assistant response
                messages.append({"role": "assistant", "content": response.content})
                break

            # Process tool results
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tu in tool_uses:
                tr = execute_tool(tu, workspace)
                tool_results.append(tr)
            messages.append({"role": "user", "content": tool_results})

        wall_seconds = time.monotonic() - t0

        # 6. Check outcome: run the failing tests
        outcome = check_test_outcome(task, workspace)

    except Exception as e:
        wall_seconds = time.monotonic() - t0
        error_msg = str(e)
        log(f"ERROR running {instance_id}/{condition}/run{run_idx}: {e}", "ERROR")

    # 7. Track files modified
    try:
        after = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=workspace, capture_output=True, text=True, timeout=30
        )
        files_after = set(after.stdout.strip().split("\n")) if after.stdout.strip() else set()
        files_modified = sorted(files_after - files_before)
    except Exception:
        files_modified = []

    result["timestamp_end"] = datetime.now(timezone.utc).isoformat()
    result["wall_seconds"] = round(wall_seconds, 2)
    result["tool_calls"] = tool_call_count
    result["files_modified"] = files_modified
    result["outcome"] = outcome
    result["error"] = error_msg

    return result


def execute_tool(tool_use, workspace: str) -> dict:
    """Execute a tool call and return the result block."""
    name = tool_use.name
    inp = tool_use.input or {}

    try:
        if name == "bash":
            cmd = inp.get("command", "")
            timeout = min(inp.get("timeout", 120), 300)
            proc = subprocess.run(
                cmd, shell=True, cwd=workspace,
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "HOME": str(Path.home())},
            )
            output = proc.stdout[-10000:] if len(proc.stdout) > 10000 else proc.stdout
            if proc.returncode != 0:
                output += f"\n[exit code: {proc.returncode}]\n" + proc.stderr[-3000:]
            return {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": output or "(no output)",
            }

        elif name == "text_editor":
            # Delegate to a simple file-editing implementation
            return execute_text_editor(tool_use, workspace)

        else:
            return {
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": f"Unknown tool: {name}",
                "is_error": True,
            }
    except subprocess.TimeoutExpired:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": "Command timed out",
            "is_error": True,
        }
    except Exception as e:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": f"Tool error: {e}",
            "is_error": True,
        }


def execute_text_editor(tool_use, workspace: str) -> dict:
    """Handle text_editor tool calls (view/create/str_replace/insert)."""
    inp = tool_use.input or {}
    command = inp.get("command", "view")
    fpath = inp.get("path", "")

    # Make path absolute relative to workspace
    if not os.path.isabs(fpath):
        fpath = os.path.join(workspace, fpath)

    try:
        if command == "view":
            view_range = inp.get("view_range")
            with open(fpath) as f:
                lines = f.readlines()
            if view_range:
                start, end = view_range
                lines = lines[start - 1:end]
                numbered = [f"{i + start}|{l}" for i, l in enumerate(lines)]
            else:
                numbered = [f"{i + 1}|{l}" for i, l in enumerate(lines)]
            content = "".join(numbered)
            if len(content) > 15000:
                content = content[:15000] + "\n... (truncated)"
            return {"type": "tool_result", "tool_use_id": tool_use.id, "content": content}

        elif command == "create":
            file_text = inp.get("file_text", "")
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w") as f:
                f.write(file_text)
            return {"type": "tool_result", "tool_use_id": tool_use.id, "content": f"Created {fpath}"}

        elif command == "str_replace":
            old_str = inp.get("old_str", "")
            new_str = inp.get("new_str", "")
            with open(fpath) as f:
                content = f.read()
            count = content.count(old_str)
            if count == 0:
                return {"type": "tool_result", "tool_use_id": tool_use.id,
                        "content": f"old_str not found in {fpath}", "is_error": True}
            if count > 1:
                return {"type": "tool_result", "tool_use_id": tool_use.id,
                        "content": f"old_str found {count} times in {fpath}; must be unique",
                        "is_error": True}
            content = content.replace(old_str, new_str, 1)
            with open(fpath, "w") as f:
                f.write(content)
            return {"type": "tool_result", "tool_use_id": tool_use.id,
                    "content": f"Replaced in {fpath}"}

        elif command == "insert":
            insert_line = inp.get("insert_line", 0)
            new_str = inp.get("new_str", "")
            with open(fpath) as f:
                lines = f.readlines()
            lines.insert(insert_line, new_str + "\n")
            with open(fpath, "w") as f:
                f.writelines(lines)
            return {"type": "tool_result", "tool_use_id": tool_use.id,
                    "content": f"Inserted at line {insert_line} in {fpath}"}

        else:
            return {"type": "tool_result", "tool_use_id": tool_use.id,
                    "content": f"Unknown editor command: {command}", "is_error": True}

    except Exception as e:
        return {"type": "tool_result", "tool_use_id": tool_use.id,
                "content": f"Editor error: {e}", "is_error": True}


def check_test_outcome(task: dict, workspace: str) -> int:
    """Run the failing tests and return 1 if they pass, 0 otherwise."""
    fail_to_pass = task.get("FAIL_TO_PASS", task.get("fail_to_pass", []))
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)

    if not fail_to_pass:
        log("No fail_to_pass tests specified, assuming failure", "WARN")
        return 0

    # Try running the test commands
    test_cmd = task.get("test_cmd", "")
    if not test_cmd:
        # Build a generic pytest command from fail_to_pass
        test_cmd = f"python -m pytest {' '.join(fail_to_pass)} -x --tb=short"

    try:
        proc = subprocess.run(
            test_cmd, shell=True, cwd=workspace,
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "HOME": str(Path.home())},
        )
        if proc.returncode == 0:
            log(f"Tests PASSED (exit 0)")
            return 1
        else:
            log(f"Tests FAILED (exit {proc.returncode})")
            return 0
    except subprocess.TimeoutExpired:
        log("Test execution timed out", "WARN")
        return 0
    except Exception as e:
        log(f"Test execution error: {e}", "ERROR")
        return 0


# ---------------------------------------------------------------------------
# SSH / VPS distribution
# ---------------------------------------------------------------------------

def ssh_run(node: str, cmd: str, timeout: int = SSH_TIMEOUT) -> subprocess.CompletedProcess:
    """Run a command on a remote node via SSH."""
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-i", os.path.expanduser(SSH_KEY),
        f"{SSH_USER}@{node}",
        cmd
    ]
    return subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)


def rsync_borg_db(node: str):
    """Rsync seeded borg DB to a VPS node for C2 condition."""
    src = os.path.expanduser(str(SEEDED_DB_PATH))
    dst = f"{SSH_USER}@{node}:~/.hermes/guild/"
    cmd = [
        "rsync", "-az", "--delete",
        "-e", f"ssh -o StrictHostKeyChecking=no -i {os.path.expanduser(SSH_KEY)}",
        f"{src}/", dst
    ]
    log(f"Syncing borg DB to {node}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log(f"rsync to {node} failed: {result.stderr}", "ERROR")
    return result.returncode == 0


def distribute_trials(tasks: list[dict], conditions: list[str],
                      nodes: list[str], dry_run: bool = False):
    """Distribute trials across VPS nodes round-robin."""
    completed = get_completed_keys()
    trials = []

    for task in tasks:
        iid = task.get("instance_id", "unknown")
        for cond in conditions:
            for run_idx in range(RUNS_PER_CELL):
                if (iid, cond, run_idx) in completed:
                    continue
                trials.append((task, cond, run_idx))

    if not trials:
        log("All trials already completed!")
        return

    log(f"Distributing {len(trials)} trials across {len(nodes)} nodes")

    if dry_run:
        for i, (task, cond, run_idx) in enumerate(trials):
            node = nodes[i % len(nodes)]
            log(f"[DRY-RUN] {task['instance_id']}/{cond}/run{run_idx} -> {node}")
        return

    # Sync seeded DB to all nodes for C2
    if "C2" in conditions:
        for node in nodes:
            rsync_borg_db(node)

    # Simple sequential distribution (could be parallelized with asyncio)
    for i, (task, cond, run_idx) in enumerate(trials):
        node = nodes[i % len(nodes)]
        log(f"Running {task['instance_id']}/{cond}/run{run_idx} on {node}")

        # Build remote command
        manifest_json = json.dumps(task)
        remote_cmd = (
            f"cd /testbed && "
            f"ANTHROPIC_API_KEY='{ANTHROPIC_API_KEY}' "
            f"python3 /root/hermes-workspace/borg/dogfood/phase_b_runner.py "
            f"--manifest-inline '{manifest_json}' "
            f"--condition {cond} --run-idx {run_idx} --single"
        )

        try:
            result = ssh_run(node, remote_cmd)
            if result.returncode == 0:
                # Parse result from stdout
                for line in result.stdout.strip().split("\n"):
                    if line.startswith('{"instance_id"'):
                        trial_result = json.loads(line)
                        trial_result["node"] = node
                        append_result(trial_result)
                        log(f"  -> outcome={trial_result.get('outcome')}")
                        break
            else:
                log(f"  -> FAILED on {node}: {result.stderr[:200]}", "ERROR")
        except Exception as e:
            log(f"  -> ERROR: {e}", "ERROR")


# ---------------------------------------------------------------------------
# Validation (dry-run)
# ---------------------------------------------------------------------------

def validate_setup(manifest_path: str, conditions: list[str]):
    """Validate everything is ready for experiment execution."""
    errors = []
    warnings = []

    # 1. Check manifest
    try:
        tasks = load_manifest(manifest_path)
        log(f"Manifest: {len(tasks)} tasks loaded")
        for t in tasks:
            if "instance_id" not in t:
                errors.append(f"Task missing instance_id: {t}")
            if "FAIL_TO_PASS" not in t and "fail_to_pass" not in t:
                warnings.append(f"Task {t.get('instance_id', '?')} missing fail_to_pass")
    except Exception as e:
        errors.append(f"Cannot load manifest: {e}")

    # 2. Check API key
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY not set")
    else:
        log("API key: present")

    # 3. Check anthropic library
    try:
        import anthropic
        log(f"anthropic library: {anthropic.__version__}")
    except ImportError:
        errors.append("anthropic library not installed (pip install anthropic)")

    # 4. Check seeded DB for C2
    if "C2" in conditions:
        seeded = Path(os.path.expanduser(str(SEEDED_DB_PATH)))
        if seeded.exists():
            log(f"Seeded DB: {seeded} exists")
        else:
            warnings.append(f"Seeded DB not found at {seeded}")

    # 5. Check existing results
    completed = get_completed_keys()
    total = len(tasks) * len(conditions) * RUNS_PER_CELL if 'tasks' in dir() else 0
    log(f"Completed: {len(completed)} / {total} trials")

    # 6. Check VPS connectivity
    for node in VPS_NODES:
        try:
            r = ssh_run(node, "echo ok", timeout=15)
            status = "OK" if r.returncode == 0 else "FAIL"
            log(f"VPS {node}: {status}")
        except Exception as e:
            warnings.append(f"VPS {node}: {e}")

    # Report
    if errors:
        log("VALIDATION FAILED:", "ERROR")
        for e in errors:
            log(f"  ERROR: {e}", "ERROR")
    if warnings:
        for w in warnings:
            log(f"  WARN: {w}", "WARN")
    if not errors:
        log("Validation PASSED — ready to run")

    return len(errors) == 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Phase B Evaluation Runner")
    parser.add_argument("--manifest", type=str, help="Path to task manifest JSON")
    parser.add_argument("--manifest-inline", type=str, help="Inline JSON task (for remote execution)")
    parser.add_argument("--condition", type=str, default="all",
                        choices=["C0", "C1", "C2", "all"],
                        help="Condition to run (default: all)")
    parser.add_argument("--run-idx", type=int, default=None,
                        help="Specific run index (0-2)")
    parser.add_argument("--single", action="store_true",
                        help="Run single trial (for remote execution)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate setup without running agents")
    parser.add_argument("--distribute", action="store_true",
                        help="Distribute across VPS nodes")
    parser.add_argument("--workspace", type=str, default="/testbed",
                        help="Workspace directory")
    parser.add_argument("--results", type=str, default=None,
                        help="Custom results file path")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from existing results (skip completed)")

    args = parser.parse_args()

    if args.results:
        global RESULTS_PATH
        RESULTS_PATH = Path(args.results)

    # Determine conditions to run
    conditions = CONDITIONS if args.condition == "all" else [args.condition]

    # Single trial mode (used by SSH distribution)
    if args.single and args.manifest_inline:
        task = json.loads(args.manifest_inline)
        run_idx = args.run_idx if args.run_idx is not None else 0
        result = run_agent_api(task, conditions[0], run_idx,
                               workspace=args.workspace, dry_run=args.dry_run)
        # Print result JSON to stdout for remote capture
        print(json.dumps(result, default=str))
        return

    # Need manifest for multi-trial mode
    if not args.manifest:
        parser.error("--manifest is required")

    # Dry-run / validation
    if args.dry_run:
        tasks = load_manifest(args.manifest)
        ok = validate_setup(args.manifest, conditions)

        # Show what would run
        completed = get_completed_keys()
        pending = 0
        for task in tasks:
            iid = task.get("instance_id", "unknown")
            for cond in conditions:
                for run_idx in range(RUNS_PER_CELL):
                    key = (iid, cond, run_idx)
                    status = "DONE" if key in completed else "PENDING"
                    if status == "PENDING":
                        pending += 1
                    log(f"  [{status}] {iid} / {cond} / run {run_idx}")

        log(f"\nTotal pending: {pending} trials")
        log(f"Estimated time: {pending * 5}–{pending * 15} minutes")
        sys.exit(0 if ok else 1)

    # Load tasks
    tasks = load_manifest(args.manifest)
    log(f"Loaded {len(tasks)} tasks from manifest")

    # Distribution mode
    if args.distribute:
        distribute_trials(tasks, conditions, VPS_NODES, dry_run=args.dry_run)
        return

    # Local execution
    completed = get_completed_keys() if args.resume else set()
    total = len(tasks) * len(conditions) * RUNS_PER_CELL
    done = 0

    for task in tasks:
        iid = task.get("instance_id", "unknown")
        for cond in conditions:
            run_indices = [args.run_idx] if args.run_idx is not None else range(RUNS_PER_CELL)
            for run_idx in run_indices:
                done += 1
                if (iid, cond, run_idx) in completed:
                    log(f"[{done}/{total}] SKIP (done) {iid}/{cond}/run{run_idx}")
                    continue

                log(f"[{done}/{total}] Running {iid}/{cond}/run{run_idx}")
                result = run_agent_api(
                    task, cond, run_idx,
                    workspace=args.workspace,
                    dry_run=args.dry_run,
                )
                result["node"] = "local"
                append_result(result)
                log(f"  -> outcome={result['outcome']} "
                    f"time={result['wall_seconds']}s "
                    f"tools={result['tool_calls']} "
                    f"files={len(result['files_modified'])}")

    # Summary
    results = load_results()
    log(f"\n=== Phase B Summary ===")
    for cond in conditions:
        cond_results = [r for r in results if r["condition"] == cond]
        if cond_results:
            successes = sum(1 for r in cond_results if r.get("outcome") == 1)
            log(f"  {cond}: {successes}/{len(cond_results)} passed "
                f"({100 * successes / len(cond_results):.0f}%)")


if __name__ == "__main__":
    main()
