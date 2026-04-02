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
    # Generic
    ("Error", "schema_drift"),
]

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
    """Return the borg/skills directory (one level above borg package)."""
    # borg/                     <- package root
    # borg/core/                <- where this file lives
    # borg/skills/              <- one level up from package
    # borg/skills/*.md          <- seed packs live here
    import borg as borg_pkg
    borg_path = Path(borg_pkg.__file__).parent  # .../borg/
    skills_dir = borg_path.parent / "skills"      # .../skills/ (one level up)
    if skills_dir.is_dir():
        return skills_dir
    # Fallback: absolute path for development workspace
    dev_path = Path("/root/hermes-workspace/borg/skills")
    if dev_path.is_dir():
        return dev_path
    raise FileNotFoundError(f"Cannot find skills directory. Checked: {skills_dir}, {dev_path}")


def _init_cache() -> None:
    """Load all seed packs into memory cache keyed by problem_class."""
    global _CACHE_INITIALIZED, _PACK_CACHE
    if _CACHE_INITIALIZED:
        return

    skills_dir = _get_skills_dir()
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

    Uses keyword matching against ERROR_KEYWORDS.
    Returns the first matching problem_class, or None if no match.
    """
    if not error_message:
        return None
    lower = error_message.lower()
    for keyword, problem_class in _ERROR_KEYWORDS:
        if keyword.lower() in lower:
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
        Formatted guidance string, or a "no pack found" message if
        no matching problem_class is found.
    """
    # Step 1: classify
    problem_class = classify_error(error_message)

    if not problem_class:
        return (
            "No matching problem class found.\n"
            "Try: borg debug <your-error-message>\n"
            "Known problem classes: " + ", ".join(PROBLEM_CLASSES)
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
