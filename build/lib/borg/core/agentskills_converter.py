"""
Borg ↔ AgentSkills.io Converter — converts between borg workflow packs
and the agentskills.io skill format.

agentskills.io format: folders containing SKILL.md (YAML frontmatter +
markdown body), optionally scripts/, references/, assets/.

Exports:
    pack_to_agentskills    -- convert a borg pack to an agentskills.io skill directory
    agentskills_to_pack    -- convert an agentskills.io skill directory to a borg pack
    pack_to_agentskills_md -- convert a borg pack to SKILL.md markdown string
    agentskills_md_to_pack -- parse SKILL.md content into a borg pack dict
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from borg.core.schema import parse_skill_frontmatter, sections_to_phases


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# agentskills.io name validation: lowercase, numbers, hyphens; max 64 chars; no leading/trailing hyphens
_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_MAX_NAME_LEN = 64
_MAX_DESC_LEN = 1024
_MAX_COMPAT_LEN = 500

# borg pack type identifier
PACK_TYPE = "workflow_pack"
PACK_VERSION = "1.0.0"

# agentskills.io metadata key used to store borg provenance
_BORG_PROVENANCE_KEY = "borg_provenance"


# ---------------------------------------------------------------------------
# Public API — Directory-level conversion
# ---------------------------------------------------------------------------

def pack_to_agentskills(
    pack: dict,
    output_dir: Path,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Convert a borg workflow pack to an agentskills.io skill directory.

    Creates:
        output_dir/
            SKILL.md           ← YAML frontmatter + full markdown body
            references/        ← contains provenance, phases as structured docs
                provenance.md   ← borg provenance metadata
                phases/         ← one markdown file per phase

    Args:
        pack: A parsed borg workflow pack dict.
        output_dir: Target directory for the agentskills.io skill.
        overwrite: If True, overwrite existing files.

    Returns:
        Dict with keys: success (bool), files_created (list),
        total_size_bytes (int), output_dir (str).
    """
    output_dir = Path(output_dir)
    refs_dir = output_dir / "references"
    phases_dir = refs_dir / "phases"
    refs_dir.mkdir(parents=True, exist_ok=True)
    phases_dir.mkdir(parents=True, exist_ok=True)

    files_created: List[str] = []
    total_size = 0

    # SKILL.md
    skill_path = output_dir / "SKILL.md"
    if skill_path.exists() and not overwrite:
        raise FileExistsError(f"SKILL.md already exists at {skill_path}")
    skill_md = pack_to_agentskills_md(pack)
    skill_path.write_text(skill_md, encoding="utf-8")
    files_created.append("SKILL.md")
    total_size += len(skill_md.encode("utf-8"))

    # references/provenance.md
    prov_path = refs_dir / "provenance.md"
    prov_md = _provenance_to_md(pack.get("provenance", {}))
    prov_path.write_text(prov_md, encoding="utf-8")
    files_created.append("references/provenance.md")
    total_size += len(prov_md.encode("utf-8"))

    # references/phases/*.md
    phases = pack.get("phases", [])
    for i, phase in enumerate(phases):
        phase_slug = phase.get("name", f"phase-{i+1}").replace(" ", "-").lower()
        # Ensure valid filename chars
        phase_slug = re.sub(r"[^a-z0-9_-]", "", phase_slug)
        phase_path = phases_dir / f"{phase_slug}.md"
        phase_md = _phase_to_md(phase, i + 1)
        phase_path.write_text(phase_md, encoding="utf-8")
        rel_path = f"references/phases/{phase_slug}.md"
        files_created.append(rel_path)
        total_size += len(phase_md.encode("utf-8"))

    return {
        "success": True,
        "files_created": files_created,
        "total_phases": len(phases),
        "total_size_bytes": total_size,
        "output_dir": str(output_dir),
    }


def agentskills_to_pack(skill_dir: Path) -> dict:
    """Convert an agentskills.io skill directory to a borg workflow pack.

    Reads SKILL.md and references/ directory to reconstruct a full borg pack.

    Args:
        skill_dir: Path to an agentskills.io skill directory containing SKILL.md.

    Returns:
        A borg workflow pack dict.

    Raises:
        FileNotFoundError: If SKILL.md does not exist in skill_dir.
        ValueError: If SKILL.md frontmatter is invalid.
    """
    skill_dir = Path(skill_dir)
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

    text = skill_path.read_text(encoding="utf-8")
    return agentskills_md_to_pack(text)


# ---------------------------------------------------------------------------
# Public API — SKILL.md string-level conversion
# ---------------------------------------------------------------------------

def pack_to_agentskills_md(pack: dict) -> str:
    """Convert a borg workflow pack to a SKILL.md markdown string.

    Produces a SKILL.md file conforming to the agentskills.io specification:
    - YAML frontmatter: name, description, optional license/compatibility/metadata
    - Markdown body: ## Overview, ## When to Use, ## Available Packs / Phases,
      ## Escalation, ## Provenance

    Args:
        pack: A parsed borg workflow pack dict.

    Returns:
        A complete SKILL.md string with YAML frontmatter and markdown body.
    """
    frontmatter, body_md = _pack_to_frontmatter_and_body(pack)
    fm_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    return f"---\n{fm_text}\n---\n{body_md}"


def agentskills_md_to_pack(text: str) -> dict:
    """Parse an agentskills.io SKILL.md string into a borg workflow pack dict.

    Args:
        text: Raw text content of a SKILL.md file.

    Returns:
        A borg workflow pack dict with all available metadata.

    Raises:
        ValueError: If the frontmatter is invalid or name is missing.
    """
    frontmatter, body = parse_skill_frontmatter(text)

    name = frontmatter.get("name", "")
    if not name:
        raise ValueError("SKILL.md frontmatter must include a 'name' field")

    _validate_name(name)
    description = frontmatter.get("description", "")
    if description and len(description) > _MAX_DESC_LEN:
        raise ValueError(f"description must be <= {_MAX_DESC_LEN} chars, got {len(description)}")

    pack_id = frontmatter.get("id") or f"agentskills://{name}"

    # Restore borg provenance if stored in metadata
    meta = frontmatter.get("metadata", {}) or {}
    borg_prov = meta.get(_BORG_PROVENANCE_KEY, {}) or {}

    provenance = {
        "author_agent": borg_prov.get("author_agent", "agentskills://converter"),
        "evidence": borg_prov.get("evidence", f"Converted from agentskills skill '{name}'"),
        "confidence": borg_prov.get("confidence", "inferred"),
        "failure_cases": borg_prov.get("failure_cases", []),
    }

    # Parse phases from markdown body
    # agentskills.io uses ### Phase N: Name for sub-headers within ## Phases
    phases = _extract_phases_from_agentskills_md(body)
    if not phases:
        phases = sections_to_phases(body)

    # If no phases found, use a default
    if not phases:
        phases = [{"name": "default", "description": body or description,
                   "checkpoint": "", "anti_patterns": [], "prompts": []}]

    # Build required_inputs from ## Required Inputs section
    required_inputs = _extract_section_list(body, "required inputs", "required inputs")
    if not required_inputs:
        required_inputs = frontmatter.get("required_inputs", [])

    # Build escalation_rules from ## Escalation section
    escalation_rules = _extract_section_list(body, "escalation", "escalation")
    if not escalation_rules:
        escalation_rules = frontmatter.get("escalation_rules",
                                           ["Escalate on ambiguous or missing information."])

    # Build tags from frontmatter
    tags = frontmatter.get("tags", [])

    # mental_model: first paragraph of body or description
    mental_model = description

    pack: Dict[str, Any] = {
        "type": PACK_TYPE,
        "version": PACK_VERSION,
        "id": pack_id,
        "problem_class": description or name,
        "mental_model": mental_model,
        "structure": list(phases),
        "phases": phases,
        "required_inputs": required_inputs,
        "escalation_rules": escalation_rules,
        "provenance": provenance,
    }

    if tags:
        pack["tags"] = tags

    # Store borg provenance in metadata for round-trip fidelity
    if "metadata" not in frontmatter:
        frontmatter["metadata"] = {}
    frontmatter["metadata"][_BORG_PROVENANCE_KEY] = provenance

    return pack


# ---------------------------------------------------------------------------
# Internal helpers — SKILL.md generation
# ---------------------------------------------------------------------------

def _pack_to_frontmatter_and_body(pack: dict) -> tuple[dict, str]:
    """Split a borg pack into YAML frontmatter dict and markdown body string."""
    pack_id = pack.get("id", "")
    name = _pack_id_to_name(pack_id)

    description = pack.get("problem_class", "") or pack.get("mental_model", "")
    if len(description) > _MAX_DESC_LEN:
        description = description[: _MAX_DESC_LEN - 3] + "..."

    # Store full provenance in metadata for round-tripping
    provenance = pack.get("provenance", {})
    metadata = {_BORG_PROVENANCE_KEY: provenance}

    frontmatter: Dict[str, Any] = {
        "name": name,
        "description": description,
        "metadata": metadata,
    }

    # Optional fields
    if pack.get("tags"):
        frontmatter["tags"] = pack["tags"]

    if pack.get("required_inputs"):
        frontmatter["required_inputs"] = pack["required_inputs"]

    if pack.get("escalation_rules"):
        frontmatter["escalation_rules"] = pack["escalation_rules"]

    # Build markdown body
    body_parts: List[str] = []

    # ## Overview
    body_parts.append("# Overview\n\n")
    mental_model = pack.get("mental_model", "")
    if mental_model:
        body_parts.append(f"{mental_model}\n\n")

    # ## When to Use
    start_signals = pack.get("start_signals", [])
    if start_signals:
        body_parts.append("## When to Use\n")
        for signal in start_signals:
            if isinstance(signal, dict):
                ep = signal.get("error_pattern", "")
                start_here = signal.get("start_here", [])
                avoid = signal.get("avoid", [])
                reasoning = signal.get("reasoning", "")
                if ep:
                    body_parts.append(f"**{ep}:**\n")
                if isinstance(start_here, list):
                    for s in start_here:
                        body_parts.append(f"- {s}\n")
                if isinstance(avoid, list):
                    for a in avoid:
                        body_parts.append(f"- ⚠️ Avoid: {a}\n")
                if reasoning:
                    body_parts.append(f"  *{reasoning}*\n")
            elif isinstance(signal, str):
                body_parts.append(f"- {signal}\n")
        body_parts.append("\n")

    # ## Required Inputs
    required_inputs = pack.get("required_inputs", [])
    if required_inputs:
        body_parts.append("## Required Inputs\n")
        for inp in required_inputs:
            body_parts.append(f"- {inp}\n")
        body_parts.append("\n")

    # ## Phases
    phases = pack.get("phases", [])
    if phases:
        body_parts.append("## Phases\n")
        for i, phase in enumerate(phases, 1):
            phase_name = phase.get("name", f"phase-{i}")
            phase_title = phase_name.replace("_", " ").title()
            body_parts.append(f"### Phase {i}: {phase_title}\n")
            desc = phase.get("description", "")
            if desc:
                body_parts.append(f"{desc}\n")
            anti_patterns = phase.get("anti_patterns", [])
            for ap in anti_patterns:
                body_parts.append(f"⚠️ Do NOT: {ap}\n")
            checkpoint = phase.get("checkpoint", "")
            if checkpoint:
                body_parts.append(f"\n✅ Before moving on: {checkpoint}\n")
            prompts = phase.get("prompts", [])
            for p in prompts:
                body_parts.append(f"\n> {p}\n")
            body_parts.append("\n")

    # ## Examples
    examples = pack.get("examples", [])
    if examples:
        body_parts.append("## Examples\n")
        for j, ex in enumerate(examples, 1):
            body_parts.append(f"**Example {j}:**\n")
            if isinstance(ex, dict):
                body_parts.append(f"**Problem:** {ex.get('problem', '')}\n")
                body_parts.append(f"**Solution:** {ex.get('solution', '')}\n")
                outcome = ex.get("outcome", "")
                if outcome:
                    body_parts.append(f"**Outcome:** {outcome}\n")
            body_parts.append("\n")

    # ## Escalation
    escalation = pack.get("escalation_rules", [])
    if escalation:
        body_parts.append("## Escalation\n")
        for rule in escalation:
            body_parts.append(f"- {rule}\n")
        body_parts.append("\n")

    return frontmatter, "".join(body_parts)


def _pack_id_to_name(pack_id: str) -> str:
    """Convert a borg pack ID to a valid agentskills.io name.

    Examples:
        guild://hermes/systematic-debugging → systematic-debugging
        borg://local/test-workflow          → test-workflow
    """
    if "://" in pack_id:
        name = pack_id.rstrip("/").split("/")[-1]
    else:
        name = pack_id
    # Sanitize: lowercase, replace non-alphanumeric with hyphens
    name = re.sub(r"[^a-zA-Z0-9]", "-", name.lower())
    name = re.sub(r"-+", "-", name).strip("-")
    if not name:
        name = "unnamed-skill"
    if len(name) > _MAX_NAME_LEN:
        name = name[: _MAX_NAME_LEN - 3] + "---"
    # Validate
    if not _NAME_RE.match(name):
        # Replace any remaining invalid chars
        name = re.sub(r"[^a-z0-9-]", "", name).strip("-")
    if not _NAME_RE.match(name):
        name = "unnamed-skill"
    return name


def _provenance_to_md(provenance: dict) -> str:
    """Render borg provenance dict as a markdown string."""
    lines = ["# Provenance\n"]
    prov_type = provenance.get("type", "unknown")
    lines.append(f"**Type:** {prov_type}\n")
    confidence = provenance.get("confidence", "unknown")
    lines.append(f"**Confidence:** {confidence}\n")
    author = provenance.get("author_agent", "unknown")
    lines.append(f"**Author Agent:** {author}\n")
    evidence = provenance.get("evidence", "")
    if evidence:
        lines.append(f"**Evidence:** {evidence}\n")
    failure_cases = provenance.get("failure_cases", [])
    if failure_cases:
        lines.append("\n## Known Failure Cases\n")
        for fc in failure_cases:
            lines.append(f"- {fc}\n")
    return "".join(lines)


def _phase_to_md(phase: dict, index: int) -> str:
    """Render a single borg phase as a markdown file."""
    lines: List[str] = []
    phase_name = phase.get("name", f"phase-{index}")
    phase_title = phase_name.replace("_", " ").title()
    lines.append(f"# Phase {index}: {phase_title}\n\n")
    desc = phase.get("description", "")
    if desc:
        lines.append(f"{desc}\n\n")
    checkpoint = phase.get("checkpoint", "")
    if checkpoint:
        lines.append(f"**Checkpoint:** {checkpoint}\n\n")
    anti_patterns = phase.get("anti_patterns", [])
    if anti_patterns:
        lines.append("## Anti-Patterns\n")
        for ap in anti_patterns:
            lines.append(f"- ⚠️ Do NOT: {ap}\n")
        lines.append("\n")
    prompts = phase.get("prompts", [])
    if prompts:
        lines.append("## Prompts\n")
        for p in prompts:
            lines.append(f"> {p}\n")
        lines.append("\n")
    skip_if = phase.get("skip_if")
    if skip_if:
        lines.append("## Skip Conditions\n")
        if isinstance(skip_if, list):
            for s in skip_if:
                if isinstance(s, dict):
                    lines.append(f"- Skip if: {s.get('condition','?')} — {s.get('reason','')}\n")
        elif isinstance(skip_if, dict):
            lines.append(f"- Skip if: {skip_if.get('condition','?')} — {skip_if.get('reason','')}\n")
        lines.append("\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers — SKILL.md parsing
# ---------------------------------------------------------------------------

def _extract_section_list(body: str, *keywords: str) -> List[str]:
    """Extract bullet list items from a section matching any keyword.

    Looks for a ## header whose text contains any of the keywords,
    then collects all subsequent - prefixed lines.
    """
    lines = body.split("\n")
    capture = False
    items: List[str] = []
    keyword_lower = [kw.lower() for kw in keywords]

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if capture:
                break
            header_lower = stripped[3:].lower()
            if any(kw in header_lower for kw in keyword_lower):
                capture = True
            continue
        if capture:
            if stripped.startswith("- "):
                items.append(stripped[2:])
            elif stripped and not stripped.startswith("#"):
                # Stop at next section or non-list content
                if items:
                    break
    return items


# Match ### Phase N: Name  (with optional trailing content after the name)
_PHASE_HEADER_RE = re.compile(r"^###\s+Phase\s+\d+:\s*([^\n#]*)", re.IGNORECASE)


def _extract_phases_from_agentskills_md(body: str) -> List[dict]:
    """Extract phases from agentskills.io-style ### Phase N: Name sub-headers.

    Looks for a ## Phases section, then collects all ### Phase N: Name
    sub-headers and their content until the next top-level ## section.
    """
    lines = body.split("\n")
    phases: List[dict] = []
    in_phases_section = False
    current_name: str | None = None
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Top-level ## header
        if stripped.startswith("## "):
            header_text = stripped[3:].strip().lower()
            if "phase" in header_text:
                in_phases_section = True
                # Commit previous phase
                if current_name is not None:
                    phases.append(_make_phase(current_name, current_lines))
                current_name = None
                current_lines = []
                continue
            else:
                if in_phases_section and current_name is not None:
                    # End of phases section
                    phases.append(_make_phase(current_name, current_lines))
                    current_name = None
                    current_lines = []
                in_phases_section = False

        # Sub-header: ### Phase N: Name
        if stripped.startswith("### "):
            m = _PHASE_HEADER_RE.match(stripped)
            if m:
                phase_title = m.group(1).strip()
                if current_name is not None:
                    phases.append(_make_phase(current_name, current_lines))
                current_name = phase_title or f"phase-{len(phases)+1}"
                current_lines = []
                continue

        if in_phases_section and current_name is not None:
            current_lines.append(line)

    # Last phase
    if current_name is not None:
        phases.append(_make_phase(current_name, current_lines))

    return phases


def _make_phase(name: str, lines: List[str]) -> dict:
    """Build a phase dict from collected lines."""
    # Filter out checkpoint/anti-pattern markers for the description
    desc_parts: List[str] = []
    anti_patterns: List[str] = []
    prompts: List[str] = []
    checkpoint = ""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("⚠️ Do NOT:"):
            anti_patterns.append(stripped.replace("⚠️ Do NOT:", "").strip())
        elif stripped.startswith("✅ Before moving on:"):
            checkpoint = stripped.replace("✅ Before moving on:", "").strip()
        elif stripped.startswith("> "):
            prompts.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("#"):
            desc_parts.append(stripped)

    description = "\n".join(desc_parts).strip()
    return {
        "name": re.sub(r"[^a-z0-9_]", "_", name.lower()),
        "description": description,
        "checkpoint": checkpoint,
        "anti_patterns": anti_patterns,
        "prompts": prompts,
    }


def _validate_name(name: str) -> None:
    """Validate an agentskills.io name field.

    Raises ValueError if invalid.
    """
    if not name:
        raise ValueError("name field is required and cannot be empty")
    if len(name) > _MAX_NAME_LEN:
        raise ValueError(f"name must be <= {_MAX_NAME_LEN} chars, got {len(name)}")
    if not _NAME_RE.match(name):
        raise ValueError(
            f"name '{name}' is invalid. Must match pattern ^[a-z0-9]+(-[a-z0-9]+)*$ "
            f"(lowercase letters, numbers, hyphens; no leading/trailing hyphens)"
        )
