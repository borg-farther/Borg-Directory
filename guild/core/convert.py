"""
Guild Convert Module — convert CLAUDE.md, .cursorrules, and SKILL.md
files into guild workflow packs.

Zero imports from tools.* or guild_mcp.* — stdlib + yaml only.

Functions:
    convert_skill      — SKILL.md (YAML frontmatter + markdown body)
    convert_claude_md  — CLAUDE.md (plain markdown with rules)
    convert_cursorrules — .cursorrules (markdown or JSON)
    convert_auto       — auto-detect format from filename
"""

import json
import os
import re
from typing import Any, Dict, List, Tuple

import yaml

from guild.core.schema import parse_skill_frontmatter, sections_to_phases


# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

_ANTI_PATTERN_RE = re.compile(
    r"(?i)\b(don't|do\s+not|never|avoid|don'ts|avoid\s+these)\b",
    re.IGNORECASE,
)

_TOOL_CONTEXT_RE = re.compile(
    r"(?i)\b(using|with|via)\s+(tool|context|file|function|api)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
)

_DEFAULT_PACK = {
    "type": "workflow_pack",
    "version": "1.0.0",
    "problem_class": "converted",
    "mental_model": "",
    "required_inputs": [],
    "escalation_rules": ["Escalate on ambiguous or missing information."],
}


# --------------------------------------------------------------------------
# Skill converter
# --------------------------------------------------------------------------

def convert_skill(path: str) -> dict:
    """Convert a SKILL.md file into a workflow pack dict.

    Args:
        path: Path to a SKILL.md file with YAML frontmatter and markdown body.

    Returns:
        A dict representing a guild workflow pack, suitable for yaml.dump().
    """
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    frontmatter, body = parse_skill_frontmatter(text)
    phases = sections_to_phases(body)

    pack = _build_pack(
        name=frontmatter.get("name", os.path.splitext(os.path.basename(path))[0]),
        description=frontmatter.get("description", ""),
        tags=frontmatter.get("tags", []),
        phases=phases,
        provenance=frontmatter,
    )

    return pack


# --------------------------------------------------------------------------
# CLAUDE.md converter
# --------------------------------------------------------------------------

def convert_claude_md(path: str) -> dict:
    """Convert a CLAUDE.md file into a workflow pack dict.

    Args:
        path: Path to a CLAUDE.md file (plain markdown with instructions/rules).

    Returns:
        A dict representing a guild workflow pack, suitable for yaml.dump().
    """
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    return _convert_markdown(path, text)


# --------------------------------------------------------------------------
# .cursorrules converter
# --------------------------------------------------------------------------

def convert_cursorrules(path: str) -> dict:
    """Convert a .cursorrules file into a workflow pack dict.

    Args:
        path: Path to a .cursorrules file (markdown or JSON format).

    Returns:
        A dict representing a guild workflow pack, suitable for yaml.dump().
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    # Try JSON first
    try:
        data = json.loads(raw)
        return _convert_json_cursorrules(path, data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fall back to markdown path
    return _convert_markdown(path, raw)


# --------------------------------------------------------------------------
# Auto-detect converter
# --------------------------------------------------------------------------

def convert_auto(path: str) -> dict:
    """Auto-detect format from filename and call the appropriate converter.

    Args:
        path: Path to a file. Detects SKILL.md, CLAUDE.md, or .cursorrules.
              Handles both bare filenames and full paths (e.g. /path/to/SKILL.md).

    Returns:
        A dict representing a guild workflow pack.

    Raises:
        ValueError: If the file format cannot be determined.
    """
    basename = os.path.basename(path)
    basename_lower = basename.lower()

    if basename_lower == "skill.md" or basename_lower.endswith("/skill.md"):
        return convert_skill(path)
    elif basename_lower == "claude.md" or basename_lower.endswith("/claude.md"):
        return convert_claude_md(path)
    elif ".cursorrules" in basename_lower:
        return convert_cursorrules(path)
    else:
        raise ValueError(
            f"Cannot auto-detect format for '{basename}'. "
            "Expected SKILL.md, CLAUDE.md, or a .cursorrules file."
        )


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

def _convert_markdown(path: str, text: str) -> dict:
    """Shared markdown-to-pack conversion for CLAUDE.md and plain .cursorrules.

    Extracts:
        - mental_model: first non-## paragraph or description section
        - phases: ## headers -> phase entries
        - anti_patterns: lines matching "don't/avoid/never"
        - required_inputs: tool/context references
    """
    lines = text.split("\n")

    mental_model = _extract_mental_model(lines)
    phases = _extract_phases_from_lines(lines)
    anti_patterns = _extract_anti_patterns(lines)
    required_inputs = _extract_required_inputs(text)

    pack = _build_pack(
        name=os.path.splitext(os.path.basename(path))[0],
        description=mental_model,
        phases=phases,
        provenance={},
    )

    # Attach anti_patterns and required_inputs
    if anti_patterns:
        for phase in pack["phases"]:
            phase.setdefault("anti_patterns", []).extend(anti_patterns)
    if required_inputs:
        pack["required_inputs"] = required_inputs

    return pack


def _convert_json_cursorrules(path: str, data: dict) -> dict:
    """Convert a JSON-format .cursorrules file into a workflow pack."""
    name = data.get("name", os.path.splitext(os.path.basename(path))[0])
    description = data.get("description", "")
    phases_data = data.get("phases", [])

    phases = []
    for p in phases_data:
        if isinstance(p, dict):
            phases.append({
                "name": p.get("name", "phase"),
                "description": p.get("description", ""),
                "checkpoint": p.get("checkpoint", ""),
                "anti_patterns": p.get("anti_patterns", []),
                "prompts": p.get("prompts", []),
            })
        else:
            phases.append({
                "name": str(p),
                "description": "",
                "checkpoint": "",
                "anti_patterns": [],
                "prompts": [],
            })

    pack = _build_pack(
        name=name,
        description=description,
        phases=phases,
        provenance={},
    )

    if "required_inputs" in data:
        pack["required_inputs"] = data["required_inputs"]
    if "escalation_rules" in data:
        pack["escalation_rules"] = data["escalation_rules"]

    return pack


def _extract_mental_model(lines: List[str]) -> str:
    """Extract mental_model from description/overview sections or first paragraph."""
    capture = False
    description_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        # Stop at first ## header after capturing description
        if stripped.startswith("## "):
            if capture:
                break
            lower = stripped.lower()
            if any(kw in lower for kw in ("description", "overview", "purpose", "intent")):
                capture = True
            continue
        if capture:
            if stripped:
                description_lines.append(stripped)
            elif description_lines:
                # Blank line after content ends the block
                break

    if description_lines:
        return " ".join(description_lines)

    # Fall back to first non-empty, non-header line
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped

    return ""


def _extract_phases_from_lines(lines: List[str]) -> List[dict]:
    """Convert ## headers in lines to phase entries using sections_to_phases."""
    # Reconstruct body from lines for sections_to_phases
    body = "\n".join(lines)
    return sections_to_phases(body)


def _extract_anti_patterns(lines: List[str]) -> List[str]:
    """Extract anti-patterns from lines containing 'don't/avoid/never'."""
    patterns: List[str] = []
    for line in lines:
        stripped = line.strip()
        if _ANTI_PATTERN_RE.search(stripped) and not stripped.startswith("#"):
            # Clean up the line
            cleaned = re.sub(r"^[\s\-\*\>]+", "", stripped).strip()
            if cleaned:
                patterns.append(cleaned)
    return patterns


def _extract_required_inputs(text: str) -> List[str]:
    """Extract required_inputs from tool/context references in text."""
    inputs: List[str] = []
    for match in _TOOL_CONTEXT_RE.finditer(text):
        inputs.append(match.group(3))
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for inp in inputs:
        if inp not in seen:
            seen.add(inp)
            unique.append(inp)
    return unique


def _build_pack(
    name: str,
    description: str,
    phases: List[dict],
    provenance: dict,
    tags: List[str] = None,
) -> dict:
    """Build a complete workflow pack dict with required fields."""
    slug = re.sub(r"[^a-zA-Z0-9]", "_", name.lower().strip())
    if not slug:
        slug = "converted"

    pack: Dict[str, Any] = {
        **_DEFAULT_PACK,
        "id": f"guild://converted/{slug}",
        "problem_class": description or "Converted workflow",
        "mental_model": description,
        "phases": phases if phases else [_empty_phase("default")],
        "provenance": {
            "author_agent": "convert://tool",
            "evidence": f"Converted from {name}",
            "confidence": provenance.get("confidence", "inferred"),
            "failure_cases": provenance.get("failure_cases", []),
        },
    }

    if tags:
        pack["tags"] = tags

    return pack


def _empty_phase(name: str) -> dict:
    return {
        "name": name,
        "description": "",
        "checkpoint": "",
        "anti_patterns": [],
        "prompts": [],
    }