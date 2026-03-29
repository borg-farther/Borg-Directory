#!/usr/bin/env python
"""Tests for borg/core/agentskills_converter.py."""

import tempfile
import os
import sys
from pathlib import Path

# Ensure borg is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from borg.core.agentskills_converter import (
    pack_to_agentskills_md,
    agentskills_md_to_pack,
    pack_to_agentskills,
    agentskills_to_pack,
    _pack_id_to_name,
    _validate_name,
    _NAME_RE,
)


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

MINIMAL_PACK = {
    "type": "workflow_pack",
    "version": "1.0.0",
    "id": "borg://test/minimal",
    "problem_class": "Testing workflow",
    "mental_model": "Test first, then fix.",
    "phases": [
        {
            "name": "setup",
            "description": "Set up test environment.",
            "checkpoint": "Tests are runnable.",
            "anti_patterns": [],
            "prompts": [],
        },
        {
            "name": "fix",
            "description": "Fix the failing test.",
            "checkpoint": "All tests pass.",
            "anti_patterns": ["Don't skip tests."],
            "prompts": [],
        },
    ],
    "required_inputs": ["pytest", "codebase"],
    "escalation_rules": ["Escalate if root cause is unclear after phase 2."],
    "provenance": {
        "type": "workflow_pack",
        "author_agent": "test-agent",
        "evidence": "Validated in unit tests.",
        "confidence": "validated",
        "failure_cases": [
            "False positives when tests are flaky.",
            "Root cause outside codebase scope.",
        ],
    },
}

PACK_WITH_STRUCTURE = {
    "type": "workflow_pack",
    "version": "1.0.0",
    "id": "guild://hermes/systematic-debugging",
    "problem_class": "Systematic debugging",
    "mental_model": "Reproduce, isolate, fix, verify.",
    "structure": ["reproduce", "isolate", "fix", "verify"],
    "phases": [
        {
            "name": "reproduce",
            "description": "Create a minimal reproduction of the bug.",
            "checkpoint": "Bug reproduced in isolation.",
            "anti_patterns": ["Don't modify production code before understanding the bug."],
            "prompts": ["What is the minimal input that triggers this bug?"],
        },
        {
            "name": "isolate",
            "description": "Narrow down the root cause.",
            "checkpoint": "Root cause identified and confirmed.",
            "anti_patterns": [],
            "prompts": [],
        },
        {
            "name": "fix",
            "description": "Apply the fix.",
            "checkpoint": "Fix applied and reviewed.",
            "anti_patterns": [],
            "prompts": [],
        },
        {
            "name": "verify",
            "description": "Verify the fix works and doesn't break anything.",
            "checkpoint": "All tests pass, no regressions.",
            "anti_patterns": [],
            "prompts": [],
        },
    ],
    "start_signals": [
        {
            "error_pattern": "TypeError / AssertionError",
            "start_here": "Use systematic-debugging pack.",
            "avoid": ["Random guessing", "Deleting code you don't understand"],
            "reasoning": "Systematic debugging prevents repeated failed attempts.",
        }
    ],
    "required_inputs": ["error_trace", "codebase"],
    "escalation_rules": ["Escalate after 3 failed fix attempts."],
    "provenance": {
        "type": "workflow_pack",
        "author_agent": "hermes/session-42",
        "evidence": "Battle-tested across 100+ debug sessions.",
        "confidence": "tested",
        "failure_cases": [
            "Bugs with non-deterministic behavior.",
            "Multi-threaded race conditions.",
        ],
    },
}

SAMPLE_SKILL_MD = """---
name: pdf-processing
description: Extract text from PDFs, fill forms, merge files. Use when handling PDFs.
compatibility: Requires Python 3.9+ and pdfplumber.
metadata:
  example: value
---

# PDF Processing

## When to Use

Use this skill when you need to work with PDF files.

## How to Extract Text

1. Load the PDF with pdfplumber
2. Extract text from each page
3. Combine the results

## How to Fill Forms

1. Locate form fields
2. Fill each field
3. Save the annotated PDF

## Phases

### Phase 1: Load

Open the PDF file.

### Phase 2: Extract

Extract the desired content.

### Phase 3: Save

Save the modified PDF.

## Escalation

- If the PDF is encrypted and you don't have the password, escalate to the user.
"""

INVALID_NAME_SKILL = """---
name: Invalid-Name-With-Caps
description: Test
---

# Test
"""


# ---------------------------------------------------------------------------
# Tests — _pack_id_to_name
# ---------------------------------------------------------------------------

class TestPackIdToName:
    def test_simple_pack_id(self):
        assert _pack_id_to_name("guild://hermes/systematic-debugging") == "systematic-debugging"

    def test_borg_uri(self):
        assert _pack_id_to_name("borg://local/my-workflow") == "my-workflow"

    def test_no_uri(self):
        assert _pack_id_to_name("plain-name") == "plain-name"

    def test_uppercase_normalized(self):
        assert _pack_id_to_name("GUILD://HERMES/TEST") == "test"

    def test_spaces_become_hyphens(self):
        assert _pack_id_to_name("guild://hermes/my test workflow") == "my-test-workflow"

    def test_empty_defaults_to_unnamed(self):
        assert _pack_id_to_name("") == "unnamed-skill"
        assert _pack_id_to_name("://") == "unnamed-skill"


# ---------------------------------------------------------------------------
# Tests — _validate_name
# ---------------------------------------------------------------------------

class TestValidateName:
    def test_valid_simple(self):
        _validate_name("debugging")

    def test_valid_with_hyphens(self):
        _validate_name("systematic-debugging")

    def test_valid_with_numbers(self):
        _validate_name("test-2024")

    def test_invalid_uppercase(self):
        try:
            _validate_name("Invalid")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "lowercase" in str(e).lower()

    def test_invalid_leading_hyphen(self):
        try:
            _validate_name("-debug")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "hyphen" in str(e).lower()

    def test_invalid_trailing_hyphen(self):
        try:
            _validate_name("debug-")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "hyphen" in str(e).lower()

    def test_too_long(self):
        long_name = "a" * 100
        try:
            _validate_name(long_name)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "64" in str(e)

    def test_empty(self):
        try:
            _validate_name("")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "empty" in str(e).lower()


# ---------------------------------------------------------------------------
# Tests — pack_to_agentskills_md
# ---------------------------------------------------------------------------

class TestPackToAgentskillsMd:
    def test_minimal_pack_round_trip(self):
        skill_md = pack_to_agentskills_md(MINIMAL_PACK)
        # YAML fields are alphabetically sorted by yaml.dump with block style
        assert skill_md.startswith("---\n")
        assert "name: minimal" in skill_md
        assert "description:" in skill_md
        assert "## Phases" in skill_md
        assert "### Phase 1: Setup" in skill_md
        assert "### Phase 2: Fix" in skill_md
        # provenance stored in metadata
        assert "metadata:" in skill_md
        assert "borg_provenance" in skill_md

    def test_full_pack_with_structure(self):
        skill_md = pack_to_agentskills_md(PACK_WITH_STRUCTURE)
        assert "systematic-debugging" in skill_md
        assert "## When to Use" in skill_md
        assert "## Phases" in skill_md
        assert "### Phase 1: Reproduce" in skill_md
        assert "### Phase 2: Isolate" in skill_md
        assert "### Phase 3: Fix" in skill_md
        assert "### Phase 4: Verify" in skill_md
        assert "Don't modify production code" in skill_md
        assert "## Escalation" in skill_md
        assert "tested" in skill_md  # confidence

    def test_description_max_length(self):
        long_desc_pack = dict(MINIMAL_PACK)
        long_desc_pack["problem_class"] = "A" * 2000
        skill_md = pack_to_agentskills_md(long_desc_pack)
        # Should be truncated to 1021 chars (1024 - "..." = 1021)
        assert len(skill_md) < 10000


# ---------------------------------------------------------------------------
# Tests — agentskills_md_to_pack
# ---------------------------------------------------------------------------

class TestAgentskillsMdToPack:
    def test_round_trip_minimal(self):
        skill_md = pack_to_agentskills_md(MINIMAL_PACK)
        recovered = agentskills_md_to_pack(skill_md)

        assert recovered["type"] == "workflow_pack"
        assert recovered["version"] == "1.0.0"
        assert "phases" in recovered
        assert len(recovered["phases"]) == 2
        assert recovered["phases"][0]["name"] == "setup"
        assert recovered["phases"][1]["name"] == "fix"
        assert recovered["required_inputs"] == ["pytest", "codebase"]
        assert len(recovered["escalation_rules"]) == 1

    def test_round_trip_full_pack(self):
        skill_md = pack_to_agentskills_md(PACK_WITH_STRUCTURE)
        recovered = agentskills_md_to_pack(skill_md)

        assert recovered["id"] == "agentskills://systematic-debugging"
        assert recovered["problem_class"] == "Systematic debugging"
        assert len(recovered["phases"]) == 4
        phase_names = [p["name"] for p in recovered["phases"]]
        assert phase_names == ["reproduce", "isolate", "fix", "verify"]
        # provenance round-trips correctly via metadata
        prov = recovered["provenance"]
        assert prov["confidence"] == "tested"
        assert prov["author_agent"] == "hermes/session-42"
        assert "Battle-tested" in prov["evidence"]

    def test_parse_sample_skill(self):
        pack = agentskills_md_to_pack(SAMPLE_SKILL_MD)

        assert pack["id"] == "agentskills://pdf-processing"
        assert "phases" in pack
        phase_names = [p["name"] for p in pack["phases"]]
        assert "load" in phase_names
        assert "extract" in phase_names
        assert "save" in phase_names
        assert pack["required_inputs"] == []

    def test_invalid_name_raises(self):
        try:
            agentskills_md_to_pack(INVALID_NAME_SKILL)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "lowercase" in str(e).lower()

    def test_missing_name_raises(self):
        try:
            agentskills_md_to_pack("---\ndescription: test\n---\n# Body\n")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "name" in str(e).lower()

    def test_description_too_long_raises(self):
        long_desc = "A" * 2000
        text = f"---\nname: test-pack\ndescription: {long_desc}\n---\n# Body\n"
        try:
            agentskills_md_to_pack(text)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "1024" in str(e)

    def test_provenance_round_trips(self):
        # The borg provenance survives round-trip via metadata
        skill_md = pack_to_agentskills_md(PACK_WITH_STRUCTURE)
        recovered = agentskills_md_to_pack(skill_md)
        prov = recovered["provenance"]
        # Original provenance values are restored via metadata
        assert prov["author_agent"] == "hermes/session-42"
        assert prov["evidence"] == "Battle-tested across 100+ debug sessions."
        assert prov["confidence"] == "tested"
        assert prov["failure_cases"] == [
            "Bugs with non-deterministic behavior.",
            "Multi-threaded race conditions.",
        ]

    def test_escalation_from_frontmatter(self):
        text = "---\nname: test-pack\ndescription: Test\nescalation_rules:\n  - Rule one\n  - Rule two\n---\n# Test\n"
        pack = agentskills_md_to_pack(text)
        assert pack["escalation_rules"] == ["Rule one", "Rule two"]

    def test_required_inputs_from_frontmatter(self):
        text = "---\nname: test-pack\ndescription: Test\nrequired_inputs:\n  - tool_a\n  - tool_b\n---\n# Test\n"
        pack = agentskills_md_to_pack(text)
        assert pack["required_inputs"] == ["tool_a", "tool_b"]


# ---------------------------------------------------------------------------
# Tests — Directory-level conversion
# ---------------------------------------------------------------------------

class TestDirectoryConversion:
    def test_pack_to_agentskills_creates_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            result = pack_to_agentskills(MINIMAL_PACK, output_dir)

            assert result["success"] is True
            assert (output_dir / "SKILL.md").exists()
            assert (output_dir / "references" / "provenance.md").exists()
            assert (output_dir / "references" / "phases" / "setup.md").exists()
            assert (output_dir / "references" / "phases" / "fix.md").exists()
            assert result["total_phases"] == 2

    def test_pack_to_agentskills_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            pack_to_agentskills(MINIMAL_PACK, output_dir)
            result = pack_to_agentskills(MINIMAL_PACK, output_dir, overwrite=True)
            assert result["success"] is True

    def test_pack_to_agentskills_no_overwrite_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            pack_to_agentskills(MINIMAL_PACK, output_dir)
            try:
                pack_to_agentskills(MINIMAL_PACK, output_dir, overwrite=False)
                assert False, "Should raise FileExistsError"
            except FileExistsError:
                pass

    def test_agentskills_to_pack_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "round-trip-skill"
            pack_to_agentskills(PACK_WITH_STRUCTURE, output_dir)

            recovered = agentskills_to_pack(output_dir)
            assert recovered["type"] == "workflow_pack"
            assert len(recovered["phases"]) == 4
            assert recovered["provenance"]["confidence"] == "tested"

    def test_agentskills_to_pack_missing_skill_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_dir = Path(tmpdir) / "empty"
            empty_dir.mkdir()
            try:
                agentskills_to_pack(empty_dir)
                assert False, "Should raise FileNotFoundError"
            except FileNotFoundError as e:
                assert "SKILL.md" in str(e)

    def test_skill_md_content_integrity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "skill"
            pack_to_agentskills(PACK_WITH_STRUCTURE, output_dir)

            skill_md = (output_dir / "SKILL.md").read_text(encoding="utf-8")
            # Parse back to pack and verify critical fields
            recovered = agentskills_md_to_pack(skill_md)
            assert recovered["id"] == "agentskills://systematic-debugging"
            assert len(recovered["phases"]) == 4


# ---------------------------------------------------------------------------
# Tests — name regex validation
# ---------------------------------------------------------------------------

class TestNameRegex:
    def test_valid_names_match(self):
        assert _NAME_RE.match("debugging")
        assert _NAME_RE.match("systematic-debugging")
        assert _NAME_RE.match("a")
        assert _NAME_RE.match("test-2024-valid")
        assert _NAME_RE.match("a-b-c")

    def test_invalid_names_do_not_match(self):
        assert not _NAME_RE.match("Debugging")
        assert not _NAME_RE.match("-debug")
        assert not _NAME_RE.match("debug-")
        assert not _NAME_RE.match("systematic_debugging")
        assert not _NAME_RE.match("systematic.debugging")
        assert not _NAME_RE.match("")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import traceback

    test_classes = [
        TestPackIdToName,
        TestValidateName,
        TestPackToAgentskillsMd,
        TestAgentskillsMdToPack,
        TestDirectoryConversion,
        TestNameRegex,
    ]

    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        print(f"\n{cls.__name__}")
        print("-" * len(cls.__name__))
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                    errors.append((cls.__name__, method_name, str(e)))
                except Exception as e:
                    print(f"  ✗ {method_name}: {type(e).__name__}: {e}")
                    failed += 1
                    errors.append((cls.__name__, method_name, f"{type(e).__name__}: {e}"))

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed > 0:
        print("\nFailures:")
        for cls_name, method_name, err in errors:
            print(f"  {cls_name}.{method_name}: {err}")
        sys.exit(1)
    else:
        print("All tests passed!")
