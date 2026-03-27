"""
Guild Safety Module — standalone pack validation for injection, credential access,
and privacy leaks. Zero imports from tools.* — stdlib + yaml only.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    re.compile(r"`[^`]+`"),                                  # backtick command substitution
    re.compile(r"\b(eval|exec)\s*\(", re.IGNORECASE),        # eval()/exec()
    re.compile(r"\brm\s+(-[rf]+\s+)?/", re.IGNORECASE),       # rm -rf /
    re.compile(r"\bsudo\s+", re.IGNORECASE),                 # sudo
    re.compile(r"\bmkfifo\b", re.IGNORECASE),                # named pipe (reverse shell)
    re.compile(r"/dev/(tcp|udp)/", re.IGNORECASE),            # bash net redirect
    re.compile(r"__import__\s*\(", re.IGNORECASE),            # Python dynamic import
    re.compile(r"\bos\.system\s*\(", re.IGNORECASE),         # os.system()
    re.compile(r"\bsubprocess\.(run|call|Popen)\s*\(", re.IGNORECASE),  # subprocess
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
    re.compile(r"~/.ssh/", re.IGNORECASE), # SSH key access
    re.compile(r"curl\s+", re.IGNORECASE), # curl exfiltration
    re.compile(r"wget\s+", re.IGNORECASE), # wget exfiltration
    re.compile(r"\bnc\s+", re.IGNORECASE), # netcat reverse shell
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


def scan_pack_safety(pack: dict) -> List[str]:
    """Scan pack for prompt injection, credential access, and file exfiltration.

    Args:
        pack: A parsed guild pack dictionary.

    Returns:
        A list of threat description strings. Empty list means the pack is clean.
    """
    threats: List[str] = []
    # Use recursive collector to catch ALL text in the pack (including prompts, steps, etc)
    texts = collect_text_fields(pack)
    combined = "\n".join(texts)

    # Check injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(combined):
            threats.append(
                f"Prompt injection detected: pattern '{pattern.pattern}' found in pack text"
            )

    # Check credential references
    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(combined):
            threats.append(
                f"Credential reference detected: pattern '{pattern.pattern}' found in pack text"
            )

    # Check file access patterns
    for pattern in _FILE_ACCESS_PATTERNS:
        if pattern.search(combined):
            threats.append(
                f"Suspicious file access detected: pattern '{pattern.pattern}' found in pack text"
            )

    # Check path traversal patterns
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

    # Phase count — V2 uses structure[], V1 uses phases[]
    if _is_v2_pack(pack):
        phase_count = len(pack.get("structure", []))
    else:
        phase_count = len(pack.get("phases", []))
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
