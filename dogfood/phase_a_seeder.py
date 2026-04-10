#!/usr/bin/env python3
"""
Phase A Seeding Automation for Borg Evaluation Experiment.

Runs 30 SWE-bench Verified tasks through a Sonnet agent that:
1. Uses borg observe/search/debug before starting
2. Reads codebase, identifies fix, applies it
3. Runs tests via Docker
4. Reports outcome via borg feedback-v3
5. Captures all traces to phase_a_log.jsonl

Usage:
  python3 phase_a_seeder.py                  # Run all 30 tasks
  python3 phase_a_seeder.py --max-tasks 5    # Run first 5
  python3 phase_a_seeder.py --task django__django-11477  # Run single task
  python3 phase_a_seeder.py --dry-run        # List tasks without running
"""

import sys
# Ensure we can find swebench - try 3.12 packages but only if they work
# The 3.11 venv packages should take priority for anthropic/pydantic
_extra = '/usr/local/lib/python3.12/dist-packages'
if _extra not in sys.path:
    sys.path.append(_extra)  # append, not insert — venv packages first

import json
import os
import subprocess
import time
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

# ── Configuration ──────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-20250514"
MAX_TOOL_CALLS = 50
TASK_TIMEOUT_SEC = 30 * 60  # 30 min per task
WORKSPACE_BASE = Path("/tmp/borg_phase_a")
LOG_FILE = Path("/root/hermes-workspace/borg/dogfood/phase_a_log.jsonl")
PROGRESS_FILE = Path("/root/hermes-workspace/borg/dogfood/phase_a_progress.json")

# Prior pilot tasks to exclude
EXCLUDE_TASKS = {
    "django__django-10973", "django__django-10554", "django__django-11087",
    "django__django-11138", "django__django-11265", "django__django-11400",
    "django__django-12708", "django__django-12754", "django__django-13315",
    "django__django-13344", "django__django-13212",
}

# Repos to include
INCLUDE_REPOS = {"django/django", "scikit-learn/scikit-learn", "sympy/sympy"}

# ── Tool definitions for the agent ─────────────────────────────────────────

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file from the filesystem. Returns file content as string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to write"},
                "content": {"type": "string", "description": "File content"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "patch_file",
        "description": "Replace old_text with new_text in a file. The old_text must appear exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to patch"},
                "old_text": {"type": "string", "description": "Exact text to find"},
                "new_text": {"type": "string", "description": "Replacement text"}
            },
            "required": ["path", "old_text", "new_text"]
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command. Returns stdout, stderr, and exit code. Use this for running tests, exploring the codebase with find/grep, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)", "default": 120}
            },
            "required": ["command"]
        }
    },
    {
        "name": "borg_search",
        "description": "Search borg's knowledge base for relevant debugging guidance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query describing the problem"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "borg_debug",
        "description": "Get structured debugging guidance for an error from borg.",
        "input_schema": {
            "type": "object",
            "properties": {
                "error": {"type": "string", "description": "Error message or traceback"}
            },
            "required": ["error"]
        }
    },
    {
        "name": "borg_feedback",
        "description": "Report outcome to borg's feedback loop. Call this when done.",
        "input_schema": {
            "type": "object",
            "properties": {
                "problem_class": {"type": "string", "description": "Classification of the problem (e.g. 'django-queryset-bug', 'model-field-validation')"},
                "success": {"type": "string", "description": "'yes' or 'no'"},
                "time_minutes": {"type": "integer", "description": "Time spent in minutes", "default": 10}
            },
            "required": ["problem_class", "success"]
        }
    }
]


# ── Tool execution ─────────────────────────────────────────────────────────

def execute_tool(name: str, input_data: dict, trace: list) -> str:
    """Execute a tool call and return the result string."""
    trace_entry = {"tool": name, "input": input_data, "timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        if name == "read_file":
            path = input_data["path"]
            try:
                content = Path(path).read_text(errors='replace')
                # Truncate very large files
                if len(content) > 50000:
                    content = content[:50000] + f"\n\n... [TRUNCATED - file is {len(content)} chars, showing first 50000]"
                trace_entry["result"] = f"read {len(content)} chars"
                return content
            except Exception as e:
                trace_entry["result"] = f"error: {e}"
                return f"Error reading file: {e}"

        elif name == "write_file":
            path = input_data["path"]
            content = input_data["content"]
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content)
            trace_entry["result"] = f"wrote {len(content)} chars"
            return "OK"

        elif name == "patch_file":
            path = input_data["path"]
            old_text = input_data["old_text"]
            new_text = input_data["new_text"]
            content = Path(path).read_text()
            count = content.count(old_text)
            if count == 0:
                trace_entry["result"] = "error: old_text not found"
                return f"Error: old_text not found in {path}. Make sure it matches exactly (including whitespace)."
            if count > 1:
                trace_entry["result"] = f"error: old_text found {count} times"
                return f"Error: old_text found {count} times in {path}. Make it more specific."
            content = content.replace(old_text, new_text, 1)
            Path(path).write_text(content)
            trace_entry["result"] = "patched"
            trace_entry["old_text_preview"] = old_text[:200]
            trace_entry["new_text_preview"] = new_text[:200]
            return "OK"

        elif name == "run_command":
            cmd = input_data["command"]
            timeout = input_data.get("timeout", 120)
            timeout = min(timeout, 300)  # cap at 5 min
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=timeout, cwd="/tmp"
                )
                output = result.stdout + result.stderr
                # Truncate very long output
                if len(output) > 20000:
                    output = output[:10000] + "\n\n... [TRUNCATED] ...\n\n" + output[-10000:]
                trace_entry["result"] = f"exit={result.returncode}, {len(output)} chars"
                trace_entry["exit_code"] = result.returncode
                return f"Exit code: {result.returncode}\n{output}"
            except subprocess.TimeoutExpired:
                trace_entry["result"] = "timeout"
                return f"Command timed out after {timeout}s"

        elif name == "borg_search":
            query = input_data["query"]
            try:
                result = subprocess.run(
                    ["borg", "search", "--json", query],
                    capture_output=True, text=True, timeout=30
                )
                trace_entry["result"] = f"exit={result.returncode}"
                output = result.stdout + result.stderr
                if len(output) > 5000:
                    output = output[:5000]
                return output if output.strip() else "No results found."
            except Exception as e:
                trace_entry["result"] = f"error: {e}"
                return f"Borg search error: {e}"

        elif name == "borg_debug":
            error = input_data["error"]
            # Truncate very long errors
            if len(error) > 2000:
                error = error[:2000]
            try:
                result = subprocess.run(
                    ["borg", "debug", error],
                    capture_output=True, text=True, timeout=30
                )
                trace_entry["result"] = f"exit={result.returncode}"
                output = result.stdout + result.stderr
                if len(output) > 5000:
                    output = output[:5000]
                return output if output.strip() else "No guidance available."
            except Exception as e:
                trace_entry["result"] = f"error: {e}"
                return f"Borg debug error: {e}"

        elif name == "borg_feedback":
            problem_class = input_data["problem_class"]
            success = input_data["success"]
            time_min = input_data.get("time_minutes", 10)
            try:
                result = subprocess.run(
                    ["borg", "feedback-v3",
                     "--problem-class", problem_class,
                     "--success", success,
                     "--time", str(time_min)],
                    capture_output=True, text=True, timeout=30
                )
                trace_entry["result"] = f"exit={result.returncode}"
                return result.stdout + result.stderr if (result.stdout + result.stderr).strip() else "Feedback recorded."
            except Exception as e:
                trace_entry["result"] = f"error: {e}"
                return f"Borg feedback error: {e}"

        else:
            trace_entry["result"] = "unknown tool"
            return f"Unknown tool: {name}"

    finally:
        trace.append(trace_entry)


# ── Workspace setup ────────────────────────────────────────────────────────

def setup_workspace(task_record: dict) -> tuple:
    """
    Create workspace: extract source from Docker image, mount it back.
    Returns (workspace_path, container_name, test_cmd, error_msg).
    """
    tid = task_record["instance_id"]
    repo = task_record["repo"]
    spec = make_test_spec(task_record)
    image = spec.instance_image_key

    # Check if image exists
    check = subprocess.run(
        ["docker", "images", "-q", image],
        capture_output=True, text=True, timeout=10
    )
    if not check.stdout.strip():
        return None, None, None, f"Docker image not found: {image}"

    workspace = WORKSPACE_BASE / tid.replace("/", "_")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    # Extract /testbed from image
    temp_container = f"borg_extract_{int(time.time())}_{os.getpid()}"
    r = subprocess.run(
        ["docker", "run", "-d", "--name", temp_container, image, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return None, None, None, f"Failed to start temp container: {r.stderr[:200]}"

    r = subprocess.run(
        ["docker", "cp", f"{temp_container}:/testbed", str(workspace / "testbed")],
        capture_output=True, text=True, timeout=180
    )
    if r.returncode != 0:
        subprocess.run(["docker", "rm", "-f", temp_container], capture_output=True, timeout=10)
        return None, None, None, f"Failed to copy testbed: {r.stderr[:200]}"

    # Apply test patch on host
    test_patch = task_record.get("test_patch", "")
    if test_patch:
        patch_file = workspace / "test_patch.diff"
        patch_file.write_text(test_patch)
        subprocess.run(
            ["git", "apply", "--allow-empty", str(patch_file)],
            cwd=workspace / "testbed",
            capture_output=True, text=True, timeout=30
        )

    # Remove temp container
    subprocess.run(["docker", "rm", "-f", temp_container], capture_output=True, timeout=10)

    # Start workspace container with mounted testbed
    container = f"borg_pa_{tid.replace('/', '_')}_{int(time.time())}"
    testbed_path = str(workspace / "testbed")
    r = subprocess.run(
        ["docker", "run", "-d", "--name", container,
         "--memory", "4g", "--cpus", "2",
         "-v", f"{testbed_path}:/testbed",
         image, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return None, None, None, f"Failed to start workspace container: {r.stderr[:200]}"

    # Build test command based on repo type
    ftp = task_record["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)

    test_cmd = build_test_command(repo, ftp, container)

    return workspace, container, test_cmd, None


def build_test_command(repo: str, fail_to_pass: list, container: str) -> str:
    """Build the docker exec test command for a given repo."""
    test_args = set()
    for test in fail_to_pass:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)

    if repo == "django/django":
        inner_cmd = f"python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    elif repo == "scikit-learn/scikit-learn":
        inner_cmd = f"python -m pytest {' '.join(test_args)} -xvs"
    elif repo == "sympy/sympy":
        inner_cmd = f"python -m pytest {' '.join(test_args)} -xvs"
    else:
        inner_cmd = f"python -m pytest {' '.join(test_args)} -xvs"

    return f'docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && {inner_cmd}"'


def cleanup_container(container: str):
    """Stop and remove a container."""
    if container:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=15)


# ── Agent loop ─────────────────────────────────────────────────────────────

def run_agent(task_record: dict, workspace: Path, container: str, test_cmd: str) -> dict:
    """
    Run a Sonnet agent session for one task.
    Returns a result dict with trace, success, etc.
    """
    tid = task_record["instance_id"]
    repo = task_record["repo"]
    problem = task_record["problem_statement"]
    ftp = task_record["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)

    testbed = workspace / "testbed"

    # Determine source directory based on repo
    if repo == "django/django":
        src_dir = testbed / "django"
    elif repo == "scikit-learn/scikit-learn":
        src_dir = testbed / "sklearn"
    elif repo == "sympy/sympy":
        src_dir = testbed / "sympy"
    else:
        src_dir = testbed

    system_prompt = f"""You are an expert software developer fixing a bug in a real open-source project.

WORKFLOW:
1. First, use borg_search to check if there's any prior knowledge about this type of issue
2. Read the problem description carefully
3. Explore the relevant source files to understand the codebase
4. Identify the root cause
5. Apply a minimal, targeted fix
6. Run the test command to verify your fix works
7. If tests fail, use borg_debug to get guidance on the error
8. Call borg_feedback to report the outcome

RULES:
- Edit source files ONLY in {src_dir}/ — do NOT modify test files
- Files are on the host filesystem — use read_file/patch_file/write_file directly
- To run tests: use run_command with the test command provided
- Make minimal changes — don't refactor unrelated code
- You have at most {MAX_TOOL_CALLS} tool calls — be efficient
- After fixing, ALWAYS run tests to verify before reporting feedback"""

    user_message = f"""Fix this bug in {repo}.

ISSUE (instance: {tid}):
{problem}

SOURCE CODE: {src_dir}
WORKSPACE: {testbed}

TEST COMMAND (run this to check your fix):
{test_cmd}

TESTS THAT MUST PASS:
{json.dumps(ftp, indent=2)}

Start by searching borg for relevant knowledge, then explore the code and fix the bug."""

    client = Anthropic()
    messages = [{"role": "user", "content": user_message}]
    trace = []
    tool_call_count = 0
    start_time = time.time()
    success = False
    final_test_output = ""

    try:
        while tool_call_count < MAX_TOOL_CALLS:
            elapsed = time.time() - start_time
            if elapsed > TASK_TIMEOUT_SEC:
                print(f"    ⏱ Timeout after {elapsed:.0f}s")
                break

            # Call the API
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str or "overloaded" in err_str:
                    wait = min(60, 10 * (retry_count + 1))
                    retry_count = getattr(run_agent, '_retry', 0) + 1
                    run_agent._retry = retry_count
                    if retry_count <= 5:
                        print(f"    ⏳ Rate limited, waiting {wait}s (attempt {retry_count}/5)...")
                        import time as _time
                        _time.sleep(wait)
                        continue
                print(f"    ❌ API error: {e}")
                trace.append({"event": "api_error", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})
                break

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Agent is done talking
                text_parts = [b.text for b in response.content if hasattr(b, 'text')]
                if text_parts:
                    trace.append({"event": "agent_message", "text": text_parts[0][:500]})
                break

            if response.stop_reason != "tool_use":
                # Unexpected stop
                trace.append({"event": "unexpected_stop", "reason": response.stop_reason})
                break

            # Process tool calls
            tool_results = []
            assistant_content = response.content

            for block in assistant_content:
                if block.type == "tool_use":
                    tool_call_count += 1
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    print(f"    🔧 [{tool_call_count}/{MAX_TOOL_CALLS}] {tool_name}({_summarize_input(tool_name, tool_input)})")

                    result_text = execute_tool(tool_name, tool_input, trace)

                    # Track test results
                    if tool_name == "run_command" and "runtests.py" in tool_input.get("command", "") or "pytest" in tool_input.get("command", ""):
                        final_test_output = result_text
                        if "Exit code: 0" in result_text and "FAILED" not in result_text:
                            success = True
                        else:
                            success = False

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text
                    })

            # Add assistant message and tool results to conversation
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

    except Exception as e:
        trace.append({"event": "exception", "error": str(e), "traceback": traceback.format_exc()})
        print(f"    ❌ Exception: {e}")

    elapsed = time.time() - start_time

    return {
        "instance_id": tid,
        "repo": repo,
        "success": success,
        "tool_calls": tool_call_count,
        "elapsed_sec": round(elapsed, 1),
        "trace": trace,
        "final_test_output": final_test_output[-2000:] if final_test_output else "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _summarize_input(name: str, inp: dict) -> str:
    """Short summary of tool input for logging."""
    if name == "read_file":
        return inp.get("path", "?")[-60:]
    elif name == "write_file":
        return f"{inp.get('path', '?')[-40:]}, {len(inp.get('content', ''))} chars"
    elif name == "patch_file":
        return f"{inp.get('path', '?')[-40:]}"
    elif name == "run_command":
        cmd = inp.get("command", "?")
        return cmd[:80] + ("..." if len(cmd) > 80 else "")
    elif name == "borg_search":
        return inp.get("query", "?")[:60]
    elif name == "borg_debug":
        return inp.get("error", "?")[:60]
    elif name == "borg_feedback":
        return f"{inp.get('problem_class', '?')}, {inp.get('success', '?')}"
    return str(inp)[:60]


# ── Task selection ─────────────────────────────────────────────────────────

def select_tasks(max_tasks: int = 30, single_task: str = None) -> list:
    """Load and select SWE-bench Verified tasks."""
    print("Loading SWE-bench Verified dataset...")
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    task_map = {t["instance_id"]: dict(t) for t in ds}
    print(f"  Total tasks in dataset: {len(task_map)}")

    if single_task:
        if single_task in task_map:
            return [task_map[single_task]]
        else:
            print(f"  ERROR: Task {single_task} not found")
            return []

    # Filter by repo and exclude pilot tasks
    candidates = []
    for tid, task in sorted(task_map.items()):
        if task["repo"] not in INCLUDE_REPOS:
            continue
        if tid in EXCLUDE_TASKS:
            continue
        # Check if docker image exists
        spec = make_test_spec(task)
        image = spec.instance_image_key
        check = subprocess.run(
            ["docker", "images", "-q", image],
            capture_output=True, text=True, timeout=10
        )
        if check.stdout.strip():
            candidates.append(task)

    print(f"  Candidates (with images, excluding pilots): {len(candidates)}")

    # Take up to max_tasks
    selected = candidates[:max_tasks]
    print(f"  Selected: {len(selected)} tasks")

    # Show breakdown
    repos = {}
    for t in selected:
        repos[t["repo"]] = repos.get(t["repo"], 0) + 1
    for r, c in sorted(repos.items()):
        print(f"    {r}: {c}")

    return selected


# ── Progress tracking ──────────────────────────────────────────────────────

def load_progress() -> dict:
    """Load progress from disk."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"completed": [], "results_summary": {}}


def save_progress(progress: dict):
    """Save progress to disk."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def append_log(entry: dict):
    """Append a result entry to the JSONL log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Store trace in borg ────────────────────────────────────────────────────

def store_trace_in_borg(result: dict):
    """Store the agent trace in borg's local DB via CLI."""
    tid = result["instance_id"]
    success = result["success"]

    # Build a compact trace summary
    edits = []
    files_read = []
    commands_run = []
    for t in result.get("trace", []):
        tool = t.get("tool", "")
        if tool == "read_file":
            files_read.append(t.get("input", {}).get("path", "?"))
        elif tool == "patch_file":
            edits.append({
                "file": t.get("input", {}).get("path", "?"),
                "old_preview": t.get("old_text_preview", ""),
                "new_preview": t.get("new_text_preview", ""),
            })
        elif tool == "write_file":
            edits.append({"file": t.get("input", {}).get("path", "?"), "action": "write"})
        elif tool == "run_command":
            commands_run.append({
                "cmd": t.get("input", {}).get("command", "?")[:200],
                "exit": t.get("exit_code", None),
            })

    trace_summary = {
        "instance_id": tid,
        "success": success,
        "files_read": files_read[:20],
        "edits": edits[:10],
        "commands": commands_run[:10],
        "tool_calls": result.get("tool_calls", 0),
        "elapsed_sec": result.get("elapsed_sec", 0),
    }

    # Use borg feedback-v3 to record
    problem_class = f"swebench-{tid}"
    try:
        subprocess.run(
            ["borg", "feedback-v3",
             "--problem-class", problem_class,
             "--success", "yes" if success else "no",
             "--time", str(int(result.get("elapsed_sec", 0) / 60))],
            capture_output=True, text=True, timeout=30
        )
    except Exception as e:
        print(f"    ⚠ Borg feedback error: {e}")

    return trace_summary


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase A Seeding Automation")
    parser.add_argument("--max-tasks", type=int, default=30, help="Max tasks to run")
    parser.add_argument("--task", type=str, default=None, help="Run a single task by instance_id")
    parser.add_argument("--dry-run", action="store_true", help="List tasks without running")
    parser.add_argument("--reset", action="store_true", help="Reset progress and start fresh")
    args = parser.parse_args()

    # Verify API key — try env, then .env files
    if not os.environ.get("ANTHROPIC_API_KEY"):
        for env_name in [".env", ".env.save.1", ".env.save"]:
            env_file = Path.home() / ".hermes" / env_name
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    if key in ("ANTHROPIC_API_KEY", "ANTHROPIC_TOKEN") and val and len(val) > 10:
                        os.environ["ANTHROPIC_API_KEY"] = val
                        break
                if os.environ.get("ANTHROPIC_API_KEY"):
                    break
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set and not found in ~/.hermes/.env*")
        sys.exit(1)

    # Select tasks
    tasks = select_tasks(max_tasks=args.max_tasks, single_task=args.task)
    if not tasks:
        print("No tasks to run.")
        sys.exit(1)

    if args.dry_run:
        print(f"\nDry run — {len(tasks)} tasks would be processed:")
        for i, t in enumerate(tasks, 1):
            print(f"  {i:2d}. {t['instance_id']} ({t['repo']})")
        return

    # Load progress for resume
    progress = load_progress() if not args.reset else {"completed": [], "results_summary": {}}
    completed_set = set(progress["completed"])

    print(f"\n{'='*60}")
    print(f"Phase A Seeding — {len(tasks)} tasks")
    print(f"Already completed: {len(completed_set)}")
    print(f"Log: {LOG_FILE}")
    print(f"{'='*60}\n")

    total_success = 0
    total_run = 0

    for i, task in enumerate(tasks, 1):
        tid = task["instance_id"]

        if tid in completed_set:
            prev = progress["results_summary"].get(tid, {})
            was_success = prev.get("success", False)
            print(f"[{i}/{len(tasks)}] {tid} — SKIPPED (already done, success={was_success})")
            if was_success:
                total_success += 1
            total_run += 1
            continue

        print(f"\n[{i}/{len(tasks)}] {tid} ({task['repo']})")
        print(f"  Setting up workspace...")

        container = None
        try:
            workspace, container, test_cmd, error = setup_workspace(task)
            if error:
                print(f"  ❌ Setup failed: {error}")
                result = {
                    "instance_id": tid, "repo": task["repo"],
                    "success": False, "error": error,
                    "tool_calls": 0, "elapsed_sec": 0, "trace": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                print(f"  Workspace: {workspace}")
                print(f"  Container: {container}")
                print(f"  Running agent...")

                result = run_agent(task, workspace, container, test_cmd)

                # Store trace in borg
                trace_summary = store_trace_in_borg(result)
                result["trace_summary"] = trace_summary

        except Exception as e:
            print(f"  ❌ Error: {e}")
            result = {
                "instance_id": tid, "repo": task["repo"],
                "success": False, "error": str(e),
                "tool_calls": 0, "elapsed_sec": 0, "trace": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            # Clean up container
            if container:
                cleanup_container(container)

        # Log result
        append_log(result)

        # Update progress
        progress["completed"].append(tid)
        progress["results_summary"][tid] = {
            "success": result["success"],
            "tool_calls": result.get("tool_calls", 0),
            "elapsed_sec": result.get("elapsed_sec", 0),
        }
        save_progress(progress)

        total_run += 1
        if result["success"]:
            total_success += 1

        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"  {status} — {result.get('tool_calls', 0)} tool calls, {result.get('elapsed_sec', 0):.0f}s")
        print(f"  Running total: {total_success}/{total_run} ({100*total_success/total_run:.0f}%)")

    # Final summary
    print(f"\n{'='*60}")
    print(f"Phase A Complete")
    print(f"  Tasks run: {total_run}")
    print(f"  Successes: {total_success}")
    print(f"  Success rate: {100*total_success/max(total_run,1):.1f}%")
    print(f"  Log: {LOG_FILE}")
    print(f"  Progress: {PROGRESS_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
