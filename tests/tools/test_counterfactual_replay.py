"""CI tests for scripts/counterfactual_replay.py — all OFFLINE (mock mode +
synthetic fixtures). Live model calls are operator-side only and never run here."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "counterfactual_replay.py"
_FIXTURES = _REPO / "tests" / "fixtures" / "counterfactual_receipts.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("counterfactual_replay", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cfr = _load_module()


# ------------------------------------------------------------------ wilson ci

def test_wilson_ci_known_values():
    lo, hi = cfr.wilson_ci(3, 10)
    assert lo == pytest.approx(0.1078, abs=1e-3)
    assert hi == pytest.approx(0.6032, abs=1e-3)
    # Zero successes still has a non-degenerate upper bound (rule-of-three-ish).
    lo0, hi0 = cfr.wilson_ci(0, 10)
    assert lo0 == 0.0
    assert 0.2 < hi0 < 0.31
    assert cfr.wilson_ci(0, 0) == (0.0, 1.0)
    # All successes is symmetric to none.
    loa, hia = cfr.wilson_ci(10, 10)
    assert hia == pytest.approx(1.0, abs=1e-12)
    assert loa == pytest.approx(1 - hi0, abs=1e-9)


def test_protocol_reading_is_ci_conservative():
    assert cfr.protocol_reading(0, 0) == "no-data"
    # 0/100: upper Wilson bound ~3.7% < 5% -> the whole CI is in the kill zone.
    assert cfr.protocol_reading(0, 100) == "kill"
    # 40/100: lower bound ~30.9% > 20% -> build.
    assert cfr.protocol_reading(40, 100) == "build"
    # 2/10 (point 20%): CI straddles the thresholds -> extend, never overclaim.
    assert cfr.protocol_reading(2, 10) == "extend"
    # 0/10: point 0% but upper bound ~27.8% -> still extend, small n can't prove kill.
    assert cfr.protocol_reading(0, 10) == "extend"


# ---------------------------------------------------------------- mock replay

def test_mock_replay_over_fixtures_exact_rate(capsys):
    report = cfr.run(["--fixtures", str(_FIXTURES), "--mock"])
    assert report["mock"] is True
    assert report["model_id"] == cfr.MODEL_ID  # pinned
    assert report["prompt_version"] == cfr.PROMPT_VERSION  # pinned
    assert report["receipts_total"] == 6
    assert report["skipped_no_context"] == 1  # the empty replay_context receipt
    assert report["replayed"] == 5
    assert report["counterfactual_count"] == 2  # pinned mock verdicts: 2 stuck
    assert report["counterfactual_rate"] == pytest.approx(0.4)
    lo, hi = report["wilson_ci_95"]
    assert 0.0 < lo < 0.4 < hi < 1.0
    assert report["protocol_reading"] == "extend"
    out = capsys.readouterr()
    assert "MOCK — not evidence" in out.err  # mock runs are loudly non-evidence


def test_mock_replay_is_deterministic():
    a = cfr.run(["--fixtures", str(_FIXTURES), "--mock"])
    b = cfr.run(["--fixtures", str(_FIXTURES), "--mock"])
    assert a == b


def test_unpinned_receipt_gets_stable_hash_verdict():
    receipt = {
        "id": 99,
        "replay_context": {"error_redacted": "SomeError: deterministic input"},
    }
    first = cfr.replay_one(receipt, mock=True)
    assert first["verdict"] in ("WOULD_HAVE_SOLVED", "WOULD_HAVE_BEEN_STUCK")
    assert cfr.replay_one(receipt, mock=True)["verdict"] == first["verdict"]


# ------------------------------------------------------------- consent + gating

def test_real_receipts_require_consent_attestation(tmp_path):
    export = tmp_path / "export.json"
    export.write_text(json.dumps([]))
    with pytest.raises(SystemExit):
        cfr.run(["--receipts-file", str(export), "--mock"])


def test_fixtures_do_not_require_consent():
    report = cfr.run(["--fixtures", str(_FIXTURES), "--mock"])
    assert report["consent_attestation"] == ""


def test_live_mode_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    export = tmp_path / "export.json"
    export.write_text(json.dumps([]))
    with pytest.raises(SystemExit):
        cfr.run(["--receipts-file", str(export), "--attest-consent", "x"])


# ------------------------------------------------------------------ db reading

def _v2_db(home: Path, rows):
    home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(home / "value_receipts.db"))
    conn.execute(
        """CREATE TABLE rescue_receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            status TEXT NOT NULL, problem_class TEXT NOT NULL DEFAULT 'unknown',
            confidence TEXT NOT NULL DEFAULT 'unknown', provenance TEXT NOT NULL DEFAULT 'unknown',
            matched INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'cli',
            session_id TEXT NOT NULL DEFAULT '', trigger TEXT NOT NULL DEFAULT 'unknown',
            trigger_n INTEGER NOT NULL DEFAULT 0, coverage_class TEXT NOT NULL DEFAULT 'unknown',
            replay_context TEXT NOT NULL DEFAULT '{}')"""
    )
    for matched, ctx in rows:
        conn.execute(
            "INSERT INTO rescue_receipts (created_at, status, matched, replay_context) "
            "VALUES ('2026-06-11T00:00:00Z', ?, ?, ?)",
            ("matched" if matched else "no_confident_match", matched, json.dumps(ctx)),
        )
    conn.commit()
    conn.close()


def test_replay_from_v2_borg_home(tmp_path):
    _v2_db(
        tmp_path,
        [
            (1, {"error_redacted": "ImportError: x", "env_fingerprint": "L/p/b",
                 "matched_id": "x", "fix_surfaced": "f", "outcome": "unknown"}),
            (0, {"error_redacted": "ignored: unmatched rows are not replayed"}),
        ],
    )
    report = cfr.run(["--borg-home", str(tmp_path), "--attest-consent", "test-op 2026-06-11", "--mock"])
    assert report["receipts_total"] == 1  # matched only
    assert report["replayed"] == 1
    assert report["consent_attestation"] == "test-op 2026-06-11"


def test_v1_db_gets_actionable_error(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "value_receipts.db"))
    conn.execute("CREATE TABLE rescue_receipts (id INTEGER PRIMARY KEY, created_at TEXT, status TEXT, matched INTEGER)")
    conn.commit()
    conn.close()
    with pytest.raises(SystemExit, match="schema v1"):
        cfr.run(["--borg-home", str(tmp_path), "--attest-consent", "x", "--mock"])


def test_missing_db_gets_actionable_error(tmp_path):
    with pytest.raises(SystemExit, match="nothing to replay"):
        cfr.run(["--borg-home", str(tmp_path), "--attest-consent", "x", "--mock"])


# -------------------------------------------------------------------- cli e2e

def test_cli_subprocess_writes_report(tmp_path):
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--fixtures", str(_FIXTURES), "--mock", "--out", str(out)],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text())
    assert report["counterfactual_rate"] == pytest.approx(0.4)
    assert json.loads(proc.stdout) == report  # stdout mirrors the file
    assert "counterfactual_rate = 2/5" in proc.stderr
