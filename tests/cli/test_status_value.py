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
    assert "Found known fixes:" in out
    # Honesty caveat must be present.
    assert "not claimed" in out


def test_cli_rescue_records_manual_trigger_with_redacted_replay_context(
    tmp_path, monkeypatch, capsys
) -> None:
    secret = "AKIAIOSFODNN7EXAMPLEKEY99"
    _run(
        ["rescue", f"ModuleNotFoundError: No module named requests token={secret}", "--short"],
        tmp_path, monkeypatch,
    )
    capsys.readouterr()

    from borg.core.value_receipts import _db_path, replayable_receipts

    assert secret.encode() not in _db_path(tmp_path).read_bytes()
    [receipt] = replayable_receipts(borg_home=tmp_path)
    assert receipt["trigger"] == "manual"  # a human typed `borg rescue`
    assert "requests" in receipt["replay_context"]["error_redacted"]  # context survives
    assert secret not in receipt["replay_context"]["error_redacted"]


def test_status_headlines_caught_after_stuck(tmp_path, monkeypatch, capsys) -> None:
    from borg.core.value_receipts import record_rescue_receipt

    record_rescue_receipt(
        {"status": "matched", "problem_class": "missing_dependency", "confidence": "tested",
         "evidence": {"source": "seed_pack"}},
        trigger="after_n_failures", trigger_n=3, error_text="x", borg_home=tmp_path,
    )
    _run(["status"], tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "🛟 Caught your agent stuck: 1" in out
    assert "Found known fixes: 1 of 1 errors" in out
    assert "matched by coverage:" in out
    assert "python_dependency=1" in out


def test_status_json_exposes_v2_value_fields(tmp_path, monkeypatch, capsys) -> None:
    from borg.core.value_receipts import record_rescue_receipt

    record_rescue_receipt(
        {"status": "matched", "problem_class": "missing_dependency", "confidence": "tested",
         "evidence": {"source": "seed_pack"}},
        trigger="after_n_failures", trigger_n=2, error_text="x", borg_home=tmp_path,
    )
    _run(["status", "--json"], tmp_path, monkeypatch)
    val = json.loads(capsys.readouterr().out)["value"]
    assert val["schema_version"] == 2
    assert val["caught_after_stuck"] == 1
    assert val["by_trigger"] == {"after_n_failures": 1}
    assert val["matched_by_coverage_class"] == {"python_dependency": 1}
    assert val["replayable_receipts"] == 1
