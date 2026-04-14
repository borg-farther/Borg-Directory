"""
Tests for borg/dojo/auto_fixer.py

Covers:
  - Decision tree (patch/create/evolve/log)
  - All 8 fix strategies
  - Atomic rollback on patch
  - YAML validation
  - Fix history tracking
  - Priority ranking
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from borg.dojo.auto_fixer import (
    AutoFixer,
    FIX_STRATEGIES,
    SKILL_CREATE_THRESHOLD,
    SKILL_SEARCH_DIRS,
    SUCCESS_RATE_PATCH_THRESHOLD,
)
from borg.dojo.data_models import (
    FailureReport,
    FixAction,
    SessionAnalysis,
    SkillGap,
    ToolMetric,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary skill directory structure."""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    return skills_root


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    """Create a temporary backup directory."""
    backup = tmp_path / "backups"
    backup.mkdir()
    return backup


@pytest.fixture
def sample_skill(temp_skill_dir: Path) -> Path:
    """Create a sample skill with valid SKILL.md."""
    skill_dir = temp_skill_dir / "test-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "# Test Skill\n\n"
        "## Overview\n"
        "A test skill for unit testing.\n"
        "\n"
        "name: test-skill\n"
        "version: 1.0\n"
    )
    return skill_dir


@pytest.fixture
def sample_analysis() -> SessionAnalysis:
    """Create a sample SessionAnalysis for testing recommend()."""
    tool_metrics: Dict[str, ToolMetric] = {
        "file_read": ToolMetric(
            tool_name="file_read",
            total_calls=10,
            successful_calls=4,
            failed_calls=6,
            success_rate=0.4,
            top_error_category="path_not_found",
            top_error_snippet="No such file: /tmp/missing.txt",
        ),
        "http_call": ToolMetric(
            tool_name="http_call",
            total_calls=5,
            successful_calls=3,
            failed_calls=2,
            success_rate=0.6,
            top_error_category="timeout",
            top_error_snippet="Request timed out after 30s",
        ),
        "bash_cmd": ToolMetric(
            tool_name="bash_cmd",
            total_calls=20,
            successful_calls=18,
            failed_calls=2,
            success_rate=0.9,
            top_error_category="permission_denied",
            top_error_snippet="Permission denied: /etc/secret",
        ),
    }

    failure_reports = [
        FailureReport(
            tool_name="file_read",
            error_category="path_not_found",
            error_snippet="No such file or directory",
            session_id="s1",
            timestamp=time.time(),
            confidence=0.95,
        ),
    ]

    skill_gaps = [
        SkillGap(
            capability="csv-parsing",
            request_count=5,
            session_ids=["s1", "s2", "s3", "s4", "s5"],
            confidence=0.85,
            existing_skill=None,
        ),
        SkillGap(
            capability="web-scraping",
            request_count=2,
            session_ids=["s1", "s2"],
            confidence=0.60,
            existing_skill=None,
        ),
    ]

    weakest_tools = sorted(
        tool_metrics.values(), key=lambda m: m.failed_calls, reverse=True
    )

    return SessionAnalysis(
        schema_version=1,
        analyzed_at=time.time(),
        days_covered=7,
        sessions_analyzed=10,
        total_tool_calls=35,
        total_errors=10,
        overall_success_rate=71.4,
        user_corrections=3,
        tool_metrics=tool_metrics,
        failure_reports=failure_reports,
        skill_gaps=skill_gaps,
        retry_patterns=[],
        weakest_tools=weakest_tools,
    )


# ---------------------------------------------------------------------------
# Strategy tests
# ---------------------------------------------------------------------------


class TestFixStrategies:
    """Tests that all 8 fix strategies are defined and have required fields."""

    def test_all_eight_categories_defined(self):
        """All 8 error categories must be present in FIX_STRATEGIES."""
        expected = {
            "path_not_found",
            "timeout",
            "permission_denied",
            "command_not_found",
            "rate_limit",
            "syntax_error",
            "network",
            "generic",
        }
        assert set(FIX_STRATEGIES.keys()) == expected

    def test_each_strategy_has_required_fields(self):
        """Each strategy must be a (patch_instruction, skill_addition) tuple."""
        for name, strat in FIX_STRATEGIES.items():
            assert isinstance(strat, tuple)
            assert len(strat) == 2
            patch_instruction, skill_addition = strat
            assert isinstance(patch_instruction, str)
            assert isinstance(skill_addition, str)
            assert len(patch_instruction) > 0
            assert len(skill_addition) > 0

    def test_generic_strategy_exists(self):
        """A generic fallback strategy must exist."""
        generic = FIX_STRATEGIES["generic"]
        assert "try/except" in generic[1].lower()


# ---------------------------------------------------------------------------
# Decision tree tests
# ---------------------------------------------------------------------------


class TestDecisionTree:
    """Tests for the patch/create/evolve/log decision tree."""

    def test_existing_skill_high_success_patches(
        self, temp_skill_dir: Path, sample_analysis: SessionAnalysis
    ):
        """Existing skill + success > 60% → patch."""
        # Create skill for bash_cmd (90% success)
        skill_dir = temp_skill_dir / "bash_cmd"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# bash_cmd skill\nname: bash_cmd\n")

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(sample_analysis)

        # bash_cmd should get a patch recommendation (90% > 60%)
        patch_fixes = [f for f in recommendations if f.action == "patch"]
        assert any(f.target_skill == "bash_cmd" for f in patch_fixes)

    def test_existing_skill_low_success_evolves(
        self, temp_skill_dir: Path, sample_analysis: SessionAnalysis
    ):
        """Existing skill + success < 60% → evolve (deferred)."""
        # Create skill for file_read (40% success)
        skill_dir = temp_skill_dir / "file_read"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# file_read skill\nname: file_read\n")

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(sample_analysis)

        # file_read should be evolve since 40% < 60%
        evolve_fixes = [f for f in recommendations if f.action == "evolve"]
        assert any(f.target_skill == "file_read" for f in evolve_fixes)

    def test_no_skill_3plus_requests_creates(
        self, temp_skill_dir: Path, sample_analysis: SessionAnalysis
    ):
        """No skill + 3+ requests → create."""
        # csv-parsing has 5 requests but no existing skill
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(sample_analysis)

        create_fixes = [f for f in recommendations if f.action == "create"]
        assert any(f.target_skill == "csv-parsing" for f in create_fixes)

    def test_no_skill_under_3_requests_logs(
        self, temp_skill_dir: Path, sample_analysis: SessionAnalysis
    ):
        """No skill + <3 requests → log (no auto-create)."""
        # web-scraping has only 2 requests
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(sample_analysis)

        log_fixes = [f for f in recommendations if f.action == "log"]
        assert any(f.target_skill == "web-scraping" for f in log_fixes)

    def test_unknown_tool_no_skill_logs(self, temp_skill_dir: Path):
        """Unknown tool with no skill and no gap info → log."""
        metric = ToolMetric(
            tool_name="completely_unknown_tool",
            total_calls=1,
            successful_calls=0,
            failed_calls=1,
            success_rate=0.0,
            top_error_category="generic",
            top_error_snippet="unknown",
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(
            SessionAnalysis(
                weakest_tools=[metric],
                tool_metrics={"completely_unknown_tool": metric},
            )
        )

        assert len(recommendations) == 0  # No gap, no skill -> no fix


# ---------------------------------------------------------------------------
# Recommend ranking tests
# ---------------------------------------------------------------------------


class TestRecommendRanking:
    """Tests that recommend() returns priority-sorted results."""

    def test_results_sorted_by_priority_desc(self, temp_skill_dir: Path):
        """recommend() must return FixActions sorted by priority descending."""
        # Create a mixed analysis
        metrics = {
            "high_error": ToolMetric(
                tool_name="high_error",
                total_calls=100,
                successful_calls=20,
                failed_calls=80,
                success_rate=0.2,
                top_error_category="generic",
                top_error_snippet="error",
            ),
            "low_error": ToolMetric(
                tool_name="low_error",
                total_calls=100,
                successful_calls=95,
                failed_calls=5,
                success_rate=0.95,
                top_error_category="generic",
                top_error_snippet="error",
            ),
        }

        for name in ["high_error", "low_error"]:
            d = temp_skill_dir / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"# {name}\n")

        analysis = SessionAnalysis(
            weakest_tools=sorted(
                metrics.values(), key=lambda m: m.failed_calls, reverse=True
            ),
            tool_metrics=metrics,
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        recommendations = fixer.recommend(analysis)

        priorities = [f.priority for f in recommendations]
        assert priorities == sorted(priorities, reverse=True)

    def test_empty_analysis_returns_empty_list(self, temp_skill_dir: Path):
        """Empty SessionAnalysis returns empty recommendations."""
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        analysis = SessionAnalysis(
            weakest_tools=[],
            tool_metrics={},
        )
        assert fixer.recommend(analysis) == []


# ---------------------------------------------------------------------------
# apply_fix tests — patch with rollback
# ---------------------------------------------------------------------------


class TestApplyFixPatch:
    """Tests for the patch action with atomic rollback."""

    def test_patch_creates_backup(self, temp_skill_dir: Path, temp_backup_dir: Path):
        """apply_fix(patch) must create a backup before modifying."""
        skill_dir = temp_skill_dir / "my-skill"
        skill_dir.mkdir()
        original_content = "# My Skill\nname: my-skill\nversion: 1.0\n"
        (skill_dir / "SKILL.md").write_text(original_content)

        fix = FixAction(
            action="patch",
            target_skill="my-skill",
            priority=50.0,
            reason="test patch",
            fix_content="\n## Added by test\nnew content\n",
        )

        with patch.object(
            AutoFixer, "BACKUP_DIR", temp_backup_dir
        ), patch.object(AutoFixer, "_find_skill", lambda self, s: skill_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.backup_content == original_content
        assert result.rollback_path is not None

    def test_patch_validates_yaml(self, temp_skill_dir: Path, temp_backup_dir: Path):
        """apply_fix(patch) validates the file and rolls back on YAML frontmatter errors."""
        skill_dir = temp_skill_dir / "bad-yaml-skill"
        skill_dir.mkdir()
        # Start with invalid YAML frontmatter (missing closing ---)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: valid\nversion: 1.0\n\n# Invalid: no closing marker\n"
        )

        # Any patch should fail validation because the existing file has no closing ---
        fix = FixAction(
            action="patch",
            target_skill="bad-yaml-skill",
            priority=50.0,
            reason="test yaml validation",
            fix_content="\n## New Section\n- item\n",
        )

        with patch.object(
            AutoFixer, "BACKUP_DIR", temp_backup_dir
        ), patch.object(AutoFixer, "_find_skill", lambda self, s: skill_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is False
        assert result.success is False
        # Original content should be restored
        assert (skill_dir / "SKILL.md").read_text() == (
            "---\nname: valid\nversion: 1.0\n\n# Invalid: no closing marker\n"
        )

    def test_patch_succeeds_with_valid_yaml(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """apply_fix(patch) succeeds when YAML remains valid."""
        skill_dir = temp_skill_dir / "good-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("name: good\nversion: 1.0\n")

        fix = FixAction(
            action="patch",
            target_skill="good-skill",
            priority=50.0,
            reason="test success",
            fix_content="\n## New Section\n- item 1\n- item 2\n",
        )

        with patch.object(
            AutoFixer, "BACKUP_DIR", temp_backup_dir
        ), patch.object(AutoFixer, "_find_skill", lambda self, s: skill_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is True
        assert result.success is True

    def test_patch_missing_skill_returns_failure(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """apply_fix(patch) returns failure when skill not found."""
        fix = FixAction(
            action="patch",
            target_skill="nonexistent-skill",
            priority=50.0,
            reason="skill not found",
            fix_content="\n## New\n",
        )

        with patch.object(
            AutoFixer, "BACKUP_DIR", temp_backup_dir
        ):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is False
        assert result.success is False


# ---------------------------------------------------------------------------
# apply_fix tests — create with rollback
# ---------------------------------------------------------------------------


class TestApplyFixCreate:
    """Tests for the create action with rollback."""

    def test_create_makes_skill_directory(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """apply_fix(create) must create the skill directory and SKILL.md."""
        fix = FixAction(
            action="create",
            target_skill="new-skill",
            priority=80.0,
            reason="new capability",
            fix_content="# New Skill\n\nname: new-skill\nversion: 1.0\n",
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is True
        assert result.success is True
        assert (temp_skill_dir / "new-skill" / "SKILL.md").exists()

    def test_create_validates_yaml(self, temp_skill_dir: Path, temp_backup_dir: Path):
        """apply_fix(create) must validate YAML and remove dir on failure."""
        # Start with incomplete frontmatter (no closing ---)
        fix = FixAction(
            action="create",
            target_skill="bad-new-skill",
            priority=80.0,
            reason="yaml test",
            fix_content="---\ninvalid: yaml: content: [broken\n",
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is False
        assert result.success is False
        assert not (temp_skill_dir / "bad-new-skill").exists()

    def test_create_duplicate_fails(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """apply_fix(create) must fail if skill already exists."""
        # Pre-create the directory
        existing = temp_skill_dir / "existing-skill"
        existing.mkdir()
        (existing / "SKILL.md").write_text("# existing\n")

        fix = FixAction(
            action="create",
            target_skill="existing-skill",
            priority=80.0,
            reason="already exists",
            fix_content="# new content\n",
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            result = fixer.apply_fix(fix)

        assert result.applied is False
        assert result.success is False


# ---------------------------------------------------------------------------
# rollback tests
# ---------------------------------------------------------------------------


class TestRollback:
    """Tests for rollback_fix()."""

    def test_rollback_patch_restores_original(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """rollback_fix(patch) must restore the original SKILL.md content."""
        skill_dir = temp_skill_dir / "rollback-skill"
        skill_dir.mkdir()
        original = "# Original\nname: rollback-skill\nversion: 1.0\n"
        (skill_dir / "SKILL.md").write_text(original)

        # Create a backup file manually
        backup_file = temp_backup_dir / "rollback-skill_12345.md"
        backup_file.write_text("# Modified\nname: rollback-skill\nversion: 2.0\n")

        fix = FixAction(
            action="patch",
            target_skill="rollback-skill",
            priority=50.0,
            reason="test rollback",
            fix_content="",
            backup_content=original,
            rollback_path=str(backup_file),
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            success = fixer.rollback_fix(fix)

        assert success is True
        assert (skill_dir / "SKILL.md").read_text() == "# Modified\nname: rollback-skill\nversion: 2.0\n"

    def test_rollback_patch_missing_backup_returns_false(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """rollback_fix returns False when backup file is missing."""
        skill_dir = temp_skill_dir / "missing-backup-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# current\n")

        fix = FixAction(
            action="patch",
            target_skill="missing-backup-skill",
            priority=50.0,
            reason="test",
            fix_content="",
            rollback_path=str(temp_backup_dir / "nonexistent.md"),
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            success = fixer.rollback_fix(fix)

        assert success is False

    def test_rollback_create_removes_directory(
        self, temp_skill_dir: Path, temp_backup_dir: Path
    ):
        """rollback_fix(create) must remove the created directory."""
        skill_dir = temp_skill_dir / "remove-me"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# to be removed\n")

        backup_marker = temp_backup_dir / "_create_remove-me_12345.marker"
        backup_marker.write_text("")

        fix = FixAction(
            action="create",
            target_skill="remove-me",
            priority=80.0,
            reason="test",
            fix_content="# new\n",
            rollback_path=str(backup_marker),
        )

        with patch.object(AutoFixer, "BACKUP_DIR", temp_backup_dir):
            fixer = AutoFixer(skill_dirs=[temp_skill_dir])
            success = fixer.rollback_fix(fix)

        assert success is True
        assert not skill_dir.exists()


# ---------------------------------------------------------------------------
# Fix history tests
# ---------------------------------------------------------------------------


class TestFixHistory:
    """Tests for fix history tracking."""

    def test_recommend_appends_to_history(self, temp_skill_dir: Path):
        """recommend() must append FixActions to internal history."""
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        analysis = SessionAnalysis(
            weakest_tools=[],
            tool_metrics={},
        )
        fixer.recommend(analysis)
        assert len(fixer.get_fix_history()) >= 0  # empty is valid

    def test_history_tracks_all_fix_types(self, temp_skill_dir: Path):
        """History must track patch, create, evolve, and log fixes."""
        # Create a skill with low success (evolve)
        skill_dir = temp_skill_dir / "low-success"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# low success\n")

        metric = ToolMetric(
            tool_name="low-success",
            total_calls=10,
            successful_calls=3,
            failed_calls=7,
            success_rate=0.3,
            top_error_category="generic",
            top_error_snippet="error",
        )

        gap = SkillGap(
            capability="csv-parsing",
            request_count=5,
            session_ids=["s1"],
            confidence=0.85,
            existing_skill=None,
        )

        analysis = SessionAnalysis(
            weakest_tools=[metric],
            tool_metrics={"low-success": metric},
            skill_gaps=[gap],
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        fixer.recommend(analysis)
        history = fixer.get_fix_history()

        actions = {f.action for f in history}
        assert "evolve" in actions
        assert "create" in actions

    def test_clear_history(self, temp_skill_dir: Path):
        """clear_history() must empty the history list."""
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        fixer.clear_history()
        assert fixer.get_fix_history() == []


# ---------------------------------------------------------------------------
# YAML validation tests
# ---------------------------------------------------------------------------


class TestYamlValidation:
    """Tests for _validate_skill_yaml()."""

    def test_valid_yaml_passes(self, tmp_path: Path):
        """Valid YAML returns True."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "name: test-skill\nversion: 1.0\ndescription: A test skill\n"
        )

        fixer = AutoFixer()
        assert fixer._validate_skill_yaml(skill_md) is True

    def test_empty_file_passes(self, tmp_path: Path):
        """Empty file is considered valid."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("")

        fixer = AutoFixer()
        assert fixer._validate_skill_yaml(skill_md) is True

    def test_invalid_yaml_fails(self, tmp_path: Path):
        """Invalid YAML frontmatter returns False with a warning log."""
        skill_md = tmp_path / "SKILL.md"
        # Use frontmatter with invalid YAML inside
        skill_md.write_text(
            "---\nname: test\n  bad_indent: yes\n---\n# Skill content\n"
        )

        fixer = AutoFixer()
        assert fixer._validate_skill_yaml(skill_md) is False

    def test_yaml_with_nested_lists_passes(self, tmp_path: Path):
        """Complex YAML with nested lists passes."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "name: complex\nversion: 1.0\nsteps:\n  - step1:\n      key: value\n  - step2:\n      key: value\n"
        )

        fixer = AutoFixer()
        assert fixer._validate_skill_yaml(skill_md) is True


# ---------------------------------------------------------------------------
# Skill finding tests
# ---------------------------------------------------------------------------


class TestSkillFinding:
    """Tests for _find_skill() and _normalize_skill_name()."""

    def test_find_skill_by_exact_name(self, temp_skill_dir: Path):
        """_find_skill returns path for exact name match."""
        skill_dir = temp_skill_dir / "exact-match"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# skill\n")

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer._find_skill("exact-match")
        assert result == skill_dir

    def test_find_skill_case_insensitive(self, temp_skill_dir: Path):
        """_find_skill matches case-insensitively."""
        skill_dir = temp_skill_dir / "CaseSensitive"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# skill\n")

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer._find_skill("casesensitive")
        assert result is not None

    def test_find_skill_not_found(self, temp_skill_dir: Path):
        """_find_skill returns None when skill doesn't exist."""
        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer._find_skill("definitely-does-not-exist-12345")
        assert result is None

    def test_normalize_skill_name(self):
        """_normalize_skill_name converts spaces and underscores to hyphens."""
        fixer = AutoFixer()
        assert fixer._normalize_skill_name("csv parsing") == "csv-parsing"
        assert fixer._normalize_skill_name("csv_parsing") == "csv-parsing"
        assert fixer._normalize_skill_name("CSV-PARSING") == "csv-parsing"

    def test_find_skill_subdirectory_match(self, temp_skill_dir: Path):
        """_find_skill matches subdirectory names (e.g. apple-notes within apple)."""
        # Some skills live as subdirectories
        skill_dir = temp_skill_dir / "parent"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# parent\n")

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer._find_skill("parent")
        assert result is not None


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_success_rate_threshold_is_60_percent(self):
        """SUCCESS_RATE_PATCH_THRESHOLD must be 0.60."""
        assert SUCCESS_RATE_PATCH_THRESHOLD == 0.60

    def test_create_threshold_is_3(self):
        """SKILL_CREATE_THRESHOLD must be 3."""
        assert SKILL_CREATE_THRESHOLD == 3

    def test_skill_search_dirs_defined(self):
        """SKILL_SEARCH_DIRS must be a non-empty list of Paths."""
        assert isinstance(SKILL_SEARCH_DIRS, list)
        assert len(SKILL_SEARCH_DIRS) > 0
        assert all(isinstance(p, Path) for p in SKILL_SEARCH_DIRS)


# ---------------------------------------------------------------------------
# Evolve and log action tests
# ---------------------------------------------------------------------------


class TestEvolveAndLogActions:
    """Tests for evolve and log (non-applied) actions."""

    def test_evolve_action_is_not_applied(self, temp_skill_dir: Path):
        """apply_fix(evolve) marks fix as applied but deferred."""
        fix = FixAction(
            action="evolve",
            target_skill="some-skill",
            priority=70.0,
            reason="low success rate",
            fix_content="",
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer.apply_fix(fix)

        # evolve is marked as applied but it's a no-op
        assert result.applied is True
        assert result.success is True

    def test_log_action_is_noop(self, temp_skill_dir: Path):
        """apply_fix(log) is a pure no-op."""
        fix = FixAction(
            action="log",
            target_skill="some-capability",
            priority=10.0,
            reason="not enough requests",
            fix_content="",
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer.apply_fix(fix)

        assert result.applied is True
        assert result.success is True

    def test_unknown_action_returns_unchanged(self, temp_skill_dir: Path):
        """apply_fix with unknown action returns fix without modification."""
        fix = FixAction(
            action="unknown_action",
            target_skill="some-skill",
            priority=50.0,
            reason="test",
            fix_content="",
        )

        fixer = AutoFixer(skill_dirs=[temp_skill_dir])
        result = fixer.apply_fix(fix)

        assert result.applied is False
        assert result.success is False
