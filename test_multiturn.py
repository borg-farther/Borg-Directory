#!/usr/bin/env python3
"""Test multi-turn conversation with tool calls."""
import json
import urllib.request
import urllib.error
from pathlib import Path

MINIMAX_KEY = Path("/root/.hermes/.env").read_text()
MINIMAX_KEY = [l.split("=", 1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
BASE_URL = "https://api.minimaxi.chat/v1"
MODEL = "MiniMax-M2.7"

def call_raw(body):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + "/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:500], "http_code": e.code}

tools = [
    {"type": "function", "function": {"name": "read_file", "description": "...", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}
]

# First call
print("=== First call ===")
messages = [{"role": "system", "content": "You are a bug fixer."}, {"role": "user", "content": "read /etc/hostname"}]
body = {"model": MODEL, "messages": messages, "tools": tools, "stream": False, "max_tokens": 500}
r = call_raw(body)
if "error" in r:
    print("  ERROR:", r["error"])
else:
    msg = r["choices"][0]["message"]
    uses = msg.get("tool_calls", [])
    print("  OK - tool_calls:", uses)

    # Second call - with history
    print("\n=== Second call ===")
    u = uses[0]
    history = [
        {"role": "assistant", "content": "", "tool_calls": uses},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"], "name": u["function"]["name"], "content": "/var/lib/data"}]},
    ]
    messages2 = [{"role": "system", "content": "You are a bug fixer."}] + history
    body2 = {"model": MODEL, "messages": messages2, "tools": tools, "stream": False, "max_tokens": 500}
    r2 = call_raw(body2)
    if "error" in r2:
        print("  ERROR:", r2["error"])
    else:
        msg2 = r2["choices"][0]["message"]
        print("  OK - content:", msg2.get("content", "")[:200])
        print("  tool_calls:", msg2.get("tool_calls"))

    # Third call - even more history
    print("\n=== Third call ===")
    history2 = [
        {"role": "assistant", "content": "", "tool_calls": uses},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": u["id"], "name": u["function"]["name"], "content": "/var/lib/data"}]},
        {"role": "assistant", "content": "", "tool_calls": msg2.get("tool_calls", [])},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": msg2["tool_calls"][0]["id"], "name": msg2["tool_calls"][0]["function"]["name"], "content": "file content here"}]},
    ]
    messages3 = [{"role": "system", "content": "You are a bug fixer."}] + history2
    body3 = {"model": MODEL, "messages": messages3, "tools": tools, "stream": False, "max_tokens": 500}
    r3 = call_raw(body3)
    if "error" in r3:
        print("  ERROR:", r3["error"])
    else:
        msg3 = r3["choices"][0]["message"]
        print("  OK - content:", msg3.get("content", "")[:200])
        print("  tool_calls:", msg3.get("tool_calls"))