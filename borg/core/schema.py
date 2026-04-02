"""
Guild Schema Module — pack parsing, validation, and field extraction.

Zero imports from tools.* or guild_mcp.* — stdlib + yaml only.

Functions:
    parse_workflow_pack  -- Parse YAML text into a validated workflow pack dict
    validate_pack        -- Validate proof gates on a parsed pack; return error list
    collect_text_fields  -- Extract all text fields that influence agent behavior
    parse_skill_frontmatter -- Parse YAML frontmatter and body from a SKILL.md file
    sections_to_phases   -- Split markdown body on ## headers into phases
"""

import re
from typing import Any, Dict, List, Tuple

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CONFIDENCE = {"guessed", "inferred", "tested", "validated"}

# Fields required for workflow_pack type
_WORKFLOW_PACK_REQUIRED_FIELDS_V1 = frozenset({
    "type",
    "version",
    "id",
    "problem_class",
    "mental_model",
    "phases",
    "provenance",
})

_WORKFLOW_PACK_REQUIRED_FIELDS_V2 = frozenset({
    "type",
    "version",
    "id",
    "problem_class",
    "mental_model",
    "structure",
    "provenance",
})

# Fields required for critique_rubric type
_CRITIQUE_RUBRIC_REQUIRED_FIELDS = frozenset({
    "type",
    "version",
    "id",
    "criteria",
    "provenance",
})

# Required fields are type-dependent
_REQUIRED_PACK_FIELDS = frozenset({
    "type",
    "version",
    "id",
    "provenance",
})


# ---------------------------------------------------------------------------
# Pack parsing
# ---------------------------------------------------------------------------

def parse_workflow_pack(yaml_text: str) -> dict:
    """Parse YAML text into a workflow pack dict with schema validation.

    Args:
        yaml_text: Raw YAML string representing a guild workflow pack.

    Returns:
        A validated pack dictionary.

    Raises:
        ValueError: If the YAML is invalid, not a mapping, or missing required fields.
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ValueError("Invalid YAML: expected a mapping at top level")

    # Select type-specific required fields; V2 packs use structure[] instead of phases[]
    pack_type = data.get("type", "")
    if pack_type == "workflow_pack":
        if "structure" in data and "phases" not in data:
            required_fields = _WORKFLOW_PACK_REQUIRED_FIELDS_V2
        else:
            required_fields = _WORKFLOW_PACK_REQUIRED_FIELDS_V1
    elif pack_type == "critique_rubric":
        required_fields = _CRITIQUE_RUBRIC_REQUIRED_FIELDS
    else:
        required_fields = _REQUIRED_PACK_FIELDS

    missing = required_fields - set(data.keys())
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

    return data


# ---------------------------------------------------------------------------
# Pack validation (proof gates)
# ---------------------------------------------------------------------------

def validate_pack(pack: dict) -> List[str]:
    """Validate proof gates on a parsed pack.

    Checks that provenance block is well-formed, confidence is valid,
    failure cases are present, and required_inputs / escalation_rules
    are non-empty lists.

    Args:
        pack: A parsed guild pack dictionary.

    Returns:
        A list of error description strings. Empty list means the pack
        passes all proof gates.
    """
    errors: List[str] = []
    provenance = pack.get("provenance", {})

    if not isinstance(provenance, dict):
        errors.append("Provenance must be a mapping")
        return errors

    if "evidence" not in provenance or not provenance.get("evidence"):
        errors.append(
            "Missing provenance.evidence — proof gate requires evidence"
        )

    confidence = provenance.get("confidence")
    if not confidence:
        errors.append(
            "Missing provenance.confidence — "
            "must be one of: guessed, inferred, tested, validated"
        )
    elif confidence not in VALID_CONFIDENCE:
        errors.append(
            f"Invalid provenance.confidence '{confidence}' — "
            f"must be one of: {', '.join(sorted(VALID_CONFIDENCE))}"
        )

    if "failure_cases" not in provenance:
        errors.append(
            "Missing provenance.failure_cases — "
            "proof gate requires known failure cases"
        )

    # required_inputs and escalation_rules only apply to workflow_pack types.
    # critique_rubric packs use 'criteria' instead of 'phases' and have no
    # required_inputs/escalation_rules.
    pack_type = pack.get("type", "")
    if pack_type == "workflow_pack":
        required_inputs = pack.get("required_inputs")
        if (
            not required_inputs
            or not isinstance(required_inputs, list)
            or len(required_inputs) < 1
        ):
            errors.append(
                "Missing or empty required_inputs — "
                "at least 1 required input must be specified"
            )

        escalation_rules = pack.get("escalation_rules")
        if (
            not escalation_rules
            or not isinstance(escalation_rules, list)
            or len(escalation_rules) < 1
        ):
            errors.append(
                "Missing or empty escalation_rules — "
                "at least 1 escalation rule must be specified"
            )

    return errors


# ---------------------------------------------------------------------------
# Text field collection
# ---------------------------------------------------------------------------

def collect_text_fields(pack: dict) -> List[str]:
    """Extract all text fields that influence agent behavior from a pack.

    Collects strings from: mental_model, phase descriptions, checkpoints,
    prompts, anti_patterns, escalation_rules, and required_inputs.

    Args:
        pack: A parsed guild pack dictionary.

    Returns:
        A flat list of string values found in behavior-influencing fields.
    """
    texts: List[str] = []

    if pack.get("mental_model"):
        texts.append(str(pack["mental_model"]))

    for phase in pack.get("phases", []):
        if isinstance(phase, dict):
            if phase.get("description"):
                texts.append(str(phase["description"]))
            if phase.get("checkpoint"):
                texts.append(str(phase["checkpoint"]))
            for prompt in phase.get("prompts", []) or []:
                texts.append(str(prompt))
            for ap in phase.get("anti_patterns", []) or []:
                texts.append(str(ap))
            for cp in phase.get("context_prompts", []) or []:
                if isinstance(cp, dict) and cp.get("prompt"):
                    texts.append(str(cp["prompt"]))
                elif isinstance(cp, str):
                    texts.append(cp)

    for rule in pack.get("escalation_rules", []) or []:
        texts.append(str(rule))

    for inp in pack.get("required_inputs", []) or []:
        texts.append(str(inp))

    return texts


# ---------------------------------------------------------------------------
# Skill frontmatter parsing
# ---------------------------------------------------------------------------

def parse_skill_frontmatter(text: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter and body from a SKILL.md file.

    Handles the --- delimited YAML frontmatter block at the top of a
    SKILL.md file, returning the parsed frontmatter dict and the
    remaining body text.

    Args:
        text: Raw text content of a SKILL.md file.

    Returns:
        A tuple of (frontmatter_dict, body_str). If no frontmatter is
        present, returns ({}, text).
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        frontmatter = {}

    body = parts[2].strip()
    return frontmatter, body


# ---------------------------------------------------------------------------
# Markdown sections to phases
# ---------------------------------------------------------------------------

_META_PATTERNS = frozenset({
    "overview",
    "when_to_use",
    "quick_reference",
    "common_rationalizations",
    "real_world_impact",
    "integration",
    "pitfalls",
    "known_issues",
    "references",
    "required_inputs",
    "escalation",
    "examples",
    "provenance",
})


def sections_to_phases(body: str) -> List[dict]:
    """Split a markdown body on ## headers into phases.

    Each top-level ``## Section Name`` heading becomes a phase entry.
    Sections whose slug matches known meta-patterns (e.g. "overview",
    "references") are skipped, as they represent reference/context
    rather than workflow steps.

    Args:
        body: The markdown body text (without frontmatter).

    Returns:
        A list of phase dictionaries, each containing name, description,
        checkpoint (empty string), anti_patterns (empty list), and prompts
        (empty list).
    """
    phases: List[dict] = []
    current_name: str | None = None
    current_lines: List[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_name is not None:
                slug = re.sub(r"[^a-z0-9_]", "_", current_name.lower().strip())
                if slug not in _META_PATTERNS:
                    phases.append(
                        {
                            "name": slug,
                            "description": "\n".join(current_lines).strip(),
                            "checkpoint": "",
                            "anti_patterns": [],
                            "prompts": [],
                        }
                    )
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_name is not None:
        slug = re.sub(r"[^a-z0-9_]", "_", current_name.lower().strip())
        if slug not in _META_PATTERNS:
            phases.append(
                {
                    "name": slug,
                    "description": "\n".join(current_lines).strip(),
                    "checkpoint": "",
                    "anti_patterns": [],
                    "prompts": [],
                }
            )

    return phases
