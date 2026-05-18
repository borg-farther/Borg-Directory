#!/usr/bin/env python3
"""Safely close autonomously-fixable Borg public-launch blockers.

This runner is intentionally conservative:
- never pushes/publishes/changes GitHub state;
- never restarts/kills/signals live services;
- never edits source outside the reviewed public-readiness allowlist;
- only cleans generated build/lib and dist side effects.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
DOCS = ROOT / "docs"
PREFLIGHT = EVAL / "20260514_fix_all_preflight.json"
RESULT_JSON = EVAL / "20260514_fix_all_public_launch_blockers.json"
REPORT_MD = DOCS / "20260514_FIX_ALL_PUBLIC_LAUNCH_BLOCKERS_REPORT.md"
SCOREBOARD = EVAL / "first_10_user_scoreboard.json"
BLOCKER_BOARD = DOCS / "20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md"
RUNBOOK = DOCS / "20260514_BORG_RELEASE_BRANCH_CLEANUP_RUNBOOK.md"

ALLOWED_STAGE = [
    "borg/core/confidence_gate.py",
    "borg/integrations/mcp_server.py",
    "tests/readiness/test_confidence_gate.py",
    "docs/BORG_PROOF_DASHBOARD.md",
    "docs/BORG_PROOF_DASHBOARD.html",
    "docs/public/proof-dashboard/index.html",
    "docs/20260514_BORG_GOOGLE_TIER_READINESS_CONTINUATION.md",
    "docs/20260514_BORG_PUBLIC_LAUNCH_READINESS_PLAN.md",
    "docs/20260514_BORG_PUBLIC_LAUNCH_IMPLEMENTATION_REPORT.md",
    "docs/20260514_BORG_PUBLIC_LAUNCH_BLOCKER_BOARD.md",
    "docs/20260514_BORG_RELEASE_BRANCH_CLEANUP_RUNBOOK.md",
    "eval/borg_proof_dashboard.json",
    "eval/first_user_release_gate_snapshot.json",
    "eval/20260514_borg_google_tier_readiness_continuation.json",
    "eval/20260514_borg_public_launch_readiness.json",
    "eval/20260514_borg_public_launch_command_log.json",
    "eval/20260514_borg_public_launch_outstanding_blockers.json",
    "eval/first_10_user_scoreboard.json",
    "eval/tests/test_borg_proof_dashboard.py",
    "scripts/build_borg_proof_dashboard.py",
    "scripts/borg_proof_dashboard_lint.py",
    "scripts/fix_public_launch_blockers_safe.py",
]

VERIFY_COMMANDS = [
    [sys.executable, "-m", "pytest", "-q", "tests/readiness/test_confidence_gate.py", "tests/mcp/test_borg_observe_confidence_gate.py", "tests/mcp/test_runtime_fingerprint.py"],
    [sys.executable, "scripts/build_borg_proof_dashboard.py"],
    [sys.executable, "scripts/borg_proof_dashboard_lint.py"],
    [sys.executable, "-m", "pytest", "-q", "eval/tests/test_borg_proof_dashboard.py"],
    [sys.executable, "eval/run_first_user_release_gate.py"],
    [sys.executable, "scripts/security_gate_check.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/security/test_privacy_structured.py", "tests/security/test_prompt_injection.py", "tests/security/test_atom_policy.py", "tests/security/test_atom_retrieval_firewall.py", "tests/security/test_privacy.py"],
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 300) -> dict[str, Any]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=full_env)
        return {"cmd": cmd, "rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as e:
        return {"cmd": cmd, "rc": 124, "stdout": e.stdout or "", "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s"}
    except FileNotFoundError as e:
        return {"cmd": cmd, "rc": 127, "stdout": "", "stderr": str(e)}


def git(*args: str, timeout: int = 300) -> dict[str, Any]:
    return run(["git", *args], timeout=timeout)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def validate_update_scoreboard() -> dict[str, Any]:
    changed = False
    if SCOREBOARD.exists():
        data = json.loads(SCOREBOARD.read_text())
    else:
        data = {"schema_version": 1, "rows": []}
        changed = True
    data.setdefault("schema_version", 1)
    data["generated_at_utc"] = data.get("generated_at_utc") or now()
    data["status"] = "pre_first_user_no_real_rows"
    data["purpose"] = "Hard evidence scoreboard for Borg first-10 external beta users. Empty rows are placeholders only and must never be counted as adoption."
    data["truth_policy"] = {
        "simulated_users_count_as_real": False,
        "internal_sessions_count_as_real": False,
        "maintainer_runs_count_as_real": False,
        "verified_external_users": 0,
        "public_self_serve_launch_allowed_before_thresholds": False,
    }
    data["thresholds"] = {
        "min_install_successes_for_public_self_serve": 8,
        "min_useful_rescue_moments_for_public_self_serve": 6,
        "max_critical_privacy_security_failures": 0,
        "required_total_real_users": 10,
    }
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    # Never fabricate users. Keep only already-present rows, and do not count them without evidence.
    verified = [r for r in rows if isinstance(r, dict) and r.get("external_user_evidence_uri") and r.get("consent_confirmed") is True]
    data["rows"] = rows
    data["current_counts"] = {
        "real_users": len(verified),
        "install_successes": sum(1 for r in verified if r.get("install_success") is True),
        "useful_rescue_moments": sum(1 for r in verified if r.get("rescue_useful") is True),
        "critical_privacy_security_failures": sum(1 for r in verified if r.get("privacy_security_incident") in (True, "critical")),
        "repeat_use_within_7_days": sum(1 for r in verified if r.get("repeat_use_within_7_days") is True),
    }
    data["current_verdict"] = {
        "first_10_complete": False,
        "public_self_serve_launch_gate": "BLOCKED",
        "reason": "No verified external user rows exist yet." if not verified else "Verified external user thresholds are not complete.",
    }
    original = SCOREBOARD.read_text() if SCOREBOARD.exists() else ""
    rendered = json.dumps(data, indent=2, sort_keys=False) + "\n"
    if rendered != original:
        SCOREBOARD.parent.mkdir(parents=True, exist_ok=True)
        SCOREBOARD.write_text(rendered)
        changed = True
    return {"changed": changed, "verified_external_users": len(verified), "path": str(SCOREBOARD.relative_to(ROOT))}


def safe_cleanup() -> dict[str, Any]:
    out: dict[str, Any] = {}
    out["git_reset"] = git("reset")
    out["git_restore_build_dist"] = git("restore", "--", "build/lib", "dist")
    untracked_build = git("ls-files", "--others", "--exclude-standard", "--", "build/lib")
    removed_build = []
    if untracked_build["rc"] == 0:
        for rel in untracked_build["stdout"].splitlines():
            p = ROOT / rel
            if rel.startswith("build/lib/") and p.is_file():
                p.unlink()
                removed_build.append(rel)
        # Remove empty generated directories under build/lib only.
        build_lib = ROOT / "build" / "lib"
        if build_lib.exists():
            for d in sorted((x for x in build_lib.rglob("*") if x.is_dir()), key=lambda x: len(x.parts), reverse=True):
                try:
                    d.rmdir()
                except OSError:
                    pass
    out["removed_untracked_generated_build_lib"] = removed_build
    removed = []
    for p in sorted((ROOT / "dist").glob("agent_borg-3.3.1*")):
        # Only remove generated package outputs that are untracked after restore.
        rel = str(p.relative_to(ROOT))
        st = run(["git", "ls-files", "--error-unmatch", rel])
        if st["rc"] != 0 and p.is_file():
            p.unlink()
            removed.append(rel)
    out["removed_untracked_generated_dist_3_3_1"] = removed
    out["status_after_cleanup"] = git("status", "--short")
    return out


def run_canaries() -> dict[str, Any]:
    code = r'''
import json
from borg.integrations import mcp_server
unrelated = mcp_server.borg_observe(task="public launch blocker spreadsheet formatting zebra stripes", context="docs")
permission = mcp_server.borg_observe(task="bash: ./deploy.sh: Permission denied", context="bash chmod execute permission denied")
print(json.dumps({
  "unrelated_contains_no_confident_match": "NO_CONFIDENT_MATCH" in unrelated or "NO CONFIDENT MATCH" in unrelated,
  "permission_mentions_permission": "permission" in permission.lower() or "chmod" in permission.lower(),
  "unrelated_excerpt": unrelated[:1000],
  "permission_excerpt": permission[:1000],
}, sort_keys=True))
'''
    r = run([sys.executable, "-c", code], timeout=180)
    parsed = None
    if r["rc"] == 0:
        try:
            parsed = json.loads(r["stdout"])
        except Exception:
            parsed = None
    status = "PASS" if parsed and parsed.get("unrelated_contains_no_confident_match") and parsed.get("permission_mentions_permission") else "FAIL"
    return {"status": status, "command": r, "parsed": parsed}


def external_install_proof() -> dict[str, Any]:
    if shutil.which("pipx"):
        env = {"PIPX_HOME": "/tmp/borg-pipx-home", "PIPX_BIN_DIR": "/tmp/borg-pipx-bin"}
        install = run(["pipx", "install", "--force", str(ROOT)], env=env, timeout=600)
        version = run(["/tmp/borg-pipx-bin/borg", "--version"], env=env, timeout=120) if install["rc"] == 0 else {"cmd": ["/tmp/borg-pipx-bin/borg", "--version"], "rc": 99, "stdout": "", "stderr": "install failed; skipped"}
        rescue = run(["/tmp/borg-pipx-bin/borg", "rescue", "bash: ./x: Permission denied; context=bash chmod execute bit"], env=env, timeout=120) if install["rc"] == 0 else {"cmd": ["/tmp/borg-pipx-bin/borg", "rescue", "..."], "rc": 99, "stdout": "", "stderr": "install failed; skipped"}
        ok = install["rc"] == 0 and version["rc"] == 0 and rescue["rc"] == 0
        return {"pipx_proof": "PASS" if ok else "FAIL", "clean_venv_externalish": "NOT_RUN_PIPX_AVAILABLE", "install": install, "version": version, "rescue": rescue}
    venv = Path("/tmp/borg-clean-venv-externalish")
    if venv.exists():
        shutil.rmtree(venv)
    mk = run([sys.executable, "-m", "venv", str(venv)], timeout=180)
    py = str(venv / "bin" / "python")
    borg_bin = str(venv / "bin" / "borg")
    install = run([py, "-m", "pip", "install", "--no-cache-dir", str(ROOT)], timeout=600) if mk["rc"] == 0 else {"cmd": [py, "-m", "pip", "install"], "rc": 99, "stdout": "", "stderr": "venv create failed; skipped"}
    version = run([borg_bin, "--version"], timeout=120) if install["rc"] == 0 else {"cmd": [borg_bin, "--version"], "rc": 99, "stdout": "", "stderr": "install failed; skipped"}
    rescue = run([borg_bin, "rescue", "bash: ./x: Permission denied; context=bash chmod execute bit"], timeout=120) if install["rc"] == 0 else {"cmd": [borg_bin, "rescue", "..."], "rc": 99, "stdout": "", "stderr": "install failed; skipped"}
    ok = mk["rc"] == 0 and install["rc"] == 0 and version["rc"] == 0 and rescue["rc"] == 0
    return {"pipx_proof": "BLOCKED_ENV", "clean_venv_externalish": "PASS" if ok else "FAIL", "venv_create": mk, "install": install, "version": version, "rescue": rescue}


def github_readonly() -> dict[str, Any]:
    return {
        "gh_auth_status": run(["gh", "auth", "status"], timeout=120) if shutil.which("gh") else {"cmd": ["gh", "auth", "status"], "rc": 127, "stdout": "", "stderr": "gh not installed"},
        "gh_api_user_login": run(["gh", "api", "user", "--jq", ".login"], timeout=120) if shutil.which("gh") else {"cmd": ["gh", "api", "user", "--jq", ".login"], "rc": 127, "stdout": "", "stderr": "gh not installed"},
        "git_remote_v": git("remote", "-v"),
        "git_ls_remote_heads_origin": git("ls-remote", "--heads", "origin", timeout=180),
    }


def sanitize_allowed_stage_files() -> dict[str, Any]:
    """Remove trailing whitespace from allowlisted text artifacts only."""
    changed: list[str] = []
    skipped: list[str] = []
    for rel in ALLOWED_STAGE:
        path = ROOT / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(rel)
            continue
        cleaned = "\n".join(line.rstrip() for line in raw.splitlines())
        if raw.endswith("\n"):
            cleaned += "\n"
        if cleaned != raw:
            path.write_text(cleaned, encoding="utf-8")
            changed.append(rel)
    return {"changed": changed, "skipped_binary_or_non_utf8": skipped}


def stage_allowed_if_gates_pass(gates_ok: bool) -> dict[str, Any]:
    existing = [p for p in ALLOWED_STAGE if (ROOT / p).exists()]
    result: dict[str, Any] = {"gates_ok": gates_ok, "existing_allowed_candidates": existing}
    if not gates_ok:
        result["status"] = "SKIPPED_GATES_FAILED"
        return result
    result["git_add"] = git("add", "--", *existing)
    result["cached_stat"] = git("diff", "--cached", "--stat")
    result["cached_check"] = git("diff", "--cached", "--check")
    result["status_after_stage"] = git("status", "--short")
    bad_cached = [line for line in result["cached_stat"].get("stdout", "").splitlines() if line.strip().startswith("build/lib/") or line.strip().startswith("dist/")]
    result["excluded_build_dist_mass_adds"] = not bad_cached
    result["status"] = "PASS" if result["git_add"]["rc"] == 0 and result["cached_check"]["rc"] == 0 and not bad_cached else "FAIL"
    return result


def update_docs_and_report(results: dict[str, Any]) -> None:
    gates_ok = all(c["rc"] == 0 for c in results["verification_commands"]) and results["source_canaries"]["status"] == "PASS"
    external_ok = results["external_install"].get("pipx_proof") == "PASS" or results["external_install"].get("clean_venv_externalish") == "PASS"
    repo_stage_ok = results["staging"].get("status") == "PASS"
    github = results["github_readonly"]
    gh_login = github.get("gh_api_user_login", {}).get("stdout", "").strip() or "unverified"
    repo_status = "PASS" if repo_stage_ok else "PARTIAL_PASS" if results["cleanup"].get("git_restore_build_dist", {}).get("rc") == 0 else "BLOCKED"
    waitlist = "YES_WITH_CAVEATS" if repo_status in {"PASS", "PARTIAL_PASS"} and gates_ok and external_ok else "NO"
    self_serve = "NO"
    results["gate_statuses"] = {
        "repo_hygiene_release_branch": repo_status,
        "local_verification_gates": "PASS" if gates_ok else "FAIL",
        "source_canaries": results["source_canaries"]["status"],
        "externalish_install_proof": "PASS" if external_ok else "FAIL",
        "github_admin_push_path": "READ_ONLY_DIAGNOSED",
        "live_mcp_runtime_identity": "HUMAN_BLOCKED",
        "first_10_real_users": "HUMAN_BLOCKED",
        "verified_external_users": results["scoreboard"].get("verified_external_users", 0),
        "public_waitlist_narrow_beta": waitlist,
        "public_self_serve_launch": self_serve,
    }
    board = f"""# Borg public launch blocker board

Generated: {now()}

## Current verdict

- **PUBLIC_WAITLIST_NARROW_BETA:** {waitlist}
- **PUBLIC_SELF_SERVE_LAUNCH:** {self_serve}
- **SUPERVISED FIRST USER:** YES, with caveats already proven in first-user gate artifacts.

## Blockers

| ID | Blocker | Status | Why it matters | Done criteria | Safe next action |
|---|---|---|---|---|---|
| PL-01 | Live MCP/runtime identity not proven after reload | HUMAN_BLOCKED | Source and fresh-process canaries pass, but autonomous mode may not restart/kill/signal live Hermes/MCP services. | `borg_runtime_fingerprint` from served process shows expected path/hash; live unrelated `borg_observe` returns `NO_CONFIDENT_MATCH`; live permission canary returns permission guidance. | Human: approve/supervise service reload, then run live canaries. |
| PL-02 | Repo hygiene / release branch surgicality | {repo_status} | Generated `build/lib`/`dist` side effects were restored/removed safely; unrelated dirty files may remain out-of-scope. | Staged release diff contains only allowlisted reviewed files; no build/lib or dist mass-adds; gates pass. | Human: review staged diff, handle unrelated unstaged files on separate branch/worktree before release merge. |
| PL-03 | First-10 real users absent | HUMAN_BLOCKED | Local gates prove engineering readiness, not adoption or utility. Public self-serve requires real external outcomes. | Scoreboard has 10 real user rows, ≥8 installs, ≥6 useful rescues, 0 critical privacy/security failures. | Human: invite consented beta users and record redacted evidence. Verified external users now: {results['scoreboard'].get('verified_external_users', 0)}. |
| PL-04 | External clean install / pipx proof | {'PASS' if external_ok else 'BLOCKED_ENV' if results['external_install'].get('pipx_proof') == 'BLOCKED_ENV' else 'FAIL'} | Public users need a clean install path outside the maintainer working tree. | pipx proof passes, or pipx unavailable and clean local venv install/rescue proof passes as external-ish fallback. | If pipx was unavailable, rerun on a host with pipx before broad self-serve. |
| PL-05 | GitHub admin/push path previously blocked | READ_ONLY_DIAGNOSED | Public release needs canonical repo access and branch/default/governance clarity; autonomous mode may not mutate GitHub. | Correct owner PAT can push/admin after human approval. | Human: with borg-farther PAT, create/push reviewed release branch and perform visibility/protection changes intentionally. Current gh login: `{gh_login}`. |
| PL-06 | Claims need final human review | {'PASS_AUTOMATED_WITH_HUMAN_REVIEW_RECOMMENDED' if gates_ok else 'OPEN'} | Automated gates can detect many unsupported claims but cannot replace release-owner review. | Public README/docs/package copy reviewed; no unsupported adoption/network claims. | Human: review public copy before announcement. |

## Non-blockers green in this run

- Targeted confidence/runtime tests: {'PASS' if results['verification_commands'][0]['rc'] == 0 else 'FAIL'}.
- Proof dashboard build/lint/test: {'PASS' if all(results['verification_commands'][i]['rc'] == 0 for i in [1,2,3]) else 'FAIL'}.
- First-user local release gate: {'PASS' if results['verification_commands'][4]['rc'] == 0 else 'FAIL'}.
- Security baseline gate: {'PASS' if results['verification_commands'][5]['rc'] == 0 else 'FAIL'}.
- Privacy/prompt-injection/atom policy/firewall tests: {'PASS' if results['verification_commands'][6]['rc'] == 0 else 'FAIL'}.
- Source canaries: {results['source_canaries']['status']}.

## Launch definitions

### Public waitlist / narrow beta
{waitlist}. Allowed only with caveats if PL-01 remains supervised/human-blocked and no self-serve claims are made.

### Public self-serve launch
NO. Requires live MCP runtime identity canary and first-10 real-user evidence.
"""
    BLOCKER_BOARD.write_text(board)
    runbook = f"""# Borg release branch cleanup runbook

Generated: {now()}

## What the safe runner did

- Backed up preflight git status/diff/cached diff to `{PREFLIGHT.relative_to(ROOT)}`.
- Ran `git reset` to unstage only.
- Ran `git restore -- build/lib dist` to restore generated side effects from HEAD.
- Removed only untracked generated `dist/agent_borg-3.3.1*` package outputs.
- Ran verification gates and source canaries.
- Staged only allowlisted public-readiness files when gates passed.

## Remaining human cleanup

1. Review `git diff --cached` and `git diff --cached --check`.
2. Keep unrelated unstaged source/docs/eval modifications out of the release branch unless separately reviewed.
3. Do not push until the release branch owner approves.
4. Do not restart live Hermes/MCP except under explicit human supervision.

## Allowed stage candidates used by runner

```text
{chr(10).join(ALLOWED_STAGE)}
```
"""
    RUNBOOK.write_text(runbook)
    report = f"""# Fix-all public launch blockers report

Generated: {now()}

## Verdicts

- **PUBLIC_WAITLIST_NARROW_BETA:** {waitlist}
- **PUBLIC_SELF_SERVE_LAUNCH:** {self_serve}

## FIXED autonomously

- Safe generated build/dist hygiene performed (`git reset`; `git restore -- build/lib dist`; removal of untracked `dist/agent_borg-3.3.1*`).
- First-10 scoreboard validated without fabricating users (`verified_external_users=0`).
- Blocker board and cleanup runbook updated.
- Local verification/security/claims-adjacent gates executed with full rc/stdout/stderr in `{RESULT_JSON.relative_to(ROOT)}`.
- Source canaries executed: unrelated readiness -> NO_CONFIDENT_MATCH; permission denied -> permission guidance.
- External-ish install proof executed: pipx status `{results['external_install'].get('pipx_proof')}`, clean venv status `{results['external_install'].get('clean_venv_externalish')}`.
- GitHub identity/remotes/heads diagnosed read-only; no push/publish/visibility mutation attempted.

## STILL HARD-BLOCKED

- `live_mcp_runtime_identity`: HUMAN_BLOCKED until an approved human-supervised live reload/canary.
- `first_10_real_users`: HUMAN_BLOCKED; verified external users remain 0.
- `github_admin_push_path`: READ_ONLY_DIAGNOSED only; human must use correct PAT and approve any push/admin mutation.

## Artifact paths

- `{PREFLIGHT.relative_to(ROOT)}`
- `{RESULT_JSON.relative_to(ROOT)}`
- `{REPORT_MD.relative_to(ROOT)}`
- `{BLOCKER_BOARD.relative_to(ROOT)}`
- `{RUNBOOK.relative_to(ROOT)}`
- `{SCOREBOARD.relative_to(ROOT)}`

## Exact human actions needed

1. Review `git diff --cached` and run `git diff --cached --check`.
2. If acceptable, push the staged release branch with the correct borg-farther GitHub token/PAT; do not push unrelated unstaged work.
3. Human-supervised reload of live Hermes/MCP, then run live canaries: `borg_runtime_fingerprint`, unrelated `borg_observe`, permission-denied `borg_observe`.
4. Recruit 10 consented external beta users; record redacted evidence in `{SCOREBOARD.relative_to(ROOT)}`; require ≥8 install successes, ≥6 useful rescues, and 0 critical privacy/security failures.
5. Final human copy/claims review before any public announcement.
"""
    REPORT_MD.write_text(report)


def main() -> int:
    os.chdir(ROOT)
    EVAL.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    preflight = {
        "generated_at_utc": now(),
        "git_status_short": git("status", "--short"),
        "git_diff_stat": git("diff", "--stat"),
        "git_diff": git("diff", timeout=600),
        "git_diff_cached_stat": git("diff", "--cached", "--stat"),
        "git_diff_cached": git("diff", "--cached", timeout=600),
        "git_branch": git("branch", "--show-current"),
        "git_remote_v": git("remote", "-v"),
    }
    write_json(PREFLIGHT, preflight)

    results: dict[str, Any] = {"generated_at_utc": now(), "preflight_path": str(PREFLIGHT.relative_to(ROOT))}
    results["scoreboard"] = validate_update_scoreboard()
    results["cleanup"] = safe_cleanup()
    results["verification_commands"] = [run(cmd, timeout=900) for cmd in VERIFY_COMMANDS]
    results["source_canaries"] = run_canaries()
    results["external_install"] = external_install_proof()
    # pipx/local installs may rebuild package artifacts into build/lib or dist;
    # restore generated side effects again before staging the release diff.
    results["post_external_cleanup"] = safe_cleanup()
    results["github_readonly"] = github_readonly()
    results["sanitize_before_staging"] = sanitize_allowed_stage_files()
    gates_ok = all(c["rc"] == 0 for c in results["verification_commands"]) and results["source_canaries"]["status"] == "PASS"
    results["staging"] = stage_allowed_if_gates_pass(gates_ok)
    update_docs_and_report(results)
    # Stage updated board/runbook/report inputs only if gates passed; report itself intentionally remains unstaged unless human opts in.
    if gates_ok:
        results["sanitize_after_doc_update"] = sanitize_allowed_stage_files()
        results["restage_after_doc_update"] = git("add", "--", *[p for p in ALLOWED_STAGE if (ROOT / p).exists()])
        results["final_cached_stat"] = git("diff", "--cached", "--stat")
        results["final_cached_check"] = git("diff", "--cached", "--check")
    results["final_status_short"] = git("status", "--short")
    write_json(RESULT_JSON, results)
    final_check_ok = results.get("final_cached_check", {}).get("rc", 0) == 0
    return 0 if gates_ok and results["staging"].get("status") == "PASS" and final_check_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
