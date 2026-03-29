"""
Borg → OpenClaw Converter — converts borg pack registry to OpenClaw skill format.

Exports:
    convert_pack_to_openclaw_ref()  — convert single pack to reference markdown
    convert_registry_to_openclaw()  — convert entire registry to skill directory
    generate_pack_index()           — generate references/pack-index.md
    generate_bridge_skill()         — generate main SKILL.md (the bridge)
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROBLEM_CLASS_EMOJI = {
    "debugging": "🐛",
    "testing": "🧪",
    "code-review": "👀",
    "planning": "📋",
    "deployment": "🚀",
    "security": "🔒",
    "performance": "⚡",
    "documentation": "📝",
    "refactoring": "🔧",
    "general": "🧠",
}

BRIDGE_SKILL_TEMPLATE = """\
---
name: borg
description: "{description}"
user-invocable: true
metadata: {{"openclaw":{{"emoji":"{emoji}","homepage":"https://github.com/bensargotest-sys/guild-tools","always":false}}}}
---

# 🧠 Borg — Collective Intelligence for AI Agents

{body}
---
*Powered by [borg](https://github.com/bensargotest-sys/guild-tools) — collective intelligence for AI agents.*
"""


# ---------------------------------------------------------------------------
# Main Converter Functions
# ---------------------------------------------------------------------------

def convert_pack_to_openclaw_ref(pack: dict) -> str:
    """Convert a single borg pack to an OpenClaw reference markdown file.

    Preserves ALL pack intelligence:
    - Full phase descriptions with checkpoints
    - All anti-patterns inline
    - Start signals as "When to Use" section
    - Examples
    - Escalation rules
    - Provenance

    Args:
        pack: A parsed borg workflow pack dict.

    Returns:
        Markdown string for the pack reference file.
    """
    pack_id = pack.get("id", "")
    name = _extract_slug(pack_id)
    problem_class = pack.get("problem_class", "")
    mental_model = pack.get("mental_model", "")
    confidence = pack.get("provenance", {}).get("confidence", "inferred")

    sections = []

    # Title
    title = name.replace("-", " ").title()
    sections.append(f"# {title}\n")
    sections.append(f"**Confidence:** {confidence} | **Problem class:** {problem_class}\n")

    # When to Use (from start_signals)
    start_signals = pack.get("start_signals", [])
    if start_signals:
        sections.append("## When to Use\n")
        for signal in start_signals:
            if isinstance(signal, dict):
                error_pattern = signal.get("error_pattern", "")
                start_here = signal.get("start_here", [])
                avoid = signal.get("avoid", [])
                reasoning = signal.get("reasoning", "")
                if error_pattern:
                    sections.append(f"**{error_pattern}:**\n")
                if start_here:
                    for s in start_here if isinstance(start_here, list) else [start_here]:
                        sections.append(f"- 🎯 {s}\n")
                if avoid:
                    for a in avoid if isinstance(avoid, list) else [avoid]:
                        sections.append(f"- ⚠️ Avoid: {a}\n")
                if reasoning:
                    sections.append(f"  *{reasoning}*\n")
            elif isinstance(signal, str):
                sections.append(f"- {signal}\n")

    # Required Inputs
    required_inputs = pack.get("required_inputs", [])
    if required_inputs:
        sections.append("## Required Inputs\n")
        for inp in required_inputs:
            sections.append(f"- {inp}\n")
        sections.append("\n")

    # Phases (core content)
    phases = pack.get("phases", [])
    if phases:
        sections.append("## Phases\n")
        for i, phase in enumerate(phases, 1):
            phase_name = phase.get("name", f"phase-{i}")
            phase_title = phase_name.replace("_", " ").title()
            sections.append(f"### Phase {i}: {phase_title}\n")
            sections.append(f"{phase.get('description', '')}\n")

            # Anti-patterns
            anti_patterns = phase.get("anti_patterns", [])
            for ap in anti_patterns:
                sections.append(f"⚠️ Do NOT: {ap}\n")

            # Checkpoint
            checkpoint = phase.get("checkpoint")
            if checkpoint:
                sections.append(f"\n✅ Before moving on: {checkpoint}\n")

            # Skip/inject conditions
            if phase.get("skip_if"):
                skip = phase["skip_if"]
                if isinstance(skip, list):
                    for s in skip:
                        if isinstance(s, dict):
                            sections.append(f"\n💡 Skip this step if: {s.get('condition','?')} — {s.get('reason','')}\n")
                elif isinstance(skip, dict):
                    sections.append(f"\n💡 Skip this step if: {skip.get('condition','?')} — {skip.get('reason','')}\n")
            if phase.get("inject_if"):
                inject = phase["inject_if"]
                if isinstance(inject, list):
                    for s in inject:
                        if isinstance(s, dict):
                            sections.append(f"\n💡 Add this step if: {s.get('condition','?')} — {s.get('message','')}\n")
                elif isinstance(inject, dict):
                    sections.append(f"\n💡 Add this step if: {inject.get('condition','?')} — {inject.get('message','')}\n")

            sections.append("\n")

    # Examples
    examples = pack.get("examples", [])
    if examples:
        sections.append("## Examples\n")
        for j, ex in enumerate(examples, 1):
            sections.append(f"**Example {j}:**\n")
            if isinstance(ex, dict):
                sections.append(f"**Problem:** {ex.get('problem', '')}\n")
                sections.append(f"**Solution:** {ex.get('solution', '')}\n")
                sections.append(f"**Outcome:** {ex.get('outcome', '')}\n")
            sections.append("\n")

    # Escalation
    escalation = pack.get("escalation_rules", [])
    if escalation:
        sections.append("## Escalation\n")
        for rule in escalation:
            sections.append(f"- {rule}\n")
        sections.append("\n")

    # Provenance footer
    provenance = pack.get("provenance", {})
    if provenance:
        parts = []
        if provenance.get("confidence"):
            parts.append(f"Confidence: {provenance['confidence']}")
        if provenance.get("evidence"):
            parts.append(f"Evidence: {provenance['evidence']}")
        if provenance.get("author_agent"):
            parts.append(f"Author: {provenance['author_agent']}")
        if parts:
            sections.append("---\n")
            sections.append("* | ".join(parts) + "*\n")

    return "".join(sections)


def generate_pack_index(packs: List[dict]) -> str:
    """Generate references/pack-index.md listing all available packs.

    Args:
        packs: List of parsed borg pack dicts.

    Returns:
        Markdown string for the pack index.
    """
    lines = [
        "# Borg Pack Index\n",
        "\n",
        "| Pack | Problem Class | Confidence | Use When |\n",
        "|------|--------------|-----------|----------|\n",
    ]

    for pack in packs:
        pack_id = pack.get("id", "")
        name = _extract_slug(pack_id)
        problem_class = pack.get("problem_class", "")
        if isinstance(problem_class, str):
            problem_class_short = problem_class.split("\n")[0][:50]
        else:
            problem_class_short = str(problem_class)[:50]
        confidence = pack.get("provenance", {}).get("confidence", "inferred")

        # Derive "use when" from start_signals or problem_class
        start_signals = pack.get("start_signals", [])
        use_when = ""
        if start_signals:
            if isinstance(start_signals[0], dict):
                use_when = start_signals[0].get("reasoning", problem_class_short)
            elif isinstance(start_signals[0], str):
                use_when = start_signals[0][:60]
        else:
            use_when = problem_class_short

        lines.append(f"| {name} | {problem_class_short} | {confidence} | {use_when} |\n")

    lines.append("\n")
    lines.append("To use a pack: `read references/packs/<pack-name>.md`\n")

    return "".join(lines)


def generate_bridge_skill(packs: List[dict], output_dir: Optional[Path] = None) -> str:
    """Generate the main SKILL.md bridge file.

    Args:
        packs: List of parsed borg pack dicts.
        output_dir: Optional output directory (used to write pack-index.md).

    Returns:
        The complete SKILL.md content as a string.
    """
    emoji = "🧠"

    # Build description (max 1024 chars)
    description = (
        "When your agent is stuck in a loop, burning tokens on a problem someone else already solved. "
        "Use when debugging takes >3 attempts, code review needs structure, or you need a proven approach "
        "for testing, planning, or deployment. Borg connects to collective agent intelligence — "
        "battle-tested workflows from thousands of agents. "
        "NOT for simple tasks that need no structure."
    )

    # Build body
    body_parts = []

    body_parts.append("Stop burning tokens on problems someone else already solved.\n")

    # When to Use
    body_parts.append("## When to Use\n")
    body_parts.append("- Your agent hit a blocker and is going in circles (3+ failed attempts)\n")
    body_parts.append("- You need a structured approach to debugging, testing, code review, or planning\n")
    body_parts.append("- You want proven workflows that worked for other agents on similar problems\n")

    # When NOT to Use
    body_parts.append("## When NOT to Use\n")
    body_parts.append("- Simple, obvious fixes (typos, missing imports)\n")
    body_parts.append("- Tasks that don't benefit from structured phases\n")
    body_parts.append("- Creative or open-ended tasks with no \"right approach\"\n")

    # How to Use
    body_parts.append("## How to Use\n")
    body_parts.append("### Step 1: Find the right pack\n")
    body_parts.append("Read the pack index to find relevant approaches:\n")
    body_parts.append("```\nread references/pack-index.md\n```\n")
    body_parts.append("### Step 2: Load the pack\n")
    body_parts.append("Once you find a matching pack, read its full instructions:\n")
    body_parts.append("```\nread references/packs/<pack-name>.md\n```\n")
    body_parts.append("### Step 3: Follow the phases\n")
    body_parts.append("Each pack has numbered phases with checkpoints. Follow them IN ORDER.\n")
    body_parts.append("Do NOT skip phases. Do NOT move to the next phase until the checkpoint passes.\n")
    body_parts.append("⚠️ **Critical:** The phases exist because agents that skip them fail. "
                     "The checkpoints exist because agents that don't verify their work produce bad fixes. "
                     "Trust the process.\n")

    # Quick Reference (top 6 packs)
    quick_packs = packs[:6]
    if quick_packs:
        body_parts.append("## Available Packs\n")
        body_parts.append("See `references/pack-index.md` for the full registry with descriptions.\n")
        body_parts.append("**Quick reference:**\n")
        for pack in quick_packs:
            pack_id = pack.get("id", "")
            name = _extract_slug(pack_id)
            problem_class = pack.get("problem_class", "")
            if isinstance(problem_class, str):
                pc_short = problem_class.split("\n")[0].strip()
            else:
                pc_short = str(problem_class)
            # Truncate to reasonable length
            if len(pc_short) > 60:
                pc_short = pc_short[:57] + "..."
            body_parts.append(f"- **{name}** — {pc_short}\n")

    body = "".join(body_parts)

    skill_md = BRIDGE_SKILL_TEMPLATE.format(
        description=description,
        emoji=emoji,
        body=body,
    )

    # Validate frontmatter
    assert len(description) <= 1024, f"Description too long: {len(description)} chars"

    return skill_md


def convert_registry_to_openclaw(
    packs: List[dict],
    output_dir: Path,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Convert the entire borg pack registry to an OpenClaw skill directory.

    Creates:
        output_dir/
            SKILL.md                    ← bridge skill
            references/
                pack-index.md            ← all packs listed
                packs/
                    <name>.md            ← individual pack references

    Args:
        packs: List of parsed borg pack dicts.
        output_dir: Target directory for the OpenClaw skill.
        overwrite: If True, overwrite existing files.

    Returns:
        Dict with keys: success (bool), files_created (list), total_size (int)
    """
    output_dir = Path(output_dir)
    refs_dir = output_dir / "references" / "packs"
    refs_dir.mkdir(parents=True, exist_ok=True)

    files_created = []
    total_size = 0

    # 1. Write main SKILL.md
    skill_path = output_dir / "SKILL.md"
    if skill_path.exists() and not overwrite:
        raise FileExistsError(f"SKILL.md already exists at {skill_path}")
    skill_md = generate_bridge_skill(packs)
    skill_path.write_text(skill_md, encoding="utf-8")
    files_created.append(str(skill_path.relative_to(output_dir)))
    total_size += len(skill_md.encode("utf-8"))

    # 2. Write pack index
    index_path = refs_dir.parent / "pack-index.md"
    pack_index_md = generate_pack_index(packs)
    index_path.write_text(pack_index_md, encoding="utf-8")
    files_created.append(str(index_path.relative_to(output_dir)))
    total_size += len(pack_index_md.encode("utf-8"))

    # 3. Write individual pack references
    for pack in packs:
        pack_id = pack.get("id", "")
        name = _extract_slug(pack_id)
        ref_path = refs_dir / f"{name}.md"

        ref_md = convert_pack_to_openclaw_ref(pack)
        ref_path.write_text(ref_md, encoding="utf-8")
        rel_path = refs_dir.relative_to(output_dir) / f"{name}.md"
        files_created.append(str(rel_path))
        total_size += len(ref_md.encode("utf-8"))

    return {
        "success": True,
        "files_created": files_created,
        "total_packs": len(packs),
        "total_size_bytes": total_size,
        "output_dir": str(output_dir),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_slug(pack_id: str) -> str:
    """Extract slug from pack ID.

    Examples:
        guild://hermes/systematic-debugging → systematic-debugging
        guild://hermes/test-driven-development → test-driven-development
    """
    if "://" in pack_id:
        return pack_id.rstrip("/").split("/")[-1]
    return pack_id


def _validate_openclaw_name(name: str) -> bool:
    """Validate OpenClaw name format: /^[a-z0-9-]+$/, max 64 chars, no leading/trailing hyphens."""
    if not name:
        return False
    if len(name) > 64:
        return False
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        return False
    return True
