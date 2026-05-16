"""First-user CLI contract tests for the README onboarding path.

These tests lock the exact public commands that failed in the fresh PyPI UAT
sweep. They intentionally exercise the CLI parser/entrypoints, not only core
functions, because first users hit console scripts first.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import borg.cli as cli_module
from borg.cli.doctor import run_doctor
from borg.tests.test_cli import capture_main


def test_borg_doctor_console_entrypoint_exists_and_delegates(monkeypatch, capsys, tmp_path):
    """`borg-doctor --json` console script must import run_doctor and emit JSON."""
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(
        "sys.argv",
        ["borg-doctor", "--json"],
    )
    monkeypatch.setattr("borg.cli.doctor._sqlite_count", lambda *args, **kwargs: 1)
    monkeypatch.setattr("borg.cli.doctor.runtime_fingerprint", lambda: {"package_version": "test"})
    monkeypatch.setattr(
        "borg.integrations.mcp_server.borg_observe",
        lambda *args, **kwargs: "ACTION: test\nBORG [TEST]",
        raising=False,
    )
    monkeypatch.setattr(
        "borg.integrations.mcp_server.borg_rate",
        lambda helpful=True: "recorded",
        raising=False,
    )
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: type("Proc", (), {"stdout": '{"result":{}}', "stderr": ""})(),
    )

    code = run_doctor()
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert code == 0
    assert payload["success"] is True


def test_borg_doctor_defaults_to_canonical_borg_dir(monkeypatch, tmp_path):
    """Doctor must not silently inspect legacy ~/.borg when BORG_HOME is unset."""
    canonical_dir = tmp_path / "canonical-guild"
    monkeypatch.delenv("BORG_HOME", raising=False)
    monkeypatch.setenv("BORG_DIR", str(canonical_dir))
    from borg.cli.doctor import runtime_fingerprint

    payload = runtime_fingerprint()
    assert payload["borg_home"] == str(canonical_dir)
    assert payload["trace_db_path"] == str(canonical_dir / "traces.db")


def test_rescue_subcommand_accepts_readme_usage(monkeypatch):
    """`borg rescue <error>` must be a real CLI subcommand."""
    code, out, err = capture_main(["rescue", "ModuleNotFoundError: No module named flask", "--short"])
    assert code == 0
    assert "ACTION" in out
    assert "STOP" in out
    assert "VERIFY" in out
    assert err == ""


def test_python_module_cli_help_matches_console_contract():
    """`python -m borg.cli --help` must work for module-first environments."""
    proc = subprocess.run(
        [sys.executable, "-m", "borg.cli", "--help"],
        cwd=str(cli_module.Path(__file__).resolve().parents[2]),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    assert "rescue" in proc.stdout
    assert "version" in proc.stdout
    assert "setup-claude" in proc.stdout


def test_console_and_source_versions_match_pyproject():
    """Console/source entrypoints must report the pyproject version, not stale host borg."""
    import tomllib

    root = cli_module.Path(__file__).resolve().parents[2]
    expected = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert cli_module.__version__ == expected
    code, out, err = capture_main(["--version"])
    assert code == 0
    assert out.strip() == f"borg {expected}"
    assert err == ""


def test_setup_claude_accepts_readme_flags_without_writing_project_files(tmp_path, monkeypatch):
    """`borg setup-claude --scope user --verify --fix` is the canonical README command."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(cli_module.Path, "home", lambda: fake_home)
    monkeypatch.setattr(cli_module, "_verify_borg_runtime", lambda *args, **kwargs: (True, "initialize handshake ok"))

    code, out, err = capture_main(["setup-claude", "--scope", "user", "--verify", "--fix"])

    assert code == 0
    assert "Verify: PASS" in out
    assert (fake_home / ".claude.json").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert err == ""


def test_setup_claude_prefers_current_venv_borg_mcp(tmp_path, monkeypatch):
    """Fresh venv setup must not wire a globally-installed stale borg-mcp from PATH."""
    fake_python = tmp_path / "venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")
    local_borg_mcp = fake_python.parent / "borg-mcp"
    local_borg_mcp.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(cli_module.sys, "executable", str(fake_python))
    monkeypatch.setattr(cli_module.shutil, "which", lambda name: "/usr/local/bin/borg-mcp")

    command, args = cli_module._resolve_borg_mcp_command()
    assert command == str(local_borg_mcp)
    assert args == []


@pytest.mark.parametrize("uri", ["systematic-debugging", "borg://hermes/systematic-debugging", "guild://hermes/systematic-debugging"])
def test_try_accepts_readme_and_legacy_uri_forms(uri, monkeypatch):
    """First-user preview must not reject documented URI aliases at parser level."""
    calls: list[str] = []

    def fake_borg_try(got_uri: str) -> str:
        calls.append(got_uri)
        return json.dumps(
            {
                "success": True,
                "id": "guild://hermes/systematic-debugging",
                "problem_class": "debugging",
                "confidence": "tested",
                "phases": [{"name": "investigate"}],
                "verdict": "safe",
                "validation_errors": [],
                "safety_threats": [],
            }
        )

    monkeypatch.setattr("borg.core.search.borg_try", fake_borg_try)
    code, out, err = capture_main(["try", uri])
    assert code == 0
    assert calls == [uri]
    assert "Pack:" in out
    assert err == ""


def test_try_does_not_emit_quality_weighted_aggregator_db_path_warning(monkeypatch, caplog):
    """Recording try outcomes must not log the old missing `_db_path` warning."""
    def fake_borg_try(got_uri: str) -> str:
        return json.dumps(
            {
                "success": True,
                "id": got_uri,
                "problem_class": "debugging",
                "confidence": "tested",
                "phases": [],
                "verdict": "safe",
                "validation_errors": [],
                "safety_threats": [],
            }
        )

    monkeypatch.setattr("borg.core.search.borg_try", fake_borg_try)
    code, out, err = capture_main(["try", "systematic-debugging"])
    assert code == 0
    combined = out + err + caplog.text
    assert "QualityWeightedAggregator" not in combined
    assert "_db_path" not in combined
