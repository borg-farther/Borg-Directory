#!/usr/bin/env python3
"""Quick test to verify MiniMax M2.7 API connection works."""
import json
import urllib.request
import urllib.error

MINIMAX_KEY = open("/root/.hermes/.env").read()
MINIMAX_KEY = [l.split("=",1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"
MODEL = "MiniMax-M2.7"

# Test 1: Simple chat without tools
print("Test 1: Simple chat...")
messages = [{"role": "user", "content": "Say 'hello' in one word"}]
body = {"model": MODEL, "messages": messages, "max_tokens": 50}
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(
    f"{MINIMAX_BASE_URL}/chat/completions",
    data=data,
    headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read())
    print("  Response:", raw["choices"][0]["message"]["content"][:100])
except Exception as e:
    print("  ERROR:", e)

# Test 2: With a valid tool_call
print("\nTest 2: With tool definition...")
tools = [
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
messages = [
    {"role": "user", "content": "What's the weather in Tokyo?"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": json.dumps({"location": "Tokyo"}),
                },
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "call_123",
        "name": "get_weather",
        "content": "Sunny, 22C",
    },
]
body = {"model": MODEL, "messages": messages, "tools": tools, "max_tokens": 200}
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(
    f"{MINIMAX_BASE_URL}/chat/completions",
    data=data,
    headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read())
    msg = raw["choices"][0]["message"]
    print("  Content:", msg.get("content", "")[:100])
    print("  Tool calls:", msg.get("tool_calls", []))
except Exception as e:
    print("  ERROR:", e)