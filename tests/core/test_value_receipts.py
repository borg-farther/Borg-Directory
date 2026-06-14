"""Tests for the local value-legibility surface (gate #10): durable, privacy-safe
rescue receipts that let `borg status` prove Borg fired and (honestly) matched.

Schema v2 adds trigger/trigger_n, coverage_class, and a redacted replay_context
(the substrate for the operator counterfactual replay)."""

from __future__ import annotations

import json
import sqlite3

from borg.core.value_receipts import (
    SCHEMA_VERSION,
    _db_path,
    record_rescue_receipt,
    recent_receipts,
    replayable_receipts,
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


# --------------------------------------------------------------------- schema v2

_V1_DDL = """CREATE TABLE rescue_receipts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    status        TEXT NOT NULL,
    problem_class TEXT NOT NULL DEFAULT 'unknown',
    confidence    TEXT NOT NULL DEFAULT 'unknown',
    provenance    TEXT NOT NULL DEFAULT 'unknown',
    matched       INTEGER NOT NULL DEFAULT 0,
    source        TEXT NOT NULL DEFAULT 'cli',
    session_id    TEXT NOT NULL DEFAULT ''
)"""


def _make_v1_db(tmp_path, rows=2):
    conn = sqlite3.connect(str(_db_path(tmp_path)))
    conn.execute(_V1_DDL)
    for i in range(rows):
        conn.execute(
            "INSERT INTO rescue_receipts (created_at, status, problem_class, matched) "
            "VALUES (?, 'matched', ?, 1)",
            (f"2026-06-0{i + 1}T00:00:00Z", f"class_{i}"),
        )
    conn.commit()
    conn.close()


def test_v1_to_v2_migration_preserves_rows_and_defaults_new_columns(tmp_path) -> None:
    _make_v1_db(tmp_path, rows=2)

    summary = value_summary(borg_home=tmp_path)  # first open migrates
    assert summary["schema_version"] == SCHEMA_VERSION == 3
    assert summary["rescues_fired"] == 2
    assert summary["rescues_matched"] == 2

    conn = sqlite3.connect(str(_db_path(tmp_path)))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM rescue_receipts ORDER BY id")]
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()

    assert user_version == 3
    for row in rows:
        assert row["trigger"] == "unknown"
        assert row["trigger_n"] == 0
        assert row["coverage_class"] == "unknown"
        assert row["replay_context"] == "{}"
        assert row["client"] == "unknown"  # v2 -> v3 adds client, defaulted


def test_v1_to_v2_migration_accepts_new_writes_alongside_old_rows(tmp_path) -> None:
    _make_v1_db(tmp_path, rows=1)
    record_rescue_receipt(_MATCH, trigger="manual", error_text="boom", borg_home=tmp_path)
    summary = value_summary(borg_home=tmp_path)
    assert summary["rescues_fired"] == 2
    assert summary["by_trigger"] == {"unknown": 1, "manual": 1}


def test_trigger_normalization() -> None:
    from borg.core.value_receipts import _normalize_trigger

    assert _normalize_trigger("manual", 0) == ("manual", 0)
    assert _normalize_trigger("task_start", 0) == ("task_start", 0)
    # n >= 2 promotes unknown to after_n_failures
    assert _normalize_trigger("unknown", 3) == ("after_n_failures", 3)
    assert _normalize_trigger("", 2) == ("after_n_failures", 2)
    # after_n_failures floors n at 2
    assert _normalize_trigger("after_n_failures", 0) == ("after_n_failures", 2)
    # junk trigger degrades to unknown, never raises
    assert _normalize_trigger("DROP TABLE", 0) == ("unknown", 0)
    # explicit trigger is not overridden by n
    assert _normalize_trigger("manual", 5) == ("manual", 0)


def test_coverage_class_buckets_and_uncovered(tmp_path) -> None:
    record_rescue_receipt(
        {**_MATCH, "problem_class": "migration_state_desync"}, borg_home=tmp_path
    )
    record_rescue_receipt(_NOMATCH, borg_home=tmp_path)
    cov = value_summary(borg_home=tmp_path)["matched_by_coverage_class"]
    assert cov == {"django_db": 1}  # unmatched receipts are 'uncovered', not counted as matched

    conn = sqlite3.connect(str(_db_path(tmp_path)))
    classes = [r[0] for r in conn.execute("SELECT coverage_class FROM rescue_receipts ORDER BY id")]
    conn.close()
    assert classes == ["django_db", "uncovered"]


def test_replay_context_is_recorded_and_redacted(tmp_path) -> None:
    secret = "AKIAIOSFODNN7EXAMPLEKEY99"
    record_rescue_receipt(
        {**_MATCH, "action": [f"export AWS_SECRET_ACCESS_KEY={secret} && retry"]},
        trigger="after_n_failures",
        trigger_n=3,
        error_text=f"ConnectionError: auth failed AWS_SECRET_ACCESS_KEY={secret}",
        borg_home=tmp_path,
    )
    raw = _db_path(tmp_path).read_bytes()
    assert secret.encode() not in raw  # neither error_text nor fix_surfaced may leak it

    [receipt] = replayable_receipts(borg_home=tmp_path)
    ctx = receipt["replay_context"]
    assert set(ctx) == {"error_redacted", "env_fingerprint", "matched_id", "fix_surfaced", "outcome"}
    assert "[REDACTED" in ctx["error_redacted"]
    assert secret not in ctx["error_redacted"]
    assert secret not in ctx["fix_surfaced"]
    assert ctx["env_fingerprint"].count("/") == 2  # OS/pyX.Y.Z/borgX.Y.Z — no PII
    assert ctx["outcome"] == "unknown"
    assert receipt["trigger"] == "after_n_failures"
    assert receipt["trigger_n"] == 3


def test_redaction_fails_closed_when_redactor_unavailable(monkeypatch, tmp_path) -> None:
    # If the privacy module breaks, the error text must be DROPPED, never stored raw.
    import borg.core.value_receipts as vr

    def _boom(_text):
        raise RuntimeError("redactor down")

    monkeypatch.setattr("borg.core.privacy.privacy_scan_structured", _boom)
    record_rescue_receipt(_MATCH, error_text="password=supersecretvalue", borg_home=tmp_path)
    raw = _db_path(tmp_path).read_bytes()
    assert b"supersecretvalue" not in raw
    [receipt] = vr.replayable_receipts(borg_home=tmp_path)
    assert "dropped" in receipt["replay_context"]["error_redacted"]


def test_value_summary_v2_fields(tmp_path) -> None:
    record_rescue_receipt(_MATCH, trigger="manual", borg_home=tmp_path)
    record_rescue_receipt(_MATCH, trigger="after_n_failures", trigger_n=2, borg_home=tmp_path)
    record_rescue_receipt(_MATCH, trigger="after_n_failures", trigger_n=4, borg_home=tmp_path)
    record_rescue_receipt(_NOMATCH, trigger="task_start", borg_home=tmp_path)

    summary = value_summary(borg_home=tmp_path)
    assert summary["caught_after_stuck"] == 2  # matched AND after_n_failures only
    assert summary["by_trigger"] == {"manual": 1, "after_n_failures": 2, "task_start": 1}
    assert summary["matched_by_coverage_class"] == {"python_dependency": 3}
    assert summary["replayable_receipts"] == 3  # matched rows carry replay_context


def test_replayable_receipts_matched_only_and_limit(tmp_path) -> None:
    record_rescue_receipt(_MATCH, error_text="err one", borg_home=tmp_path)
    record_rescue_receipt(_NOMATCH, error_text="err two", borg_home=tmp_path)
    matched = replayable_receipts(borg_home=tmp_path)
    assert len(matched) == 1 and matched[0]["problem_class"] == "missing_dependency"
    everything = replayable_receipts(matched_only=False, borg_home=tmp_path)
    assert len(everything) == 2
    assert replayable_receipts(limit=1, matched_only=False, borg_home=tmp_path)[0]["id"] == 2


def test_replayable_receipts_read_only_on_clean_home(tmp_path) -> None:
    assert replayable_receipts(borg_home=tmp_path) == []
    assert not _db_path(tmp_path).exists()


def test_v2_receipt_persists_no_raw_error_secret_from_error_text(tmp_path) -> None:
    # Same honesty rule as v1, now for the new error_text path.
    record_rescue_receipt(
        _MATCH,
        error_text="ghp_abcdefghijklmnopqrstuvwxyz0123456789 leaked plus jane.doe@acme-corp.com",
        borg_home=tmp_path,
    )
    raw = _db_path(tmp_path).read_bytes()
    assert b"ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in raw
    assert b"jane.doe@acme-corp.com" not in raw
