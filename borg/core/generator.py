"""
Borg Pack → Platform Rules Generator.

Converts borg workflow packs to native rule files for AI IDE platforms:
    - .cursorrules  (Cursor)
    - .clinerules   (Cline)
    - CLAUDE.md     (Claude Code)
    - .windsurfrules (Windsurf)

Usage:
    from borg.core.generator import generate_rules
    output = generate_rules(pack, format="cursorrules")
    output = generate_rules(pack, format="all")
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------

FORMATS = ("cursorrules", "clinerules", "claude-md", "windsurfrules")

FORMAT_FILENAMES = {
    "cursorrules": ".cursorrules",
    "clinerules": ".clinerules",
    "claude-md": "CLAUDE.md",
    "windsurfrules": ".windsurfrules",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(pack_id: str) -> str:
    """Extract slug from pack id like 'borg://converted/my-pack' or 'my-pack'."""
    if "/" in pack_id:
        return pack_id.rsplit("/", 1)[-1]
    return pack_id


def _title(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def _get_phases(pack: dict) -> list:
    """Get phases from pack, handling both v1 and v2 schemas."""
    # v1: phases is a list
    phases = pack.get("phases", [])
    if phases:
        return phases
    # v2: structure.phases
    structure = pack.get("structure", {})
    if isinstance(structure, dict):
        return structure.get("phases", [])
    return []


def _get_anti_patterns(pack: dict) -> list:
    """Get TOP-LEVEL anti-patterns from pack only.
    
    Does NOT collect from phases — those are rendered inline by _render_phases_markdown.
    This prevents duplication where phase anti-patterns appeared both inline and
    in a separate section.
    """
    return pack.get("anti_patterns", [])


def _render_phases_markdown(phases: list, numbered: bool = True) -> str:
    """Render phases as markdown sections."""
    lines = []
    for i, phase in enumerate(phases, 1):
        name = phase.get("name", phase.get("title", f"Phase {i}"))
        desc = phase.get("description", "")
        checkpoint = phase.get("checkpoint", "")
        prompts = phase.get("prompts", [])
        anti_patterns = phase.get("anti_patterns", [])

        prefix = f"{i}. " if numbered else "- "
        title = _title(name)
        lines.append(f"### {prefix}{title}")
        if desc:
            lines.append(f"{desc}")
        lines.append("")

        if prompts:
            for prompt in prompts:
                if isinstance(prompt, str):
                    lines.append(f"  - {prompt}")
                elif isinstance(prompt, dict):
                    lines.append(f"  - {prompt.get('text', prompt.get('prompt', str(prompt)))}")
            lines.append("")

        if checkpoint:
            lines.append(f"**Checkpoint:** {checkpoint}")
            lines.append("")

        if anti_patterns:
            lines.append("**Avoid:**")
            for ap in anti_patterns:
                if isinstance(ap, str):
                    lines.append(f"  - ❌ {ap}")
                elif isinstance(ap, dict):
                    action = ap.get("action", ap.get("pattern", ""))
                    why = ap.get("why_fails", ap.get("why", ""))
                    lines.append(f"  - ❌ {action}" + (f" — {why}" if why else ""))
            lines.append("")

    return "\n".join(lines)


def _render_anti_patterns_section(anti_patterns: list) -> str:
    """Render a standalone anti-patterns section."""
    if not anti_patterns:
        return ""
    lines = ["## Anti-Patterns", ""]
    for ap in anti_patterns:
        if isinstance(ap, str):
            lines.append(f"- ❌ {ap}")
        elif isinstance(ap, dict):
            action = ap.get("action", ap.get("pattern", ""))
            why = ap.get("why_fails", ap.get("why", ""))
            lines.append(f"- ❌ {action}" + (f" — {why}" if why else ""))
    lines.append("")
    return "\n".join(lines)


def _render_evidence(pack: dict) -> str:
    """Render evidence/provenance section."""
    evidence = pack.get("evidence", {})
    provenance = pack.get("provenance", {})
    if not evidence and not provenance:
        return ""

    lines = ["## Evidence", ""]
    if evidence:
        success = evidence.get("success_rate", evidence.get("success_count", ""))
        uses = evidence.get("uses", evidence.get("total", ""))
        if success:
            lines.append(f"- Success rate: {success}")
        if uses:
            lines.append(f"- Total uses: {uses}")
    if provenance:
        confidence = provenance.get("confidence", "")
        if confidence:
            lines.append(f"- Confidence: {confidence}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Format-specific generators
# ---------------------------------------------------------------------------

def _generate_cursorrules(pack: dict) -> str:
    """Generate .cursorrules from a borg pack."""
    pack_id = pack.get("id", "unknown")
    slug = _slug(pack_id)
    title = _title(slug)
    problem_class = pack.get("problem_class", "general")
    mental_model = pack.get("mental_model", "")
    phases = _get_phases(pack)
    anti_patterns = _get_anti_patterns(pack)

    lines = [
        f"# {title}",
        f"# Problem class: {problem_class}",
        "",
    ]

    if mental_model:
        lines.append(mental_model)
        lines.append("")

    # Key principles from phases
    lines.append("## Workflow")
    lines.append("")
    lines.append(_render_phases_markdown(phases))

    if anti_patterns:
        lines.append(_render_anti_patterns_section(anti_patterns))

    # Required inputs
    req = pack.get("required_inputs", [])
    if req:
        lines.append("## Required Context")
        lines.append("")
        for r in req:
            lines.append(f"- {r}")
        lines.append("")

    # Escalation
    esc = pack.get("escalation_rules", [])
    if esc:
        lines.append("## Escalation Rules")
        lines.append("")
        for e in esc:
            if isinstance(e, str):
                lines.append(f"- {e}")
            elif isinstance(e, dict):
                cond = e.get("condition", e.get("when", ""))
                action = e.get("action", e.get("then", ""))
                lines.append(f"- If {cond}: {action}")
        lines.append("")

    lines.append(f"# Generated from borg pack: {pack_id}")
    return "\n".join(lines)


def _generate_clinerules(pack: dict) -> str:
    """Generate .clinerules from a borg pack."""
    pack_id = pack.get("id", "unknown")
    slug = _slug(pack_id)
    title = _title(slug)
    problem_class = pack.get("problem_class", "general")
    mental_model = pack.get("mental_model", "")
    phases = _get_phases(pack)
    anti_patterns = _get_anti_patterns(pack)

    lines = [
        f"# {title}",
        "",
        f"Problem class: {problem_class}",
        "",
    ]

    if mental_model:
        lines.append(f"## Approach")
        lines.append(f"{mental_model}")
        lines.append("")

    lines.append("## Phases")
    lines.append("")
    lines.append(_render_phases_markdown(phases))

    if anti_patterns:
        lines.append(_render_anti_patterns_section(anti_patterns))

    lines.append(_render_evidence(pack))

    lines.append(f"<!-- Generated from borg pack: {pack_id} -->")
    return "\n".join(lines)


def _generate_claude_md(pack: dict) -> str:
    """Generate CLAUDE.md from a borg pack."""
    pack_id = pack.get("id", "unknown")
    slug = _slug(pack_id)
    title = _title(slug)
    problem_class = pack.get("problem_class", "general")
    mental_model = pack.get("mental_model", "")
    phases = _get_phases(pack)
    anti_patterns = _get_anti_patterns(pack)

    lines = [
        f"# {title}",
        "",
        f"## Overview",
        f"Problem class: {problem_class}",
    ]

    if mental_model:
        lines.append(f"Approach: {mental_model}")
    lines.append("")

    # Commands section (Claude Code convention)
    lines.append("## Commands")
    lines.append("")
    lines.append(f"- Apply pack: `borg apply {slug} --task \"<description>\"`")
    lines.append(f"- Get guidance: `borg debug \"<error message>\"`")
    lines.append(f"- Search packs: `borg search {problem_class}`")
    lines.append("")

    lines.append("## Workflow Phases")
    lines.append("")
    lines.append(_render_phases_markdown(phases))

    if anti_patterns:
        lines.append(_render_anti_patterns_section(anti_patterns))

    # Required inputs
    req = pack.get("required_inputs", [])
    if req:
        lines.append("## Required Context")
        lines.append("")
        for r in req:
            lines.append(f"- {r}")
        lines.append("")

    # Escalation
    esc = pack.get("escalation_rules", [])
    if esc:
        lines.append("## Escalation")
        lines.append("")
        for e in esc:
            if isinstance(e, str):
                lines.append(f"- {e}")
            elif isinstance(e, dict):
                cond = e.get("condition", e.get("when", ""))
                action = e.get("action", e.get("then", ""))
                lines.append(f"- **{cond}**: {action}")
        lines.append("")

    lines.append(_render_evidence(pack))

    lines.append(f"<!-- Generated from borg pack: {pack_id} -->")
    return "\n".join(lines)


def _generate_windsurfrules(pack: dict) -> str:
    """Generate .windsurfrules from a borg pack."""
    pack_id = pack.get("id", "unknown")
    slug = _slug(pack_id)
    title = _title(slug)
    problem_class = pack.get("problem_class", "general")
    mental_model = pack.get("mental_model", "")
    phases = _get_phases(pack)
    anti_patterns = _get_anti_patterns(pack)

    # Windsurf prefers concise, flat format
    lines = [
        f"# {title}",
        "",
    ]

    if mental_model:
        lines.append(f"{mental_model}")
        lines.append("")

    lines.append("## Steps")
    lines.append("")
    for i, phase in enumerate(phases, 1):
        name = phase.get("name", phase.get("title", f"Phase {i}"))
        desc = phase.get("description", "")
        checkpoint = phase.get("checkpoint", "")
        lines.append(f"{i}. **{_title(name)}**: {desc}")
        if checkpoint:
            lines.append(f"   - Verify: {checkpoint}")
    lines.append("")

    if anti_patterns:
        lines.append("## Avoid")
        lines.append("")
        for ap in anti_patterns:
            if isinstance(ap, str):
                lines.append(f"- {ap}")
            elif isinstance(ap, dict):
                action = ap.get("action", ap.get("pattern", ""))
                lines.append(f"- {action}")
        lines.append("")

    lines.append(f"# Source: borg pack {pack_id}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

GENERATORS = {
    "cursorrules": _generate_cursorrules,
    "clinerules": _generate_clinerules,
    "claude-md": _generate_claude_md,
    "windsurfrules": _generate_windsurfrules,
}


def generate_rules(pack: dict, format: str = "cursorrules") -> Union[str, Dict[str, str]]:
    """Generate platform-specific rules from a borg workflow pack.

    Args:
        pack: Parsed borg pack dict.
        format: One of 'cursorrules', 'clinerules', 'claude-md', 'windsurfrules', 'all'.

    Returns:
        String content for single format, or dict of {format: content} for 'all'.

    Raises:
        ValueError: If format is not recognized.
    """
    if format == "all":
        return {fmt: gen(pack) for fmt, gen in GENERATORS.items()}

    if format not in GENERATORS:
        raise ValueError(f"Unknown format '{format}'. Choose from: {', '.join(FORMATS)}, all")

    return GENERATORS[format](pack)


def generate_to_files(
    pack: dict,
    format: str = "all",
    output_dir: Optional[str] = None,
) -> Dict[str, str]:
    """Generate rules and write to files.

    Args:
        pack: Parsed borg pack dict.
        format: Target format or 'all'.
        output_dir: Directory to write files. Defaults to current directory.

    Returns:
        Dict of {filename: absolute_path} for files written.
    """
    out = Path(output_dir) if output_dir else Path.cwd()
    out.mkdir(parents=True, exist_ok=True)

    if format == "all":
        results = generate_rules(pack, "all")
    else:
        results = {format: generate_rules(pack, format)}

    written = {}
    for fmt, content in results.items():
        filename = FORMAT_FILENAMES[fmt]
        filepath = out / filename
        filepath.write_text(content, encoding="utf-8")
        written[filename] = str(filepath.resolve())

    return written


def load_pack(pack_name: str) -> dict:
    """Load a pack from the local registry by name.

    Searches ~/.hermes/guild/<name>/pack.yaml and local registry.

    Args:
        pack_name: Pack name/slug.

    Returns:
        Parsed pack dict.

    Raises:
        FileNotFoundError: If pack not found.
    """
    # Check ~/.hermes/guild/<name>/pack.yaml
    guild_dir = Path.home() / ".hermes" / "guild"
    pack_path = guild_dir / pack_name / "pack.yaml"
    if pack_path.exists():
        return yaml.safe_load(pack_path.read_text(encoding="utf-8"))

    # Check seeds directory
    seeds_dir = Path(__file__).parent.parent / "seeds"
    for seed_file in seeds_dir.glob("*.yaml"):
        data = yaml.safe_load(seed_file.read_text(encoding="utf-8"))
        if data and _slug(data.get("id", "")) == pack_name:
            return data

    # Check all guild subdirectories
    if guild_dir.exists():
        for subdir in guild_dir.iterdir():
            if subdir.is_dir():
                candidate = subdir / "pack.yaml"
                if candidate.exists():
                    data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
                    if data and _slug(data.get("id", "")) == pack_name:
                        return data

    raise FileNotFoundError(f"Pack not found: {pack_name}")
