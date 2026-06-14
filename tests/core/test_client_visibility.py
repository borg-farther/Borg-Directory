"""Per-client firing visibility + hit-rate separation (pilot signal integrity).

The verdict's anti-false-negative core: the operator must be able to read, at
day 15, hit-rate / miss-rate and per-client fires SEPARATELY from
counterfactual_rate, so a recall or per-client visibility gap can't masquerade
as "no value." These tests lock that instrumentation in.
"""

from __future__ import annotations

import json
import os
import sqlite3

import pytest

from borg.core import value_receipts as vr


def _matched(pc="missing_dependency"):
    return {"status": "matched", "problem_class": pc, "confidence": "tested",
            "evidence": {"source": "seed_pack"}, "action": ["pip install x"]}


def _miss():
    return {"status": "no_confident_match", "problem_class": "unknown",
            "confidence": "unknown", "evidence": {"source": "none"}, "action": []}


def test_normalize_client():
    assert vr.normalize_client("Claude Code") == "claude-code"
    assert vr.normalize_client("Cursor") == "cursor"
    assert vr.normalize_client("") == "unknown"
    assert vr.normalize_client(None) == "unknown"  # type: ignore[arg-type]


def test_hit_rate_and_miss_rate(tmp_path):
    home = tmp_path
    vr.record_rescue_receipt(_matched(), source="mcp", client="Claude Code", borg_home=home)
    vr.record_rescue_receipt(_miss(), source="mcp", client="Claude Code", borg_home=home)
    vr.record_rescue_receipt(_matched("schema_drift"), source="mcp", client="Cursor", borg_home=home)
    s = vr.value_summary(borg_home=home)
    assert s["rescues_fired"] == 3
    assert s["rescues_matched"] == 2
    assert s["hit_rate"] == round(2 / 3, 4)
    assert s["miss_rate"] == round(1 / 3, 4)


def test_per_client_fire_and_match_breakdown(tmp_path):
    home = tmp_path
    vr.record_rescue_receipt(_matched(), source="mcp", client="Claude Code", borg_home=home)
    vr.record_rescue_receipt(_miss(), source="mcp", client="Claude Code", borg_home=home)
    vr.record_rescue_receipt(_matched("schema_drift"), source="mcp", client="Cursor", borg_home=home)
    s = vr.value_summary(borg_home=home)
    assert s["fires_by_client"] == {"claude-code": 2, "cursor": 1}
    assert s["matched_by_client"] == {"claude-code": 1, "cursor": 1}


def test_empty_store_has_the_new_keys(tmp_path):
    s = vr.value_summary(borg_home=tmp_path)
    for key in ("hit_rate", "miss_rate", "fires_by_client", "matched_by_client"):
        assert key in s
    assert s["hit_rate"] is None and s["fires_by_client"] == {}


def test_v2_to_v3_migration_preserves_receipts(tmp_path):
    db = tmp_path / "value_receipts.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE rescue_receipts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "created_at TEXT NOT NULL, status TEXT NOT NULL, problem_class TEXT DEFAULT 'unknown', "
        "confidence TEXT DEFAULT 'unknown', provenance TEXT DEFAULT 'unknown', matched INTEGER DEFAULT 0, "
        "source TEXT DEFAULT 'cli', session_id TEXT DEFAULT '', trigger TEXT DEFAULT 'unknown', "
        "trigger_n INTEGER DEFAULT 0, coverage_class TEXT DEFAULT 'unknown', replay_context TEXT DEFAULT '{}')"
    )
    conn.execute("PRAGMA user_version = 2")
    conn.execute("INSERT INTO rescue_receipts (created_at,status,problem_class,matched,source) "
                 "VALUES ('2026-06-01T00:00:00Z','matched','missing_dependency',1,'cli')")
    conn.commit()
    conn.close()

    # New code migrates on connect; old receipt survives, defaults client=unknown.
    vr.record_rescue_receipt(_matched("schema_drift"), source="mcp", client="Cursor", borg_home=tmp_path)
    s = vr.value_summary(borg_home=tmp_path)
    assert s["schema_version"] == 3
    assert s["rescues_fired"] == 2
    assert s["fires_by_client"] == {"unknown": 1, "cursor": 1}


def test_mcp_initialize_clientinfo_flows_into_receipt(tmp_path, monkeypatch):
    """End-to-end: initialize(clientInfo.name=Cursor) -> borg_rescue receipt tagged cursor."""
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server

    mcp_server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"clientInfo": {"name": "Cursor", "version": "0.42"}},
    })
    assert mcp_server._current_client.get() == "Cursor"

    mcp_server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "borg_rescue",
                   "arguments": {"input": "ModuleNotFoundError: No module named 'flask'"}},
    })
    s = vr.value_summary(borg_home=tmp_path)
    assert s["rescues_fired"] >= 1
    assert s["fires_by_client"].get("cursor", 0) >= 1, s["fires_by_client"]
