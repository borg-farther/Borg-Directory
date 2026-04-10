"""Tests for borg.core.generator — pack → platform rules export."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from borg.core.generator import (
    FORMATS,
    FORMAT_FILENAMES,
    generate_rules,
    generate_to_files,
    load_pack,
    _slug,
    _title,
    _get_phases,
    _get_anti_patterns,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pack():
    return {
        "type": "workflow_pack",
        "version": "1.0",
        "id": "systematic-debugging",
        "problem_class": "debugging",
        "mental_model": "Reproduce first, then bisect to isolate the root cause.",
        "phases": [
            {
                "name": "reproduce",
                "description": "Create a minimal reproduction of the bug.",
                "checkpoint": "Bug reliably triggers",
                "anti_patterns": [
                    {"action": "Skip reproduction", "why_fails": "Wastes time guessing"},
                ],
                "prompts": ["Run the failing test to see exact error"],
            },
            {
                "name": "investigate",
                "description": "Bisect and trace to find root cause.",
                "checkpoint": "Root cause identified",
                "anti_patterns": [],
                "prompts": [],
            },
            {
                "name": "fix",
                "description": "Apply the minimal fix and verify.",
                "checkpoint": "All tests pass",
                "anti_patterns": [
                    {"action": "Shotgun debugging", "why_fails": "Creates new bugs"},
                ],
                "prompts": ["Run full test suite after fix"],
            },
        ],
        "anti_patterns": [
            {"action": "Changing random things", "why_fails": "Masks the real issue"},
        ],
        "required_inputs": ["error message", "stack trace"],
        "escalation_rules": [
            {"condition": "3 failed attempts", "action": "Escalate to human"},
        ],
        "provenance": {
            "author": "agent://test",
            "confidence": "tested",
        },
        "evidence": {
            "success_rate": 0.92,
            "uses": 45,
        },
    }


@pytest.fixture
def v2_pack():
    """Pack using v2 schema with structure.phases."""
    return {
        "type": "workflow_pack",
        "version": "2.0",
        "id": "v2-pack",
        "problem_class": "testing",
        "mental_model": "Test first.",
        "structure": {
            "phases": [
                {"name": "write-test", "description": "Write failing test first."},
                {"name": "implement", "description": "Write minimal code to pass."},
            ],
        },
        "provenance": {"confidence": "inferred"},
    }


@pytest.fixture
def guild_pack_dir(sample_pack, tmp_path):
    """Create a temp guild directory with a pack."""
    pack_dir = tmp_path / "test-pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        yaml.safe_dump(sample_pack, default_flow_style=False, sort_keys=False)
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_slug_simple(self):
        assert _slug("my-pack") == "my-pack"

    def test_slug_with_prefix(self):
        assert _slug("borg://converted/my-pack") == "my-pack"

    def test_title(self):
        assert _title("systematic-debugging") == "Systematic Debugging"
        assert _title("my_pack") == "My Pack"

    def test_get_phases_v1(self, sample_pack):
        phases = _get_phases(sample_pack)
        assert len(phases) == 3
        assert phases[0]["name"] == "reproduce"

    def test_get_phases_v2(self, v2_pack):
        phases = _get_phases(v2_pack)
        assert len(phases) == 2
        assert phases[0]["name"] == "write-test"

    def test_get_anti_patterns(self, sample_pack):
        aps = _get_anti_patterns(sample_pack)
        assert len(aps) >= 1
        assert any("random" in ap.get("action", "").lower() for ap in aps)


# ---------------------------------------------------------------------------
# Unit tests — format generators
# ---------------------------------------------------------------------------

class TestCursorrules:
    def test_basic_output(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert isinstance(result, str)
        assert "Systematic Debugging" in result
        assert "debugging" in result.lower()

    def test_has_phases(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert "Reproduce" in result
        assert "Investigate" in result
        assert "Fix" in result

    def test_has_anti_patterns(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert "❌" in result
        assert "Skip reproduction" in result

    def test_has_mental_model(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert "Reproduce first" in result

    def test_has_required_inputs(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert "error message" in result

    def test_has_escalation(self, sample_pack):
        result = generate_rules(sample_pack, "cursorrules")
        assert "3 failed attempts" in result


class TestClinerules:
    def test_basic_output(self, sample_pack):
        result = generate_rules(sample_pack, "clinerules")
        assert isinstance(result, str)
        assert "Systematic Debugging" in result

    def test_has_phases(self, sample_pack):
        result = generate_rules(sample_pack, "clinerules")
        assert "Reproduce" in result

    def test_has_evidence(self, sample_pack):
        result = generate_rules(sample_pack, "clinerules")
        assert "0.92" in result or "92" in result


class TestClaudeMd:
    def test_basic_output(self, sample_pack):
        result = generate_rules(sample_pack, "claude-md")
        assert isinstance(result, str)
        assert "Systematic Debugging" in result

    def test_has_commands_section(self, sample_pack):
        result = generate_rules(sample_pack, "claude-md")
        assert "## Commands" in result
        assert "borg apply" in result
        assert "borg debug" in result

    def test_has_phases(self, sample_pack):
        result = generate_rules(sample_pack, "claude-md")
        assert "Workflow Phases" in result

    def test_has_escalation(self, sample_pack):
        result = generate_rules(sample_pack, "claude-md")
        assert "Escalation" in result


class TestWindsurfrules:
    def test_basic_output(self, sample_pack):
        result = generate_rules(sample_pack, "windsurfrules")
        assert isinstance(result, str)
        assert "Systematic Debugging" in result

    def test_concise(self, sample_pack):
        result = generate_rules(sample_pack, "windsurfrules")
        # Windsurf should be more concise than others
        cursorrules = generate_rules(sample_pack, "cursorrules")
        assert len(result) <= len(cursorrules)

    def test_has_steps(self, sample_pack):
        result = generate_rules(sample_pack, "windsurfrules")
        assert "1." in result
        assert "2." in result


# ---------------------------------------------------------------------------
# Integration tests — all formats
# ---------------------------------------------------------------------------

class TestAllFormats:
    def test_generate_all(self, sample_pack):
        result = generate_rules(sample_pack, "all")
        assert isinstance(result, dict)
        assert set(result.keys()) == set(FORMATS)
        for fmt, content in result.items():
            assert isinstance(content, str)
            assert len(content) > 50

    def test_v2_pack_all_formats(self, v2_pack):
        result = generate_rules(v2_pack, "all")
        assert isinstance(result, dict)
        for content in result.values():
            assert "Write Test" in content or "write-test" in content.lower()

    def test_unknown_format_raises(self, sample_pack):
        with pytest.raises(ValueError, match="Unknown format"):
            generate_rules(sample_pack, "invalid-format")


class TestGenerateToFiles:
    def test_write_all(self, sample_pack):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate_to_files(sample_pack, format="all", output_dir=tmpdir)
            assert len(written) == 4
            for filename, filepath in written.items():
                assert Path(filepath).exists()
                content = Path(filepath).read_text()
                assert len(content) > 50

    def test_write_single(self, sample_pack):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate_to_files(sample_pack, format="cursorrules", output_dir=tmpdir)
            assert len(written) == 1
            assert ".cursorrules" in written
            assert Path(written[".cursorrules"]).exists()

    def test_filenames_correct(self, sample_pack):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generate_to_files(sample_pack, format="all", output_dir=tmpdir)
            assert ".cursorrules" in written
            assert ".clinerules" in written
            assert "CLAUDE.md" in written
            assert ".windsurfrules" in written


class TestLoadPack:
    def test_load_from_guild(self, sample_pack, guild_pack_dir, monkeypatch):
        monkeypatch.setenv("HOME", str(guild_pack_dir.parent))
        # Create the expected directory structure
        guild_dir = guild_pack_dir.parent / ".hermes" / "guild" / "test-pack"
        guild_dir.mkdir(parents=True, exist_ok=True)
        (guild_dir / "pack.yaml").write_text(
            yaml.safe_dump(sample_pack, default_flow_style=False, sort_keys=False)
        )
        # Monkey-patch Path.home()
        monkeypatch.setattr(Path, "home", lambda: guild_pack_dir.parent)
        pack = load_pack("test-pack")
        assert pack["id"] == "systematic-debugging"

    def test_load_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        with pytest.raises(FileNotFoundError, match="Pack not found"):
            load_pack("nonexistent-pack")


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_phases(self):
        pack = {
            "id": "empty",
            "problem_class": "general",
            "phases": [],
            "provenance": {},
        }
        for fmt in FORMATS:
            result = generate_rules(pack, fmt)
            assert isinstance(result, str)

    def test_minimal_pack(self):
        pack = {"id": "minimal", "problem_class": "general"}
        for fmt in FORMATS:
            result = generate_rules(pack, fmt)
            assert isinstance(result, str)
            assert "Minimal" in result

    def test_string_anti_patterns(self):
        pack = {
            "id": "str-aps",
            "problem_class": "general",
            "anti_patterns": ["Don't do this", "Also avoid that"],
            "phases": [],
        }
        result = generate_rules(pack, "cursorrules")
        assert "Don't do this" in result

    def test_pack_with_start_signals(self):
        """Packs with start_signals should not crash."""
        pack = {
            "id": "with-signals",
            "problem_class": "debugging",
            "start_signals": [
                {"error_pattern": "ImportError"},
            ],
            "phases": [{"name": "fix", "description": "Fix it"}],
        }
        for fmt in FORMATS:
            result = generate_rules(pack, fmt)
            assert isinstance(result, str)
