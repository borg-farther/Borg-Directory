"""Tests for guild/cli.py."""

from __future__ import annotations

import argparse
import json
import sys
from unittest.mock import patch, MagicMock

import pytest

import borg.cli as cli_module
from borg.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_argv(monkeypatch):
    """Isolate each test from the real CLI argv."""
    monkeypatch.setattr(sys, "argv", ["borg"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def capture_main(args: list[str]) -> tuple[int, str, str]:
    """Run main() with given args, return (exit_code, stdout, stderr)."""
    sys.argv = ["borg"] + args
    captured_out = ""
    captured_err = ""

    def fake_stdout_write(s):
        nonlocal captured_out
        captured_out += str(s)

    def fake_stderr_write(s):
        nonlocal captured_err
        captured_err += str(s)

    try:
        with patch.object(sys, "stdout", MagicMock(wraps=sys.stdout, write=fake_stdout_write)), \
             patch.object(sys, "stderr", MagicMock(wraps=sys.stderr, write=fake_stderr_write)):
            code = main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1

    return code, captured_out, captured_err


# ---------------------------------------------------------------------------
# Subcommand dispatch tests
# ---------------------------------------------------------------------------

@patch("borg.cli.borg_search")
def test_search_dispatches_to_borg_search(mock_search):
    mock_search.return_value = '{"success": true, "matches": [], "total": 0}'
    code, out, err = capture_main(["search", "debugging"])
    assert code == 0
    mock_search.assert_called_once()
    assert mock_search.call_args[0][0] == "debugging"


@patch("borg.cli.borg_pull")
def test_pull_dispatches_to_borg_pull(mock_pull):
    mock_pull.return_value = json.dumps({"success": True, "name": "foo", "path": "/tmp/foo"})
    code, out, err = capture_main(["pull", "borg://test/foo"])
    assert code == 0
    mock_pull.assert_called_once_with("borg://test/foo")


@patch("borg.cli.borg_try")
def test_try_dispatches_to_borg_try(mock_try):
    mock_try.return_value = json.dumps({"success": True, "id": "foo"})
    code, out, err = capture_main(["try", "borg://test/foo"])
    assert code == 0
    mock_try.assert_called_once_with("borg://test/foo")


@patch("borg.cli.borg_init")
def test_init_dispatches_to_borg_init(mock_init):
    mock_init.return_value = json.dumps({
        "success": True,
        "content": "type: workflow_pack\n",
    })
    code, out, err = capture_main(["init", "my-skill"])
    assert code == 0
    mock_init.assert_called_once_with("my-skill")


@patch("borg.cli.apply_handler")
def test_apply_dispatches_to_apply_handler(mock_apply):
    mock_apply.return_value = json.dumps({
        "success": True,
        "session_id": "sess-123",
    })
    code, out, err = capture_main(["apply", "mypack", "--task", "do the thing"])
    assert code == 0
    assert mock_apply.call_args[1]["action"] == "start"
    assert mock_apply.call_args[1]["pack_name"] == "mypack"
    assert mock_apply.call_args[1]["task"] == "do the thing"


@patch("borg.cli.action_publish")
def test_publish_dispatches_to_action_publish(mock_publish):
    mock_publish.return_value = json.dumps({"success": True})
    code, out, err = capture_main(["publish", "/path/to/pack.yaml"])
    assert code == 0
    mock_publish.assert_called_once_with(path="/path/to/pack.yaml")


@patch("borg.core.session.load_session")
@patch("borg.cli._core_generate_feedback")
def test_feedback_dispatches_to_generate_feedback(mock_fb, mock_load):
    mock_load.return_value = {
        "pack_id": "p/1",
        "pack_version": "1.0",
        "phase_results": [],
        "task": "test",
        "outcome": "ok",
    }
    mock_fb.return_value = {"type": "feedback", "schema_version": "1.0"}
    code, out, err = capture_main(["feedback", "sess-123"])
    assert code == 0
    mock_fb.assert_called_once()


@patch("borg.cli.action_list")
def test_list_dispatches_to_action_list(mock_list):
    mock_list.return_value = json.dumps({
        "success": True,
        "artifacts": [
            {"type": "pack", "name": "debug-pack", "id": "borg://debug", "confidence": "tested"},
        ],
        "total": 1,
    })
    code, out, err = capture_main(["list"])
    assert code == 0
    mock_list.assert_called_once()


# ---------------------------------------------------------------------------
# Help text tests
# ---------------------------------------------------------------------------

def test_help_text_shows_all_commands():
    code, out, err = capture_main(["--help"])
    assert code == 0
    for cmd in ["search", "pull", "try", "init", "apply", "publish", "feedback", "convert", "list", "autopilot", "version"]:
        assert cmd in out, f"'{cmd}' not found in help output"


def test_help_short_flag():
    code, out, err = capture_main(["-h"])
    assert code == 0
    assert "search" in out


# ---------------------------------------------------------------------------
# Unknown / missing command
# ---------------------------------------------------------------------------

def test_unknown_command_shows_help():
    code, out, err = capture_main(["unknown-command"])
    assert code == 2
    # argparse error should contain the invalid command message
    assert "unknown-command" in err or "invalid choice" in err.lower() or "error" in err.lower()


def test_missing_subcommand_shows_help():
    code, out, err = capture_main([])
    # argparse exits with 2 for missing required args (usage error)
    assert code == 2
    assert "command" in err.lower() or "borg" in out.lower()


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_prints_version():
    code, out, err = capture_main(["version"])
    assert code == 0
    assert "borg" in out.lower()
    # Should print version string (e.g. "2.0.0")
    assert any(c.isdigit() for c in out), f"Expected version number in output: {out}"


def test_version_does_not_print_help():
    code, out, err = capture_main(["version"])
    assert code == 0
    # Help text should NOT appear in version output
    assert "search" not in out
    assert "pull" not in out


# ---------------------------------------------------------------------------
# Apply missing --task
# ---------------------------------------------------------------------------

def test_apply_requires_task():
    code, out, err = capture_main(["apply", "mypack"])
    # Should fail due to missing required --task
    assert code == 2


@patch("borg.cli.convert_auto")
def test_convert_dispatches_to_convert_auto(mock_convert):
    mock_convert.return_value = {"type": "workflow_pack", "version": "1.0"}
    code, out, err = capture_main(["convert", "/path/to/myfile.md"])
    assert code == 0
    mock_convert.assert_called_once_with("/path/to/myfile.md")
    assert "workflow_pack" in out


@patch("borg.cli.convert_skill")
def test_convert_with_explicit_format_dispatches_correctly(mock_convert):
    mock_convert.return_value = {"type": "workflow_pack", "version": "1.0", "id": "test"}
    code, out, err = capture_main(["convert", "/path/to/SKILL.md", "--format", "skill"])
    assert code == 0
    mock_convert.assert_called_once_with("/path/to/SKILL.md")
    assert "workflow_pack" in out


# ---------------------------------------------------------------------------
# setup-claude tests
# ---------------------------------------------------------------------------

from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import tempfile
import os


@patch("borg.cli.Path.home")
def test_setup_claude_creates_config_and_claude_md(mock_home, tmp_path, monkeypatch):
    """setup-claude creates claude_desktop_config.json and CLAUDE.md."""
    # Use a temp home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    # Use a temp cwd
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    code, out, err = capture_main(["setup-claude"])
    assert code == 0

    # Check config was created
    config_file = fake_home / ".config" / "claude" / "claude_desktop_config.json"
    assert config_file.exists(), f"Expected config at {config_file}, got: {list((fake_home / '.config' / 'claude').iterdir()) if (fake_home / '.config' / 'claude').exists() else 'dir not found'}"

    config = json.loads(config_file.read_text())
    assert "mcpServers" in config
    assert "borg" in config["mcpServers"]
    borg_entry = config["mcpServers"]["borg"]
    assert borg_entry["command"] == "python"
    assert borg_entry["args"] == ["-m", "borg.integrations.mcp_server"]

    # Check CLAUDE.md was created
    claude_md = project_dir / "CLAUDE.md"
    assert claude_md.exists()
    content = claude_md.read_text()
    assert "Borg Workflow Packs" in content
    assert "borg search" in content

    # Check success message
    assert "[setup-claude]" in out or "setup-claude" in out.lower()


@patch("borg.cli.Path.home")
def test_setup_claude_idempotent_no_reinstall(mock_home, tmp_path, monkeypatch):
    """setup-claude does nothing if already configured correctly."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create a correctly-configured CLAUDE.md
    claude_md = project_dir / "CLAUDE.md"
    from borg.cli import CLAUDE_MD_TEMPLATE
    instructions = CLAUDE_MD_TEMPLATE.lstrip("\n")
    claude_md.write_text("# Project CLAUDE.md\n" + instructions + "\n")

    code, out, err = capture_main(["setup-claude"])
    assert code == 0
    # Should not change anything
    assert "already" in out.lower() or "Everything already" in out


@patch("borg.cli.Path.home")
def test_setup_claude_appends_to_existing_claude_md(mock_home, tmp_path, monkeypatch):
    """setup-claude appends to CLAUDE.md if guild section not present."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create a CLAUDE.md without guild section
    claude_md = project_dir / "CLAUDE.md"
    claude_md.write_text("# Project CLAUDE.md\n\nSome existing content.\n")

    code, out, err = capture_main(["setup-claude"])
    assert code == 0

    content = claude_md.read_text()
    assert "Borg Workflow Packs" in content
    assert "Some existing content" in content


@patch("borg.cli.Path.home")
def test_setup_claude_updates_existing_guild_section(mock_home, tmp_path, monkeypatch):
    """setup-claude replaces existing guild section in CLAUDE.md."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create a CLAUDE.md with a different guild section
    claude_md = project_dir / "CLAUDE.md"
    claude_md.write_text("# Project CLAUDE.md\n\n## Borg Workflow Packs\n\nOld guild content here.\n\n## Other Section\n\nMore stuff.\n")

    code, out, err = capture_main(["setup-claude"])
    assert code == 0

    content = claude_md.read_text()
    assert "Borg Workflow Packs" in content
    assert "Old guild content" not in content
    assert "More stuff" in content


# ---------------------------------------------------------------------------
# setup-cursor tests
# ---------------------------------------------------------------------------

@patch("borg.cli.Path.home")
def test_setup_cursor_creates_mcp_json_and_cursorrules(mock_home, tmp_path, monkeypatch):
    """setup-cursor creates .cursor/mcp.json and .cursorrules."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    code, out, err = capture_main(["setup-cursor"])
    assert code == 0

    # Check .cursor/mcp.json was created
    mcp_file = project_dir / ".cursor" / "mcp.json"
    assert mcp_file.exists(), f"Expected mcp.json at {mcp_file}"

    config = json.loads(mcp_file.read_text())
    assert "mcpServers" in config
    assert "borg" in config["mcpServers"]
    borg_entry = config["mcpServers"]["borg"]
    assert borg_entry["command"] == "python"
    assert borg_entry["args"] == ["-m", "borg.integrations.mcp_server"]

    # Check .cursorrules was created
    cursor_rules = project_dir / ".cursorrules"
    assert cursor_rules.exists()
    content = cursor_rules.read_text()
    assert "Borg Workflow Packs" in content
    assert "borg search" in content


@patch("borg.cli.Path.home")
def test_setup_cursor_idempotent_no_reinstall(mock_home, tmp_path, monkeypatch):
    """setup-cursor does nothing if already configured correctly."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create a correctly-configured .cursorrules
    cursor_rules = project_dir / ".cursorrules"
    from borg.cli import CURSOR_RULES_TEMPLATE
    instructions = CURSOR_RULES_TEMPLATE.lstrip("\n")
    cursor_rules.write_text(instructions + "\n")

    code, out, err = capture_main(["setup-cursor"])
    assert code == 0
    assert "already" in out.lower() or "Everything already" in out


@patch("borg.cli.Path.home")
def test_setup_cursor_appends_to_existing_cursorrules(mock_home, tmp_path, monkeypatch):
    """setup-cursor appends to .cursorrules if guild section not present."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create .cursorrules without guild section
    cursor_rules = project_dir / ".cursorrules"
    cursor_rules.write_text("Some existing rules.\n")

    code, out, err = capture_main(["setup-cursor"])
    assert code == 0

    content = cursor_rules.read_text()
    assert "Borg Workflow Packs" in content
    assert "Some existing rules" in content


@patch("borg.cli.Path.home")
def test_setup_cursor_updates_existing_guild_section(mock_home, tmp_path, monkeypatch):
    """setup-cursor replaces existing guild section in .cursorrules."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create .cursorrules with a different guild section
    cursor_rules = project_dir / ".cursorrules"
    cursor_rules.write_text("## Borg Workflow Packs\n\nOld guild content here.\n\n## Other Section\n\nMore stuff.\n")

    code, out, err = capture_main(["setup-cursor"])
    assert code == 0

    content = cursor_rules.read_text()
    assert "Borg Workflow Packs" in content
    assert "Old guild content" not in content
    assert "More stuff" in content


@patch("borg.cli.Path.home")
def test_setup_cursor_merges_with_existing_other_mcp_servers(mock_home, tmp_path, monkeypatch):
    """setup-cursor preserves existing mcpServers entries."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create .cursor/mcp.json with other servers
    mcp_dir = project_dir / ".cursor"
    mcp_dir.mkdir()
    mcp_file = mcp_dir / "mcp.json"
    mcp_file.write_text(json.dumps({
        "mcpServers": {
            "some-other-server": {
                "command": "node",
                "args": ["/some/path"]
            }
        }
    }))

    code, out, err = capture_main(["setup-cursor"])
    assert code == 0

    config = json.loads(mcp_file.read_text())
    assert "some-other-server" in config["mcpServers"]
    assert "borg" in config["mcpServers"]
    assert config["mcpServers"]["some-other-server"]["command"] == "node"


@patch("borg.cli.Path.home")
def test_setup_claude_merges_with_existing_other_mcp_servers(mock_home, tmp_path, monkeypatch):
    """setup-claude preserves existing mcpServers entries."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mock_home.return_value = fake_home

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Pre-create claude_desktop_config.json with other servers
    config_dir = fake_home / ".config" / "claude"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "claude_desktop_config.json"
    config_file.write_text(json.dumps({
        "mcpServers": {
            "some-other-server": {
                "command": "node",
                "args": ["/some/path"]
            }
        }
    }))

    code, out, err = capture_main(["setup-claude"])
    assert code == 0

    config = json.loads(config_file.read_text())
    assert "some-other-server" in config["mcpServers"]
    assert "borg" in config["mcpServers"]
    assert config["mcpServers"]["some-other-server"]["command"] == "node"


def test_help_text_shows_setup_commands():
    """Help text includes the new setup-claude and setup-cursor commands."""
    code, out, err = capture_main(["--help"])
    assert code == 0
    assert "setup-claude" in out
    assert "setup-cursor" in out


# ---------------------------------------------------------------------------
# reputation tests
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from borg.db.reputation import ReputationProfile, AccessTier, FreeRiderStatus


@patch("borg.cli.AgentStore")
@patch("borg.cli.ReputationEngine")
def test_reputation_calls_build_profile(mock_engine_cls, mock_store_cls):
    """reputation command calls ReputationEngine.build_profile with agent_id."""
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine
    mock_engine.build_profile.return_value = ReputationProfile(
        agent_id="agent-42",
        contribution_score=0.0,
        access_tier=AccessTier.COMMUNITY,
        free_rider_status=FreeRiderStatus.OK,
        packs_published=0,
        packs_consumed=0,
        last_active_at=None,
    )

    code, out, err = capture_main(["reputation", "agent-42"])

    assert code == 0
    mock_engine.build_profile.assert_called_once_with("agent-42")
    assert "agent-42" in out
    assert "Contribution Score" in out


@patch("borg.cli.AgentStore")
@patch("borg.cli.ReputationEngine")
def test_reputation_shows_all_profile_fields(mock_engine_cls, mock_store_cls):
    """reputation command displays contribution score, tier, free-rider, packs, last active."""
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine
    mock_engine.build_profile.return_value = ReputationProfile(
        agent_id="agent-99",
        contribution_score=25.5,
        access_tier=AccessTier.VALIDATED,
        free_rider_status=FreeRiderStatus.FLAGGED,
        packs_published=3,
        packs_consumed=7,
        last_active_at=datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc),
    )

    code, out, err = capture_main(["reputation", "agent-99"])

    assert code == 0
    assert "25.50" in out
    assert "validated" in out
    assert "flagged" in out
    assert "3" in out
    assert "7" in out
    assert "2025-06-15" in out


# ---------------------------------------------------------------------------
# status tests
# ---------------------------------------------------------------------------

@patch("borg.cli.AgentStore")
@patch("borg.cli.load_persisted_sessions")
@patch("borg.cli.get_borg_dir")
def test_status_shows_borg_dir_and_db(mock_get_borg_dir, mock_load_sessions, mock_store_cls):
    """status command displays BORG_DIR and database path."""
    mock_get_borg_dir.return_value.__str__ = MagicMock(return_value="/fake/guild")
    mock_get_borg_dir.return_value.__truediv__ = lambda self, x: f"/fake/guild/{x}"
    mock_load_sessions.return_value = []
    mock_store = MagicMock()
    mock_store.list_packs.return_value = []
    mock_store.list_agents.return_value = []
    mock_store_cls.return_value = mock_store

    code, out, err = capture_main(["status"])

    assert code == 0
    assert "/fake/guild" in out
    assert "guild.db" in out


@patch("borg.cli.AgentStore")
@patch("borg.cli.load_persisted_sessions")
@patch("borg.cli.get_borg_dir")
@patch("borg.cli._active_sessions", {})
def test_status_shows_pack_and_agent_counts(mock_get_borg_dir, mock_load_sessions, mock_store_cls):
    """status command shows number of packs and agents."""
    mock_get_borg_dir.return_value.__str__ = MagicMock(return_value="/fake/guild")
    mock_get_borg_dir.return_value.__truediv__ = lambda self, x: f"/fake/guild/{x}"
    mock_load_sessions.return_value = []
    mock_store = MagicMock()
    mock_store.list_packs.return_value = [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]
    mock_store.list_agents.return_value = [{"agent_id": "a1"}, {"agent_id": "a2"}]
    mock_store_cls.return_value = mock_store

    code, out, err = capture_main(["status"])

    assert code == 0
    assert "3" in out  # pack count
    assert "2" in out  # agent count


@patch("borg.cli.AgentStore")
@patch("borg.cli.load_persisted_sessions")
@patch("borg.cli.get_borg_dir")
def test_status_shows_running_sessions(mock_get_borg_dir, mock_load_sessions, mock_store_cls):
    """status command lists running sessions with their state."""
    mock_get_borg_dir.return_value.__str__ = MagicMock(return_value="/fake/guild")
    mock_get_borg_dir.return_value.__truediv__ = lambda self, x: f"/fake/guild/{x}"

    running_session = {
        "session_id": "sess-abc",
        "pack_name": "debug-pack",
        "status": "running",
    }
    mock_load_sessions.return_value = [running_session]
    mock_store = MagicMock()
    mock_store.list_packs.return_value = []
    mock_store.list_agents.return_value = []
    mock_store_cls.return_value = mock_store

    code, out, err = capture_main(["status"])

    assert code == 0
    assert "sess-abc" in out
    assert "debug-pack" in out
    assert "running" in out


@patch("borg.cli.AgentStore")
@patch("borg.cli.load_persisted_sessions")
@patch("borg.cli.get_borg_dir")
def test_status_dispatches_to_subcommand(mock_get_borg_dir, mock_load_sessions, mock_store_cls):
    """status command is registered and callable."""
    mock_get_borg_dir.return_value.__str__ = MagicMock(return_value="/fake/guild")
    mock_get_borg_dir.return_value.__truediv__ = lambda self, x: f"/fake/guild/{x}"
    mock_load_sessions.return_value = []
    mock_store = MagicMock()
    mock_store.list_packs.return_value = []
    mock_store.list_agents.return_value = []
    mock_store_cls.return_value = mock_store

    code, out, err = capture_main(["status"])
    assert code == 0
