#!/usr/bin/env python3
"""Run a fresh GitHub source-install canary for Borg public self-service.

This proves the advertised public GitHub VCS install path from a clean temp
virtualenv. It records the PEP 610 ``direct_url.json`` resolved commit, then
exercises the installed CLI and local stdio MCP surfaces from the venv. It never
uses editable installs, never installs into the operator environment, and never
restarts or mutates served runtimes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "github_source_install_snapshot.json"
DEFAULT_REPO_URL = "https://github.com/borg-farther/Borg-Directory.git"
EXPECTED_SUMMARY = "Failure memory CLI and MCP server for AI coding agents"


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
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    in_project = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "[project]":
            in_project = True
            continue
        if in_project and line.startswith("["):
            break
        if in_project:
            match = re.match(r"version\s*=\s*['\"]([^'\"]+)['\"]", line)
            if match:
                return match.group(1)
    raise RuntimeError("Could not parse [project].version from pyproject.toml")


def run_cmd(
    name: str,
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int = 180,
    input_text: str | None = None,
) -> CommandResult:
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


def _looks_like_sha(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def resolve_remote_commit(repo_url: str, ref: str) -> dict[str, Any]:
    """Resolve a public Git ref without trusting local checkout state."""
    candidates = [ref]
    if ref and not ref.startswith("refs/") and not _looks_like_sha(ref):
        candidates = [f"refs/heads/{ref}", f"refs/tags/{ref}", ref]
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        proc = subprocess.run(
            ["git", "ls-remote", repo_url, candidate],
            text=True,
            capture_output=True,
            timeout=120,
        )
        attempts.append({"ref": candidate, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and _looks_like_sha(parts[0]):
                    return {"passed": True, "repo_url": repo_url, "requested_ref": ref, "resolved_ref": parts[1], "commit_id": parts[0], "attempts": attempts}
    if _looks_like_sha(ref):
        return {"passed": True, "repo_url": repo_url, "requested_ref": ref, "resolved_ref": ref, "commit_id": ref, "attempts": attempts, "assumed_direct_sha": True}
    return {"passed": False, "repo_url": repo_url, "requested_ref": ref, "resolved_ref": None, "commit_id": None, "attempts": attempts}


def mcp_stdio_canary(borg_mcp: Path, env: dict[str, str], expected_version: str) -> dict[str, Any]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "borg_rescue",
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
    responses: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            decoded = json.loads(line)
            if isinstance(decoded, dict):
                responses.append(decoded)
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{exc}: {line[:200]}")

    by_id = {resp.get("id"): resp for resp in responses}
    server_info = ((by_id.get(1) or {}).get("result") or {}).get("serverInfo") or {}
    tools = (((by_id.get(2) or {}).get("result") or {}).get("tools") or [])
    tool_names = {str(tool.get("name")) for tool in tools if isinstance(tool, dict) and tool.get("name")}
    rescue_text = ""
    try:
        rescue_text = by_id[3]["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        rescue_text = ""
    fingerprint_text = ""
    try:
        fingerprint_text = by_id[4]["result"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError):
        fingerprint_text = ""
    fingerprint_payload: dict[str, Any] = {}
    try:
        decoded = json.loads(fingerprint_text)
        if isinstance(decoded, dict):
            fingerprint_payload = decoded
    except json.JSONDecodeError:
        fingerprint_payload = {}
    observe_canary = fingerprint_payload.get("observe_behavior_canary") or {}
    confidence_canary = fingerprint_payload.get("confidence_gate_canary") or {}
    loaded_hashes = fingerprint_payload.get("loaded_function_hashes") or {}
    source_loaded_signal = bool(
        fingerprint_payload.get("borg_version") == expected_version
        and fingerprint_payload.get("source_version") == expected_version
        and fingerprint_payload.get("version_matches_source") is True
        and fingerprint_payload.get("reload_status") == "loaded_code_matches_source_behavior"
    )
    installed_package_signal = bool(
        fingerprint_payload.get("borg_version") == expected_version
        and fingerprint_payload.get("source_version") in {None, expected_version}
        and (
            fingerprint_payload.get("version_matches_source") in {False, None}
            or fingerprint_payload.get("version_matches_source") is True
        )
        and fingerprint_payload.get("reload_status") in {None, "reload_or_patch_required", "loaded_code_matches_source_behavior"}
    )
    fingerprint_signal = bool(
        fingerprint_payload.get("success") is True
        and (source_loaded_signal or installed_package_signal)
        and observe_canary.get("passed") is True
        and observe_canary.get("meta_prompt_failed_closed") is True
        and confidence_canary.get("passed") is True
        and loaded_hashes.get("borg.integrations.mcp_server.borg_observe")
    )
    passed = bool(
        result.passed
        and not parse_errors
        and set(by_id) >= {1, 2, 3, 4}
        and server_info.get("name") == "borg-mcp-server"
        and server_info.get("version") == expected_version
        and {"borg_rescue", "borg_observe", "borg_runtime_fingerprint"}.issubset(tool_names)
        and all(token in rescue_text for token in ["ACTION", "STOP", "VERIFY"])
        and fingerprint_signal
    )
    return {
        "passed": passed,
        "command_result": asdict(result),
        "response_count": len(responses),
        "parse_errors": parse_errors,
        "server_info": server_info,
        "tool_count": len(tool_names),
        "required_tools_present": sorted({"borg_rescue", "borg_observe", "borg_runtime_fingerprint"} & tool_names),
        "rescue_value_signal": all(token in rescue_text for token in ["ACTION", "STOP", "VERIFY"]),
        "fingerprint_signal": fingerprint_signal,
        "fingerprint_summary": {
            "success": fingerprint_payload.get("success"),
            "borg_version": fingerprint_payload.get("borg_version"),
            "source_version": fingerprint_payload.get("source_version"),
            "version_matches_source": fingerprint_payload.get("version_matches_source"),
            "reload_status": fingerprint_payload.get("reload_status"),
            "source_loaded_signal": source_loaded_signal,
            "installed_package_signal": installed_package_signal,
            "confidence_gate_canary_passed": confidence_canary.get("passed"),
            "observe_behavior_canary_passed": observe_canary.get("passed"),
        },
    }


def installed_distribution_probe(py: Path, expected_version: str) -> dict[str, Any]:
    code = r'''
import json
from importlib import metadata
import borg

dist = metadata.distribution('agent-borg')
direct_text = dist.read_text('direct_url.json') or '{}'
try:
    direct = json.loads(direct_text)
except Exception:
    direct = {'_parse_error': direct_text[:500]}
print(json.dumps({
    'version': borg.__version__,
    'file': borg.__file__,
    'dist_version': dist.version,
    'direct_url': direct,
}, sort_keys=True))
'''
    result = run_cmd("python_distribution_probe", [str(py), "-c", code], timeout=120)
    parsed: dict[str, Any] = {}
    if result.passed:
        try:
            decoded = json.loads(result.stdout)
            if isinstance(decoded, dict):
                parsed = decoded
        except json.JSONDecodeError:
            parsed = {}
    direct = parsed.get("direct_url") or {}
    vcs_info = direct.get("vcs_info") or {}
    passed = bool(
        result.passed
        and parsed.get("version") == expected_version
        and parsed.get("dist_version") == expected_version
        and parsed.get("file")
        and "site-packages" in str(parsed.get("file"))
        and direct.get("vcs_info")
        and vcs_info.get("vcs") == "git"
        and _looks_like_sha(str(vcs_info.get("commit_id") or ""))
    )
    return {"passed": passed, "command_result": asdict(result), "parsed": parsed}


def run_canary(repo_url: str, ref: str, expected_version: str, expected_commit: str | None) -> dict[str, Any]:
    remote = resolve_remote_commit(repo_url, ref)
    if not expected_commit:
        expected_commit = str(remote.get("commit_id") or "") or None
    venv_dir = Path(tempfile.mkdtemp(prefix="borg-github-source-"))
    results: list[CommandResult] = []
    mcp_result: dict[str, Any] = {"passed": False, "detail": "not run"}
    dist_probe: dict[str, Any] = {"passed": False, "detail": "not run"}
    try:
        py = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"
        borg = venv_dir / "bin" / "borg"
        doctor = venv_dir / "bin" / "borg-doctor"
        borg_mcp = venv_dir / "bin" / "borg-mcp"
        run_dir = venv_dir / "run-cwd"
        home = venv_dir / "home"
        borg_home = venv_dir / "borg-home"
        for path in [run_dir, home, borg_home]:
            path.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": "",
            "PYTHONNOUSERSITE": "1",
            "HOME": str(home),
            "BORG_HOME": str(borg_home),
            "BORG_DIR": str(borg_home),
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        })
        results.append(run_cmd("fresh_venv_create", [sys.executable, "-m", "venv", str(venv_dir)], timeout=120))
        if results[-1].passed:
            results.append(run_cmd(
                "pip_install_github_source",
                [str(pip), "install", "--isolated", "--disable-pip-version-check", "--no-cache-dir", f"git+{repo_url}@{ref}"],
                env=env,
                cwd=run_dir,
                timeout=420,
            ))
        install_ok = bool(results and results[-1].name == "pip_install_github_source" and results[-1].passed)
        if install_ok:
            command_specs = [
                ("pip_show_agent_borg", [str(py), "-m", "pip", "show", "agent-borg"], [f"Version: {expected_version}", f"Summary: {EXPECTED_SUMMARY}"]),
                ("borg_version", [str(borg), "--version"], [expected_version]),
                ("borg_doctor_json", [str(doctor), "--json"], ["runtime", "checks"]),
                ("borg_rescue_json", [str(borg), "rescue", "ModuleNotFoundError: No module named flask", "--json"], ["agent_instruction", "human_receipt", "ACTION", "STOP", "VERIFY"]),
            ]
            for name, cmd, needles in command_specs:
                result = run_cmd(name, cmd, env=env, cwd=run_dir, timeout=180)
                combined = result.stdout + result.stderr
                if result.passed and all(needle in combined for needle in needles):
                    result.detail = "expected value signal present"
                else:
                    result.passed = False
                    result.detail = "missing expected output tokens or command failed"
                results.append(result)
            dist_probe = installed_distribution_probe(py, expected_version)
            if borg_mcp.exists():
                mcp_result = mcp_stdio_canary(borg_mcp, env, expected_version)
            else:
                mcp_result = {"passed": False, "detail": "borg-mcp console script missing"}
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)

    direct_url = ((dist_probe.get("parsed") or {}).get("direct_url") or {}) if isinstance(dist_probe, dict) else {}
    vcs_info = direct_url.get("vcs_info") or {}
    resolved_commit = vcs_info.get("commit_id")
    source_resolution = {
        "repo_url": repo_url,
        "requested_ref": ref,
        "expected_commit": expected_commit,
        "remote_resolution": remote,
        "direct_url": direct_url,
        "resolved_commit": resolved_commit,
        "requested_revision": vcs_info.get("requested_revision"),
        "commit_matches_expected": bool(expected_commit and resolved_commit == expected_commit),
        "url_matches_expected": str(direct_url.get("url") or "").rstrip("/") == repo_url.rstrip("/"),
    }
    success = bool(
        all(result.passed for result in results)
        and dist_probe.get("passed") is True
        and mcp_result.get("passed") is True
        and source_resolution["commit_matches_expected"]
        and source_resolution["url_matches_expected"]
    )
    return {
        "schema_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package": "agent-borg",
        "version": expected_version,
        "install_source": "github_source",
        "source_resolution": source_resolution,
        "results": [asdict(result) for result in results],
        "python_distribution_probe": dist_probe,
        "mcp_stdio_canary": mcp_result,
        "success": success,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fresh GitHub source install canary for agent-borg")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL, help="Public Git repository URL")
    parser.add_argument("--ref", default=os.getenv("GITHUB_HEAD_SHA") or os.getenv("GITHUB_SHA") or "main", help="Git ref/SHA to install")
    parser.add_argument("--expected-commit", default="", help="Expected resolved git commit. Defaults to ls-remote/ref resolution when possible.")
    parser.add_argument("--version", default=source_version(), help="Expected Borg package version")
    parser.add_argument("--output", default=str(SNAPSHOT), help="Snapshot JSON path")
    args = parser.parse_args(argv)

    snapshot = run_canary(args.repo_url, args.ref, args.version, args.expected_commit or None)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
