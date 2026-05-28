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
    """Load a pack from a file, local Borg registry, or bundled seed packs.

    First users commonly copy the README command
    ``borg generate systematic-debugging --format cursorrules`` immediately after
    installing ``agent-borg``. That must work from a clean PyPI/GitHub install
    with an empty ``BORG_HOME``; it cannot depend on maintainer-only checkout
    paths or a pre-populated local registry.

    Args:
        pack_name: Pack slug/URI slug or an explicit .yaml/.yml file path.
            Bare slugs intentionally do not load same-named files from the
            current working directory; generated agent-rule files must not be
            poisoned by a project-local file shadowing a bundled trusted seed.

    Returns:
        Parsed pack dict.

    Raises:
        FileNotFoundError: If pack not found.
    """
    def _load_yaml_file(path: Path) -> dict | None:
        try:
            if not path.exists() or not path.is_file():
                return None
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError:
            return None
        return data if isinstance(data, dict) else None

    direct_path = Path(pack_name)
    is_explicit_yaml_path = direct_path.suffix.lower() in {".yaml", ".yml"}
    if is_explicit_yaml_path:
        direct = _load_yaml_file(direct_path)
        if direct is not None:
            return direct

    # Check BORG_HOME/guild/<name>/pack.yaml first, then the legacy
    # ~/.hermes/guild location for users/tests migrating from pre-3.3 Borg.
    from borg.core.dirs import get_borg_dir
    guild_dir = get_borg_dir()
    legacy_guild_dir = Path.home() / ".hermes" / "guild"
    guild_dirs = [guild_dir]
    if legacy_guild_dir != guild_dir:
        guild_dirs.append(legacy_guild_dir)

    for candidate_guild_dir in guild_dirs:
        data = _load_yaml_file(candidate_guild_dir / pack_name / "pack.yaml")
        if data is not None:
            return data

    # Check bundled wheel data. ``borg.core.generate`` and the CLI used to look
    # only under ``borg/seeds`` while the shipped workflow packs live under
    # ``borg/seeds_data/packs``. Keep the legacy directory, but prefer the
    # package-data path proven by fresh installs.
    package_root = Path(__file__).resolve().parents[1]
    seed_roots = [package_root / "seeds_data" / "packs", package_root / "seeds"]
    for seed_root in seed_roots:
        for suffix in (".yaml", ".workflow.yaml", ".rubric.yaml"):
            data = _load_yaml_file(seed_root / f"{pack_name}{suffix}")
            if data is not None:
                return data
        try:
            seed_files = list(seed_root.glob("*.yaml"))
        except OSError:
            seed_files = []
        for seed_file in seed_files:
            data = _load_yaml_file(seed_file)
            if data and _slug(data.get("id", "")) == pack_name:
                return data

    # Check all guild subdirectories by ID/slug as a final local-registry scan.
    for candidate_guild_dir in guild_dirs:
        try:
            subdirs = list(candidate_guild_dir.iterdir()) if candidate_guild_dir.exists() else []
        except OSError:
            subdirs = []
        for subdir in subdirs:
            if not subdir.is_dir():
                continue
            data = _load_yaml_file(subdir / "pack.yaml")
            if data and _slug(data.get("id", "")) == pack_name:
                return data

    raise FileNotFoundError(f"Pack not found: {pack_name}")
