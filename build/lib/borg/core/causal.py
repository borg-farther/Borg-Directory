"""
Causal attribution — identifies the tool call that turned a failing session into a success.

Heuristic: in a successful trace, find the last tool call with an error result,
then take the NEXT tool call as the causal intervention. If no error-containing
tool calls exist, take the last tool call as the likely resolution.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional


_ERROR_RESULT_KEYWORDS = (
    'error', 'exception', 'failed', 'traceback', 'errno',
    'refused', 'timeout', 'not found', 'denied', 'invalid',
)


def tag_causal_intervention(trace: Dict[str, Any]) -> Optional[str]:
    """
    Given a trace dict, return a human-readable description of the tool call
    most likely responsible for turning a failure into a success.

    Args:
        trace: A trace dict (from sqlite3.Row or dict()). Expected fields:
            - outcome (str): must be 'success'
            - tool_calls (str or list): JSON string or list of call dicts
            - causal_intervention (str, optional): pre-existing tag

    Returns:
        String like "bash(command='python manage.py migrate --fake')" or None.
    """
    if trace.get('outcome') != 'success':
        return None

    if trace.get('causal_intervention'):
        return trace['causal_intervention']

    tool_calls = trace.get('tool_calls', [])
    if not tool_calls:
        return None

    # Parse JSON string or treat as count
    if isinstance(tool_calls, str):
        try:
            tool_calls = json.loads(tool_calls)
        except Exception:
            # It's a plain integer (count) from old traces — no causal data available
            return None

    if not isinstance(tool_calls, list) or len(tool_calls) < 2:
        return None

    # Find the last tool call whose result contains an error keyword
    last_error_idx = -1
    for i, call in enumerate(tool_calls):
        result_str = str(
            call.get('result', '') or call.get('output', '') or ''
        ).lower()
        if any(kw in result_str for kw in _ERROR_RESULT_KEYWORDS):
            last_error_idx = i

    # The causal intervention is the call immediately after the last error
    if last_error_idx >= 0 and last_error_idx + 1 < len(tool_calls):
        causal = tool_calls[last_error_idx + 1]
    else:
        # No error found — assume last call resolved it
        causal = tool_calls[-1]

    tool_name = str(causal.get('tool') or causal.get('name') or 'unknown')
    args = causal.get('args') or causal.get('arguments') or {}

    if isinstance(args, dict) and args:
        arg_parts = [
            f"{k}={str(v)[:40]}"
            for k, v in list(args.items())[:4]
        ]
        arg_str = ', '.join(arg_parts)
        return f"{tool_name}({arg_str})"
    elif isinstance(args, str) and args:
        return f"{tool_name}({args[:60]})"

    return tool_name
