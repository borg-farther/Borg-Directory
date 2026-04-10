#!/usr/bin/env python3
"""Debug: isolate why first call fails"""
from pathlib import Path
import json, urllib.request, urllib.error

def load_env(path):
    out = {}
    if not path.exists(): return out
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln: continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

env = load_env(Path("/root/.hermes/.env"))
KEY = env.get("MINIMAX_API_KEY", "")
BASE = "https://api.minimaxi.chat/v1"

TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "borg_debug", "description": "Ask borg", "parameters": {"type": "object", "properties": {"traceback": {"type": "string"}}, "required": ["traceback"]}}},
    {"type": "function", "function": {"name": "borg_search", "description": "Search borg", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "finish", "description": "Done", "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}}}},
]

SHORT_PROMPT = "You are a helpful coding assistant. A Django test is failing: TypeError: 'NoneType' object has no attribute 'split'. Use borg_search to find known approaches."
SYSTEM_MSG = "You are a skilled Django bug fixer."

def do_call(msgs, tools=None, model="MiniMax-M2.7"):
    body = {"model": model, "messages": msgs, "stream": False, "max_tokens": 2048}
    if tools: body["tools"] = tools
    body = {k: v for k, v in body.items() if v is not None}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = json.loads(resp.read())
        msg = raw["choices"][0]["message"]
        return f"OK: text={msg.get('content','')[:100]!r} tools={bool(msg.get('tool_calls'))}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:300]}"
    except Exception as e:
        return f"ERR: {e}"

print("Test 1: system+user, no tools")
r = do_call([{"role": "system", "content": SYSTEM_MSG}, {"role": "user", "content": SHORT_PROMPT}])
print(r)

print("\nTest 2: system+user, with tools")
r = do_call([{"role": "system", "content": SYSTEM_MSG}, {"role": "user", "content": SHORT_PROMPT}], TOOLS)
print(r)

print("\nTest 3: system only, no tools")
r = do_call([{"role": "system", "content": SYSTEM_MSG}])
print(r)

print("\nTest 4: system only, with tools")
r = do_call([{"role": "system", "content": SYSTEM_MSG}], TOOLS)
print(r)

print("\nTest 5: user only, with tools (what harness sends)")
r = do_call([{"role": "user", "content": SHORT_PROMPT}], TOOLS)
print(r)

print("\nTest 6: system+user+user, with tools (harness exact format with 2 messages)")
r = do_call([{"role": "system", "content": SYSTEM_MSG}, {"role": "user", "content": "Task: django test failure"}], TOOLS)
print(r)
