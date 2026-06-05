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
    canary_env,
    mcp_stdio_canary,
    redact_text,
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


def _direct_url_resolution(result: CommandResult, expected_commit: str | None) -> dict[str, Any]:
    """Extract VCS commit proof from pip's installed direct_url.json output."""
    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        parsed = {}
    vcs = parsed.get("vcs_info") if isinstance(parsed, dict) else {}
    if not isinstance(vcs, dict):
        vcs = {}
    vcs_name = vcs.get("vcs")
    resolved_commit = vcs.get("commit_id")
    requested_revision = vcs.get("requested_revision")
    expected_commit_is_sha = isinstance(expected_commit, str) and bool(__import__("re").fullmatch(r"[0-9a-f]{40}", expected_commit))
    commit_matches_expected = bool(expected_commit_is_sha and resolved_commit == expected_commit)
    return {
        "passed": bool(result.passed and vcs_name == "git" and resolved_commit and expected_commit_is_sha and commit_matches_expected),
        "direct_url": parsed if isinstance(parsed, dict) else {},
        "vcs": vcs_name,
        "requested_revision": requested_revision,
        "resolved_commit": resolved_commit,
        "expected_commit": expected_commit,
        "expected_commit_is_sha": expected_commit_is_sha,
        "commit_matches_expected": commit_matches_expected,
        "detail": "installed VCS direct_url commit matches expected commit" if commit_matches_expected else "installed VCS direct_url commit missing or not bound to a recorded 40-hex expected commit",
    }


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
        "repo_root": "<repo-root>",
        "detail": "installed borg module is outside the source checkout" if installed_file_text and not leaked else "checkout import leakage detected or installed module path missing",
    }


def run_canary(
    install_source: str,
    version: str,
    *,
    install_source_label: str = "github_source",
    expected_commit: str | None = None,
) -> dict[str, Any]:
    venv_dir = Path(tempfile.mkdtemp(prefix="borg-github-source-"))
    results: list[CommandResult] = []
    mcp_result: dict[str, Any] = {"passed": False, "detail": "not run"}
    checkout_import_leakage: dict[str, Any] = {"passed": False, "detail": "not run"}
    source_resolution: dict[str, Any] = {"passed": False, "detail": "not run"}
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

        env = canary_env(home=isolated_home, borg_home=isolated_borg_home)
        # Keep the source-install canary clean even on maintainer machines that
        # have local fixture roots configured or readable.  The Git self-serve
        # proof must come from packaged seed data plus the installed source, not
        # from AB-only /root checkouts or test-pack directories.
        for local_pack_env in ("BORG_TEST_PACKS_DIR", "BORG_MAINTAINER_PACKS_DIR"):
            env.pop(local_pack_env, None)
        pip_env = env.copy()
        pip_env.update({
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        })

        results.append(run_cmd("fresh_venv_create", [sys.executable, "-m", "venv", str(venv_dir)], env=env, cwd=venv_dir.parent, timeout=120))
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
            direct_url_result = run_cmd(
                "pip_direct_url_agent_borg",
                [
                    str(py),
                    "-c",
                    "import importlib.metadata as m, json; d=m.distribution('agent-borg'); print(d.read_text('direct_url.json') or '{}')",
                ],
                env=env,
                cwd=runtime_cwd,
                timeout=60,
            )
            source_resolution = _direct_url_resolution(direct_url_result, expected_commit)
            require_vcs_commit = install_source_label == "github_source" or install_source.startswith("git+")
            if not require_vcs_commit and not source_resolution.get("resolved_commit"):
                source_resolution["passed"] = True
                source_resolution["detail"] = "non-VCS local source smoke; resolved commit is not required"
            if not source_resolution.get("passed"):
                direct_url_result.passed = False
                direct_url_result.detail = str(source_resolution.get("detail"))
            results.append(direct_url_result)

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

    passed = (
        all(result.passed for result in results)
        and bool(mcp_result.get("passed"))
        and bool(checkout_import_leakage.get("passed"))
        and bool(source_resolution.get("passed"))
    )
    return {
        "schema_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package": "agent-borg",
        "version": version,
        "install_source": install_source_label,
        "install_target": redact_text(install_source),
        "source_resolution": source_resolution,
        "runtime_cwd_policy": "all runtime commands execute from an isolated non-repo runtime-cwd",
        "repo_root": "<repo-root>",
        "checkout_import_leakage": checkout_import_leakage,
        "results": [asdict(result) for result in results],
        "mcp_stdio_canary": mcp_result,
        "success": passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fresh GitHub/source install canary for agent-borg")
    parser.add_argument("--version", default=source_version(), help="Expected agent-borg version after VCS install")
    parser.add_argument("--install-source", default=DEFAULT_GITHUB_INSTALL_SOURCE, help="pip VCS install source, e.g. git+https://...@main or git+file:///checkout")
    parser.add_argument("--expected-commit", default=None, help="Expected VCS commit id that pip direct_url.json must resolve to")
    parser.add_argument("--install-source-label", default="github_source", help="Machine label for the source channel")
    parser.add_argument("--output", default=str(SNAPSHOT), help="Snapshot JSON path")
    args = parser.parse_args(argv)

    try:
        snapshot = run_canary(
            args.install_source,
            args.version,
            install_source_label=args.install_source_label,
            expected_commit=args.expected_commit,
        )
    except Exception as exc:
        snapshot = {
            "schema_version": 1,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "package": "agent-borg",
            "version": args.version,
            "install_source": args.install_source_label,
            "install_target": redact_text(args.install_source),
            "source_resolution": {"passed": False, "detail": "not run because canary raised before source resolution", "expected_commit": args.expected_commit},
            "runtime_cwd_policy": "all runtime commands execute from an isolated non-repo runtime-cwd",
            "repo_root": "<repo-root>",
            "checkout_import_leakage": {"passed": False, "detail": "not run because canary raised before import leakage check"},
            "results": [asdict(CommandResult(
                name="canary_unhandled_exception",
                command=[],
                cwd=redact_text(Path(tempfile.gettempdir())),
                returncode=1,
                passed=False,
                stdout="",
                stderr=redact_text(f"{type(exc).__name__}: {exc}"),
                duration_s=0.0,
                detail=f"exception={type(exc).__name__}",
            ))],
            "mcp_stdio_canary": {"passed": False, "detail": "not run because canary raised before MCP check", "expected_version": args.version},
            "success": False,
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
