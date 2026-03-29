# OpenClaw Implementation Spec — Borg Integration v2
## Status: IMPLEMENTATION READY
## Version: 2.0 | Date: 2026-03-29

---

## 1. OVERVIEW

This spec advances the OpenClaw integration from "researched" (documented in PRD v1/v2) to fully specified implementation. It covers the **hybrid bridge architecture**, the **borg→OpenClaw converter**, the **MCP bridge tools**, and the **CLI commands** needed to make borg packs discoverable and usable within OpenClaw's 339k-star ecosystem.

### What Already Exists
- `borg/integrations/mcp_server.py` — MCP server with 10 tools (search, pull, try, init, apply, publish, feedback, suggest, observe, convert)
- `borg/core/convert.py` — Converter for SKILL.md/CLAUDE.md/.cursorrules → borg pack (one direction only)
- `borg/core/search.py` — Search engine with text/semantic/hybrid modes
- `borg/core/uri.py` — URI resolution and pack fetching
- `PRD_OPENCLAW_CONVERTER_v2.md` — Detailed hybrid bridge architecture design

### What Needs to Be Built
1. **OpenClaw converter module** (`borg/core/openclaw_converter.py`) — converts borg packs → OpenClaw skill format
2. **New MCP tool** `borg_sync` — push converted skill to OpenClaw
3. **New CLI command** `borg openclaw sync` — CLI interface to the sync tool
4. **New MCP tool** `borg_list_openclaw` — list what's currently installed in OpenClaw

---

## 2. HYBRID BRIDGE ARCHITECTURE

### Why the Hybrid Bridge (Not Per-Pack Conversion)

The v1 PRD attempted per-pack SKILL.md conversion. This fails because:

| Problem | Impact |
|---------|--------|
| OpenClaw descriptions are the **only** matching signal for skill triggers | Borg's structured descriptions become generic when flattened to markdown |
| OpenClaw enforces no phase ordering | Borg's checkpoint-enforced phases become advisory suggestions |
| OpenClaw recommends <500 lines per skill | Borg packs with phases+examples+anti-patterns run 1500+ lines |
| 23 packs = 23 mediocre skills |分散 signal, no single compelling description |

The hybrid bridge solves this with **two layers**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     OpenClaw Pi Agent                            │
│   Sees: "borg" skill with killer description → triggers it      │
│   Reads: references/pack-index.md for pack discovery             │
│   Loads: references/packs/<name>.md for full pack intelligence  │
└────────────────────────┬────────────────────────────────────────┘
                         │ reads SKILL.md
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  ~/.openclaw/skills/borg/                        [ Borg Skill ] │
│  ├── SKILL.md                  ← The bridge (trigger + guide)   │
│  ├── references/                                               │
│  │   ├── pack-index.md          ← All 23 packs listed           │
│  │   └── packs/                                                 │
│  │       ├── systematic-debugging.md  ← Full pack preserved     │
│  │       ├── test-driven-development.md                         │
│  │       └── ... (23 total)                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │ borg CLI / MCP tools
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  ~/.hermes/guild/                          [ Borg Pack Store ]   │
│  ├── packs/                                                       │
│  │   ├── systematic-debugging.workflow.yaml                      │
│  │   └── ...                                                     │
│  └── index.json                  ← Remote registry              │
└─────────────────────────────────────────────────────────────────┘
```

### The Borg SKILL.md (Bridge Skill — <200 lines)

This is the **only** OpenClaw skill. Its description is trigger-optimized to fire whenever the Pi agent is stuck, debugging, or needs structure:

```markdown
---
name: borg
description: "When your agent is stuck in a loop, burning tokens on a problem someone else already solved. Use when debugging takes >3 attempts, code review needs structure, or you need a proven approach for testing, planning, or deployment. Borg connects to collective agent intelligence — battle-tested workflows from thousands of agents. NOT for simple tasks that need no structure."
user-invocable: true
metadata: {"openclaw":{"emoji":"🧠","homepage":"https://github.com/bensargotest-sys/guild-tools","always":false}}
---

# 🧠 Borg — Collective Intelligence for AI Agents

Stop burning tokens on problems someone else already solved.

## When to Use

- Your agent hit a blocker and is going in circles (3+ failed attempts)
- You need a structured approach to debugging, testing, code review, or planning
- You want proven workflows that worked for other agents on similar problems

## When NOT to Use

- Simple, obvious fixes (typos, missing imports)
- Tasks that don't benefit from structured phases
- Creative or open-ended tasks with no "right approach"

## How to Use

### Step 1: Find the right pack

Read the pack index to find relevant approaches:

```
read references/pack-index.md
```

### Step 2: Load the pack

Once you find a matching pack, read its full instructions:

```
read references/packs/<pack-name>.md
```

### Step 3: Follow the phases

Each pack has numbered phases with checkpoints. Follow them IN ORDER.
Do NOT skip phases. Do NOT move to the next phase until the checkpoint passes.

⚠️ **Critical:** The phases exist because agents that skip them fail.
The checkpoints exist because agents that don't verify their work produce bad fixes.
Trust the process.

## Available Packs

See `references/pack-index.md` for the full registry with descriptions.

**Quick reference:**
- **systematic-debugging** — reproduce → investigate → hypothesize → fix → verify
- **test-driven-development** — write test first → watch it fail → implement → verify
- **code-review** — understand → check logic → check edge cases → suggest
- **writing-plans** — scope → break down → sequence → validate

---
*Powered by [borg](https://github.com/bensargotest-sys/guild-tools) — collective intelligence for AI agents.*
```

### The Pack Index (references/pack-index.md)

```markdown
# Borg Pack Index

| Pack | Problem Class | Confidence | Use When |
|------|--------------|-----------|----------|
| systematic-debugging | debugging | tested | Agent stuck debugging, >3 failed attempts |
| test-driven-development | testing | tested | Need to write tests or implement TDD |
| code-review | code-review | inferred | Reviewing code changes for bugs/quality |
| writing-plans | planning | inferred | Breaking down complex tasks into steps |
| github-pr-workflow | github | inferred | Managing GitHub PRs from creation to merge |
| codebase-inspection | inspect | inferred | Understanding an unfamiliar codebase |
| ... | ... | ... | ... |

To use a pack: `read references/packs/<pack-name>.md`
```

### Individual Pack Reference Files (references/packs/<name>.md)

Each pack is converted to a full markdown file preserving ALL intelligence:

```markdown
# Systematic Debugging

**Confidence:** tested | **Problem class:** debugging

## When to Use

Look for: TypeError, AttributeError, unexpected None, test failures
🎯 Start with: the CALLER of the failing function — trace upstream
⚠️ Avoid: the method definition itself, adding None checks at the symptom

## Required Inputs

- Reproducible error or failing test
- Access to the codebase

## Phases

### Phase 1: Reproduce
Reproduce the bug consistently. Capture exact error, stack trace, steps to trigger.
Run the failing test in isolation with verbose output.
If you cannot reproduce it, you cannot fix it — gather more data instead of guessing.

⚠️ Do NOT: guess at fixes before reproducing
⚠️ Do NOT: add broad try/except blocks to hide the error

✅ Before moving on: You can trigger the exact error on demand

### Phase 2: Investigate Root Cause
[... full phase content preserved ...]

## Examples

**Problem:** Agent spent 20 minutes trying random fixes for a TypeError
**Solution:** Pack forced reproduce → investigate flow. Stack trace showed wrong argument order.
**Outcome:** 4 minutes vs 20 minutes. One targeted fix vs 6 reverted attempts.

## Escalation

After 5 attempts without progress: ask the human for guidance.

---
*Confidence: tested | Evidence: tested across 10+ agents | Author: agent://hermes*
```

---

## 3. BORG PACK → OPENCLAW CONVERTER

### File: `borg/core/openclaw_converter.py`

This module converts borg workflow packs into OpenClaw-compatible format.

```python
"""
Borg → OpenClaw Converter — converts borg pack registry to OpenClaw skill format.

Exports:
    convert_pack_to_openclaw_ref()  — convert single pack to reference markdown
    convert_registry_to_openclaw()  — convert entire registry to skill directory
    generate_pack_index()           — generate references/pack-index.md
    generate_bridge_skill()        — generate main SKILL.md (the bridge)
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
```

---

## 4. MCP SERVER EXTENSIONS

### New Tool: `borg_sync`

Syncs the borg pack registry to OpenClaw's skills directory.

```python
TOOL_DEFINITION_BORG_SYNC = {
    "name": "borg_sync",
    "description": (
        "Sync borg workflow packs to OpenClaw's skills directory. "
        "Converts all borg packs to the hybrid bridge format and copies them to ~/.openclaw/skills/borg/. "
        "After syncing, OpenClaw agents can access borg packs via the 'borg' skill. "
        "Run this after borg pack updates to refresh the OpenClaw integration."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["sync", "status", "clean"],
                "description": "'sync' pushes packs to OpenClaw, 'status' shows current state, 'clean' removes installed skill",
                "default": "sync",
            },
            "openclaw_dir": {
                "type": "string",
                "description": "OpenClaw skills directory (defaults to ~/.openclaw/skills)",
                "default": "~/.openclaw/skills",
            },
        },
        "required": ["action"],
    },
}
```

### New Tool: `borg_list_openclaw`

Lists what's currently installed in OpenClaw's skills directory.

```python
TOOL_DEFINITION_BORG_LIST_OPENCLAW = {
    "name": "borg_list_openclaw",
    "description": (
        "List all skills currently installed in OpenClaw's skills directory. "
        "Shows which borg packs are available and their sync status."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "openclaw_dir": {
                "type": "string",
                "description": "OpenClaw skills directory (defaults to ~/.openclaw/skills)",
                "default": "~/.openclaw/skills",
            },
        },
    },
}
```

### Implementation in `borg/integrations/mcp_server.py`

Add to the TOOLS list and implement the dispatch:

```python
# In TOOLS list (add after borg_convert):
TOOLS: List[Dict[str, Any]] = [
    # ... existing 10 tools ...
    {
        "name": "borg_sync",
        "description": "...",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["sync", "status", "clean"], "default": "sync"},
                "openclaw_dir": {"type": "string", "default": "~/.openclaw/skills"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "borg_list_openclaw",
        "description": "...",
        "inputSchema": {
            "type": "object",
            "properties": {
                "openclaw_dir": {"type": "string", "default": "~/.openclaw/skills"},
            },
        },
    },
]

# New tool implementations:
def borg_sync(action: str = "sync", openclaw_dir: str = "~/.openclaw/skills") -> str:
    """Sync borg packs to OpenClaw skills directory."""
    try:
        from borg.core.openclaw_converter import convert_registry_to_openclaw
        from borg.core.uri import resolve_guild_uri, fetch_with_retry
        from borg.core.schema import parse_workflow_pack
        import yaml

        openclaw_path = Path(openclaw_dir).expanduser()

        if action == "status":
            borg_skill_dir = openclaw_path / "borg"
            if borg_skill_dir.exists():
                refs_dir = borg_skill_dir / "references" / "packs"
                pack_count = len(list(refs_dir.glob("*.md"))) if refs_dir.exists() else 0
                return json.dumps({
                    "success": True,
                    "installed": True,
                    "pack_count": pack_count,
                    "path": str(borg_skill_dir),
                })
            else:
                return json.dumps({
                    "success": True,
                    "installed": False,
                    "pack_count": 0,
                    "path": str(borg_skill_dir),
                })

        elif action == "clean":
            borg_skill_dir = openclaw_path / "borg"
            import shutil
            if borg_skill_dir.exists():
                shutil.rmtree(borg_skill_dir)
                return json.dumps({
                    "success": True,
                    "action": "cleaned",
                    "removed_path": str(borg_skill_dir),
                })
            else:
                return json.dumps({
                    "success": True,
                    "action": "already_clean",
                    "path": str(borg_skill_dir),
                })

        elif action == "sync":
            # Load all packs from registry
            packs = []
            pack_urls = [
                "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/index.json"
            ]

            # Fetch index to get pack list
            index_url = "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/index.json"
            index_content, err = fetch_with_retry(index_url)
            if err:
                return json.dumps({"success": False, "error": f"Failed to fetch index: {err}"})

            index_data = json.loads(index_content)
            pack_list = index_data.get("packs", [])

            # Load each pack
            for pack_entry in pack_list:
                pack_name = pack_entry.get("name", "")
                pack_url = f"https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/{pack_name}.workflow.yaml"
                content, err = fetch_with_retry(pack_url)
                if err:
                    continue  # Skip failed packs, don't fail the whole sync
                try:
                    pack = parse_workflow_pack(content)
                    packs.append(pack)
                except ValueError:
                    continue

            # Convert and write
            output_dir = openclaw_path / "borg"
            result = convert_registry_to_openclaw(packs, output_dir, overwrite=True)
            result["action"] = "synced"
            return json.dumps(result)

        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "type": type(e).__name__})


def borg_list_openclaw(openclaw_dir: str = "~/.openclaw/skills") -> str:
    """List all skills installed in OpenClaw directory."""
    try:
        openclaw_path = Path(openclaw_dir).expanduser()
        if not openclaw_path.exists():
            return json.dumps({"success": True, "skills": [], "path": str(openclaw_path)})

        skills = []
        for skill_dir in openclaw_path.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                has_skill_md = skill_md.exists()
                ref_count = 0
                refs_dir = skill_dir / "references" / "packs"
                if refs_dir.exists():
                    ref_count = len(list(refs_dir.glob("*.md")))

                skills.append({
                    "name": skill_dir.name,
                    "path": str(skill_dir),
                    "has_skill_md": has_skill_md,
                    "pack_reference_count": ref_count,
                })

        return json.dumps({
            "success": True,
            "skills": skills,
            "path": str(openclaw_path),
            "total": len(skills),
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

### Tool Dispatch Update

```python
# In _call_tool_impl(), add:
elif name == "borg_sync":
    return borg_sync(
        action=arguments.get("action", "sync"),
        openclaw_dir=arguments.get("openclaw_dir", "~/.openclaw/skills"),
    )
elif name == "borg_list_openclaw":
    return borg_list_openclaw(
        openclaw_dir=arguments.get("openclaw_dir", "~/.openclaw/skills"),
    )
```

---

## 5. CLI EXTENSION

### New Command: `borg openclaw`

```bash
borg openclaw sync        # Sync borg packs to ~/.openclaw/skills/borg/
borg openclaw status      # Show current OpenClaw installation status
borg openclaw clean       # Remove borg skill from OpenClaw directory
borg openclaw list        # List all skills in ~/.openclaw/skills/
```

### Implementation (add to `borg/cli.py`)

```python
# In main() argparse, add:
p = sub.add_parser("openclaw", help="OpenClaw integration commands")
openclaw_sub = p.add_subparsers(dest="openclaw_command", required=True)

sync_p = openclaw_sub.add_parser("sync", help="Sync borg packs to OpenClaw")
sync_p.add_argument("--openclaw-dir", default="~/.openclaw/skills")
sync_p.set_defaults(func=_cmd_openclaw_sync)

status_p = openclaw_sub.add_parser("status", help="Show OpenClaw installation status")
status_p.add_argument("--openclaw-dir", default="~/.openclaw/skills")
status_p.set_defaults(func=_cmd_openclaw_status)

clean_p = openclaw_sub.add_parser("clean", help="Remove borg from OpenClaw")
clean_p.add_argument("--openclaw-dir", default="~/.openclaw/skills")
clean_p.set_defaults(func=_cmd_openclaw_clean)

list_p = openclaw_sub.add_parser("list", help="List OpenClaw skills")
list_p.add_argument("--openclaw-dir", default="~/.openclaw/skills")
list_p.set_defaults(func=_cmd_openclaw_list)


def _cmd_openclaw_sync(args) -> int:
    """Sync borg packs to OpenClaw directory."""
    from borg.core.openclaw_converter import convert_registry_to_openclaw
    from borg.core.uri import fetch_with_retry
    from borg.core.schema import parse_workflow_pack
    import json

    openclaw_path = Path(args.openclaw_dir).expanduser()

    # Fetch index
    index_url = "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/index.json"
    index_content, err = fetch_with_retry(index_url)
    if err:
        print(f"Error: Failed to fetch pack index: {err}", file=sys.stderr)
        return 1

    index_data = json.loads(index_content)
    pack_list = index_data.get("packs", [])

    print(f"Found {len(pack_list)} packs in registry...")

    # Load each pack
    packs = []
    for pack_entry in pack_list:
        pack_name = pack_entry.get("name", "")
        pack_url = f"https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/{pack_name}.workflow.yaml"
        content, err = fetch_with_retry(pack_url)
        if err:
            print(f"  Skipping {pack_name}: {err}", file=sys.stderr)
            continue
        try:
            pack = parse_workflow_pack(content)
            packs.append(pack)
            print(f"  Loaded: {pack_name}")
        except ValueError as e:
            print(f"  Skipping {pack_name}: {e}", file=sys.stderr)

    # Convert and write
    output_dir = openclaw_path / "borg"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = convert_registry_to_openclaw(packs, output_dir, overwrite=True)

    print(f"\nSynced {result['total_packs']} packs to {output_dir}")
    print(f"Files created: {result['total_size_bytes']:,} bytes total")
    for f in result["files_created"]:
        print(f"  - {f}")

    return 0


def _cmd_openclaw_status(args) -> int:
    """Show OpenClaw installation status."""
    from borg.integrations.mcp_server import borg_sync
    import json

    result = borg_sync(action="status", openclaw_dir=args.openclaw_dir)
    data = json.loads(result)
    if data["installed"]:
        print(f"✓ Borg skill installed at: {data['path']}")
        print(f"  Pack references: {data['pack_count']}")
    else:
        print(f"✗ Borg skill not installed at: {data['path']}")
        print(f"  Run: borg openclaw sync")
    return 0


def _cmd_openclaw_clean(args) -> int:
    """Remove borg from OpenClaw directory."""
    from borg.integrations.mcp_server import borg_sync
    import json

    result = borg_sync(action="clean", openclaw_dir=args.openclaw_dir)
    data = json.loads(result)
    print(f"✓ {data['action']}: {data['removed_path']}")
    return 0


def _cmd_openclaw_list(args) -> int:
    """List all skills in OpenClaw directory."""
    from borg.integrations.mcp_server import borg_list_openclaw
    import json

    result = borg_list_openclaw(openclaw_dir=args.openclaw_dir)
    data = json.loads(result)
    print(f"Skills in {data['path']}:")
    for skill in data["skills"]:
        ref_info = f" ({skill['pack_reference_count']} packs)" if skill["pack_reference_count"] else ""
        print(f"  - {skill['name']}{ref_info}")
    if not data["skills"]:
        print("  (none)")
    return 0
```

---

## 6. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OpenClaw Agent Runtime                               │
│                                                                             │
│  Pi agent is STUCK / needs structure                                        │
│           │                                                                  │
│           ▼                                                                  │
│  OpenClaw skill list → matches "borg" skill (description trigger)          │
│           │                                                                  │
│           ▼                                                                  │
│  Pi agent reads SKILL.md                                                    │
│           │                                                                  │
│           ▼                                                                  │
│  → Step 1: read references/pack-index.md    [all 23 packs listed]         │
│           │                                                                  │
│           ▼                                                                  │
│  → Step 2: read references/packs/<name>.md  [full pack with phases]         │
│           │                                                                  │
│           ▼                                                                  │
│  Agent follows phases IN ORDER with checkpoints                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ borg openclaw sync
                                    │ (periodic refresh)
┌────────────────────────────────────┼────────────────────────────────────────┐
│                                      │                                        │
│  ~/.openclaw/skills/borg/           │  ~/.hermes/guild/packs/                │
│  ├── SKILL.md                       │  ├── index.json (remote)               │
│  ├── references/                    │  ├── systematic-debugging.workflow.yaml │
│  │   ├── pack-index.md              │  ├── test-driven-development.yaml      │
│  │   └── packs/                     │  └── ... (23 packs)                     │
│  │       ├── systematic-debugging.md │                                        │
│  │       ├── test-driven-dev.md      │                                        │
│  │       └── ...                    │                                        │
│                                      │                                        │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                                       │ borg_sync (MCP tool)
                                       │ or borg openclaw sync (CLI)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Borg Pack Registry                                      │
│  Bensargotest-sys/guild-packs on GitHub                                      │
│  index.json + 23 *.workflow.yaml packs                                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. API ENDPOINTS (MCP Tools)

### Full Tool List (12 total after adding 2)

| Tool | Purpose | Key Params |
|------|---------|-----------|
| `borg_search` | Find packs by keyword/semantic | `query`, `mode` |
| `borg_pull` | Fetch and save pack locally | `uri` |
| `borg_try` | Preview pack without saving | `uri` |
| `borg_init` | Scaffold a new pack | `pack_name`, `problem_class` |
| `borg_apply` | Execute pack with session tracking | `action`, `pack_name`, `task` |
| `borg_publish` | Publish pack or feedback | `action`, `pack_name` |
| `borg_feedback` | Generate feedback from session | `session_id` |
| `borg_suggest` | Auto-suggest pack from frustration | `context`, `failure_count` |
| `borg_observe` | Silent guidance on task start | `task`, `context` |
| `borg_convert` | Convert SKILL.md → pack | `path`, `format` |
| **`borg_sync`** | **Push packs to OpenClaw** | `action`, `openclaw_dir` |
| **`borg_list_openclaw`** | **List OpenClaw skills** | `openclaw_dir` |

### `borg_sync` — Return Values

**action=sync:**
```json
{
  "success": true,
  "action": "synced",
  "total_packs": 23,
  "files_created": [
    "SKILL.md",
    "references/pack-index.md",
    "references/packs/systematic-debugging.md",
    ...
  ],
  "total_size_bytes": 142384,
  "output_dir": "/home/user/.openclaw/skills/borg"
}
```

**action=status:**
```json
{
  "success": true,
  "installed": true,
  "pack_count": 23,
  "path": "/home/user/.openclaw/skills/borg"
}
```

**action=clean:**
```json
{
  "success": true,
  "action": "cleaned",
  "removed_path": "/home/user/.openclaw/skills/borg"
}
```

---

## 8. STEP-BY-STEP IMPLEMENTATION PLAN

### Phase 1: Core Converter (Day 1)
- [ ] Create `borg/core/openclaw_converter.py` with:
  - `convert_pack_to_openclaw_ref()`
  - `generate_pack_index()`
  - `generate_bridge_skill()`
  - `convert_registry_to_openclaw()`
  - `_extract_slug()`, `_validate_openclaw_name()`
- [ ] Add `PROBLEM_CLASS_EMOJI` and `BRIDGE_SKILL_TEMPLATE` constants
- [ ] Write unit tests in `borg/tests/test_openclaw_converter.py`

### Phase 2: MCP Server Integration (Day 1-2)
- [ ] Add `borg_sync` tool definition to TOOLS list
- [ ] Add `borg_list_openclaw` tool definition to TOOLS list
- [ ] Implement `borg_sync()` function
- [ ] Implement `borg_list_openclaw()` function
- [ ] Add dispatch cases in `_call_tool_impl()`
- [ ] Update test file `test_mcp_server.py` with new tool tests

### Phase 3: CLI Integration (Day 2)
- [ ] Add `borg openclaw` subcommand parser in `cli.py`
- [ ] Implement `_cmd_openclaw_sync()`
- [ ] Implement `_cmd_openclaw_status()`
- [ ] Implement `_cmd_openclaw_clean()`
- [ ] Implement `_cmd_openclaw_list()`

### Phase 4: Testing & Validation (Day 2-3)
- [ ] Verify all 23 packs convert without error
- [ ] Verify generated SKILL.md passes OpenClaw's `quick_validate.py`
- [ ] Run existing test suite to confirm no regressions
- [ ] Test `borg openclaw sync` end-to-end on a machine with OpenClaw

### Phase 5: Documentation (Day 3)
- [ ] Update `docs/OPENCLAW_SETUP.md` with new CLI commands
- [ ] Update `docs/OPENCLAW_CONVERSION.md` (from PRD v2, already has full details)
- [ ] Add examples for each `borg_sync` action

---

## 9. FILE MANIFEST

### Files to CREATE

| File | Purpose |
|------|---------|
| `borg/core/openclaw_converter.py` | Pack → OpenClaw conversion engine |
| `borg/tests/test_openclaw_converter.py` | Unit tests for converter |
| `docs/OPENCLAW_IMPLEMENTATION_SPEC.md` | This spec |

### Files to MODIFY

| File | Changes |
|------|---------|
| `borg/integrations/mcp_server.py` | Add `borg_sync`, `borg_list_openclaw` tools + dispatch |
| `borg/cli.py` | Add `borg openclaw sync/status/clean/list` commands |

### Files Already Complete (No Changes Needed)

| File | Notes |
|------|-------|
| `borg/core/convert.py` | Already converts SKILL.md → pack (opposite direction) |
| `borg/core/search.py` | Already handles pack search/discovery |
| `borg/core/schema.py` | Already handles pack validation |
| `borg/core/uri.py` | Already handles URI resolution |

---

## 10. VALIDATION CHECKLIST

### Functional Tests (must all pass)
- [ ] `convert_pack_to_openclaw_ref()` produces valid markdown for all 23 packs
- [ ] `generate_pack_index()` lists all 23 packs correctly
- [ ] `generate_bridge_skill()` produces SKILL.md < 200 lines with description ≤ 1024 chars
- [ ] `convert_registry_to_openclaw()` creates correct directory structure
- [ ] `borg_sync` MCP tool executes without errors
- [ ] `borg openclaw sync` CLI command completes successfully
- [ ] `borg_list_openclaw` returns correct installed skill list

### Quality Metrics (measure and report)
- [ ] Phase preservation: phases_in_ref / phases_in_pack ≥ 0.95
- [ ] Anti-pattern preservation: anti_patterns_in_ref / anti_patterns_in_pack ≥ 0.95
- [ ] Example preservation: examples_in_ref / examples_in_pack = 1.0
- [ ] Total skill directory size < 256KB

### Regression Tests (must not break)
- [ ] All 1037 existing borg tests pass
- [ ] `borg search`, `borg pull`, `borg try` still work correctly
- [ ] MCP server `initialize`, `tools/list`, `tools/call` still work

---

## 11. OPEN QUESTIONS (Resolved)

| Question | Resolution |
|----------|-----------|
| Per-pack vs hybrid bridge? | **Hybrid bridge** — single "borg" skill, pack references |
| How does the Pi agent find packs? | Reads `references/pack-index.md` from the borg skill |
| How does the Pi agent load a pack? | Uses OpenClaw's `read` tool on `references/packs/<name>.md` |
| How many OpenClaw skills created? | **1** (the "borg" bridge skill) |
| What happens when packs update? | Re-run `borg openclaw sync` to refresh |
| What about ClawHub publishing? | v2 feature — requires MIT-0 licensing + ClawHub account |
