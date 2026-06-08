from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CURRENT_DOCS = [
    Path("README.md"),
    Path("docs/INSTALL.md"),
    Path("docs/QUICKSTART.md"),
    Path("docs/TRYING_BORG.md"),
    Path("docs/MCP_SETUP.md"),
    Path("docs/ONBOARDING.md"),
    Path("docs/FIRST_10_BETA_READINESS.md"),
    Path("docs/INTEGRATION_GUIDE.md"),
    Path("docs/landing-page/install-snippets.md"),
]
INSTALL_DOCS = [
    Path("README.md"),
    Path("docs/INSTALL.md"),
    Path("docs/QUICKSTART.md"),
    Path("docs/TRYING_BORG.md"),
]


def _read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _code_blocks(text: str) -> list[str]:
    return re.findall(r"```(?:bash|sh|shell|powershell|ps1)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)


def _strip_fenced_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _heading_start(text: str, pattern: str) -> int:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    assert match, f"missing heading matching {pattern!r}"
    return match.start()


def _section_between(text: str, start_pattern: str, end_pattern: str | None = None) -> str:
    start = _heading_start(text, start_pattern)
    end = len(text) if end_pattern is None else _heading_start(text, end_pattern)
    assert start < end
    return text[start:end]


def _extract_os_block(text: str, os_name: str) -> str:
    match = re.search(
        rf"(?ims)^###?\s+{re.escape(os_name)}\b.*?```(?:bash|sh|shell|powershell|ps1)?\s*\n(?P<commands>.*?)```",
        text,
    )
    assert match, f"missing {os_name} install code block"
    return match.group("commands")


@pytest.mark.parametrize("relative_path", INSTALL_DOCS, ids=str)
def test_install_docs_have_os_specific_agent_borg_pipx_paths(relative_path: Path) -> None:
    text = _read(relative_path)

    for os_name in ("macOS", "Linux", "Windows"):
        block = _extract_os_block(text, os_name)
        assert "agent-borg" in block
        if relative_path.name != "FIRST_10_BETA_READINESS.md":
            assert "pipx" in block


@pytest.mark.parametrize("relative_path", CURRENT_DOCS, ids=str)
def test_current_docs_distinguish_package_cli_and_mcp_names(relative_path: Path) -> None:
    text = _read(relative_path)

    assert re.search(r"(?is)(package|install package|package name).*`agent-borg`", text), relative_path
    assert re.search(r"(?is)(cli|command).*`borg`", text), relative_path

    if relative_path in INSTALL_DOCS:
        assert "borg version" in text
        assert "borg-doctor --json" in text


@pytest.mark.parametrize("relative_path", CURRENT_DOCS, ids=str)
def test_current_docs_warn_against_wrong_borg_packages(relative_path: Path) -> None:
    text = _read(relative_path).lower()

    assert "do **not**" in text or "do not" in text
    assert "borgbackup" in text
    assert "agent-borg" in text


@pytest.mark.parametrize("relative_path", CURRENT_DOCS, ids=str)
def test_current_docs_do_not_offer_runnable_wrong_install_commands(relative_path: Path) -> None:
    text = _read(relative_path)
    bad_install = re.compile(
        r"(?im)^\s*(?:sudo\s+)?(?:python3?\s+-m\s+pip|py\s+-m\s+pip|pip|pipx|brew|apt|apt-get|dnf|pacman)\s+"
        r"(?:install|-S(?:yu)?(?:\s+--needed)?|install\s+-y)\s+"
        r"(?:borg|borgbackup|guild-packs|guildpacks|guild-mcp)\b"
    )

    for block in _code_blocks(text):
        assert not bad_install.search(block), f"{relative_path} has a runnable wrong install command:\n{block}"


@pytest.mark.parametrize("relative_path", [Path("README.md"), Path("docs/QUICKSTART.md"), Path("docs/TRYING_BORG.md"), Path("docs/MCP_SETUP.md")], ids=str)
def test_claude_code_setup_has_binary_verify_and_restart(relative_path: Path) -> None:
    text = _read(relative_path)

    assert "borg setup-claude --scope user --verify --fix" in text
    assert "Verify: PASS" in text
    assert re.search(r"fully (quit and )?restart Claude Code", text)
    assert "what MCP tools do you have from Borg?" in text
    assert "borg_rescue" in text and "borg_observe" in text and "borg_search" in text


def test_docs_index_links_install_guide() -> None:
    text = _read(Path("docs/README.md"))
    assert "[`INSTALL.md`](INSTALL.md)" in text


def test_legacy_setup_docs_are_archived_not_current_root_docs() -> None:
    assert not (ROOT / "docs" / "HERMES_NOUS_SETUP.md").exists()
    assert not (ROOT / "docs" / "OPENCLAW_SETUP.md").exists()
    assert not (ROOT / "docs" / "UX_AUDIT_HERMES.md").exists()
    assert (ROOT / "docs" / "archive" / "legacy-setup" / "HERMES_NOUS_SETUP.md").exists()
    assert (ROOT / "docs" / "archive" / "legacy-setup" / "OPENCLAW_SETUP.md").exists()
    assert (ROOT / "docs" / "archive" / "legacy-audits" / "UX_AUDIT_HERMES.md").exists()


def test_readme_has_early_agent_runner_why_and_how() -> None:
    text = _read(Path("README.md"))

    agent_start = _heading_start(text, r"^##\s+For people running AI agents\b")
    install_start = _heading_start(text, r"^##\s+1\.\s+Install path")
    assert agent_start < install_start

    block = text[agent_start:install_start]
    assert "Why:" in block
    assert "How:" in block
    assert "agent host" in block
    assert "Hermes with Claude/GPT models" in block
    assert "Claude Code" in block
    assert "Hermes Agent" in block
    assert "OpenClaw" in block
    assert "ACTION / STOP / VERIFY" in block
    assert "NO_CONFIDENT_MATCH" in block
    assert "borg setup-claude --scope user --verify --fix" in block
    assert "mcp_servers.borg" in block
    assert "mcpServers.borg" in block
    assert "what MCP tools do you have from Borg?" in block


def test_mcp_setup_has_agent_host_sections_in_order() -> None:
    text = _read(Path("docs/MCP_SETUP.md"))

    why = _heading_start(text, r"^##\s+Why connect an agent to Borg\?")
    preflight = _heading_start(text, r"^##\s+Preflight\b")
    claude = _heading_start(text, r"^##\s+Claude Code\b")
    hermes = _heading_start(text, r"^##\s+Hermes Agent\b")
    openclaw = _heading_start(text, r"^##\s+OpenClaw\b")
    generic = _heading_start(text, r"^##\s+Generic MCP clients\b")

    assert [why, preflight, claude, hermes, openclaw, generic] == sorted(
        [why, preflight, claude, hermes, openclaw, generic]
    )

    why_block = text[why:preflight]
    assert "ACTION / STOP / VERIFY" in why_block
    assert "NO_CONFIDENT_MATCH" in why_block
    assert "exact failing command" in why_block
    assert "agent host" in why_block
    assert "Hermes with Claude" in why_block
    assert "GPT" in why_block


def test_mcp_setup_has_platform_specific_borg_mcp_config() -> None:
    text = _read(Path("docs/MCP_SETUP.md"))

    claude = _section_between(text, r"^##\s+Claude Code\b", r"^##\s+Hermes Agent\b")
    assert "borg setup-claude --scope user --verify --fix" in claude
    assert "Verify: PASS" in claude
    assert "fully quit and restart Claude Code" in claude

    hermes = _section_between(text, r"^##\s+Hermes Agent\b", r"^##\s+OpenClaw\b")
    assert "regardless of whether Hermes is using Claude, GPT" in hermes
    assert "~/.hermes/config.yaml" in hermes
    assert "mcp_servers:" in hermes
    assert re.search(r"(?m)^\s*command:\s*borg-mcp\b", hermes)
    assert "mcp_borg_borg_rescue" in hermes

    openclaw = _section_between(text, r"^##\s+OpenClaw\b", r"^##\s+Generic MCP clients\b")
    assert "mcpServers" in openclaw
    assert '"command": "borg-mcp"' in openclaw
    assert "does not currently publish a verified one-command OpenClaw installer" in openclaw

    generic = _section_between(text, r"^##\s+Generic MCP clients\b", r"^##\s+Core first-user MCP tools\b")
    assert "mcpServers" in generic
    assert '"command": "borg-mcp"' in generic
    assert "BORG_HOME" in generic


def test_current_docs_do_not_reference_removed_borg_rate_tool() -> None:
    for relative_path in CURRENT_DOCS:
        assert "borg_rate" not in _read(relative_path), relative_path


def test_agent_runner_docs_keep_one_prompting_area_not_repeated_per_host() -> None:
    text = _read(Path("docs/MCP_SETUP.md"))
    visible_text = _strip_fenced_code(text)

    assert len(re.findall(r"(?im)^##\s+Prime the agent once\b", text)) == 1
    assert len(re.findall(r"(?i)Before attempting technical fixes", text)) == 1
    assert len(re.findall(r"(?i)borgbackup", visible_text)) == 1
