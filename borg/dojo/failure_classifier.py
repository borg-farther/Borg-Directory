"""
Borg Dojo — Failure Classifier.

Classifies tool call results into error categories. Designed to address
false positives from the adversarial review:

  - ONLY match error patterns in role='tool' messages (never assistant)
  - Return confidence scores with each classification
  - The 'could not' false positive: phrase "I could not find..." should NOT
    trigger path_not_found when it appears in assistant text; only tool results
    with explicit error structures should be classified.

Public API:
  classify_tool_result(content: str, role: str = "tool") -> Tuple[bool, str, float]
  detect_corrections(messages: List[Tuple[str, float]]) -> List[CorrectionSignal]
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from borg.dojo.data_models import CorrectionSignal, FailureReport


# =============================================================================
# Error category definitions
# =============================================================================

# Each error category carries:
#   - patterns: list of regexes (prepended with (?i) for case-insensitive)
#   - role_filter: must be "tool" — this is the core false-positive mitigation
#   - min_confidence: minimum confidence to accept this category
#   - context_boosts: multipliers when certain keywords co-occur

_RAW_CATEGORIES = {
    "path_not_found": {
        "patterns": [
            r"no such file",
            r"ENOENT",
            r"FileNotFoundError",
            r"not found",
            r"directory does not exist",
            r"does not exist",
        ],
        "role_filter": "tool",
        "min_confidence": 0.9,
        "context_boosts": {"file": 0.05, "path": 0.05, "directory": 0.05},
    },
    "timeout": {
        "patterns": [
            r"ETIMEDOUT",
            r"timed?\s*out",
            r"deadline exceeded",
            r"timeout",
            r"request timeout",
        ],
        "role_filter": "tool",
        "min_confidence": 0.85,
        "context_boosts": {"connect": 0.05, "network": 0.05},
    },
    "permission_denied": {
        "patterns": [
            r"EACCES",
            r"permission denied",
            r"403 forbidden",
            r"access denied",
            r"not permitted",
        ],
        "role_filter": "tool",
        "min_confidence": 0.9,
        "context_boosts": {"chmod": 0.05, "sudo": 0.05},
    },
    "command_not_found": {
        "patterns": [
            r"command not found",
            r"not recognized",
            r"'[\\w.-]+' (is not recognized|not found)",
            r"shell: command not found",
        ],
        "role_filter": "tool",
        "min_confidence": 0.95,
        "context_boosts": {},
    },
    "rate_limit": {
        "patterns": [
            r"429",
            r"rate limit",
            r"too many requests",
            r"quota exceeded",
            r"retry-after",
        ],
        "role_filter": "tool",
        "min_confidence": 0.9,
        "context_boosts": {"retry": 0.05},
    },
    "syntax_error": {
        "patterns": [
            r"SyntaxError",
            r"IndentationError",
            r"unexpected token",
            r"parse error",
            r"invalid syntax",
        ],
        "role_filter": "tool",
        "min_confidence": 0.95,
        "context_boosts": {},
    },
    "network": {
        "patterns": [
            r"connection refused",
            r"ECONNREFUSED",
            r"network unreachable",
            r"dns failure",
            r"no route to host",
            r"socket error",
        ],
        "role_filter": "tool",
        "min_confidence": 0.85,
        "context_boosts": {},
    },
    "generic": {
        "patterns": [
            r"error",
            r"failed",
            r"failure",
            r"exception",
        ],
        "role_filter": "tool",
        "min_confidence": 0.5,
        "context_boosts": {},
    },
}


# Pre-compile all patterns at module load for performance
@dataclass(frozen=True)
class ErrorCategory:
    """Frozen definition for one error category."""

    name: str
    compiled_patterns: List[Tuple[re.Pattern, str]]  # (compiled_regex, original_pattern_str)
    role_filter: str
    min_confidence: float
    context_boosts: Dict[str, float]


ERROR_CATEGORIES: Dict[str, ErrorCategory] = {
    name: ErrorCategory(
        name=name,
        compiled_patterns=[(re.compile(p, re.IGNORECASE), p) for p in cfg["patterns"]],
        role_filter=cfg["role_filter"],
        min_confidence=cfg["min_confidence"],
        context_boosts=cfg["context_boosts"],
    )
    for name, cfg in _RAW_CATEGORIES.items()
}


# =============================================================================
# Correction patterns applied ONLY to role='user' messages
# =============================================================================

_CORRECTION_RAW = [
    # High confidence (explicit correction)
    (r"^no[,.\s]", 0.9),
    (r"wrong\s+(file|path|dir|command)", 0.95),
    (r"I meant", 0.9),
    (r"that's not (right|correct|what)", 0.9),
    (r"not right", 0.85),
    # Medium confidence (possible correction)
    (r"try again", 0.7),
    (r"doesn't work", 0.7),
    (r"not working", 0.7),
    (r"didn't work", 0.7),
    # Low confidence (may be unrelated)
    (r"^stop\b", 0.5),
    (r"\bundo\b", 0.6),
    (r"^wait\b", 0.5),
]

CORRECTION_PATTERNS: List[Tuple[re.Pattern, str, float]] = [
    (re.compile(p, re.IGNORECASE), p, conf) for p, conf in _CORRECTION_RAW
]


# =============================================================================
# False-positive mitigation helpers
# =============================================================================

# Phrases that appear frequently in assistant text but should NOT be treated
# as error signals. These are stripped or downgraded before classification.
# IMPORTANT: replacement text must NOT contain "error" to avoid triggering
# the generic error detector after stripping.
_FALSE_POSITIVE_PHRASES = [
    (re.compile(r"I could not", re.IGNORECASE), "[COULD_NOT_ASSISTANT]"),
    (re.compile(r"could not (find|be)", re.IGNORECASE), "[COULD_NOT_ASSISTANT]"),
    (re.compile(r"no errors? found", re.IGNORECASE), "[NO_ERRORS_SUCCESS]"),
    (re.compile(r"without error", re.IGNORECASE), "[CLEAN_SUCCESS]"),
    (re.compile(r"error[- ]free", re.IGNORECASE), "[CLEAN_SUCCESS]"),
]

# Regex to detect explicit JSON error structure from tool results
_ERROR_STRUCTURE_RE = re.compile(
    r'\{\s*"error"\s*:\s*"[^"]+"', re.IGNORECASE
)


def _is_structured_error(content: str) -> bool:
    """Return True if content has an explicit error JSON structure.

    Matches {"error": "message"} but NOT {"errors": []} or {"error": null}.
    """
    return bool(_ERROR_STRUCTURE_RE.search(content))


def _is_error_list(content: str) -> bool:
    """Return True if content has an 'errors': [] pattern (empty error list)."""
    return bool(re.search(r'"errors"\s*:\s*\[\s*\]', content))


def _strip_false_positives(text: str) -> str:
    """Remove or mask phrases that cause false positives.

    Replacement text uses brackets so it can't accidentally match error patterns.
    """
    result = text
    for fp_re, replacement in _FALSE_POSITIVE_PHRASES:
        result = fp_re.sub(replacement, result)
    return result


# =============================================================================
# Public API
# =============================================================================


def classify_tool_result(
    content: str,
    role: str = "tool",
    tool_name: str = "unknown",
    session_id: str = "unknown",
    timestamp: float = 0.0,
) -> Tuple[bool, str, float]:
    """Classify a tool result as success or failure.

    This function ONLY matches error patterns in role='tool' messages.
    Assistant and user messages are passed through as (False, '', 0.0)
    to prevent false positives from reasoning traces.

    Args:
        content: The tool result text (PII-redacted by caller).
        role: Message role — only 'tool' produces classifications.
        tool_name: Name of the tool (for FailureReport).
        session_id: Session ID (for FailureReport).
        timestamp: Unix timestamp (for FailureReport).

    Returns:
        Tuple of (is_error, error_category, confidence).
        If role != 'tool', returns (False, '', 0.0).
    """

    # ============================================================
    # CORE DESIGN: Only classify tool role messages
    # ============================================================
    if role != "tool":
        return (False, "", 0.0)

    if not content or not content.strip():
        return (False, "", 0.0)

    # Fast path: reject obvious non-errors before any regex work
    # Empty error list: {"success": true, "errors": []} — NOT an error
    if _is_error_list(content):
        return (False, "", 0.0)

    # Strip phrases that cause false positives
    cleaned = _strip_false_positives(content)

    best_category: str = "generic"
    best_confidence: float = 0.0
    best_pattern_str: str = ""

    for cat_name, cat in ERROR_CATEGORIES.items():
        if cat_name == "generic":
            continue  # generic is fallback, evaluate last

        for compiled_re, pattern_str in cat.compiled_patterns:
            match = compiled_re.search(cleaned)
            if not match:
                continue

            # Base confidence from category definition
            confidence = cat.min_confidence

            # Context boost — check surrounding words
            context_window = cleaned[max(0, match.start() - 30): match.end() + 30].lower()
            for boost_keyword, boost_amount in cat.context_boosts.items():
                if boost_keyword in context_window:
                    confidence += boost_amount

            # Clamp to [min_confidence, 1.0]
            confidence = min(1.0, confidence)

            if confidence > best_confidence:
                best_confidence = confidence
                best_category = cat_name
                best_pattern_str = pattern_str

    # If no specific category matched, check generic as fallback
    if best_confidence == 0.0:
        # Check if there's any error-like signal at all
        generic_cat = ERROR_CATEGORIES["generic"]
        for compiled_re, pattern_str in generic_cat.compiled_patterns:
            if compiled_re.search(cleaned):
                best_confidence = generic_cat.min_confidence
                best_category = "generic"
                best_pattern_str = pattern_str
                break

    is_error = best_confidence >= 0.5

    return (is_error, best_category, best_confidence)


def classify_tool_result_to_report(
    content: str,
    role: str = "tool",
    tool_name: str = "unknown",
    session_id: str = "unknown",
    timestamp: float = 0.0,
) -> FailureReport | None:
    """Classify and return a FailureReport, or None if no error detected."""

    is_error, error_category, confidence = classify_tool_result(
        content, role, tool_name, session_id, timestamp
    )

    if not is_error:
        return None

    snippet = content[:200] if content else ""

    return FailureReport(
        tool_name=tool_name,
        error_category=error_category,
        error_snippet=snippet,
        session_id=session_id,
        timestamp=timestamp,
        confidence=confidence,
    )


def detect_corrections(
    messages: List[Tuple[str, float]]
) -> List[CorrectionSignal]:
    """Detect user correction signals in a list of user messages.

    Correction patterns are ONLY applied to role='user' messages.
    The caller is responsible for filtering messages by role before
    passing them here.

    Args:
        messages: List of (content, timestamp) tuples for user messages.

    Returns:
        List of CorrectionSignal, one per detected correction.
    """

    signals: List[CorrectionSignal] = []

    for content, ts in messages:
        if not content:
            continue

        for compiled_re, pattern_str, base_confidence in CORRECTION_PATTERNS:
            match = compiled_re.search(content)
            if not match:
                continue

            # Apply the confidence directly (patterns are mutually exclusive
            # in practice; we take the first/strongest match per message)
            snippet = content[:200]

            signals.append(
                CorrectionSignal(
                    pattern=pattern_str,
                    confidence=base_confidence,
                    timestamp=ts,
                    snippet=snippet,
                )
            )
            break  # Only one correction per message in canonical form

    return signals
