"""
Guild Safety Module — standalone pack validation for injection, credential access,
and privacy leaks. Zero imports from tools.* — stdlib + yaml only.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Literal

import yaml


# --------------------------------------------------------------------------
# Safety patterns — compiled once at module load
# --------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    # Prompt injection
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+your", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"disregard", re.IGNORECASE),
    re.compile(r"override", re.IGNORECASE),
    re.compile(r"new\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now", re.IGNORECASE),
    re.compile(r"act\s+as", re.IGNORECASE),
    re.compile(r"forget\s+previous", re.IGNORECASE),
    # Shell / code injection
    re.compile(r"\$\("),                                     # $(...) command substitution
    re.compile(r"\b(eval|exec)\s*\(", re.IGNORECASE),        # eval()/exec()
    re.compile(r"\brm\s+(-[rf]+\s+)?/", re.IGNORECASE),       # rm -rf /
    re.compile(r"\bmkfifo\b", re.IGNORECASE),                # named pipe (reverse shell)
    re.compile(r"/dev/(tcp|udp)/", re.IGNORECASE),            # bash net redirect
    re.compile(r"__import__\s*\(", re.IGNORECASE),            # Python dynamic import
    re.compile(r"\bos\.system\s*\(", re.IGNORECASE),         # os.system()
    re.compile(r"\bsubprocess\.(run|call|Popen)\s*\(", re.IGNORECASE),  # subprocess
]

# Privilege escalation patterns — produces WARNINGS, not blocks
# These are security concerns but not direct injection vectors
_PRIVILEGE_ESCALATION_PATTERNS = [
    re.compile(r"\bsudo\s+", re.IGNORECASE),                 # sudo
]

_CREDENTIAL_PATTERNS = [
    re.compile(r"\.env\b", re.IGNORECASE),
    re.compile(r"api[_\s-]?key", re.IGNORECASE),
    re.compile(r"\bsecret\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
]

_FILE_ACCESS_PATTERNS = [
    re.compile(r"ls\s+~/.hermes", re.IGNORECASE),
    re.compile(r"cat\s+\.env", re.IGNORECASE),
    re.compile(r"cat\s+~/.hermes", re.IGNORECASE),
    re.compile(r"\.\./", re.IGNORECASE),   # path traversal
    re.compile(r"ls\s+~/.ssh\b", re.IGNORECASE),  # SSH key directory enumeration
    re.compile(r"cat\s+~/.ssh/", re.IGNORECASE),  # reading SSH private keys
    re.compile(r"\bnc\s+", re.IGNORECASE), # netcat reverse shell
]

# File access patterns that are only flagged in STRICT mode or in prompts/anti_patterns
# NOT flagged in descriptions (instructional text) in NORMAL mode
_FILE_ACCESS_WARNINGS = [
    re.compile(r"curl\s+", re.IGNORECASE), # curl exfiltration
    re.compile(r"wget\s+", re.IGNORECASE), # wget exfiltration
]

_PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),            # Double-dot path traversal in any string field
    re.compile(r"\.\.%2f", re.IGNORECASE),  # URL-encoded ..%2f
]

_PRIVACY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"~/.hermes\b"), "hermes config path"),
    (re.compile(r"/root/\S+"), "root home path"),
    (re.compile(r"/home/\w+/\S+"), "user home path"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "IP address"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "email address"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI API key"),
    (re.compile(r"\bxoxb-[A-Za-z0-9-]+\b"), "Slack bot token"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "GitHub personal access token"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"), "Google API key"),
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "AWS access key"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "GitLab token"),
]

# --------------------------------------------------------------------------
# Size limit constants
# --------------------------------------------------------------------------

MAX_PHASES: int = 20
MAX_PACK_SIZE_BYTES: int = 500 * 1024   # 500 KB
MAX_FIELD_SIZE_BYTES: int = 10 * 1024   # 10 KB


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def collect_text_fields(obj: Any) -> List[str]:
    """Recursively extract all string values from a nested dict/list structure.

    Args:
        obj: A dict, list, or scalar value.

    Returns:
        A flat list of all string values found.
    """
    strings: List[str] = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(collect_text_fields(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            strings.extend(collect_text_fields(item))
    return strings


def _iter_pack_phases(pack: dict) -> List[dict]:
    """Return V1 and V2 phases that can influence generated agent behavior."""
    phases = pack.get("phases")
    if isinstance(phases, list) and phases:
        return [phase for phase in phases if isinstance(phase, dict)]
    structure = pack.get("structure")
    if isinstance(structure, dict):
        phases = structure.get("phases", [])
    else:
        phases = structure if isinstance(structure, list) else []
    return [phase for phase in phases if isinstance(phase, dict)]


def _append_behavior_texts(value: Any, sink: List[str]) -> None:
    """Append nested strings from behavior-influencing fields to a sink."""
    sink.extend(collect_text_fields(value))


def _phase_count(pack: dict) -> int:
    if _is_v2_pack(pack):
        structure = pack.get("structure", [])
        if isinstance(structure, dict):
            phases = structure.get("phases", [])
        else:
            phases = structure
        return len(phases) if isinstance(phases, list) else 0
    phases = pack.get("phases", [])
    return len(phases) if isinstance(phases, list) else 0


def scan_pack_safety(pack: dict, mode: Literal["normal", "strict"] = "normal") -> List[str]:
    """Scan pack for prompt injection, credential access, and file exfiltration.

    Args:
        pack: A parsed guild pack dictionary.
        mode: "normal" (default) — only flags dangerous patterns in prompts/anti_patterns,
              "strict" — flags patterns in all text fields.
              In normal mode, curl/wget and $(command substitution) in descriptions are
              treated as instructional text (allowed), not threats.

    Returns:
        A list of threat description strings. Empty list means the pack is clean.
    """
    threats: List[str] = []
    warnings: List[str] = []

    if mode == "normal":
        # NORMAL mode: separate text into command contexts vs instructional contexts
        command_texts: List[str] = []  # prompts, anti_patterns, required_inputs, escalation_rules — higher risk
        instruction_texts: List[str] = []  # descriptions, mental_model — lower risk

        # Collect all fields that are rendered into generated rules or influence
        # agent behaviour. V1 packs use phases[]; V2 packs use structure.phases[].
        # Treat executable/adaptive prompt surfaces as command context; headings
        # and descriptions remain instructional but still block prompt-injection,
        # credential, file-access and path-traversal patterns.
        for field in ("id", "name", "problem_class", "mental_model"):
            _append_behavior_texts(pack.get(field), instruction_texts)

        for phase in _iter_pack_phases(pack):
            for field in ("name", "title", "description"):
                _append_behavior_texts(phase.get(field), instruction_texts)
            _append_behavior_texts(phase.get("checkpoint"), command_texts)
            for field in (
                "prompts",
                "anti_patterns",
                "context_prompts",
                "inject_if",
                "skip_if",
                "start_signals",
            ):
                _append_behavior_texts(phase.get(field), command_texts)

        for field in (
            "required_inputs",
            "escalation_rules",
            "prompt",
            "context_prompts",
            "start_signals",
            "inject_if",
            "skip_if",
            "anti_patterns",
        ):
            _append_behavior_texts(pack.get(field), command_texts)

        command_combined = "\n".join(command_texts)
        instruction_combined = "\n".join(instruction_texts)

        # Check injection patterns — $(...) only in command contexts
        for pattern in _INJECTION_PATTERNS:
            if pattern.pattern == r"\$\(":
                # $(...) is only dangerous in command contexts
                if pattern.search(command_combined):
                    threats.append(
                        f"Prompt injection detected: pattern '{pattern.pattern}' found in pack prompts/anti_patterns"
                    )
            else:
                # Other injection patterns check all text
                if pattern.search(command_combined) or pattern.search(instruction_combined):
                    threats.append(
                        f"Prompt injection detected: pattern '{pattern.pattern}' found in pack text"
                    )

        # Check privilege escalation patterns — warnings only
        for pattern in _PRIVILEGE_ESCALATION_PATTERNS:
            if pattern.search(command_combined):
                warnings.append(
                    f"Privilege escalation warning: pattern '{pattern.pattern}' found in pack prompts"
                )

        # Check credential patterns — all text
        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(command_combined) or pattern.search(instruction_combined):
                threats.append(
                    f"Credential reference detected: pattern '{pattern.pattern}' found in pack text"
                )

        # Check file access patterns — always blocking
        for pattern in _FILE_ACCESS_PATTERNS:
            if pattern.search(command_combined) or pattern.search(instruction_combined):
                threats.append(
                    f"Suspicious file access detected: pattern '{pattern.pattern}' found in pack text"
                )

        # Check curl/wget patterns — only blocking in command contexts (prompts/anti_patterns)
        for pattern in _FILE_ACCESS_WARNINGS:
            if pattern.search(command_combined):
                threats.append(
                    f"Suspicious file access detected: pattern '{pattern.pattern}' found in pack prompts/anti_patterns"
                )
            elif pattern.search(instruction_combined):
                warnings.append(
                    f"File access warning: pattern '{pattern.pattern}' found in pack descriptions (informational only)"
                )

        # Check path traversal patterns — all text
        for pattern in _PATH_TRAVERSAL_PATTERNS:
            if pattern.search(command_combined) or pattern.search(instruction_combined):
                threats.append(
                    f"Path traversal detected: pattern '{pattern.pattern}' found in pack text"
                )

        return threats + warnings

    else:
        # STRICT mode: scan all text for everything (legacy behavior)
        texts = collect_text_fields(pack)
        combined = "\n".join(texts)

        for pattern in _INJECTION_PATTERNS:
            if pattern.search(combined):
                threats.append(
                    f"Prompt injection detected: pattern '{pattern.pattern}' found in pack text"
                )

        for pattern in _PRIVILEGE_ESCALATION_PATTERNS:
            if pattern.search(combined):
                threats.append(
                    f"Privilege escalation detected: pattern '{pattern.pattern}' found in pack text"
                )

        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(combined):
                threats.append(
                    f"Credential reference detected: pattern '{pattern.pattern}' found in pack text"
                )

        for pattern in _FILE_ACCESS_PATTERNS:
            if pattern.search(combined):
                threats.append(
                    f"Suspicious file access detected: pattern '{pattern.pattern}' found in pack text"
                )

        for pattern in _FILE_ACCESS_WARNINGS:
            if pattern.search(combined):
                threats.append(
                    f"Suspicious file access detected: pattern '{pattern.pattern}' found in pack text"
                )

        for pattern in _PATH_TRAVERSAL_PATTERNS:
            if pattern.search(combined):
                threats.append(
                    f"Path traversal detected: pattern '{pattern.pattern}' found in pack text"
                )

        return threats


def scan_privacy(pack: dict) -> List[str]:
    """Recursively scan all string values in a pack dict for privacy leaks.

    Args:
        pack: A parsed guild pack dictionary.

    Returns:
        A list of threat description strings. Empty list means no PII/secrets found.
    """
    threats: List[str] = []
    all_strings = collect_text_fields(pack)
    for s in all_strings:
        for pat, label in _PRIVACY_PATTERNS:
            match = pat.search(s)
            if match:
                threats.append(f"Privacy leak ({label}): '{match.group()}' in value")
    return threats


def check_pack_size_limits(pack: dict, pack_file: Path) -> List[str]:
    """Validate pack against size limits.

    Args:
        pack: A parsed guild pack dictionary.
        pack_file: Path to the pack YAML file on disk (used for file-size check).

    Returns:
        A list of violation description strings. Empty list means within limits.
    """
    violations: List[str] = []

    # Total file size
    try:
        file_size = pack_file.stat().st_size
        if file_size > MAX_PACK_SIZE_BYTES:
            violations.append(
                f"Pack file exceeds 500KB limit: {file_size} bytes"
            )
    except OSError:
        pass

    # Phase count — V2 uses structure.phases or legacy structure[], V1 uses phases[]
    phase_count = _phase_count(pack)
    if phase_count > MAX_PHASES:
        violations.append(
            f"Pack has {phase_count} phases, exceeds limit of {MAX_PHASES}"
        )

    # Per-field size check
    def check_fields(obj: Any, path: str = "") -> None:
        if isinstance(obj, str):
            if len(obj.encode("utf-8")) > MAX_FIELD_SIZE_BYTES:
                violations.append(
                    f"Field '{path}' exceeds 10KB limit: {len(obj.encode('utf-8'))} bytes"
                )
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_fields(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_fields(item, f"{path}[{i}]")

    check_fields(pack)
    return violations


# --------------------------------------------------------------------------
# Private helpers (mirror the originals, no tools.* imports)
# --------------------------------------------------------------------------

def _is_v2_pack(pack: dict) -> bool:
    """Return True if this is a V2 pack (has structure[] instead of phases[])."""
    return "structure" in pack and "phases" not in pack
