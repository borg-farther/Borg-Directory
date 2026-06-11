"""Borg — failure memory for AI coding agents.

The top-level :func:`check` helper is intentionally tiny, but it must be real:
it is the first API many agents try after ``import borg``.  Returning an empty
placeholder silently destroys first-user value, so this wrapper delegates to the
same search path used by the CLI/MCP server and fails closed with an empty list
only when the search layer itself is unavailable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

def _version_from_source_pyproject() -> str | None:
    """Return the source-tree version when running from a checkout."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    if 'name = "agent-borg"' not in text:
        return None
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return match.group(1) if match else None

_source_version = _version_from_source_pyproject()
if _source_version:
    __version__ = _source_version
else:
    try:
        from importlib.metadata import PackageNotFoundError, version as _pkg_version

        __version__ = _pkg_version("agent-borg")
    except (ImportError, PackageNotFoundError):
        __version__ = "3.3.20"  # fallback only when package metadata is unavailable


def check(context: str, constraints: dict | None = None, top_k: int = 3) -> list[dict[str, Any]]:
    """Return relevant Borg memories/packs for ``context``.

    Args:
        context: Error text, task description, or debugging context.
        constraints: Optional hints. Supported keys today:
            ``mode`` (``text``/``semantic``/``hybrid``), ``agent_id``.
        top_k: Maximum number of results to return.

    Returns:
        A list of result dictionaries from ``borg.core.search.borg_search``,
        filtered to confident (lexically-grounded) matches only via the same
        gate the CLI/MCP rescue path uses. An empty list means no confident
        match or search unavailable -- it is never a confident-but-irrelevant
        hit, and it no longer means "API not implemented".

        For a structured rescue packet (ACTION/STOP/VERIFY, confidence, and an
        explicit NO_CONFIDENT_MATCH signal) prefer the ``borg_rescue`` MCP tool
        or ``borg.core.rescue.rescue(...)``; ``check`` is a confidence-gated
        pack lookup, not the full rescue engine.
    """
    if not context or not str(context).strip():
        return []
    hints = constraints or {}
    mode = str(hints.get("mode", "hybrid"))
    agent_id = hints.get("agent_id")
    try:
        from borg.core.confidence_gate import pack_match_is_confident
        from borg.core.search import borg_search

        raw = borg_search(str(context), mode=mode, requesting_agent_id=agent_id)
        payload = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(payload, dict) or not payload.get("success"):
            return []
        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            return []
        # Gate out confident-but-irrelevant hits: borg_search ranks packs by
        # weak lexical/semantic similarity and will surface unrelated seed packs
        # for verbatim stderr (e.g. a ModuleNotFoundError returning Django/Docker
        # packs). Require the same lexical grounding the rescue path requires so
        # the documented Python API never returns a confident wrong answer.
        confident = [
            m
            for m in matches
            if isinstance(m, dict) and pack_match_is_confident(str(context), m)
        ]
        return confident[: max(0, int(top_k))]
    except Exception:
        return []
