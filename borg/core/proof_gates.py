"""
Guild Proof Gates Module (T1.5) — standalone proof-gate validation for guild packs.

Responsibilities:
  - validate_proof_gates()         — gate validation on workflow_pack and feedback artifacts
  - compute_pack_tier()            — CORE / VALIDATED / COMMUNITY trust tier
  - compute_pack_tier_from_index()  — tier from a flat index.json entry
  - check_confidence_decay()       — age-based confidence downgrade

Zero imports from tools.* or guild_mcp.* — stdlib + yaml only.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CONFIDENCE = {"guessed", "inferred", "tested", "validated"}
TRUST_TIERS = ("CORE", "VALIDATED", "COMMUNITY")

# Confidence decay TTLs (days before confidence level degrades)
CONFIDENCE_TTL_DAYS = {
    "validated": 365,
    "tested": 180,
    "inferred": 90,
    "guessed": 30,
}

# Downgrade chain for confidence decay
_CONFIDENCE_DOWNGRADE = {
    "validated": "tested",
    "tested": "inferred",
    "inferred": "guessed",
    "guessed": "expired",
}

# Required top-level fields on a workflow_pack artifact.
# Accepts either V1 ``phases`` or V2 ``structure`` (mutually exclusive).
_REQUIRED_PACK_FIELDS_COMMON = {"type", "version", "id", "problem_class", "mental_model", "provenance"}
_REQUIRED_PACK_FIELDS_V1 = _REQUIRED_PACK_FIELDS_COMMON | {"phases"}
_REQUIRED_PACK_FIELDS_V2 = _REQUIRED_PACK_FIELDS_COMMON | {"structure"}

# Backward-compatibility alias (tests import this name directly)
_REQUIRED_PACK_FIELDS = _REQUIRED_PACK_FIELDS_V1


# ---------------------------------------------------------------------------
# Proof-gate validation
# ---------------------------------------------------------------------------

def validate_proof_gates(artifact: dict) -> List[str]:
    """Validate proof gates on any artifact type (workflow_pack or feedback).

    Returns a list of error strings. Empty list means the artifact passes
    all proof gates.

    Confidence-level field requirements (per design doc T1.5):
      guessed    — provenance.author, provenance.created, provenance.confidence,
                   provenance.failure_cases >= 1
      inferred   — guessed + provenance.evidence (non-empty string)
      tested     — inferred + examples >= 1 (each with problem, solution, outcome)
                   + feedback from a different agent
      validated  — examples >= 2 from independent agents + evaluator_rubric
                   + 3+ distinct operators

    Args:
        artifact: Parsed guild artifact dict (YAML mapping).

    Returns:
        List of human-readable error messages. Empty list = pass.
    """
    errors: List[str] = []
    artifact_type = artifact.get("type", "unknown")

    if artifact_type == "workflow_pack":
        errors.extend(_validate_workflow_pack_gates(artifact))

    elif artifact_type == "feedback":
        errors.extend(_validate_feedback_gates(artifact))

    else:
        errors.append(f"Unknown artifact type: {artifact_type}")

    return errors


def _validate_workflow_pack_gates(pack: dict) -> List[str]:
    """Run proof-gate validation for a workflow_pack artifact."""
    errors: List[str] = []
    provenance = pack.get("provenance", {})

    # provenance must be a mapping
    if not isinstance(provenance, dict):
        errors.append("provenance must be a mapping")
        return errors

    # ---- Core provenance fields ----
    # Accept either 'author' or 'author_agent' field
    if not provenance.get("author") and not provenance.get("author_agent"):
        errors.append("Missing provenance.author or provenance.author_agent")

    if not provenance.get("created"):
        errors.append("Missing provenance.created")

    confidence = provenance.get("confidence", "")
    if not confidence:
        errors.append("Missing provenance.confidence")
    elif confidence not in VALID_CONFIDENCE:
        errors.append(
            f"Invalid provenance.confidence '{confidence}' — "
            f"must be one of: {', '.join(sorted(VALID_CONFIDENCE))}"
        )

    failure_cases = provenance.get("failure_cases")
    if failure_cases is None:
        errors.append("Missing provenance.failure_cases")
    elif not isinstance(failure_cases, list):
        errors.append("provenance.failure_cases must be a list")
    elif len(failure_cases) < 1:
        errors.append("provenance.failure_cases must have at least 1 entry")

    # ---- Tiered requirements ----
    if confidence == "inferred":
        if not provenance.get("evidence"):
            errors.append(
                "Missing provenance.evidence — required for 'inferred' confidence"
            )

    elif confidence == "tested":
        if not provenance.get("evidence"):
            errors.append(
                "Missing provenance.evidence — required for 'tested' confidence"
            )
        examples = pack.get("examples")
        if not examples or not isinstance(examples, list) or len(examples) < 1:
            errors.append(
                "Missing or too few examples — 'tested' requires at least 1 "
                "(each with problem, solution, outcome)"
            )
        else:
            for i, ex in enumerate(examples):
                if not isinstance(ex, dict):
                    errors.append(f"examples[{i}] must be a mapping")
                    continue
                for field in ("problem", "solution", "outcome"):
                    if not ex.get(field):
                        errors.append(
                            f"examples[{i}] missing '{field}' — required for "
                            "tested-level example"
                        )
        if not pack.get("feedback_agent"):
            errors.append(
                "Missing feedback_agent — 'tested' requires feedback "
                "from a different agent"
            )

    elif confidence == "validated":
        if not provenance.get("evidence"):
            errors.append(
                "Missing provenance.evidence — required for 'validated' confidence"
            )
        examples = pack.get("examples")
        if not examples or not isinstance(examples, list) or len(examples) < 2:
            errors.append(
                "Too few examples — 'validated' requires at least 2 examples "
                "from independent agents"
            )
        else:
            seen_agents = set()
            for i, ex in enumerate(examples):
                if not isinstance(ex, dict):
                    errors.append(f"examples[{i}] must be a mapping")
                    continue
                for field in ("problem", "solution", "outcome"):
                    if not ex.get(field):
                        errors.append(
                            f"examples[{i}] missing '{field}' — required for "
                            "validated-level example"
                        )
                agent = ex.get("agent", "")
                if agent:
                    seen_agents.add(agent)
            if len(seen_agents) < 2:
                errors.append(
                    f"examples must come from >= 2 independent agents — "
                    f"found: {sorted(seen_agents) or 'none'}"
                )
        if not pack.get("evaluator_rubric"):
            errors.append(
                "Missing evaluator_rubric — 'validated' requires an evaluation rubric"
            )
        operators = pack.get("operators", [])
        if not operators or len(operators) < 3:
            errors.append(
                f"Too few operators — 'validated' requires at least 3 distinct "
                f"operators, found: {len(operators) if operators else 0}"
            )

    # ---- Required top-level fields ----
    # V2 packs use structure[], V1 packs use phases[]
    if "structure" in pack and "phases" not in pack:
        required_fields = _REQUIRED_PACK_FIELDS_V2
    else:
        required_fields = _REQUIRED_PACK_FIELDS_V1
    missing = required_fields - set(pack.keys())
    if missing:
        errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

    return errors


def _validate_feedback_gates(feedback: dict) -> List[str]:
    """Run proof-gate validation for a feedback artifact."""
    errors: List[str] = []
    provenance = feedback.get("provenance", {})

    if not isinstance(provenance, dict):
        errors.append("provenance must be a mapping")
        return errors

    if not provenance.get("confidence"):
        errors.append("Missing provenance.confidence on feedback")

    if not feedback.get("parent_artifact"):
        errors.append("Feedback must reference a parent_artifact")

    if not feedback.get("execution_log_hash"):
        errors.append("Feedback must include execution_log_hash (PRD §12)")

    return errors


# ---------------------------------------------------------------------------
# Trust-tier computation
# ---------------------------------------------------------------------------

def compute_pack_tier(pack: dict) -> str:
    """Determine the trust tier for a guild pack.

    Returns one of: 'CORE', 'VALIDATED', 'COMMUNITY'.

      CORE      — confidence='validated'
                  AND provenance.author_agent starts with 'agent://hermes'
                  AND has 3+ failure_cases
                  AND (examples field absent OR examples non-empty)
      VALIDATED — confidence in ('tested', 'validated')
                  AND has evidence
                  AND has 1+ failure_cases
      COMMUNITY — everything else
    """
    provenance = pack.get("provenance") or {}
    confidence = provenance.get("confidence", "")
    author_agent = provenance.get("author_agent", "")
    evidence = provenance.get("evidence", "")
    failure_cases = provenance.get("failure_cases") or []
    examples = pack.get("examples")  # may not exist at all

    # CORE tier
    if (
        confidence == "validated"
        and isinstance(author_agent, str)
        and author_agent.startswith("agent://hermes")
        and isinstance(failure_cases, list)
        and len(failure_cases) >= 3
    ):
        if examples is not None:
            if not examples:
                pass  # fall through — examples exists but empty
            else:
                return "CORE"
        else:
            # examples field doesn't exist — OK for CORE
            return "CORE"

    # VALIDATED tier
    if (
        confidence in ("tested", "validated")
        and evidence
        and isinstance(failure_cases, list)
        and len(failure_cases) >= 1
    ):
        return "VALIDATED"

    return "COMMUNITY"


def compute_pack_tier_from_index(index_entry: dict) -> str:
    """Compute trust tier from an index.json entry (flat structure).

    Index entries have confidence/evidence/failure_cases at top level,
    not nested under provenance. This function adapts the flat entry
    into the format compute_pack_tier expects.
    """
    pseudo_pack: dict = {
        "provenance": {
            "confidence": index_entry.get("confidence", ""),
            "author_agent": index_entry.get("author_agent", ""),
            "evidence": index_entry.get("evidence", ""),
            "failure_cases": index_entry.get("failure_cases", []),
        },
    }
    if "examples" in index_entry:
        pseudo_pack["examples"] = index_entry["examples"]
    return compute_pack_tier(pseudo_pack)


# ---------------------------------------------------------------------------
# Confidence decay
# ---------------------------------------------------------------------------

def check_confidence_decay(pack: dict) -> dict:
    """Check if a pack's confidence has decayed based on age.

    Reads provenance.created, computes age in days, and downgrades
    confidence if the TTL for the current level has been exceeded.

    TTL ladder (days):
      validated → 365
      tested    → 180
      inferred  →  90
      guessed   →  30

    Returns dict with keys:
      confidence, original_confidence, decayed, age_days, warning
    """
    provenance = pack.get("provenance") or {}
    original_confidence = provenance.get("confidence", "guessed")
    created = provenance.get("created")

    if not created:
        return {
            "confidence": original_confidence,
            "original_confidence": original_confidence,
            "decayed": False,
            "age_days": -1,
            "warning": "No created timestamp in provenance — cannot verify freshness.",
        }

    try:
        created_dt = datetime.fromisoformat(created)
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - created_dt).days
    except (ValueError, TypeError):
        return {
            "confidence": original_confidence,
            "original_confidence": original_confidence,
            "decayed": False,
            "age_days": -1,
            "warning": f"Invalid created timestamp: {created}",
        }

    current = original_confidence
    ttl = CONFIDENCE_TTL_DAYS.get(current)
    if ttl is not None and age_days > ttl:
        current = _CONFIDENCE_DOWNGRADE.get(current, "expired")
        warning = (
            f"This pack was {original_confidence} {age_days} days ago. "
            f"Confidence decayed from {original_confidence} to {current}. "
            f"Recent feedback would restore it."
        )
        return {
            "confidence": current,
            "original_confidence": original_confidence,
            "decayed": True,
            "age_days": age_days,
            "warning": warning,
        }

    return {
        "confidence": original_confidence,
        "original_confidence": original_confidence,
        "decayed": False,
        "age_days": age_days,
        "warning": "",
    }
