"""
Borg Dojo — Skill Gap Detector.

Detects missing capabilities from user request patterns. A gap is flagged
when the user has asked for something 3+ times but no existing skill
adequately covers it.

Public API:
  detect_skill_gaps(
      user_messages: List[Tuple[str, str]],  # (content, session_id)
      existing_skills: Dict[str, Path],
  ) -> List[SkillGap]

Constants:
  REQUEST_PATTERNS — 12+ (regex, capability) pairs
  SKILL_GAP_THRESHOLD — minimum request count to flag a gap (default: 3)
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

from borg.dojo.data_models import SkillGap


# =============================================================================
# Request patterns — maps user request regexes to normalized capability names
# =============================================================================

REQUEST_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # (compiled_regex, capability_key, description)
    (re.compile(r"(?i)parse.*csv|csv.*parse", re.IGNORECASE), "csv-parsing", "CSV parsing"),
    (re.compile(r"(?i)convert.*pdf|pdf.*convert", re.IGNORECASE), "pdf-conversion", "PDF conversion"),
    (re.compile(r"(?i)send.*email|email.*send", re.IGNORECASE), "email-sending", "Email sending"),
    (re.compile(r"(?i)create.*chart|plot.*graph|make.*chart", re.IGNORECASE), "chart-creation", "Chart creation"),
    (re.compile(r"(?i)docker.*compose|compose.*up", re.IGNORECASE), "docker-management", "Docker compose management"),
    (re.compile(r"(?i)deploy.*to|push.*prod|deploy.*prod", re.IGNORECASE), "deployment", "Deployment"),
    (re.compile(r"(?i)scrape.*web|crawl.*site|web.*scrape", re.IGNORECASE), "web-scraping", "Web scraping"),
    (re.compile(r"(?i)unit.*test|test.*unit|write.*test", re.IGNORECASE), "unit-testing", "Unit testing"),
    (re.compile(r"(?i)database.*query|sql.*query|query.*db", re.IGNORECASE), "database-operations", "Database operations"),
    (re.compile(r"(?i)api.*call|call.*api|fetch.*api|rest.*api|call.*endpoint", re.IGNORECASE), "api-integration", "API integration"),
    (re.compile(r"(?i)resize.*image|crop.*image|image.*resize|image.*crop", re.IGNORECASE), "image-processing", "Image processing"),
    (re.compile(r"(?i)merge.*pdf|split.*pdf", re.IGNORECASE), "pdf-manipulation", "PDF manipulation"),
]

# Threshold: flag as gap only if requested 3+ times
SKILL_GAP_THRESHOLD = 3

# Map capability keys to existing skill names that partially or fully cover them.
# If a user request matches a capability that has an existing skill, we still
# flag it as a gap if the user has requested 3+ times — the skill may be
# insufficient or undiscovered.
_EXISTING_SKILL_MAP: Dict[str, List[str]] = {
    "csv-parsing": ["csv-tools", "data-processing"],
    "pdf-conversion": ["pdf-tools"],
    "email-sending": ["email-tools", "notifications"],
    "chart-creation": ["visualization", "charts"],
    "docker-management": ["docker", "containers"],
    "deployment": ["devops", "ci-cd"],
    "web-scraping": ["web-tools", "crawling"],
    "unit-testing": ["testing", "qa"],
    "database-operations": ["database", "sql"],
    "api-integration": ["api", "webhooks"],
    "image-processing": ["image-tools", "media"],
    "pdf-manipulation": ["pdf-tools"],
}


# =============================================================================
# Capability normalization
# =============================================================================

_CAPABILITY_ALIASES: Dict[str, str] = {
    "csv": "csv-parsing",
    "pdf": "pdf-conversion",
    "email": "email-sending",
    "chart": "chart-creation",
    "docker": "docker-management",
    "deploy": "deployment",
    "scrape": "web-scraping",
    "web scraping": "web-scraping",
    "test": "unit-testing",
    "sql": "database-operations",
    "database": "database-operations",
    "api": "api-integration",
    "image": "image-processing",
}


def _normalize_capability(cap: str) -> str:
    """Normalize a capability string to the canonical key."""
    cap_lower = cap.lower().strip()
    return _CAPABILITY_ALIASES.get(cap_lower, cap_lower.replace(" ", "-"))


# =============================================================================
# Public API
# =============================================================================


def detect_skill_gaps(
    user_messages: List[Tuple[str, str]],  # List of (content, session_id)
    existing_skills: Dict[str, Path] | None = None,
) -> List[SkillGap]:
    """Detect missing capabilities from user request patterns.

    A capability is flagged as a gap when:
      1. The user requested it 3+ times across all sessions, AND
      2. No existing skill adequately covers it (or the skill exists but
         the user is still struggling — indicated by repeated requests).

    Args:
        user_messages: List of (message_content, session_id) tuples.
            Should contain only user-role messages.
        existing_skills: Dict mapping skill names to their Path on disk.
            Used to determine if a matching skill already exists.
            If None, skips existing-skill check.

    Returns:
        List of SkillGap objects sorted by request_count descending.
        Empty list if no gaps detected.
    """

    existing_skills = existing_skills or {}

    # Track request counts per capability
    capability_counts: Dict[str, int] = {}
    capability_sessions: Dict[str, List[str]] = {}
    capability_snippets: Dict[str, str] = {}

    for content, session_id in user_messages:
        if not content:
            continue

        content_lower = content.lower()

        for compiled_re, cap_key, cap_desc in REQUEST_PATTERNS:
            if compiled_re.search(content):
                capability_counts[cap_key] = capability_counts.get(cap_key, 0) + 1
                if cap_key not in capability_sessions:
                    capability_sessions[cap_key] = []
                if session_id not in capability_sessions[cap_key]:
                    capability_sessions[cap_key].append(session_id)
                # Store a snippet for debugging
                if cap_key not in capability_snippets:
                    capability_snippets[cap_key] = content[:100]

    gaps: List[SkillGap] = []

    for cap_key, count in capability_counts.items():
        if count < SKILL_GAP_THRESHOLD:
            continue

        # Check if an existing skill covers this capability
        existing_skill_names = _EXISTING_SKILL_MAP.get(cap_key, [])
        matched_skill: str | None = None

        if existing_skills:
            for skill_name in existing_skill_names:
                if skill_name in existing_skills:
                    matched_skill = skill_name
                    break

        # Confidence: higher when more requests, lower when skill exists
        base_confidence = min(0.5 + (count * 0.1), 0.95)
        if matched_skill:
            # Skill exists but user still struggles — lower confidence in "missing"
            confidence = base_confidence * 0.7
        else:
            confidence = base_confidence

        gaps.append(
            SkillGap(
                capability=cap_key,
                request_count=count,
                session_ids=capability_sessions[cap_key],
                confidence=round(confidence, 2),
                existing_skill=matched_skill,
            )
        )

    # Sort by request count descending
    gaps.sort(key=lambda g: g.request_count, reverse=True)

    return gaps


def get_request_count_for_capability(
    user_messages: List[Tuple[str, str]],
    capability: str,
) -> int:
    """Count how many times a specific capability was requested.

    Args:
        user_messages: List of (message_content, session_id) tuples.
        capability: Capability key (e.g. "csv-parsing") or alias.

    Returns:
        Number of matching requests.
    """

    cap_key = _normalize_capability(capability)
    count = 0

    for content, _session_id in user_messages:
        if not content:
            continue
        for compiled_re, key, _desc in REQUEST_PATTERNS:
            if key == cap_key and compiled_re.search(content):
                count += 1
                break  # Count once per message

    return count
