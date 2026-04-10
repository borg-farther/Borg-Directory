#!/usr/bin/env python3
"""Debug: check the tool call format from MiniMax more carefully."""
import json
import urllib.request

MINIMAX_KEY = open("/root/.hermes/.env").read()
MINIMAX_KEY = [l.split("=",1)[1].strip() for l in MINIMAX_KEY.splitlines() if l.startswith("MINIMAX_API_KEY=")][0].strip('"').strip("'")
MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"

def call(messages, tools=None, model="MiniMax-M2.7"):
    body = {"model": model, "messages": messages, "max_tokens": 300}
    if tools:
        body["tools"] = tools
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{MINIMAX_BASE_URL}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {MINIMAX_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the workspace.",
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
            "name": "finish",
            "description": "Signal you are done editing.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
]

# Check what MiniMax returns - exact structure
print("=== Tool call structure from MiniMax ===")
messages = [
    {"role": "user", "content": "Read the file /etc/hostname and then finish."},
]
raw = call(messages, tools)
msg = raw["choices"][0]["message"]
print("Full message dict:")
print(json.dumps(msg, indent=2, ensure_ascii=False))
print("\nRaw tool_calls from MiniMax:")
print(repr(msg.get("tool_calls")))

# Now try a second turn with the tool result to see if it continues
print("\n=== Second turn: tool result sent back ===")
tc = msg.get("tool_calls", [])
first_tc = tc[0] if tc else None
if first_tc:
    messages = [
        {"role": "user", "content": "Read the file /etc/hostname and then finish."},
        {"role": "assistant", "content": "", "tool_calls": [first_tc]},
        {"role": "tool", "tool_call_id": first_tc["id"], "name": first_tc["function"]["name"], "content": "/var/lib/data\n"},
    ]
    raw2 = call(messages, tools)
    msg2 = raw2["choices"][0]["message"]
    print("Second response content:", msg2.get("content", "")[:300])
    print("Second tool_calls:", msg2.get("tool_calls"))
