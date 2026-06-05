"""Repo-owned Hermes plugin logic for ``borg_search_assist``.

The deployed Hermes plugin at ``~/.hermes/plugins/borg_search_assist`` should be
only a thin shim importing this module. Keep matcher logic here so behavior is
versioned, testable, and safe to reload on the next operator gateway restart.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

LOG_PATH = Path(os.environ.get("BORG_RECIPE_LOG", str(Path.home() / ".borg" / "hermes_recipe.log")))
STATE_PATH = Path(os.environ.get("BORG_RECIPE_STATE", "/tmp/borg_hermes_state.json"))

# Populated lazily so importing this module does not require the federation SDK.
Client: Any | None = None

# Existing Hermes plugin classes. These keep the old token-only behavior so
# TypeScript/Docker/Node matches do not regress while conversational matching is
# added behind a stricter dual-condition gate below.
EXISTING_ERROR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"TS\d{3,5}\b|typescript|\.tsx?\b", re.I), "typescript-error"),
    (re.compile(r"\bdocker\b|dockerfile|container", re.I), "docker-error"),
    (re.compile(r"\bnode(?:js)?\b|npm\b|ENOENT|EADDRINUSE", re.I), "nodejs-error"),
)

ERROR_REPORT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfails?\s+with\b", re.I),
    re.compile(r"\bfailed\s+with\b", re.I),
    re.compile(r"\bgetting\b.+\bwhen\s+(?:i\s+)?run\b", re.I | re.S),
    re.compile(r"\bthrows?\b|\bthrowing\b", re.I),
    re.compile(r"^\s*Traceback \(most recent call last\):", re.I | re.M),
    re.compile(r"\btraceback\b", re.I),
)

TECHNICAL_TOKEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:psycopg2|pg_config|libpq|postgres(?:ql)?-dev|python\d*(?:\.\d+)?-dev)\b",
            re.I,
        ),
        "python-package-build-error",
    ),
    (
        re.compile(r"\b(?:ModuleNotFoundError|ImportError|No module named)\b", re.I),
        "python-import-error",
    ),
    (
        re.compile(r"\b(?:pytest|AssertionError|python|\.py)\b|^\s*Traceback ", re.I | re.M),
        "python-error",
    ),
    (
        re.compile(r"\b(?:cargo|rustc)\b|\berror\[E\d{3,5}\]", re.I),
        "rust-error",
    ),
)

LOCAL_TECHNOLOGY_BY_CLASS = {
    "docker-error": "docker",
    "nodejs-error": "nodejs",
    "python-error": "python",
    "python-import-error": "python",
    "python-package-build-error": "python",
    "rust-error": "rust",
    "typescript-error": "typescript",
}


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")


def _ensure_borg_importable() -> bool:
    """Make the Borg Collective SDK importable from Hermes or Borg venvs."""
    try:
        import borg_collective  # noqa: F401
        return True
    except ImportError:
        pass

    py_xy = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate = Path.home() / ".borg" / "venv" / "lib" / py_xy / "site-packages"
    if candidate.is_dir():
        sys.path.insert(0, str(candidate))
        try:
            import borg_collective  # noqa: F401
            return True
        except ImportError:
            return False
    return False


def _client_factory() -> Any:
    global Client
    if Client is None:
        from borg_collective import Client as CollectiveClient

        Client = CollectiveClient
    return Client


def _has_error_report_signal(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in ERROR_REPORT_PATTERNS)


def _classify_technical_token(text: str) -> str | None:
    for pattern, error_class in TECHNICAL_TOKEN_PATTERNS:
        if pattern.search(text or ""):
            return error_class
    return None


def find_local_traces(user_msg: str, error_class: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search the local Borg trace DB as a federation-empty fallback."""
    from borg.core.trace_matcher import find_relevant

    technology = LOCAL_TECHNOLOGY_BY_CLASS.get(error_class)
    if technology:
        return list(find_relevant(user_msg, technology=technology, limit=limit) or [])
    return list(find_relevant(user_msg, limit=limit) or [])


def _local_trace_preview(trace: dict[str, Any]) -> str:
    return str(
        trace.get("approach_summary")
        or trace.get("causal_intervention")
        or trace.get("root_cause")
        or trace.get("task_description")
        or ""
    )


def _emit_local_trace_context(
    *,
    traces: list[dict[str, Any]],
    error_class: str,
    session_id: Any,
) -> dict[str, str] | None:
    if not traces:
        return None
    top = traces[0]
    top_trace_id = str(top.get("id") or top.get("trace_id") or "")
    preview = _local_trace_preview(top)
    local_search_id = uuid.uuid4().hex
    STATE_PATH.write_text(
        json.dumps(
            {
                "local_search_id": local_search_id,
                "top_trace_id": top_trace_id,
                "error_class": error_class,
                "source": "local_trace_db",
                "ts": time.time(),
                "session_id": session_id,
            }
        ),
        encoding="utf-8",
    )
    hint = (
        f"[Borg] {len(traces)} prior local trace(s) hit '{error_class}'. "
        f"Top: {top_trace_id} — {preview[:140]}"
    )
    _log(
        "pre_llm_call: local fallback "
        f"cls={error_class} count={len(traces)} top={top_trace_id} "
        f"local_search_id={local_search_id} hint_emitted=1"
    )
    return {"context": hint}


def detect_error_class(text: str) -> str | None:
    """Return Borg search error class for an incoming Hermes user message.

    Existing explicit ecosystem tokens keep their old behavior. New
    conversational matches require both an error-report phrase and a concrete
    technical/error token so benign greetings, status requests, and login/MOTD
    text do not reopen the old false-positive class.
    """
    if not isinstance(text, str) or not text:
        return None

    for pattern, error_class in EXISTING_ERROR_PATTERNS:
        if pattern.search(text):
            return error_class

    if not _has_error_report_signal(text):
        return None
    return _classify_technical_token(text)


# Backward-compatible name used by the original unversioned plugin.
def _detect(text: str) -> str | None:
    return detect_error_class(text)


def on_pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    """Hermes ``pre_llm_call`` callback."""
    user_msg = kwargs.get("user_message") or ""
    if not isinstance(user_msg, str):
        return None

    error_class = detect_error_class(user_msg)
    if error_class is None:
        _log(f"pre_llm_call: no error class matched (session={kwargs.get('session_id','?')})")
        return None

    if not _ensure_borg_importable():
        _log("pre_llm_call: borg_collective import failed — skipping")
        return None

    try:
        client_factory = _client_factory()
        with client_factory.from_config() as client:
            results = client.search(error_class=error_class, limit=3)
    except Exception as exc:
        _log(f"pre_llm_call: search failed cls={error_class} err={exc!r}")
        try:
            return _emit_local_trace_context(
                traces=find_local_traces(user_msg, error_class, limit=3),
                error_class=error_class,
                session_id=kwargs.get("session_id"),
            )
        except Exception as local_exc:
            _log(f"pre_llm_call: local fallback failed cls={error_class} err={local_exc!r}")
            return None

    if results.count == 0:
        _log(f"pre_llm_call: search ran cls={error_class} count=0")
        try:
            return _emit_local_trace_context(
                traces=find_local_traces(user_msg, error_class, limit=3),
                error_class=error_class,
                session_id=kwargs.get("session_id"),
            )
        except Exception as local_exc:
            _log(f"pre_llm_call: local fallback failed cls={error_class} err={local_exc!r}")
            return None

    top = results.results[0]
    local_search_id = uuid.uuid4().hex
    STATE_PATH.write_text(
        json.dumps(
            {
                "local_search_id": local_search_id,
                "top_trace_id": top.trace_id,
                "error_class": error_class,
                "ts": time.time(),
                "session_id": kwargs.get("session_id"),
            }
        ),
        encoding="utf-8",
    )
    hint = (
        f"[Borg] {results.count} prior agent(s) hit '{error_class}'. "
        f"Top: {top.trace_id} — {top.preview[:140]}"
    )
    _log(
        "pre_llm_call: search ran "
        f"cls={error_class} count={results.count} top={top.trace_id} "
        f"local_search_id={local_search_id} hint_emitted=1"
    )
    return {"context": hint}


# Backward-compatible name used by the original unversioned plugin.
def _on_pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    return on_pre_llm_call(**kwargs)


def on_post_tool_call(**kwargs: Any) -> None:
    """Hermes ``post_tool_call`` callback: send feedback for the cached search."""
    if not STATE_PATH.exists():
        return None
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None

    blob = json.dumps(kwargs.get("tool_result") or kwargs.get("result") or kwargs)[:2000]
    indicates_error = bool(re.search(r"error|failed|exception|traceback", blob, re.I))
    outcome = "didnt_help" if indicates_error else "helped"

    if not _ensure_borg_importable():
        _log("post_tool_call: borg_collective import failed — skipping feedback")
        return None

    try:
        client_factory = _client_factory()
        with client_factory.from_config() as client:
            client.feedback(
                state["top_trace_id"],
                retrieved=True,
                read=True,
                applied=True,
                outcome=outcome,
                note=f"prior_search_id={state['local_search_id']}",
            )
        _log(
            "post_tool_call: feedback sent "
            f"trace={state['top_trace_id']} outcome={outcome} "
            f"prior_search_id={state['local_search_id']}"
        )
    except Exception as exc:
        _log(f"post_tool_call: feedback failed err={exc!r}")
    return None


# Backward-compatible name used by the original unversioned plugin.
def _on_post_tool_call(**kwargs: Any) -> None:
    return on_post_tool_call(**kwargs)


def register(ctx: Any) -> None:
    """Register Hermes lifecycle hooks."""
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    ctx.register_hook("post_tool_call", on_post_tool_call)
    _log("plugin registered: pre_llm_call + post_tool_call")


__all__ = [
    "Client",
    "EXISTING_ERROR_PATTERNS",
    "ERROR_REPORT_PATTERNS",
    "LOG_PATH",
    "STATE_PATH",
    "TECHNICAL_TOKEN_PATTERNS",
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
