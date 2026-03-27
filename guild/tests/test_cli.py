"""Tests for guild/cli.py."""

from __future__ import annotations

import argparse
import json
import sys
from unittest.mock import patch, MagicMock

import pytest

import guild.cli as cli_module
from guild.cli import main


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_argv(monkeypatch):
    """Isolate each test from the real CLI argv."""
    monkeypatch.setattr(sys, "argv", ["guildpacks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def capture_main(args: list[str]) -> tuple[int, str, str]:
    """Run main() with given args, return (exit_code, stdout, stderr)."""
    sys.argv = ["guildpacks"] + args
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

@patch("guild.cli.guild_search")
def test_search_dispatches_to_guild_search(mock_search):
    mock_search.return_value = '{"success": true, "matches": [], "total": 0}'
    code, out, err = capture_main(["search", "debugging"])
    assert code == 0
    mock_search.assert_called_once()
    assert mock_search.call_args[0][0] == "debugging"


@patch("guild.cli.guild_pull")
def test_pull_dispatches_to_guild_pull(mock_pull):
    mock_pull.return_value = json.dumps({"success": True, "name": "foo", "path": "/tmp/foo"})
    code, out, err = capture_main(["pull", "guild://test/foo"])
    assert code == 0
    mock_pull.assert_called_once_with("guild://test/foo")


@patch("guild.cli.guild_try")
def test_try_dispatches_to_guild_try(mock_try):
    mock_try.return_value = json.dumps({"success": True, "id": "foo"})
    code, out, err = capture_main(["try", "guild://test/foo"])
    assert code == 0
    mock_try.assert_called_once_with("guild://test/foo")


@patch("guild.cli.guild_init")
def test_init_dispatches_to_guild_init(mock_init):
    mock_init.return_value = json.dumps({
        "success": True,
        "content": "type: workflow_pack\n",
    })
    code, out, err = capture_main(["init", "my-skill"])
    assert code == 0
    mock_init.assert_called_once_with("my-skill")


@patch("guild.cli.apply_handler")
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


@patch("guild.cli.action_publish")
def test_publish_dispatches_to_action_publish(mock_publish):
    mock_publish.return_value = json.dumps({"success": True})
    code, out, err = capture_main(["publish", "/path/to/pack.yaml"])
    assert code == 0
    mock_publish.assert_called_once_with(path="/path/to/pack.yaml")


@patch("guild.core.session.load_session")
@patch("guild.cli._core_generate_feedback")
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


@patch("guild.cli.action_list")
def test_list_dispatches_to_action_list(mock_list):
    mock_list.return_value = json.dumps({
        "success": True,
        "artifacts": [
            {"type": "pack", "name": "debug-pack", "id": "guild://debug", "confidence": "tested"},
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
    assert "command" in err.lower() or "guild" in out.lower()


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_prints_version():
    code, out, err = capture_main(["version"])
    assert code == 0
    assert "guild" in out.lower()
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


@patch("guild.cli.convert_auto")
def test_convert_dispatches_to_convert_auto(mock_convert):
    mock_convert.return_value = {"type": "workflow_pack", "version": "1.0"}
    code, out, err = capture_main(["convert", "/path/to/myfile.md"])
    assert code == 0
    mock_convert.assert_called_once_with("/path/to/myfile.md")
    assert "workflow_pack" in out


@patch("guild.cli.convert_skill")
def test_convert_with_explicit_format_dispatches_correctly(mock_convert):
    mock_convert.return_value = {"type": "workflow_pack", "version": "1.0", "id": "test"}
    code, out, err = capture_main(["convert", "/path/to/SKILL.md", "--format", "skill"])
    assert code == 0
    mock_convert.assert_called_once_with("/path/to/SKILL.md")
    assert "workflow_pack" in out
