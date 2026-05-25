#!/usr/bin/env python3
"""Build an honest Borg proof dashboard from local repo artifacts only."""
from __future__ import annotations

import html
import json
import re
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVAL = ROOT / "eval"
PUBLIC = DOCS / "public" / "proof-dashboard"
PUBLIC_ROOT = DOCS / "public"
JSON_OUT = EVAL / "borg_proof_dashboard.json"
MD_OUT = DOCS / "BORG_PROOF_DASHBOARD.md"
HTML_OUT = DOCS / "BORG_PROOF_DASHBOARD.html"
PUBLIC_OUT = PUBLIC / "index.html"
PUBLIC_STATUS_OUT = PUBLIC_ROOT / "status.json"
PUBLIC_VALUE_OUT = PUBLIC_ROOT / "value.json"
PUBLIC_IMPACT_OUT = PUBLIC_ROOT / "impact" / "impact.json"
CANONICAL_REPO_URL = "https://github.com/borg-farther/Borg-Directory"

SOURCE_PATHS = [
    "pyproject.toml",
    "borg/__init__.py",
    "eval/first_user_release_gate_snapshot.json",
    "eval/uat_scoreboard_snapshot.json",
    "eval/gate_run_snapshot.json",
    "eval/real_user_rollout_gate_snapshot.json",
    "eval/public_self_serve_launch_gate_snapshot.json",
    "eval/pypi_fresh_install_snapshot.json",
    "eval/load_10_snapshot.json",
    "eval/load_100_snapshot.json",
    "eval/load_1000_snapshot.json",
    "PROJECT_STATUS.md",
    "GO_NO_GO_DECISION.md",
    "UAT_RESULTS.md",
    "ROADMAP.md",
]

HYPE_RE = re.compile(r"\b(proven external adoption|hundreds of users|production ready)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(rel: str) -> dict | None:
    path = ROOT / rel
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_parse_error": str(exc)}


def nested(data: dict | None, keys: list[str], default=None):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def status_bool(value) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "UNKNOWN"


def pyproject_version() -> str | None:
    path = ROOT / "pyproject.toml"
    if not path.exists():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return nested(data, ["project", "version"])


def init_version() -> str | None:
    path = ROOT / "borg" / "__init__.py"
    if not path.exists():
        return None
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def current_commit() -> str | None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode != 0
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
        untracked = bool(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).strip())
        if dirty or staged or untracked:
            return f"{commit}+dirty"
        return commit
    except Exception:
        return None


def source_record(rel: str, claim: str, freshness: str | None = None) -> dict:
    path = ROOT / rel
    exists = path.exists()
    return {
        "path": rel,
        "exists": exists,
        "sha256": sha256(path) if exists else None,
        "freshness_timestamp": freshness or (mtime_iso(path) if exists else None),
        "claim_derived": claim if exists else f"MISSING: {claim}",
    }


def pack_count() -> int | None:
    packs = ROOT / "borg" / "seeds_data" / "packs"
    if not packs.exists():
        return None
    return len(sorted(packs.glob("*.yaml")))


def build_model() -> dict:
    first = load_json("eval/first_user_release_gate_snapshot.json")
    uat = load_json("eval/uat_scoreboard_snapshot.json")
    gate = load_json("eval/gate_run_snapshot.json")
    real_user = load_json("eval/real_user_rollout_gate_snapshot.json")
    public_gate = load_json("eval/public_self_serve_launch_gate_snapshot.json")
    pypi_fresh = load_json("eval/pypi_fresh_install_snapshot.json")
    loads = {str(n): load_json(f"eval/load_{n}_snapshot.json") for n in (10, 100, 1000)}
    pv, rv = pyproject_version(), init_version()
    commit = current_commit()
    pcount = pack_count()

    verified_external_users = 0
    external_user_evidence = "No artifact found that identifies real verified external users; simulated/logical load users are excluded."

    version_consistent = bool(pv and rv and pv == rv)
    first_gate_pass = nested(first, ["all_pass"])
    if first_gate_pass is None and isinstance(first, dict) and isinstance(first.get("results"), list):
        first_gate_pass = all(item.get("passed") is True for item in first["results"] if isinstance(item, dict))
    uat_pass = nested(uat, ["synthetic_load_all_pass"], nested(uat, ["all_pass"]))
    gate_pass = nested(gate, ["synthetic_load_all_pass"], nested(gate, ["all_pass"]))
    real_user_100_pass = nested(real_user, ["ready_for_100_real_users"], nested(uat, ["real_user_rollout", "ready_for_100_real_users"]))
    public_self_serve_pass = nested(public_gate, ["ready_for_public_self_serve_launch"])
    pypi_fresh_pass = nested(pypi_fresh, ["success"])
    pypi_fresh_version = nested(pypi_fresh, ["version"])
    max_recommended_real_users = nested(public_gate, ["max_recommended_real_users_now"], nested(real_user, ["max_recommended_real_users_now"], nested(uat, ["real_user_rollout", "max_recommended_real_users_now"], 0)))
    controlled_beta_ready = nested(public_gate, ["ready_for_controlled_first_10_beta"]) is True
    real_user_blockers = nested(real_user, ["blockers"], nested(uat, ["real_user_rollout", "blockers"], []))
    load_summary = {}
    for n, data in loads.items():
        load_summary[n] = {
            "exists": data is not None,
            "passed": nested(data, ["passed"], nested(uat, ["loads", n, "passed"])),
            "users_label": nested(data, ["users"], int(n)),
            "concurrency_model": nested(data, ["concurrency_model"], "UNKNOWN" if data is None else None),
            "total_requests": nested(data, ["total_requests"], nested(uat, ["loads", n, "total_requests"])),
            "success_rate": nested(data, ["success_rate"], nested(uat, ["loads", n, "success_rate"])),
            "p95_ms": nested(data, ["latency_ms", "p95"], nested(uat, ["loads", n, "p95_ms"])),
            "p99_ms": nested(data, ["latency_ms", "p99"], nested(uat, ["loads", n, "p99_ms"])),
            "timestamp": nested(data, ["timestamp"], nested(uat, ["loads", n, "timestamp"])),
        }

    local_release_candidate_ready = bool(version_consistent and (first_gate_pass is True) and (uat_pass is True) and (gate_pass is True))
    controlled_beta_why = (
        "Controlled first-10 beta infrastructure is green; keep broad launch blocked until row-derived external-user evidence passes."
        if controlled_beta_ready
        else "Controlled first-10 beta is blocked until the public package path is green: PyPI latest metadata, fresh-install canary, stdio MCP canary, and docs guard must all pass."
    )
    verdicts = {
        "controlled_first_10_beta": {
            "verdict": "CONDITIONAL" if controlled_beta_ready else "NO-GO",
            "why": controlled_beta_why,
        },
        "local_release_candidate": {
            "verdict": "CONDITIONAL" if local_release_candidate_ready else "NO-GO",
            "why": "Local source/wheel gates pass, but this does not authorize public beta without PyPI/latest/fresh-install proof." if local_release_candidate_ready else "Required local first-user/readiness gates are not all passing or are missing.",
        },
        "unattended_git_onboarding": {
            "verdict": "NO-GO",
            "why": "No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes.",
        },
        "broad_public_launch": {
            "verdict": "NO-GO" if public_self_serve_pass is not True else "GO",
            "why": (
                "Public self-serve gate is blocked only by row-derived first-10 external-user evidence; PyPI/latest/fresh-install/MCP/docs gates are green."
                if pypi_fresh_pass is True and public_self_serve_pass is not True
                else "Public self-serve gate is blocked until PyPI latest/fresh-install/MCP/docs gates pass and first-10 external evidence exists."
            ) if public_self_serve_pass is not True else "Public self-serve gate has passed with row-derived external evidence.",
        },
    }

    metrics = {
        "verified_external_users": {"value": verified_external_users, "honesty_label": "HARD_EVIDENCE_ABSENT_DEFAULT_ZERO", "provenance": external_user_evidence},
        "active_contributors_consumers": {"value": "UNKNOWN", "honesty_label": "MISSING_BORG_ANALYTICS_ARTIFACT", "provenance": "No Borg analytics export artifact was found under eval/ or docs/."},
        "packs": {"value": pcount if pcount is not None else "MISSING", "honesty_label": "REPO_FILE_COUNT" if pcount is not None else "MISSING", "provenance": "borg/seeds_data/packs/*.yaml"},
        "first_user_release_gate": {"value": status_bool(first_gate_pass), "honesty_label": "LOCAL_ARTIFACT", "provenance": "eval/first_user_release_gate_snapshot.json" if first else "MISSING"},
        "uat_scoreboard_synthetic_load": {"value": status_bool(uat_pass), "honesty_label": "LOCAL_ARTIFACT_LOGICAL_USERS", "provenance": "eval/uat_scoreboard_snapshot.json" if uat else "MISSING"},
        "gate_run_synthetic_load": {"value": status_bool(gate_pass), "honesty_label": "LOCAL_ARTIFACT_LOGICAL_USERS", "provenance": "eval/gate_run_snapshot.json" if gate else "MISSING"},
        "real_user_100_rollout_gate": {"value": status_bool(real_user_100_pass), "honesty_label": "REAL_EXTERNAL_USERS", "provenance": "eval/real_user_rollout_gate_snapshot.json" if real_user else "MISSING"},
        "max_recommended_real_users_now": {"value": max_recommended_real_users, "honesty_label": "REAL_EXTERNAL_USERS", "provenance": "eval/real_user_rollout_gate_snapshot.json" if real_user else "MISSING"},
        "public_self_serve_launch_gate": {"value": status_bool(public_self_serve_pass), "honesty_label": "PUBLIC_LAUNCH_GATE", "provenance": "eval/public_self_serve_launch_gate_snapshot.json" if public_gate else "MISSING"},
        "pypi_fresh_install_canary": {"value": status_bool(pypi_fresh_pass), "honesty_label": "PYPI_FRESH_INSTALL", "provenance": "eval/pypi_fresh_install_snapshot.json" if pypi_fresh else "MISSING"},
        "source_version_consistency": {"value": f"pyproject={pv or 'MISSING'} runtime={rv or 'MISSING'}", "honesty_label": "REPO_SOURCE", "provenance": "pyproject.toml; borg/__init__.py"},
        "host_runtime_split_brain": {"value": "NOT_REPRODUCED_IN_THIS_BUILD", "honesty_label": "EVIDENCE_GAP", "provenance": "Prior docs mention runtime/host issues, but this dashboard build did not run environment probes."},
        "load_gates": {"value": load_summary, "honesty_label": "LOGICAL_USERS_NOT_REAL_USERS", "provenance": "eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json"},
    }

    blockers = {
        "user_affecting": [
            "No real external first-user install/rescue outcome has been recorded yet.",
            "PyPI fresh-install canary is not green yet." if pypi_fresh_pass is not True else "PyPI fresh-install canary is green.",
            "Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention.",
        ],
        "investor_affecting": [
            "Verified external users: 0 based on available hard evidence.",
            "Local/logical load gates prove engineering readiness, not market adoption or retention.",
        ],
        "security_privacy": [
            "Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.",
            "Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script.",
        ],
        "release_hygiene": [
            "Do not change repo visibility from this proof build.",
            "Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness.",
        ],
        "evidence_gaps": [
            "No Borg analytics export proving active contributors or consumers was found.",
            "No first-10-user scoreboard with real outcomes exists yet.",
            f"100-real-user gate remains blocked: {real_user_blockers or ['no blocker detail found']}",
            "Host/runtime split-brain was not freshly reproduced by this dashboard build.",
        ],
    }

    if pypi_fresh_pass is True:
        first_tester_action = f"Use `pipx install agent-borg=={pypi_fresh_version or pv or 'CURRENT_VERSION'}` with controlled first-10 beta testers and label it as beta evidence capture, not public launch."
    else:
        first_tester_action = f"After `agent-borg=={pv or 'CURRENT_VERSION'}` is published and the PyPI fresh-install + stdio MCP canary passes, use that exact PyPI version with controlled first-10 beta testers."
    next_actions = [
        first_tester_action,
        "Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers.",
        "Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields.",
        "If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO.",
        "Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN.",
        "Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction.",
    ]

    evidence = []
    if first:
        evidence.append(source_record("eval/first_user_release_gate_snapshot.json", f"first-user release gate all_pass={first_gate_pass}", nested(first, ["generated_at_utc"], nested(first, ["timestamp"]))))
    else:
        evidence.append(source_record("eval/first_user_release_gate_snapshot.json", "first-user release gate status unknown"))
    if uat:
        evidence.append(source_record("eval/uat_scoreboard_snapshot.json", f"UAT synthetic_load_all_pass={uat_pass}; real_user_100_all_pass={real_user_100_pass}; ready_for_10={nested(uat, ['ready_for_10'])}; ready_for_1000={nested(uat, ['ready_for_1000'])}", nested(uat, ["timestamp"])))
    else:
        evidence.append(source_record("eval/uat_scoreboard_snapshot.json", "UAT scoreboard missing"))
    if gate:
        evidence.append(source_record("eval/gate_run_snapshot.json", f"gate run synthetic_load_all_pass={gate_pass}; overall_100_real_user_pass={real_user_100_pass}; ready_for_10={nested(gate, ['ready_for_10'])}; ready_for_1000={nested(gate, ['ready_for_1000'])}", nested(gate, ["timestamp"])))
    else:
        evidence.append(source_record("eval/gate_run_snapshot.json", "gate run missing"))
    if real_user:
        evidence.append(source_record("eval/real_user_rollout_gate_snapshot.json", f"100-real-user gate={real_user_100_pass}; max_recommended_real_users={max_recommended_real_users}; blockers={real_user_blockers}", nested(real_user, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/real_user_rollout_gate_snapshot.json", "real-user rollout gate missing"))
    if public_gate:
        evidence.append(source_record("eval/public_self_serve_launch_gate_snapshot.json", f"public self-serve gate={public_self_serve_pass}; max_recommended_real_users={nested(public_gate, ['max_recommended_real_users_now'])}; blockers={nested(public_gate, ['blockers'], [])}", nested(public_gate, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/public_self_serve_launch_gate_snapshot.json", "public self-serve launch gate missing"))
    if pypi_fresh:
        evidence.append(source_record("eval/pypi_fresh_install_snapshot.json", f"PyPI fresh-install canary success={pypi_fresh_pass}; version={nested(pypi_fresh, ['version'])}", nested(pypi_fresh, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/pypi_fresh_install_snapshot.json", "PyPI fresh-install canary missing"))
    for n, data in loads.items():
        evidence.append(source_record(f"eval/load_{n}_snapshot.json", f"logical load {n}: passed={load_summary[str(n)]['passed']}; total_requests={load_summary[str(n)]['total_requests']}; success_rate={load_summary[str(n)]['success_rate']}; p95_ms={load_summary[str(n)]['p95_ms']}; model={load_summary[str(n)]['concurrency_model']}", load_summary[str(n)]["timestamp"]))
    evidence.append(source_record("pyproject.toml", f"package version={pv}; scripts declared in project metadata"))
    evidence.append(source_record("borg/__init__.py", f"runtime __version__={rv}; top-level check() delegates to search"))
    for rel in ["PROJECT_STATUS.md", "GO_NO_GO_DECISION.md", "UAT_RESULTS.md", "ROADMAP.md"]:
        if (ROOT / rel).exists():
            evidence.append(source_record(rel, "prior local status/readiness narrative used as contextual evidence only, not external adoption proof"))

    first10_cols = ["user id/pseudonym", "install success", "time to first rescue", "rescue useful yes/no", "MCP setup success", "blocker", "outcome recorded"]
    first10_rows = [{c: "" for c in first10_cols} for _ in range(10)]

    return {
        "generated_at_utc": now_iso(),
        "repo": CANONICAL_REPO_URL,
        "source_revision": commit,
        "top_verdict": verdicts,
        "controlled_first_10_beta": {
            "answer": "GO" if controlled_beta_ready else "NO-GO",
            "conditions": [
                "Controlled testers only." if controlled_beta_ready else "Do not invite controlled beta users until PyPI latest, fresh-install, and stdio MCP canaries are green.",
                "Do not present as unattended public launch ready.",
                "Capture real first-user outcome evidence immediately." if controlled_beta_ready else "Keep first-10 evidence capture prepared, but blocked until package evidence is green.",
            ],
        },
        "metrics": metrics,
        "evidence": evidence,
        "blockers": blockers,
        "first_10_user_scoreboard_template": {"columns": first10_cols, "rows": first10_rows},
        "anti_hype": {
            "simulated_users_are_not_real_users": True,
            "internal_sessions_are_not_adoption": True,
            "verified_external_users_default_zero": True,
            "text": "Simulated/logical users are not real users. Internal sessions, tool calls, local tests, and maintainer runs are not adoption. Real verified external users are 0 unless a hard evidence artifact proves otherwise; no such artifact was found by this build.",
        },
        "next_action_queue_before_sharing_git_with_first_user": next_actions,
    }


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", "<br>") for x in row) + " |")
    return "\n".join(out)


def render_md(model: dict) -> str:
    verdict_rows = [[k.replace("_", " "), v["verdict"], v["why"]] for k, v in model["top_verdict"].items()]
    metric_rows = []
    for k, v in model["metrics"].items():
        val = v["value"]
        if isinstance(val, (dict, list)):
            val = "`" + json.dumps(val, sort_keys=True) + "`"
        metric_rows.append([k, val, v["honesty_label"], v["provenance"]])
    evidence_rows = [[e["path"], e["exists"], e["sha256"] or "MISSING", e["freshness_timestamp"] or "UNKNOWN", e["claim_derived"]] for e in model["evidence"]]
    blocker_rows = [[cat.replace("_", " "), "<br>".join(items)] for cat, items in model["blockers"].items()]
    score_cols = model["first_10_user_scoreboard_template"]["columns"]
    score_rows = [[i + 1] + [r[c] for c in score_cols] for i, r in enumerate(model["first_10_user_scoreboard_template"]["rows"])]
    next_rows = [[i + 1, item] for i, item in enumerate(model["next_action_queue_before_sharing_git_with_first_user"])]
    return f"""# Borg Proof Dashboard

Generated: `{model['generated_at_utc']}`
Repo: `{model['repo']}`
Source snapshot: `{model.get('source_revision') or 'UNKNOWN'}`

## Big top verdict

{md_table(['Scope', 'Verdict', 'Why'], verdict_rows)}

**Controlled first-10 beta only?** {model['controlled_first_10_beta']['answer']} — {'; '.join(model['controlled_first_10_beta']['conditions'])}

## Metrics with provenance and honesty labels

{md_table(['Metric', 'Value', 'Honesty label', 'Provenance'], metric_rows)}

## Evidence table

{md_table(['Source file path', 'Exists', 'SHA256', 'Freshness timestamp', 'Exact claim derived'], evidence_rows)}

## Blockers

{md_table(['Category', 'Blockers'], blocker_rows)}

## First-10-user scoreboard template

{md_table(['#'] + score_cols, score_rows)}

## Anti-hype section

{model['anti_hype']['text']}

## Next action queue before controlled first-10 beta testers

{md_table(['#', 'Action'], next_rows)}
"""


def render_html(model: dict, md: str) -> str:
    # Simple standalone HTML; the markdown is embedded as escaped preformatted source plus readable sections.
    css = """
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;line-height:1.45;color:#16202a}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #d7dee8;padding:.5rem;vertical-align:top}th{background:#edf2f7}.verdict{font-size:1.25rem;font-weight:700}.conditional{color:#9a5b00}.nogo{color:#9b1c1c}.go{color:#126b33}.note{background:#fff7db;border:1px solid #f0ce73;padding:1rem;border-radius:8px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em;word-break:break-all}pre{white-space:pre-wrap;background:#f7fafc;border:1px solid #d7dee8;padding:1rem;border-radius:8px}
"""
    def esc(x): return html.escape(str(x))
    verdict_html = "".join(f"<tr><td>{esc(k.replace('_',' '))}</td><td class='verdict {esc(v['verdict'].lower().replace('-',''))}'>{esc(v['verdict'])}</td><td>{esc(v['why'])}</td></tr>" for k,v in model["top_verdict"].items())
    metric_html = "".join(f"<tr><td>{esc(k)}</td><td class='mono'>{esc(json.dumps(v['value'], sort_keys=True) if isinstance(v['value'], (dict,list)) else v['value'])}</td><td>{esc(v['honesty_label'])}</td><td>{esc(v['provenance'])}</td></tr>" for k,v in model["metrics"].items())
    evidence_html = "".join(f"<tr><td class='mono'>{esc(e['path'])}</td><td>{esc(e['exists'])}</td><td class='mono'>{esc(e['sha256'] or 'MISSING')}</td><td>{esc(e['freshness_timestamp'] or 'UNKNOWN')}</td><td>{esc(e['claim_derived'])}</td></tr>" for e in model["evidence"])
    blockers_html = "".join(f"<tr><td>{esc(k.replace('_',' '))}</td><td><ul>{''.join('<li>'+esc(i)+'</li>' for i in v)}</ul></td></tr>" for k,v in model["blockers"].items())
    cols = model["first_10_user_scoreboard_template"]["columns"]
    score_head = "".join(f"<th>{esc(c)}</th>" for c in ["#"]+cols)
    score_body = "".join("<tr><td>%d</td>%s</tr>" % (i+1, "".join(f"<td>{esc(row[c])}</td>" for c in cols)) for i,row in enumerate(model["first_10_user_scoreboard_template"]["rows"]))
    next_html = "".join(f"<li>{esc(x)}</li>" for x in model["next_action_queue_before_sharing_git_with_first_user"])
    return f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Borg Proof Dashboard</title><style>{css}</style></head><body>
<h1>Borg Proof Dashboard</h1><p>Generated: <span class=\"mono\">{esc(model['generated_at_utc'])}</span><br>Repo: <span class=\"mono\">{esc(model['repo'])}</span><br>Source snapshot: <span class=\"mono\">{esc(model.get('source_revision') or 'UNKNOWN')}</span></p>
<h2>Big top verdict</h2><table><tr><th>Scope</th><th>Verdict</th><th>Why</th></tr>{verdict_html}</table>
<p class=\"note\"><strong>Controlled first-10 beta only?</strong> {esc(model['controlled_first_10_beta']['answer'])}. {' '.join(esc(c) for c in model['controlled_first_10_beta']['conditions'])}</p>
<h2>Metrics with provenance and honesty labels</h2><table><tr><th>Metric</th><th>Value</th><th>Honesty label</th><th>Provenance</th></tr>{metric_html}</table>
<h2>Evidence table</h2><table><tr><th>Source file path</th><th>Exists</th><th>SHA256</th><th>Freshness timestamp</th><th>Exact claim derived</th></tr>{evidence_html}</table>
<h2>Blockers</h2><table><tr><th>Category</th><th>Blockers</th></tr>{blockers_html}</table>
<h2>First-10-user scoreboard template</h2><table><tr>{score_head}</tr>{score_body}</table>
<h2>Anti-hype section</h2><p class=\"note\">{esc(model['anti_hype']['text'])}</p>
<h2>Next action queue before controlled first-10 beta testers</h2><ol>{next_html}</ol>
<h2>Markdown source</h2><pre>{esc(md)}</pre>
</body></html>"""


def build_public_payloads(model: dict) -> tuple[dict, dict, dict]:
    """Return compact JSON payloads consumed by docs/public/borg-live-dashboard.html."""
    controlled = model["top_verdict"]["controlled_first_10_beta"]
    broad = model["top_verdict"]["broad_public_launch"]
    local = model["top_verdict"]["local_release_candidate"]
    blockers = model.get("blockers", {})
    metrics = model.get("metrics", {})
    source_version = str(metrics.get("source_version_consistency", {}).get("value", "UNKNOWN"))
    generated = model["generated_at_utc"]
    controlled_is_green = controlled.get("verdict") == "CONDITIONAL"
    broad_is_green = broad.get("verdict") == "GO"
    if broad_is_green:
        public_state = "GO public self-serve"
        value_detail = "Public self-serve launch gate is green with row-derived external-user evidence."
    elif controlled_is_green:
        public_state = "NO-GO public self-serve; controlled first-10 beta GO"
        value_detail = "Controlled first-10 public-package beta infrastructure is green; public self-serve remains blocked until row-derived first-10 external-user evidence passes."
    else:
        public_state = "NO-GO public self-serve; source/local release-candidate only"
        value_detail = "Public-package controlled beta remains blocked until PyPI latest and fresh PyPI install + stdio MCP canaries pass for the current source version."

    status_payload = {
        "schema_version": 1,
        "source": "docs/public/status.json",
        "updated_at": generated,
        "repo": model["repo"],
        "source_revision": model.get("source_revision"),
        "source_version_consistency": source_version,
        "readiness": broad["verdict"],
        "state": public_state,
        "status": broad["verdict"],
        "decision": broad["verdict"],
        "go_no_go": broad["why"],
        "distribution_gate": controlled["verdict"],
        "local_release_candidate": local,
        "controlled_first_10_beta": controlled,
        "broad_public_launch": broad,
        "max_recommended_real_users_now": metrics.get("max_recommended_real_users_now", {}).get("value", 0),
        "verified_external_users": metrics.get("verified_external_users", {}).get("value", 0),
        "blockers": blockers,
        "evidence": [
            "eval/first_user_release_gate_snapshot.json",
            "eval/public_self_serve_launch_gate_snapshot.json",
            "eval/pypi_fresh_install_snapshot.json",
            "eval/real_user_rollout_gate_snapshot.json",
        ],
    }
    value_payload = {
        "schema_version": 1,
        "updated_at": generated,
        "headline": "ACTION / STOP / VERIFY rescue packets are green in first-user package gates",
        "summary": "Borg gives coding agents a concrete next action, a dead end to avoid, and a verification step for known failure classes.",
        "detail": value_detail,
        "primary_metric": metrics.get("first_user_release_gate", {}).get("value", "UNKNOWN"),
        "honesty_label": "LOCAL_SOURCE_GATE_NOT_EXTERNAL_ADOPTION",
    }
    impact_payload = {
        "schema_version": 1,
        "updated_at": generated,
        "headline": "external-user impact not proven yet",
        "summary": "0 verified external users in row-derived first-10 evidence; synthetic/logical load does not count as adoption.",
        "detail": "Public self-serve launch requires 10 consented external users, at least 8 installs, at least 6 useful rescues, and 0 critical privacy/security incidents.",
        "primary_impact": "NO-GO public self-serve",
        "honesty_label": "REAL_EXTERNAL_USERS_REQUIRED",
    }
    return status_payload, value_payload, impact_payload


def display_path(path: Path) -> str:
    """Return a stable path for CLI output even when tests redirect outputs."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    EVAL.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PUBLIC_STATUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_VALUE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_IMPACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    model = build_model()
    md = render_md(model)
    html_text = render_html(model, md)
    status_payload, value_payload, impact_payload = build_public_payloads(model)
    JSON_OUT.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(md, encoding="utf-8")
    HTML_OUT.write_text(html_text, encoding="utf-8")
    PUBLIC_OUT.write_text(html_text, encoding="utf-8")
    PUBLIC_STATUS_OUT.write_text(json.dumps(status_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PUBLIC_VALUE_OUT.write_text(json.dumps(value_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PUBLIC_IMPACT_OUT.write_text(json.dumps(impact_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(display_path(MD_OUT))
    print(display_path(HTML_OUT))
    print(display_path(JSON_OUT))
    print(display_path(PUBLIC_OUT))
    print(display_path(PUBLIC_STATUS_OUT))
    print(display_path(PUBLIC_VALUE_OUT))
    print(display_path(PUBLIC_IMPACT_OUT))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
