# PRD: Borg Pack → OpenClaw Skill Converter
## Product Requirements Document + Engineering Spec
## Version: 1.0 | Date: 2026-03-28

---

## 1. GOAL

Convert borg workflow packs (YAML) into OpenClaw-compatible SKILL.md files that:
1. Can be dropped into `~/.openclaw/skills/<name>/` and work immediately
2. Can be published to ClawHub via `clawhub publish`
3. Preserve as much borg intelligence as possible (phases, examples, anti-patterns, failure memory)
4. Are indistinguishable from native OpenClaw skills to the end user

**Success = a converted borg pack that OpenClaw's `loadSkillsFromDir()` loads without errors and that the Pi agent model can read and follow.**

---

## 2. FORMAT ANALYSIS

### 2a. Borg Pack Format (source)

```yaml
type: workflow_pack           # always "workflow_pack"
version: "1.0"                # schema version
id: guild://hermes/test-driven-development  # URI identifier
problem_class: testing        # task category
mental_model: systematic      # approach archetype
confidence: tested            # guessed|inferred|tested|validated
required_inputs:              # what the agent needs to start
  - "codebase path"
  - "feature description"
phases:                       # ordered execution steps
  - name: phase_name
    description: "What to do in this phase"
    checkpoint: "What must be true before moving on"
    anti_patterns:
      - "What NOT to do"
    prompts: []               # additional prompts
    skip_if: "condition"      # conditional skip
    inject_if: "condition"    # conditional inject
    context_prompts: []       # context-dependent prompts
examples:                     # problem/solution/outcome triples
  - problem: "Agent spent 20 min on random fixes"
    solution: "Pack forced systematic approach"
    outcome: "4 min vs 20 min"
escalation_rules:             # when to give up
  max_iterations: 5
  on_failure: "ask_human"
provenance:                   # trust metadata
  author_agent: "agent://hermes"
  confidence: tested
  evidence: "tested across 10 agents"
  failure_cases: ["edge case X"]
  created: "2026-01-15"
  updated: "2026-03-28"
start_signals:                # what triggers this pack
  look_for: ["test", "tdd"]
  start_here: "the test file"
  avoid: ["implementation first"]
```

### 2b. OpenClaw SKILL.md Format (target)

```markdown
---
name: skill-name              # required, /^[a-z0-9-]+$/, max 64 chars
description: "When to use..." # required, max 1024 chars
user-invocable: true          # optional, default true
metadata: {"openclaw": {...}} # optional, single-line JSON
---

# Skill Title

Free-form markdown body — instructions, examples, notes.
The model reads this and decides how to follow it.
No explicit "phases" — just well-structured instructions.
```

**Key differences:**
- Borg has structured phases with checkpoints → OpenClaw has free-form markdown
- Borg has anti_patterns per phase → OpenClaw has no formal anti-pattern mechanism
- Borg has provenance/confidence → OpenClaw has no equivalent (could go in body)
- Borg has examples → OpenClaw has no formal examples (could go in body)
- Borg has skip_if/inject_if → OpenClaw has gating via `requires` but not conditional phases

---

## 3. FIELD MAPPING

### 3a. Direct Mappings

| Borg Field | OpenClaw Field | Transform |
|-----------|---------------|-----------|
| `id` (last segment) | `name` | Extract slug from URI, validate `/^[a-z0-9-]+$/` |
| `problem_class` + summary | `description` | Compose: "Use when {problem_class}. {mental_model} approach. Confidence: {confidence}." Max 1024 chars |
| `version` | body mention | No frontmatter field; mention in body |
| `provenance.confidence` | body section | "## Confidence: {tested}" |
| `provenance.evidence` | body section | Part of confidence section |

### 3b. Structural Transformations

| Borg Structure | OpenClaw Equivalent | How |
|---------------|-------------------|-----|
| `phases[]` | `## Phases` body section | Convert each phase to numbered step with description + checkpoint |
| `phases[].anti_patterns` | Inline warnings | "⚠️ Do NOT: {anti_pattern}" under each phase |
| `phases[].checkpoint` | Inline checkpoint | "✅ Before moving on: {checkpoint}" after each phase |
| `examples[]` | `## Examples` body section | Format as "**Problem:** ... **Solution:** ... **Outcome:** ..." |
| `start_signals` | `## When to Use` section | "Look for: {look_for}. Start with: {start_here}. Avoid: {avoid}" |
| `escalation_rules` | `## Escalation` section | "After {max_iterations} attempts: {on_failure}" |
| `required_inputs` | `## Required Inputs` section | Bulleted list |
| `mental_model` | `## Overview` section | "This skill uses a {mental_model} approach..." |

### 3c. Information Loss (unavoidable)

| Borg Feature | Why Lost | Mitigation |
|-------------|---------|-----------|
| `skip_if` / `inject_if` | OpenClaw has no conditional phase execution | Include as "Skip this step if: {condition}" text |
| `context_prompts` | No equivalent | Include in phase description |
| `provenance.created/updated` | No frontmatter field | Include in body footer |
| `provenance.author_agent` | No frontmatter field | Include in body footer |
| Reputation data | No equivalent | Not included |
| `type: workflow_pack` | Not needed | Skill type is implicit |

### 3d. Information Gain (OpenClaw-specific fields to add)

| OpenClaw Field | Value | Why |
|---------------|-------|-----|
| `user-invocable` | `true` | All borg packs should be user-invocable |
| `metadata.openclaw.emoji` | Auto-selected by problem_class | Decorative but helps discovery |
| `metadata.openclaw.homepage` | `https://github.com/bensargotest-sys/guild-packs` | Link back to borg |

---

## 4. CONVERSION ALGORITHM

```python
def convert_pack_to_openclaw_skill(pack: dict) -> tuple[str, dict]:
    """Convert borg pack YAML to OpenClaw SKILL.md content + directory structure.
    
    Returns:
        (skill_md_content: str, files: dict[str, str])
        files maps relative paths to content (e.g. {"SKILL.md": "...", "references/examples.md": "..."})
    """
    
    # 1. Extract name from pack ID
    pack_id = pack.get("id", "")
    name = extract_slug(pack_id)  # "guild://hermes/test-driven-development" → "test-driven-development"
    validate_name(name)  # /^[a-z0-9-]+$/, max 64 chars
    
    # 2. Build description (max 1024 chars)
    problem_class = pack.get("problem_class", "general")
    mental_model = pack.get("mental_model", "")
    confidence = pack.get("provenance", {}).get("confidence", pack.get("confidence", "inferred"))
    description = f"Use for {problem_class} tasks. "
    if mental_model:
        description += f"{mental_model.replace('-', ' ').title()} approach. "
    description += f"Confidence: {confidence}."
    description = description[:1024]
    
    # 3. Build metadata
    emoji = PROBLEM_CLASS_EMOJI.get(problem_class, "🧠")
    metadata = {
        "openclaw": {
            "emoji": emoji,
            "homepage": "https://github.com/bensargotest-sys/guild-packs"
        }
    }
    
    # 4. Build frontmatter
    frontmatter = f"""---
name: {name}
description: {description}
user-invocable: true
metadata: {json.dumps(metadata)}
---"""
    
    # 5. Build body
    body = build_body(pack)
    
    # 6. Combine
    skill_md = frontmatter + "\n\n" + body
    
    # 7. Build file structure
    files = {"SKILL.md": skill_md}
    
    # If examples are lengthy, put them in references/
    examples = pack.get("examples", [])
    if len(examples) > 3:
        examples_md = format_examples_reference(examples)
        files["references/examples.md"] = examples_md
    
    return name, files


def build_body(pack: dict) -> str:
    """Build the markdown body from pack data."""
    sections = []
    
    # Title
    name = extract_slug(pack.get("id", "unknown"))
    title = name.replace("-", " ").title()
    sections.append(f"# {title}")
    
    # Overview
    if pack.get("mental_model"):
        sections.append(f"\n## Overview\n\nThis uses a **{pack['mental_model']}** approach to {pack.get('problem_class', 'the task')}.")
    
    # When to Use
    start_signals = pack.get("start_signals", {})
    if start_signals:
        when_section = "\n## When to Use\n"
        if start_signals.get("look_for"):
            when_section += f"\nLook for: {', '.join(start_signals['look_for'])}"
        if start_signals.get("start_here"):
            when_section += f"\n\n🎯 **Start here:** {start_signals['start_here']}"
        if start_signals.get("avoid"):
            when_section += f"\n\n⚠️ **Avoid starting with:** {', '.join(start_signals['avoid'])}"
        sections.append(when_section)
    
    # Required Inputs
    required_inputs = pack.get("required_inputs", [])
    if required_inputs:
        inputs_section = "\n## Required Inputs\n"
        for inp in required_inputs:
            inputs_section += f"\n- {inp}"
        sections.append(inputs_section)
    
    # Phases (core content)
    phases = pack.get("phases", [])
    if phases:
        phases_section = "\n## Phases\n"
        for i, phase in enumerate(phases, 1):
            phase_name = phase.get("name", f"step_{i}")
            phase_title = phase_name.replace("_", " ").title()
            phases_section += f"\n### Phase {i}: {phase_title}\n"
            phases_section += f"\n{phase.get('description', '')}\n"
            
            # Anti-patterns
            anti_patterns = phase.get("anti_patterns", [])
            for ap in anti_patterns:
                phases_section += f"\n⚠️ **Do NOT:** {ap}"
            
            # Checkpoint
            checkpoint = phase.get("checkpoint")
            if checkpoint:
                phases_section += f"\n\n✅ **Before moving on:** {checkpoint}\n"
            
            # Skip/inject conditions
            if phase.get("skip_if"):
                phases_section += f"\n💡 Skip this step if: {phase['skip_if']}\n"
            if phase.get("inject_if"):
                phases_section += f"\n💡 Add this step if: {phase['inject_if']}\n"
        
        sections.append(phases_section)
    
    # Examples (inline if ≤3, reference if >3)
    examples = pack.get("examples", [])
    if examples and len(examples) <= 3:
        ex_section = "\n## Examples\n"
        for ex in examples:
            ex_section += f"\n**Problem:** {ex.get('problem', '')}\n"
            ex_section += f"**Solution:** {ex.get('solution', '')}\n"
            ex_section += f"**Outcome:** {ex.get('outcome', '')}\n"
        sections.append(ex_section)
    elif examples:
        sections.append("\n## Examples\n\nSee `references/examples.md` for detailed examples.\n")
    
    # Escalation
    escalation = pack.get("escalation_rules", {})
    if escalation:
        esc_section = "\n## Escalation\n"
        if escalation.get("max_iterations"):
            esc_section += f"\nAfter **{escalation['max_iterations']}** attempts without progress:"
        if escalation.get("on_failure"):
            esc_section += f"\n- {escalation['on_failure']}"
        sections.append(esc_section)
    
    # Confidence/Provenance footer
    provenance = pack.get("provenance", {})
    if provenance:
        prov_section = "\n---\n\n## Provenance\n"
        prov_section += f"\n- **Confidence:** {provenance.get('confidence', 'inferred')}"
        if provenance.get("evidence"):
            prov_section += f"\n- **Evidence:** {provenance['evidence']}"
        if provenance.get("failure_cases"):
            prov_section += f"\n- **Known failure cases:** {', '.join(provenance['failure_cases'])}"
        if provenance.get("author_agent"):
            prov_section += f"\n- **Author:** {provenance['author_agent']}"
        sections.append(prov_section)
    
    # Attribution
    sections.append("\n---\n*Generated by [borg](https://github.com/bensargotest-sys/guild-tools) — collective intelligence for AI agents.*")
    
    return "\n".join(sections)
```

---

## 5. EVAL CRITERIA

### 5a. Functional Evals (automated — must all pass)

| ID | Test | Pass Criteria |
|----|------|--------------|
| F1 | Frontmatter `name` validation | `/^[a-z0-9-]+$/`, no leading/trailing hyphens, max 64 chars |
| F2 | Frontmatter `description` length | ≤ 1024 chars, no angle brackets |
| F3 | SKILL.md total size | ≤ 256KB (OpenClaw enforced limit) |
| F4 | OpenClaw `quick_validate.py` passes | Run OpenClaw's own validator against output |
| F5 | YAML frontmatter parses | `yaml.safe_load()` on frontmatter block succeeds |
| F6 | All 21 borg packs convert without error | Zero crashes on full registry |
| F7 | Round-trip name extraction | `extract_slug(pack_id)` produces valid OpenClaw name for all packs |
| F8 | Metadata JSON is valid | `json.loads(metadata_line)` succeeds |
| F9 | Output directory structure valid | `SKILL.md` exists, optional `references/`, `scripts/`, `assets/` |
| F10 | No PII/secrets in output | No API keys, tokens, or personal data |

### 5b. Quality Evals (automated — measure, don't gate)

| ID | Test | Metric | Target |
|----|------|--------|--------|
| Q1 | Phase preservation | phases_in_output / phases_in_input | ≥ 0.95 |
| Q2 | Anti-pattern preservation | anti_patterns_in_output / anti_patterns_in_input | ≥ 0.95 |
| Q3 | Example preservation | examples_in_output / examples_in_input | 1.0 |
| Q4 | Body word count | words in output body | 100-5000 (OpenClaw best practice) |
| Q5 | Description informativeness | description contains problem_class AND confidence | 1.0 |
| Q6 | Checkpoint preservation | checkpoints_in_output / checkpoints_in_input | ≥ 0.95 |

### 5c. Integration Evals (manual — verify once)

| ID | Test | How |
|----|------|-----|
| I1 | OpenClaw loads skill | Copy to `~/.openclaw/skills/`, run `openclaw`, verify no load errors |
| I2 | Skill appears in skill list | `openclaw skills list` shows the converted skill |
| I3 | Model can read and follow | Send a task matching the skill's problem_class, verify model references it |
| I4 | ClawHub publish succeeds | `clawhub publish ./output --slug test-pack --name "Test" --version 0.1.0` |
| I5 | ClawHub search finds it | `clawhub search "debugging"` returns the published skill |

### 5d. Regression Evals

| ID | Test | Pass Criteria |
|----|------|--------------|
| R1 | Existing borg tests pass | 1037 tests, 0 failures |
| R2 | Existing convert.py tests pass | No regression in SKILL→pack conversion |
| R3 | CLI `borg convert --format=openclaw` works | New format option doesn't break existing formats |

---

## 6. IMPLEMENTATION SPEC

### 6a. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `borg/core/convert.py` | MODIFY | Add `convert_pack_to_openclaw()` function |
| `borg/cli.py` | MODIFY | Add `--format=openclaw` to convert command |
| `borg/integrations/mcp_server.py` | MODIFY | Add `format="openclaw"` to `borg_convert` tool |
| `borg/tests/test_convert_openclaw.py` | CREATE | All F* and Q* evals as pytest tests |
| `docs/OPENCLAW_CONVERSION.md` | CREATE | User-facing docs |

### 6b. CLI Interface

```bash
# Convert a single pack
borg convert path/to/pack.yaml --format=openclaw --output ./output/

# Convert all packs in registry
borg convert --all --format=openclaw --output ./openclaw-skills/

# Convert and publish to ClawHub (future)
borg convert path/to/pack.yaml --format=openclaw --publish
```

### 6c. MCP Tool Interface

```json
{
    "name": "borg_convert",
    "arguments": {
        "path": "path/to/pack.yaml",
        "format": "openclaw"
    }
}
```

Returns:
```json
{
    "success": true,
    "output_dir": "./openclaw-skills/systematic-debugging/",
    "files": ["SKILL.md", "references/examples.md"],
    "validation": {
        "name_valid": true,
        "description_length": 87,
        "total_size_bytes": 3420,
        "quick_validate_pass": true
    }
}
```

### 6d. Emoji Mapping

```python
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
```

---

## 7. EDGE CASES

| Case | Handling |
|------|---------|
| Pack ID with no `/` | Use entire ID as name |
| Pack ID with special chars | Strip non `[a-z0-9-]`, validate result |
| Empty phases list | Output "No structured phases. Follow the description." |
| Very long phase descriptions (>2000 chars) | Truncate to 2000 chars with "..." |
| Pack with no examples | Skip Examples section |
| Pack with >10 examples | Put in `references/examples.md` |
| Rubric packs (critique_rubric type) | Different conversion: rubric criteria → sections |
| Pack with `skip_if`/`inject_if` | Include as text guidance, not executable logic |
| Name collision (two packs → same slug) | Append problem_class: "debugging-systematic" |
| SKILL.md > 256KB | Split into main + references |

---

## 8. DEPENDENCIES

| Dependency | Status | Notes |
|-----------|--------|-------|
| OpenClaw `quick_validate.py` | Available at `/tmp/openclaw-analysis/skills/skill-creator/scripts/quick_validate.py` | Copy to test fixtures |
| `clawhub` CLI | Not installed | `npm install -g clawhub@latest` for I4/I5 evals |
| OpenClaw runtime | Not installed | Needed only for I1-I3 manual evals |

---

## 9. NOT IN SCOPE (v1)

- Auto-publish to ClawHub (v2 feature)
- Bi-directional conversion (OpenClaw skill → borg pack already exists in convert.py)
- OpenClaw `install` spec generation (requires/bins/env)
- Skill versioning sync with pack provenance
- Conditional phase logic translation (no OpenClaw equivalent)

---

## 10. ACCEPTANCE CRITERIA

**v1 ships when:**
1. All 21 borg packs convert to valid SKILL.md files (F6)
2. OpenClaw's `quick_validate.py` passes on all outputs (F4)
3. All F* tests pass (automated)
4. Q1-Q6 metrics meet targets (measured)
5. At least 1 converted skill loads in OpenClaw (I1 — manual, can be deferred)
6. 1037+ tests pass, 0 regressions (R1-R3)
7. CLI `borg convert --format=openclaw` works end-to-end
8. Documentation written

---

## 11. OPEN QUESTIONS

1. **ClawHub account**: Do we need a dedicated account to publish? (GitHub OAuth required, 14-day account age)
2. **Licensing**: ClawHub requires MIT-0 for published skills. Are borg packs MIT-0 compatible?
3. **Naming convention**: Should converted skills have a `borg-` prefix for discoverability? (e.g., `borg-systematic-debugging`)
4. **Update strategy**: When a borg pack improves, how do we push updates to ClawHub? (version bump + `clawhub sync`)
5. **Attribution**: How prominent should "Generated by borg" be? (footer vs. prominent notice)
