"""Regression tests for D-008: `borg autopilot` must configure the Hermes MCP
server under key `mcp_servers.borg` (not `guild`) and set an absolute BORG_HOME,
matching every other setup command and the documented contract."""

from __future__ import annotations

import sys

import yaml

from borg.cli import main


def test_autopilot_writes_borg_server_key_with_borg_home(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))  # Path.home() resolves via $HOME on POSIX
    monkeypatch.setattr(sys, "argv", ["borg", "autopilot"])

    rc = main()
    assert rc == 0

    config_path = tmp_path / ".hermes" / "config.yaml"
    assert config_path.exists()
    config = yaml.safe_load(config_path.read_text())

    servers = config["mcp_servers"]
    assert "borg" in servers, "autopilot must write mcp_servers.borg (docs mandate 'borg')"
    assert "guild" not in servers, "autopilot must not write the stale mcp_servers.guild key"

    env = servers["borg"]["env"]
    assert env.get("BORG_HOME"), "autopilot must set an absolute BORG_HOME like every other setup command"
    assert env.get("PYTHONPATH")


def test_autopilot_skill_does_not_reference_guild_mcp_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["borg", "autopilot"])
    assert main() == 0
    # The generated config must not contain a top-level guild server mapping.
    config = yaml.safe_load((tmp_path / ".hermes" / "config.yaml").read_text())
    assert set(config.get("mcp_servers", {})) == {"borg"}
