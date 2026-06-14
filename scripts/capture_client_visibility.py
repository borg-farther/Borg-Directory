#!/usr/bin/env python3
"""Capture what an MCP client receives when Borg fires — per client.

The firing-visibility relay (E-014) was only ever verified live on Claude Code.
This tool reproduces, over the REAL borg-mcp stdio transport, exactly what any
named client receives, so the load-bearing question can be answered for Cursor
(or any client) without a GUI:

    Is the "🛟 Borg:" moment-line in the MODEL-VISIBLE tool result
    (result.content[].text — which the client feeds to its model, the only path
    by which the line can be relayed to the human), or ONLY in
    structuredContent.user_message (which most clients, Cursor included, do not
    render in the UI)?

    python scripts/capture_client_visibility.py --client Cursor
    python scripts/capture_client_visibility.py --client "Claude Code" --json

This is a PROTOCOL-level capture: it proves where the line lands in the payload.
Whether a given client's model then chooses to relay model-visible text is model
behavior (for Claude Code, verified live in E-014); this tool makes the payload
fact reproducible and client-labeled.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MOMENT_PREFIX = "🛟 Borg:"


def _drive_server(client_name: str, error_text: str) -> dict:
    """Run borg-mcp over stdio as `client_name` and return the borg_rescue response."""
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05",
                    "clientInfo": {"name": client_name, "version": "capture"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "borg_rescue", "arguments": {"input": error_text}}},
    ]
    stdin = "".join(json.dumps(r) + "\n" for r in requests)
    proc = subprocess.run(
        [sys.executable, "-m", "borg.integrations.mcp_server"],
        input=stdin.encode("utf-8"),
        capture_output=True,
        cwd=_REPO_ROOT,
        timeout=60,
    )
    frames = {}
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict) and "id" in msg:
            frames[msg["id"]] = msg
    if 2 not in frames:
        raise RuntimeError(f"no tools/call response; stderr={proc.stderr.decode('utf-8','replace')[:400]}")
    return frames[2].get("result", {})


def analyze(client_name: str, error_text: str) -> dict:
    result = _drive_server(client_name, error_text)
    content_text = ""
    for block in result.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            content_text += block.get("text", "")
    structured = result.get("structuredContent", {}) or {}
    structured_user_message = structured.get("user_message", "")
    top_user_message = result.get("user_message", "")

    in_model_visible = MOMENT_PREFIX in content_text
    # Where in the model-visible text does the line appear (leading matters: the
    # E-014 fix put it first so clients that truncate from the tail keep it)?
    position = content_text.find(MOMENT_PREFIX)
    leads_early = 0 <= position <= 400

    return {
        "client": client_name,
        "error_text": error_text,
        "moment_line_in_model_visible_content": in_model_visible,
        "moment_line_char_offset_in_content": position,
        "moment_line_leads_early": leads_early,
        "moment_line_in_structuredContent_user_message": MOMENT_PREFIX in str(structured_user_message),
        "moment_line_in_top_level_user_message": MOMENT_PREFIX in str(top_user_message),
        "structuredContent_user_message": structured_user_message,
        "verdict": (
            "RELAYABLE — moment-line is in the model-visible tool result; this "
            "client's model CAN surface it (model-dependent). It is ALSO in "
            "structuredContent.user_message, which Cursor's UI does not render — "
            "so the model-visible path is the one that matters for Cursor."
            if in_model_visible else
            "NOT RELAYABLE — moment-line is absent from the model-visible content; "
            "this client cannot surface it. Point the user to `borg status` (pull)."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--client", default="Cursor", help='MCP client name (e.g. "Cursor", "Claude Code")')
    ap.add_argument("--error", default="ModuleNotFoundError: No module named 'flask'")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = analyze(args.client, args.error)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"client: {report['client']}")
        print(f"moment-line in model-visible tool result: {report['moment_line_in_model_visible_content']} "
              f"(offset {report['moment_line_char_offset_in_content']}, leads_early={report['moment_line_leads_early']})")
        print(f"moment-line in structuredContent.user_message (UI-only, Cursor ignores): "
              f"{report['moment_line_in_structuredContent_user_message']}")
        print(f"verdict: {report['verdict']}")
    return 0 if report["moment_line_in_model_visible_content"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
