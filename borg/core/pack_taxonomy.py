"""
Pack Taxonomy + CLI Guidance Renderer

Provides:
  - ERROR_TYPE_TO_PROBLEM_CLASS: maps error_type strings → problem_class
  - classify_error(error_message): parses error message → problem_class
  - load_pack_by_problem_class(problem_class): loads matching pack YAML
  - render_pack_guidance(pack): formats pack for CLI output
  - BORG_DEBUG_KWARGS: maps problem_class → @mention placeholders used in packs

Architecture:
  - Seed packs live in borg/skills/*.md (YAML frontmatter)
  - Pack loader reads them and caches in memory
  - Thompson Sampling integration via v3_integration.BorgV3
"""

from __future__ import annotations

import importlib.resources
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------
# Error → problem_class taxonomy
# -----------------------------------------------------------------------
# Maps error type name substrings → problem_class
# First match wins (evaluated in order).

_ERROR_KEYWORDS: List[Tuple[str, str]] = [
    # Django migrations
    ("circular", "circular_dependency"),
    ("dependency cycle", "circular_dependency"),
    ("InvalidMoveError", "circular_dependency"),
    ("makemigrations", "migration_state_desync"),
    ("migrate", "migration_state_desync"),
    ("no such table", "migration_state_desync"),
    ("table already exists", "migration_state_desync"),
    ("applied migrations", "migration_state_desync"),
    # Django models / DB
    ("FOREIGN KEY constraint failed", "missing_foreign_key"),
    ("IntegrityError", "missing_foreign_key"),
    ("no such column", "schema_drift"),
    ("table has no column", "schema_drift"),
    # Django config
    ("ImproperlyConfigured", "configuration_error"),
    ("SECRET_KEY", "configuration_error"),
    ("ALLOWED_HOSTS", "configuration_error"),
    ("DATABASE_URL", "configuration_error"),
    # Python types
    ("NoneType", "null_pointer_chain"),
    ("'NoneType'", "null_pointer_chain"),
    ("object is not iterable", "null_pointer_chain"),
    # Python imports
    ("circular import", "import_cycle"),
    ("import cycle", "import_cycle"),
    ("cannot import name", "import_cycle"),
    # Permissions
    ("PermissionError", "permission_denied"),
    ("permission denied", "permission_denied"),
    ("EACCES", "permission_denied"),
    ("EPERM", "permission_denied"),
    # Concurrency
    ("dictionary changed size during iteration", "race_condition"),
    ("TimeoutError", "timeout_hang"),
    ("timed out", "timeout_hang"),
    ("Connection refused", "timeout_hang"),
    ("Connection timed out", "timeout_hang"),
    ("GatewayTimeout", "timeout_hang"),
    # Missing dependencies
    ("ModuleNotFoundError", "missing_dependency"),
    ("No module named", "missing_dependency"),
    ("ImportError", "missing_dependency"),
    # Type errors
    ("TypeError", "type_mismatch"),
    ("mypy", "type_mismatch"),
    # Schema drift
    ("OperationalError", "schema_drift"),
    ("SyncError", "schema_drift"),
    # NOTE: v3.2.2 — the bare ("Error", "schema_drift") fallback was removed.
    # It was a generic substring trap that routed every error containing the
    # word "error" — Rust E0382, Docker ENOSPC, Go panics, JS TypeError — to
    # the Django schema_drift pack. See docs/20260408-0623_classifier_prd/
    # for the full PRD and the new confidence-gated classifier roadmap.
]


# -----------------------------------------------------------------------
# Phase 0 language detection — non-Python locking signals
# -----------------------------------------------------------------------
# Each entry is a regex that, if matched, locks the input to a specific
# non-Python language. Phase 0 only needs to detect "this is definitely
# NOT Python" so classify_error can refuse to answer instead of routing
# to a Python/Django pack. Phase 1 (ARCHITECTURE_SPEC.md §5.1) replaces
# this with a full multi-language detection cascade.
import re as _re

_NON_PYTHON_LOCKING_SIGNALS: List[Tuple[str, "_re.Pattern[str]"]] = [
    # Rust — rustc error codes and borrow checker
    ("rust", _re.compile(r"error\[E\d{4}\]")),
    ("rust", _re.compile(r"\bborrow checker\b", _re.IGNORECASE)),
    ("rust", _re.compile(r"borrow of moved value", _re.IGNORECASE)),
    ("rust", _re.compile(r"\bcargo (build|run|test|check)\b")),
    ("rust", _re.compile(r"\brustc\b")),
    ("rust", _re.compile(r"does not live long enough")),
    ("rust", _re.compile(r"cannot borrow .* as mutable")),
    # Go — runtime panics, goroutines, modules
    ("go", _re.compile(r"\bgoroutine \d+ \[")),
    ("go", _re.compile(r"panic: runtime error")),
    ("go", _re.compile(r"invalid memory address or nil pointer dereference")),
    ("go", _re.compile(r"\bgo\.mod\b")),
    ("go", _re.compile(r"go: cannot find module")),
    # JavaScript / Node.js
    ("javascript", _re.compile(r"Cannot read propert(?:y|ies) of (?:null|undefined)")),
    ("javascript", _re.compile(r"\bReferenceError\b.*is not defined")),
    ("javascript", _re.compile(r"UnhandledPromiseRejectionWarning")),
    ("javascript", _re.compile(r"\bnode_modules\b")),
    ("javascript", _re.compile(r"at .*\.(?:js|mjs|cjs):\d+")),
    ("javascript", _re.compile(r"npm ERR!")),
    # TypeScript — compiler errors
    ("typescript", _re.compile(r"\bTS\d{4}\b")),
    ("typescript", _re.compile(r"is not assignable to type")),
    ("typescript", _re.compile(r"\.tsx?:\d+:\d+")),
    # React / Next.js
    ("react", _re.compile(r"Hydration failed because", _re.IGNORECASE)),
    ("react", _re.compile(r"Text content does not match server-rendered HTML")),
    ("react", _re.compile(r"Invalid hook call")),
    ("react", _re.compile(r"Each child in a list should have a unique \"key\" prop")),
    # Docker / BuildKit
    ("docker", _re.compile(r"\bENOSPC\b")),
    ("docker", _re.compile(r"no space left on device", _re.IGNORECASE)),
    ("docker", _re.compile(r"failed to solve:")),
    ("docker", _re.compile(r"^docker:", _re.MULTILINE)),
    ("docker", _re.compile(r"COPY failed:")),
    ("docker", _re.compile(r"manifest unknown")),
    # Kubernetes
    ("kubernetes", _re.compile(r"CrashLoopBackOff")),
    ("kubernetes", _re.compile(r"ImagePullBackOff")),
    ("kubernetes", _re.compile(r"ErrImagePull")),
    ("kubernetes", _re.compile(r"OOMKilled")),
    ("kubernetes", _re.compile(r"\bkubectl\b")),
    ("kubernetes", _re.compile(r"FailedScheduling")),
]

# Python "positive lock" signals — if any of these match we KEEP processing
# Python keywords even if a non-Python signal also fires (polyglot logs).
_PYTHON_LOCKING_SIGNALS: List["_re.Pattern[str]"] = [
    _re.compile(r"Traceback \(most recent call last\)"),
    _re.compile(r"\bpython3?(?:\.\d+)?\b"),
    _re.compile(r"\.py:\d+"),
    _re.compile(r"\bmanage\.py\b"),
    _re.compile(r"\bdjango\."),
    _re.compile(r"\bflask\b", _re.IGNORECASE),
    _re.compile(r"\bfastapi\b", _re.IGNORECASE),
    _re.compile(r"\bpip install\b"),
    _re.compile(r"ModuleNotFoundError: No module named"),
]


def _detect_language_quick(error_message: str) -> Optional[str]:
    """Phase 0 language detector — return non-Python language if locked.

    Returns one of {'rust','go','javascript','typescript','react','docker',
    'kubernetes'} when a high-confidence non-Python signal fires AND no
    Python locking signal also fires. Returns None otherwise (which means
    "Python or unknown — proceed with the legacy keyword table").

    Phase 1 will replace this with the full cascade in
    ARCHITECTURE_SPEC.md §4.3 / §5.1.
    """
    if not error_message:
        return None
    # If any Python locking signal fires, treat as Python (keep current behaviour).
    for pat in _PYTHON_LOCKING_SIGNALS:
        if pat.search(error_message):
            return None
    # Otherwise, the first non-Python locking signal wins.
    for lang, pat in _NON_PYTHON_LOCKING_SIGNALS:
        if pat.search(error_message):
            return lang
    return None


# -----------------------------------------------------------------------
# v3.2.3 anti_signatures — suppress first-match-wins over-fires
# -----------------------------------------------------------------------
# An anti_signature is a regex that, if it matches the error text, blocks
# the firing keyword's problem_class from winning. The classifier loop
# continues to the next keyword and returns None if nothing clears.
#
# Each entry names the corpus row it targets and the Python positive it
# explicitly does NOT match. See docs/20260408-0623_classifier_prd/
# v323_fc_analysis.md for the full design + simulation proof.
#
# Phase 1 will migrate these into per-pack `anti_signatures` frontmatter
# (ARCHITECTURE_SPEC.md §4.2 / §8.1). Until then, the dict lives here next
# to _ERROR_KEYWORDS so the patch is a pure classifier change.
_ANTI_SIGNATURES: Dict[str, List["_re.Pattern[str]"]] = {
    "circular_dependency": [
        # Corpus row e0009 — Python's canonical "partially initialized
        # module" phrasing is the RIGHT phrase for import_cycle, not
        # circular_dependency. Does NOT match any of the 10
        # PYTHON_REGRESSION_FIXTURES (none contain "partially initialized
        # module" or "most likely due to a circular import").
        _re.compile(r"partially initialized module", _re.IGNORECASE),
        _re.compile(r"most likely due to a circular import", _re.IGNORECASE),
        # Corpus row e0044 — JS JSON.stringify cyclic structure error.
        # Does NOT match any Python fixture (no Python fixture mentions
        # "Converting circular structure to JSON").
        _re.compile(r"Converting circular structure to JSON", _re.IGNORECASE),
    ],
    "type_mismatch": [
        # Corpus row e0036 — JS "Cannot read property 'length' of null"
        # (pre-2019 singular phrasing). The 0-40 char gap covers the
        # quoted key like 'length'. Anchored on `of (null|undefined)` so
        # a Python message containing the literal phrase "cannot read
        # property" without the JS-specific null/undefined ending will
        # not match. Does NOT match any Python fixture.
        _re.compile(
            r"Cannot read propert(?:y|ies)\b[^\n]{0,40}?\bof (?:null|undefined)",
            _re.IGNORECASE,
        ),
        # Corpus row e0042 — JS "x is not a function". Python equivalent
        # for non-callables is "is not callable" (PEP 8 / CPython), so
        # the literal `is not a function` is JS-only. Does NOT match any
        # Python fixture.
        _re.compile(r"\bis not a function\b", _re.IGNORECASE),
        # Corpus row e0043 — JS "Assignment to constant variable". Python
        # does not have const-reassignment errors (no consts). Does NOT
        # match any Python fixture.
        _re.compile(r"Assignment to constant variable", _re.IGNORECASE),
        # Corpus row e0044 — defence-in-depth duplicate of the
        # circular_dependency anti_signature. If _ERROR_KEYWORDS is ever
        # reordered so TypeError fires before 'circular', this row still
        # gets suppressed. Does NOT match any Python fixture.
        _re.compile(r"Converting circular structure to JSON", _re.IGNORECASE),
    ],
    "import_cycle": [
        # Corpus row e0122 — Go's exact cyclic-import compiler phrasing.
        # Does NOT match any Python fixture (no Python fixture contains
        # the literal string "import cycle not allowed").
        _re.compile(r"import cycle not allowed", _re.IGNORECASE),
    ],
    "timeout_hang": [
        # Corpus row e0157 — K8s readiness/liveness/startup probe failures
        # that contain the substring "connection refused" but should
        # route to k8s_probe_failed (no pack yet — Phase 3). Does NOT
        # match Python fixture #7 "TimeoutError: [Errno 110] Connection
        # timed out" because that fixture has no probe-failed phrasing.
        _re.compile(
            r"\b(?:Readiness|Liveness|Startup) probe failed\b",
            _re.IGNORECASE,
        ),
    ],
}


def _anti_signature_blocks(error_message: str, problem_class: str) -> bool:
    """Return True if any anti_signature for the class matches the text.

    Preserves case of the original `error_message` — the regexes use
    re.IGNORECASE themselves where appropriate. Safe on empty / None
    inputs (returns False).
    """
    if not error_message:
        return False
    for pattern in _ANTI_SIGNATURES.get(problem_class, ()):
        if pattern.search(error_message):
            return True
    return False

# Canonical list of all known problem classes (must match seed pack filenames)
PROBLEM_CLASSES: List[str] = [
    "circular_dependency",
    "null_pointer_chain",
    "missing_foreign_key",
    "migration_state_desync",
    "import_cycle",
    "race_condition",
    "configuration_error",
    "type_mismatch",
    "missing_dependency",
    "timeout_hang",
    "schema_drift",
    "permission_denied",
]

# -----------------------------------------------------------------------
# Pack cache
# -----------------------------------------------------------------------

_PACK_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_INITIALIZED = False


def _get_skills_dir() -> Path:
    """Return the directory containing seed pack .md files.
    
    Search order:
    1. borg/seeds_data/ inside the installed package (PyPI installs)
    2. skills/ directory sibling to borg package (editable/dev installs)
    3. Absolute dev fallback
    4. Return None if not found (callers must handle gracefully)
    """
    import borg as borg_pkg
    borg_path = Path(borg_pkg.__file__).parent  # .../borg/

    # 1. Inside package (PyPI wheel)
    seeds_data = borg_path / "seeds_data"
    if seeds_data.is_dir():
        return seeds_data

    # 2. Sibling to package (editable install)
    skills_dir = borg_path.parent / "skills"
    if skills_dir.is_dir():
        return skills_dir

    # 3. Absolute dev fallback
    dev_path = Path("/root/hermes-workspace/borg/skills")
    if dev_path.is_dir():
        return dev_path

    # 4. Not found — return None instead of crashing
    return None


def _init_cache() -> None:
    """Load all seed packs into memory cache keyed by problem_class."""
    global _CACHE_INITIALIZED, _PACK_CACHE
    if _CACHE_INITIALIZED:
        return

    skills_dir = _get_skills_dir()
    if skills_dir is None:
        _CACHE_INITIALIZED = True
        return
    for pack_file in skills_dir.glob("*.md"):
        try:
            text = pack_file.read_text(encoding="utf-8")
            if not text.startswith("---"):
                continue
            # Extract YAML frontmatter
            yaml_text = text[3:]
            if yaml_text.startswith("\n"):
                yaml_text = yaml_text[1:]
            idx = yaml_text.find("\n---")
            if idx == -1:
                continue
            frontmatter = yaml_text[:idx]
            data = yaml.safe_load(frontmatter)
            if not isinstance(data, dict):
                continue
            pc = data.get("problem_class", "")
            if pc:
                _PACK_CACHE[pc] = data
        except Exception:
            continue

    _CACHE_INITIALIZED = True


def get_cache() -> Dict[str, Dict[str, Any]]:
    """Return the pack cache (initializing it if needed)."""
    _init_cache()
    return _PACK_CACHE


# -----------------------------------------------------------------------
# Core functions
# -----------------------------------------------------------------------

def classify_error(error_message: str) -> Optional[str]:
    """
    Classify an error message string into a problem_class.

    v3.2.3 (Phase 0 of the multi-language classifier roadmap):
    1. Detect non-Python locking signals (Rust E0xxx, Go panic, JS
       Cannot read properties of, TS####, React Hydration failed,
       Docker ENOSPC, Kubernetes CrashLoopBackOff, etc.). If any
       fire, return None ("we don't know yet, refusing to give a
       Python answer to a non-Python error").
    2. Walk the legacy substring keyword table (Python/Django coverage
       unchanged).
    3. Before returning a keyword's problem_class, consult
       `_ANTI_SIGNATURES` to suppress known first-match-wins
       over-fires on Python-looking inputs whose text has a JS/Go/K8s
       phrase the language guard did not catch.

    Phase 1+ (ARCHITECTURE_SPEC.md §3-§7) replaces this with a
    confidence-scored Match | UnknownMatch dataclass return type and
    migrates `_ANTI_SIGNATURES` into per-pack frontmatter.

    See docs/20260408-0623_classifier_prd/ for the full PRD.
    """
    if not error_message:
        return None
    # Phase 0 language guard — refuse to answer non-Python errors.
    if _detect_language_quick(error_message) is not None:
        return None
    lower = error_message.lower()
    for keyword, problem_class in _ERROR_KEYWORDS:
        if keyword.lower() in lower:
            # v3.2.3 anti_signature gate — if a class-specific regex
            # matches the (case-preserved) text, suppress this keyword
            # and keep scanning. Returns None at the end if nothing
            # clears, so `debug_error()` falls through to the same
            # UnknownMatch block as before.
            if _anti_signature_blocks(error_message, problem_class):
                continue
            return problem_class
    return None


def load_pack_by_problem_class(problem_class: str) -> Optional[Dict[str, Any]]:
    """Load a seed pack by problem_class. Returns None if not found."""
    _init_cache()
    return _PACK_CACHE.get(problem_class)


def get_investigation_trail(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get investigation_trail from pack, with @placeholder expansion."""
    trail = pack.get("investigation_trail", [])
    if not isinstance(trail, list):
        return []
    return [
        {
            "file": _expand_placeholder(t["file"]) if isinstance(t, dict) else t,
            "position": t.get("position", "") if isinstance(t, dict) else "",
            "what": t.get("what", "") if isinstance(t, dict) else "",
            "grep_pattern": t.get("grep_pattern", "") if isinstance(t, dict) else "",
        }
        for t in trail
        if isinstance(t, dict)
    ]


def _expand_placeholder(text: str) -> str:
    """Expand @mention placeholders in pack content to their canonical names."""
    replacements = {
        "@call_site": "the file containing the failing method call",
        "@method_return": "the file containing the method that returned None",
        "@upstream_call_site": "the file containing the caller's caller",
        "@migration_file": "the most recent migration file",
        "@parent_model": "the related model file",
        "@env_file": ".env or environment configuration",
        "@settings": "settings.py or equivalent",
        "@failing_module": "the module that failed to import",
        "@package_init": "__init__.py in the package",
        "@called_module": "the module being imported",
        "@error_location": "the file containing the TypeError",
        "@function_definition": "the file containing the function definition",
        "@caller_location": "the file containing the call site",
        "@blocking_call": "the file containing the network/database call",
        "@service_check": "service configuration",
        "@shared_resource": "the file containing shared state",
        "@timing_window": "the file with the concurrent code",
        "@db_schema": "the database with the relevant table",
        "@failing_model": "the Django model with the FK field",
        "@parent_table": "the related database table",
        "@resource_path": "the file or directory with permission issue",
        "@app_code": "the application code accessing the resource",
        "@process_user": "the user the application runs as",
        "@upstream_none": "the file that produced None",
    }
    for placeholder, replacement in replacements.items():
        if text == placeholder or f"@{placeholder}" in text:
            text = text.replace(f"@{placeholder}", placeholder)
            # Return the replacement name
            return replacement
    return text


def render_pack_guidance(
    pack: Dict[str, Any],
    error_message: Optional[str] = None,
    show_evidence: bool = True,
) -> str:
    """
    Render a pack as a human-readable CLI guidance block.

    Args:
        pack: Pack data dict with YAML frontmatter fields
        error_message: Optional original error message for header
        show_evidence: Include evidence stats in output

    Returns:
        Formatted multi-line string suitable for CLI output
    """
    lines: List[str] = []

    problem_class = pack.get("problem_class", "unknown")
    framework = pack.get("framework", "")
    problem_desc = (
        pack.get("problem_signature", {})
        .get("problem_description", "")
        .split(".")[0]  # First sentence only
    )
    root_cause = pack.get("root_cause", {})
    root_cat = root_cause.get("category", "") if isinstance(root_cause, dict) else ""
    root_exp = root_cause.get("explanation", "") if isinstance(root_cause, dict) else ""

    # Header
    lines.append("=" * 60)
    if error_message:
        # Truncate long error messages
        msg = error_message[:120] + ("..." if len(error_message) > 120 else "")
        lines.append(f"ERROR: {msg}")
        lines.append("=" * 60)
    lines.append(f"[{problem_class}]" + (f" ({framework})" if framework else ""))
    if problem_desc:
        lines.append(f"Problem: {problem_desc}")
    lines.append("")

    # Root cause
    if root_cat or root_exp:
        lines.append("ROOT CAUSE:")
        if root_cat:
            lines.append(f"  Category: {root_cat}")
        if root_exp:
            lines.append(f"  {root_exp}")
        lines.append("")

    # Investigation trail
    trail = get_investigation_trail(pack)
    if trail:
        lines.append("INVESTIGATION TRAIL:")
        for i, step in enumerate(trail, 1):
            pos = step.get("position", "").lower()
            pos_str = f"[{pos}] " if pos else ""
            file_hint = step.get("file", "")
            what = step.get("what", "")
            grep = step.get("grep_pattern", "")
            lines.append(f"  {i}. {pos_str}{file_hint}")
            if what:
                lines.append(f"     → {what}")
            if grep:
                lines.append(f"     grep: {grep}")
        lines.append("")

    # Resolution sequence
    res_seq = pack.get("resolution_sequence", [])
    if isinstance(res_seq, list) and res_seq:
        lines.append("RESOLUTION SEQUENCE:")
        for i, step in enumerate(res_seq, 1):
            if isinstance(step, dict):
                action = step.get("action", "")
                cmd = step.get("command", "")
                why = step.get("why", "")
                if action:
                    lines.append(f"  {i}. {action}")
                if cmd:
                    lines.append(f"     Command: {cmd}")
                if why:
                    lines.append(f"     Why: {why}")
            elif isinstance(step, str):
                lines.append(f"  {i}. {step}")
        lines.append("")

    # Anti-patterns
    anti = pack.get("anti_patterns", [])
    if isinstance(anti, list) and anti:
        lines.append("ANTI-PATTERNS (don't do these):")
        for item in anti:
            if isinstance(item, dict):
                action = item.get("action", "")
                why = item.get("why_fails", "")
                if action:
                    lines.append(f"  ✗ {action}")
                if why:
                    lines.append(f"    Fails because: {why}")
            elif isinstance(item, str):
                lines.append(f"  ✗ {item}")
        lines.append("")

    # Evidence
    if show_evidence:
        evidence = pack.get("evidence", {})
        if isinstance(evidence, dict):
            success = evidence.get("success_count", 0)
            failure = evidence.get("failure_count", 0)
            total = success + failure
            rate = evidence.get("success_rate", 0.0)
            uses = evidence.get("uses", 0)
            avg_time = evidence.get("avg_time_to_resolve_minutes", 0.0)
            if total > 0:
                lines.append(f"EVIDENCE: {success}/{total} successes ({rate:.0%}) over {uses} uses")
                if avg_time > 0:
                    lines.append(f"         Avg resolve time: {avg_time:.1f} min")
            lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# -----------------------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------------------

def debug_error(error_message: str, show_evidence: bool = True) -> str:
    """
    Main debug function: classify error → load pack → render guidance.

    Args:
        error_message: The error message or traceback to debug
        show_evidence: Include evidence stats in output

    Returns:
        Formatted guidance string, or an "I don't know yet" UnknownMatch
        block when no matching problem_class is found. v3.2.2 (Phase 0)
        explicitly refuses to print Python/Django guidance for detected
        non-Python errors — it returns the UnknownMatch block instead.
    """
    # Phase 0: detect non-Python languages first so the UnknownMatch
    # block can name the language we DID detect.
    detected_lang = _detect_language_quick(error_message) if error_message else None

    # Step 1: classify
    problem_class = classify_error(error_message)

    if not problem_class:
        lang_line = (
            f"Detected language: {detected_lang}. "
            "Borg currently has Python/Django expert packs only.\n"
            f"Borg refuses to give a Python answer to a {detected_lang} "
            "error — see docs/20260408-0623_classifier_prd/ for the\n"
            "multi-language classifier roadmap."
        ) if detected_lang else (
            "Borg's current packs are Python/Django specific.\n"
            "If your error is Python/Django, try pasting more of the traceback."
        )
        return (
            "============================================================\n"
            f"ERROR: {error_message[:120]}{'...' if len(error_message) > 120 else ''}\n"
            "============================================================\n"
            "[unknown] No matching problem class found.\n"
            "\n"
            f"{lang_line}\n"
            "\n"
            "Known Python/Django problem classes:\n"
            "  " + ", ".join(PROBLEM_CLASSES) + "\n"
            "\n"
            "Help us add coverage for your language:\n"
            "  https://github.com/bensargotest-sys/agent-borg/issues/new\n"
            "============================================================"
        )

    # Step 2: load pack
    pack = load_pack_by_problem_class(problem_class)

    if not pack:
        return (
            f"Pack for '{problem_class}' found but failed to load.\n"
            "This is a system error — check that borg/skills/*.md files exist."
        )

    # Step 3: render
    return render_pack_guidance(pack, error_message=error_message, show_evidence=show_evidence)
