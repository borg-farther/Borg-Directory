"""
Guild Privacy Module — PII and secret scanning for guild artifacts.

Zero imports from tools.* or guild_mcp.* — stdlib + re only.

Patterns detected:
  - File paths (/home/*, /root/*, ~/.*, C:\\)
  - IP addresses
  - API keys / tokens (OpenAI, Slack, GitHub, Google, AWS, GitLab)
  - Email addresses
"""

import copy
import re
from typing import Any, List, Tuple


# ============================================================================
# Privacy patterns — compiled once at module load
# ============================================================================

_PRIVACY_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"~/.hermes\b"), "hermes config path"),
    (re.compile(r"/root/\S+"), "root home path"),
    (re.compile(r"/home/\w+/\S+"), "user home path"),
    (re.compile(r"C:\\[^\s]+"), "Windows path"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "IP address"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "email address"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI API key"),
    (re.compile(r"\bxoxb-[A-Za-z0-9-]+\b"), "Slack bot token"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "GitHub personal access token"),
    (re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"), "Google API key"),
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "AWS access key"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "GitLab token"),
]


# ============================================================================
# Public API
# ============================================================================

def collect_strings(obj: Any) -> List[str]:
    """Recursively collect all string values from a nested dict/list structure.

    Args:
        obj: A dict, list, tuple, or scalar value.

    Returns:
        A flat list of all string values found.
    """
    strings: List[str] = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            strings.extend(collect_strings(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            strings.extend(collect_strings(item))
    return strings


def privacy_scan_text(text: str) -> Tuple[str, List[str]]:
    """Scan text for PII/secrets. Returns (sanitized_text, list_of_findings).

    Findings are formatted as "{label}: {count} occurrence(s)".
    The sanitized text has matches replaced with "[REDACTED:{label}]".

    Args:
        text: The input string to scan.

    Returns:
        A 2-tuple of (sanitized_text, findings_list).
    """
    if not text:
        return text, []

    findings: List[str] = []
    sanitized = text
    for pattern, label in _PRIVACY_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            findings.append(f"{label}: {len(matches)} occurrence(s)")
            sanitized = pattern.sub(f"[REDACTED:{label}]", sanitized)
    return sanitized, findings


def privacy_redact(text: str) -> str:
    """Scan text for PII/secrets and replace all matches with [REDACTED].

    Unlike privacy_scan_text, this function:
      - Does not return findings
      - Replaces ALL matches with a plain "[REDACTED]" (no label), regardless
        of which pattern matched

    Suitable for sanitizing log output.

    Args:
        text: The input string to redact.

    Returns:
        The input string with all PII/secret matches replaced by "[REDACTED]".
    """
    if not text:
        return text

    sanitized = text
    for pattern, _label in _PRIVACY_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def privacy_scan_artifact(artifact: dict) -> Tuple[dict, List[str]]:
    """Deep-scan all string fields in an artifact dict.

    Recursively traverses the artifact and scans every string value.
    Returns a deep-copied sanitized artifact with all PII/secrets replaced
    by "[REDACTED:{label}]" markers, plus a flat list of findings.

    Args:
        artifact: The artifact dictionary to scan.

    Returns:
        A 2-tuple of (sanitized_artifact_copy, findings_list).
        Findings are formatted as "{path}: {label}: {count} occurrence(s)".
    """
    sanitized = copy.deepcopy(artifact)
    all_findings: List[str] = []

    def _scan_obj(obj: Any, path: str = "") -> Any:
        if isinstance(obj, str):
            new_val, findings = privacy_scan_text(obj)
            if findings:
                for f in findings:
                    all_findings.append(f"{path}: {f}" if path else f)
            return new_val
        elif isinstance(obj, dict):
            return {k: _scan_obj(v, f"{path}.{k}" if path else k) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_scan_obj(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        return obj

    sanitized = _scan_obj(sanitized)
    return sanitized, all_findings
