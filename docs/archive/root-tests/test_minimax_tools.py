#!/usr/bin/env python3
"""Debug MiniMax tool calling format."""
import json
import urllib.request
import urllib.error

MINIMAX_KEY = open("/root/.hermes/.env").read()
MINIMAX_KEY = [l.split("=",1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"
MODEL = "MiniMax-M2.7"

def call(messages, tools=None, model=MODEL):
    body = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools
    body["max_tokens"] = 500
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{MINIMAX_BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

# Tool definition - different formats to try
tools_v1 = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    }
]

# Try just a system message with tools
print("Test: User asks about weather with tools available...")
messages = [
    {"role": "system", "content": "You have access to a get_weather tool."},
    {"role": "user", "content": "What's the weather in Tokyo?"},
]
try:
    raw = call(messages, tools_v1)
    msg = raw["choices"][0]["message"]
    print("  Content:", msg.get("content", "")[:200])
    print("  Tool calls:", msg.get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)

# Try with explicit tool role
print("\nTest: Tool call from assistant...")
messages = [
    {"role": "system", "content": "You have access to a get_weather tool."},
    {"role": "user", "content": "What's the weather in Tokyo?"},
    {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_weather", "arguments": json.dumps({"location": "Tokyo"})}}]},
    {"role": "tool", "tool_call_id": "call_1", "name": "get_weather", "content": "Sunny 25C"},
]
try:
    raw = call(messages, tools_v1)
    msg = raw["choices"][0]["message"]
    print("  Content:", msg.get("content", "")[:200])
    print("  Tool calls:", msg.get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)

# Try tool format as just dict (not wrapped in "function")
tools_v2 = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }
]
print("\nTest: read_file tool...")
messages = [
    {"role": "user", "content": "Read the file /etc/hostname"},
]
try:
    raw = call(messages, tools_v2)
    msg = raw["choices"][0]["message"]
    print("  Content:", msg.get("content", "")[:200])
    print("  Tool calls:", msg.get("tool_calls"))
except Exception as e:
    print("  ERROR:", e)