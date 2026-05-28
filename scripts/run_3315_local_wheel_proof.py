#!/usr/bin/env python3
"""Build and smoke-test the current Borg wheel without destructive temp cleanup.

The script creates a unique temp root, builds artifacts there, installs the wheel
into a fresh venv, and proves the user-facing channels from a non-repo cwd with
PYTHONPATH cleared and isolated HOME/BORG_HOME.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "local_wheel_3315_proof.json"
REPORT = ROOT / "docs" / "20260528_LOCAL_WHEEL_3315_PROOF.md"
EXPECTED = "3.3.15"


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 180) -> dict:
    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd or ROOT),
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - start, 3),
        "stdout": proc.stdout[-6000:],
        "stderr": proc.stderr[-6000:],
    }


def ok(step: dict) -> bool:
    return step.get("returncode") == 0


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="borg-3315-wheel-proof-"))
    build_dir = temp_root / "dist"
    venv = temp_root / "venv"
    home = temp_root / "home"
    cwd = temp_root / "nonrepo-cwd"
    rules = cwd / "rules"
    openclaw = cwd / "openclaw"
    cwd.mkdir(parents=True)
    home.mkdir(parents=True)

    steps: list[dict] = []
    base_env = os.environ.copy()
    base_env.update({"PYTHONDONTWRITEBYTECODE": "1"})

    steps.append(run([sys.executable, "-m", "build", "--outdir", str(build_dir)], env=base_env, timeout=300))
    wheel = build_dir / "agent_borg-3.3.15-py3-none-any.whl"
    sdist = build_dir / "agent_borg-3.3.15.tar.gz"
    artifact_checks = {
        "wheel_exists": wheel.exists(),
        "sdist_exists": sdist.exists(),
        "artifacts": [],
    }
    for artifact in sorted(build_dir.glob("*")):
        artifact_checks["artifacts"].append({
            "name": artifact.name,
            "size": artifact.stat().st_size,
            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        })
    if wheel.exists():
        with zipfile.ZipFile(wheel) as z:
            names = z.namelist()
        artifact_checks.update({
            "wheel_has_seed_pack": any("borg/seeds_data/packs/systematic-debugging.workflow.yaml" in n for n in names),
            "wheel_has_seed_md": any("borg/seeds_data/systematic-debugging.md" in n for n in names),
            "wheel_has_mcp": any("borg/integrations/mcp_server.py" in n for n in names),
        })
    if sdist.exists():
        with tarfile.open(sdist) as t:
            names = t.getnames()
        artifact_checks.update({
            "sdist_has_seed_pack": any("borg/seeds_data/packs/systematic-debugging.workflow.yaml" in n for n in names),
            "sdist_has_seed_md": any("borg/seeds_data/systematic-debugging.md" in n for n in names),
        })

    steps.append(run([sys.executable, "-m", "twine", "check", str(wheel), str(sdist)], env=base_env, timeout=180))
    steps.append(run([sys.executable, "-m", "venv", str(venv)], env=base_env, timeout=180))

    install_env = base_env.copy()
    install_env.update({"PYTHONPATH": "", "HOME": str(home), "BORG_HOME": str(home / ".borg")})
    pip = venv / "bin" / "pip"
    py = venv / "bin" / "python"
    borg = venv / "bin" / "borg"
    borg_mcp = venv / "bin" / "borg-mcp"

    steps.append(run([str(pip), "install", "--no-cache-dir", str(wheel)], cwd=cwd, env=install_env, timeout=300))
    steps.append(run([str(borg), "--version"], cwd=cwd, env=install_env, timeout=60))
    doctor = venv / "bin" / "borg-doctor"
    steps.append(run([str(doctor), "--json"], cwd=cwd, env=install_env, timeout=120))
    steps.append(run([str(borg), "rescue", "ModuleNotFoundError: No module named flask", "--json"], cwd=cwd, env=install_env, timeout=120))
    steps.append(run([str(borg), "generate", "systematic-debugging", "--format", "all", "--output", str(rules)], cwd=cwd, env=install_env, timeout=120))
    rules_checks = {name: (rules / name).is_file() and (rules / name).stat().st_size > 0 for name in [".cursorrules", ".clinerules", "CLAUDE.md", ".windsurfrules"]}
    steps.append(run([str(borg), "convert", ".", "--format", "openclaw", "--all", "--output", str(openclaw)], cwd=cwd, env=install_env, timeout=120))
    openclaw_checks = {
        "skill_md": (openclaw / "SKILL.md").is_file() and (openclaw / "SKILL.md").stat().st_size > 0,
        "pack_index": (openclaw / "references" / "pack-index.md").is_file(),
        "systematic_pack": (openclaw / "references" / "packs" / "systematic-debugging.md").is_file(),
    }
    steps.append(run([str(py), "-c", "import borg, json; print(borg.__version__); print(borg.__file__); r=borg.check('ModuleNotFoundError: No module named flask', top_k=1); print(type(r).__name__, len(r))"], cwd=cwd, env=install_env, timeout=120))

    # Newline JSON-RPC stdio MCP canary.
    mcp_payload = "".join([
        json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"borg-local-wheel-proof","version":"1"}}}) + "\n",
        json.dumps({"jsonrpc":"2.0","method":"notifications/initialized","params":{}}) + "\n",
        json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}) + "\n",
        json.dumps({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"borg_rescue","arguments":{"input":"ModuleNotFoundError: No module named flask","show_guidance":False}}}) + "\n",
    ])
    start = time.time()
    proc = subprocess.run([str(borg_mcp)], input=mcp_payload, cwd=str(cwd), env=install_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    mcp_step = {"cmd": [str(borg_mcp)], "cwd": str(cwd), "returncode": proc.returncode, "duration_seconds": round(time.time() - start, 3), "stdout": proc.stdout[-6000:], "stderr": proc.stderr[-6000:]}
    steps.append(mcp_step)
    mcp_lines = []
    for line in proc.stdout.splitlines():
        try:
            mcp_lines.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    mcp_checks = {
        "returncode_zero": proc.returncode == 0,
        "initialize_version": next((x.get("result", {}).get("serverInfo", {}).get("version") for x in mcp_lines if x.get("id") == 1), None),
        "tools_list_count": len(next((x.get("result", {}).get("tools", []) for x in mcp_lines if x.get("id") == 2), [])),
        "rescue_response_has_action": "ACTION" in proc.stdout or "action" in proc.stdout,
        "stderr_tail": proc.stderr[-1200:],
    }

    import_step = steps[-2]
    result = {
        "schema_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_revision": run(["git", "rev-parse", "HEAD"])["stdout"].strip(),
        "source_status_short": run(["git", "status", "--short"])["stdout"],
        "expected_version": EXPECTED,
        "temp_root": str(temp_root),
        "artifact_checks": artifact_checks,
        "rules_checks": rules_checks,
        "openclaw_checks": openclaw_checks,
        "mcp_checks": mcp_checks,
        "steps": steps,
    }
    result["passed"] = all([
        artifact_checks.get("wheel_exists"),
        artifact_checks.get("sdist_exists"),
        artifact_checks.get("wheel_has_seed_pack"),
        artifact_checks.get("wheel_has_seed_md"),
        artifact_checks.get("wheel_has_mcp"),
        artifact_checks.get("sdist_has_seed_pack"),
        artifact_checks.get("sdist_has_seed_md"),
        all(ok(s) for s in steps),
        EXPECTED in steps[4].get("stdout", ""),
        str(venv / "lib") in import_step.get("stdout", "") or "site-packages" in import_step.get("stdout", ""),
        all(rules_checks.values()),
        all(openclaw_checks.values()),
        mcp_checks["initialize_version"] == EXPECTED,
        mcp_checks["tools_list_count"] >= 10,
        mcp_checks["rescue_response_has_action"],
    ])

    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# Local wheel proof for agent-borg 3.3.15",
        "",
        "> Historical/internal — not current product documentation. This is a release proof artifact, not public first-user guidance.",
        "",
        f"generated_at_utc: `{result['generated_at_utc']}`",
        f"source_revision: `{result['source_revision']}`",
        f"passed: `{result['passed']}`",
        f"temp_root: `{temp_root}`",
        "",
        "## artifact sha256",
    ]
    for a in artifact_checks["artifacts"]:
        lines.append(f"- `{a['name']}` — `{a['sha256']}` ({a['size']} bytes)")
    lines += [
        "",
        "## checks",
        f"- build/twine/install/cli/api/mcp steps all rc=0: `{all(ok(s) for s in steps)}`",
        f"- packaged seed data present: `{artifact_checks.get('wheel_has_seed_pack') and artifact_checks.get('wheel_has_seed_md') and artifact_checks.get('sdist_has_seed_pack') and artifact_checks.get('sdist_has_seed_md')}`",
        f"- generated rules: `{rules_checks}`",
        f"- OpenClaw output: `{openclaw_checks}`",
        f"- MCP server version: `{mcp_checks['initialize_version']}`",
        f"- MCP tools listed: `{mcp_checks['tools_list_count']}`",
        f"- MCP rescue has value signal: `{mcp_checks['rescue_response_has_action']}`",
        "",
        "This is a local wheel/source release-candidate proof only. It does not prove PyPI latest, served runtime, public self-serve, or real external-user evidence.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "out": str(OUT), "report": str(REPORT), "temp_root": str(temp_root), "mcp_version": mcp_checks["initialize_version"], "mcp_tools": mcp_checks["tools_list_count"]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
