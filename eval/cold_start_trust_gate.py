#!/usr/bin/env python3
"""Cold-start trust hardening gate for Borg first answers.

This gate exists because one irrelevant first Borg answer can destroy trust.  It
proves that meta/product/readiness prompts fail closed instead of receiving
random framework guidance, while concrete errors still get concrete help.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SNAPSHOT = ROOT / "eval" / "cold_start_trust_gate_snapshot.json"
REPORT = ROOT / "docs" / "COLD_START_TRUST_HARDENING.md"

META_TRUST_TASK = (
    "Audit product readiness and cold-start trust hardening. Explain why "
    "irrelevant Django/permission guidance leaked; do not debug Django."
)
META_TRUST_CONTEXT = "public self-service first-answer trust gate"
PERMISSION_TASK = "Fix bash: ./deploy.sh: Permission denied"
PERMISSION_CONTEXT = "bash: ./deploy.sh: Permission denied"

BANNED_META_TOKENS = ("pack guidance", "django", "migrate", "migration", "chmod", "permission denied")


def _frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def _read_frames(data: bytes) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    stream = io.BytesIO(data)
    while True:
        header = stream.readline()
        if not header:
            break
        if not header.lower().startswith(b"content-length:"):
            raise ValueError(f"unexpected stdio header: {header[:80]!r}; data={data[:200]!r}")
        length = int(header.split(b":", 1)[1].strip())
        blank = stream.readline()
        if blank not in (b"\r\n", b"\n"):
            raise ValueError(f"bad frame separator: {blank!r}")
        body = stream.read(length)
        if len(body) != length:
            raise ValueError("short frame body")
        frames.append(json.loads(body))
    return frames


def _meta_output_passed(text: str) -> tuple[bool, list[str]]:
    lowered = text.lower()
    blockers: list[str] = []
    if "no_confident_match" not in lowered and "no confident match" not in lowered:
        blockers.append("meta/readiness prompt did not fail closed with NO_CONFIDENT_MATCH")
    for token in BANNED_META_TOKENS:
        if token in lowered:
            blockers.append(f"meta/readiness prompt leaked banned token: {token}")
    return not blockers, blockers


def _stdio_observe(task: str, context: str, tmp_root: Path) -> dict[str, Any]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "borg_observe", "arguments": {"task": task, "context": context}},
        },
    ]
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "PYTHONNOUSERSITE": "1",
        "HOME": str(tmp_root / "home"),
        "BORG_HOME": str(tmp_root / "borg-home"),
        "BORG_DIR": str(tmp_root / "borg-home"),
    })
    proc = subprocess.run(
        [sys.executable, "-m", "borg.integrations.mcp_server"],
        cwd=ROOT,
        input=b"".join(_frame(req) for req in requests),
        capture_output=True,
        timeout=45,
        env=env,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        return {"passed": False, "returncode": proc.returncode, "stdout": stdout[-2000:], "stderr": stderr[-2000:], "text": ""}
    try:
        frames = _read_frames(proc.stdout)
        text = frames[-1]["result"]["content"][0]["text"]
    except Exception as exc:
        return {"passed": False, "returncode": proc.returncode, "stdout": stdout[-2000:], "stderr": stderr[-2000:], "error": str(exc), "text": ""}
    return {"passed": True, "returncode": proc.returncode, "stderr": stderr[-2000:], "text": text}


def _confidence_gate_canaries() -> list[dict[str, Any]]:
    from borg.core import confidence_gate
    from borg.integrations import mcp_server

    irrelevant_trace = {
        "similarity": 0.92,
        "root_cause": "BORG_HOME was not set in the Hermes plugin service file.",
        "approach_summary": "Patch the real plugin runtime path and verify traces.db loading.",
    }
    irrelevant_guidance = """
ACTION: Edit /root/.hermes/hermes-agent/hermes_cli/plugins/borg_auto_trace/__init__.py and set BORG_HOME=/root/.borg.
CONFIDENCE: Real traces: 202 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
WHAT WORKED (2 prior sessions)
Root cause: BORG_HOME not set in Hermes service.
"""
    checks = [
        {
            "name": "meta_permission_mentions_are_not_permission_tasks",
            "passed": confidence_gate.permission_guidance_matches_task(
                "Audit why irrelevant permission guidance leaked into a product-readiness answer",
                "do not debug chmod or file permissions",
            ) is False,
        },
        {
            "name": "meta_django_mentions_do_not_set_django_tech",
            "passed": mcp_server._detect_technology(
                "Audit why irrelevant Django migration guidance leaked into product readiness",
                "do not debug Django migrations",
            ) == "",
        },
        {
            "name": "high_similarity_meta_only_trace_rejected",
            "passed": confidence_gate.trace_match_is_confident(
                irrelevant_trace,
                query="public self-service trust hardening product readiness first-answer relevance",
            ) is False,
        },
        {
            "name": "irrelevant_real_trace_only_guidance_not_injectable",
            "passed": confidence_gate.guidance_is_safe_to_inject(
                irrelevant_guidance,
                "Harden public self-service trust/readiness first-answer relevance.",
                "",
            ) is False,
        },
        {
            "name": "concrete_permission_signal_still_allowed",
            "passed": confidence_gate.permission_guidance_matches_task(PERMISSION_TASK, PERMISSION_CONTEXT) is True,
        },
    ]
    return checks


def compile_gate() -> dict[str, Any]:
    checks: list[dict[str, Any]] = _confidence_gate_canaries()
    with tempfile.TemporaryDirectory(prefix="borg-cold-start-trust-") as tmp:
        tmp_root = Path(tmp)
        meta_stdio = _stdio_observe(META_TRUST_TASK, META_TRUST_CONTEXT, tmp_root)
        meta_passed, meta_blockers = _meta_output_passed(meta_stdio.get("text", ""))
        checks.append({
            "name": "stdio_meta_trust_prompt_fails_closed",
            "passed": bool(meta_stdio.get("passed") and meta_passed),
            "blockers": meta_blockers,
            "stderr_tail": meta_stdio.get("stderr", "")[-1000:],
            "text_excerpt": meta_stdio.get("text", "")[:1200],
        })

        permission_stdio = _stdio_observe(PERMISSION_TASK, PERMISSION_CONTEXT, tmp_root)
        permission_lower = permission_stdio.get("text", "").lower()
        permission_action = next((line for line in permission_lower.splitlines() if line.startswith("action:")), "")
        checks.append({
            "name": "stdio_concrete_permission_prompt_gets_specific_guidance",
            "passed": bool(
                permission_stdio.get("passed")
                and ("chmod +x" in permission_lower or "bash-permission-denied" in permission_lower)
                and "npm" not in permission_action
                and "~/.npm-global" not in permission_action
                and "no_confident_match" not in permission_lower
            ),
            "stderr_tail": permission_stdio.get("stderr", "")[-1000:],
            "text_excerpt": permission_stdio.get("text", "")[:1200],
        })

    blockers = [
        f"{check['name']}: {', '.join(check.get('blockers') or ['failed'])}"
        for check in checks
        if not check.get("passed")
    ]
    return {
        "schema_version": 1,
        "gate_type": "cold_start_trust_hardening",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": not blockers,
        "checks": checks,
        "blockers": blockers,
        "trust_policy": (
            "Borg must fail closed with NO_CONFIDENT_MATCH for meta/product/readiness prompts, "
            "must not inject unrelated framework guidance, and must preserve concrete error guidance for exact failures."
        ),
        "bad_answer_feedback_path": {
            "agent_fast_path": "call borg_rate(helpful=False) immediately after a bad suggestion",
            "durable_memory_path": "call borg_record_failure(error_pattern, pack_id, phase, approach, outcome='failure') when the bad path is concrete",
            "human_path": "open a GitHub issue using the bad-answer report template or paste the redacted transcript into first-10 evidence intake",
        },
    }


def write_report(snapshot: dict[str, Any]) -> None:
    verdict = "PASS" if snapshot["passed"] else "FAIL"
    lines = [
        "# Borg cold-start trust hardening",
        "",
        f"Generated: `{snapshot['generated_at_utc']}`",
        f"Gate: **{verdict}**",
        "",
        "## Why this gate exists",
        "",
        "One irrelevant first Borg answer can destroy trust. Cold-start prompts must therefore fail closed instead of forcing a weak pack or random framework fix.",
        "",
        "## Hard policy",
        "",
        snapshot["trust_policy"],
        "",
        "## Scope and runtime boundary",
        "",
        "This gate proves fresh source/stdio behavior from this checkout. It does not prove that a long-lived served Hermes/MCP runtime has reloaded this code. Served runtime GO additionally requires `borg_runtime_fingerprint` with `version_matches_source=true`, `observe_behavior_canary.passed=true`, and `reload_status=loaded_code_matches_source_behavior`.",
        "",
        "## Checks",
        "",
    ]
    for check in snapshot["checks"]:
        lines.append(f"- `{check['name']}`: `{'PASS' if check.get('passed') else 'FAIL'}`")
    lines.extend(["", "## Bad-answer feedback path", ""])
    feedback = snapshot["bad_answer_feedback_path"]
    lines.extend([
        f"- Agent fast path: `{feedback['agent_fast_path']}`",
        f"- Durable memory path: `{feedback['durable_memory_path']}`",
        f"- Human path: {feedback['human_path']}",
        "",
        "## Public rollout boundary",
        "",
        "This gate is required for controlled beta and public self-serve, but it is not sufficient for public self-serve. Broad public launch still requires row-derived first-10 external-user evidence.",
        "",
        "## Evidence artifacts",
        "",
        "- `eval/cold_start_trust_gate_snapshot.json`",
        "- `tests/readiness/test_confidence_gate.py`",
        "- `tests/mcp/test_borg_observe_confidence_gate.py`",
        "- `tests/mcp/test_stdio_transport.py`",
        "",
    ])
    if snapshot["blockers"]:
        lines.extend(["## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in snapshot["blockers"])
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Borg cold-start trust hardening canaries")
    parser.add_argument("--no-write", action="store_true", help="Do not write snapshot/report artifacts")
    args = parser.parse_args(argv)

    snapshot = compile_gate()
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_report(snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
