#!/usr/bin/env python3
"""Borg first-user release gate.

This is the executable answer to: "is Borg ready for its first user?"
It builds/installs the package into a clean virtualenv and runs the public
commands a real first user copies from the README/PyPI page: `borg rescue`,
`borg-doctor --json`, `borg try ...`, and `borg setup-claude ...`. The script is
intentionally fail-closed: any failed command, missing value receipt, URI drift,
or doc/status contradiction returns a non-zero exit code.

Usage from repo root:
    python eval/run_first_user_release_gate.py

Optional:
    python eval/run_first_user_release_gate.py --skip-build --install-source .
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
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "first_user_release_gate_snapshot.json"
PROJECT_STATUS = ROOT / "PROJECT_STATUS.md"
GO_NO_GO = ROOT / "GO_NO_GO_DECISION.md"
UAT_RESULTS = ROOT / "UAT_RESULTS.md"

PLACEHOLDER_RE = re.compile(r"\b(todo|tbd|placeholder|fixme|lorem ipsum)\b", re.I)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    command: list[str] | None = None
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    duration_s: float | None = None


def _run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, timeout: int = 120, input_text: str | None = None) -> CheckResult:
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CheckResult(
        name=" ".join(cmd),
        passed=proc.returncode == 0,
        detail="exit=0" if proc.returncode == 0 else f"exit={proc.returncode}",
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
        duration_s=round(time.monotonic() - started, 3),
    )


def _append(results: list[CheckResult], name: str, passed: bool, detail: str, **kwargs: object) -> None:
    results.append(CheckResult(name=name, passed=passed, detail=detail, **kwargs))


def _latest_wheel(dist_dir: Path) -> Path | None:
    wheels = sorted(dist_dir.glob("agent_borg-*.whl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return wheels[0] if wheels else None


def _contains_all(text: str, needles: Iterable[str]) -> bool:
    return all(n in text for n in needles)


def _quality_doc(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text.strip()) < 200:
        return False, "too short to be evidence-bearing"
    if PLACEHOLDER_RE.search(text):
        return False, "contains placeholder language"
    return True, "present and non-placeholder"


def _write_status(results: list[CheckResult], snapshot: dict[str, object]) -> None:
    passed = all(r.passed for r in results)
    failed = [r for r in results if not r.passed]
    status = "GO" if passed else "NO-GO"
    generated = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    PROJECT_STATUS.write_text(
        "# Borg Project Status\n\n"
        f"Generated: {generated}\n\n"
        f"First-user local release gate: **{status}**\n\n"
        "Public self-serve launch: **not authorized by this gate**; governed by `eval/public_self_serve_launch_gate.py` and first-10 external evidence.\n\n"
        "## Gate Summary\n\n"
        f"- passed: {sum(1 for r in results if r.passed)}\n"
        f"- failed: {len(failed)}\n"
        f"- snapshot: `eval/first_user_release_gate_snapshot.json`\n\n"
        "## Failed Checks\n\n"
        + ("None.\n" if not failed else "\n".join(f"- `{r.name}` — {r.detail}" for r in failed) + "\n")
        + "\n## Day-One Value Contract\n\n"
        "A first user must be able to install Borg, run `borg rescue`, and receive visible "
        "`ACTION / STOP / VERIFY` guidance plus a machine-readable JSON path without reading source code.\n",
        encoding="utf-8",
    )

    GO_NO_GO.write_text(
        "# Borg Go / No-Go Decision\n\n"
        f"Generated: {generated}\n\n"
        f"Decision (first-user local install only): **{status}**\n\n"
        "Public self-serve launch: **NO-GO until `eval/public_self_serve_launch_gate.py` passes with row-derived first-10 external evidence**.\n\n"
        "## Rule\n\n"
        "GO requires a clean fresh install, working console entrypoints, command/doc consistency, "
        "day-one rescue value, security baseline artifacts, and no failing hard gates.\n\n"
        "## Evidence\n\n"
        f"Machine snapshot: `eval/first_user_release_gate_snapshot.json`\n\n"
        "## Blockers\n\n"
        + ("None.\n" if not failed else "\n".join(f"- `{r.name}` — {r.detail}" for r in failed) + "\n"),
        encoding="utf-8",
    )

    UAT_RESULTS.write_text(
        "# Borg First-User UAT Results\n\n"
        f"Generated: {generated}\n\n"
        f"Overall (first-user local install only): **{status}**\n\n"
        "Public self-serve launch is governed by `eval/public_self_serve_launch_gate.py`, not by this UAT file.\n\n"
        "| Check | Result | Detail |\n|---|---:|---|\n"
        + "\n".join(
            f"| `{r.name}` | {'PASS' if r.passed else 'FAIL'} | {r.detail.replace('|', '/')} |" for r in results
        )
        + "\n",
        encoding="utf-8",
    )


def run_gate(args: argparse.Namespace) -> int:
    results: list[CheckResult] = []

    # Static release metadata checks.
    pyproject = ROOT / "pyproject.toml"
    init_py = ROOT / "borg" / "__init__.py"
    readme = ROOT / "README.md"
    license_file = ROOT / "LICENSE"
    for path in [pyproject, init_py, readme, license_file]:
        _append(results, f"file:{path.relative_to(ROOT)}", path.exists(), "present" if path.exists() else "missing")

    pyproject_text = pyproject.read_text(encoding="utf-8", errors="replace") if pyproject.exists() else ""
    init_text = init_py.read_text(encoding="utf-8", errors="replace") if init_py.exists() else ""
    version_meta = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.M)
    version_runtime = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    _append(
        results,
        "version_consistency",
        bool(version_meta and version_runtime and version_meta.group(1) == version_runtime.group(1)),
        f"pyproject={version_meta.group(1) if version_meta else 'missing'} runtime={version_runtime.group(1) if version_runtime else 'missing'}",
    )
    _append(
        results,
        "script_entrypoints",
        _contains_all(pyproject_text, ["borg =", "borg-mcp =", "borg-doctor = \"borg.cli.doctor:run_doctor\""]),
        "borg, borg-mcp, borg-doctor declared",
    )
    _append(
        results,
        "project_urls",
        _contains_all(pyproject_text, ["Homepage", "Repository", "Documentation", "Issues"]),
        "Homepage/Repository/Documentation/Issues present",
    )

    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    _append(
        results,
        "readme_day_one_path",
        _contains_all(readme_text, ["pip install agent-borg", "borg rescue"]),
        "README must include install + rescue as first-user path",
    )

    # Security/readiness artifact quality checks.
    for artifact in [
        ROOT / "eval" / "security_hardening_baseline.json",
        ROOT / "docs" / "SECURITY_HARDENING_BASELINE.md",
        ROOT / ".github" / "workflows" / "security-gates.yml",
        ROOT / "scripts" / "security_gate_check.py",
    ]:
        ok, detail = _quality_doc(artifact)
        _append(results, f"security_artifact:{artifact.relative_to(ROOT)}", ok, detail)

    venv_dir = Path(tempfile.mkdtemp(prefix="borg-first-user-gate-"))
    try:
        py = venv_dir / "bin" / "python"
        pip = venv_dir / "bin" / "pip"
        borg = venv_dir / "bin" / "borg"
        doctor = venv_dir / "bin" / "borg-doctor"

        res = _run([sys.executable, "-m", "venv", str(venv_dir)], timeout=120)
        res.name = "fresh_venv_create"
        results.append(res)
        if not res.passed:
            raise RuntimeError("fresh venv creation failed")

        if not args.skip_build:
            if (ROOT / "build").exists():
                shutil.rmtree(ROOT / "build")
            if (ROOT / "dist").exists():
                shutil.rmtree(ROOT / "dist")
            res = _run([str(py), "-m", "pip", "install", "--upgrade", "pip", "build"], timeout=240)
            res.name = "install_build_tooling"
            results.append(res)
            if res.passed:
                build_res = _run([str(py), "-m", "build", str(ROOT)], timeout=300)
                build_res.name = "build_wheel"
                results.append(build_res)

        install_target = args.install_source
        if not install_target:
            wheel = _latest_wheel(ROOT / "dist")
            install_target = str(wheel) if wheel else str(ROOT)
        install_res = _run([str(pip), "install", "--no-cache-dir", install_target], timeout=300)
        install_res.name = "fresh_install_agent_borg"
        results.append(install_res)

        env = os.environ.copy()
        isolated_home = venv_dir / "borg-home"
        isolated_user_home = venv_dir / "home"
        isolated_user_home.mkdir(parents=True, exist_ok=True)
        env["BORG_HOME"] = str(isolated_home)
        env["BORG_DIR"] = str(isolated_home)
        env["HOME"] = str(isolated_user_home)
        env["PYTHONNOUSERSITE"] = "1"

        generated_rules_dir = venv_dir / "generated-rules"
        openclaw_dir = venv_dir / "openclaw"
        commands = [
            ("borg_version", [str(borg), "--version"], None, ["borg"]),
            ("borg_help", [str(borg), "--help"], None, ["borg rescue", "borg start"]),
            ("borg_rescue_text", [str(borg), "rescue", "ModuleNotFoundError: No module named flask", "--short"], None, ["ACTION", "STOP", "VERIFY"]),
            ("borg_rescue_json", [str(borg), "rescue", "ModuleNotFoundError: No module named flask", "--json"], None, ["agent_instruction", "human_receipt"]),
            ("borg_doctor_json", [str(doctor), "--json"], None, ["runtime", "checks"]),
            ("borg_try_bare", [str(borg), "try", "systematic-debugging"], None, ["Pack:"]),
            ("borg_try_borg_uri", [str(borg), "try", "borg://hermes/systematic-debugging"], None, ["Pack:"]),
            ("borg_try_guild_uri", [str(borg), "try", "guild://hermes/systematic-debugging"], None, ["Pack:"]),
            (
                "borg_generate_rules",
                [str(borg), "generate", "systematic-debugging", "--format", "all", "--output", str(generated_rules_dir)],
                None,
                [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"],
            ),
            (
                "borg_convert_openclaw",
                [str(borg), "convert", ".", "--format", "openclaw", "--all", "--output", str(openclaw_dir)],
                None,
                ["Converted", "OpenClaw", "systematic-debugging"],
            ),
            ("borg_setup_claude_flags", [str(borg), "setup-claude", "--scope", "user", "--verify", "--fix"], None, ["setup-claude"]),
        ]
        for name, cmd, stdin, needles in commands:
            res = _run(cmd, env=env, timeout=180, input_text=stdin)
            res.name = name
            text = res.stdout + res.stderr
            if not res.passed:
                res.detail = f"command failed: {res.detail}"
            elif not _contains_all(text, needles):
                res.passed = False
                res.detail = f"missing expected output tokens: {needles}"
            elif name == "borg_generate_rules" and not all(
                (generated_rules_dir / filename).exists()
                for filename in [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"]
            ):
                res.passed = False
                res.detail = "rules export command returned success but did not write all expected files"
            elif name == "borg_convert_openclaw" and not all(
                (openclaw_dir / filename).exists()
                for filename in ["SKILL.md", "references/pack-index.md", "references/packs/systematic-debugging.md"]
            ):
                res.passed = False
                res.detail = "OpenClaw conversion returned success but did not write expected bridge files"
            else:
                res.detail = "public command returned expected value signal"
            results.append(res)

        # Import API surface: catches wheel packaging omissions masked by editable installs.
        api_code = "import borg, json; r=borg.check('ModuleNotFoundError: No module named flask', top_k=1); print(json.dumps({'version': borg.__version__, 'result_type': type(r).__name__, 'count': len(r)}))"
        res = _run([str(py), "-c", api_code], env=env, timeout=120)
        res.name = "public_import_api_check"
        if res.passed and '"result_type": "list"' in res.stdout:
            res.detail = "borg.check returned list without crashing"
        else:
            res.passed = False
            res.detail = "borg.check failed or did not return list"
        results.append(res)

    except Exception as exc:
        _append(results, "gate_runner_exception", False, str(exc))
    finally:
        if not args.keep_venv:
            shutil.rmtree(venv_dir, ignore_errors=True)

    snapshot = {
        "success": all(r.passed for r in results),
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": str(ROOT),
        "results": [asdict(r) for r in results],
    }
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_status(results, snapshot)

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["success"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Borg first-user release hard gate")
    parser.add_argument("--skip-build", action="store_true", help="Skip local wheel build and install --install-source or repo")
    parser.add_argument("--install-source", default="", help="Wheel/path/spec to install into fresh venv")
    parser.add_argument("--keep-venv", action="store_true", help="Keep temp venv for debugging")
    return run_gate(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
