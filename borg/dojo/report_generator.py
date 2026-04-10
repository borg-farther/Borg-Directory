"""
Borg Dojo — Report Generator.

Generates formatted improvement reports in CLI, Telegram, and Discord formats.

Public API:
  generate_report(
      analysis: SessionAnalysis,
      fixes: List[FixAction] = None,
      history: List[MetricSnapshot] = None,
      fmt: str = "cli",
  ) -> str
"""

import logging
from typing import Any, Dict, List, Optional

from .learning_curve import MetricSnapshot

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Report Generator
# -----------------------------------------------------------------------

class ReportGenerator:
    """Generates formatted reports for CLI, Telegram, and Discord."""

    def generate(
        self,
        analysis,
        fixes: Optional[List] = None,
        history: Optional[List[MetricSnapshot]] = None,
        fmt: str = "cli",
    ) -> str:
        """Generate a formatted improvement report.

        Args:
            analysis: SessionAnalysis object with all analysis results.
            fixes: List of FixAction objects from this cycle.
            history: List of MetricSnapshot for trend data.
            fmt: Output format — "cli", "telegram", or "discord".

        Returns:
            Formatted report string.
        """
        fixes = fixes or []
        history = history or []

        if fmt == "telegram":
            return self._telegram_report(analysis, fixes, history)
        elif fmt == "discord":
            return self._discord_report(analysis, fixes, history)
        else:
            return self._cli_report(analysis, fixes, history)

    # ------------------------------------------------------------------
    # CLI format
    # ------------------------------------------------------------------

    def _cli_report(self, analysis, fixes: List, history: List[MetricSnapshot]) -> str:
        lines = [
            "",
            "=" * 60,
            "  DOJO SESSION ANALYSIS REPORT",
            "=" * 60,
            f"  Analyzed: {analysis.sessions_analyzed} sessions "
            f"({analysis.days_covered} days)",
            f"  Success rate: {analysis.overall_success_rate:.1f}%  "
            f"  Errors: {analysis.total_errors}  "
            f"  Corrections: {analysis.user_corrections}",
            "",
        ]

        if analysis.weakest_tools:
            lines.append("  --- TOP TOOL FAILURES ---")
            for i, tool in enumerate(analysis.weakest_tools[:5], 1):
                lines.append(
                    f"  {i}. {tool.tool_name}: {tool.failed_calls} failures, "
                    f"{tool.success_rate * 100:.0f}% success, "
                    f"top error: {tool.top_error_category}"
                )
            lines.append("")

        if analysis.skill_gaps:
            lines.append("  --- SKILL GAPS ---")
            for gap in analysis.skill_gaps[:5]:
                lines.append(
                    f"  - {gap.capability}: requested {gap.request_count}x "
                    f"(confidence: {gap.confidence:.0%})"
                )
            lines.append("")

        if fixes:
            lines.append("  --- FIXES APPLIED ---")
            for fix in fixes:
                status = "OK" if fix.success else "FAIL"
                lines.append(
                    f"  [{status}] {fix.action} → {fix.target_skill} "
                    f"(priority: {fix.priority:.1f})"
                )
            lines.append("")

        if history:
            trend = self._get_trend_data(history, "overall_success_rate")
            if trend["values"]:
                lines.append(f"  --- TREND ({trend['direction']}) ---")
                lines.append(
                    f"  Success rate: avg={trend['avg']:.1f}%, "
                    f"range=[{trend['min']:.1f}%, {trend['max']:.1f}%]"
                )
                spark = self._sparkline_from_values(
                    trend["values"][-10:] if len(trend["values"]) > 10 else trend["values"]
                )
                lines.append(f"  Sparkline: {spark}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Telegram format (compact, emoji-heavy)
    # ------------------------------------------------------------------

    def _telegram_report(
        self, analysis, fixes: List, history: List[MetricSnapshot]
    ) -> str:
        blocks: List[str] = []

        # Header
        blocks.append("🧠 *Dojo Analysis*")
        blocks.append(
            f"_{analysis.sessions_analyzed} sessions / "
            f"{analysis.days_covered} days_"
        )

        # Key metrics row
        success_emoji = "✅" if analysis.overall_success_rate >= 80 else "⚠️"
        blocks.append(
            f"{success_emoji} Success: `{analysis.overall_success_rate:.1f}%`  "
            f"❌ Errors: `{analysis.total_errors}`  "
            f"🔄 Corrections: `{analysis.user_corrections}`"
        )
        blocks.append("")

        # Weakest tools
        if analysis.weakest_tools:
            blocks.append("📉 *Top Failures*")
            for tool in analysis.weakest_tools[:3]:
                blocks.append(
                    f"  • `{tool.tool_name}`: {tool.failed_calls} fails, "
                    f"{tool.success_rate * 100:.0f}% ok"
                )
            blocks.append("")

        # Skill gaps
        if analysis.skill_gaps:
            blocks.append("🔍 *Skill Gaps*")
            for gap in analysis.skill_gaps[:3]:
                blocks.append(
                    f"  • {gap.capability}: {gap.request_count}x requested"
                )
            blocks.append("")

        # Fixes applied
        if fixes:
            ok_fixes = [f for f in fixes if f.success]
            fail_fixes = [f for f in fixes if not f.success]
            if ok_fixes:
                blocks.append(f"🔧 *Fixes applied:* {len(ok_fixes)}")
                for fix in ok_fixes[:3]:
                    blocks.append(f"  ✅ {fix.action} → `{fix.target_skill}`")
            if fail_fixes:
                blocks.append(f"⚠️ *Fixes failed:* {len(fail_fixes)}")
                for fix in fail_fixes[:3]:
                    blocks.append(f"  ❌ {fix.action} → `{fix.target_skill}`")
            blocks.append("")

        # Trend
        if history and len(history) >= 2:
            trend = self._get_trend_data(history, "overall_success_rate")
            direction_emoji = {
                "improving": "📈",
                "declining": "📉",
                "neutral": "➡️",
            }.get(trend["direction"], "➡️")
            blocks.append(
                f"{direction_emoji} *Trend:* {trend['direction']} "
                f"(avg {trend['avg']:.1f}%)"
            )
            spark = self._sparkline_from_values(
                trend["values"][-10:] if len(trend["values"]) > 10 else trend["values"]
            )
            blocks.append(f"`{spark}`")

        return "\n".join(blocks)

    # ------------------------------------------------------------------
    # Discord format (embed-style)
    # ------------------------------------------------------------------

    def _discord_report(
        self, analysis, fixes: List, history: List[MetricSnapshot]
    ) -> str:
        lines: List[str] = []

        # Header
        lines.append("**🧠 Dojo Session Analysis**")
        lines.append(f"*{analysis.sessions_analyzed} sessions / {analysis.days_covered} days*")
        lines.append("")

        # Key stats
        lines.append(f"**Success Rate:** `{analysis.overall_success_rate:.1f}%`")
        lines.append(f"**Total Errors:** `{analysis.total_errors}`")
        lines.append(f"**User Corrections:** `{analysis.user_corrections}`")
        lines.append("")

        # Weakest tools
        if analysis.weakest_tools:
            lines.append("**📉 Top Tool Failures**")
            for tool in analysis.weakest_tools[:3]:
                lines.append(
                    f"> `{tool.tool_name}` — {tool.failed_calls} fails, "
                    f"{tool.success_rate * 100:.0f}% success, "
                    f"top error: `{tool.top_error_category}`"
                )
            lines.append("")

        # Skill gaps
        if analysis.skill_gaps:
            lines.append("**🔍 Detected Skill Gaps**")
            for gap in analysis.skill_gaps[:3]:
                lines.append(
                    f"> {gap.capability} requested {gap.request_count}x "
                    f"(confidence: {gap.confidence:.0%})"
                )
            lines.append("")

        # Fixes
        if fixes:
            ok_fixes = [f for f in fixes if f.success]
            fail_fixes = [f for f in fixes if not f.success]
            if ok_fixes:
                lines.append(f"**🔧 Fixes Applied ({len(ok_fixes)})**")
                for fix in ok_fixes[:3]:
                    lines.append(f"> ✅ {fix.action} → `{fix.target_skill}`")
            if fail_fixes:
                lines.append(f"**⚠️ Fixes Failed ({len(fail_fixes)})**")
                for fix in fail_fixes[:3]:
                    lines.append(f"> ❌ {fix.action} → `{fix.target_skill}`")
            lines.append("")

        # Trend
        if history and len(history) >= 2:
            trend = self._get_trend_data(history, "overall_success_rate")
            lines.append(
                f"**Trend:** {trend['direction']} "
                f"(avg {trend['avg']:.1f}%, "
                f"range {trend['min']:.1f}%–{trend['max']:.1f}%)"
            )
            spark = self._sparkline_from_values(
                trend["values"][-10:] if len(trend["values"]) > 10 else trend["values"]
            )
            lines.append(f"`{spark}`")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_trend_data(
        self, history: List[MetricSnapshot], metric: str
    ) -> Dict[str, Any]:
        """Compute simple trend data from a history list."""
        values = [getattr(snap, metric, None) for snap in history if hasattr(snap, metric)]
        values = [v for v in values if v is not None]
        if not values:
            return {"values": [], "avg": 0.0, "min": 0.0, "max": 0.0, "direction": "neutral"}

        direction = "neutral"
        if len(values) >= 2:
            if values[-1] > values[0]:
                direction = "improving"
            elif values[-1] < values[0]:
                direction = "declining"

        return {
            "values": values,
            "avg": round(sum(values) / len(values), 2),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "direction": direction,
        }

    def _sparkline_from_values(self, values: List[float], width: int = 10) -> str:
        """Generate a sparkline from a list of numeric values."""
        if not values:
            return "─" * width
        if len(values) < 2:
            return "─" * width

        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        min_v, max_v = min(values), max(values)
        span = max_v - min_v
        if span == 0:
            normalized = [2] * len(values)
        else:
            normalized = [int(((v - min_v) / span) * 4) for v in values]

        return "".join(blocks[min(n, 7)] for n in normalized[-width:])
