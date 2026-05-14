"""Shared fail-closed confidence and injection-safety gates for Borg guidance.

This module is intentionally dependency-light because it sits on the hot path
between retrieval and prompt injection.  CLI, MCP, plugins, and public APIs
should call these helpers instead of maintaining local copies.
"""

from __future__ import annotations

import re
from typing import Any

_BORG_GUIDANCE_BLOCK_PATTERN = re.compile(
    r"(?:^|\n)===\s*BORG GUIDANCE\s*===.*?(?=\n===\s*[A-Z][A-Z _-]{3,}\s*===|\Z)",
    re.IGNORECASE | re.DOTALL,
)

_PERMISSION_SIGNAL_PATTERN = re.compile(
    r"permission\s+denied|eacces|operation\s+not\s+permitted|read[- ]only\s+file\s*system|chmod\b|access\s+denied",
    re.IGNORECASE,
)

_DEFAULT_PACK_STOPWORDS = {
    "a", "an", "the", "all", "for", "to", "of", "in", "on", "and", "or",
    "build", "fix", "audit", "make", "create", "update", "task", "error",
}

_DEFAULT_TRACE_STOPWORDS = _DEFAULT_PACK_STOPWORDS | {
    # Borg/meta words are too broad to prove relevance. They caused unrelated
    # Hermes/Borg plugin traces to leak into readiness/dashboard tasks.
    "borg", "trace", "traces", "mcp", "plugin", "runtime", "hermes",
    "guidance", "observe", "observed", "match", "matching", "relevance",
    "readiness", "continue", "first", "user", "users", "gate", "gates",
}


def strip_embedded_borg_guidance(message: str) -> str:
    """Remove pasted/injected Borg guidance before classifying a new task.

    A user may quote a previous `=== BORG GUIDANCE ===` block while asking a
    meta question. The quoted guidance must be inert text, never evidence that
    the new task is a permission problem, merge conflict, migration issue, etc.
    """
    if not message:
        return ""
    return _BORG_GUIDANCE_BLOCK_PATTERN.sub("\n", str(message)).strip()


def permission_guidance_matches_task(task: str, context: str = "") -> bool:
    """Return True only when the cleaned task/context has permission signals."""
    task_clean = strip_embedded_borg_guidance(task or "")
    context_clean = strip_embedded_borg_guidance(context or "")
    return bool(_PERMISSION_SIGNAL_PATTERN.search(f"{task_clean} {context_clean}"))


def guidance_is_safe_to_inject(guidance: str, task: str, context: str = "") -> bool:
    """Fail closed on weak, synthetic, no-match, or irrelevant guidance.

    This is the final safety decision before Borg guidance can be injected into
    an agent prompt. It intentionally suppresses no-match output too: a no-match
    response is useful to display to humans, but should not be injected as
    operational guidance for the next LLM call.
    """
    if not guidance or len(str(guidance)) < 50:
        return False

    task_clean = strip_embedded_borg_guidance(task or "")
    context_clean = strip_embedded_borg_guidance(context or "")
    lowered = str(guidance).lower()

    if "no_confident_match" in lowered or "no confident match" in lowered:
        return False

    has_pack_guidance = "pack guidance" in lowered
    is_permission_pack = "pack guidance (bash-permission-denied)" in lowered

    if is_permission_pack and not permission_guidance_matches_task(task_clean, context_clean):
        return False

    if "real traces: 0" in lowered and has_pack_guidance:
        if is_permission_pack:
            return permission_guidance_matches_task(task_clean, context_clean)
        return False

    if "borg [synthetic only]" in lowered and has_pack_guidance:
        if is_permission_pack:
            return permission_guidance_matches_task(task_clean, context_clean)
        return False

    return True


def no_confident_match_response(tech: str = "") -> str:
    """Honest fail-closed response when Borg has no trustworthy match."""
    tech_display = tech or "this task"
    return (
        f"ACTION: proceed with normal debugging for {tech_display}; Borg has no proven cache hit.\n\n"
        "STOP: do not force a weak or unrelated pack onto this task.\n\n"
        "VERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.\n\n"
        "CONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.\n\n"
        f"NO_CONFIDENT_MATCH: No confident Borg match for {tech_display}.\n"
        "Borg found no relevant real traces, synthetic hits, or exact pack class match.\n"
        "Proceed with normal reasoning; do not treat Borg as evidence for this task.\n"
        "After resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful."
    )


def _terms(text: str, stopwords: set[str]) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9_+-]{3,}", strip_embedded_borg_guidance(text or "").lower())
        if t not in stopwords
    }


def _trace_text(trace: dict[str, Any]) -> str:
    values: list[str] = []
    for key in (
        "causal_intervention", "approach_summary", "root_cause",
        "errors_encountered", "error_patterns", "task", "title",
        "problem", "summary", "files_modified", "key_files",
    ):
        value = trace.get(key)
        if isinstance(value, list):
            values.extend(str(v) for v in value)
        elif value:
            values.append(str(value))
    return " ".join(values)


def trace_match_is_confident(
    trace: dict[str, Any],
    min_similarity: float = 0.45,
    *,
    query: str = "",
    lexical_similarity_floor: float = 0.60,
    min_query_overlap: int = 2,
    stopwords: set[str] | None = None,
) -> bool:
    """Reject explicit low-similarity, content-free, or lexically unrelated trace hits.

    Semantic search can return plausible-looking false positives around common
    Borg/Hermes terms (plugin, runtime, trace, observe). For medium similarity
    hits we require concrete non-meta token overlap with the current task before
    allowing ACTION/WHAT WORKED guidance.
    """
    if not isinstance(trace, dict):
        return False
    similarity = trace.get("similarity")
    if similarity is not None:
        try:
            if float(similarity) < min_similarity:
                return False
        except (TypeError, ValueError):
            return False
    match_score = trace.get("match_score")
    if match_score is not None:
        try:
            if float(match_score) <= 0:
                return False
        except (TypeError, ValueError):
            return False
    has_actionable_content = bool(
        str(trace.get("causal_intervention") or "").strip()
        or str(trace.get("approach_summary") or "").strip()
        or str(trace.get("root_cause") or "").strip()
    )
    if not has_actionable_content:
        return False

    if query and similarity is not None:
        try:
            sim = float(similarity)
        except (TypeError, ValueError):
            return False
        if sim < lexical_similarity_floor:
            active_stopwords = stopwords or _DEFAULT_TRACE_STOPWORDS
            query_terms = _terms(query, active_stopwords)
            trace_terms = _terms(_trace_text(trace), active_stopwords)
            if len(query_terms & trace_terms) < min_query_overlap:
                return False

    return True


def pack_match_is_confident(
    query: str,
    pack: dict[str, Any],
    *,
    stopwords: set[str] | None = None,
    min_overlap: int = 2,
) -> bool:
    """Return True only for exact/lexically strong pack matches."""
    if not isinstance(pack, dict):
        return False
    query_l = strip_embedded_borg_guidance(query or "").lower()
    if not query_l.strip():
        return False

    name = str(pack.get("name") or pack.get("id") or "").lower()
    problem_class = str(pack.get("problem_class") or "").lower()
    tags = " ".join(str(t).lower() for t in (pack.get("tags") or []))
    search_text = str(pack.get("search_text") or pack.get("solution") or "").lower()
    class_text = " ".join([
        name.replace("-", " "),
        problem_class.replace("_", " "),
        tags,
        search_text,
    ])

    permission_pack = (
        "permission" in class_text
        or "eacces" in class_text
        or "operation not permitted" in class_text
        or "chmod" in class_text
    )
    if permission_pack:
        return permission_guidance_matches_task(query_l)

    active_stopwords = stopwords or _DEFAULT_PACK_STOPWORDS
    query_terms = {
        t for t in re.findall(r"[a-z0-9_+-]{3,}", query_l)
        if t not in active_stopwords
    }
    pack_terms = {
        t for t in re.findall(r"[a-z0-9_+-]{3,}", class_text)
        if t not in active_stopwords
    }
    if not query_terms or not pack_terms:
        return False
    return len(query_terms & pack_terms) >= min_overlap
