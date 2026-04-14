"""
Borg Dojo — Learning Curve Tracker.

Saves daily metric snapshots for trend analysis. Supports sparkline generation
and retrieval of historical data.

Public API:
  save_snapshot(analysis: SessionAnalysis, fixes: List[FixAction]) -> MetricSnapshot
  load_history() -> List[MetricSnapshot]
  get_trend(metric: str, days: int) -> Dict
  sparkline(metric: str, width: int) -> str

Constants:
  METRICS_FILE — path to the JSON metrics store
  MAX_SNAPSHOTS — maximum snapshots to retain (365)
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from borg.dojo.data_models import FixAction, MetricSnapshot, SessionAnalysis

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------

METRICS_FILE = Path.home() / ".hermes" / "borg" / "dojo_metrics.json"
MAX_SNAPSHOTS = 365

__all__ = ["LearningCurveTracker", "METRICS_FILE", "MAX_SNAPSHOTS"]


# -----------------------------------------------------------------------
# LearningCurveTracker
# -----------------------------------------------------------------------

class LearningCurveTracker:
    """Tracks agent performance over time."""

    def __init__(self, metrics_file: Optional[Path] = None):
        self.metrics_file = metrics_file or METRICS_FILE
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Snapshot operations
    # ------------------------------------------------------------------

    def save_snapshot(
        self,
        analysis,
        fixes: Optional[List] = None,
    ) -> MetricSnapshot:
        """Save a metric snapshot from a SessionAnalysis.

        Args:
            analysis: SessionAnalysis object with analysis results.
            fixes: List of FixAction objects applied in this cycle.

        Returns:
            The saved MetricSnapshot.
        """
        fixes = fixes or []

        weakest_tools = []
        for tm in analysis.weakest_tools[:5]:
            weakest_tools.append({
                "tool_name": tm.tool_name,
                "error_count": tm.failed_calls,
                "success_rate": round(tm.success_rate * 100, 1),
                "top_error": tm.top_error_category,
            })

        improvements = []
        for fix in fixes:
            if fix.applied:
                improvements.append({
                    "skill": fix.target_skill,
                    "action": fix.action,
                    "success": fix.success,
                    "priority": fix.priority,
                })

        snapshot = MetricSnapshot(
            timestamp=time.time(),
            date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            sessions_analyzed=analysis.sessions_analyzed,
            total_tool_calls=analysis.total_tool_calls,
            overall_success_rate=analysis.overall_success_rate,
            total_errors=analysis.total_errors,
            user_corrections=analysis.user_corrections,
            skill_gaps_count=len(analysis.skill_gaps),
            retry_pattern_count=len(analysis.retry_patterns),
            weakest_tools=weakest_tools,
            improvements_made=improvements,
            schema_version=1,
        )

        # Load existing history, append, rotate
        history = self._load_raw()
        history.append(snapshot.to_dict())

        # Rotate to MAX_SNAPSHOTS
        if len(history) > MAX_SNAPSHOTS:
            history = history[-MAX_SNAPSHOTS:]

        self._save_raw(history)
        logger.info("Saved metric snapshot: %s sessions, %.1f%% success rate",
                    snapshot.sessions_analyzed, snapshot.overall_success_rate)

        return snapshot

    def load_history(self) -> List[MetricSnapshot]:
        """Load all metric snapshots, newest last."""
        raw = self._load_raw()
        result = []
        for d in raw:
            try:
                result.append(MetricSnapshot.from_dict(d))
            except Exception as e:
                logger.warning("Skipping corrupted snapshot: %s", e)
        return result

    def get_trend(self, metric: str = "overall_success_rate", days: int = 30) -> Dict:
        """Compute trend statistics for a metric over the last N days.

        Args:
            metric: One of the MetricSnapshot numeric fields.
            days: Number of days to look back.

        Returns:
            Dict with 'values', 'avg', 'min', 'max', 'direction'.
        """
        history = self.load_history()
        cutoff = time.time() - (days * 86400)

        values = []
        for snap in history:
            if snap.timestamp >= cutoff:
                val = getattr(snap, metric, None)
                if val is not None:
                    values.append(val)

        if not values:
            return {"values": [], "avg": 0.0, "min": 0.0, "max": 0.0, "direction": "neutral"}

        avg = sum(values) / len(values)
        direction = "neutral"
        if len(values) >= 2:
            if values[-1] > values[0]:
                direction = "improving"
            elif values[-1] < values[0]:
                direction = "declining"

        return {
            "values": values,
            "avg": round(avg, 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "direction": direction,
            "count": len(values),
        }

    def sparkline(self, metric: str = "overall_success_rate", width: int = 10) -> str:
        """Generate a text sparkline for a metric.

        Uses Unicode block characters for compact display.
        """
        history = self.load_history()
        if len(history) < 2:
            return "─" * width

        values = [getattr(snap, metric, None) for snap in history]
        values = [v for v in values if v is not None]
        if not values:
            return "─" * width

        # Normalize to 0-4 range for block characters
        min_v, max_v = min(values), max(values)
        span = max_v - min_v
        if span == 0:
            normalized = [2] * len(values)
        else:
            normalized = [int(((v - min_v) / span) * 4) for v in values]

        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        return "".join(blocks[min(n, 7)] for n in normalized[-width:])

    # ------------------------------------------------------------------
    # Raw JSON persistence
    # ------------------------------------------------------------------

    def _load_raw(self) -> List[Dict[str, Any]]:
        """Load raw JSON list from metrics file."""
        if not self.metrics_file.exists():
            return []
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("%s: expected list, got %s — starting fresh",
                               self.metrics_file, type(data).__name__)
                return []
            return data
        except json.JSONDecodeError as e:
            logger.warning("%s: corrupted JSON (%s) — starting fresh", self.metrics_file, e)
            return []

    def _save_raw(self, data: List[Dict[str, Any]]) -> None:
        """Atomically save raw JSON list to metrics file."""
        tmp = self.metrics_file.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp.replace(self.metrics_file)
        except Exception as e:
            logger.error("Failed to save metrics to %s: %s", self.metrics_file, e)
            if tmp.exists():
                tmp.unlink()
