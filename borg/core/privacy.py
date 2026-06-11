"""
Guild Privacy Module — PII and secret scanning for guild artifacts and learning atoms.

Backward-compatible legacy APIs remain available:
  - privacy_scan_text
  - privacy_redact
  - privacy_scan_artifact

Structured APIs for privacy-safe collective memory:
  - privacy_scan_structured
  - privacy_risk_score
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, List, Tuple


# ============================================================================
# Legacy privacy patterns — compiled once at module load
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
# Structured privacy API
# ============================================================================

@dataclass(frozen=True)
class PrivacyFinding:
    """A deterministic privacy/security finding without storing the raw match."""

    kind: str
    label: str
    severity: str
    start: int
    end: int
    sample_hash: str


@dataclass(frozen=True)
class PrivacyScanResult:
    """Structured privacy scan result."""

    sanitized: Any
    findings: List[PrivacyFinding]
    risk_score: float
    blocked: bool


_STRUCTURED_PATTERNS: List[Tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"postgres(?:ql)?://[^\s]+", re.I), "database_url", "database URL", "critical"),
    (re.compile(r"mysql://[^\s]+", re.I), "database_url", "database URL", "critical"),
    (re.compile(r"mongodb(?:\+srv)?://[^\s]+", re.I), "database_url", "database URL", "critical"),
    (re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.I), "bearer_token", "bearer token", "critical"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.I), "bearer_token", "bearer token", "critical"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "private_key", "private key", "critical"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "jwt", "JWT", "critical"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "api_key", "OpenAI API key", "critical"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "api_key", "GitHub personal access token", "critical"),
    (re.compile(r"\bAKIA[A-Z0-9]{16}\b"), "api_key", "AWS access key", "critical"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "api_key", "GitLab token", "critical"),
    (re.compile(r"\bxoxb-[A-Za-z0-9-]+\b"), "api_key", "Slack bot token", "critical"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "email", "email address", "high"),
    (re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})(?!\w)"), "phone", "phone number", "high"),
    (re.compile(r"/root/\S+"), "local_path", "root home path", "medium"),
    (re.compile(r"/home/[A-Za-z0-9_.-]+/\S+"), "local_path", "user home path", "medium"),
    (re.compile(r"~/\S+"), "local_path", "home path", "medium"),
    (re.compile(r"C:\\[^\s]+"), "local_path", "Windows path", "medium"),
    (re.compile(r"https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+|[^\s/]+\.(?:local|internal))[^\s]*", re.I), "private_url", "private URL", "medium"),
    (re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b"), "private_ip", "private IP", "medium"),
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b"), "ip_address", "IPv6 address", "medium"),
    (re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b"), "device_id", "MAC address", "medium"),
]

_SEVERITY_SCORE = {"low": 10, "medium": 35, "high": 70, "critical": 100}

# Name-driven credential assignments: AWS_SECRET_ACCESS_KEY=..., db_password: ...,
# token=shortvalue. The entropy rule below only fires on \b-delimited names (\b
# never matches after '_', so compound env-var names slip through) with 32+-char
# high-entropy values. When the NAME says credential, the value is secret
# regardless of its length or entropy. Bare `key=` is excluded (too common as a
# code kwarg); compound forms like *_key / api_key are matched. The name is kept
# in the sanitized text for context; only the value is redacted.
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(?<![A-Za-z0-9])"
    r"(?:[A-Za-z0-9_.-]*?(?:secret|passw(?:or)?d|pwd|passphrase|credential|cred|token|bearer|auth|apikey|api[_-]key)s?"
    r"|[A-Za-z0-9_.-]+[_-]keys?)"
    r"\s*[:=]\s*[\"']?(?!\[REDACTED)([^\s\"',;]{6,})"
)


def _hash_sample(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()[:16]


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {ch: value.count(ch) for ch in set(value)}
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def privacy_scan_structured(text: str) -> PrivacyScanResult:
    """Scan text and return structured findings plus fail-closed risk score."""
    if not text:
        return PrivacyScanResult(text, [], 0, False)

    sanitized = str(text)
    findings: List[PrivacyFinding] = []
    for pattern, kind, label, severity in _STRUCTURED_PATTERNS:
        matches = list(pattern.finditer(sanitized))
        for match in matches:
            findings.append(
                PrivacyFinding(kind, label, severity, match.start(), match.end(), _hash_sample(match.group(0)))
            )
        sanitized = pattern.sub(f"[REDACTED:{kind}]", sanitized)

    entropy_pattern = re.compile(r"(?i)\b(?:token|secret|key|password|pwd)\s*=\s*([A-Za-z0-9_\-+/=]{32,})")
    entropy_matches = list(entropy_pattern.finditer(sanitized))
    for match in entropy_matches:
        candidate = match.group(1)
        if _entropy(candidate) >= 4.0:
            findings.append(
                PrivacyFinding("high_entropy", "high entropy secret", "critical", match.start(1), match.end(1), _hash_sample(candidate))
            )
    sanitized = entropy_pattern.sub(lambda m: m.group(0).replace(m.group(1), "[REDACTED:high_entropy]"), sanitized)

    for match in _CREDENTIAL_ASSIGNMENT.finditer(sanitized):
        findings.append(
            PrivacyFinding(
                "credential_assignment", "credential assignment", "critical",
                match.start(1), match.end(1), _hash_sample(match.group(1)),
            )
        )
    sanitized = _CREDENTIAL_ASSIGNMENT.sub(
        lambda m: m.group(0).replace(m.group(1), "[REDACTED:credential_assignment]"), sanitized
    )

    risk = max((_SEVERITY_SCORE[f.severity] for f in findings), default=0)
    return PrivacyScanResult(sanitized, findings, risk, risk >= 70)


def privacy_risk_score(obj: Any) -> PrivacyScanResult:
    """Deep-scan object strings and return sanitized object plus aggregate risk."""
    all_findings: List[PrivacyFinding] = []

    def _scan(value: Any) -> Any:
        if isinstance(value, str):
            result = privacy_scan_structured(value)
            all_findings.extend(result.findings)
            return result.sanitized
        if isinstance(value, dict):
            return {k: _scan(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_scan(v) for v in value]
        if isinstance(value, tuple):
            return tuple(_scan(v) for v in value)
        return value

    sanitized = _scan(copy.deepcopy(obj))
    risk = max((_SEVERITY_SCORE[f.severity] for f in all_findings), default=0)
    return PrivacyScanResult(sanitized, all_findings, risk, risk >= 70)


# ============================================================================
# Backward-compatible public API
# ============================================================================

def collect_strings(obj: Any) -> List[str]:
    """Recursively collect all string values from a nested dict/list structure."""
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
    """Scan text for PII/secrets. Returns (sanitized_text, list_of_findings)."""
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
    """Scan text for PII/secrets and replace all matches with [REDACTED]."""
    if not text:
        return text

    sanitized = text
    for pattern, _label in _PRIVACY_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def privacy_scan_artifact(artifact: dict) -> Tuple[dict, List[str]]:
    """Deep-scan all string fields in an artifact dict using the legacy scanner."""
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
