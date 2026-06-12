"""Tests for `borg receipts` — the pilot user's data rights over their local,
redacted rescue receipts: list, consented export (round-trips into the
counterfactual replay tool), outcome close-out, and permanent delete."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from borg.cli import main
from borg.core.value_receipts import record_rescue_receipt, value_summary

_REPO = Path(__file__).resolve().parents[2]

_MATCH = {
    "status": "matched",
    "problem_class": "missing_dependency",
    "confidence": "tested",
    "evidence": {"source": "seed_pack"},
}


def _run(argv, borg_home, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.setattr(sys, "argv", ["borg", *argv])
    return main()


def _seed(borg_home, n=2):
    for i in range(n):
        record_rescue_receipt(
            {**_MATCH, "problem_class": f"class_{i}"},
            trigger="manual",
            error_text=f"SomeError: case {i}",
            borg_home=borg_home,
        )


def test_receipts_list_shows_ids_and_outcomes(tmp_path, monkeypatch, capsys):
    _seed(tmp_path)
    assert _run(["receipts", "list"], tmp_path, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "#1" in out and "#2" in out
    assert "outcome=unknown" in out


def test_receipts_export_shows_content_and_respects_abort(tmp_path, monkeypatch, capsys):
    _seed(tmp_path)
    target = tmp_path / "export.json"
    monkeypatch.setattr("borg.cli._read_single_line_from_stdin", lambda _prompt: "n")
    assert _run(["receipts", "export", "--out", str(target)], tmp_path, monkeypatch) == 1
    out = capsys.readouterr().out
    assert "This is the FULL content" in out  # user sees exactly what is shared
    assert "class_0" in out
    assert "Aborted" in out
    assert not target.exists()  # abort writes nothing


def test_receipts_export_confirmed_round_trips_into_replay_tool(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=3)
    target = tmp_path / "export.json"
    monkeypatch.setattr("borg.cli._read_single_line_from_stdin", lambda _prompt: "y")
    assert _run(["receipts", "export", "--out", str(target)], tmp_path, monkeypatch) == 0
    capsys.readouterr()

    export = json.loads(target.read_text())
    assert export["schema"] == "borg-receipts-export/1"
    assert len(export["receipts"]) == 3
    assert "no raw error text" in export["note"]

    # The export is byte-compatible with scripts/counterfactual_replay.py input.
    spec = importlib.util.spec_from_file_location(
        "counterfactual_replay", _REPO / "scripts" / "counterfactual_replay.py"
    )
    cfr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfr)
    report = cfr.run([
        "--receipts-file", str(target), "--attest-consent", "test-op 2026-06-11", "--mock",
    ])
    capsys.readouterr()
    assert report["receipts_total"] == 3
    assert report["replayed"] == 3  # every exported receipt is replayable


def test_receipts_export_yes_flag_skips_prompt(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=1)
    target = tmp_path / "export.json"
    monkeypatch.setattr(
        "borg.cli._read_single_line_from_stdin",
        lambda _prompt: (_ for _ in ()).throw(AssertionError("must not prompt with --yes")),
    )
    assert _run(["receipts", "export", "--out", str(target), "--yes"], tmp_path, monkeypatch) == 0
    assert target.exists()


def test_receipts_export_empty_home_errors(tmp_path, monkeypatch, capsys):
    target = tmp_path / "export.json"
    assert _run(["receipts", "export", "--out", str(target), "--yes"], tmp_path, monkeypatch) == 1
    assert not target.exists()


def test_receipts_outcome_updates_replay_context(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=1)
    assert _run(["receipts", "outcome", "--id", "1", "--outcome", "worked"], tmp_path, monkeypatch) == 0
    capsys.readouterr()
    assert _run(["receipts", "list", "--json"], tmp_path, monkeypatch) == 0
    rows = json.loads(capsys.readouterr().out)["receipts"]
    assert rows[0]["replay_context"]["outcome"] == "worked"


def test_receipts_outcome_rejects_invalid_value(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=1)
    assert _run(["receipts", "outcome", "--id", "1", "--outcome", "amazing"], tmp_path, monkeypatch) == 1


def test_receipts_outcome_missing_id_errors(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=1)
    assert _run(["receipts", "outcome", "--id", "99", "--outcome", "worked"], tmp_path, monkeypatch) == 1


def test_receipts_delete_by_id_and_all(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=3)
    assert _run(["receipts", "delete", "--id", "2", "--yes"], tmp_path, monkeypatch) == 0
    assert value_summary(borg_home=tmp_path)["rescues_fired"] == 2

    assert _run(["receipts", "delete", "--all", "--yes"], tmp_path, monkeypatch) == 0
    assert value_summary(borg_home=tmp_path)["rescues_fired"] == 0


def test_receipts_delete_confirm_abort_keeps_rows(tmp_path, monkeypatch, capsys):
    _seed(tmp_path, n=2)
    monkeypatch.setattr("borg.cli._read_single_line_from_stdin", lambda _prompt: "n")
    assert _run(["receipts", "delete", "--all"], tmp_path, monkeypatch) == 1
    assert value_summary(borg_home=tmp_path)["rescues_fired"] == 2
