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
