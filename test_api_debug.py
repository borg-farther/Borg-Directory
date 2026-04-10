#!/usr/bin/env python3
"""Find what's causing the 400 error with system prompt + tools."""
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

# Test 1: Short system prompt + tools
print("Test 1: Short system prompt + tools...")
r = call_raw({
    "model": MODEL,
    "messages": [{"role": "system", "content": "You are a bug fixer."}, {"role": "user", "content": "read /etc/hostname"}],
    "tools": [{"type": "function", "function": {"name": "read_file", "description": "...", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}],
    "max_tokens": 100,
})
if "error" in r:
    print("  ERROR:", r["error"])
else:
    print("  SUCCESS:", r["choices"][0]["message"].get("tool_calls"))

# Test 2: Long system prompt + tools
print("\nTest 2: Long system prompt + tools...")
long_sys = """You are a skilled Django bug fixer. Your job is to fix the bug described below.
PROBLEM STATEMENT: The bug is XYZ.
Failing test: test_foo
You have access to these tools:
- read_file(path): Read a file
- borg_debug(traceback): Ask borg collective intelligence for debugging guidance
- finish(reason): Signal you are done"""
r = call_raw({
    "model": MODEL,
    "messages": [{"role": "system", "content": long_sys}, {"role": "user", "content": "read /etc/hostname"}],
    "tools": [{"type": "function", "function": {"name": "read_file", "description": "...", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}],
    "max_tokens": 100,
})
if "error" in r:
    print("  ERROR:", r["error"])
else:
    print("  SUCCESS:", r["choices"][0]["message"].get("tool_calls"))

# Test 3: Same as Test 2 but without tools
print("\nTest 3: Long system prompt, no tools...")
r = call_raw({
    "model": MODEL,
    "messages": [{"role": "system", "content": long_sys}, {"role": "user", "content": "read /etc/hostname"}],
    "max_tokens": 100,
})
if "error" in r:
    print("  ERROR:", r["error"])
else:
    print("  SUCCESS:", r["choices"][0]["message"].get("content", "")[:100])

# Test 4: Multiple tools
print("\nTest 4: Multiple tools...")
r = call_raw({
    "model": MODEL,
    "messages": [{"role": "system", "content": "You are a bug fixer."}, {"role": "user", "content": "read /etc/hostname"}],
    "tools": [
        {"type": "function", "function": {"name": "read_file", "description": "...", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "finish", "description": "...", "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}}}},
        {"type": "function", "function": {"name": "borg_debug", "description": "...", "parameters": {"type": "object", "properties": {"traceback": {"type": "string"}}, "required": ["traceback"]}}},
    ],
    "max_tokens": 100,
})
if "error" in r:
    print("  ERROR:", r["error"])
else:
    print("  SUCCESS:", r["choices"][0]["message"].get("tool_calls"))