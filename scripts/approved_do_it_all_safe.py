#!/usr/bin/env python3
"""Approved do-it-all safe runner for Borg public-waitlist readiness.

Conservative constraints honored:
- no SSH;
- no live service restart/kill/signal/reload;
- no GitHub visibility mutation;
- no fabricated first-10 users;
- commit/push only if gates pass and staged diff is allowlisted.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
DOCS = ROOT / "docs"
JSON_PATH = EVAL / "20260514_approved_do_it_all.json"
MD_PATH = DOCS / "20260514_APPROVED_DO_IT_ALL_FINAL_STATUS.md"
INVITE_PATH = DOCS / "20260514_FIRST_10_USER_INVITE_PACKET.md"
SCOREBOARD = EVAL / "first_10_user_scoreboard.json"
BRANCH = "public-waitlist-readiness-20260514"
COMMIT_MSG = "chore(borg): public waitlist readiness proof"

PRIOR_ALLOWLIST = {
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
}
ALLOWLIST = PRIOR_ALLOWLIST | {
    "docs/20260514_APPROVED_DO_IT_ALL_FINAL_STATUS.md",
    "eval/20260514_approved_do_it_all.json",
}

GATES = [
    [sys.executable, "-m", "pytest", "-q", "tests/readiness/test_confidence_gate.py", "tests/mcp/test_borg_observe_confidence_gate.py", "tests/mcp/test_runtime_fingerprint.py"],
    [sys.executable, "scripts/build_borg_proof_dashboard.py"],
    [sys.executable, "scripts/borg_proof_dashboard_lint.py"],
    [sys.executable, "-m", "pytest", "-q", "eval/tests/test_borg_proof_dashboard.py"],
    [sys.executable, "eval/run_first_user_release_gate.py"],
    [sys.executable, "scripts/security_gate_check.py"],
    [sys.executable, "-m", "pytest", "-q", "tests/security/test_privacy_structured.py", "tests/security/test_prompt_injection.py", "tests/security/test_atom_policy.py", "tests/security/test_atom_retrieval_firewall.py", "tests/security/test_privacy.py"],
    [sys.executable, "scripts/fix_public_launch_blockers_safe.py"],
]

COMMANDS: list[dict[str, Any]] = []

def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def run(cmd: list[str], *, timeout: int = 900, env: dict[str, str] | None = None, name: str | None = None) -> dict[str, Any]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    rec: dict[str, Any] = {"name": name or " ".join(cmd), "cmd": cmd, "started_at_utc": now()}
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=full_env)
        rec.update({"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
    except subprocess.TimeoutExpired as e:
        rec.update({"rc": 124, "stdout": e.stdout or "", "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s"})
    except FileNotFoundError as e:
        rec.update({"rc": 127, "stdout": "", "stderr": str(e)})
    rec["ended_at_utc"] = now()
    COMMANDS.append(rec)
    return rec

def git(*args: str, timeout: int = 900) -> dict[str, Any]:
    return run(["git", *args], timeout=timeout, name="git " + " ".join(args))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def scoreboard_status() -> dict[str, Any]:
    if not SCOREBOARD.exists():
        data = {"schema_version": 1, "rows": []}
    else:
        data = json.loads(SCOREBOARD.read_text())
    data.setdefault("schema_version", 1)
    data.setdefault("generated_at_utc", now())
    data["status"] = "pre_first_user_no_real_rows"
    data.setdefault("purpose", "Hard evidence scoreboard for Borg first-10 external beta users. Empty rows are placeholders only and must never be counted as adoption.")
    data["truth_policy"] = {
        "simulated_users_count_as_real": False,
        "internal_sessions_count_as_real": False,
        "maintainer_runs_count_as_real": False,
        "verified_external_users": 0,
        "public_self_serve_launch_allowed_before_thresholds": False,
    }
    data.setdefault("columns", [
        "user_id_pseudonym", "external_user_evidence_uri", "consent_confirmed", "install_method",
        "install_success", "time_to_first_rescue_minutes", "rescue_input_redacted",
        "rescue_returned_action_stop_verify", "rescue_useful", "mcp_setup_attempted", "mcp_setup_success",
        "no_confident_match_when_unknown", "blocker_category", "blocker_notes_redacted",
        "privacy_security_incident", "repeat_use_within_7_days", "outcome_recorded",
    ])
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    # Do not count any rows unless explicit external evidence + consent exists. Existing rows are preserved but current run has none.
    verified = [r for r in rows if isinstance(r, dict) and r.get("external_user_evidence_uri") and r.get("consent_confirmed") is True]
    data["rows"] = rows
    data["current_counts"] = {
        "real_users": len(verified),
        "install_successes": sum(1 for r in verified if r.get("install_success") is True),
        "useful_rescue_moments": sum(1 for r in verified if r.get("rescue_useful") is True),
        "critical_privacy_security_failures": sum(1 for r in verified if r.get("privacy_security_incident") in (True, "critical")),
        "repeat_use_within_7_days": sum(1 for r in verified if r.get("repeat_use_within_7_days") is True),
    }
    data["current_verdict"] = {"first_10_complete": False, "public_self_serve_launch_gate": "BLOCKED", "reason": "No verified external user rows exist yet."}
    SCOREBOARD.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")
    return {"exists": True, "verified_external_users": len(verified), "current_counts": data["current_counts"]}

def write_invite_packet() -> None:
    INVITE_PATH.write_text(f"""# Borg first-10 user invite packet

Generated: {now()}

## Exact invite message

Hi — we are running a small consented Borg beta for the first 10 external users. Borg is an error/debugging assistant that returns ACTION / STOP / VERIFY guidance from local/public project traces. Would you be willing to try one install and one real debugging query, then send redacted feedback? Please do not paste secrets, tokens, proprietary code, private customer data, or confidential logs.

## Install commands

Preferred isolated install:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install git+https://github.com/borg-farther/Borg-Directory.git
borg --version
borg rescue "paste a REDACTED real error here"
```

Fallback if pipx is unavailable:

```bash
python -m venv /tmp/borg-beta-venv
/tmp/borg-beta-venv/bin/python -m pip install git+https://github.com/borg-farther/Borg-Directory.git
/tmp/borg-beta-venv/bin/borg --version
/tmp/borg-beta-venv/bin/borg rescue "paste a REDACTED real error here"
```

## Consent and privacy warning

By participating, the user consents to have redacted outcome metadata recorded for launch readiness. Do not collect raw secrets, credentials, private keys, customer data, or unreduced proprietary logs. Store only pseudonymous user id, install outcome, redacted error category, whether advice was useful, and whether any privacy/security incident occurred.

## Feedback fields to collect

- user_id_pseudonym
- external_user_evidence_uri
- consent_confirmed
- install_method
- install_success
- time_to_first_rescue_minutes
- rescue_input_redacted
- rescue_returned_action_stop_verify
- rescue_useful
- mcp_setup_attempted
- mcp_setup_success
- no_confident_match_when_unknown
- blocker_category
- blocker_notes_redacted
- privacy_security_incident
- repeat_use_within_7_days
- outcome_recorded

## Scoreboard update instructions

Update `eval/first_10_user_scoreboard.json` only after a real external user provides consent and hard evidence. Keep `truth_policy.verified_external_users=0` until evidence exists. Never add fake rows. Public self-serve remains blocked until 10 real external users are verified with at least 8 install successes, at least 6 useful rescue moments, and 0 critical privacy/security failures.
""")

def source_canaries() -> dict[str, Any]:
    code = r'''
import json
from borg.integrations import mcp_server
unrelated = mcp_server.borg_observe(task="public launch blocker spreadsheet formatting zebra stripes", context="docs")
permission = mcp_server.borg_observe(task="bash: ./deploy.sh: Permission denied", context="bash chmod execute permission denied")
print(json.dumps({
  "unrelated_contains_no_confident_match": "NO_CONFIDENT_MATCH" in unrelated or "NO CONFIDENT MATCH" in unrelated,
  "permission_mentions_permission": "permission" in permission.lower() or "chmod" in permission.lower(),
  "unrelated_excerpt": unrelated[:1500],
  "permission_excerpt": permission[:1500],
}, sort_keys=True))
'''
    r = run([sys.executable, "-c", code], name="source_canaries", timeout=240)
    parsed = None
    if r["rc"] == 0:
        try:
            parsed = json.loads(r["stdout"])
        except Exception as e:
            parsed = {"parse_error": str(e)}
    ok = bool(parsed and parsed.get("unrelated_contains_no_confident_match") and parsed.get("permission_mentions_permission"))
    return {"status": "PASS" if ok else "FAIL", "parsed": parsed, "command_index": len(COMMANDS) - 1}

def pipx_proof() -> dict[str, Any]:
    env = {"PIPX_HOME": "/tmp/borg-pipx-home", "PIPX_BIN_DIR": "/tmp/borg-pipx-bin"}
    borg_bin = Path("/tmp/borg-pipx-bin/borg")
    install = None
    if borg_bin.exists():
        source = "existing /tmp/borg-pipx-bin/borg"
    elif shutil.which("pipx"):
        source = "pipx install --force local repo"
        install = run(["pipx", "install", "--force", str(ROOT)], env=env, timeout=900, name="pipx install local repo")
    else:
        source = "blocked: pipx unavailable and /tmp/borg-pipx-bin/borg absent"
    version = run([str(borg_bin), "--version"], env=env, timeout=180, name="pipx borg --version") if borg_bin.exists() else {"rc": 127, "stdout": "", "stderr": "borg bin absent"}
    if borg_bin.exists():
        COMMANDS.append({"name": "pipx borg rescue", "cmd": [str(borg_bin), "rescue", "bash: ./x: Permission denied; context=bash chmod execute bit"], "started_at_utc": now(), **subprocess_run_capture([str(borg_bin), "rescue", "bash: ./x: Permission denied; context=bash chmod execute bit"], env=env), "ended_at_utc": now()})
        rescue = COMMANDS[-1]
    else:
        rescue = {"rc": 127, "stdout": "", "stderr": "borg bin absent"}
    ok = (install is None or install.get("rc") == 0) and version.get("rc") == 0 and rescue.get("rc") == 0
    return {"status": "PASS" if ok else "FAIL", "source": source, "install": install, "version": version, "rescue": rescue}

def subprocess_run_capture(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 180) -> dict[str, Any]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=full_env)
        return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as e:
        return {"rc": 124, "stdout": e.stdout or "", "stderr": (e.stderr or "") + f"\nTIMEOUT after {timeout}s"}
    except FileNotFoundError as e:
        return {"rc": 127, "stdout": "", "stderr": str(e)}

def staged_names() -> list[str]:
    r = git("diff", "--cached", "--name-only")
    return [x for x in r.get("stdout", "").splitlines() if x.strip()]

def write_md(results: dict[str, Any]) -> None:
    gs = results.get("gate_statuses", {})
    commit = results.get("commit", {})
    push = results.get("push", {})
    MD_PATH.write_text(f"""# Approved do-it-all final status

Generated: {now()}

## Verdict

- **DONE/PARTIAL/BLOCKED:** {results.get('overall_status')}
- **PUBLIC_WAITLIST_NARROW_BETA:** {gs.get('PUBLIC_WAITLIST_NARROW_BETA')}
- **PUBLIC_SELF_SERVE_LAUNCH:** {gs.get('PUBLIC_SELF_SERVE_LAUNCH')}
- **live_mcp_runtime_identity:** HUMAN_BLOCKED (no live reload/canary allowed under safety rules)
- **first_10_real_users:** HUMAN_BLOCKED (verified_external_users={results.get('scoreboard', {}).get('verified_external_users')})

## Branch / commit / push

- branch: `{results.get('current_branch_after')}`
- commit attempted: {commit.get('attempted')}
- commit rc: {commit.get('rc')}
- pushed: {push.get('pushed')}
- push rc: {push.get('rc')}
- HEAD: `{results.get('head_after')}`
- ls-remote branch: `{results.get('ls_remote_branch', {}).get('stdout', '').strip()}`

## Gates

- required gates pass: {results.get('gates_ok')}
- source canaries: {results.get('source_canaries', {}).get('status')}
- pipx proof: {results.get('pipx_proof', {}).get('status')}
- security gate: {results.get('security_gate_status')}
- staged diff allowlisted: {results.get('staged_diff', {}).get('allowlisted')}
- `git diff --cached --check`: rc={results.get('staged_diff', {}).get('check_rc')}

## Artifacts

- `eval/20260514_approved_do_it_all.json`
- `docs/20260514_APPROVED_DO_IT_ALL_FINAL_STATUS.md`
- `docs/20260514_FIRST_10_USER_INVITE_PACKET.md`
- `eval/first_10_user_scoreboard.json`

## Remaining blockers

1. Human-supervised live Hermes/MCP reload/canary remains required; autonomous reload was not performed.
2. First-10 real users remain pending; no fake users were added.
3. Public self-serve launch remains NO until live MCP canary after supervised reload and first-10 real users pass.
""")

def main() -> int:
    os.chdir(ROOT)
    EVAL.mkdir(exist_ok=True)
    DOCS.mkdir(exist_ok=True)
    results: dict[str, Any] = {"generated_at_utc": now(), "commands": COMMANDS}
    results["pre_status"] = git("status", "--short")
    results["pre_branch"] = git("branch", "--show-current")
    results["scoreboard"] = scoreboard_status()
    write_invite_packet()

    gate_results = []
    for cmd in GATES:
        gate_results.append(run(cmd, timeout=1200, name="gate: " + " ".join(cmd)))
    results["gate_results"] = gate_results
    results["gates_ok"] = all(g["rc"] == 0 for g in gate_results)
    results["security_gate_status"] = "PASS" if gate_results[5]["rc"] == 0 else "FAIL"
    results["source_canaries"] = source_canaries()
    results["pipx_proof"] = pipx_proof()

    # fix_public_launch_blockers_safe may re-stage the prior allowlisted release files. Add only the two approved final status artifacts.
    # Do not stage invite packet or this script because the user provided a tighter staged-diff allowlist.
    write_md({**results, "overall_status": "IN_PROGRESS", "gate_statuses": {}})
    write_json(JSON_PATH, {**results, "commands": COMMANDS})
    git("add", "--", str(JSON_PATH.relative_to(ROOT)), str(MD_PATH.relative_to(ROOT)))

    check = git("diff", "--cached", "--check")
    names = staged_names()
    unexpected = [n for n in names if n not in ALLOWLIST]
    results["staged_diff"] = {"check_rc": check["rc"], "names": names, "unexpected": unexpected, "allowlisted": not unexpected}

    canaries_ok = results["source_canaries"]["status"] == "PASS"
    pipx_ok = results["pipx_proof"]["status"] == "PASS"
    security_ok = results["security_gate_status"] == "PASS"
    safe_to_commit = bool(results["gates_ok"] and canaries_ok and pipx_ok and security_ok and check["rc"] == 0 and not unexpected)
    results["safe_to_commit"] = safe_to_commit

    if safe_to_commit:
        # Create/switch branch preserving staged changes.
        existing = git("show-ref", "--verify", "--quiet", f"refs/heads/{BRANCH}")
        if existing["rc"] == 0:
            switch = git("switch", BRANCH)
        else:
            switch = git("switch", "-c", BRANCH)
        results["branch_switch"] = switch
        # Re-check after switch.
        check2 = git("diff", "--cached", "--check")
        names2 = staged_names()
        unexpected2 = [n for n in names2 if n not in ALLOWLIST]
        results["staged_diff_after_switch"] = {"check_rc": check2["rc"], "names": names2, "unexpected": unexpected2, "allowlisted": not unexpected2}
        if switch["rc"] == 0 and check2["rc"] == 0 and not unexpected2:
            c = git("commit", "-m", COMMIT_MSG)
            results["commit"] = {"attempted": True, "rc": c["rc"], "stdout": c["stdout"], "stderr": c["stderr"]}
            if c["rc"] == 0:
                p = git("push", "-u", "origin", BRANCH, timeout=1200)
                results["push"] = {"pushed": p["rc"] == 0, "rc": p["rc"], "stdout": p["stdout"], "stderr": p["stderr"]}
            else:
                results["push"] = {"pushed": False, "rc": 98, "stdout": "", "stderr": "commit failed; skipped push"}
        else:
            results["commit"] = {"attempted": False, "rc": 97, "stdout": "", "stderr": "branch switch or post-switch allowlist check failed"}
            results["push"] = {"pushed": False, "rc": 97, "stdout": "", "stderr": "commit skipped"}
    else:
        results["branch_switch"] = {"rc": 96, "stdout": "", "stderr": "safe_to_commit false; skipped"}
        results["commit"] = {"attempted": False, "rc": 96, "stdout": "", "stderr": "safe_to_commit false; skipped"}
        results["push"] = {"pushed": False, "rc": 96, "stdout": "", "stderr": "safe_to_commit false; skipped"}

    results["head_after"] = git("rev-parse", "HEAD").get("stdout", "").strip()
    results["status_after"] = git("status", "--short")
    results["current_branch_after"] = git("branch", "--show-current").get("stdout", "").strip()
    results["remote_v"] = git("remote", "-v")
    results["ls_remote_branch"] = git("ls-remote", "--heads", "origin", BRANCH, timeout=240)
    results["gh_auth_status"] = run(["gh", "auth", "status"], timeout=180, name="gh auth status") if shutil.which("gh") else {"rc": 127, "stdout": "", "stderr": "gh absent"}
    if shutil.which("gh"):
        results["gh_user"] = run(["gh", "api", "user", "--jq", ".login"], timeout=180, name="gh api user --jq .login")
        results["gh_repo_view"] = run(["gh", "repo", "view", "borg-farther/Borg-Directory", "--json", "nameWithOwner,visibility,url,viewerPermission,defaultBranchRef"], timeout=180, name="gh repo view")
    else:
        results["gh_user"] = {"rc": 127, "stdout": "", "stderr": "gh absent"}
        results["gh_repo_view"] = {"rc": 127, "stdout": "", "stderr": "gh absent"}

    push_ok = bool(results.get("push", {}).get("pushed"))
    claims_ok = results["gates_ok"] and security_ok
    results["gate_statuses"] = {
        "PUBLIC_WAITLIST_NARROW_BETA": "YES" if (results["gates_ok"] and push_ok and pipx_ok and security_ok and claims_ok) else "NO",
        "PUBLIC_SELF_SERVE_LAUNCH": "NO",
        "live_mcp_runtime_identity": "HUMAN_BLOCKED",
        "first_10_real_users": "HUMAN_BLOCKED",
        "verified_external_users": results["scoreboard"].get("verified_external_users", 0),
    }
    if push_ok and results["gate_statuses"]["PUBLIC_WAITLIST_NARROW_BETA"] == "YES":
        results["overall_status"] = "DONE_WITH_CAVEATS"
    elif results["gates_ok"] and safe_to_commit and not push_ok:
        results["overall_status"] = "PARTIAL_PUSH_BLOCKED"
    else:
        results["overall_status"] = "BLOCKED"

    write_md(results)
    write_json(JSON_PATH, {**results, "commands": COMMANDS})
    # Final report files are intentionally not re-staged after post-push updates, to avoid amending pushed commit.
    return 0 if push_ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
