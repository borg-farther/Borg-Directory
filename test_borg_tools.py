#!/usr/bin/env python3
"""Quick MiniMax-M2.7 test: does it call borg tools?"""
from pathlib import Path
import json, os, urllib.request, urllib.error

def load_env(path):
    out = {}
    if not path.exists(): return out
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln: continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

env = load_env(Path(os.path.expanduser("~/.hermes/.env")))
KEY = env.get("MINIMAX_API_KEY", "")
BASE = "https://api.minimaxi.chat/v1"

PROMPT = """You are a skilled bug fixer. A Django test is failing with this error:

TypeError: 'NoneType' object has no attribute 'split'

Search the borg knowledge base for known approaches, then call borg_debug with the traceback below.

Traceback:
  File "/testbed/django/core/management/commands/test.py", line 42, in handle
    result = test_handler.execute()
  File "/testbed/django/test/runner.py", line 123, in run
    failures = self.run_tests(tests)
  File "/testbed/django/test/runner.py", line 87, in run_tests
    suite.addTests loader.loadTestsFromName(test_name)
  File "/testbed/django/test/utils.py", line 207, in loadTestsFromName
    return loader.loadTestsFromName(name, module)
  File "/testbed/django/test/utils.py", line 195, in loadTestsFromName
    module = import_module(mod_name)
  File "/testbed/django/test/utils.py", line 63, in handle
    if not module: return
  File "/testbed/django/test/utils.py", line 64, in handle
    result = module.split('.')
TypeError: 'NoneType' object has no attribute 'split'

Use borg_search and borg_debug tools to get debugging guidance."""

TOOLS = [
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
            "description": "Signal you are done.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
]

messages = [{"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": PROMPT}]

body = {"model": "MiniMax-M2.7", "messages": messages, "tools": TOOLS, "stream": False, "max_tokens": 2048}
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(
    f"{BASE}/chat/completions", data=data,
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read())
    choice = raw["choices"][0]
    msg = choice.get("message", {})
    text = msg.get("content", "")
    uses = msg.get("tool_calls", []) or []
    print(f"finish_reason: {choice.get('finish_reason')}")
    print(f"text (first 300): {text[:300]!r}")
    print(f"tool_calls: {len(uses)} calls")
    for u in uses:
        fn = u.get("function", {})
        print(f"  -> {fn.get('name')}({fn.get('arguments','')[:100]})")
except Exception as e:
    print(f"ERROR: {e}")
