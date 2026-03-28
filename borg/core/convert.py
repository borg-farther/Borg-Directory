"""
Guild Convert Module — convert CLAUDE.md, .cursorrules, and SKILL.md
files into guild workflow packs.

Zero imports from tools.* or guild_mcp.* — stdlib + yaml only.

Functions:
    convert_skill      — SKILL.md (YAML frontmatter + markdown body)
    convert_claude_md  — CLAUDE.md (plain markdown with rules)
    convert_cursorrules — .cursorrules (markdown or JSON)
    convert_auto       — auto-detect format from filename
    convert_pack_to_openclaw_ref  — Convert pack dict to OpenClaw reference markdown
    generate_pack_index           — Generate pack index markdown
    generate_bridge_skill         — Generate main SKILL.md for OpenClaw bridge
    convert_registry_to_openclaw   — Orchestrator: write full OpenClaw skill directory
"""

import json
import os
import re
import yaml
from typing import Any, Dict, List, Tuple

from borg.core.schema import parse_skill_frontmatter, sections_to_phases


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
        "id": f"borg://converted/{slug}",
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


# ---------------------------------------------------------------------------
# OpenClaw Bridge Converter
# ---------------------------------------------------------------------------
# Converts borg packs to OpenClaw skill format (hybrid bridge approach).
# See PRD_OPENCLAW_CONVERTER_v2.md for full design spec.
# ---------------------------------------------------------------------------

# Name validation regex
_OPENCLAW_NAME_RE = re.compile(r"^[a-z0-9-]+$")
_MAX_NAME_LEN = 64


def _extract_slug(pack_id: str) -> str:
    """Extract slug from pack ID.
    
    Examples:
        'guild://hermes/systematic-debugging' -> 'systematic-debugging'
        'guild://hermes/test-driven-development' -> 'test-driven-development'
        'systematic-debugging' -> 'systematic-debugging'
    """
    if not pack_id:
        return "unnamed"
    # Handle guild:// URI format
    if "://" in pack_id:
        slug = pack_id.split("/")[-1]
    else:
        slug = pack_id
    # Sanitize: only allow [a-z0-9-]
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    slug = slug.strip("-")
    if not slug:
        slug = "unnamed"
    return slug[:_MAX_NAME_LEN]


def _validate_name(name: str) -> str:
    """Validate and sanitize a name for OpenClaw use.
    
    Returns a valid name or raises ValueError.
    """
    if not name:
        raise ValueError("Name cannot be empty")
    if len(name) > _MAX_NAME_LEN:
        raise ValueError(f"Name exceeds {_MAX_NAME_LEN} chars: {name[:50]}...")
    if not _OPENCLAW_NAME_RE.match(name):
        raise ValueError(f"Invalid name (must match {_OPENCLAW_NAME_RE.pattern}): {name}")
    return name


def _pack_phase_to_markdown(phase: dict) -> str:
    """Convert a single phase dict to markdown preserving all fields."""
    lines = []
    name = phase.get("name", "unnamed-phase")
    description = phase.get("description", "")
    checkpoint = phase.get("checkpoint", "")
    anti_patterns = phase.get("anti_patterns", [])
    prompts = phase.get("prompts", [])
    skip_if = phase.get("skip_if", [])
    inject_if = phase.get("inject_if", [])
    context_prompts = phase.get("context_prompts", [])

    lines.append(f"### {name}")
    if description:
        # Handle multi-line descriptions
        for line in description.split("\n"):
            lines.append(line)
    lines.append("")

    # Checkpoint
    if checkpoint:
        lines.append(f"**Checkpoint:** {checkpoint}")
        lines.append("")

    # Anti-patterns
    if anti_patterns:
        lines.append("**Anti-patterns:**")
        for ap in anti_patterns:
            lines.append(f"- {ap}")
        lines.append("")

    # Prompts
    if prompts:
        lines.append("**Prompts:**")
        for p in prompts:
            lines.append(f"- {p}")
        lines.append("")

    # skip_if conditions
    if skip_if:
        lines.append("**Skip if:**")
        for cond in skip_if:
            if isinstance(cond, dict):
                lines.append(f"- `{cond.get('condition', '')}` — {cond.get('reason', '')}")
            else:
                lines.append(f"- {cond}")
        lines.append("")

    # inject_if conditions
    if inject_if:
        lines.append("**Inject if:**")
        for cond in inject_if:
            if isinstance(cond, dict):
                lines.append(f"- `{cond.get('condition', '')}` → {cond.get('message', '')}")
            else:
                lines.append(f"- {cond}")
        lines.append("")

    # context_prompts
    if context_prompts:
        lines.append("**Context prompts:**")
        for cp in context_prompts:
            if isinstance(cp, dict):
                lines.append(f"- `{cp.get('condition', '')}` → {cp.get('prompt', '')}")
            else:
                lines.append(f"- {cp}")
        lines.append("")

    return "\n".join(lines)


def convert_pack_to_openclaw_ref(pack: dict) -> str:
    """Convert a single pack dict to a markdown reference file.
    
    Preserves ALL structure: phases, checkpoints, anti-patterns, examples,
    start_signals, escalation, provenance. Zero information loss.
    
    Args:
        pack: A workflow pack dict with keys like id, name, problem_class,
              mental_model, phases, examples, start_signals, escalation_rules,
              provenance, required_inputs, confidence, etc.
    
    Returns:
        Markdown string for the pack reference file.
    """
    lines = []

    # Title
    name = pack.get("name", pack.get("id", "Unknown Pack"))
    # Extract display name from id if name not available
    if not name or name == pack.get("id"):
        slug = _extract_slug(pack.get("id", ""))
        name = slug.replace("-", " ").replace("_", " ").title()
    
    lines.append(f"# {name}")
    lines.append("")

    # Metadata line
    confidence = None
    provenance = pack.get("provenance", {})
    if isinstance(provenance, dict):
        confidence = provenance.get("confidence", "")
    
    problem_class = pack.get("problem_class", "")
    if confidence:
        lines.append(f"**Confidence:** {confidence}")
    if problem_class:
        lines.append(f"**Problem class:** {problem_class}")
    lines.append("")

    # When to Use (derived from start_signals)
    start_signals = pack.get("start_signals", [])
    if start_signals:
        lines.append("## When to Use")
        for signal in start_signals:
            if isinstance(signal, dict):
                error_pattern = signal.get("error_pattern", "")
                start_here = signal.get("start_here", [])
                avoid = signal.get("avoid", [])
                reasoning = signal.get("reasoning", "")
                
                if error_pattern:
                    lines.append(f"**{error_pattern}:**")
                if start_here:
                    lines.append(f"- Start here: {', '.join(start_here)}")
                if avoid:
                    lines.append(f"- Avoid: {', '.join(avoid)}")
                if reasoning:
                    lines.append(f"- Why: {reasoning}")
                lines.append("")
            elif isinstance(signal, str):
                lines.append(f"- {signal}")
        lines.append("")

    # Required Inputs
    required_inputs = pack.get("required_inputs", [])
    if required_inputs:
        lines.append("## Required Inputs")
        for inp in required_inputs:
            lines.append(f"- {inp}")
        lines.append("")

    # Mental Model
    mental_model = pack.get("mental_model", "")
    if mental_model:
        lines.append("## Mental Model")
        for line in mental_model.split("\n"):
            lines.append(line)
        lines.append("")

    # Phases
    phases = pack.get("phases", [])
    if phases:
        lines.append("## Phases")
        lines.append("")
        for phase in phases:
            if isinstance(phase, dict):
                lines.append(_pack_phase_to_markdown(phase))
            elif isinstance(phase, str):
                lines.append(f"### {phase}")
                lines.append("")
        lines.append("")

    # Examples
    examples = pack.get("examples", [])
    if examples:
        lines.append("## Examples")
        for i, ex in enumerate(examples, 1):
            if isinstance(ex, dict):
                problem = ex.get("problem", "")
                solution = ex.get("solution", "")
                outcome = ex.get("outcome", "")
                
                lines.append(f"**Example {i}:**")
                if problem:
                    lines.append(f"- Problem: {problem}")
                if solution:
                    lines.append(f"- Solution: {solution}")
                if outcome:
                    lines.append(f"- Outcome: {outcome}")
                lines.append("")
            elif isinstance(ex, str):
                lines.append(f"- {ex}")
        lines.append("")

    # Escalation Rules
    escalation_rules = pack.get("escalation_rules", [])
    if escalation_rules:
        lines.append("## Escalation")
        for rule in escalation_rules:
            lines.append(f"- {rule}")
        lines.append("")

    # Provenance
    if provenance:
        provenance_lines = []
        if isinstance(provenance, dict):
            author = provenance.get("author_agent", provenance.get("author", ""))
            conf = provenance.get("confidence", "")
            evidence = provenance.get("evidence", "")
            created = provenance.get("created", "")
            failure_cases = provenance.get("failure_cases", [])
            
            provenance_parts = []
            if author:
                provenance_parts.append(f"Author: {author}")
            if conf:
                provenance_parts.append(f"Confidence: {conf}")
            if created:
                provenance_parts.append(f"Created: {created}")
            
            if provenance_parts:
                provenance_lines.append(" | ".join(provenance_parts))
            if evidence:
                provenance_lines.append(f"Evidence: {evidence}")
            if failure_cases:
                provenance_lines.append(f"Failure cases: {', '.join(failure_cases)}")
        
        if provenance_lines:
            lines.append("---")
            for pl in provenance_lines:
                lines.append(pl)
            lines.append("")

    return "\n".join(lines)


def generate_pack_index(packs: list) -> str:
    """Generate the pack index markdown table.
    
    Args:
        packs: List of pack dicts.
    
    Returns:
        Markdown string for references/pack-index.md.
    """
    lines = []
    lines.append("# Borg Pack Index")
    lines.append("")
    lines.append("| Pack | Problem Class | Confidence | Use When |")
    lines.append("|------|-------------|-----------|----------|")

    for pack in packs:
        slug = _extract_slug(pack.get("id", ""))
        
        # Problem class
        problem_class = pack.get("problem_class", "")
        if isinstance(problem_class, str):
            # Truncate multi-line
            problem_class = problem_class.split("\n")[0][:50]
        
        # Confidence
        provenance = pack.get("provenance", {})
        if isinstance(provenance, dict):
            confidence = provenance.get("confidence", "unknown")
        else:
            confidence = "unknown"
        
        # Derive "Use When" from start_signals if available
        use_when = ""
        start_signals = pack.get("start_signals", [])
        if start_signals and isinstance(start_signals[0], dict):
            # Use the first start_signal's error_pattern as the trigger hint
            first_signal = start_signals[0]
            error_pattern = first_signal.get("error_pattern", "")
            if error_pattern:
                use_when = f"Trigger: {error_pattern}"
        
        # Truncate use_when
        if len(use_when) > 50:
            use_when = use_when[:47] + "..."
        
        lines.append(f"| {slug} | {problem_class} | {confidence} | {use_when} |")

    lines.append("")
    lines.append("To use a pack: `read references/packs/<pack-name>.md`")
    lines.append("")
    lines.append("---\n")
    lines.append(f"*Total packs: {len(packs)}*")

    return "\n".join(lines)


def _generate_quick_reference(packs: list) -> str:
    """Generate the quick reference list of packs for SKILL.md."""
    lines = []
    lines.append("**Available packs:**")
    lines.append("")
    
    # Group by problem class for a cleaner presentation
    by_class: Dict[str, list] = {}
    for pack in packs:
        slug = _extract_slug(pack.get("id", ""))
        provenance = pack.get("provenance", {})
        confidence = "unknown"
        if isinstance(provenance, dict):
            confidence = provenance.get("confidence", "unknown")
        
        problem_class = pack.get("problem_class", "")
        if isinstance(problem_class, str):
            problem_class = problem_class.split("\n")[0]
        
        if problem_class not in by_class:
            by_class[problem_class] = []
        by_class[problem_class].append((slug, confidence))
    
    for pc, packs_list in by_class.items():
        lines.append(f"- *{pc}:*")
        for slug, conf in packs_list:
            lines.append(f"  - **{slug}** ({conf})")
    
    return "\n".join(lines)


def generate_bridge_skill(packs: list) -> str:
    """Generate the main SKILL.md for the OpenClaw bridge.
    
    This is the entry point skill that teaches the model when and how
    to use borg packs. Must be <200 lines.
    
    Args:
        packs: List of pack dicts.
    
    Returns:
        Markdown string for the SKILL.md file.
    """
    lines = []
    
    # Frontmatter (YAML)
    lines.append("---")
    lines.append("name: borg")
    lines.append("description: \"Use when your agent is stuck in a loop, burning tokens on a problem it can't solve after 3+ attempts. Covers debugging, testing, code review, planning. Borg provides battle-tested workflows from collective agent intelligence. NOT for simple/obvious fixes.\"")
    lines.append("user-invocable: true")
    lines.append("metadata: {\"openclaw\":{\"emoji\":\"🧠\",\"homepage\":\"https://github.com/bensargotest-sys/guild-tools\",\"always\":false}}")
    lines.append("---")
    lines.append("")
    
    # Title
    lines.append("# 🧠 Borg — Collective Intelligence for AI Agents")
    lines.append("")
    lines.append("Stop burning tokens on problems someone else already solved.")
    lines.append("")
    
    # When to Use
    lines.append("## When to Use")
    lines.append("")
    lines.append("- Your agent hit a blocker and is going in circles (3+ failed attempts)")
    lines.append("- You need a structured approach to debugging, testing, code review, or planning")
    lines.append("- You want proven workflows that worked for other agents on similar problems")
    lines.append("")
    
    # When NOT to Use
    lines.append("## When NOT to Use")
    lines.append("")
    lines.append("- Simple, obvious fixes (typos, missing imports)")
    lines.append("- Tasks that don't benefit from structured phases")
    lines.append("- Creative or open-ended tasks with no \"right approach\"")
    lines.append("")
    
    # How to Use
    lines.append("## How to Use")
    lines.append("")
    lines.append("### Step 1: Find the right pack")
    lines.append("")
    lines.append("Read the pack index to find relevant approaches:")
    lines.append("")
    lines.append("```")
    lines.append("read references/pack-index.md")
    lines.append("```")
    lines.append("")
    lines.append("### Step 2: Load the pack")
    lines.append("")
    lines.append("Once you find a matching pack, read its full instructions:")
    lines.append("")
    lines.append("```")
    lines.append("read references/packs/<pack-name>.md")
    lines.append("```")
    lines.append("")
    lines.append("### Step 3: Follow the phases")
    lines.append("")
    lines.append("Each pack has numbered phases with checkpoints. Follow them IN ORDER.")
    lines.append("Do NOT skip phases. Do NOT move to the next phase until the checkpoint passes.")
    lines.append("")
    lines.append("⚠️ **Critical:** The phases exist because agents that skip them fail. The checkpoints exist because agents that don't verify their work produce bad fixes. Trust the process.")
    lines.append("")
    
    # Quick Reference
    lines.append("## Available Packs")
    lines.append("")
    quick_ref = _generate_quick_reference(packs)
    lines.append(quick_ref)
    lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("*Powered by [borg](https://github.com/bensargotest-sys/guild-tools) — collective intelligence for AI agents.*")

    return "\n".join(lines)


def convert_registry_to_openclaw(packs: list, output_dir: str) -> dict:
    """Convert entire borg pack registry to ONE OpenClaw skill with references.
    
    Creates the following file structure in output_dir:
        SKILL.md                    — main bridge skill (<200 lines)
        references/
            pack-index.md           — pack index table
            packs/
                <slug>.md          — individual pack reference files
    
    Args:
        packs: List of pack dicts to convert.
        output_dir: Directory to write the skill files to.
    
    Returns:
        dict mapping file paths to content (for testing/debugging):
        {
            "SKILL.md": "...",
            "references/pack-index.md": "...",
            "references/packs/systematic-debugging.md": "...",
            ...
        }
    
    Raises:
        ValueError: If a pack name is invalid for OpenClaw.
        OSError: If the output directory cannot be created.
    """
    import pathlib
    
    output_path = pathlib.Path(output_dir)
    
    # Create directory structure
    refs_dir = output_path / "references" / "packs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    
    files: Dict[str, str] = {}
    
    # 1. Generate main SKILL.md (the bridge)
    skill_md = generate_bridge_skill(packs)
    files["SKILL.md"] = skill_md
    
    # 2. Generate pack index
    index_md = generate_pack_index(packs)
    files["references/pack-index.md"] = index_md
    
    # 3. Convert each pack to a reference file
    pack_refs: Dict[str, str] = {}
    for pack in packs:
        pack_id = pack.get("id", "")
        slug = _extract_slug(pack_id)
        
        # Validate slug
        try:
            _validate_name(slug)
        except ValueError as e:
            raise ValueError(f"Invalid pack name '{slug}' from pack id '{pack_id}': {e}")
        
        ref_content = convert_pack_to_openclaw_ref(pack)
        pack_refs[slug] = ref_content
        files[f"references/packs/{slug}.md"] = ref_content
    
    # Write all files to disk
    for rel_path, content in files.items():
        file_path = output_path / rel_path
        file_path.write_text(content, encoding="utf-8")
    
    return {
        "success": True,
        "output_dir": str(output_path),
        "files_written": len(files),
        "pack_count": len(packs),
        "pack_slugs": list(pack_refs.keys()),
        "skill_md_lines": len(skill_md.split("\n")),
        "files": files,
    }