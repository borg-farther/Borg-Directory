"""Tests for the federation kill-switch (PART 10 gate #27).

`borg sharing off` must instantly fail-close every learning-atom egress path,
independent of the opt-in `local_only` default, and `borg sharing on` must
restore it. Local-only operations must remain available while the switch is on.
"""

from __future__ import annotations

import json
import sys

import pytest

from borg.core.sharing import (
    SharingDisabledError,
    assert_sharing_allowed,
    disable_sharing,
    enable_sharing,
    is_sharing_disabled,
    sharing_status,
)


# --------------------------------------------------------------------------- #
# core module
# --------------------------------------------------------------------------- #
def test_default_enabled(tmp_path) -> None:
    assert is_sharing_disabled(tmp_path) is False
    assert sharing_status(tmp_path)["disabled"] is False


def test_disable_enable_roundtrip(tmp_path) -> None:
    record = disable_sharing("incident-7", borg_home=tmp_path)
    assert record["disabled"] is True
    assert record["reason"] == "incident-7"
    assert is_sharing_disabled(tmp_path) is True
    assert (tmp_path / "SHARING_DISABLED").exists()

    status = sharing_status(tmp_path)
    assert status["disabled"] is True
    assert status["reason"] == "incident-7"
    assert status["disabled_at"]

    out = enable_sharing(borg_home=tmp_path)
    assert out["was_disabled"] is True
    assert is_sharing_disabled(tmp_path) is False
    assert not (tmp_path / "SHARING_DISABLED").exists()


def test_disable_is_idempotent_and_enable_when_already_on(tmp_path) -> None:
    disable_sharing(borg_home=tmp_path)
    disable_sharing(borg_home=tmp_path)  # no error
    assert is_sharing_disabled(tmp_path) is True
    enable_sharing(borg_home=tmp_path)
    out = enable_sharing(borg_home=tmp_path)  # already enabled
    assert out["was_disabled"] is False


def test_assert_sharing_allowed_fails_closed(tmp_path) -> None:
    disable_sharing(borg_home=tmp_path)
    with pytest.raises(SharingDisabledError):
        assert_sharing_allowed("atom publish", borg_home=tmp_path)
    enable_sharing(borg_home=tmp_path)
    assert_sharing_allowed("atom publish", borg_home=tmp_path)  # must not raise


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _run_cli(argv, borg_home, monkeypatch) -> int:
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.setattr(sys, "argv", ["borg", *argv])
    from borg.cli import main

    return main()


def test_cli_off_status_on(tmp_path, monkeypatch, capsys) -> None:
    assert _run_cli(["sharing", "off", "--reason", "ks-test"], tmp_path, monkeypatch) == 0
    assert (tmp_path / "SHARING_DISABLED").exists()
    capsys.readouterr()  # drain the `off` human output

    assert _run_cli(["sharing", "status", "--json"], tmp_path, monkeypatch) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["disabled"] is True
    assert status["reason"] == "ks-test"

    assert _run_cli(["sharing", "on"], tmp_path, monkeypatch) == 0
    assert not (tmp_path / "SHARING_DISABLED").exists()


# --------------------------------------------------------------------------- #
# egress guards (the gate #27 acceptance tests)
# --------------------------------------------------------------------------- #
def test_atom_publish_blocked_when_sharing_off(tmp_path, monkeypatch, capsys) -> None:
    """gate #27: `borg sharing off` blocks a subsequent atom publish."""
    disable_sharing(borg_home=tmp_path)
    rc = _run_cli(["atom", "publish", str(tmp_path / "nope.yaml")], tmp_path, monkeypatch)
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["killswitch"] == "sharing_disabled"


def test_borg_publish_blocked_when_sharing_off(tmp_path, monkeypatch, capsys) -> None:
    disable_sharing(borg_home=tmp_path)
    rc = _run_cli(["publish", str(tmp_path / "nope.yaml")], tmp_path, monkeypatch)
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["killswitch"] == "sharing_disabled"


def test_atom_distill_nonlocal_blocked_but_local_allowed(tmp_path, monkeypatch, capsys) -> None:
    # Seed one trace so distill can resolve a trace id.
    assert _run_cli(
        ["observe", "fix zzz", "--error", "ZZZError ks-test", "--agent", "a", "--json"],
        tmp_path,
        monkeypatch,
    ) == 0
    # `observe --json` prints a human "Recorded trace ..." line then the JSON.
    trace_id = json.loads(capsys.readouterr().out.strip().splitlines()[-1])["trace_id"]

    disable_sharing(borg_home=tmp_path)
    # global scope is an egress preparation -> blocked
    rc = _run_cli(["atom", "distill", "--trace-id", trace_id, "--scope", "global"], tmp_path, monkeypatch)
    assert rc == 1
    assert "kill-switch engaged" in capsys.readouterr().err

    # local scope never leaves the device -> allowed even while the switch is engaged
    rc = _run_cli(["atom", "distill", "--trace-id", trace_id, "--scope", "local"], tmp_path, monkeypatch)
    captured = capsys.readouterr()
    assert rc == 0
    assert "kill-switch" not in captured.out


# --------------------------------------------------------------------------- #
# MCP tool guard
# --------------------------------------------------------------------------- #
def test_mcp_borg_publish_blocked_when_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    disable_sharing(borg_home=tmp_path)
    from borg.integrations.mcp_server import borg_publish

    res = json.loads(borg_publish(action="publish", path=str(tmp_path / "x.yaml")))
    assert res["killswitch"] == "sharing_disabled"


def test_mcp_borg_publish_list_not_blocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    disable_sharing(borg_home=tmp_path)
    from borg.integrations.mcp_server import borg_publish

    res = json.loads(borg_publish(action="list"))
    # `list` is read-only and must not be blocked by the egress kill-switch.
    assert "killswitch" not in res
