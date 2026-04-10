#!/usr/bin/env python3
"""Root cause analysis - find why first call fails with long prompt."""
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

# The exact prompt from the C3 script
PROBLEM = "Django bug fix problem: the view is not rendering correctly."
LONG_SYS = f"""You are a skilled Django bug fixer. Your job is to fix the bug described below.

PROBLEM STATEMENT:
{PROBLEM}

Failing test: test_view

You have access to these tools:
- read_file(path): Read a file
- borg_debug(traceback): Ask borg collective intelligence for debugging guidance (PASTE the failing traceback)
- borg_search(query): Search the borg knowledge base for known approaches
- finish(reason): Signal you are done

Begin by looking at the problem statement and running the failing test to understand the error."""

tools = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "borg_debug", "description": "Ask borg for debugging guidance.", "parameters": {"type": "object", "properties": {"traceback": {"type": "string"}}, "required": ["traceback"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Signal done.", "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}}}},
]

print("Test: long system prompt + user content...")
messages = [{"role": "system", "content": LONG_SYS}, {"role": "user", "content": "Begin fixing the bug."}]
body = {"model": MODEL, "messages": messages, "tools": tools, "stream": False, "max_tokens": 2048}
r = call_raw(body)
if "error" in r:
    print("  ERROR:", r["error"])
else:
    msg = r["choices"][0]["message"]
    print("  OK")
    print("  content:", msg.get("content", "")[:100])
    print("  tool_calls:", msg.get("tool_calls"))

# Try without the user message (just system + user "hi")
print("\nTest: system prompt + simple user...")
messages2 = [{"role": "system", "content": LONG_SYS}, {"role": "user", "content": "hi"}]
body2 = {"model": MODEL, "messages": messages2, "tools": tools, "stream": False, "max_tokens": 2048}
r2 = call_raw(body2)
if "error" in r2:
    print("  ERROR:", r2["error"])
else:
    msg2 = r2["choices"][0]["message"]
    print("  OK")
    print("  content:", msg2.get("content", "")[:100])
    print("  tool_calls:", msg2.get("tool_calls"))

# Try with just a short system prompt
print("\nTest: short system + user...")
messages3 = [{"role": "system", "content": "You are a bug fixer with tools."}, {"role": "user", "content": "hi"}]
body3 = {"model": MODEL, "messages": messages3, "tools": tools, "stream": False, "max_tokens": 2048}
r3 = call_raw(body3)
if "error" in r3:
    print("  ERROR:", r3["error"])
else:
    msg3 = r3["choices"][0]["message"]
    print("  OK")
    print("  content:", msg3.get("content", "")[:100])
    print("  tool_calls:", msg3.get("tool_calls"))