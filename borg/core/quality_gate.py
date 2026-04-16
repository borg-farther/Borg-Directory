"""Session-quality gate for save_trace (competitive review item #6).

Prevents hollow traces from entering the DB. Based on Icarus-Daedalus
quality scoring: traces must have meaningful root_cause, approach, and
outcome to be saved. Without this, 65% of auto-captured traces are
empty shells that pollute retrieval.

Returns (should_save: bool, reason: str, score: int).
"""


def check_trace_quality(trace: dict) -> tuple:
    """Score a trace 0-7. Minimum 3 to save. Returns (pass, reason, score)."""
    score = 0
    reasons = []

    # Hard gate: root_cause must exist and be meaningful (>= 20 chars)
    root_cause = trace.get('root_cause', '') or ''
    if len(root_cause.strip()) < 20:
        return (False, 'root_cause too short or empty (hard gate)', 0)

    score += 2
    reasons.append('root_cause present')

    # approach_summary adds value
    approach = trace.get('approach_summary', '') or ''
    if len(approach.strip()) >= 10:
        score += 2
        reasons.append('approach present')

    # outcome recorded
    outcome = trace.get('outcome', '') or ''
    if outcome in ('success', 'failure', 'partial'):
        score += 1
        reasons.append(f'outcome={outcome}')

    # tool_calls indicates real work happened
    tool_calls = trace.get('tool_calls', 0)
    if isinstance(tool_calls, str):
        try:
            tool_calls = int(tool_calls)
        except (ValueError, TypeError):
            tool_calls = 0
    if tool_calls >= 3:
        score += 1
        reasons.append(f'{tool_calls} tool calls')

    # technology tagged
    tech = trace.get('technology', '') or ''
    if len(tech.strip()) >= 2:
        score += 1
        reasons.append(f'tech={tech}')

    threshold = 3
    passed = score >= threshold
    reason = f"score={score}/{threshold}: {', '.join(reasons)}"
    if not passed:
        reason = f"REJECTED {reason}"

    return (passed, reason, score)
