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
        __version__ = "3.3.11"  # fallback only when package metadata is unavailable


def check(context: str, constraints: dict | None = None, top_k: int = 3) -> list[dict[str, Any]]:
    """Return relevant Borg memories/packs for ``context``.

    Args:
        context: Error text, task description, or debugging context.
        constraints: Optional hints. Supported keys today:
            ``mode`` (``text``/``semantic``/``hybrid``), ``agent_id``.
        top_k: Maximum number of results to return.

    Returns:
        A list of result dictionaries from ``borg.core.search.borg_search``.
        Empty means no confident match or search unavailable; it no longer means
        "API not implemented".
    """
    if not context or not str(context).strip():
        return []
    hints = constraints or {}
    mode = str(hints.get("mode", "hybrid"))
    agent_id = hints.get("agent_id")
    try:
        from borg.core.search import borg_search

        raw = borg_search(str(context), mode=mode, requesting_agent_id=agent_id)
        payload = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(payload, dict) or not payload.get("success"):
            return []
        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            return []
        return [m for m in matches[: max(0, int(top_k))] if isinstance(m, dict)]
    except Exception:
        return []
