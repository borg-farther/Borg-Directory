"""
Start-Here Signal Matcher for Borg Brain.

Matches error patterns against pack signals to provide targeted guidance
about where to start debugging and what to avoid.
"""

import re
from typing import Optional, Dict, Any


def match_start_signal(signals: list, error_context: str) -> Optional[Dict[str, Any]]:
    """Match error context against a list of start signals.

    Args:
        signals: List of signal dicts, each containing:
            - error_pattern (str): Regex pattern to match against error context
            - start_here (list of str): Places to focus on
            - avoid (list of str): Places to avoid
            - reasoning (str): Why this guidance applies
        error_context: The error message or context to match against

    Returns:
        First matching signal dict with {start_here, avoid, reasoning}, or None if no match.
    """
    if not signals or not error_context:
        return None

    for signal in signals:
        error_pattern = signal.get("error_pattern", "")
        if not error_pattern:
            continue

        try:
            if re.search(error_pattern, error_context):
                return {
                    "start_here": signal.get("start_here", []),
                    "avoid": signal.get("avoid", []),
                    "reasoning": signal.get("reasoning", ""),
                }
        except re.error:
            # Invalid regex pattern, skip this signal
            continue

    return None
