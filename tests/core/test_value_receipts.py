"""Tests for the local value-legibility surface (gate #10): durable, privacy-safe
rescue receipts that let `borg status` prove Borg fired and (honestly) matched."""

from __future__ import annotations

from borg.core.value_receipts import (
    _db_path,
    record_rescue_receipt,
    recent_receipts,
    value_summary,
)

_MATCH = {
    "status": "matched",
    "problem_class": "missing_dependency",
    "confidence": "tested",
    "evidence": {"source": "seed_pack"},
}
_NOMATCH = {
    "status": "no_confident_match",
    "problem_class": "unknown",
    "confidence": "unknown",
    "evidence": {"source": "none"},
}


def test_record_and_summary_roundtrip(tmp_path) -> None:
    record_rescue_receipt(_MATCH, source="cli", borg_home=tmp_path)
    record_rescue_receipt(_MATCH, source="cli", borg_home=tmp_path)
    record_rescue_receipt(_NOMATCH, source="cli", borg_home=tmp_path)

    summary = value_summary(borg_home=tmp_path)
    assert summary["rescues_fired"] == 3
    assert summary["rescues_matched"] == 2
    assert summary["no_confident_match"] == 1
    assert summary["matched_by_confidence"] == {"tested": 2}
    assert summary["matched_by_provenance"] == {"seed_corpus": 2}
    assert summary["distinct_problem_classes"] == 1  # same class twice
    # Honesty: never claims time/token savings.
    assert "not claimed" in summary["savings_note"].lower()


def test_provenance_mapping(tmp_path) -> None:
    for src in ("seed_pack", "local_trace_db", "atom"):
        record_rescue_receipt(
            {"status": "matched", "problem_class": "x", "confidence": "tested", "evidence": {"source": src}},
            borg_home=tmp_path,
        )
    provs = value_summary(borg_home=tmp_path)["matched_by_provenance"]
    assert provs.get("seed_corpus") == 1
    assert provs.get("your_traces") == 1
    assert provs.get("collective") == 1


def test_record_is_best_effort_and_never_raises(tmp_path) -> None:
    assert record_rescue_receipt(None, borg_home=tmp_path) == {}
    assert record_rescue_receipt(12345, borg_home=tmp_path) == {}
    # The bad calls must not have created a corrupt/poisoned summary.
    assert value_summary(borg_home=tmp_path)["rescues_fired"] == 0


def test_empty_summary_is_zero(tmp_path) -> None:
    summary = value_summary(borg_home=tmp_path)
    assert summary["rescues_fired"] == 0
    assert summary["rescues_matched"] == 0
    assert summary["matched_by_provenance"] == {}


def test_receipt_persists_no_raw_error_or_secret(tmp_path) -> None:
    # A receipt must store only the class/confidence/provenance, never raw text
    # that could carry a secret from the guidance/error.
    record_rescue_receipt(
        {
            "status": "matched",
            "problem_class": "missing_dependency",
            "confidence": "tested",
            "evidence": {"source": "seed_pack"},
            "guidance": "AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE leaked secret",
            "human_receipt": "contact jane.doe@acme-corp.com",
        },
        borg_home=tmp_path,
    )
    raw = _db_path(tmp_path).read_bytes()
    assert b"AKIAIOSFODNN7EXAMPLE" not in raw
    assert b"AWS_SECRET_ACCESS_KEY" not in raw
    assert b"jane.doe@acme-corp.com" not in raw


def test_recent_receipts_orders_newest_first(tmp_path) -> None:
    record_rescue_receipt({**_MATCH, "problem_class": "first"}, borg_home=tmp_path)
    record_rescue_receipt({**_MATCH, "problem_class": "second"}, borg_home=tmp_path)
    recent = recent_receipts(limit=5, borg_home=tmp_path)
    assert [r["problem_class"] for r in recent] == ["second", "first"]
