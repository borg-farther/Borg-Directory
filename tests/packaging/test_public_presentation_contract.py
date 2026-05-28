from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 CI
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _gitlink_doc_roots() -> set[str]:
    """Return docs/* gitlink roots that are preserved vendor/reference snapshots."""
    result = subprocess.run(
        ["git", "ls-files", "-s", "docs"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    roots: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) == 4 and parts[0] == "160000" and parts[3].startswith("docs/"):
            rel = Path(parts[3]).relative_to("docs")
            if rel.parts:
                roots.add(rel.parts[0])
    return roots


def test_readme_leads_with_concrete_value_before_install_matrix() -> None:
    text = read("README.md")
    top = text[: text.index("## For people running AI agents")]

    assert "failure memory for AI coding agents" in top
    assert "ACTION" in top and "STOP" in top and "VERIFY" in top
    assert "NO_CONFIDENT_MATCH" in top
    assert "pipx install agent-borg" in top
    assert 'borg rescue "ModuleNotFoundError: No module named flask" --short' in top
    assert "BORG RESCUE" in top and "status: matched" in top
    assert "Canonical/no-loss policy" not in top
    assert top.index("## Try Borg in 60 seconds") < text.index("## 1. Install `agent-borg`")


def test_runtime_distribution_drafts_do_not_pin_stale_borg_versions() -> None:
    project = tomllib.loads(read("pyproject.toml"))["project"]
    current_version = project["version"]

    dockerfile = read("deploy/docker/Dockerfile.borg")
    assert f"ARG BORG_VERSION={current_version}" in dockerfile
    assert f"agent-borg=={current_version}" not in dockerfile, "Docker build should use the tested BORG_VERSION ARG"
    stale_pins = [pin for pin in re.findall(r"agent-borg==([0-9]+\.[0-9]+\.[0-9]+)", dockerfile) if pin != current_version]
    assert stale_pins == []
    assert 'borg --version | grep -q "${BORG_VERSION}"' in dockerfile

    smithery = read("deploy/smithery/smithery.yaml")
    assert 'serverCommand: "borg-mcp"' in smithery
    assert '"version": "' + current_version + '"' in smithery
    assert '"mcpTools": 24' in smithery
    assert 'authorName: "Borg contributors"' in smithery
    assert "punkrocker" not in smithery
    assert 'remote: false' in smithery
    assert "Remote/HTTP listing remains NO-GO until served runtime cutover proof passes" in smithery
    assert "Reduce token waste" not in smithery
    assert "measured savings until first-10 evidence exists" in smithery
    assert 'borg_runtime_fingerprint' in smithery
    assert "python -m borg.integrations.mcp_server" not in smithery
    assert '"version": "1.0.0"' not in smithery
    assert "13 built-in tools" not in smithery


def test_current_docs_preserve_3315_release_candidate_truth() -> None:
    watched = {
        "README.md": read("README.md"),
        "CHANGELOG.md": read("CHANGELOG.md"),
        "llms.txt": read("llms.txt"),
        "SUPPORT.md": read("SUPPORT.md"),
        "docs/README.md": read("docs/README.md"),
        "docs/READINESS.md": read("docs/READINESS.md"),
        "docs/ROADMAP.md": read("docs/ROADMAP.md"),
        "docs/FIRST_10_BETA_READINESS.md": read("docs/FIRST_10_BETA_READINESS.md"),
        "docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md": read("docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"),
        "docs/BORG_PROOF_DASHBOARD.md": read("docs/BORG_PROOF_DASHBOARD.md"),
        "docs/VALUE_COMMUNICATION_DASHBOARD.md": read("docs/VALUE_COMMUNICATION_DASHBOARD.md"),
        "docs/VALUE_COMMUNICATION_DASHBOARD.html": read("docs/VALUE_COMMUNICATION_DASHBOARD.html"),
        "docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md": read("docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md"),
    }
    stale_or_unsupported = [
        "PyPI latest remains 3.3.7",
        "upload aborted on release-provenance gates",
        "blocked until `agent-borg==3.3.8` is published",
        "BORG_338_RELEASE_PREFLIGHT",
        "BORG_339_RELEASE_PREFLIGHT",
        "release_preflight_3_3_8",
        "fresh-install/stdout MCP",
        "guild-packs 2.1.1",
        "guildpacks CLI",
        "guild_observe",
        "conditional GO for controlled first-10 beta",
        "CONDITIONAL GO for `agent-borg==3.3.15`",
        "PyPI latest, fresh-install, and stdio MCP canaries are green for this version",
        "PyPI latest metadata and fresh PyPI install + stdio MCP canary are green for `agent-borg==3.3.15`",
        "Current package path status: `agent-borg==3.3.15` is published",
        "controlled first-10 beta invites may start",
    ]

    for path, text in watched.items():
        for phrase in stale_or_unsupported:
            assert phrase not in text, f"{path} still contains stale/unsupported phrase: {phrase}"

    assert "source/local release candidate" in watched["README.md"]
    assert "NO-GO for this 3.3.15 source branch" in watched["docs/READINESS.md"]


def test_public_examples_and_benchmark_readmes_do_not_overclaim_external_lift() -> None:
    watched = {
        "README.md": read("README.md"),
        "benchmarks/README.md": read("benchmarks/README.md"),
        "examples/skills/borg/SKILL.md": read("examples/skills/borg/SKILL.md"),
        "borg/seeds_data/borg/SKILL.md": read("borg/seeds_data/borg/SKILL.md"),
        "examples/openclaw-skill/SKILL.md": read("examples/openclaw-skill/SKILL.md"),
        "examples/openclaw-skill/references/packs/systematic-debugging.md": read(
            "examples/openclaw-skill/references/packs/systematic-debugging.md"
        ),
    }
    overclaims = [
        "thousands of agent sessions",
        "proven in real agent sessions",
        "battle-tested workflows from collective agent intelligence",
        "statistically significant agent-level success lift",
        "statistically significant external agent-level lift",
        "2.3 iterations vs 5.7",
        "~95%",
        "40% reduction from systematic approach",
        "Reduces average fix time from 20+ minutes to under 8",
    ]

    for path, text in watched.items():
        for phrase in overclaims:
            assert phrase not in text, f"{path} still contains unsupported claim: {phrase}"

    assert "Synthetic benchmark design, not public efficacy proof" in watched["benchmarks/README.md"]
    assert "not an external benchmark" in watched[
        "examples/openclaw-skill/references/packs/systematic-debugging.md"
    ]


def test_channel_matrix_documents_all_first_user_mix_paths() -> None:
    project = tomllib.loads(read("pyproject.toml"))["project"]
    current_version = project["version"]
    matrix = read("docs/CHANNELS_AND_INSTALL_METHODS.md")
    root_readme = read("README.md")
    docs_index = read("docs/README.md")

    assert f"agent-borg=={current_version}" in matrix
    for phrase in [
        "pipx install agent-borg==",
        "python -m pip install git+https://github.com/borg-farther/Borg-Directory.git@main",
        "borg generate systematic-debugging --format all --output",
        "borg convert . --format openclaw --all --output",
        "import borg, json",
        "MCP config command `borg-mcp`",
        "served/remote MCP",
        "broad public self-serve",
        "measured external lift",
    ]:
        assert phrase in matrix
    assert "CHANNELS_AND_INSTALL_METHODS.md" in root_readme
    assert "CHANNELS_AND_INSTALL_METHODS.md" in docs_index


def test_release_gates_cover_export_openclaw_api_and_mcp_mix_paths() -> None:
    first_user_gate = read("eval/run_first_user_release_gate.py")
    pypi_canary = read("eval/run_pypi_fresh_install_canary.py")

    for text in [first_user_gate, pypi_canary]:
        assert "borg_generate" in text
        assert "systematic-debugging" in text
        assert "--format" in text and "all" in text
        assert "borg_convert_openclaw" in text
        assert "openclaw" in text.lower()
        assert "python_api_check" in text or "public_import_api_check" in text
    assert "borg_runtime_fingerprint" in pypi_canary


def test_final_production_ready_todo_preserves_hard_gate_boundaries() -> None:
    todo = read("docs/20260528_BORG_PRODUCTION_READY_FINAL_TODO.md")
    required = [
        "not yet production ready",
        "not yet controlled first-10 beta ready on the new 3.3.15 channel-completeness branch",
        "Published PyPI latest observed:** `agent-borg==3.3.14`",
        "Ship 3.3.15 to GitHub main and PyPI",
        "Generated rules / OpenClaw path",
        "Served/remote MCP production channel",
        "NO-GO until the actual served process is fingerprinted",
        "Current verified external users are `0/10`",
        "Run the first-10 external beta",
        "public self-serve and 100-user rollout blocked",
        "external lift",
        "no-write",
        "Smithery draft",
    ]
    for phrase in required:
        assert phrase in todo


def test_value_communication_dashboard_exposes_row_derived_savings_contract() -> None:
    md = read("docs/VALUE_COMMUNICATION_DASHBOARD.md")
    html = read("docs/VALUE_COMMUNICATION_DASHBOARD.html")
    value = json.loads(read("docs/public/value.json"))

    for text in [md, html]:
        assert "baseline_minutes_without_borg" in text
        assert "actual_minutes_with_borg" in text
        assert "net_minutes_saved" in text
        assert "savings_claim_type=none" in text
        assert "row-derived measured savings" in text
    assert value["value_honesty_label"] == "ROW_DERIVED_EXTERNAL_USER_SAVINGS_REQUIRED"
    assert value["measured_savings"]["rows_with_measured_value"] == 0
    assert value["measured_savings"]["net_minutes_saved"] == 0.0
    assert value["measured_savings"]["net_tokens_saved"] == 0


def test_bad_answer_feedback_path_is_public_and_redaction_first() -> None:
    issue = read(".github/ISSUE_TEMPLATE/bad-answer.yml")
    cold = read("docs/COLD_START_TRUST_HARDENING.md")

    assert "bad-answer" in issue
    assert "expected-guidance" in issue
    assert "privacy-confirmation" in issue
    assert "do not paste" in issue.lower() or "do not include" in issue.lower()
    assert "Bad first answers are launch blockers" in issue
    assert "Bad-answer feedback path" in cold
    assert "borg_record_failure" in cold
    assert "redacted transcript" in cold
    assert "borg_rate" not in cold


def test_non_current_public_docs_are_bannered_or_operator_scoped() -> None:
    current = {
        "README.md",
        "INSTALL.md",
        "QUICKSTART.md",
        "TRYING_BORG.md",
        "MCP_SETUP.md",
        "CHANNELS_AND_INSTALL_METHODS.md",
        "ONBOARDING.md",
        "20260514_FIRST_10_USER_INVITE_PACKET.md",
        "FIRST_10_BETA_READINESS.md",
        "READINESS.md",
        "ROADMAP.md",
        "20260522_BORG_PRODUCTION_DAY_ONE_HARDENING_PLAN.md",
        "20260526-1302_OPTIMAL_SAFE_COLLECTIVE_LEARNING_LOOP.md",
        "20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md",
        "20260517_BORG_100_REAL_USER_READINESS.md",
        "PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md",
        "BORG_PROOF_DASHBOARD.md",
        "VALUE_COMMUNICATION_DASHBOARD.md",
        "SELF_SERVICE_OPS_READINESS.md",
        "SELF_SERVICE_OPS_READINESS_REPORT.md",
        "FIRST_10_EVIDENCE_INTAKE.md",
        "ROLLBACK_AND_COMMS_RUNBOOK.md",
        "COLD_START_TRUST_HARDENING.md",
        "SECURITY_HARDENING_BASELINE.md",
        "PRIVACY_MODEL.md",
        "PROMPT_INJECTION_THREAT_MODEL.md",
        "TRUST_AND_PROMOTION.md",
        "REVOCATION_AND_DELETION.md",
        "LEARNING_ATOM_SCHEMA.md",
        "CANONICAL_REPO.md",
        "LIVE_MCP_SELF_SERVE_CANARY.md",
        "20260526_7_USER_CONTROLLED_LAUNCH_AND_100_USER_STAGE_GATES.md",
        "20260526_ALWAYS_CURRENT_RUNTIME_AND_FEDERATED_LEARNING_PLAN.md",
        "20260526-2046_REMOTE_FEDERATED_LEARNING_GO_PROOF.md",
        "20260526-2115_FEDERATED_LEARNING_OPTIMALITY_AUDIT.md",
        "20260526-2230_MAX_VALUE_COLLECTIVE_INTELLIGENCE_LOOP.md",
        "20260528_BORG_PRODUCTION_READY_FINAL_TODO.md",
    }
    docs = ROOT / "docs"
    gitlink_roots = _gitlink_doc_roots()
    failures: list[str] = []
    for path in docs.rglob("*.md"):
        rel = path.relative_to(docs)
        if rel.parts and rel.parts[0] == "archive":
            continue
        if rel.parts and rel.parts[0] in gitlink_roots:
            continue
        if str(rel) in current:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[:600]
        if "Historical/internal — not current product documentation" not in text:
            failures.append(str(rel))
    assert not failures, "non-current docs missing historical/internal banner: " + ", ".join(failures[:20])


def test_public_live_dashboard_json_endpoints_exist_and_no_go_is_badge_red() -> None:
    for relative in [
        "docs/public/status.json",
        "docs/public/value.json",
        "docs/public/impact/impact.json",
    ]:
        payload = json.loads(read(relative))
        assert payload["schema_version"] == 1
        assert payload["updated_at"]

    status = json.loads(read("docs/public/status.json"))
    assert status["repo"] == "https://github.com/borg-farther/Borg-Directory"
    assert status["state"].startswith("NO-GO public self-serve")
    if status["controlled_first_10_beta"]["verdict"] == "CONDITIONAL":
        assert "controlled first-10 beta GO" in status["state"]
        assert "source/local release-candidate only" not in status["state"]
    else:
        assert "source/local release-candidate only" in status["state"]
    assert status["verified_external_users"] == 0

    html = read("docs/public/borg-live-dashboard.html")
    bad_idx = html.index("/(fail|red|block|no-go)/")
    ok_idx = html.index("/(go|ready|ok|green|pass)/")
    assert bad_idx < ok_idx, "NO-GO must render red before generic GO regex can match"


def test_public_docs_do_not_expose_credential_reconnaissance() -> None:
    sensitive_paths = [
        "docs/20260408-1118_borg_roadmap/SECRETS_AUDIT.md",
        "docs/20260408-1003_scope3_experiment/PREFLIGHT_REPORT.md",
        "docs/20260423-150401_github-cutover-closure-proof.md",
    ]
    forbidden = [
        "API Keys discovered & tested live",
        "Confirmed working",
        "Token scopes:",
        "Token:",
        "PYPI_TOKEN",
        "GITHUB_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "OPENROUTER_API_KEY",
        "MINIMAX_API_KEY",
        "ANTHROPIC_TOKEN",
        "OAuth quota",
    ]
    for relative in sensitive_paths:
        text = read(relative)
        assert "redacted" in text.lower()
        for phrase in forbidden:
            assert phrase not in text, f"{relative} exposes credential reconnaissance phrase: {phrase}"
