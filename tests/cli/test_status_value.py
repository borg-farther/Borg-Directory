"""Integration test for D-009: a CLI rescue must leave a durable value receipt
that `borg status` surfaces, so a human can prove Borg fired and helped."""

from __future__ import annotations

import json
import sys

from borg.cli import main


def _run(argv, borg_home, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.setattr(sys, "argv", ["borg", *argv])
    return main()


def test_cli_rescue_records_value_receipt_visible_in_status(tmp_path, monkeypatch, capsys) -> None:
    # Before any rescue, the tally is empty.
    _run(["status", "--json"], tmp_path, monkeypatch)
    before = json.loads(capsys.readouterr().out)["value"]
    assert before["rescues_fired"] == 0

    # A real rescue against the bundled seed corpus.
    _run(["rescue", "ModuleNotFoundError: No module named requests", "--short"], tmp_path, monkeypatch)
    capsys.readouterr()  # drain rescue output

    _run(["status", "--json"], tmp_path, monkeypatch)
    after = json.loads(capsys.readouterr().out)["value"]
    assert after["rescues_fired"] >= 1
    assert after["rescues_matched"] >= 1
    assert after["matched_by_provenance"].get("seed_corpus", 0) >= 1


def test_status_human_output_shows_value_section(tmp_path, monkeypatch, capsys) -> None:
    _run(["rescue", "TypeError: unsupported operand type(s) for +: 'int' and 'str'", "--short"], tmp_path, monkeypatch)
    capsys.readouterr()
    _run(["status"], tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "Value on this machine" in out
    assert "Borg fired:" in out
    # Honesty caveat must be present.
    assert "not claimed" in out
