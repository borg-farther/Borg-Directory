from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from borg.integrations import mcp_server

ROOT = Path(__file__).resolve().parents[2]


def _frame(payload: dict) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def _read_frames(data: bytes) -> list[dict]:
    frames: list[dict] = []
    stream = io.BytesIO(data)
    while True:
        header = stream.readline()
        if not header:
            break
        assert header.lower().startswith(b"content-length:"), data[:200]
        length = int(header.split(b":", 1)[1].strip())
        blank = stream.readline()
        assert blank in (b"\r\n", b"\n")
        body = stream.read(length)
        assert len(body) == length
        frames.append(json.loads(body))
    return frames


def test_stdio_transport_parses_content_length_frames() -> None:
    payloads = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]

    parsed = list(mcp_server._iter_stdio_messages(io.BytesIO(b"".join(_frame(p) for p in payloads))))

    assert parsed == [(json.dumps(payloads[0], separators=(",", ":")), True), (json.dumps(payloads[1], separators=(",", ":")), True)]


def test_stdio_transport_preserves_newline_json_compatibility() -> None:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
    parsed = list(mcp_server._iter_stdio_messages(io.BytesIO((json.dumps(payload) + "\n").encode("utf-8"))))

    assert parsed == [(json.dumps(payload), False)]


def test_stdio_response_uses_matching_framing() -> None:
    out = io.BytesIO()
    mcp_server._write_stdio_response({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}, framed=True, output=out)
    frames = _read_frames(out.getvalue())

    assert frames == [{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}]


def test_borg_mcp_console_script_accepts_standard_mcp_framing(tmp_path: Path) -> None:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "PYTHONNOUSERSITE": "1",
        "HOME": str(tmp_path / "home"),
        "BORG_HOME": str(tmp_path / "borg-home"),
        "BORG_DIR": str(tmp_path / "borg-home"),
    })

    proc = subprocess.run(
        [sys.executable, "-m", "borg.integrations.mcp_server"],
        cwd=ROOT,
        input=b"".join(_frame(req) for req in requests),
        capture_output=True,
        timeout=30,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    frames = _read_frames(proc.stdout)
    by_id = {frame["id"]: frame for frame in frames}
    assert by_id[1]["result"]["serverInfo"]["name"] == "borg-mcp-server"
    tool_names = {tool["name"] for tool in by_id[2]["result"]["tools"]}
    assert "error_lookup" in tool_names
