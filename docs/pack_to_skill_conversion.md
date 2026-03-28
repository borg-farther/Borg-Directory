# Pack → SKILL.md Conversion: Field Mapping & Required Transformations

## Overview

This document maps every field in a borg `workflow_pack` YAML to its equivalent in a Hermes `SKILL.md` file (YAML frontmatter + markdown body). It also documents what currently exists in `borg/core/convert.py`, what needs transformation, and what has no equivalent.

**Current convert.py direction**: SKILL.md → pack (Hermes → borg)
**Required direction for this task**: pack → SKILL.md (borg → Hermes)

---

## Section 1: Borg Pack YAML Structure

A `workflow_pack` has these top-level fields:

```yaml
type: workflow_pack              # always "workflow_pack" for workflow packs
schema_version: "1.0"             # optional, appears in some packs
version: "1.0.0"                  # pack version string
id: guild://hermes/name          # unique URI
problem_class: >                 # one-line or multi-line problem description
  Free-text description of when to use this pack
mental_model: >                  # free-text mental model / core principle
  One to several sentences
confidence: tested|inferred|...  # top-level sometimes, usually in provenance
required_inputs:                 # list of required input descriptors
  - 'task_description: what...'
escalation_rules:               # list of escalation rule strings
  - "If stuck after 2 attempts..."
failure_cases:                  # sometimes at top level, usually in provenance
  - "Case 1"
phases:                          # ordered list of phase objects
  - name: phase_name
    description: >              # markdown content for the phase
      Multi-line content...
    checkpoint: >               # success criteria for the phase
    anti_patterns: []           # list of anti-pattern strings
    prompts: []                 # list of prompt strings
    skip_if: []                 # conditional: conditions to skip this phase
    inject_if: []               # conditional: messages to inject
    context_prompts: []         # conditional: context-sensitive prompts
examples:                        # list of problem/solution/outcome triples
  - problem: "..."
    solution: "..."
    outcome: "..."
provenance:                     # authorship and evidence block
  author_agent: agent://...
  created: ISO timestamp
  updated: ISO timestamp
  evidence: >                   # free-text evidence for confidence
  confidence: tested|inferred|guessed|validated
  failure_cases: []             # list of failure case strings
start_signals:                  # error_pattern → guidance mappings
  - error_pattern: "Regex"
    start_here: [...]
    avoid: [...]
    reasoning: "..."
tags:                            # sometimes present as top-level field
  - tag1
```

---

## Section 2: Hermes SKILL.md Structure

```markdown
---
name: skill-name
description: One-line description of what the skill does
version: 1.0.0                  # optional
author: Author Name              # optional
license: MIT                      # optional
confidence: tested|inferred       # optional
evidence: "Free-text evidence..."  # optional
failure_cases:                    # optional
  - "Case 1"
metadata:                         # optional, Hermes-specific sub-keys
  hermes:
    tags: [Tag1, Tag2]
    related_skills: [skill1, skill2]
    homepage: https://...
prerequisites:                    # optional
  env_vars: [VAR1, VAR2]
  commands: [cmd1, cmd2]
platforms: [linux, macos]         # optional
dependencies: []                  # optional
---

# Skill Title

Use this skill when [context].

## Body Sections (## headers become structured content)

Content under each ## header is part of the markdown body.
```

---

## Section 3: Field-by-Field Mapping

### Top-Level Pack Fields → SKILL.md Frontmatter

| Pack Field | SKILL.md Field | Mapping Type | Notes |
|------------|----------------|--------------|-------|
| `id` (e.g. `guild://hermes/code-review`) | `name` (slugified) | Transform | Extract slug from `guild://hermes/NAME`, use lowercase hyphenated. `id: guild://hermes/code-review` → `name: code-review` |
| `problem_class` | `description` | Direct | Pack's `problem_class` is multi-line; SKILL `description` is one-line. Truncate or use first line. |
| `mental_model` | (body section) | Transform | No direct frontmatter equivalent. Becomes body content (e.g. "## Overview" or "## Core Principle") |
| `version` | `version` | Direct | Pass through unchanged |
| `confidence` (top-level) | `confidence` | Direct | Only if present at pack top-level; usually it's in `provenance` |
| `provenance.confidence` | `confidence` | Direct | `provenance.confidence` → frontmatter `confidence` |
| `provenance.evidence` | `evidence` | Direct | `provenance.evidence` → frontmatter `evidence` |
| `provenance.author_agent` | `author` | Transform | Strip `agent://` prefix, e.g. `agent://hermes/guild-team` → `Hermes Agent` |
| `provenance.created` | (not stored) | Drop | Creation date not stored in SKILL frontmatter |
| `provenance.updated` | (not stored) | Drop | Update date not stored in SKILL frontmatter |
| `provenance.failure_cases` | `failure_cases` | Direct | `provenance.failure_cases` → frontmatter `failure_cases` |
| `required_inputs` | (not stored) | Drop | Packs require this for proof gates; SKILL has no equivalent |
| `escalation_rules` | (not stored) | Drop | Packs require this; SKILL has no equivalent |
| `tags` (top-level) | `metadata.hermes.tags` | Transform | Pack `tags: [debug, testing]` → SKILL `metadata.hermes.tags: [debug, testing]` |
| `start_signals` | (not stored) | Drop | Error-pattern → guidance mapping; would need new skill body section |
| `examples` | (not stored) | Drop | Problem/solution/outcome triples stored in pack but not in SKILL |

### Phase-Level Pack Fields → SKILL.md Body

| Pack Phase Field | SKILL.md Equivalent | Mapping Type | Notes |
|-----------------|---------------------|--------------|-------|
| `phases[].name` | `## name` (header) | Direct | Pack phase `name: reproduce` → SKILL section `## Reproduce` |
| `phases[].description` | Body under `## name` | Direct | Multi-line markdown content; pass through unchanged |
| `phases[].checkpoint` | (not stored) | Drop | Success criteria for phase completion; SKILL has no checkpoint concept |
| `phases[].anti_patterns` | (not stored) | Drop | Anti-patterns are pack-specific workflow enforcement |
| `phases[].prompts` | (not stored) | Drop | Prompt strings for the phase; SKILL has no equivalent |
| `phases[].skip_if` | (not stored) | Drop | Conditional phase skipping; Hermes handles conditionals differently |
| `phases[].inject_if` | (not stored) | Drop | Conditional message injection |
| `phases[].context_prompts` | (not stored) | Drop | Context-sensitive prompts |

---

## Section 4: What Maps Directly (No Transformation)

These fields pass through from pack to SKILL frontmatter unchanged (or near-directly):

- `version` → `version`
- `provenance.confidence` → `confidence`
- `provenance.evidence` → `evidence`
- `provenance.failure_cases` → `failure_cases`
- `phases[].name` → `## Section Name` (slug → title case)
- `phases[].description` → body content under the section

---

## Section 5: What Needs Transformation

### 5.1 `id` → `name`

**Pack**: `id: guild://hermes/systematic-debugging`
**SKILL**: `name: systematic-debugging`

```python
# Extraction
slug = id.replace("guild://hermes/", "")  # "systematic-debugging"
name = slug.replace("-", "_")  # or keep hyphenated as name
```

### 5.2 `problem_class` → `description`

**Pack**: Multi-line problem description (can be 2-3 sentences)
**SKILL**: Single-line description

```python
# Take first line or sentence
description = problem_class.strip().split("\n")[0].strip()
if len(description) > 200:
    description = description[:197] + "..."
```

### 5.3 `mental_model` → Body Section

**Pack**: `mental_model` is a top-level field
**SKILL**: No equivalent frontmatter field; must become a body section (e.g., `## Overview` or `## Core Principle`)

```python
# Insert as first or early body section
body = f"## Overview\n\n{mental_model}\n\n" + existing_body
```

### 5.4 `provenance.author_agent` → `author`

**Pack**: `author_agent: agent://hermes/guild-team`
**SKILL**: `author: Hermes Agent`

```python
# Strip agent:// prefix, humanize
agent_id = provenance.get("author_agent", "")
if agent_id.startswith("agent://"):
    author = agent_id.split("/")[-1].replace("-", " ").title()
else:
    author = agent_id
```

### 5.5 `tags` → `metadata.hermes.tags`

**Pack**: `tags: [debugging, troubleshooting]`
**SKILL**: `metadata.hermes.tags: [debugging, troubleshooting]`

```python
# Restructure nested
metadata = {"hermes": {"tags": pack.get("tags", [])}}
```

### 5.6 `provenance.created`/`updated` → (drop)

These have no SKILL.md equivalent. The frontmatter has no date fields.

### 5.7 `required_inputs` → (drop)

Packs require `required_inputs` for proof-gate validation. SKILL.md has no equivalent; this constraint is not expressed in Hermes skills.

### 5.8 `escalation_rules` → (drop)

Same as `required_inputs` — pack-specific enforcement with no SKILL equivalent.

### 5.9 `examples` → (drop)

Pack `examples` (problem/solution/outcome triples) have no SKILL.md equivalent. This is pack-specific workflow metadata.

### 5.10 `start_signals` → (drop)

Error-pattern → guidance mappings in packs (`start_signals[].error_pattern`, `start_here`, `avoid`, `reasoning`) have no SKILL.md equivalent.

---

## Section 6: What Has No Equivalent in SKILL

These pack fields have no SKILL.md representation at all:

| Field | Why No Equivalent |
|-------|-------------------|
| `required_inputs` | Hermes skills are loaded on demand; no input contract needed |
| `escalation_rules` | Hermes handles escalation via different mechanisms |
| `phases[].checkpoint` | SKILL has no phase completion gates |
| `phases[].prompts` | Prompt strings are an internal pack mechanism |
| `phases[].anti_patterns` | Anti-pattern enforcement is pack-specific |
| `phases[].skip_if` / `inject_if` / `context_prompts` | Conditional phase extension has no SKILL equivalent |
| `start_signals` | Error-pattern → guidance is a pack execution feature |
| `examples` (problem/solution/outcome) | Workflow metadata not stored in SKILL |
| `provenance.created` / `updated` | No creation/update dates in SKILL frontmatter |
| `schema_version` | Pack-specific versioning detail |

---

## Section 7: Current convert.py Capabilities

**File**: `borg/core/convert.py`

**Supported conversions** (SKILL.md → pack, i.e., Hermes → borg):

| Function | Input | Output |
|----------|-------|--------|
| `convert_skill(path)` | `SKILL.md` (YAML frontmatter + markdown body) | `workflow_pack` dict |
| `convert_claude_md(path)` | `CLAUDE.md` (plain markdown) | `workflow_pack` dict |
| `convert_cursorrules(path)` | `.cursorrules` (markdown or JSON) | `workflow_pack` dict |
| `convert_auto(path)` | Auto-detects SKILL.md / CLAUDE.md / .cursorrules | `workflow_pack` dict |

**Key helpers** (from `borg/core/schema.py`):
- `parse_skill_frontmatter(text)` → `(frontmatter_dict, body_str)`
- `sections_to_phases(body)` → splits markdown `## headers` into phase objects

**What convert.py does NOT support**:
- `convert_pack_to_skill()` — no reverse conversion exists
- Any `workflow_pack` → `SKILL.md` direction
- Reading `workflow_pack` YAML files at all (only writes/generates them)

---

## Section 8: Required Implementation — `convert_pack_to_skill()`

To convert a pack to a SKILL.md file, the following steps are needed:

### 8.1 Signature

```python
def convert_pack_to_skill(pack: dict, name: str = None) -> str:
    """Convert a workflow pack dict into a SKILL.md string.

    Args:
        pack: Parsed workflow_pack dict
        name: Optional override for the skill name (defaults to pack id slug)

    Returns:
        A complete SKILL.md file content (YAML frontmatter + markdown body).
    """
```

### 8.2 Algorithm

```
1. Extract name from pack.id (guild://hermes/NAME → NAME)
2. Build frontmatter:
   - name: slug from id
   - description: first line of problem_class (max ~200 chars)
   - version: pack.version if present
   - confidence: provenance.confidence if present
   - evidence: provenance.evidence if present
   - failure_cases: provenance.failure_cases if present
   - author: humanize provenance.author_agent
   - metadata.hermes.tags: pack.tags if present
3. Build body:
   - If mental_model exists: prepend "## Overview\n\n{mental_model}\n\n---\n\n"
   - For each phase in phases:
     - Add "## {Phase Title}\n\n"
     - Add phase.description (which may contain markdown)
   - If examples exist (not in SKILL but could go in references):
     - Optionally add "## Examples\n\n" section with examples
4. Combine: "---\n{yaml.dump(frontmatter)}\n---\n\n{body}"
```

### 8.3 Frontmatter Construction

```python
frontmatter = {
    "name": pack_id_slug,
    "description": first_line_of(problem_class),
    "version": pack.get("version", "1.0.0"),
}
if provenance.get("confidence"):
    frontmatter["confidence"] = provenance["confidence"]
if provenance.get("evidence"):
    frontmatter["evidence"] = provenance["evidence"]
if provenance.get("failure_cases"):
    frontmatter["failure_cases"] = provenance["failure_cases"]
if pack.get("tags"):
    frontmatter["metadata"] = {"hermes": {"tags": pack["tags"]}}
if provenance.get("author_agent"):
    frontmatter["author"] = humanize_author(provenance["author_agent"])
```

### 8.4 Body Construction

```python
body_parts = []

# mental_model becomes Overview
if pack.get("mental_model"):
    body_parts.append("## Overview\n")
    body_parts.append(pack["mental_model"].strip())
    body_parts.append("\n\n---\n")

# Each phase becomes a ## section
for phase in pack.get("phases", []):
    name = phase.get("name", "phase")
    title = name.replace("_", " ").title()
    body_parts.append(f"## {title}\n\n")
    if phase.get("description"):
        body_parts.append(phase["description"].strip())
    body_parts.append("\n\n")
```

### 8.5 Lossy Fields (Information Lost in Conversion)

The following pack data **cannot** be represented in SKILL.md:

- `required_inputs` — dropped
- `escalation_rules` — dropped
- `phases[].checkpoint` — dropped
- `phases[].prompts` — dropped
- `phases[].anti_patterns` — dropped
- `phases[].skip_if` / `inject_if` / `context_prompts` — dropped
- `start_signals` — dropped
- `examples` (problem/solution/outcome) — dropped
- `provenance.created` / `updated` — dropped
- `schema_version` — dropped

**This is acceptable** because SKILL.md is a human-readable skill definition format, not an executable workflow format. The pack's enforcement machinery (checkpoints, proof gates, anti-patterns, escalation) is borg-specific.

---

## Section 9: Summary Comparison Table

| Pack Field | SKILL.md Field | Direction | Transformation Needed |
|------------|----------------|-----------|----------------------|
| `id` → slug | `name` | pack → skill | Yes: extract slug from URI |
| `problem_class` | `description` | pack → skill | Yes: first line only, ~200 char max |
| `mental_model` | (body: ## Overview) | pack → skill | Yes: move to body section |
| `version` | `version` | pack → skill | No: direct pass-through |
| `provenance.confidence` | `confidence` | pack → skill | No: direct |
| `provenance.evidence` | `evidence` | pack → skill | No: direct |
| `provenance.failure_cases` | `failure_cases` | pack → skill | No: direct |
| `provenance.author_agent` | `author` | pack → skill | Yes: strip agent://, humanize |
| `tags` | `metadata.hermes.tags` | pack → skill | Yes: nest under metadata.hermes |
| `phases[].name` | `## Name` | pack → skill | Yes: slug → title case |
| `phases[].description` | body content | pack → skill | No: direct markdown |
| `required_inputs` | (none) | pack → skill | Drop |
| `escalation_rules` | (none) | pack → skill | Drop |
| `phases[].checkpoint` | (none) | pack → skill | Drop |
| `phases[].anti_patterns` | (none) | pack → skill | Drop |
| `phases[].prompts` | (none) | pack → skill | Drop |
| `start_signals` | (none) | pack → skill | Drop |
| `examples` | (none) | pack → skill | Drop |
| `provenance.created/updated` | (none) | pack → skill | Drop |

---

## Appendix: Hermes SKILL.md Frontmatter Variants Observed

From the 6 skills reviewed, two frontmatter variants exist:

**Variant A — Full metadata** (excalidraw, systematic-debugging, xitter):
```yaml
name: skill-name
description: One-line description
version: 1.0.0
author: Author Name
license: MIT
confidence: tested
evidence: "Free-text evidence..."
failure_cases:
  - "Case 1"
metadata:
  hermes:
    tags: [...]
    related_skills: [...]
dependencies: []
prerequisites:
  env_vars: [...]
  commands: [...]
platforms: [...]
```

**Variant B — Minimal** (youtube-content, code-review):
```yaml
name: skill-name
description: One-line description
# Only name and description required
```

**Variant C — API-style** (notion):
```yaml
name: notion
description: Notion API for creating and managing...
version: 1.0.0
author: community
license: MIT
metadata:
  hermes:
    tags: [Notion, Productivity, Notes, Database, API]
    homepage: https://developers.notion.com
prerequisites:
  env_vars: [NOTION_API_KEY]
```

The only **required** frontmatter fields are `name` and `description`. All others are optional.
