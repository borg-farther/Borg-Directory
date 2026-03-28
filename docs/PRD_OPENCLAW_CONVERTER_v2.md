# PRD v2: Borg → OpenClaw Integration
## Revised after deep architecture analysis
## Version: 2.0 | Date: 2026-03-28

---

## WHY v1 WAS WRONG

The v1 PRD treated OpenClaw SKILL.md as a format conversion target — just translate borg YAML fields into markdown sections. Three fatal flaws:

1. **Phase enforcement doesn't exist in OpenClaw.** Borg's structured phases with checkpoints physically prevent skipping steps. SKILL.md is advisory markdown — the model can and will ignore numbered phases when stuck. Converting phases to markdown loses the enforcement that makes borg valuable.

2. **Description is the ONLY matching signal.** The Pi agent sees `<name> + <description> + <location>` in an XML skills list. The SKILL.md body is NOT in the system prompt — the model must `read()` it AFTER deciding the skill applies. Our proposed description ("Use for debugging tasks. systematic approach. Confidence: tested.") is generic garbage that won't trigger correctly.

3. **Size kills it.** OpenClaw recommends <500 lines. A rich borg pack with phases + examples + anti-patterns + start_signals converts to 1500+ lines. Trimming loses the intelligence that makes borg valuable.

**The fundamental mismatch:** Borg packs are executable workflows with enforcement. SKILL.md is advisory guidance. You can't make one into the other without losing what matters.

---

## THE CORRECT APPROACH: HYBRID

### Two-layer design:

**Layer 1: ONE "borg" OpenClaw skill (the bridge)**
A single skill that teaches OpenClaw's Pi agent WHEN and HOW to use borg. Lives at `~/.openclaw/skills/borg/SKILL.md`. This skill:
- Has a killer description that triggers on the right scenarios
- Explains how to invoke borg (CLI or read pack files)
- Contains the borg registry index so the model can discover packs
- Is <200 lines, well within OpenClaw limits

**Layer 2: Pack files in references/ (the intelligence)**
Each borg pack is stored as a readable file in the skill's `references/` directory. When the borg skill triggers, the model reads the appropriate pack file from `references/`. This preserves:
- Full phase structure with descriptions
- All anti-patterns and checkpoints
- Examples and start_signals
- Provenance and confidence data

### Why this is optimal:

| Concern | v1 (per-pack conversion) | v2 (hybrid bridge) |
|---------|------------------------|-------------------|
| Information loss | Critical — phases become suggestions | Zero — packs preserved as-is |
| Discovery | 21 mediocre descriptions | 1 excellent description |
| Maintenance | 21 skills to update | 1 skill + pack files |
| Context budget | 21 × ~200 chars = 4200 chars | 1 × ~200 chars = 200 chars |
| Size limit | Hits 500-line limit per pack | Main skill <200 lines |
| ClawHub publishing | 21 separate publishes | 1 publish with bundled references |
| Enforcement | Lost | Preserved (pack instructions intact) |

---

## DETAILED DESIGN

### The borg SKILL.md

```markdown
---
name: borg
description: "Use when your agent is stuck in a loop, burning tokens on a problem someone else already solved. Use when debugging takes >3 attempts, code review needs structure, or you need a proven approach for testing, planning, or deployment. Borg connects to collective agent intelligence — battle-tested workflows from thousands of agents. NOT for simple tasks that need no structure."
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

⚠️ **Critical:** The phases exist because agents that skip them fail. The checkpoints exist because agents that don't verify their work produce bad fixes. Trust the process.

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

### The pack-index.md (references/)

```markdown
# Borg Pack Index

| Pack | Problem Class | Confidence | Use When |
|------|-------------|-----------|----------|
| systematic-debugging | debugging | tested | Agent stuck debugging, >3 failed attempts |
| test-driven-development | testing | tested | Need to write tests or implement TDD |
| code-review | code-review | inferred | Reviewing code changes for bugs/quality |
| writing-plans | planning | inferred | Breaking down complex tasks into steps |
| ... | ... | ... | ... |

To use a pack: `read references/packs/<pack-name>.md`
```

### Pack files (references/packs/)

Each pack is converted to a markdown file that preserves ALL structure:

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

⚠️ Do NOT: guess at fixes without reproducing first
⚠️ Do NOT: add broad try/except blocks to hide the error

✅ Before moving on: You can trigger the exact error on demand

### Phase 2: Investigate Root Cause
[... full phase content preserved ...]

### Phase 3: Hypothesis and Minimal Test
[... full phase content preserved ...]

### Phase 4: Fix and Verify
[... full phase content preserved ...]

## Examples

**Problem:** Agent spent 20 minutes trying random fixes for a TypeError
**Solution:** Pack forced reproduce → investigate flow. Stack trace showed wrong argument order.
**Outcome:** 4 minutes vs 20 minutes. One targeted fix vs 6 reverted attempts.

[... more examples ...]

## Escalation

After 5 attempts without progress: ask the human for guidance.

---
*Confidence: tested | Evidence: tested across 10+ agents | Author: agent://hermes*
```

---

## CONVERSION ALGORITHM (v2)

```python
def convert_pack_registry_to_openclaw_skill(packs: list[dict]) -> dict[str, str]:
    """Convert entire borg pack registry to ONE OpenClaw skill with references.
    
    Returns:
        dict mapping file paths to content:
        {
            "SKILL.md": "...",
            "references/pack-index.md": "...",
            "references/packs/systematic-debugging.md": "...",
            "references/packs/code-review.md": "...",
            ...
        }
    """
    files = {}
    
    # 1. Generate main SKILL.md (the bridge)
    files["SKILL.md"] = generate_bridge_skill(packs)
    
    # 2. Generate pack index
    files["references/pack-index.md"] = generate_pack_index(packs)
    
    # 3. Convert each pack to a reference file
    for pack in packs:
        name = extract_slug(pack.get("id", ""))
        files[f"references/packs/{name}.md"] = convert_single_pack_to_md(pack)
    
    return files


def generate_bridge_skill(packs: list[dict]) -> str:
    """Generate the main SKILL.md with pack quick reference."""
    # Template with dynamic pack list
    # Description must be <1024 chars and trigger-optimized
    # Body must be <200 lines
    ...

def generate_pack_index(packs: list[dict]) -> str:
    """Generate references/pack-index.md with all packs listed."""
    # Table format: name | problem_class | confidence | use_when
    ...

def convert_single_pack_to_md(pack: dict) -> str:
    """Convert a single pack to a readable markdown file in references/packs/."""
    # Preserves ALL pack intelligence:
    # - Full phase descriptions with checkpoints
    # - All anti-patterns inline
    # - Start signals as "When to Use" section
    # - Examples
    # - Escalation rules
    # - Provenance
    # No size limit on reference files (256KB skill total limit applies)
    ...
```

---

## EVAL CRITERIA (v2)

### Functional (automated)

| ID | Test | Pass Criteria |
|----|------|--------------|
| F1 | Main SKILL.md frontmatter valid | name=/^[a-z0-9-]+$/, description≤1024 chars |
| F2 | Main SKILL.md < 200 lines | Stays well under OpenClaw 500-line recommendation |
| F3 | OpenClaw quick_validate.py passes on SKILL.md | Official validator succeeds |
| F4 | All 21 packs produce reference files | Zero conversion errors |
| F5 | Pack index lists all packs | count(index_entries) == count(packs) |
| F6 | Total skill directory < 256KB | OpenClaw hard limit |
| F7 | No PII in any output file | Automated scan |
| F8 | Reference file paths are valid | No spaces, special chars in filenames |

### Quality (automated metrics)

| ID | Test | Metric | Target |
|----|------|--------|--------|
| Q1 | Phase preservation in reference files | phases_out / phases_in | 1.0 (zero loss) |
| Q2 | Anti-pattern preservation | anti_patterns_out / anti_patterns_in | 1.0 |
| Q3 | Example preservation | examples_out / examples_in | 1.0 |
| Q4 | Start signal preservation | start_signals_out / start_signals_in | 1.0 |
| Q5 | Description trigger quality | Contains problem_class + when-to-use + when-NOT-to-use | True |
| Q6 | Pack index completeness | All packs listed with useful descriptions | True |

### Integration (manual, deferred)

| ID | Test | How |
|----|------|-----|
| I1 | OpenClaw loads the borg skill | Drop into ~/.openclaw/skills/, verify load |
| I2 | Pi agent reads SKILL.md when stuck | Send debugging task, observe skill trigger |
| I3 | Pi agent reads correct pack reference | After trigger, model reads references/packs/systematic-debugging.md |
| I4 | ClawHub publish succeeds | `clawhub publish ./borg --slug borg --name "Borg" --version 1.0.0` |
| I5 | ClawHub install + use works | Fresh machine, `clawhub install borg`, verify skill loads |

### Regression

| ID | Test | Pass Criteria |
|----|------|--------------|
| R1 | Existing borg tests | 1037 tests, 0 failures |
| R2 | Existing convert.py tests | No regression |

---

## OPEN QUESTIONS (updated)

1. **ClawHub 50MB limit**: 21 pack reference files + SKILL.md + index — will this fit? (Estimate: ~150KB total — yes)
2. **ClawHub account**: Need GitHub account with 14+ days age to publish
3. **Naming**: `borg` as skill name — is it taken on ClawHub? Check before publishing
4. **borg prefix on ClawHub**: Should we use `borg` or `agent-borg` to match PyPI?
5. **Reference file loading**: Does OpenClaw's Pi agent actually `read()` files from references/? (Confirmed: yes, via read tool — but need to test with real runtime)
6. **Update workflow**: When packs improve, re-run converter + `clawhub publish --version x.y.z`

---

## v1 PRD STATUS: SUPERSEDED

The per-pack SKILL.md conversion approach (v1) is kept as a FALLBACK only. If the hybrid bridge approach fails integration testing (I1-I3), we fall back to v1 with the following fixes:
- Rewrite ALL descriptions with trigger-optimized language
- Aggressively trim bodies to <500 lines
- Accept that phase enforcement is advisory only
- Publish individually to ClawHub

But v2 is the recommended path.
