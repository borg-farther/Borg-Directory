#!/usr/bin/env python3
"""Compile Borg public self-serve launch readiness.

This is the canonical hard gate for broad public self-serve. It is intentionally
stricter than local first-user or synthetic load gates: it requires row-derived
external-user evidence, PyPI latest/fresh-install proof, MCP stdio canary proof,
and docs/claim consistency. It returns nonzero until those are all true.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.first_10_evidence import evaluate_scoreboard

SNAPSHOT = ROOT / "eval" / "public_self_serve_launch_gate_snapshot.json"
REPORT = ROOT / "docs" / "PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"

CURRENT_CLAIM_DOCS = [
    Path("README.md"),
    Path("PROJECT_STATUS.md"),
    Path("GO_NO_GO_DECISION.md"),
    Path("UAT_RESULTS.md"),
    Path("docs/README.md"),
    Path("docs/READINESS.md"),
    Path("docs/INSTALL.md"),
    Path("docs/QUICKSTART.md"),
    Path("docs/TRYING_BORG.md"),
    Path("docs/MCP_SETUP.md"),
    Path("docs/ONBOARDING.md"),
    Path("docs/FIRST_10_BETA_READINESS.md"),
    Path("docs/20260514_FIRST_10_USER_INVITE_PACKET.md"),
    Path("docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md"),
    Path("docs/20260517_BORG_100_REAL_USER_READINESS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/20260522_PUBLIC_PRESENTATION_AUDIT.md"),
    Path("docs/20260522_BORG_PRODUCTION_DAY_ONE_HARDENING_PLAN.md"),
    Path("docs/20260522_BORG_339_RELEASE_PREFLIGHT_PUBLISHED.md"),
    Path("docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"),
    Path("docs/VALUE_COMMUNICATION_DASHBOARD.md"),
    Path("docs/VALUE_COMMUNICATION_DASHBOARD.html"),
    Path("docs/BORG_PROOF_DASHBOARD.md"),
    Path("docs/BORG_PROOF_DASHBOARD.html"),
    Path("docs/public/proof-dashboard/index.html"),
    Path("docs/SECURITY_HARDENING_BASELINE.md"),
    Path("docs/PRIVACY_MODEL.md"),
    Path("docs/PROMPT_INJECTION_THREAT_MODEL.md"),
    Path("docs/TRUST_AND_PROMOTION.md"),
    Path("docs/REVOCATION_AND_DELETION.md"),
    Path("docs/LEARNING_ATOM_SCHEMA.md"),
    Path("eval/borg_proof_dashboard.json"),
]

UNSUPPORTED_WHEN_BLOCKED = [
    (re.compile(r"(?i)public\s+self[- ]serve\s+launch\s*[:\-]\s*(?:\*\*)?\s*(go|yes|ship|ready|approved)\b"), "public self-serve launch GO/ready claim"),
    (re.compile(r"(?im)^\s*Decision\s*:\s*(?:\*\*)?\s*(go|yes|ready)\b"), "unqualified GO/ready decision claim"),
    (re.compile(r"(?i)\bdecision\s*[:\-]\s*(?:\*\*)?\s*ship\b"), "unqualified SHIP decision claim"),
    (re.compile(r"(?i)\bcompletion\s+lift\s*[:\-].*\+\d+%"), "completion-lift claim without external evidence"),
    (re.compile(r"(?i)\bstatistically\s+significant\b.*\b(agent|external|lift|completion)"), "statistically significant external/agent lift claim"),
    (re.compile(r"(?i)\bfrontier[- ]better[- ]than\b.*\b(proven|yes|true|go)"), "frontier-better-than proven claim"),
    (re.compile(r"(?i)Ready\s+to\s+share\s+Git\s+now\?\W{0,80}YES"), "stale Git-sharing YES claim"),
    (re.compile(r"(?i)version_package"), "stale proof-dashboard version metric"),
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def fetch_pypi_latest(package: str = "agent-borg", timeout: int = 30) -> dict[str, Any]:
    url = f"https://pypi.org/pypi/{package}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "Borg-public-self-serve-gate/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        "package": package,
        "url": url,
        "version": data.get("info", {}).get("version"),
        "project_urls": data.get("info", {}).get("project_urls") or {},
        "requires_dist": data.get("info", {}).get("requires_dist") or [],
    }


def pypi_latest_check(expected_version: str, *, fetch_network: bool = True, pypi_data: dict[str, Any] | None = None) -> dict[str, Any]:
    if pypi_data is None and fetch_network:
        try:
            pypi_data = fetch_pypi_latest()
        except Exception as exc:  # pragma: no cover - network failure shape is environment-specific
            return {"passed": False, "error": str(exc), "expected_version": expected_version}
    elif pypi_data is None:
        return {"passed": False, "error": "network disabled and no PyPI data provided", "expected_version": expected_version}

    project_urls = pypi_data.get("project_urls") or {}
    required_urls = {
        "Homepage": "https://github.com/borg-farther/Borg-Directory",
        "Repository": "https://github.com/borg-farther/Borg-Directory",
        "Documentation": "https://github.com/borg-farther/Borg-Directory#readme",
        "Issues": "https://github.com/borg-farther/Borg-Directory/issues",
    }
    url_missing = sorted(set(required_urls) - set(project_urls))
    url_mismatches = {
        key: {"expected": expected, "actual": project_urls.get(key)}
        for key, expected in required_urls.items()
        if project_urls.get(key) != expected
    }
    latest = pypi_data.get("version")
    passed = latest == expected_version and not url_missing and not url_mismatches
    return {
        "passed": passed,
        "package": pypi_data.get("package", "agent-borg"),
        "latest_version": latest,
        "expected_version": expected_version,
        "url_missing": url_missing,
        "url_mismatches": url_mismatches,
        "requires_dist": pypi_data.get("requires_dist") or [],
        "project_urls": project_urls,
    }


def first_user_release_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    results = data.get("results") or []
    failures = [item.get("name") for item in results if not item.get("passed")]
    return {
        "passed": bool(data.get("success")) and not failures,
        "exists": bool(data),
        "generated_at_utc": data.get("generated_at_utc"),
        "passed_count": sum(1 for item in results if item.get("passed")),
        "failed_count": len(failures),
        "failures": failures,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
    }


def pypi_fresh_install_check(path: Path, expected_version: str) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {"passed": False, "exists": False, "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "error": "missing PyPI fresh-install snapshot"}
    results = data.get("results") or []
    failures = [item.get("name") for item in results if not item.get("passed")]
    mcp = data.get("mcp_stdio_canary") or {}
    passed = bool(data.get("success")) and data.get("version") == expected_version and not failures and bool(mcp.get("passed"))
    return {
        "passed": passed,
        "exists": True,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "generated_at_utc": data.get("generated_at_utc"),
        "version": data.get("version"),
        "expected_version": expected_version,
        "failed_count": len(failures),
        "failures": failures,
        "mcp_stdio_canary_passed": bool(mcp.get("passed")),
        "mcp_server_info": mcp.get("server_info"),
    }


def docs_claim_guard(paths: list[Path], expected_version: str, *, public_evidence_ready: bool) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checked: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(str(rel))

        for match in re.finditer(r"agent-borg==(?P<version>\d+\.\d+\.\d+)", text):
            if match.group("version") != expected_version:
                violations.append({
                    "path": str(rel),
                    "kind": "stale agent-borg pin",
                    "detail": f"found agent-borg=={match.group('version')} expected agent-borg=={expected_version}",
                })

        stale_release_tokens = [
            (r"BORG_338_RELEASE_PREFLIGHT", "stale 3.3.8 release-proof reference"),
            (r"release_preflight_3_3_8", "stale 3.3.8 release-preflight snapshot reference"),
            (r"serverInfo\.version\s*==\s*3\.3\.8", "stale MCP version claim"),
        ]
        for pattern, label in stale_release_tokens:
            match = re.search(pattern, text)
            if match:
                violations.append({"path": str(rel), "kind": label, "detail": match.group(0)[:180]})

        if re.search(r"(?im)^\s*(?:python\s+-m\s+)?pipx\s+install\s+git\+https://github\.com/borg-farther/Borg-Directory\.git\b", text):
            violations.append({"path": str(rel), "kind": "public git+ install path", "detail": "current public first-user docs must use PyPI agent-borg, not git+ source install"})

        if not public_evidence_ready:
            for pattern, label in UNSUPPORTED_WHEN_BLOCKED:
                match = pattern.search(text)
                if match:
                    line = text[: match.start()].count("\n") + 1
                    line_text = text.splitlines()[line - 1] if line - 1 < len(text.splitlines()) else match.group(0)
                    negated = re.search(r"(?i)\b(not claimed|not proven|unproven|no claim|does not claim|without claiming)\b", line_text)
                    if "statistically significant" in label and negated:
                        continue
                    violations.append({"path": str(rel), "line": line, "kind": label, "detail": match.group(0)[:180]})

    return {"passed": not violations, "checked": checked, "violations": violations}


def first_10_evidence_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {"passed": False, "exists": False, "error": "missing first-10 scoreboard"}
    evidence = evaluate_scoreboard(data)
    passed = bool(evidence["schema_valid"] and evidence["thresholds_passed"] and evidence["stored_consistency"]["passed"])
    derived = evidence["derived_counts"]
    thresholds = evidence["thresholds"]
    return {
        "passed": passed,
        "exists": True,
        "row_count": evidence["row_count"],
        "counted_external_rows": evidence["counted_external_rows"],
        "derived_counts": derived,
        "thresholds": thresholds,
        "stored_consistency": evidence["stored_consistency"],
        "invalid_rows": evidence["invalid_rows"],
        "blockers": evidence["blockers"],
        "scoreboard_gate": (data.get("current_verdict") or {}).get("public_self_serve_launch_gate"),
    }


def compile_gate(*, fetch_network: bool = True, pypi_data: dict[str, Any] | None = None) -> dict[str, Any]:
    version = source_version()
    first_10 = first_10_evidence_check(ROOT / "eval" / "first_10_user_scoreboard.json")
    first_user = first_user_release_check(ROOT / "eval" / "first_user_release_gate_snapshot.json")
    pypi_latest = pypi_latest_check(version, fetch_network=fetch_network, pypi_data=pypi_data)
    pypi_fresh = pypi_fresh_install_check(ROOT / "eval" / "pypi_fresh_install_snapshot.json", version)
    docs = docs_claim_guard(CURRENT_CLAIM_DOCS, version, public_evidence_ready=first_10["passed"])

    infrastructure_ready = bool(first_user["passed"] and pypi_latest["passed"] and pypi_fresh["passed"] and docs["passed"])
    public_self_serve_ready = bool(infrastructure_ready and first_10["passed"])
    blockers: list[str] = []
    if not first_user["passed"]:
        blockers.append("first-user local release gate snapshot is missing or failing")
    if not pypi_latest["passed"]:
        blockers.append("PyPI latest metadata does not match source version or required project URLs")
    if not pypi_fresh["passed"]:
        blockers.append("PyPI fresh-install + MCP stdio canary snapshot is missing or failing")
    if not docs["passed"]:
        blockers.append("public docs/claim guard found stale install pins or unsupported launch/value claims")
    if not first_10["passed"]:
        blockers.extend(first_10.get("blockers") or ["first-10 external-user evidence has not passed"])

    return {
        "schema_version": 1,
        "gate_type": "public_self_serve_launch",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": version,
        "ready_for_controlled_first_10_beta": infrastructure_ready,
        "ready_for_public_self_serve_launch": public_self_serve_ready,
        "max_recommended_real_users_now": 100 if public_self_serve_ready else 10 if infrastructure_ready else 0,
        "gates": {
            "first_user_release": first_user,
            "pypi_latest": pypi_latest,
            "pypi_fresh_install_and_mcp_stdio": pypi_fresh,
            "docs_claim_guard": docs,
            "first_10_external_evidence": first_10,
        },
        "blockers": blockers,
        "truth_policy": "Public self-serve is GO only after PyPI/fresh-install/MCP/docs gates pass AND row-derived first-10 external-user evidence passes. Synthetic users and aggregate-only edits never count.",
    }


def write_report(snapshot: dict[str, Any]) -> None:
    verdict = "GO" if snapshot["ready_for_public_self_serve_launch"] else "NO-GO"
    lines = [
        "# Borg public self-serve launch go/no-go",
        "",
        f"Generated: {snapshot['generated_at_utc']}",
        f"Source version: `{snapshot['source_version']}`",
        "",
        f"Public self-serve launch: **{verdict}**",
        f"Controlled first-10 beta infrastructure: **{'GO' if snapshot['ready_for_controlled_first_10_beta'] else 'NO-GO'}**",
        f"Max recommended real users now: **{snapshot['max_recommended_real_users_now']}**",
        "",
        "## Hard rule",
        "",
        snapshot["truth_policy"],
        "",
        "## Gate results",
        "",
    ]
    for name, gate in snapshot["gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if gate.get('passed') else 'FAIL'}`")
    lines.extend(["", "## Blockers", ""])
    if snapshot["blockers"]:
        lines.extend(f"- {blocker}" for blocker in snapshot["blockers"])
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Evidence artifacts",
        "",
        "- `eval/public_self_serve_launch_gate_snapshot.json`",
        "- `eval/first_10_user_scoreboard.json`",
        "- `eval/pypi_fresh_install_snapshot.json`",
        "- `eval/first_user_release_gate_snapshot.json`",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Borg public self-serve launch readiness")
    parser.add_argument("--no-network", action="store_true", help="Do not query PyPI; gate fails unless test code injects PyPI data")
    parser.add_argument("--no-write", action="store_true", help="Do not write snapshot/report artifacts")
    args = parser.parse_args(argv)

    snapshot = compile_gate(fetch_network=not args.no_network)
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_report(snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["ready_for_public_self_serve_launch"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
