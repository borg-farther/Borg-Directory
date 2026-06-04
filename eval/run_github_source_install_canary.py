#!/usr/bin/env python3
"""Run a fresh GitHub/source install canary for Borg self-service via git.

This intentionally installs `agent-borg` from a VCS source into a throwaway
virtualenv with `PYTHONPATH` cleared, then exercises first-user CLI, API, and
MCP stdio surfaces from installed console scripts. It never installs into the
operator's global environment and never restarts any live service.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.run_pypi_fresh_install_canary import (  # noqa: E402
    BANNED_PUBLIC_COPY,
    EXPECTED_SUMMARY,
    CommandResult,
    mcp_stdio_canary,
    run_cmd,
    source_version,
)

SNAPSHOT = ROOT / "eval" / "github_source_install_snapshot.json"
DEFAULT_GITHUB_INSTALL_SOURCE = "git+https://github.com/borg-farther/Borg-Directory.git@main"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _expected_files_ok(name: str, generated_rules_dir: Path, openclaw_dir: Path) -> bool:
    if name == "borg_generate_systematic_debugging_rules":
        return all(
            (generated_rules_dir / filename).exists()
            for filename in [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"]
        )
    if name == "borg_convert_openclaw_registry":
        return all(
            (openclaw_dir / filename).exists()
            for filename in ["SKILL.md", "references/pack-index.md", "references/packs/systematic-debugging.md"]
        )
    return True


def _checkout_import_leakage_check(result: CommandResult) -> dict[str, Any]:
    installed_file = None
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        if isinstance(payload, dict):
            installed_file = payload.get("file")
    except (IndexError, json.JSONDecodeError):
        installed_file = None

    installed_file_text = str(installed_file or "")
    repo_prefix = str(ROOT.resolve())
    leaked = bool(installed_file_text) and Path(installed_file_text).resolve().as_posix().startswith(Path(repo_prefix).as_posix())
    return {
        "passed": bool(installed_file_text) and not leaked,
        "installed_file": installed_file_text or None,
        "repo_root": str(ROOT),
        "detail": "installed borg module is outside the source checkout" if installed_file_text and not leaked else "checkout import leakage detected or installed module path missing",
    }


def run_canary(install_source: str, version: str, *, install_source_label: str = "github_source") -> dict[str, Any]:
    venv_dir = Path(tempfile.mkdtemp(prefix="borg-github-source-"))
    results: list[CommandResult] = []
    mcp_result: dict[str, Any] = {"passed": False, "detail": "not run"}
    checkout_import_leakage: dict[str, Any] = {"passed": False, "detail": "not run"}
    runtime_cwd = venv_dir / "runtime-cwd"
    try:
        py = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"
        borg = venv_dir / "bin" / "borg"
        doctor = venv_dir / "bin" / "borg-doctor"
        borg_mcp = venv_dir / "bin" / "borg-mcp"

        isolated_home = venv_dir / "home"
        isolated_borg_home = venv_dir / "borg-home"
        isolated_home.mkdir(parents=True, exist_ok=True)
        isolated_borg_home.mkdir(parents=True, exist_ok=True)
        runtime_cwd.mkdir(parents=True, exist_ok=True)

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
                "pip_install_git_source",
                [
                    str(pip),
                    "install",
                    "--isolated",
                    "--disable-pip-version-check",
                    "--no-cache-dir",
                    install_source,
                ],
                env=pip_env,
                cwd=runtime_cwd,
                timeout=420,
            ))
        install_ok = bool(results and results[-1].name == "pip_install_git_source" and results[-1].passed)

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
                result = run_cmd(name, cmd, env=env, cwd=runtime_cwd, timeout=180)
                combined = result.stdout + result.stderr
                stale_copy = [snippet for snippet in BANNED_PUBLIC_COPY if snippet in combined]
                files_ok = _expected_files_ok(name, generated_rules_dir, openclaw_dir)
                if result.passed and all(needle in combined for needle in needles) and not stale_copy and files_ok:
                    result.detail = "expected value signal present"
                else:
                    result.passed = False
                    result.detail = "missing expected output tokens, stale public copy present, expected files missing, or command failed"
                results.append(result)
                if name == "python_api_check":
                    checkout_import_leakage = _checkout_import_leakage_check(result)

            if borg_mcp.exists():
                mcp_result = mcp_stdio_canary(borg_mcp, env, version, cwd=runtime_cwd)
            else:
                mcp_result = {"passed": False, "detail": "borg-mcp console script missing", "expected_version": version}
        else:
            mcp_result = {"passed": False, "detail": "not run because git source install failed", "expected_version": version}
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)

    passed = all(result.passed for result in results) and bool(mcp_result.get("passed")) and bool(checkout_import_leakage.get("passed"))
    return {
        "schema_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package": "agent-borg",
        "version": version,
        "install_source": install_source_label,
        "install_target": install_source,
        "runtime_cwd_policy": "all runtime commands execute from an isolated non-repo runtime-cwd",
        "repo_root": str(ROOT),
        "checkout_import_leakage": checkout_import_leakage,
        "results": [asdict(result) for result in results],
        "mcp_stdio_canary": mcp_result,
        "success": passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fresh GitHub/source install canary for agent-borg")
    parser.add_argument("--version", default=source_version(), help="Expected agent-borg version after VCS install")
    parser.add_argument("--install-source", default=DEFAULT_GITHUB_INSTALL_SOURCE, help="pip VCS install source, e.g. git+https://...@main or git+file:///checkout")
    parser.add_argument("--install-source-label", default="github_source", help="Machine label for the source channel")
    parser.add_argument("--output", default=str(SNAPSHOT), help="Snapshot JSON path")
    args = parser.parse_args(argv)

    snapshot = run_canary(args.install_source, args.version, install_source_label=args.install_source_label)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
