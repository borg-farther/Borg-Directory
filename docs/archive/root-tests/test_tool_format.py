#!/usr/bin/env python3
"""Debug: find exactly which tool format MiniMax rejects."""
import json
import urllib.request

MINIMAX_KEY = open("/root/.hermes/.env").read()
MINIMAX_KEY = [l.split("=", 1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
BASE = "https://api.minimaxi.chat/v1"

def call(messages, tools=None, model="MiniMax-M2.7"):
    body = {"model": model, "messages": messages, "max_tokens": 300}
    if tools is not None:
        body["tools"] = tools
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

# Try the exact format from my script (which failed)
print("Test 1: Tool format from my script (input_schema)...")
tools1 = [
    {
        "name": "read_file",
        "description": "Read a text file from the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    }
]
messages = [{"role": "user", "content": "Read /etc/hostname"}]
try:
    raw = call(messages, tools1)
    print("  SUCCESS:", raw["choices"][0]["message"].get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)

# Try the format that worked in test_minimax_debug.py (function wrapped)
print("\nTest 2: Tool format that worked (type:function)...")
tools2 = [
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
    }
]
try:
    raw = call(messages, tools2)
    print("  SUCCESS:", raw["choices"][0]["message"].get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)

# Try mixing both
print("\nTest 3: Mix of both...")
tools3 = [
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
        "name": "finish",
        "description": "Signal you are done.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
        },
    },
]
try:
    raw = call(messages, tools3)
    print("  SUCCESS:", raw["choices"][0]["message"].get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)