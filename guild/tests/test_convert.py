"""
Tests for guild.core.convert — SKILL.md, CLAUDE.md, and .cursorrules converters.
"""

import json
import os
import tempfile

import pytest

from guild.core.convert import (
    convert_auto,
    convert_claude_md,
    convert_cursorrules,
    convert_skill,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def minimal_pack(**overrides):
    """Return a minimal valid pack with optional field overrides."""
    base = {
        "type": "workflow_pack",
        "version": "1.0.0",
        "id": "guild://test/minimal",
        "problem_class": "Test problem",
        "mental_model": "Think step by step.",
        "phases": [
            {
                "name": "plan",
                "description": "Plan the approach.",
                "checkpoint": "Plan approved.",
                "prompts": ["Make a plan."],
                "anti_patterns": ["Rushing ahead."],
            },
        ],
        "provenance": {
            "author_agent": "agent://test",
            "evidence": "Tested in CI.",
            "confidence": "tested",
            "failure_cases": ["Skipped planning phase."],
        },
        "required_inputs": ["task description"],
        "escalation_rules": ["Escalate on error."],
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# convert_skill
# --------------------------------------------------------------------------

class TestConvertSkill:
    def test_basic_skill(self, tmp_path):
        skill_path = tmp_path / "debug_skill.md"
        write_file(skill_path, """---
name: Debug Skill
description: A systematic debugging workflow
tags: [debugging, troubleshooting]
confidence: tested
failure_cases:
  - Skipping root cause analysis
  - Making random changes
---
## Understand
Gather context about the bug. Read error messages and logs.

## Reproduce
Create a minimal test case that reproduces the issue.

## Diagnose
Use debugging tools to find the root cause.

## Fix
Apply the fix and verify it works.
""")
        pack = convert_skill(str(skill_path))

        assert pack["type"] == "workflow_pack"
        assert pack["version"] == "1.0.0"
        assert "debug_skill" in pack["id"]
        assert pack["problem_class"] == "A systematic debugging workflow"
        assert pack["mental_model"] == "A systematic debugging workflow"
        assert len(pack["phases"]) == 4
        assert pack["provenance"]["confidence"] == "tested"
        assert "Skipping root cause analysis" in pack["provenance"]["failure_cases"]

    def test_skill_without_frontmatter(self, tmp_path):
        skill_path = tmp_path / "skill_no_fm.md"
        write_file(skill_path, """## Phase One
Content for phase one.

## Phase Two
Content for phase two.
""")
        pack = convert_skill(str(skill_path))

        assert len(pack["phases"]) == 2
        assert pack["phases"][0]["name"] == "phase_one"
        assert pack["phases"][1]["name"] == "phase_two"

    def test_skill_meta_sections_skipped(self, tmp_path):
        skill_path = tmp_path / "skill_meta.md"
        write_file(skill_path, """---
name: Meta Skill
---
## overview
Overview text should be skipped.

## planning
This phase should appear.

## references
References should be skipped.
""")
        pack = convert_skill(str(skill_path))
        names = [p["name"] for p in pack["phases"]]
        assert "overview" not in names
        assert "references" not in names
        assert "planning" in names


# --------------------------------------------------------------------------
# convert_claude_md
# --------------------------------------------------------------------------

class TestConvertClaudeMd:
    def test_basic_claude_md(self, tmp_path):
        claude_path = tmp_path / "CLAUDE.md"
        write_file(claude_path, """# Claude Instructions

## Description
Think step by step and verify each claim.

## Process

### Plan
Before writing code, outline the approach.

### Execute
Write the code following the plan.

### Verify
Run tests and check for regressions.

## Anti-Patterns
Don't skip tests.
Don't leave debug code.
Never commit secrets.
""")
        pack = convert_claude_md(str(claude_path))

        assert pack["type"] == "workflow_pack"
        assert "claude" in pack["id"]
        assert len(pack["phases"]) >= 2
        # Anti-patterns extracted
        anti_texts = []
        for phase in pack["phases"]:
            anti_texts.extend(phase.get("anti_patterns", []))
        assert any("Don't skip tests" in ap for ap in anti_texts)
        assert any("Never commit secrets" in ap for ap in anti_texts)

    def test_mental_model_from_description(self, tmp_path):
        claude_path = tmp_path / "CLAUDE.md"
        write_file(claude_path, """## Description
A methodical approach to code review.

## Review
Look for bugs and style issues.
""")
        pack = convert_claude_md(str(claude_path))
        assert "methodical approach" in pack["mental_model"]

    def test_required_inputs_extracted(self, tmp_path):
        claude_path = tmp_path / "CLAUDE.md"
        write_file(claude_path, """## Overview

Use the file tool to read files and the search function to find patterns.
Then use the write tool to make changes.

## Process
Call the analyzer function with context.
""")
        pack = convert_claude_md(str(claude_path))
        # Tool/context references should be extracted
        inputs = pack.get("required_inputs", [])
        assert isinstance(inputs, list)


# --------------------------------------------------------------------------
# convert_cursorrules
# --------------------------------------------------------------------------

class TestConvertCursorrules:
    def test_markdown_cursorrules(self, tmp_path):
        rules_path = tmp_path / ".cursorrules"
        write_file(rules_path, """## Design

Follow the existing code style. Keep functions small.

## Implementation

Write tests first. Use type hints.

## Anti-Patterns
Don't use global state.
Avoid magic numbers.
""")
        pack = convert_cursorrules(str(rules_path))

        assert pack["type"] == "workflow_pack"
        assert len(pack["phases"]) >= 2

    def test_json_cursorrules(self, tmp_path):
        rules_path = tmp_path / ".cursorrules"
        data = {
            "name": "JSON Cursor Rules",
            "description": "Rules for code generation",
            "phases": [
                {
                    "name": "analyze",
                    "description": "Understand the requirements",
                    "anti_patterns": ["Rushing"],
                },
                {
                    "name": "generate",
                    "description": "Write the code",
                },
            ],
            "required_inputs": ["specification", "context"],
        }
        write_file(rules_path, json.dumps(data, indent=2))

        pack = convert_cursorrules(str(rules_path))

        assert pack["type"] == "workflow_pack"
        assert "json_cursor_rules" in pack["id"]
        assert len(pack["phases"]) == 2
        assert pack["phases"][0]["anti_patterns"] == ["Rushing"]
        assert pack["required_inputs"] == ["specification", "context"]

    def test_json_cursorrules_string_phases(self, tmp_path):
        rules_path = tmp_path / ".cursorrules"
        data = {
            "name": "Simple Rules",
            "phases": ["planning", "execution", "verification"],
        }
        write_file(rules_path, json.dumps(data))

        pack = convert_cursorrules(str(rules_path))
        assert len(pack["phases"]) == 3
        assert pack["phases"][0]["name"] == "planning"


# --------------------------------------------------------------------------
# convert_auto
# --------------------------------------------------------------------------

class TestConvertAuto:
    def test_auto_skill_md(self, tmp_path):
        path = tmp_path / "SKILL.md"
        write_file(path, """---
name: Auto Skill
---
## Step One
Do this.

## Step Two
Do that.
""")
        pack = convert_auto(str(path))
        assert "auto_skill" in pack["id"]

    def test_auto_claude_md(self, tmp_path):
        path = tmp_path / "CLAUDE.md"
        write_file(path, """## Overview
A workflow.
""")
        pack = convert_auto(str(path))
        assert "claude" in pack["id"]

    def test_auto_cursorrules(self, tmp_path):
        path = tmp_path / ".cursorrules"
        write_file(path, """## Phase
Content.
""")
        pack = convert_auto(str(path))
        assert "cursorrules" in pack["id"].lower() or ".cursorrules" in str(pack["id"])

    def test_auto_unknown_raises(self, tmp_path):
        path = tmp_path / "README.md"
        write_file(path, "Some content.")
        with pytest.raises(ValueError, match="Cannot auto-detect"):
            convert_auto(str(path))


# --------------------------------------------------------------------------
# Integration: pack round-trip
# --------------------------------------------------------------------------

class TestConvertPackIntegrity:
    def test_pack_dict_is_yaml_dumpable(self, tmp_path):
        skill_path = tmp_path / "test_skill.md"
        write_file(skill_path, """---
name: Dump Test
description: Test that output is yaml-dumpable
---
## Phase One
Content.
""")
        pack = convert_skill(str(skill_path))
        # Should not raise
        yaml_text = yaml.dump(pack, default_flow_style=False)
        assert "workflow_pack" in yaml_text
        assert "phase_one" in yaml_text

    def test_pack_has_all_required_fields(self, tmp_path):
        skill_path = tmp_path / "full_skill.md"
        write_file(skill_path, """---
name: Full Skill
confidence: tested
failure_cases:
  - Case 1
---
## Phase One
Content.
""")
        pack = convert_skill(str(skill_path))

        # Check all required fields per schema
        assert pack["type"] == "workflow_pack"
        assert pack["version"] == "1.0.0"
        assert "id" in pack
        assert "problem_class" in pack
        assert "mental_model" in pack
        assert "phases" in pack
        assert isinstance(pack["phases"], list)
        assert "provenance" in pack
        assert "required_inputs" in pack
        assert "escalation_rules" in pack
        assert pack["provenance"]["confidence"] == "tested"


import yaml  # noqa: E402  (used in tests above)
