#!/usr/bin/env python3
"""
Borg Dojo Cron Runner — entry point for hermes cron.

Intended to be called by hermes cron (or any system scheduler) to run the
full dojo pipeline overnight and deliver the report.

Usage (direct):
    python -m borg.dojo.cron_runner --days 7 --format telegram --deliver-to telegram

Environment variables:
    BORG_DOJO_ENABLED   Must be "true" to activate (default: false)
    HERMES_HOME         Override hermes home directory (default: ~/.hermes)
    BORG_DOJO_DAYS      Default days to analyze (default: 7)
    BORG_DOJO_FORMAT    Default report format: telegram, discord, or cli (default: telegram)
    BORG_DOJO_AUTO_FIX  Whether to auto-fix top weaknesses (default: true)

Exit codes:
    0  — Success (report generated)
    1  — Pipeline disabled (BORG_DOJO_ENABLED != true)
    2  — Database not found
    3  — Report generation failed
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Ensure borg package is importable
_BORG_ROOT = Path(__file__).parent.parent.parent
if str(_BORG_ROOT) not in sys.path:
    sys.path.insert(0, str(_BORG_ROOT))


def _configure_logging(verbose: bool = False) -> None:
    """Configure logging for cron run."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_pipeline(
    days: int = 7,
    report_format: str = "telegram",
    auto_fix: bool = True,
    deliver_to: str | None = None,
) -> tuple[bool, str]:
    """
    Run the full dojo pipeline and return (success, report_text).

    Returns (False, error_message) on failure.
    """
    from borg.dojo.pipeline import DojoPipeline, BORG_DOJO_ENABLED

    if not BORG_DOJO_ENABLED:
        return False, "Dojo pipeline is disabled (set BORG_DOJO_ENABLED=true to activate)."

    logger = logging.getLogger("cron_runner")
    start = time.time()

    try:
        pipeline = DojoPipeline()
        logger.info("Starting dojo pipeline: days=%d, format=%s, auto_fix=%s", days, report_format, auto_fix)

        report = pipeline.run(
            days=days,
            auto_fix=auto_fix,
            report_fmt=report_format,
            deliver_to=deliver_to,
        )

        elapsed = time.time() - start
        logger.info("Pipeline completed in %.1fs", elapsed)
        logger.debug("Report:\n%s", report)

        return True, report

    except FileNotFoundError as e:
        logger.error("Database not found: %s", e)
        return False, f"Database not found: {e}"
    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        return False, f"Pipeline error: {e}"


def deliver_report(report: str, deliver_to: str | None) -> bool:
    """
    Deliver report to the specified target.

    Currently supports:
      - "telegram" — prints to stdout (hermes cron handles delivery)
      - "discord"  — prints to stdout with discord-friendly formatting
      - "cli"      — prints to stdout
      - None       — prints to stdout

    Returns True if delivery was successful.
    """
    if deliver_to is None:
        print(report)
        return True

    logger = logging.getLogger("cron_runner")

    if deliver_to == "telegram":
        # hermes cron reads stdout and delivers to telegram
        print(report)
        logger.info("Report delivered to telegram (stdout)")
        return True

    elif deliver_to == "discord":
        # Wrap in code block for discord
        print(f"```\n{report}\n```")
        logger.info("Report delivered to discord (stdout, code block)")
        return True

    elif deliver_to == "cli":
        print(report)
        logger.info("Report delivered to cli (stdout)")
        return True

    else:
        logger.warning("Unknown delivery target '%s', falling back to stdout", deliver_to)
        print(report)
        return True


def main() -> int:
    """CLI entry point. Returns exit code (0=success, 1=disabled, 2=not found, 3=error)."""
    parser = argparse.ArgumentParser(
        prog="python -m borg.dojo.cron_runner",
        description="Run the Borg Dojo pipeline and deliver the report.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("BORG_DOJO_DAYS", "7")),
        help="Number of days to analyze (default: 7)",
    )
    parser.add_argument(
        "--format",
        dest="report_format",
        type=str,
        default=os.getenv("BORG_DOJO_FORMAT", "telegram"),
        choices=["telegram", "discord", "cli"],
        help="Report format (default: telegram)",
    )
    parser.add_argument(
        "--auto-fix",
        type=lambda x: x.lower() in ("true", "1", "yes"),
        default=os.getenv("BORG_DOJO_AUTO_FIX", "true").lower() in ("true", "1", "yes"),
        help="Whether to auto-fix top 3 weaknesses (default: true)",
    )
    parser.add_argument(
        "--deliver-to",
        type=str,
        default=None,
        choices=["telegram", "discord", "cli"],
        help="Delivery target (hermes cron handles actual delivery after reading stdout)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()
    _configure_logging(args.verbose)
    logger = logging.getLogger("cron_runner")

    # Check feature flag
    from borg.dojo.pipeline import BORG_DOJO_ENABLED
    if not BORG_DOJO_ENABLED:
        logger.error("BORG_DOJO_ENABLED is not set to 'true'")
        print("ERROR: Dojo pipeline is disabled (set BORG_DOJO_ENABLED=true to activate).", file=sys.stderr)
        return 1

    # Run the pipeline
    success, result = run_pipeline(
        days=args.days,
        report_format=args.report_format,
        auto_fix=args.auto_fix,
        deliver_to=args.deliver_to,
    )

    if not success:
        print(f"ERROR: {result}", file=sys.stderr)
        if "not found" in result.lower():
            return 2
        return 3

    # Deliver
    deliver_report(result, args.deliver_to)
    logger.info("Cron run completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
