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


def _tracked_docs_entries_by_mode(mode: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-s", "docs"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) == 4 and parts[0] == mode and parts[3].startswith("docs/"):
            paths.append(parts[3])
    return paths


def _gitlink_doc_roots() -> set[str]:
    """Return docs/* gitlink roots.

    GitHub Pages legacy publishing checks out the selected source with
    submodules enabled. A gitlink under docs/ without a valid .gitmodules URL
    fails before Pages can publish any static file, so the public /docs source
    must not contain gitlinks.
    """
    roots: set[str] = set()
    for path in _tracked_docs_entries_by_mode("160000"):
        rel = Path(path).relative_to("docs")
        if rel.parts:
            roots.add(rel.parts[0])
    return roots


def _tracked_doc_symlinks() -> list[str]:
    """Return tracked symlinks under docs/.

    GitHub's Pages artifact uploader archives the selected source with
    dereferencing enabled. A symlink from docs/ to a host-local or unreadable
    path can fail artifact creation even when checkout succeeds, so the public
    /docs source must be plain files/directories only.
    """
    return _tracked_docs_entries_by_mode("120000")


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
    assert top.index("## Try Borg in 60 seconds") < text.index("## 1. Install path")


def test_release_governance_docs_use_exact_check_contexts_and_valid_codeowner() -> None:
    from eval import release_governance_gate

    docs = "\n".join(
        [
            read("docs/20260531_BORG_PRODUCTION_READY_PRIORITIZED_TODO.md"),
            read("docs/20260601_AGENT_BORG_3_3_16_IMMUTABLE_RELEASE_PACKET.md"),
        ]
    )
    for context in release_governance_gate.DEFAULT_REQUIRED_CHECKS:
        assert f"`{context}`" in docs
    codeowners = read(".github/CODEOWNERS")
    assert "@borg-farther/maintainers" not in codeowners
    assert "@borg-farther/maintainers" in docs, "docs should explain why the old team owner is invalid"
    assert "@borg-farther" in codeowners


def test_runtime_distribution_drafts_do_not_pin_stale_borg_versions() -> None:
    project = tomllib.loads(read("pyproject.toml"))["project"]
    current_version = project["version"]

    dockerfile = read("deploy/docker/Dockerfile.borg")
    assert f"ARG BORG_VERSION={current_version}" in dockerfile
    assert f"agent-borg=={current_version}" not in dockerfile, "Docker build should use the tested BORG_VERSION ARG"
    stale_pins = [pin for pin in re.findall(r"agent-borg==([0-9]+\.[0-9]+\.[0-9]+)", dockerfile) if pin != current_version]
    assert stale_pins == []
    assert 'borg --version | grep -q "${BORG_VERSION}"' in dockerfile
    assert 'borg --version | grep -q "${BORG_VERSION}";' in dockerfile
    bad_fail_open_healthcheck = '&& borg --version | grep -q "${BORG_VERSION}" \\\\n    && gh auth status > /dev/null 2>&1 || true'
    assert bad_fail_open_healthcheck not in dockerfile

    dockerignore = read(".dockerignore")
    for ignored in [".git/", ".venv/", "venv/", "dist/", "build/", ".ruff_cache/", ".mypy_cache/", ".pytest_cache/"]:
        assert ignored in dockerignore

    smithery = read("deploy/smithery/smithery.yaml")
    assert 'serverCommand: "borg-mcp"' in smithery
    assert '"version": "' + current_version + '"' in smithery
    from borg.integrations import mcp_server

    current_tool_count = len(mcp_server.TOOLS)
    assert f'"mcpTools": {current_tool_count}' in smithery
    assert f"{current_tool_count} built-in MCP tools" in smithery
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


def test_current_docs_preserve_same_version_artifact_drift_truth() -> None:
    watched = {
        "README.md": read("README.md"),
        "CHANGELOG.md": read("CHANGELOG.md"),
        "llms.txt": read("llms.txt"),
        "SUPPORT.md": read("SUPPORT.md"),
        "docs/CHANNELS_AND_INSTALL_METHODS.md": read("docs/CHANNELS_AND_INSTALL_METHODS.md"),
        "docs/20260531_BORG_PRODUCTION_READY_PRIORITIZED_TODO.md": read("docs/20260531_BORG_PRODUCTION_READY_PRIORITIZED_TODO.md"),
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
        "guild-packs 2.1.1",
        "guildpacks CLI",
        "guild_observe",
        "CONDITIONAL GO for `agent-borg==3.3.15`",
        "PyPI latest, fresh-install, and stdio MCP canaries are green for this version",
        "PyPI latest metadata and fresh PyPI install + stdio MCP canary are green for `agent-borg==3.3.15`",
        "exact-version fresh-install, stdio MCP, generated-rules, OpenClaw, CLI, and Python API canary proof is green",
        "Exact-version PyPI fresh-install, stdio MCP, generated-rules, OpenClaw, CLI, and Python API canaries pass",
        "package/local proof is green",
        "runtime and package metadata canaries pass",
        "runtime canary and package-current proof for `agent-borg==3.3.18` are green",
        "Production PyPI package/runtime path works",
        "controlled first-10 beta invites may start",
        "Controlled first-10 beta infrastructure: **GO**",
        "up to 10 consented controlled testers may proceed",
        "controlled first-10 beta may run for `agent-borg==3.3.15`",
        "Package path proof green",
        "package/local stdio proof",
        "fresh-install/MCP/generate/OpenClaw canaries pass for controlled first-10 beta",
        "published package metadata, PyPI latest, and proof artifacts agree on `agent-borg==3.3.15`",
    ]

    for path, text in watched.items():
        for phrase in stale_or_unsupported:
            assert phrase not in text, f"{path} still contains stale/unsupported phrase: {phrase}"

    assert "GitHub source exact-commit install is **GO**" in watched["README.md"]
    assert "current-source PyPI/package proof is **NO-GO**" in watched["README.md"]
    assert "Broad public self-serve launch, 100-user rollout, served/remote MCP, and measured external lift are **not claimed**" in watched["README.md"]
    assert "GitHub source exact-commit install: **GO**" in watched["docs/READINESS.md"]
    assert "Controlled first-10 beta: **NO-GO until source/package/release/ops/docs gates are green**" in watched["docs/READINESS.md"]
    assert "GitHub source exact-commit canary" in watched["docs/READINESS.md"]
    assert "served-runtime fingerprint" in watched["docs/READINESS.md"]
    assert "GitHub `main` release governance is enforced" in watched["docs/READINESS.md"]
    assert "Public self-serve launch: **NO-GO until first-10 external-user evidence passes**" in watched["docs/READINESS.md"]
    assert "Controlled first-10 beta infrastructure: **NO-GO**" in watched["docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"]
    assert "first-10 external-user evidence has not passed" in watched["docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"]


def test_prioritized_production_ready_todo_locks_current_blockers_and_boundaries() -> None:
    doc = read("docs/20260531_BORG_PRODUCTION_READY_PRIORITIZED_TODO.md")

    required_phrases = [
        "**Current rollout verdict:** **NO-GO for controlled first-10, public self-serve, served/remote MCP, 100-user rollout, and measured external lift**",
        "Current cap:** `0` real users",
        "PyPI artifact predates the current source commit by `2 days, 20:41:51.967245`",
        "production PyPI upload requires explicit user/operator approval naming package and version",
        "agents must not restart, kill, signal, or reload Hermes/gateway processes",
        "GitHub admin/maintainer approval required for branch-protection mutation",
        "verified external users >= 10",
        "install successes >= 8",
        "useful rescue moments >= 6",
        "Smithery `mcpTools` differs from `len(borg.integrations.mcp_server.TOOLS)`",
        "Final reflection from scratch",
    ]
    for phrase in required_phrases:
        assert phrase in doc

    unsupported = [
        "controlled first-10 beta invites may start",
        "public self-serve launch: GO",
        "Package path proof green",
    ]
    for phrase in unsupported:
        assert phrase not in doc
    assert "do not re-upload the same version" in doc


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
        "python -m pip install 'git+https://github.com/borg-farther/Borg-Directory.git@main'",
        "eval/github_source_install_snapshot.json",
        "GitHub source exact-commit canary",
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
        "same-version artifact is stale relative to the current source revision",
        "Package proof is red until a new immutable version is published and freshly canaried",
        "Controlled first-10 beta:** NO-GO right now",
        "stale served runtime",
        "Broad public self-serve remains **NO-GO**",
        "100-real-user rollout remains **NO-GO**",
        "Published PyPI latest observed:** `agent-borg==3.3.15`",
        "Publish a new immutable post-hardening package version and keep the proof chain synchronized",
        "`pipx install agent-borg==3.3.16` or isolated `pip install agent-borg==3.3.16`",
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
        "20260531_BORG_PRODUCTION_INVENTORY_BOARD.md",
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
    assert (ROOT / "docs" / ".nojekyll").exists(), "GitHub Pages /docs source must publish static generated files without Jekyll"
    assert not _gitlink_doc_roots(), "GitHub Pages /docs source must not contain submodule gitlinks"
    assert not _tracked_doc_symlinks(), "GitHub Pages /docs source must not contain tracked symlinks"

    for relative in [
        "docs/status.json",
        "docs/public/status.json",
        "docs/public/value.json",
        "docs/public/impact/impact.json",
    ]:
        payload = json.loads(read(relative))
        assert payload["schema_version"] == 1
        assert payload["updated_at"]

    status = json.loads(read("docs/public/status.json"))
    status_alias = json.loads(read("docs/status.json"))
    dashboard_payload = json.loads(read("eval/borg_proof_dashboard.json"))
    value = json.loads(read("docs/public/value.json"))
    assert status_alias == status
    root_index = read("docs/index.html")
    proof_index = read("docs/proof-dashboard/index.html")
    assert './public/proof-dashboard/' in root_index
    assert './status.json' in root_index
    assert '../public/proof-dashboard/' in proof_index
    assert '../status.json' in proof_index
    assert status["repo"] == "https://github.com/borg-farther/Borg-Directory"
    assert status["state"].startswith("NO-GO public self-serve")
    if status["controlled_first_10_beta"]["verdict"] == "CONDITIONAL":
        assert "controlled first-10 beta CONDITIONAL GO while gates remain green" in status["state"]
        assert "source/local release-candidate only" not in status["state"]
    else:
        assert (
            "public package proof green, release controls blocked" in status["state"]
            or "source/local release-candidate only" in status["state"]
            or "PyPI runtime canary green, package metadata stale" in status["state"]
        )
        if dashboard_payload["metrics"]["pypi_package_current_gate"]["value"] == "FAIL":
            assert status["state"] in {
                "NO-GO public self-serve; source/local release-candidate only",
                "NO-GO public self-serve; PyPI runtime canary green, package metadata stale",
            }
            assert "package gates" not in value["headline"].lower()
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
