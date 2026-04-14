"""
Unit and E2E tests for borg/dojo/pipeline.py.

Tests cover:
  - DojoPipeline construction and feature flag
  - analyze() on real state.db
  - Full run() with real state.db
  - All three report formats
  - analyze_recent_sessions() convenience function
  - Borg integration graceful degradation
  - Snapshot saving and history
  - Line count targets
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from borg.dojo import BORG_DOJO_ENABLED
from borg.dojo.auto_fixer import AutoFixer, FixAction
from borg.dojo.data_models import SessionAnalysis, ToolMetric
from borg.dojo.learning_curve import LearningCurveTracker, MetricSnapshot
from borg.dojo.pipeline import (
    BORG_DOJO_ENABLED as PIPELINE_FLAG,
    DojoPipeline,
    _cached_analysis,
    analyze_recent_sessions,
    get_cached_analysis,
)

REAL_DB = Path.home() / ".hermes" / "state.db"


def real_db_available():
    return REAL_DB.exists()


def count_lines(path: Path) -> int:
    with open(path) as f:
        return len(f.readlines())


# ============================================================================
# analyze_recent_sessions
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestAnalyzeRecentSessions:
    def test_returns_session_analysis(self):
        r = analyze_recent_sessions(days=7)
        assert isinstance(r, SessionAnalysis)

    def test_schema_version_set(self):
        r = analyze_recent_sessions(days=7)
        assert r.schema_version == 1

    def test_days_covered_field(self):
        r = analyze_recent_sessions(days=7)
        assert r.days_covered == 7

    def test_all_fields_present(self):
        r = analyze_recent_sessions(days=7)
        for f in ("schema_version", "analyzed_at", "sessions_analyzed",
                  "total_tool_calls", "total_errors", "overall_success_rate",
                  "user_corrections", "tool_metrics", "failure_reports",
                  "skill_gaps", "retry_patterns", "weakest_tools"):
            assert hasattr(r, f)

    def test_tool_metrics_structure(self):
        r = analyze_recent_sessions(days=7)
        for _, tm in r.tool_metrics.items():
            assert isinstance(tm, ToolMetric)
            assert 0.0 <= tm.success_rate <= 1.0

    def test_pii_free(self):
        r = analyze_recent_sessions(days=30)
        as_dict = vars(r)
        assert "user_id" not in as_dict
        for fr in r.failure_reports:
            assert len(fr.error_snippet) <= 200


# ============================================================================
# DojoPipeline init
# ============================================================================

class TestPipelineInit:
    def test_default_db_path(self):
        p = DojoPipeline()
        assert p.db_path == REAL_DB

    def test_custom_db_path(self):
        p = DojoPipeline(db_path=Path("/custom/path.db"))
        assert p.db_path == Path("/custom/path.db")

    def test_properties_none_before_run(self):
        p = DojoPipeline()
        assert p.analysis is None
        assert p.fixes == []
        assert p.snapshot is None


# ============================================================================
# DojoPipeline.run()
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestPipelineRun:
    def test_run_returns_string(self):
        p = DojoPipeline(db_path=REAL_DB)
        r = p.run(days=3, auto_fix=False, report_fmt="cli")
        assert isinstance(r, str)
        assert len(r) > 0

    def test_run_populates_analysis(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=False, report_fmt="cli")
        assert p.analysis is not None
        assert isinstance(p.analysis, SessionAnalysis)

    def test_run_populates_snapshot(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=False, report_fmt="cli")
        assert p.snapshot is not None
        assert isinstance(p.snapshot, MetricSnapshot)

    def test_run_stores_empty_fixes_when_autofix_disabled(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=False, report_fmt="cli")
        assert p.fixes == []

    def test_telegram_format(self):
        p = DojoPipeline(db_path=REAL_DB)
        r = p.run(days=3, auto_fix=False, report_fmt="telegram")
        assert any(c in r for c in ["✅", "❌", "⚠️", "📉", "📈"])

    def test_discord_format(self):
        p = DojoPipeline(db_path=REAL_DB)
        r = p.run(days=3, auto_fix=False, report_fmt="discord")
        assert "Dojo" in r or "dojo" in r.lower()

    def test_cli_format(self):
        p = DojoPipeline(db_path=REAL_DB)
        r = p.run(days=3, auto_fix=False, report_fmt="cli")
        assert "DOJO" in r or "Report" in r

    def test_success_rate_computed(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=7, auto_fix=False, report_fmt="cli")
        a = p.analysis
        if a.total_tool_calls > 0:
            expected = ((a.total_tool_calls - a.total_errors) / a.total_tool_calls) * 100.0
            assert abs(a.overall_success_rate - round(expected, 2)) < 0.1


# ============================================================================
# Feature flag
# ============================================================================

class TestFeatureFlag:
    def test_flag_matches_module_flag(self):
        assert PIPELINE_FLAG == BORG_DOJO_ENABLED

    def test_run_when_disabled_returns_message(self, monkeypatch):
        monkeypatch.setenv("BORG_DOJO_ENABLED", "false")
        import importlib
        import borg.dojo.pipeline as p
        importlib.reload(p)
        pipeline = p.DojoPipeline(db_path=REAL_DB)
        result = pipeline.run(days=7, auto_fix=False, report_fmt="cli")
        assert "disabled" in result.lower() or "skipped" in result.lower()
        # Reload again with enabled=True to restore module state for subsequent tests
        monkeypatch.setenv("BORG_DOJO_ENABLED", "true")
        importlib.reload(p)


# ============================================================================
# analyze() method
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestAnalyzeMethod:
    def test_analyze_returns_analysis(self):
        from borg.dojo.session_reader import SessionReader
        p = DojoPipeline(db_path=REAL_DB)
        with SessionReader(db_path=REAL_DB, days=7) as reader:
            r = p._analyze_reader(reader, days=7)
        assert isinstance(r, SessionAnalysis)

    def test_analyze_empty_db(self):
        """Empty DB returns zeroed analysis."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            empty_db = Path(f.name)
        try:
            conn = sqlite3.connect(str(empty_db))
            conn.execute("CREATE TABLE sessions(id TEXT PRIMARY KEY, source TEXT, model TEXT, "
                         "started_at REAL, ended_at REAL, tool_call_count INTEGER, "
                         "message_count INTEGER, estimated_cost_usd REAL)")
            conn.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT, "
                         "role TEXT, content TEXT, tool_calls TEXT, tool_call_id TEXT, timestamp REAL)")
            conn.commit()
            conn.close()
            from borg.dojo.session_reader import SessionReader
            p = DojoPipeline(db_path=empty_db)
            with SessionReader(db_path=empty_db, days=7) as reader:
                r = p._analyze_reader(reader, days=7)
            assert r.sessions_analyzed == 0
            assert r.total_tool_calls == 0
            assert r.total_errors == 0
        finally:
            empty_db.unlink(missing_ok=True)

    def test_tool_metrics_consistent(self):
        from borg.dojo.session_reader import SessionReader
        p = DojoPipeline(db_path=REAL_DB)
        with SessionReader(db_path=REAL_DB, days=7) as reader:
            r = p._analyze_reader(reader, days=7)
        for _, tm in r.tool_metrics.items():
            assert tm.total_calls == tm.successful_calls + tm.failed_calls


# ============================================================================
# Borg integration graceful degradation
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestBorgIntegration:
    def test_pipeline_runs_without_borg_modules(self, monkeypatch):
        """Pipeline must run even when borg core modules are absent."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("borg."):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        p = DojoPipeline(db_path=REAL_DB)
        r = p.run(days=3, auto_fix=False, report_fmt="cli")
        assert isinstance(r, str)
        assert len(r) > 0


# ============================================================================
# Cached analysis
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestCachedAnalysis:
    def test_cached_after_run(self):
        import borg.dojo.pipeline as pipeline_module
        pipeline_module._cached_analysis = None
        pipeline = DojoPipeline(db_path=REAL_DB)
        result = pipeline.run(days=3, auto_fix=False, report_fmt="cli")
        # run() populates the module-level _cached_analysis
        cached = get_cached_analysis()
        assert cached is not None
        assert cached.sessions_analyzed == pipeline.analysis.sessions_analyzed
        assert result is not None and len(result) > 0


# ============================================================================
# Snapshot saving
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestSnapshotSaving:
    def test_snapshot_fields(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=False, report_fmt="cli")
        snap = p.snapshot
        assert snap.sessions_analyzed >= 0
        assert 0.0 <= snap.overall_success_rate <= 100.0
        assert isinstance(snap.weakest_tools, list)
        assert isinstance(snap.improvements_made, list)

    def test_snapshot_roundtrip(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=False, report_fmt="cli")
        snap = p.snapshot
        d = snap.to_dict()
        restored = MetricSnapshot.from_dict(d)
        assert restored.sessions_analyzed == snap.sessions_analyzed
        assert restored.overall_success_rate == snap.overall_success_rate


# ============================================================================
# Custom db path
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestCustomDBPath:
    def test_custom_path_works(self):
        r = analyze_recent_sessions(days=1, db_path=REAL_DB)
        assert isinstance(r, SessionAnalysis)

    def test_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            analyze_recent_sessions(days=7, db_path=Path("/nonexistent/db/state.db"))


# ============================================================================
# AutoFixer integration
# ============================================================================

@pytest.mark.skipif(not real_db_available(), reason="state.db not available")
class TestAutoFixerIntegration:
    def test_recommend_returns_fix_actions(self):
        r = analyze_recent_sessions(days=7)
        fixer = AutoFixer()
        fixes = fixer.recommend(r)
        assert isinstance(fixes, list)
        for f in fixes:
            assert isinstance(f, FixAction)
            assert f.action in ("patch", "create", "evolve", "log")

    def test_fixes_sorted_by_priority(self):
        r = analyze_recent_sessions(days=7)
        fixer = AutoFixer()
        fixes = fixer.recommend(r)
        if len(fixes) >= 2:
            prs = [f.priority for f in fixes]
            assert prs == sorted(prs, reverse=True)

    def test_top_3_applied_when_autofix_true(self):
        p = DojoPipeline(db_path=REAL_DB)
        p.run(days=3, auto_fix=True, report_fmt="cli")
        assert len(p.fixes) <= 3


# ============================================================================
# Line count targets
# ============================================================================

class TestCodeSize:
    def test_pipeline_under_320_lines(self):
        lines = count_lines(Path(__file__).parent.parent / "pipeline.py")
        assert lines < 320

    def test_pipeline_over_200_lines(self):
        lines = count_lines(Path(__file__).parent.parent / "pipeline.py")
        assert lines > 200

    def test_tests_under_450_lines(self):
        lines = count_lines(Path(__file__))
        assert lines < 450

    def test_tests_over_150_lines(self):
        lines = count_lines(Path(__file__))
        assert lines > 150
