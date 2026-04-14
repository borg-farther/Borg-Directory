"""
Borg Rules File Generator — multi-format output for AI IDE platforms.

Generates platform-specific rules files from borg workflow packs:

  cursorrules   → .cursorrules  (Cursor)
  clinerules    → .clinerules   (Cline)
  claude-md     → CLAUDE.md     (Claude Code)
  windsurfrules → .windsurfrules (Windsurf)

Each output is written to look NATIVE to that platform — not a converted borg pack.
Phases become numbered instructions; anti-patterns become DO NOT rules;
checkpoints become verification steps.

Functions:
    generate_rules(pack, format)  — generate one format
    generate_all(pack)            — generate all four formats as a dict
"""

from __future__ import annotations

import textwrap
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Format constants
# ---------------------------------------------------------------------------

ALL_FORMATS = ("cursorrules", "clinerules", "claude-md", "windsurfrules")

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_rules(pack: Dict[str, Any], format: str) -> str:
    """Generate a platform-specific rules file from a borg pack.

    Args:
        pack: A borg workflow pack dict (from YAML). Expected keys:
              id, name, problem_class, mental_model, phases (list of dicts).
              Each phase dict may have: name, description, checkpoint,
              anti_patterns (list of str), prompts (list of str).
        format: One of "cursorrules", "clinerules", "claude-md", "windsurfrules".
                 Special value "all" returns a dict of all four format strings.

    Returns:
        The generated rules file content as a string.

    Raises:
        ValueError: If format is not recognised.
    """
    if format == "all":
        return generate_all(pack)  # type: ignore[return-value]

    if format == "cursorrules":
        return _gen_cursorrules(pack)
    elif format == "clinerules":
        return _gen_clinerules(pack)
    elif format == "claude-md":
        return _gen_claude_md(pack)
    elif format == "windsurfrules":
        return _gen_windsurfrules(pack)
    else:
        raise ValueError(
            f"Unknown format '{format}'. "
            f"Use one of: {', '.join(ALL_FORMATS)}"
        )


def generate_all(pack: Dict[str, Any]) -> Dict[str, str]:
    """Generate all four format rules files from a borg pack.

    Returns:
        Dict with keys "cursorrules", "clinerules", "claude-md", "windsurfrules".
    """
    return {
        "cursorrules": _gen_cursorrules(pack),
        "clinerules": _gen_clinerules(pack),
        "claude-md": _gen_claude_md(pack),
        "windsurfrules": _gen_windsurfrules(pack),
    }


# ---------------------------------------------------------------------------
# Internal: shared helpers
# ---------------------------------------------------------------------------


def _pack_name(pack: Dict[str, Any]) -> str:
    """Return the pack's display name."""
    return pack.get("name") or pack.get("id", "unnamed-pack")


def _phase_items(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the phases list, normalised to a list of dicts."""
    phases = pack.get("phases", [])
    if not phases:
        return [{"name": "main", "description": pack.get("mental_model", ""), "checkpoint": "", "anti_patterns": []}]
    return phases


def _indent(text: str, width: int = 2) -> str:
    """Indent every non-empty line of text by `width` spaces."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        lines.append(" " * width + line if stripped else line)
    return "\n".join(lines)


def _wrap(text: str, width: int = 80) -> str:
    """Hard-wrap text to width, preserving paragraphs."""
    paragraphs = text.split("\n\n")
    wrapped = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            wrapped.append("")
            continue
        # Detect bullet list
        if para.startswith("-"):
            wrapped.append(para)
        else:
            wrapped.append(textwrap.fill(para, width=width))
    return "\n".join(wrapped)


def _strip_description(text: str) -> str:
    """Strip YAML >-style leading indentation and normalize whitespace.

    Preserves the structural separation of lines (newlines, list markers, code fences)
    while removing only incidental whitespace.
    """
    if not text:
        return ""
    lines = text.expandtabs().splitlines()
    # Remove leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    # Remove common leading indentation from all lines (2-4 spaces)
    if lines:
        indent = len(lines[0]) - len(lines[0].lstrip())
        if indent > 0:
            lines = [l[indent:] if l.startswith(" " * indent) else l for l in lines]
    result = "\n".join(lines).strip()
    # Normalize each line: collapse runs of whitespace to single space,
    # but preserve line breaks between paragraphs (blank lines) and
    # preserve inline formatting like `code`, **bold**, etc.
    paragraphs = result.split("\n\n")
    normalized = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            normalized.append("")
            continue
        # For non-list paragraphs, collapse internal whitespace
        if not para.startswith("-"):
            para = " ".join(para.split())
        normalized.append(para)
    return "\n".join(normalized)


# ---------------------------------------------------------------------------
# Format: cursorrules
# ---------------------------------------------------------------------------


def _gen_cursorrules(pack: Dict[str, Any]) -> str:
    """Generate a .cursorrules file.

    Cursor uses a flat markdown structure. Phases become numbered steps.
    DO NOT blocks are used for anti-patterns. Checkpoints are ### Verification.
    """
    lines = []
    name = _pack_name(pack)
    problem = _strip_description(pack.get("problem_class", ""))
    mental = _strip_description(pack.get("mental_model", ""))
    phases = _phase_items(pack)

    # Header
    lines.append(f"# {name}")
    lines.append("")
    if problem:
        lines.append(f"**Problem:** {problem}")
        lines.append("")
    if mental:
        lines.append(f"**Mental Model:** {mental}")
        lines.append("")

    # Phases as numbered steps
    lines.append("## Steps")
    lines.append("")
    for i, phase in enumerate(phases, 1):
        pname = phase.get("name", f"phase-{i}").replace("_", " ").title()
        desc = _strip_description(phase.get("description", ""))
        if desc:
            lines.append(f"{i}. **{pname}** — {desc}")
        else:
            lines.append(f"{i}. **{pname}**")

        # Inline prompts under step
        prompts = phase.get("prompts", [])
        if prompts:
            for p in prompts[:3]:
                lines.append(f"   - {p}")

        checkpoint = phase.get("checkpoint", "").strip()
        if checkpoint:
            cp = _strip_description(checkpoint)
            lines.append(f"   → Verify: {cp}")

        lines.append("")

    # Anti-patterns as DO NOT block
    anti = _collect_anti_patterns(phases)
    if anti:
        lines.append("## DO NOT")
        lines.append("")
        for ap in anti[:8]:
            lines.append(f"- {ap}")
        lines.append("")

    # Verification checkpoint
    if phases:
        final_checkpoint = phases[-1].get("checkpoint", "").strip()
        if final_checkpoint:
            lines.append(f"## Verification")
            lines.append("")
            lines.append(f"Before marking complete: {final_checkpoint}")
            lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Format: clinerules
# ---------------------------------------------------------------------------


def _gen_clinerules(pack: Dict[str, Any]) -> str:
    """Generate a .clinerules file.

    Cline uses a structured format with sections. Phases as ## Phase N,
    anti-patterns as DO NOT, checkpoints as CHECK: markers.
    """
    lines = []
    name = _pack_name(pack)
    problem = _strip_description(pack.get("problem_class", ""))
    mental = _strip_description(pack.get("mental_model", ""))
    phases = _phase_items(pack)

    # Header
    lines.append(f"# {name}")
    lines.append("")
    if problem:
        lines.append(f"**Problem:** {problem}")
        lines.append("")
    if mental:
        lines.append(f"**Approach:** {mental}")
        lines.append("")

    # Phases
    for i, phase in enumerate(phases, 1):
        pname = phase.get("name", f"phase-{i}").replace("_", " ").title()
        desc = _strip_description(phase.get("description", ""))

        lines.append(f"## Phase {i}: {pname}")
        lines.append("")
        if desc:
            lines.append(desc)
            lines.append("")

        # Prompts
        prompts = phase.get("prompts", [])
        if prompts:
            lines.append("**Prompts:**")
            for p in prompts[:3]:
                lines.append(f"- {p}")
            lines.append("")

        # Checkpoint
        checkpoint = phase.get("checkpoint", "").strip()
        if checkpoint:
            cp = _strip_description(checkpoint)
            lines.append(f"**CHECK:** {cp}")
            lines.append("")

        lines.append("")

    # Anti-patterns
    anti = _collect_anti_patterns(phases)
    if anti:
        lines.append("## DO NOT")
        lines.append("")
        for ap in anti[:8]:
            lines.append(f"- {ap}")
        lines.append("")

    # Final verification
    if phases:
        final_checkpoint = phases[-1].get("checkpoint", "").strip()
        if final_checkpoint:
            lines.append("## Final Verification")
            lines.append("")
            lines.append(f"**CHECK:** {final_checkpoint}")
            lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Format: claude-md
# ---------------------------------------------------------------------------


def _gen_claude_md(pack: Dict[str, Any]) -> str:
    """Generate a CLAUDE.md file.

    Claude Code uses a human-readable guide format. Phases as numbered list,
    anti-patterns as ## DO NOT list, checkpoints as > Verification quote.
    """
    lines = []
    name = _pack_name(pack)
    problem = _strip_description(pack.get("problem_class", ""))
    mental = _strip_description(pack.get("mental_model", ""))
    phases = _phase_items(pack)

    # Header
    lines.append(f"# {name}")
    lines.append("")
    if problem:
        lines.append(f"**Use when:** {problem}")
        lines.append("")
    if mental:
        lines.append(f"**Mental model:** {mental}")
        lines.append("")

    # Core rule
    lines.append("## Approach")
    lines.append("")
    for i, phase in enumerate(phases, 1):
        pname = phase.get("name", f"phase-{i}").replace("_", " ").title()
        desc = _strip_description(phase.get("description", ""))
        if desc:
            lines.append(f"{i}. **{pname}**: {desc}")
        else:
            lines.append(f"{i}. **{pname}**")
        lines.append("")

    # Anti-patterns
    anti = _collect_anti_patterns(phases)
    if anti:
        lines.append("## DO NOT")
        lines.append("")
        for ap in anti[:8]:
            lines.append(f"- {ap}")
        lines.append("")

    # Checkpoints as verification
    checkpoints = _collect_checkpoints(phases)
    if checkpoints:
        lines.append("## Verification")
        lines.append("")
        for cp in checkpoints[:4]:
            lines.append(f"> {cp}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Format: windsurfrules
# ---------------------------------------------------------------------------


def _gen_windsurfrules(pack: Dict[str, Any]) -> str:
    """Generate a .windsurfrules file.

    Windsurf uses a clean section-based format with @ Phase markers,
    anti-patterns as NOT: tags, and checkpoints as ✓ markers.
    """
    lines = []
    name = _pack_name(pack)
    problem = _strip_description(pack.get("problem_class", ""))
    mental = _strip_description(pack.get("mental_model", ""))
    phases = _phase_items(pack)

    # Header
    lines.append(f"# {name}")
    lines.append("")
    if problem:
        lines.append(f"**Problem:** {problem}")
        lines.append("")
    if mental:
        lines.append(f"**Mental Model:** {mental}")
        lines.append("")

    # Phases as @PHASE sections
    for i, phase in enumerate(phases, 1):
        pname = phase.get("name", f"phase-{i}").replace("_", " ").title()
        desc = _strip_description(phase.get("description", ""))

        lines.append(f"@PHASE {i}: {pname}")
        lines.append("")
        if desc:
            lines.append(desc)
            lines.append("")

        # Inline prompts
        prompts = phase.get("prompts", [])
        if prompts:
            for p in prompts[:3]:
                lines.append(f"  - {p}")
            lines.append("")

        # Checkpoint as ✓
        checkpoint = phase.get("checkpoint", "").strip()
        if checkpoint:
            cp = _strip_description(checkpoint)
            lines.append(f"  ✓ {cp}")
            lines.append("")

        lines.append("")

    # Anti-patterns
    anti = _collect_anti_patterns(phases)
    if anti:
        lines.append("@ANTI_PATTERNS")
        lines.append("")
        for ap in anti[:8]:
            lines.append(f"NOT: {ap}")
        lines.append("")

    # Final checkpoint
    if phases:
        final_checkpoint = phases[-1].get("checkpoint", "").strip()
        if final_checkpoint:
            lines.append("@VERIFICATION")
            lines.append("")
            lines.append(f"✓ {final_checkpoint}")
            lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Internal: collect anti-patterns and checkpoints from phases
# ---------------------------------------------------------------------------


def _collect_anti_patterns(phases: List[Dict[str, Any]]) -> List[str]:
    """Extract unique anti-patterns from phases, de-duplicated."""
    seen: set = set()
    result: List[str] = []
    for phase in phases:
        for ap in phase.get("anti_patterns", []):
            cleaned = _strip_description(ap) if isinstance(ap, str) else str(ap)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
    return result


def _collect_checkpoints(phases: List[Dict[str, Any]]) -> List[str]:
    """Collect checkpoints from phases."""
    result: List[str] = []
    for phase in phases:
        cp = phase.get("checkpoint", "").strip()
        if cp:
            result.append(_strip_description(cp))
    return result


# ---------------------------------------------------------------------------
# CLI helper: load pack from name or path
# ---------------------------------------------------------------------------


def load_pack(pack_identifier: str) -> Dict[str, Any]:
    """Load a pack dict from a pack name or file path.

    Args:
        pack_identifier: Either a pack name (e.g. "systematic-debugging") or
                        a path to a .yaml/.yml file.

    Returns:
        The pack dict.

    Raises:
        FileNotFoundError: If no file is found for the identifier.
        ValueError: If the file does not contain a valid workflow pack.
    """
    import pathlib
    import yaml

    path = pathlib.Path(pack_identifier)
    if path.exists() and path.is_file():
        content = path.read_text(encoding="utf-8")
        pack = yaml.safe_load(content)
        if isinstance(pack, dict):
            return pack
        raise ValueError(f"Pack file does not contain a dict: {pack_identifier}")

    # Try as a pack name in the guild-packs directory
    guild_packs_dir = pathlib.Path("/root/hermes-workspace/guild-packs/packs")
    candidates = [
        guild_packs_dir / f"{pack_identifier}.yaml",
        guild_packs_dir / f"{pack_identifier}.workflow.yaml",
        guild_packs_dir / f"{pack_identifier}.rubric.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            pack = yaml.safe_load(candidate.read_text(encoding="utf-8"))
            if isinstance(pack, dict):
                return pack

    # Also try HERMES_HOME
    hermes_home = pathlib.Path.home() / ".hermes" / "guild"
    if hermes_home.exists():
        for pack_yaml in hermes_home.glob("*/pack.yaml"):
            if pack_yaml.parent.name == pack_identifier:
                pack = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                if isinstance(pack, dict):
                    return pack

    raise FileNotFoundError(f"Pack not found: {pack_identifier}")
