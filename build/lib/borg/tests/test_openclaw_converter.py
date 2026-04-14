"""
Tests for borg/core/openclaw_converter.py — Borg → OpenClaw converter.

Tests:
  - convert_pack_to_openclaw_ref()
  - generate_pack_index()
  - generate_bridge_skill()
  - convert_registry_to_openclaw()
  - _extract_slug()
  - _validate_openclaw_name()
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core import openclaw_converter as oc_module


# ============================================================================
# Helpers
# ============================================================================

def minimal_pack(overrides: Dict[str, Any] = None) -> dict:
    """Minimal valid workflow_pack artifact."""
    base = {
        "type": "workflow_pack",
        "version": "1.0",
        "id": "test-pack",
        "problem_class": "debugging",
        "mental_model": "fast-thinker",
        "phases": [
            {
                "name": "reproduce",
                "description": "Reproduce the bug consistently. Capture exact error, stack trace, steps to trigger.",
                "checkpoint": "You can trigger the exact error on demand",
                "prompts": ["Reproduce {input}"],
                "anti_patterns": [
                    "Do NOT guess at fixes before reproducing",
                    "Do NOT add broad try/except blocks to hide the error",
                ],
            },
            {
                "name": "investigate",
                "description": "Trace the root cause of the bug.",
                "checkpoint": "Root cause identified",
                "prompts": ["Investigate {input}"],
                "anti_patterns": [],
            },
        ],
        "start_signals": [
            {
                "error_pattern": "TypeError",
                "start_here": ["Trace the call chain upward from the failing function"],
                "avoid": ["the method definition itself", "adding None checks at the symptom"],
                "reasoning": "Most TypeErrors are caused by wrong argument order or type mismatch",
            }
        ],
        "required_inputs": ["Reproducible error", "Access to the codebase"],
        "examples": [
            {
                "problem": "Agent spent 20 minutes trying random fixes for a TypeError",
                "solution": "Pack forced reproduce → investigate flow. Stack trace showed wrong argument order.",
                "outcome": "4 minutes vs 20 minutes. One targeted fix vs 6 reverted attempts.",
            }
        ],
        "escalation_rules": ["After 5 attempts without progress: ask the human for guidance."],
        "provenance": {
            "author": "agent://test",
            "author_agent": "agent://test",
            "created": "2026-01-01T00:00:00+00:00",
            "confidence": "tested",
            "evidence": "tested across 10+ agents",
            "failure_cases": ["wrong label"],
        },
    }
    if overrides:
        base.update(overrides)
    return base


def pack_yaml(artifact: dict) -> str:
    return yaml.dump(artifact, default_flow_style=False, sort_keys=False)


# ============================================================================
# _extract_slug tests
# ============================================================================

class TestExtractSlug:
    """Tests for _extract_slug()."""

    @pytest.mark.parametrize("pack_id,expected", [
        ("guild://hermes/systematic-debugging", "systematic-debugging"),
        ("guild://hermes/test-driven-development", "test-driven-development"),
        ("simple-name", "simple-name"),
        ("no-scheme-here", "no-scheme-here"),
    ])
    def test_extracts_slug(self, pack_id: str, expected: str):
        result = oc_module._extract_slug(pack_id)
        assert result == expected


# ============================================================================
# _validate_openclaw_name tests
# ============================================================================

class TestValidateOpenclawName:
    """Tests for _validate_openclaw_name()."""

    @pytest.mark.parametrize("name,valid", [
        ("borg", True),
        ("systematic-debugging", True),
        ("my-skill-2024", True),
        ("a", True),
        ("", False),
        ("-leading-hyphen", False),
        ("trailing-hyphen-", False),
        ("under_score", False),
        ("UPPER", False),
        ("a" * 64, True),
        ("a" * 65, False),  # > 64 chars
        ("has spaces", False),
    ])
    def test_validates_format(self, name: str, valid: bool):
        assert oc_module._validate_openclaw_name(name) == valid


# ============================================================================
# convert_pack_to_openclaw_ref tests
# ============================================================================

class TestConvertPackToOpenclawRef:
    """Tests for convert_pack_to_openclaw_ref()."""

    def test_basic_conversion(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        # Title (id "test/pack" becomes "test pack" title)
        assert "# Test Pack" in result
        assert "**Confidence:** tested | **Problem class:** debugging" in result

    def test_when_to_use_from_start_signals(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "## When to Use" in result
        assert "**TypeError:**" in result
        assert "🎯 Trace the call chain" in result
        assert "⚠️ Avoid: the method definition itself" in result

    def test_required_inputs_section(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "## Required Inputs" in result
        assert "- Reproducible error" in result
        assert "- Access to the codebase" in result

    def test_phases_with_anti_patterns_and_checkpoints(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "## Phases" in result
        assert "### Phase 1: Reproduce" in result
        assert "⚠️ Do NOT: Do NOT guess at fixes before reproducing" in result
        assert "✅ Before moving on: You can trigger the exact error on demand" in result

    def test_examples_section(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "## Examples" in result
        assert "**Problem:** Agent spent 20 minutes trying random fixes" in result
        assert "**Solution:** Pack forced reproduce" in result
        assert "**Outcome:** 4 minutes vs 20 minutes" in result

    def test_escalation_section(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "## Escalation" in result
        assert "After 5 attempts without progress" in result

    def test_provenance_footer(self):
        pack = minimal_pack()
        result = oc_module.convert_pack_to_openclaw_ref(pack)

        assert "---" in result
        assert "Confidence: tested" in result
        assert "Evidence: tested across 10+ agents" in result
        assert "Author: agent://test" in result

    def test_missing_optional_fields(self):
        """Pack with no start_signals, examples, escalation still renders."""
        minimal = {
            "id": "bare-pack",
            "problem_class": "general",
            "phases": [
                {"name": "step_1", "description": "Do the thing."}
            ],
            "provenance": {"confidence": "inferred"},
        }
        result = oc_module.convert_pack_to_openclaw_ref(minimal)
        assert "# Bare Pack" in result
        assert "## Phases" in result
        assert "### Phase 1: Step 1" in result


# ============================================================================
# generate_pack_index tests
# ============================================================================

class TestGeneratePackIndex:
    """Tests for generate_pack_index()."""

    def test_table_headers(self):
        packs = [
            minimal_pack({"id": "guild://hermes/pack-a", "problem_class": "debugging"}),
            minimal_pack({"id": "guild://hermes/pack-b", "problem_class": "testing"}),
        ]
        result = oc_module.generate_pack_index(packs)

        assert "# Borg Pack Index" in result
        assert "| Pack | Problem Class | Confidence | Use When |" in result
        assert "|------|--------------|-----------|----------|" in result

    def test_includes_pack_rows(self):
        packs = [
            minimal_pack({
                "id": "guild://hermes/systematic-debugging",
                "problem_class": "debugging",
                "provenance": {"confidence": "tested"},
                "start_signals": [
                    {"reasoning": "Agent is stuck debugging"}
                ],
            }),
        ]
        result = oc_module.generate_pack_index(packs)

        assert "| systematic-debugging | debugging | tested | Agent is stuck debugging |" in result

    def test_truncates_long_problem_class(self):
        packs = [
            minimal_pack({
                "id": "guild://hermes/long-class",
                "problem_class": "a" * 100,
            }),
        ]
        result = oc_module.generate_pack_index(packs)

        # problem_class truncated to 50 chars
        assert "| long-class | " in result

    def test_empty_packs_list(self):
        result = oc_module.generate_pack_index([])
        assert "# Borg Pack Index" in result
        assert "To use a pack:" in result

    def test_uses_problem_class_when_no_start_signals(self):
        packs = [
            minimal_pack({
                "id": "guild://hermes/no-signals",
                "problem_class": "code-review",
                "start_signals": [],
            }),
        ]
        result = oc_module.generate_pack_index(packs)
        assert "| no-signals | code-review |" in result


# ============================================================================
# generate_bridge_skill tests
# ============================================================================

class TestGenerateBridgeSkill:
    """Tests for generate_bridge_skill()."""

    def test_frontmatter_present(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert result.startswith("---")
        assert 'name: borg' in result
        assert 'description:' in result
        assert 'user-invocable: true' in result

    def test_emoji_in_metadata(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert 'emoji":"🧠"' in result

    def test_when_to_use_section(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert "## When to Use" in result
        assert "3+ failed attempts" in result

    def test_when_not_to_use_section(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert "## When NOT to Use" in result
        assert "Simple, obvious fixes" in result

    def test_how_to_use_section(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert "## How to Use" in result
        assert "Step 1: Find the right pack" in result
        assert "references/pack-index.md" in result

    def test_quick_reference_packs(self):
        packs = [
            minimal_pack({"id": "guild://hermes/pack-a", "problem_class": "debugging"}),
            minimal_pack({"id": "guild://hermes/pack-b", "problem_class": "testing"}),
        ]
        result = oc_module.generate_bridge_skill(packs)

        assert "## Available Packs" in result
        assert "**pack-a**" in result
        assert "**pack-b**" in result

    def test_description_max_length(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        # Extract description from frontmatter
        desc_match = result.split('description: "')[1].split('"')[0]
        assert len(desc_match) <= 1024

    def test_trust_the_process_warning(self):
        packs = [minimal_pack()]
        result = oc_module.generate_bridge_skill(packs)

        assert "Trust the process" in result
        assert "⚠️ **Critical:**" in result


# ============================================================================
# convert_registry_to_openclaw tests
# ============================================================================

class TestConvertRegistryToOpenclaw:
    """Tests for convert_registry_to_openclaw()."""

    def test_creates_directory_structure(self, tmp_path):
        packs = [
            minimal_pack({"id": "guild://hermes/pack-one"}),
        ]
        output_dir = tmp_path / "openclaw"

        result = oc_module.convert_registry_to_openclaw(packs, output_dir)

        assert result["success"] is True
        assert (output_dir / "SKILL.md").exists()
        assert (output_dir / "references" / "pack-index.md").exists()
        assert (output_dir / "references" / "packs" / "pack-one.md").exists()

    def test_files_created_count(self, tmp_path):
        packs = [
            minimal_pack({"id": "guild://hermes/pack-a"}),
            minimal_pack({"id": "guild://hermes/pack-b"}),
        ]
        output_dir = tmp_path / "openclaw"

        result = oc_module.convert_registry_to_openclaw(packs, output_dir)

        assert result["total_packs"] == 2
        # SKILL.md + pack-index.md + 2 pack files = 4
        assert len(result["files_created"]) == 4

    def test_overwrite_true_replaces_existing(self, tmp_path):
        packs = [minimal_pack({"id": "guild://hermes/pack-x"})]
        output_dir = tmp_path / "openclaw"

        # First call
        result1 = oc_module.convert_registry_to_openclaw(packs, output_dir)
        assert result1["success"] is True

        # Modify SKILL.md to detect overwrite
        (output_dir / "SKILL.md").write_text("modified")

        # Second call with overwrite=True
        result2 = oc_module.convert_registry_to_openclaw(packs, output_dir, overwrite=True)
        assert result2["success"] is True
        assert (output_dir / "SKILL.md").read_text() != "modified"

    def test_overwrite_false_raises_on_existing(self, tmp_path):
        packs = [minimal_pack({"id": "guild://hermes/pack-y"})]
        output_dir = tmp_path / "openclaw"

        # First call
        oc_module.convert_registry_to_openclaw(packs, output_dir)

        # Second call without overwrite should raise
        with pytest.raises(FileExistsError, match="SKILL.md already exists"):
            oc_module.convert_registry_to_openclaw(packs, output_dir, overwrite=False)

    def test_total_size_reported(self, tmp_path):
        packs = [minimal_pack({"id": "guild://hermes/size-test"})]
        output_dir = tmp_path / "openclaw"

        result = oc_module.convert_registry_to_openclaw(packs, output_dir)

        assert result["total_size_bytes"] > 0
        assert "output_dir" in result

    def test_pack_content_preserved(self, tmp_path):
        packs = [
            minimal_pack({
                "id": "guild://hermes/preservation-test",
                "problem_class": "debugging",
            }),
        ]
        output_dir = tmp_path / "openclaw"

        oc_module.convert_registry_to_openclaw(packs, output_dir)

        pack_md = (output_dir / "references" / "packs" / "preservation-test.md").read_text()
        assert "Preservation Test" in pack_md
        assert "debugging" in pack_md
        assert "Phase 1: Reproduce" in pack_md


# ============================================================================
# PROBLEM_CLASS_EMOJI constant
# ============================================================================

class TestProblemClassEmoji:
    def test_known_classes_have_emoji(self):
        for cls, emoji in oc_module.PROBLEM_CLASS_EMOJI.items():
            assert emoji is not None
            assert len(emoji) > 0

    def test_debugging_is_bug(self):
        assert oc_module.PROBLEM_CLASS_EMOJI["debugging"] == "🐛"

    def test_testing_is_flask(self):
        assert oc_module.PROBLEM_CLASS_EMOJI["testing"] == "🧪"
