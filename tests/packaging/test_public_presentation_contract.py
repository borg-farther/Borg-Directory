from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_readme_leads_with_concrete_value_before_install_matrix() -> None:
    text = read("README.md")
    top = text[: text.index("## For people running AI agents")]

    assert "failure memory for AI coding agents" in top
    assert "ACTION" in top and "STOP" in top and "VERIFY" in top
    assert "NO_CONFIDENT_MATCH" in top
    assert "pipx install agent-borg" in top
    assert 'borg rescue "ModuleNotFoundError: No module named flask"' in top
    assert top.index("## Try Borg in 60 seconds") < text.index("## 1. Install `agent-borg`")


def test_current_docs_do_not_contradict_338_published_state() -> None:
    watched = {
        "CHANGELOG.md": read("CHANGELOG.md"),
        "docs/README.md": read("docs/README.md"),
        "docs/VALUE_COMMUNICATION_DASHBOARD.md": read("docs/VALUE_COMMUNICATION_DASHBOARD.md"),
        "docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md": read("docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md"),
        "docs/ROADMAP.md": read("docs/ROADMAP.md"),
        "docs/20260522_PUBLIC_PRESENTATION_AUDIT.md": read("docs/20260522_PUBLIC_PRESENTATION_AUDIT.md"),
    }
    stale = [
        "PyPI latest remains 3.3.7",
        "upload aborted on release-provenance gates",
        "NO-GO until PyPI latest/fresh-install/MCP canary passes",
        "blocked until `agent-borg==3.3.8` is published",
        "guild-packs 2.1.1",
        "guildpacks CLI",
        "guild_observe",
    ]

    for path, text in watched.items():
        for phrase in stale:
            assert phrase not in text, f"{path} still contains stale phrase: {phrase}"


def test_public_examples_and_benchmark_readmes_do_not_overclaim_external_lift() -> None:
    watched = {
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
