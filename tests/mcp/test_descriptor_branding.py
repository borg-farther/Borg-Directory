"""Regression tests for D-012: MCP tool descriptors must not reference stale
`guild_*` tool names. The real tools are all `borg_*` (plus `error_lookup`); an
agent that reads a hint like "Run guild_pull first" would call a tool that does
not exist."""

from __future__ import annotations

import re

from borg.integrations.mcp_server import TOOLS

# Stale prefixes that named nonexistent tools before the rename.
_GUILD_TOOL_RE = re.compile(
    r"guild_(search|pull|try|init|apply|publish|feedback|suggest|observe|convert|"
    r"rescue|record|reputation|analytics|context|recall|first_10|collective)"
)


def _descriptor_text(tool: dict) -> str:
    return " ".join(
        [
            str(tool.get("name", "")),
            str(tool.get("description", "")),
            str(tool.get("inputSchema", "")),
        ]
    )


def test_no_real_tool_is_named_guild() -> None:
    names = {t["name"] for t in TOOLS}
    offenders = {n for n in names if n.startswith("guild_")}
    assert not offenders, f"tools should be borg_*, found: {offenders}"


def test_no_descriptor_directs_agents_to_nonexistent_guild_tools() -> None:
    offenders = []
    for tool in TOOLS:
        for match in _GUILD_TOOL_RE.finditer(_descriptor_text(tool)):
            offenders.append((tool["name"], match.group(0)))
    assert not offenders, f"descriptors reference nonexistent guild_* tools: {offenders}"


def test_guild_uri_scheme_is_preserved() -> None:
    # The `guild://` URI scheme and ~/.hermes/guild/ paths are real identifiers and
    # must NOT be renamed; at least one descriptor still documents the scheme.
    assert any("guild://" in _descriptor_text(t) for t in TOOLS)
