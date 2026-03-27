"""
Borg Agent Hook — T1.10 integration bridge for agent frameworks.

Provides three entry points for the auto-suggest at pain-point feature:

    borg_on_failure()      — called after consecutive failures;
                               checks for borg pack suggestions.
    borg_on_task_start()   — proactive pack search before work begins.
    borg_format_pack_suggestion() — formats a single pack as a readable string.

Other agents import this module and call these functions at the appropriate
liftoff / frustration points in their own loop.
"""

import json
import logging
from typing import List, Optional

from borg.core.search import (
    check_for_suggestion,
    classify_task,
    borg_search,
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------- -
# Public API
# -------------------------------------------------------------------------- -


def borg_on_failure(
    context: str,
    failure_count: int,
    tried_packs: Optional[List[str]] = None,
) -> Optional[str]:
    """Check for a borg pack suggestion after consecutive failures.

    This is the function an agent framework calls after consecutive failures.
    It wraps ``check_for_suggestion`` from ``borg.core.search`` and,
    when a suggestion is available, formats it into a human-readable message.

    Args:
        context: Recent conversation / error text providing context.
        failure_count: Number of consecutive failed attempts.
        tried_packs: Optional list of pack names already attempted
                     (these will be excluded from suggestions).

    Returns:
        A formatted suggestion string such as:
            "Borg pack available: systematic-debugging (Debugging workflow). "
            "Try: borg_try borg://hermes/systematic-debugging"
        or ``None`` if no suggestion is warranted.
    """
    if not context and failure_count < 2:
        return None

    tried_packs = tried_packs or []

    raw = check_for_suggestion(
        conversation_context=context,
        failure_count=failure_count,
        tried_packs=tried_packs,
    )

    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("check_for_suggestion returned unparseable JSON: %s", raw)
        return None

    if not result.get("has_suggestion"):
        return None

    suggestion_text = result.get("suggestion", "")
    suggestions_list = result.get("suggestions", [])

    if not suggestion_text and suggestions_list:
        # Fall back to formatting from the suggestions list
        first = suggestions_list[0]
        suggestion_text = borg_format_pack_suggestion(
            pack_name=first.get("pack_name", ""),
            confidence=first.get("confidence", ""),
            problem_class=first.get("problem_class", ""),
            why=first.get("why_relevant", ""),
        )

    return suggestion_text if suggestion_text else None


def borg_on_task_start(task_description: str) -> Optional[str]:
    """Proactively search for relevant borg packs before work begins.

    Classifies the incoming task description, searches guild packs,
    and returns a brief recommendation message if matches are found.

    Args:
        task_description: Free-text description of the task to be attempted.

    Returns:
        A string such as:
            "You might find these useful: systematic-debugging "
            "(Debugging workflow; matches your debug task)"
        or ``None`` if no relevant packs are found.
    """
    if not task_description:
        return None

    search_terms = classify_task(task_description)

    if not search_terms:
        return None

    all_matches: List[dict] = []
    for term in search_terms:
        try:
            raw = borg_search(term)
            result = json.loads(raw)
            if result.get("success") and result.get("matches"):
                all_matches.extend(result["matches"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug("borg_search failed for term '%s': %s", term, e)
            continue

    if not all_matches:
        return None

    # Deduplicate by name
    seen: set = set()
    unique: List[dict] = []
    for match in all_matches:
        name = match.get("name", "")
        if name and name not in seen:
            seen.add(name)
            unique.append(match)

    if not unique:
        return None

    # Format top 3 as a readable list
    formatted = []
    for pack in unique[:3]:
        name = pack.get("name", "")
        problem_class = pack.get("problem_class", "")
        confidence = pack.get("confidence", "")
        why = ""
        if search_terms:
            why = f"matches your {search_terms[0]} task"
        if problem_class:
            why = f"{problem_class}" if not why else f"{problem_class}; {why}"
        formatted.append(
            borg_format_pack_suggestion(name, confidence, problem_class, why)
        )

    if not formatted:
        return None

    if len(formatted) == 1:
        return f"You might find this useful: {formatted[0]}"
    else:
        return f"You might find these useful: {'; '.join(formatted)}"


def borg_format_pack_suggestion(
    pack_name: str,
    confidence: str,
    problem_class: str,
    why: str,
) -> str:
    """Format a single borg pack suggestion as a clean, readable string.

    Args:
        pack_name: Name of the pack (used to build the guild:// URI).
        confidence: Provenance confidence level (e.g. "tested", "inferred").
        problem_class: Short description of what the pack solves.
        why: Human-readable explanation of why this pack is relevant.

    Returns:
        A formatted string such as:
            "systematic-debugging (Debugging workflow; matches your debug task)"
        or with confidence badge:
            "systematic-debugging [tested] (Debugging workflow)"
    """
    if not pack_name:
        return ""

    uri = f"borg://hermes/{pack_name}"

    parts = [pack_name]

    # Add confidence badge if known
    if confidence and confidence not in ("unknown", ""):
        parts.append(f"[{confidence}]")

    # Add problem class or phase description
    if problem_class:
        parts.append(f"({problem_class})")

    # Append why it's relevant
    if why:
        parts.append(f"; {why}")

    result = " ".join(parts)

    # If it looks short, append the try command
    if len(parts) <= 2:
        result = f"{result} — try: {uri}"

    return result
