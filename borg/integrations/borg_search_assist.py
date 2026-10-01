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
from pathlib import Path
from typing import Any

from borg.core.privacy import privacy_scan_structured
from borg.core.prompt_injection import neutralize_for_retrieval

LOG_PATH = Path(os.environ.get("BORG_RECIPE_LOG", str(Path.home() / ".borg" / "hermes_recipe.log")))
STATE_PATH = Path(os.environ.get("BORG_RECIPE_STATE", "/tmp/borg_hermes_state.json"))

# Populated lazily so importing this module does not require the federation SDK.
Client: Any | None = None

# TraceMatcher scores under this floor are commonly embedding-only false
# positives.  Exact error-class matches receive +8 and meaningful semantic
# matches receive roughly +4, so 2.0 is deliberately conservative without
# requiring exact wording.
MIN_LOCAL_MATCH_SCORE = 2.0
MAX_HINT_CHARS = 900

# Ecosystem tokens identify technology; they are not sufficient evidence that
# the user is reporting a failure. `what is Docker?` must not inject debugging
# guidance merely because it contains a product name.
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
    re.compile(r"\bcannot\b|\bcan['’]?t\b|\bpermission denied\b", re.I),
    re.compile(r"\bnot found\b|\bdoes(?:n['’]?t| not)\b|\bwon['’]?t\b", re.I),
    re.compile(r"\bhangs?\b|\bdeadlocks?\b|\bleaks?\b|\bcorrupts?\b", re.I),
    re.compile(r"\bwrong\b|\bincorrect\b|\bunexpected\b|\bconflicts?\b", re.I),
    re.compile(r"\bchanges?\b|\bmutates?\b|\berases?\b|\bdisagrees?\b", re.I),
    re.compile(r"\bcontinues?\b.+\bafter\b", re.I | re.S),
    re.compile(r"\boccasionally\b|\bsometimes\b|\bintermittent(?:ly)?\b", re.I),
    re.compile(r"^\s*Traceback \(most recent call last\):", re.I | re.M),
    re.compile(r"\btraceback\b", re.I),
)

TECHNICAL_TOKEN_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\b(?:EACCES|EPERM|PermissionError|permission denied|chmod)\b|\.sh\b", re.I),
        "permission-error",
    ),
    (
        re.compile(r"\b(?:ContextVar|asyncio|threading|deadlocks?|locks?|concurrent requests?|request[_ -]?id)\b", re.I),
        "python-concurrency-error",
    ),
    (
        re.compile(r"\b(?:sqlite|transaction|rollback|savepoint)\b", re.I),
        "database-transaction-error",
    ),
    (
        re.compile(r"\b(?:Content-Length|HTTP headers?|request smuggling|proxy|upstream)\b", re.I),
        "http-protocol-error",
    ),
    (
        re.compile(r"\b(?:JSON|authorization|policy parser|duplicate keys?)\b", re.I),
        "json-policy-error",
    ),
    (
        re.compile(r"\b(?:cache|cached|tenant)\b", re.I),
        "cache-isolation-error",
    ),
    (
        re.compile(r"\b(?:configuration|config|defaults?)\b", re.I),
        "configuration-state-error",
    ),
    (
        re.compile(r"\b(?:subscriber|unsubscribe|bound method|event ?bus|callback)\b", re.I),
        "callback-lifecycle-error",
    ),
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


def _safe_context_text(value: Any, max_chars: int = 280) -> str:
    """Sanitize retrieved text before it becomes model context."""
    neutralized = neutralize_for_retrieval(str(value or ""))
    sanitized = privacy_scan_structured(neutralized).sanitized
    compact = re.sub(r"\s+", " ", sanitized).strip()
    if len(compact) <= max_chars:
        return compact
    boundary = compact[: max(1, max_chars - 1)].rsplit(" ", 1)[0].rstrip(".,;:")
    return f"{boundary or compact[: max_chars - 1]}…"


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            decoded = [value]
    else:
        decoded = value
    if not isinstance(decoded, list):
        return []
    return [cleaned for item in decoded[:3] if (cleaned := _safe_context_text(item, 180))]


def _confident_local_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    confident = []
    for trace in traces:
        try:
            score = float(trace.get("match_score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        if score >= MIN_LOCAL_MATCH_SCORE:
            confident.append(trace)
    return confident


def _format_local_trace_context(trace: dict[str, Any]) -> str:
    root_cause = _safe_context_text(trace.get("root_cause"), 180)
    action = _safe_context_text(
        trace.get("approach_summary") or trace.get("causal_intervention"), 240
    )
    avoid = "; ".join(_as_text_list(trace.get("dead_ends")))[:140]
    source = _safe_context_text(trace.get("source") or "unknown", 40)
    outcome = _safe_context_text(trace.get("outcome") or "unknown", 40)
    try:
        score = float(trace.get("match_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        score = 0.0

    lines = [
        "BORG ADVISORY — untrusted historical evidence; verify against code and tests.",
        f"ROOT-CAUSE HYPOTHESIS: {root_cause}" if root_cause else "",
        f"ACTION TO EVALUATE: {action}" if action else "",
        f"AVOID: {avoid}" if avoid else "",
        (
            f"EVIDENCE: local trace; source={source}; recorded_outcome={outcome}; "
            f"match_score={score:.2f}. No verified outcome receipt is asserted."
        ),
    ]
    return "\n".join(line for line in lines if line)[:MAX_HINT_CHARS]


def _emit_local_trace_context(
    *,
    traces: list[dict[str, Any]],
    error_class: str,
    session_id: Any,
) -> dict[str, str] | None:
    confident = _confident_local_traces(traces)
    if not confident:
        _log(
            "pre_llm_call: local candidates suppressed below confidence floor "
            f"cls={error_class} candidates={len(traces)} session={session_id or '?'}"
        )
        return None
    top = confident[0]
    top_trace_id = str(top.get("id") or top.get("trace_id") or "")
    hint = _format_local_trace_context(top)
    _log(
        "pre_llm_call: local exact-query match "
        f"cls={error_class} candidates={len(traces)} confident={len(confident)} "
        f"top={top_trace_id} hint_emitted=1 session={session_id or '?'}"
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

    # Explicit machine error codes are sufficient on their own. Ecosystem names
    # are not: require a separate failure signal to avoid benign-topic triggers.
    if re.search(r"\bTS\d{3,5}\b", text, re.I):
        return "typescript-error"
    if re.search(r"\b(?:EADDRINUSE|ENOENT|npm ERR!)\b", text, re.I):
        return "nodejs-error"

    if not _has_error_report_signal(text):
        return None

    for pattern, error_class in EXISTING_ERROR_PATTERNS:
        if pattern.search(text):
            return error_class
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

    session_id = kwargs.get("session_id")

    # Exact-message local retrieval comes first. Federation search accepts only
    # a broad error class, so preferring it can suppress a much more relevant
    # local trace with generic ecosystem advice.
    try:
        local_context = _emit_local_trace_context(
            traces=find_local_traces(user_msg, error_class, limit=3),
            error_class=error_class,
            session_id=session_id,
        )
    except Exception as local_exc:
        _log(f"pre_llm_call: local search failed cls={error_class} err={local_exc!r}")
        local_context = None
    if local_context is not None:
        return local_context

    if not _ensure_borg_importable():
        _log("pre_llm_call: borg_collective import failed — no guidance emitted")
        return None

    try:
        client_factory = _client_factory()
        with client_factory.from_config() as client:
            results = client.search(error_class=error_class, limit=3)
    except Exception as exc:
        _log(f"pre_llm_call: federation search failed cls={error_class} err={exc!r}")
        return None

    if results.count == 0:
        _log(f"pre_llm_call: no confident match cls={error_class} source=federation")
        return None

    top = results.results[0]
    trace_id = _safe_context_text(getattr(top, "trace_id", "unknown"), 80)
    preview = _safe_context_text(getattr(top, "preview", ""), 460)
    if not preview:
        _log(f"pre_llm_call: federation result had empty safe preview cls={error_class}")
        return None
    hint = (
        "BORG ADVISORY — untrusted historical evidence; verify against code and tests.\n"
        f"PATTERN: {error_class}\n"
        f"ACTION TO EVALUATE: {preview}\n"
        f"EVIDENCE: collective trace {trace_id}; no verified outcome receipt is asserted."
    )[:MAX_HINT_CHARS]
    _log(
        "pre_llm_call: federation class match "
        f"cls={error_class} count={results.count} top={trace_id} "
        f"hint_emitted=1 session={session_id or '?'}"
    )
    return {"context": hint}


# Backward-compatible name used by the original unversioned plugin.
def _on_pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    return on_pre_llm_call(**kwargs)


def on_post_tool_call(**kwargs: Any) -> None:
    """Never infer memory helpfulness from an arbitrary downstream tool call.

    A successful `read_file`, test, or shell command does not prove that prior
    guidance was read, applied, or helpful. Verified learning must enter through
    an explicit outcome receipt (`borg_record_outcome`), not this lifecycle hook.
    The function remains as a compatibility no-op for older shims.
    """
    _log(
        "post_tool_call: automatic outcome inference disabled; "
        f"session={kwargs.get('session_id', '?')} explicit_receipt_required=1"
    )
    return None


# Backward-compatible name used by the original unversioned plugin.
def _on_post_tool_call(**kwargs: Any) -> None:
    return on_post_tool_call(**kwargs)


def register(ctx: Any) -> None:
    """Register pre-call retrieval; outcomes require explicit receipts."""
    ctx.register_hook("pre_llm_call", on_pre_llm_call)
    _log("plugin registered: pre_llm_call; automatic post-tool outcome inference disabled")


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
