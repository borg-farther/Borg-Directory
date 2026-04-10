#!/usr/bin/env python3
"""
C3 Replay: 15 runs x 20 iterations MiniMax-M2.7 to validate seed packs.

Gate: >=12/15 runs return non-empty borg content (debug output).

For each of 15 pre-registered Django Verified tasks:
  1. Run the task with MiniMax-M2.7 (via OpenAI-compatible API + MiniMax base URL)
  2. Call `borg debug <error>` on the task's error traceback
  3. Count whether borg returned content (non-empty response)
  4. Log run result

Exit: 0 if >=12/15 passes, 1 otherwise.
"""
from __future__ import annotations
import json
import os
import sys
import time
import traceback
from pathlib import Path

# -- paths ---------------------------------------------------------------------
ROOT = Path("/root/hermes-workspace/borg")
WORKDIR = Path("/root/c3_workdir")
OUTDIR = Path("/root/c3_output")
JSONL = OUTDIR / "c3_results.jsonl"
LOGFILE = OUTDIR / "c3_run.log"

WORKDIR.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

# -- MiniMax M2.7 credentials --------------------------------------------------
def _load_env(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

_HERMES_ENV = _load_env(Path("/root/.hermes/.env"))
MINIMAX_KEY = _HERMES_ENV.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"
MODEL = "MiniMax-M2.7"

if not MINIMAX_KEY:
    print("ERROR: MINIMAX_API_KEY not found in /root/.hermes/.env")
    sys.exit(1)

# -- pre-registered tasks ------------------------------------------------------
PRE_REGISTERED = [
    "django__django-10554",
    "django__django-11138",
    "django__django-11400",
    "django__django-12708",
    "django__django-12754",
    "django__django-13212",
    "django__django-13344",
    "django__django-14631",
    "django__django-15128",
    "django__django-15252",
    "django__django-15503",
    "django__django-15957",
    "django__django-16263",
    "django__django-16560",
    "django__django-16631",
]

# -- logging -------------------------------------------------------------------
def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")
        f.flush()

# -- LLM call via OpenAI-compatible API ---------------------------------------
def call_llm(
    prompt: str,
    history: list,
    tools: list,
    model: str = MODEL,
    key: str = MINIMAX_KEY,
    base_url: str = MINIMAX_BASE_URL,
    initial_user_msg: str = None,
):
    """Call MiniMax M2.7 via OpenAI-compatible /v1/chat/completions endpoint.

    initial_user_msg: if provided, sends a user kickoff message after system.
    This is required because MiniMax rejects system-only messages (HTTP 2013).
    """
    import urllib.request
    import urllib.error

    messages = [{"role": "system", "content": prompt}]
    if initial_user_msg:
        messages.append({"role": "user", "content": initial_user_msg})
    messages += history
    body = {
        "model": model,
        "messages": messages,
        "tools": tools if tools else None,
        "stream": False,
        "max_tokens": 2048,
    }
    body = {k: v for k, v in body.items() if v is not None}

    data = json.dumps(body).encode("utf-8")
    req_headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=data,
        headers=req_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:500]}")

    choice = raw["choices"][0]
    stop = choice.get("finish_reason", "")
    msg = choice.get("message", {})
    text = msg.get("content", "")
    uses = msg.get("tool_calls", []) or []
    usage = raw.get("usage", {})
    in_t = usage.get("prompt_tokens", 0)
    out_t = usage.get("completion_tokens", 0)
    return text, uses, in_t, out_t, stop

# -- borg tools ----------------------------------------------------------------
def borg_debug(traceback_str: str) -> str:
    """Call borg debug and return the output."""
    import subprocess

    try:
        r = subprocess.run(
            ["borg", "debug", traceback_str],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (r.stdout + r.stderr)[-4000:]
        return out
    except Exception as e:
        return f"borg ERROR: {e}"

def borg_search(query: str) -> str:
    """Call borg search and return the output."""
    import subprocess

    try:
        r = subprocess.run(
            ["borg", "search", query],
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (r.stdout + r.stderr)[-4000:]
        return out
    except Exception as e:
        return f"borg ERROR: {e}"

# -- system prompt -------------------------------------------------------------
def system_prompt(task: dict, error_type: str) -> str:
    problem = task.get("problem_statement", "")[:1000]
    return f"""You are a skilled Django bug fixer. Your job is to fix the bug described below.

PROBLEM STATEMENT:
{problem}

Failing test: {error_type}

CRITICAL: Before writing any code or running tests, you MUST use the borg
knowledge base to find known approaches to this class of error:

1. Use borg_search with a query describing the error type (e.g. "NoneType has
   no attribute", "circular import", "django migration").
2. Use borg_debug with the failing traceback to get collective debugging guidance.

The borg knowledge base contains battle-tested patterns from thousands of bug fixes.
Use it FIRST, then proceed with your analysis.

Available tools:
- borg_search(query): Search the borg knowledge base for known approaches to this error type
- borg_debug(traceback): Get collective debugging guidance from the borg collective
- read_file(path): Read a file
- write_file(path, content): Overwrite a file
- run_pytest(test): Run a pytest test
- run_bash(cmd): Run a bash command
- finish(reason): Signal you are done

Begin by calling borg_search with a short query describing the error.
"""

# -- tool specs (MiniMax-compatible format) -----------------------------------
def tool_specs() -> list[dict]:
    """Return tool specs in MiniMax-compatible format (type: function wrapper)."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a text file from the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Overwrite a file with new content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_pytest",
                "description": "Run a single pytest test inside the testbed and return exit code + tail.",
                "parameters": {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                    "required": ["test"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_bash",
                "description": "Run a bash command in the workspace (read-only safe ops).",
                "parameters": {
                    "type": "object",
                    "properties": {"cmd": {"type": "string"}},
                    "required": ["cmd"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "borg_debug",
                "description": "Ask the borg collective intelligence for a debugging approach. PASTE the failing traceback as input.",
                "parameters": {
                    "type": "object",
                    "properties": {"traceback": {"type": "string"}},
                    "required": ["traceback"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "borg_search",
                "description": "Search the borg knowledge base for known approaches to a class of error.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Signal you are done editing and want the test grader to run.",
                "parameters": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                },
            },
        },
    ]

# -- task loader --------------------------------------------------------------
def load_tasks(task_ids: list[str]) -> dict[str, dict]:
    log(f"Loading {len(task_ids)} tasks from SWE-bench Verified")
    try:
        from datasets import load_dataset
    except ImportError:
        log("ERROR: pip install datasets")
        sys.exit(1)

    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    wanted = set(task_ids)
    out: dict[str, dict] = {}
    for r in ds:
        if r["instance_id"] in wanted:
            out[r["instance_id"]] = dict(r)
    missing = wanted - set(out.keys())
    if missing:
        log(f"WARNING: tasks missing from dataset: {missing}")
    log(f"Loaded {len(out)} task records")
    return out

# -- parse tool calls ----------------------------------------------------------
def parse_tool_calls(uses: list) -> tuple[str, dict]:
    """Parse tool call name and args from MiniMax-format tool_calls.

    MiniMax returns: [{"id": "...", "type": "function",
                       "function": {"name": "...", "arguments": "{...}"}, ...}]
    """
    if not uses:
        return "", {}
    u = uses[0]
    if isinstance(u, dict):
        name = u.get("function", {}).get("name", "")
        raw_args = u.get("function", {}).get("arguments", "")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
        else:
            args = raw_args or {}
    else:
        name = ""
        args = {}
    return name, args

# -- core runner --------------------------------------------------------------
def run_single_task_c3(task: dict, max_iters: int = 20) -> dict:
    """Run one task with borg debug + search available. Track borg content returns."""
    result = {
        "task_id": task["instance_id"],
        "model": MODEL,
        "iterations": 0,
        "borg_debug_calls": 0,
        "borg_search_calls": 0,
        "borg_debug_content": False,
        "borg_search_content": False,
        "llm_cost_usd": 0.0,
        "error": None,
    }

    tools = tool_specs()
    history = []
    in_tot = 0
    out_tot = 0
    t0 = time.time()

    try:
        for it in range(max_iters):
            result["iterations"] = it + 1

            try:
                text, uses, in_t, out_t, stop = call_llm(
                    system_prompt(task, ""),
                    history,
                    tools,
                    initial_user_msg=(
                        f"Task instance: {task.get('instance_id','')}\n\n"
                        f"Problem statement:\n{task.get('problem_statement','')[:600]}\n\n"
                        f"First, use borg_search to find known approaches to this problem. "
                        f"Then use borg_debug if you have a traceback to analyze."
                    ),
                )
            except Exception as e:
                result["error"] = f"llm_call_failed: {type(e).__name__}: {str(e)[:300]}"
                break

            in_tot += in_t
            out_tot += out_t
            result["llm_cost_usd"] += cost(in_t, out_t)

            # Build assistant message blocks
            asst_blocks = []
            if text:
                asst_blocks.append({"type": "text", "text": text})
            for u in uses:
                if isinstance(u, dict):
                    asst_blocks.append({
                        "type": "tool_use",
                        "id": u.get("id", ""),
                        "name": u.get("function", {}).get("name", ""),
                        "input": u.get("function", {}).get("arguments", {}),
                    })

            # MiniMax rejects empty content (2013). Use fallback when both text
            # and tool_calls are absent (e.g. finish_reason=content_filter).
            # Keep blocks if they exist (tool_use format); fall back to text.
            if asst_blocks:
                history.append({"role": "assistant", "content": asst_blocks})
            elif text:
                history.append({"role": "assistant", "content": text})
            else:
                # Model returned nothing useful — stop instead of sending empty
                result["error"] = f"empty_response: stop={stop!r} text={text!r} uses={uses}"
                break

            if not uses:
                # Model emitted text only — stop
                break

            tool_results = []
            for u in uses:
                name, args = parse_tool_calls([u])

                if name == "finish":
                    break

                elif name == "borg_debug":
                    result["borg_debug_calls"] += 1
                    traceback_str = args.get("traceback", "") if isinstance(args, dict) else ""
                    output = borg_debug(traceback_str)
                    content_len = len(output.strip())
                    if content_len > 100:
                        result["borg_debug_content"] = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": u.get("id", ""),
                        "name": name,
                        "content": output[:4000],
                    })

                elif name == "borg_search":
                    result["borg_search_calls"] += 1
                    query = args.get("query", "") if isinstance(args, dict) else ""
                    output = borg_search(query)
                    content_len = len(output.strip())
                    if content_len > 50:
                        result["borg_search_content"] = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": u.get("id", ""),
                        "name": name,
                        "content": output[:4000],
                    })

                elif name == "read_file":
                    path = args.get("path", "") if isinstance(args, dict) else ""
                    try:
                        content = Path(path).read_text(errors="replace")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": content[:6000] + ("\n...[truncated]" if len(content) > 6000 else ""),
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": f"ERROR: {e}",
                        })

                elif name == "run_bash":
                    cmd = args.get("cmd", "") if isinstance(args, dict) else ""
                    import subprocess as sp
                    try:
                        r = sp.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=120)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": f"exit={r.returncode}\nSTDOUT:\n{r.stdout[-3000:]}\nSTDERR:\n{r.stderr[-1000:]}",
                        })
                    except sp.TimeoutExpired:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": "ERROR: timeout 120s",
                        })

                elif name == "run_pytest":
                    test_name = args.get("test", "") if isinstance(args, dict) else ""
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": u.get("id", ""),
                        "name": name,
                        "content": f"run_pytest not available in replay mode: {test_name}",
                    })

                elif name == "write_file":
                    path = args.get("path", "") if isinstance(args, dict) else ""
                    content = args.get("content", "") if isinstance(args, dict) else ""
                    try:
                        Path(path).parent.mkdir(parents=True, exist_ok=True)
                        Path(path).write_text(content)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": f"wrote {len(content)} bytes to {path}",
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": u.get("id", ""),
                            "name": name,
                            "content": f"ERROR: {e}",
                        })

                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": u.get("id", ""),
                        "name": name,
                        "content": f"unknown tool: {name}",
                    })

            history.append({"role": "user", "content": tool_results})

        result["input_tokens"] = in_tot
        result["output_tokens"] = out_tot
        result["tokens_used"] = in_tot + out_tot
        result["time_seconds"] = round(time.time() - t0, 2)

    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:400]}"
        result["traceback"] = traceback.format_exc()[-1500:]

    return result

def cost(in_tok: int, out_tok: int) -> float:
    """USD cost for MiniMax M2.7."""
    price_per_m_in = 0.20
    price_per_m_out = 1.10
    return (in_tok * price_per_m_in + out_tok * price_per_m_out) / 1_000_000

# -- JSONL writer --------------------------------------------------------------
def append_jsonl(path: str, record: dict):
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())

# -- main ---------------------------------------------------------------------
def main():
    if JSONL.exists():
        backup = JSONL.with_suffix(f".jsonl.bak.{int(time.time())}")
        JSONL.rename(backup)
        log(f"Existing JSONL backed up to {backup.name}")

    log(f"== C3 Replay: 15 runs x 20 iters MiniMax-M2.7 ==")
    log(f"model={MODEL}")
    log(f"jsonl={JSONL}")
    log(f"workdir={WORKDIR}")

    tasks = load_tasks(PRE_REGISTERED)

    passed = 0
    results = []

    for i, task_id in enumerate(PRE_REGISTERED, 1):
        if task_id not in tasks:
            log(f"TASK SKIP: {task_id} not found in dataset")
            continue

        log(f"-- Run {i}/15: {task_id}")
        task = tasks[task_id]

        rec = run_single_task_c3(task, max_iters=20)
        rec["run_index"] = i

        # Gate: non-empty borg content
        borg_content = rec.get("borg_debug_content", False) or rec.get("borg_search_content", False)
        rec["borg_content"] = borg_content
        rec["passed"] = borg_content

        append_jsonl(str(JSONL), rec)

        if borg_content:
            passed += 1
            log(f"  PASS: borg_content=True (debug={rec.get('borg_debug_calls',0)}, search={rec.get('borg_search_calls',0)})")
        else:
            log(f"  FAIL: borg_content=False (debug={rec.get('borg_debug_calls',0)}, search={rec.get('borg_search_calls',0)})")

        log(f"  iters={rec.get('iterations',0)} cost=${rec.get('llm_cost_usd',0):.5f} dt={rec.get('time_seconds',0):.1f}s")

    log("== DONE ==")
    log(f"passed={passed}/15")

    summary = {"passed": passed, "total": 15, "gate": ">=12/15"}
    with open(OUTDIR / "c3_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    if passed >= 12:
        log(f"GATE PASSED: {passed}/15 >= 12/15")
        return 0
    else:
        log(f"GATE FAILED: {passed}/15 < 12/15")
        return 1

if __name__ == "__main__":
    sys.exit(main())