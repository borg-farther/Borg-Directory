#!/usr/bin/env python3
"""Run a fresh PyPI install canary for Borg public self-serve readiness.

This intentionally installs the published `agent-borg` package into a throwaway
virtualenv with `PYTHONPATH` cleared, then exercises the first-user CLI and MCP
stdio surfaces from the installed console scripts. It never installs into the
operator's global environment and never restarts any live service.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "pypi_fresh_install_snapshot.json"
EXPECTED_SUMMARY = "Failure memory CLI and MCP server for AI coding agents"
BANNED_PUBLIC_COPY = [
    "Collective memory MCP server",
    "Semantic reasoning cache",
    "Collective Intelligence for AI Agents",
    "collective intelligence for AI agents",
    "collective agent intelligence",
    "battle-tested workflows from thousands of agents",
]


@dataclass
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    passed: bool
    stdout: str
    stderr: str
    duration_s: float
    detail: str


def source_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def run_cmd(name: str, cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None, timeout: int = 180, input_text: str | None = None) -> CommandResult:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or Path(tempfile.gettempdir())),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(
        name=name,
        command=cmd,
        returncode=proc.returncode,
        passed=proc.returncode == 0,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_s=round(time.monotonic() - started, 3),
        detail="exit=0" if proc.returncode == 0 else f"exit={proc.returncode}",
    )


def mcp_stdio_canary(borg_mcp: Path, env: dict[str, str], expected_version: str) -> dict[str, Any]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "error_lookup",
                "arguments": {"input": "ModuleNotFoundError: No module named flask", "show_guidance": False},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "borg_runtime_fingerprint", "arguments": {}},
        },
    ]
    input_text = "\n".join(json.dumps(req) for req in requests) + "\n"
    result = run_cmd("mcp_stdio_jsonrpc", [str(borg_mcp)], env=env, timeout=180, input_text=input_text)
    responses = []
    parse_errors: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{exc}: {line[:200]}")

    by_id = {resp.get("id"): resp for resp in responses if isinstance(resp, dict)}
    tools = (((by_id.get(2) or {}).get("result") or {}).get("tools") or [])
    tool_names = {str(tool.get("name")) for tool in tools if isinstance(tool, dict) and tool.get("name")}
    alias_text = ""
    alias_resp = by_id.get(3) or {}
    try:
        alias_text = alias_resp["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        alias_text = ""
    fingerprint_text = ""
    fingerprint_resp = by_id.get(4) or {}
    try:
        fingerprint_text = fingerprint_resp["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        fingerprint_text = ""

    fingerprint_payload: dict[str, Any] = {}
    try:
        decoded = json.loads(fingerprint_text)
        if isinstance(decoded, dict):
            fingerprint_payload = decoded
    except json.JSONDecodeError:
        fingerprint_payload = {}

    server_info = ((by_id.get(1) or {}).get("result") or {}).get("serverInfo") or {}
    loaded_hashes = fingerprint_payload.get("loaded_function_hashes") or {}
    observe_canary = fingerprint_payload.get("observe_behavior_canary") or {}
    confidence_canary = fingerprint_payload.get("confidence_gate_canary") or {}
    fingerprint_signal = (
        fingerprint_payload.get("success") is True
        and fingerprint_payload.get("borg_version") == expected_version
        and bool(loaded_hashes.get("borg.core.confidence_gate.trace_match_is_confident"))
        and bool(loaded_hashes.get("borg.integrations.mcp_server.borg_observe"))
        and observe_canary.get("passed") is True
        and observe_canary.get("meta_prompt_failed_closed") is True
        and confidence_canary.get("passed") is True
    )
    passed = (
        result.passed
        and not parse_errors
        and set(by_id) >= {1, 2, 3, 4}
        and server_info.get("name") == "borg-mcp-server"
        and server_info.get("version") == expected_version
        and "error_lookup" in tool_names
        and "ACTION" in alias_text
        and "STOP" in alias_text
        and "VERIFY" in alias_text
        and fingerprint_signal
    )
    return {
        "passed": passed,
        "command_result": asdict(result),
        "response_count": len(responses),
        "parse_errors": parse_errors,
        "tool_count": len(tool_names),
        "required_tools_present": sorted(set(tool_names) & {"error_lookup", "borg_runtime_fingerprint", "borg_rescue", "borg_observe"}),
        "server_info": server_info,
        "expected_version": expected_version,
        "alias_value_signal": all(token in alias_text for token in ["ACTION", "STOP", "VERIFY"]),
        "fingerprint_signal": fingerprint_signal,
    }


def run_canary(version: str) -> dict[str, Any]:
    venv_dir = Path(tempfile.mkdtemp(prefix="borg-pypi-fresh-"))
    results: list[CommandResult] = []
    mcp_result: dict[str, Any] = {"passed": False, "detail": "not run"}
    try:
        py = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"
        borg = venv_dir / "bin" / "borg"
        doctor = venv_dir / "bin" / "borg-doctor"
        borg_mcp = venv_dir / "bin" / "borg-mcp"

        isolated_home = venv_dir / "home"
        isolated_borg_home = venv_dir / "borg-home"
        isolated_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
            "HOME": str(isolated_home),
            "BORG_HOME": str(isolated_borg_home),
            "BORG_DIR": str(isolated_borg_home),
        })
        pip_env = env.copy()
        pip_env.update({
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        })

        results.append(run_cmd("fresh_venv_create", [sys.executable, "-m", "venv", str(venv_dir)], timeout=120))
        if results[-1].passed:
            results.append(run_cmd(
                "pip_install_agent_borg",
                [
                    str(pip),
                    "install",
                    "--isolated",
                    "--disable-pip-version-check",
                    "--no-cache-dir",
                    "--index-url",
                    "https://pypi.org/simple",
                    f"agent-borg=={version}",
                ],
                env=pip_env,
                timeout=300,
            ))
        install_ok = bool(results and results[-1].name == "pip_install_agent_borg" and results[-1].passed)
        generated_rules_dir = venv_dir / "generated-rules"
        openclaw_dir = venv_dir / "openclaw"
        commands = [
            ("pip_show_agent_borg", [str(py), "-m", "pip", "show", "agent-borg"], [f"Version: {version}", f"Summary: {EXPECTED_SUMMARY}"]),
            ("borg_version", [str(borg), "--version"], [version]),
            ("borg_help", [str(borg), "--help"], ["failure memory for AI coding agents", "borg rescue", "borg start"]),
            ("borg_rescue_json", [str(borg), "rescue", "ModuleNotFoundError: No module named flask", "--json"], ["agent_instruction", "human_receipt", "ACTION", "STOP", "VERIFY"]),
            ("borg_doctor_json", [str(doctor), "--json"], ["runtime", "checks"]),
            (
                "borg_generate_systematic_debugging_rules",
                [str(borg), "generate", "systematic-debugging", "--format", "all", "--output", str(generated_rules_dir)],
                [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"],
            ),
            (
                "borg_convert_openclaw_registry",
                [str(borg), "convert", ".", "--format", "openclaw", "--all", "--output", str(openclaw_dir)],
                ["Converted", "OpenClaw", "systematic-debugging"],
            ),
            (
                "python_api_check",
                [str(py), "-c", "import borg, json; r=borg.check('ModuleNotFoundError: No module named flask', top_k=1); print(json.dumps({'version': borg.__version__, 'result_type': type(r).__name__, 'count': len(r), 'file': borg.__file__}))"],
                [version, '"result_type": "list"'],
            ),
        ]
        if install_ok:
            for name, cmd, needles in commands:
                result = run_cmd(name, cmd, env=env, timeout=180)
                combined = result.stdout + result.stderr
                stale_copy = [snippet for snippet in BANNED_PUBLIC_COPY if snippet in combined]
                files_ok = True
                if name == "borg_generate_systematic_debugging_rules":
                    files_ok = all(
                        (generated_rules_dir / filename).exists()
                        for filename in [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"]
                    )
                elif name == "borg_convert_openclaw_registry":
                    files_ok = all(
                        (openclaw_dir / filename).exists()
                        for filename in ["SKILL.md", "references/pack-index.md", "references/packs/systematic-debugging.md"]
                    )
                if result.passed and all(needle in combined for needle in needles) and not stale_copy and files_ok:
                    result.detail = "expected value signal present"
                else:
                    result.passed = False
                    result.detail = "missing expected output tokens, stale public copy present, expected files missing, or command failed"
                results.append(result)

            if borg_mcp.exists():
                mcp_result = mcp_stdio_canary(borg_mcp, env, version)
            else:
                mcp_result = {"passed": False, "detail": "borg-mcp console script missing", "expected_version": version}
        else:
            mcp_result = {"passed": False, "detail": "not run because PyPI install failed", "expected_version": version}
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)

    return {
        "schema_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package": "agent-borg",
        "version": version,
        "install_source": "pypi",
        "results": [asdict(result) for result in results],
        "mcp_stdio_canary": mcp_result,
        "success": all(result.passed for result in results) and bool(mcp_result.get("passed")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fresh PyPI install canary for agent-borg")
    parser.add_argument("--version", default=source_version(), help="agent-borg version to install from PyPI")
    parser.add_argument("--output", default=str(SNAPSHOT), help="Snapshot JSON path")
    args = parser.parse_args(argv)

    snapshot = run_canary(args.version)
    output = Path(args.output)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
