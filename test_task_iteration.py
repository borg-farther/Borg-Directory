#!/usr/bin/env python3
"""Quick test of one full task iteration with the C3 script's approach."""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# Load env
MINIMAX_KEY = Path("/root/.hermes/.env").read_text()
MINIMAX_KEY = [l.split("=", 1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
BASE_URL = "https://api.minimaxi.chat/v1"
MODEL = "MiniMax-M2.7"

def call_llm(prompt, history, tools):
    messages = [{"role": "system", "content": prompt}] + history
    body = {"model": MODEL, "messages": messages, "tools": tools, "stream": False, "max_tokens": 2048}
    body = {k: v for k, v in body.items() if v is not None}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read())
    choice = raw["choices"][0]
    msg = choice.get("message", {})
    text = msg.get("content", "")
    uses = msg.get("tool_calls", []) or []
    usage = raw.get("usage", {})
    in_t = usage.get("prompt_tokens", 0)
    out_t = usage.get("completion_tokens", 0)
    stop = choice.get("finish_reason", "")
    return text, uses, in_t, out_t, stop

def tool_specs():
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
                "name": "borg_debug",
                "description": "Ask borg for debugging guidance.",
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
                "name": "finish",
                "description": "Signal you are done.",
                "parameters": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                },
            },
        },
    ]

tools = tool_specs()
history = []

system_prompt = """You are a skilled Django bug fixer.
You have access to: read_file(path), borg_debug(traceback), finish(reason).
Begin."""

# First call - no history
print("=== First call ===")
text, uses, in_t, out_t, stop = call_llm(system_prompt, [], tools)
print(f"text (first 200): {text[:200]}")
print(f"uses: {uses}")
print(f"in_t={in_t}, out_t={out_t}, stop={stop}")

# Simulate reading a file and sending back result
if uses:
    u = uses[0]
    name = u.get("function", {}).get("name", "")
    args = u.get("function", {}).get("arguments", "")
    if isinstance(args, str):
        args = json.loads(args)
    print(f"\nTool call: {name} with args={args}")
    
    if name == "read_file":
        tool_result_content = "/etc/hostname content here"
    elif name == "borg_debug":
        import subprocess
        tb = args.get("traceback", "")
        r = subprocess.run(["borg", "debug", tb], capture_output=True, text=True, timeout=30)
        tool_result_content = (r.stdout + r.stderr)[-2000:]
        print(f"borg_debug response (first 200): {tool_result_content[:200]}")
    else:
        tool_result_content = "done"
    
    history.append({"role": "assistant", "content": "", "tool_calls": uses})
    history.append({"role": "user", "content": [{
        "type": "tool_result",
        "tool_use_id": u.get("id", ""),
        "name": name,
        "content": tool_result_content,
    }]})
    
    print("\n=== Second call ===")
    text2, uses2, in_t2, out_t2, stop2 = call_llm(system_prompt, history, tools)
    print(f"text2 (first 200): {text2[:200]}")
    print(f"uses2: {uses2}")
    print(f"in_t2={in_t2}, out_t2={out_t2}")
else:
    print("NO tool calls returned!")