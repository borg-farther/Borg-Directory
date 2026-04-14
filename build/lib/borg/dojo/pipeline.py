"""
Borg Dojo — Cron Pipeline Orchestrator.

Full analyze-fix-report pipeline for cron execution.

Pipeline steps (per BORG_DOJO_SPEC.md section 4.8):
  1. Read sessions via SessionReader
  2. Classify failures using FailureClassifier
  3. Detect skill gaps using SkillGapDetector
  4. Produce SessionAnalysis dataclass
  5. Optionally auto-fix top 3 weaknesses
  6. Save metric snapshot via LearningCurveTracker
  7. Generate formatted report via ReportGenerator
  8. Feed into borg modules (aggregator, nudge, reputation)

Public API:
  DojoPipeline -- main orchestrator class
  analyze_recent_sessions(days, db_path) -- one-shot convenience function

Feature flag:
  BORG_DOJO_ENABLED env var must be "true" to activate (default: false).
"""

import logging
import os
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .auto_fixer import AutoFixer, FixAction
from .data_models import FailureReport, SessionAnalysis, SkillGap, ToolMetric
from .failure_classifier import classify_tool_result, detect_corrections
from .learning_curve import LearningCurveTracker, MetricSnapshot
from .report_generator import ReportGenerator
from .session_reader import SessionReader
from .skill_gap_detector import detect_skill_gaps

logger = logging.getLogger(__name__)

BORG_DOJO_ENABLED = os.getenv("BORG_DOJO_ENABLED", "true").lower() == "true"
REAL_DB_PATH = Path.home() / ".hermes" / "state.db"
SCHEMA_VERSION = 1
_cached_analysis: Optional[SessionAnalysis] = None


# ============================================================================
# Convenience function
# ============================================================================

def analyze_recent_sessions(
    days: int = 7,
    db_path: Optional[Path] = None,
) -> SessionAnalysis:
    """One-shot session analysis. Reads state.db, classifies failures,
    detects skill gaps, and returns a SessionAnalysis.

    Args:
        days: Number of days to look back (default: 7).
        db_path: Override path to state.db (default: ~/.hermes/state.db).

    Raises:
        FileNotFoundError: state.db does not exist.
        RuntimeError: state.db integrity check failed.
    """
    global _cached_analysis
    db_path = db_path or REAL_DB_PATH
    pipeline = DojoPipeline(db_path=db_path)
    with SessionReader(db_path=db_path, days=days) as reader:
        _cached_analysis = pipeline._analyze_reader(reader, days=days)
    return _cached_analysis


# ============================================================================
# DojoPipeline
# ============================================================================

class DojoPipeline:
    """Full analyze-fix-report pipeline for cron execution."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or REAL_DB_PATH
        self._analysis: Optional[SessionAnalysis] = None
        self._fixes: List[FixAction] = []
        self._snapshot: Optional[MetricSnapshot] = None

    @property
    def analysis(self) -> Optional[SessionAnalysis]:
        return self._analysis

    @property
    def snapshot(self) -> Optional[MetricSnapshot]:
        return self._snapshot

    def run(
        self,
        days: int = 7,
        auto_fix: bool = True,
        report_fmt: str = "telegram",
        deliver_to: Optional[str] = None,
    ) -> str:
        """Execute the full dojo pipeline.

        Steps: read sessions -> analyze -> auto-fix -> snapshot -> report -> feed borg.

        Args:
            days: Number of days to analyze (default: 7).
            auto_fix: Whether to apply fixes to top 3 weaknesses.
            report_fmt: "cli", "telegram", or "discord".
            deliver_to: Optional report delivery target.

        Returns:
            Formatted report string.
        """
        global _cached_analysis

        if not BORG_DOJO_ENABLED:
            return "Dojo pipeline is disabled (set BORG_DOJO_ENABLED=true to activate)."

        start = time.time()
        logger.info("Pipeline start: days=%d, auto_fix=%s", days, auto_fix)

        # Step 1: Read and analyze
        with SessionReader(db_path=self.db_path, days=days) as reader:
            self._analysis = self._analyze_reader(reader, days=days)
        _cached_analysis = self._analysis
        logger.info("Step1: %d sessions, %d tool calls, %d errors",
                    self._analysis.sessions_analyzed,
                    self._analysis.total_tool_calls,
                    self._analysis.total_errors)

        # Step 2: Auto-fix top 3
        self._fixes = []
        if auto_fix:
            fixer = AutoFixer()
            recs = fixer.recommend(self._analysis)
            self._fixes = [fixer.apply_fix(r) for r in recs[:3]]
            for f in self._fixes:
                logger.info("  Fix %s: %s %s", "OK" if f.success else "FAIL",
                            f.action, f.target_skill)

        # Step 3: Save snapshot
        self._snapshot = LearningCurveTracker().save_snapshot(
            self._analysis, self._fixes)

        # Step 4: Generate report
        history = LearningCurveTracker().load_history()
        report = ReportGenerator().generate(
            self._analysis, self._fixes, history, fmt=report_fmt)
        logger.info("Step4: report generated (%s), %.1fs", report_fmt, time.time() - start)

        # Step 5: Feed borg modules
        self._feed_aggregator()
        self._feed_nudge()
        self._feed_thompson_sampling()
        self._feed_reputation()

        return report

    # -------------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------------

    def _analyze_reader(self, reader: SessionReader, days: int = 7) -> SessionAnalysis:
        """Run analysis over an open SessionReader: classify failures + detect gaps."""
        tool_metrics: Dict[str, ToolMetric] = {}
        failure_reports: List[FailureReport] = []
        all_user_msgs: List[tuple] = []  # (content, timestamp)
        user_msgs_by_sess: Dict[str, List[tuple]] = {}
        sessions_analyzed = total_tool_calls = total_errors = total_corrections = 0

        for session in reader.iter_sessions():
            sessions_analyzed += 1
            sid = session.session_id
            tool_calls = reader.get_tool_calls(sid)
            total_tool_calls += len(tool_calls)

            for tc in tool_calls:
                tm = tool_metrics.setdefault(tc.tool_name, ToolMetric(tool_name=tc.tool_name))
                tm.total_calls += 1
                if tc.is_error:
                    total_errors += 1
                    tm.failed_calls += 1
                    is_err, cat, conf = classify_tool_result(
                        tc.result_snippet, role="tool",
                        tool_name=tc.tool_name, session_id=sid, timestamp=tc.timestamp)
                    if is_err:
                        failure_reports.append(FailureReport(
                            tool_name=tc.tool_name, error_category=cat,
                            error_snippet=tc.result_snippet[:200],
                            session_id=sid, timestamp=tc.timestamp, confidence=conf))
                else:
                    tm.successful_calls += 1

            user_msgs = reader.get_user_messages(sid)
            if user_msgs:
                all_user_msgs.extend(user_msgs)
                user_msgs_by_sess[sid] = [(c, sid) for c, _ in user_msgs]

        # Per-tool rates + top error
        for tm in tool_metrics.values():
            if tm.total_calls > 0:
                tm.success_rate = round(tm.successful_calls / tm.total_calls, 4)
            tfs = [f for f in failure_reports if f.tool_name == tm.tool_name]
            if tfs:
                cat_cnt = Counter(f.error_category for f in tfs).most_common(1)[0]
                tm.top_error_category = cat_cnt[0]
                tm.top_error_snippet = next(
                    (f.error_snippet for f in tfs if f.error_category == cat_cnt[0]), "")

        # Corrections + skill gaps
        total_corrections = len(detect_corrections(all_user_msgs))
        flat_msgs = [(c, sid) for sid, msgs in user_msgs_by_sess.items() for c, _ in msgs]
        skill_gaps: List[SkillGap] = []
        try:
            skill_gaps = detect_skill_gaps(flat_msgs)
        except Exception as e:
            logger.warning("Skill gap detection failed: %s", e)

        weakest = sorted(
            [tm for tm in tool_metrics.values() if tm.failed_calls > 0],
            key=lambda x: x.failed_calls, reverse=True)

        rate = 0.0
        if total_tool_calls > 0:
            rate = round(((total_tool_calls - total_errors) / total_tool_calls) * 100.0, 2)

        return SessionAnalysis(
            schema_version=SCHEMA_VERSION, analyzed_at=time.time(), days_covered=days,
            sessions_analyzed=sessions_analyzed, total_tool_calls=total_tool_calls,
            total_errors=total_errors, overall_success_rate=rate,
            user_corrections=total_corrections, tool_metrics=tool_metrics,
            failure_reports=failure_reports, skill_gaps=skill_gaps,
            retry_patterns=[], weakest_tools=weakest)

    # -------------------------------------------------------------------------
    # Borg integration (try/except for graceful degradation)
    # -------------------------------------------------------------------------

    def _feed_aggregator(self) -> None:
        if self._analysis is None:
            return
        try:
            from borg.aggregator import ingest_session_analysis
            ingest_session_analysis(self._analysis)
        except ImportError:
            logger.debug("aggregator unavailable -- skipping")
        except Exception as e:
            logger.warning("aggregator feed failed: %s", e)

    def _feed_nudge(self) -> None:
        if self._analysis is None:
            return
        try:
            from borg.nudge import NudgeEngine
            try:
                engine = NudgeEngine.get_instance()
                for t in (self._analysis.weakest_tools or [])[:5]:
                    engine.add_signal("weak_tool_failure",
                                      {"tool": t.tool_name, "failures": t.failed_calls})
                for g in (self._analysis.skill_gaps or [])[:3]:
                    engine.add_signal("skill_gap",
                                      {"capability": g.capability, "requests": g.request_count})
            except AttributeError:
                from borg.nudge import add_dojo_signal
                for t in (self._analysis.weakest_tools or [])[:5]:
                    add_dojo_signal("weak_tool_failure",
                                    {"tool": t.tool_name, "failures": t.failed_calls})
                for g in (self._analysis.skill_gaps or [])[:3]:
                    add_dojo_signal("skill_gap",
                                    {"capability": g.capability, "requests": g.request_count})
        except ImportError:
            logger.debug("nudge unavailable -- skipping")
        except Exception as e:
            logger.warning("nudge feed failed: %s", e)

    def _feed_thompson_sampling(self) -> None:
        """Ingest session analysis outcomes into the V3 Thompson Sampling selector.

        This closes the loop: Dojo's failure reports become priors for
        ContextualSelector.record_outcome() so BorgV3.search() makes better
        pack selections on subsequent tasks.
        """
        if self._analysis is None:
            return
        try:
            from borg.core.contextual_selector import ContextualSelector
            from borg.core.v3_integration import _StubFeedbackLoop
            selector = ContextualSelector(feedback_loop=_StubFeedbackLoop())
            for outcome in getattr(self._analysis, "outcomes", []):
                selector.record_outcome(outcome.pack_id, outcome.category, outcome.successful)
        except ImportError:
            logger.debug("ContextualSelector unavailable -- skipping")
        except Exception as e:
            logger.warning("Thompson sampling feed failed: %s", e)

    def _feed_reputation(self) -> None:
        if self._analysis is None:
            return
        try:
            from borg.reputation import apply_session_feedback
            apply_session_feedback(self._analysis)
        except ImportError:
            logger.debug("reputation unavailable -- skipping")
        except Exception as e:
            logger.warning("reputation feed failed: %s", e)

    # -------------------------------------------------------------------------
    # Accessors
    # -------------------------------------------------------------------------

    @property
    def analysis(self) -> Optional[SessionAnalysis]:
        return self._analysis

    @property
    def fixes(self) -> List[FixAction]:
        return self._fixes

    @property
    def snapshot(self) -> Optional[MetricSnapshot]:
        return self._snapshot


def get_cached_analysis() -> Optional[SessionAnalysis]:
    """Return cached SessionAnalysis from the last pipeline run.
    Used by borg/core/search.py for dynamic keyword augmentation.
    """
    return _cached_analysis
