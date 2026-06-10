"""Canonical thin shim for the deployed Hermes ``borg_search_assist`` plugin.

Deploy this file to ``~/.hermes/plugins/borg_search_assist/__init__.py`` after
backing up the active copy. Runtime logic lives in
``borg.integrations.borg_search_assist``.
"""

from borg.integrations.borg_search_assist import (  # noqa: F401
    _detect,
    _ensure_borg_importable,
    _on_post_tool_call,
    _on_pre_llm_call,
    detect_error_class,
    find_local_traces,
    on_post_tool_call,
    on_pre_llm_call,
    register,
)

__all__ = [
    "_detect",
    "_ensure_borg_importable",
    "_on_post_tool_call",
    "_on_pre_llm_call",
    "detect_error_class",
    "find_local_traces",
    "on_post_tool_call",
    "on_pre_llm_call",
    "register",
]
