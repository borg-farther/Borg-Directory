from __future__ import annotations

from pathlib import Path
import json
import subprocess

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


def test_current_docs_do_not_contradict_3310_published_state() -> None:
    watched = {
        "README.md": read("README.md"),
        "CHANGELOG.md": read("CHANGELOG.md"),
        "docs/README.md": read("docs/README.md"),
        "docs/READINESS.md": read("docs/READINESS.md"),
        "docs/ROADMAP.md": read("docs/ROADMAP.md"),
        "docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md": read("docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"),
        "docs/BORG_PROOF_DASHBOARD.md": read("docs/BORG_PROOF_DASHBOARD.md"),
        "docs/VALUE_COMMUNICATION_DASHBOARD.md": read("docs/VALUE_COMMUNICATION_DASHBOARD.md"),
        "docs/VALUE_COMMUNICATION_DASHBOARD.html": read("docs/VALUE_COMMUNICATION_DASHBOARD.html"),
        "docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md": read("docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md"),
    }
    stale = [
        "PyPI latest remains 3.3.7",
        "upload aborted on release-provenance gates",
        "NO-GO until PyPI latest/fresh-install/MCP canary passes",
        "PyPI latest/fresh-install/stdio MCP package evidence is not green yet",
        "no controlled first-10 beta invites until package evidence is green",
        "blocked until `agent-borg==3.3.8` is published",
        "BORG_338_RELEASE_PREFLIGHT",
        "BORG_339_RELEASE_PREFLIGHT",
        "release_preflight_3_3_8",
        "fresh-install/stdout MCP",
        "guild-packs 2.1.1",
        "guildpacks CLI",
        "guild_observe",
    ]

    for path, text in watched.items():
        for phrase in stale:
            assert phrase not in text, f"{path} still contains stale phrase: {phrase}"


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

def test_non_current_public_docs_are_bannered_or_operator_scoped() -> None:
    current = {
        "README.md",
        "INSTALL.md",
        "QUICKSTART.md",
        "TRYING_BORG.md",
        "MCP_SETUP.md",
        "ONBOARDING.md",
        "20260514_FIRST_10_USER_INVITE_PACKET.md",
        "FIRST_10_BETA_READINESS.md",
        "READINESS.md",
        "ROADMAP.md",
        "20260522_BORG_PRODUCTION_DAY_ONE_HARDENING_PLAN.md",
        "20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md",
        "20260517_BORG_100_REAL_USER_READINESS.md",
        "PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md",
        "BORG_PROOF_DASHBOARD.md",
        "VALUE_COMMUNICATION_DASHBOARD.md",
        "SECURITY_HARDENING_BASELINE.md",
        "PRIVACY_MODEL.md",
        "PROMPT_INJECTION_THREAT_MODEL.md",
        "TRUST_AND_PROMOTION.md",
        "REVOCATION_AND_DELETION.md",
        "LEARNING_ATOM_SCHEMA.md",
        "CANONICAL_REPO.md",
        "LIVE_MCP_SELF_SERVE_CANARY.md",
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
    assert "controlled first-10 beta GO" in status["state"]
    assert "source/local release-candidate only" not in status["state"]
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
