"""Host-specific Borg priming candidates for agents.

The optimizer target here is not pack content; it is the tiny rule block that
makes agents call Borg at the right time and close the outcome loop.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_HOST_LABELS = {
    "claude-code": "Claude Code",
    "codex": "Codex CLI",
    "cursor": "Cursor",
    "hermes": "Hermes Agent",
    "generic": "generic agent",
}
_REQUIRED_TERMS = ("borg_observe", "error_lookup", "NO_CONFIDENT_MATCH", "borg_record_outcome", "VERIFY")
_FLAG_OVERCLAIM_RE = re.compile(r"(?i)([\"']?(first[_-]?10[_-]?claim|global[_-]?promotion[_-]?allowed|public[_-]?lift[_-]?claim)[\"']?\s*[:=]\s*(true|yes|1))")
_NATURAL_OVERCLAIM_RE = re.compile(r"(?i)(borg\s+(has\s+)?(proven|verified|achieved)\s+first[-_\s]?10\s+lift|public\s+lift\s+(is\s+)?(proven|verified|achieved)|global\s+promotion\s+(is\s+)?(approved|allowed|ready))")
_UNSAFE_TRUST_RE = re.compile(r"(?i)(always\s+trust\s+borg|skip\s+verify|do\s+not\s+verify|ignore\s+verification)")


def _sha256_ref(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _normalize_host(host: str) -> str:
    value = str(host or "generic").strip().lower().replace("_", "-")
    return value if value in _HOST_LABELS else "generic"


def score_agent_priming(prompt: str) -> dict[str, Any]:
    """Score whether a priming block teaches the right Borg interaction loop."""
    text = str(prompt or "")
    lowered = text.lower()
    missing = [term for term in _REQUIRED_TERMS if term.lower() not in lowered]
    hard_failures: list[str] = []
    if _FLAG_OVERCLAIM_RE.search(text) or _NATURAL_OVERCLAIM_RE.search(text):
        hard_failures.append("overclaim")
    if _UNSAFE_TRUST_RE.search(text):
        hard_failures.append("unsafe_trust_instruction")
    if missing:
        hard_failures.append("missing_required_call_rules")
    score = 0.0 if hard_failures else 1.0
    return {
        "schema_version": "1.0",
        "score": score,
        "required_terms_present": sorted(set(_REQUIRED_TERMS) - set(missing)),
        "missing_terms": missing,
        "hard_failures": hard_failures,
    }


def build_agent_priming_candidate(host: str = "generic") -> dict[str, Any]:
    """Return a host-specific priming artifact for maintainer review/export."""
    normalized = _normalize_host(host)
    label = _HOST_LABELS[normalized]
    prompt = (
        f"Borg interaction rule for {label}:\n"
        "- At the start of technical debug/test/review/deploy work, call `borg_observe` once with the exact task and tech context.\n"
        "- When there is a concrete error, failing command, stack trace, or repeated failure, call `error_lookup` / `borg_rescue` with the exact text before changing code.\n"
        "- If Borg returns `NO_CONFIDENT_MATCH`, say that plainly; do not blend weak retrieval into the answer or pretend Borg helped.\n"
        "- Follow Borg's `ACTION`, avoid `STOP`, then rerun the exact `VERIFY` command/test.\n"
        "- after VERIFY, call `borg_record_outcome` with the intervention_id, outcome, helpful, verified, and verification evidence so Borg learns.\n"
        "- Borg guidance is advisory until verified; never claim first-10 lift, public lift, or global promotion from this local priming block.\n"
    )
    score = score_agent_priming(prompt)
    artifact = {
        "schema_version": "1.0",
        "host": normalized,
        "host_label": label,
        "prompt": prompt,
        "prompt_sha256": _sha256_ref(prompt),
        "call_rules": {
            "task_start_debug_test_review": "borg_observe",
            "concrete_error": "error_lookup",
            "weak_match": "NO_CONFIDENT_MATCH",
            "after_verify": "borg_record_outcome",
        },
        "score": score,
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
    }
    # Make accidental future edits fail closed if they weaken the loop.
    if score["hard_failures"]:
        artifact["recommendation"] = "blocked"
    else:
        artifact["recommendation"] = "eligible_for_host_rules_review"
    return artifact


def render_agent_priming(host: str = "generic") -> str:
    return build_agent_priming_candidate(host)["prompt"]


def dumps_agent_priming(host: str = "generic") -> str:
    return json.dumps(build_agent_priming_candidate(host), indent=2, sort_keys=True, ensure_ascii=False)
