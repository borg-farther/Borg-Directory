from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_URL = "https://github.com/borg-farther/Borg-Directory"
LEGACY_REPOS = [
    "borg-init",
    "borg-collective-v1",
    "borg-collective-py",
    "guild-v2",
    "guild-packs",
    "guild-benchmark",
    "guild-mcp-package",
]
UNIQUE_ASSETS = [
    "borg/wiki",
    "borg/extraction.py",
    "borg/mutation",
    "borg/meta_mcp",
    "packs/*.yaml",
    "patterns/*.arp.yaml",
    "challenge source trees",
    "guild_* tool-name compatibility",
]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_root_readme_links_canonical_no_loss_policy() -> None:
    text = _read("README.md")
    assert CANONICAL_URL in text
    assert "docs/CANONICAL_REPO.md" in text
    assert "Install package:** `agent-borg`" in text
    assert "MCP server command:** `borg-mcp`" in text


def test_ai_agent_guidance_enforces_canonical_repo_and_no_loss() -> None:
    text = _read("AGENTS.md")
    assert CANONICAL_URL in text
    assert "/root/hermes-workspace/borg" in text
    assert "Do not delete" in text
    assert "/root/hermes-workspace/guild-v2" in text
    assert "docs/CANONICAL_REPO.md" in text
    assert "Do not reintroduce stale setup names" in text


def test_canonical_repo_policy_preserves_legacy_unique_assets() -> None:
    text = _read("docs/CANONICAL_REPO.md")
    assert CANONICAL_URL in text
    assert "Do **not** use `git clean`" in text or "Do **not** use `git clean`," in text
    assert "no destructive cleanup".lower() in text.lower() or "Non-destructive rule" in text
    assert "snapshot" in text
    for repo in LEGACY_REPOS:
        assert repo in text
    for asset in UNIQUE_ASSETS:
        assert asset in text.replace("`", "")
    assert "lossless replacement" in text


def test_no_loss_manifest_is_machine_readable_and_matches_policy() -> None:
    manifest = json.loads(_read("docs/repo-manifest/20260518_borg_no_loss_manifest.json"))
    assert manifest["canonical"]["github"] == CANONICAL_URL
    assert manifest["canonical"]["package"] == "agent-borg"
    assert manifest["canonical"]["cli"] == "borg"
    assert manifest["canonical"]["mcp_server"] == "borg-mcp"
    assert manifest["status"] == "implemented_guardrails_no_destructive_cleanup"
    repo_names = {repo["name"] for repo in manifest["legacy_repos"]}
    for repo in LEGACY_REPOS:
        assert any(repo in name for name in repo_names)
    assert any("no git clean" in rule for rule in manifest["non_destructive_policy"])
    assert manifest["remaining_operator_gated"]


def test_shipped_borg_seed_skill_uses_current_public_home_and_commands() -> None:
    for relative_path in ["examples/skills/borg/SKILL.md", "borg/seeds_data/borg/SKILL.md"]:
        text = _read(relative_path)
        assert CANONICAL_URL in text
        assert "pip install agent-borg" in text
        assert "borg-mcp" in text
        assert "punkrocker/agent-borg" not in text
        assert "legacy-org/agent-borg" not in text
        assert "borgd" not in text
