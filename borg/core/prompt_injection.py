"""Deterministic prompt-injection scanning for Borg learning atoms."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PromptInjectionFinding:
    kind: str
    severity: str
    evidence_hash: str


@dataclass(frozen=True)
class PromptInjectionScanResult:
    findings: List[PromptInjectionFinding]
    score: float
    blocked: bool


_PATTERNS = [
    (re.compile(r"\b(ignore|disregard|override)\s+(all\s+)?((previous|prior)\s+)?(system|developer)?\s*instructions\b", re.I), "instruction_override", "critical", 90),
    (re.compile(r"\b(reveal|print|show|dump)\s+(the\s+)?(system|developer)\s+prompt\b", re.I), "instruction_override", "critical", 90),
    (re.compile(r"\b(cat|read|open)\s+~?/\.?(env|ssh/id_rsa|aws/credentials)\b", re.I), "exfiltration", "critical", 100),
    (re.compile(r"\b(send|upload|post|exfiltrate|leak)\b[^.\n]*(credential|secret|token|api[_ -]?key|\.env|id_rsa)", re.I), "exfiltration", "critical", 100),
    (re.compile(r"\b(curl|wget)\s+https?://", re.I), "tool_coercion", "high", 80),
    (re.compile(r"\bwhen\s+retrieved\b|\bfuture\s+agent\b|\byou\s+must\b", re.I), "retrieval_poisoning", "high", 80),
    (re.compile(r"<!--.*?(ignore|system|developer|credential|secret).*?-->", re.I | re.S), "hidden_instruction", "high", 75),
    (re.compile(r"\[[^\]]*(safe|click|read)[^\]]*\]\(https?://[^)]*(evil|leak|token|credential)[^)]*\)", re.I), "hidden_instruction", "high", 75),
    (re.compile(r"[A-Za-z0-9+/=]{80,}"), "encoded_payload", "medium", 45),
    (re.compile("[\u200b\u200c\u200d\ufeff]"), "hidden_unicode", "medium", 45),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()[:16]


def scan_prompt_injection(text: str) -> PromptInjectionScanResult:
    """Detect instruction override, exfiltration, tool coercion, and retrieval poisoning."""
    if not text:
        return PromptInjectionScanResult([], 0, False)

    findings: List[PromptInjectionFinding] = []
    score = 0.0
    for pattern, kind, severity, weight in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(PromptInjectionFinding(kind, severity, _hash(match.group(0))))
            score = max(score, float(weight))
    return PromptInjectionScanResult(findings, score, score >= 75)


def neutralize_for_retrieval(text: str) -> str:
    """Remove dangerous sentences while preserving benign historical advice."""
    if not text:
        return text

    kept = []
    for sentence in _SENTENCE_SPLIT.split(str(text)):
        scan = scan_prompt_injection(sentence)
        if not scan.blocked:
            kept.append(sentence)
    cleaned = " ".join(kept).strip()
    # Defense-in-depth redactions for common secret paths that may appear in mixed text.
    cleaned = re.sub(r"~?/\.?(env|ssh/id_rsa|aws/credentials)\b", "[REDACTED]", cleaned, flags=re.I)
    return cleaned
