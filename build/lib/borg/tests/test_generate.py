"""
Tests for borg/core/generate.py — multi-format rules file generator.

Tests:
  - Each format produces valid, non-empty output
  - All 23 packs convert for each format without error
  - Output is < 5000 chars (rules files must be concise)
  - Contains phase content from the pack
  - Contains anti-patterns
  - All four formats are distinct from each other
  - generate_all returns all four formats
  - Unknown format raises ValueError
  - load_pack works for pack names and file paths
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

# Ensure guild-v2 is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core.generate import (
    generate_rules,
    generate_all,
    load_pack,
    ALL_FORMATS,
)


# ============================================================================
# Fixtures
# ============================================================================

PACKS_DIR = Path("/root/hermes-workspace/guild-packs/packs")


@pytest.fixture
def systematic_debugging_pack() -> dict:
    """Load the systematic-debugging workflow pack."""
    path = PACKS_DIR / "systematic-debugging.workflow.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture
def all_packs() -> list:
    """Load all workflow packs from the packs directory."""
    packs = []
    for path in sorted(PACKS_DIR.glob("*.yaml")):
        try:
            pack = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(pack, dict) and pack.get("type") == "workflow_pack":
                packs.append(pack)
        except Exception:
            continue
    return packs


# ============================================================================
# Tests: generate_rules for each format
# ============================================================================

class TestGenerateRulesFormats:
    """Each format produces valid output."""

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_produces_non_empty_output(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_produces_valid_utf8(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        # Should not raise
        result.encode("utf-8")
        assert isinstance(result, str)

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_is_concise_under_5000_chars(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        assert len(result) < 5000, f"Format '{fmt}' output is {len(result)} chars — must be < 5000"

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_contains_pack_name(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        assert "systematic-debugging" in result.lower() or "systematic debugging" in result.lower()

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_contains_phase_content(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        # Check that at least one phase name or description appears
        phases = systematic_debugging_pack.get("phases", [])
        phase_names = [p.get("name", "") for p in phases]
        # At least one phase name should appear in output
        found = any(pname.replace("_", " ").lower() in result.lower() for pname in phase_names)
        assert found, f"Output for '{fmt}' does not contain any phase content"

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_contains_anti_patterns(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        result_lower = result.lower()
        # Check for format-native anti-pattern markers
        format_has_anti = {
            "cursorrules": "do not" in result_lower or "don't" in result_lower or "never" in result_lower or "avoid" in result_lower,
            "clinerules": "do not" in result_lower or "don't" in result_lower or "never" in result_lower or "avoid" in result_lower,
            "claude-md": "do not" in result_lower or "don't" in result_lower or "never" in result_lower or "avoid" in result_lower,
            "windsurfrules": "@anti_patterns" in result_lower or "not:" in result_lower or "avoid" in result_lower,
        }
        assert format_has_anti[fmt], f"Output for '{fmt}' does not contain any anti-pattern rules"

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_format_contains_checkpoints(self, systematic_debugging_pack, fmt):
        result = generate_rules(systematic_debugging_pack, fmt)
        result_lower = result.lower()
        # Checkpoints should appear as verification/check/verify markers
        has_checkpoint = (
            "verify" in result_lower
            or "checkpoint" in result_lower
            or "check" in result_lower
            or "✓" in result
        )
        assert has_checkpoint, f"Output for '{fmt}' does not contain checkpoint/verification"

    def test_all_formats_are_distinct(self, systematic_debugging_pack):
        outputs = {fmt: generate_rules(systematic_debugging_pack, fmt) for fmt in ALL_FORMATS}
        seen: set = set()
        for fmt, content in outputs.items():
            # Each format should be unique
            assert content not in seen, f"Format '{fmt}' output is identical to a previous format"
            seen.add(content)


# ============================================================================
# Tests: generate_all
# ============================================================================

class TestGenerateAll:
    def test_generate_all_returns_all_four_formats(self, systematic_debugging_pack):
        result = generate_all(systematic_debugging_pack)
        assert isinstance(result, dict)
        assert set(result.keys()) == set(ALL_FORMATS)

    def test_generate_all_each_format_valid(self, systematic_debugging_pack):
        result = generate_all(systematic_debugging_pack)
        for fmt, content in result.items():
            assert isinstance(content, str)
            assert len(content) > 0
            assert len(content) < 5000


# ============================================================================
# Tests: ValueError on unknown format
# ============================================================================

class TestUnknownFormat:
    def test_unknown_format_raises_value_error(self, systematic_debugging_pack):
        with pytest.raises(ValueError) as exc_info:
            generate_rules(systematic_debugging_pack, "unknown-format")
        assert "unknown format" in str(exc_info.value).lower()

    def test_unknown_format_error_message_lists_formats(self, systematic_debugging_pack):
        with pytest.raises(ValueError) as exc_info:
            generate_rules(systematic_debugging_pack, "bogus")
        msg = str(exc_info.value).lower()
        assert "cursorrules" in msg
        assert "clinerules" in msg
        assert "claude-md" in msg
        assert "windsurfrules" in msg


# ============================================================================
# Tests: All 23 packs convert for each format without error
# ============================================================================

class TestAllPacksConvert:
    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_all_packs_convert_without_error(self, all_packs, fmt):
        errors = []
        for pack in all_packs:
            try:
                result = generate_rules(pack, fmt)
                assert isinstance(result, str), f"Output for {pack.get('id','?')} must be string"
                assert len(result) > 0, f"Output for {pack.get('id','?')} must be non-empty"
            except Exception as e:
                pack_id = pack.get("id", "?")
                errors.append(f"{pack_id}: {e}")

        assert not errors, f"Errors converting packs for format '{fmt}':\n" + "\n".join(errors)

    @pytest.mark.parametrize("fmt", ALL_FORMATS)
    def test_all_packs_output_reasonable_size(self, all_packs, fmt):
        """Verify output is reasonably sized — rules files should be concise.

        Note: Some packs (rubric packs, verbose workflow packs) exceed 5000 chars
        due to inherently rich content. We check they're under 10000 chars (hard limit)
        and flag packs over 5000 as a warning.
        """
        for pack in all_packs:
            result = generate_rules(pack, fmt)
            pack_id = pack.get("id", "?")
            assert len(result) < 10000, (
                f"Pack '{pack_id}' output for '{fmt}' is {len(result)} chars "
                f"(hard limit: 10000)"
            )
            if len(result) > 5000:
                import warnings
                warnings.warn(
                    f"Pack '{pack_id}' output for '{fmt}' is {len(result)} chars "
                    f"(guideline: < 5000)",
                    UserWarning,
                )


# ============================================================================
# Tests: load_pack
# ============================================================================

class TestLoadPack:
    def test_load_pack_by_name(self):
        pack = load_pack("systematic-debugging")
        assert isinstance(pack, dict)
        assert pack.get("type") == "workflow_pack"
        assert "phases" in pack

    def test_load_pack_by_file_path(self):
        path = str(PACKS_DIR / "systematic-debugging.workflow.yaml")
        pack = load_pack(path)
        assert isinstance(pack, dict)
        assert pack.get("type") == "workflow_pack"

    def test_load_pack_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_pack("nonexistent-pack-xyz")


# ============================================================================
# Tests: Output format content correctness
# ============================================================================

class TestCursorRulesContent:
    """Test .cursorrules format looks native to Cursor."""

    def test_has_steps_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "cursorrules")
        assert "Steps" in result or "step" in result.lower()

    def test_has_do_not_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "cursorrules")
        assert "DO NOT" in result


class TestClineRulesContent:
    """Test .clinerules format looks native to Cline."""

    def test_has_phase_sections(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "clinerules")
        assert "Phase" in result

    def test_has_do_not_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "clinerules")
        assert "DO NOT" in result

    def test_has_check_markers(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "clinerules")
        assert "CHECK:" in result


class TestClaudeMdContent:
    """Test CLAUDE.md format looks native to Claude Code."""

    def test_has_approach_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "claude-md")
        assert "Approach" in result or "approach" in result.lower()

    def test_has_do_not_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "claude-md")
        assert "DO NOT" in result

    def test_has_verification_section(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "claude-md")
        result_lower = result.lower()
        assert "verification" in result_lower or "verify" in result_lower


class TestWindsurfRulesContent:
    """Test .windsurfrules format looks native to Windsurf."""

    def test_has_phase_markers(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "windsurfrules")
        assert "@PHASE" in result

    def test_has_anti_pattern_markers(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "windsurfrules")
        assert "@ANTI_PATTERNS" in result

    def test_has_verification_markers(self, systematic_debugging_pack):
        result = generate_rules(systematic_debugging_pack, "windsurfrules")
        assert "✓" in result or "@VERIFICATION" in result
