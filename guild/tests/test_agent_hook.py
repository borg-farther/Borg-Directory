"""
Tests for guild/integrations/agent_hook.py — T1.10 agent integration bridge.

Tests:
    guild_on_failure    — wraps check_for_suggestion, formats output
    guild_on_task_start — proactive search via classify_task + guild_search
    guild_format_pack_suggestion — formats pack metadata into readable string
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from guild.integrations.agent_hook import (
    guild_on_failure,
    guild_on_task_start,
    guild_format_pack_suggestion,
)


# -------------------------------------------------------------------------- -
# Fixtures
# -------------------------------------------------------------------------- -

def _mock_suggestion(
    has_suggestion=True,
    suggestion="Guild pack available: systematic-debugging (Debugging workflow). "
              "Try: guild_try guild://hermes/systematic-debugging",
    pack_name="systematic-debugging",
    confidence="tested",
    problem_class="Debugging workflow",
    why="matches your debug task",
    search_terms=None,
    match_count=1,
):
    """Build a fake check_for_suggestion JSON response."""
    suggestions_list = []
    if has_suggestion:
        suggestions_list.append({
            "pack_name": pack_name,
            "confidence": confidence,
            "problem_class": problem_class,
            "why_relevant": why,
        })

    return json.dumps({
        "has_suggestion": has_suggestion,
        "suggestion": suggestion if has_suggestion else "",
        "suggestions": suggestions_list,
        "pack_name": pack_name if has_suggestion else "",
        "pack_uri": f"guild://hermes/{pack_name}" if has_suggestion else "",
        "search_terms": search_terms or [],
        "match_count": match_count,
    })


# -------------------------------------------------------------------------- -
# guild_on_failure tests
# -------------------------------------------------------------------------- -

class TestGuildOnFailure:
    """Tests for guild_on_failure()."""

    def test_returns_none_when_no_context_and_low_failure_count(self):
        """No suggestion if context is empty and failure_count < 2."""
        result = guild_on_failure(context="", failure_count=1)
        assert result is None

    def test_calls_check_for_suggestion_with_correct_args(self):
        """guild_on_failure passes context and failure_count to check_for_suggestion."""
        mock_response = _mock_suggestion()
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response) as mock_check:
            result = guild_on_failure(
                context="the build is still failing with the same error",
                failure_count=2,
                tried_packs=["some-pack"],
            )

        mock_check.assert_called_once_with(
            conversation_context="the build is still failing with the same error",
            failure_count=2,
            tried_packs=["some-pack"],
        )
        assert result is not None
        assert "systematic-debugging" in result

    def test_returns_none_when_check_returns_no_suggestion(self):
        """When check_for_suggestion has has_suggestion=False, guild_on_failure returns None."""
        mock_response = json.dumps({"has_suggestion": False})
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response):
            result = guild_on_failure(context="some context", failure_count=3)

        assert result is None

    def test_returns_formatted_suggestion_on_has_suggestion_true(self):
        """When has_suggestion=True, returns the formatted suggestion string."""
        mock_response = _mock_suggestion(
            suggestion="Guild pack available: systematic-debugging (Debugging workflow). "
                      "Try: guild_try guild://hermes/systematic-debugging",
        )
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response):
            result = guild_on_failure(context="still failing", failure_count=2)

        assert result is not None
        assert "systematic-debugging" in result

    def test_falls_back_to_suggestions_list_when_suggestion_field_empty(self):
        """If 'suggestion' field is empty but 'suggestions' list is present, format from list."""
        mock_response = json.dumps({
            "has_suggestion": True,
            "suggestion": "",
            "suggestions": [{
                "pack_name": "test-pack",
                "confidence": "tested",
                "problem_class": "Testing workflow",
                "why_relevant": "matches your test task",
            }],
            "pack_name": "test-pack",
            "search_terms": ["test"],
            "match_count": 1,
        })
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response):
            result = guild_on_failure(context="test is failing", failure_count=2)

        assert result is not None
        assert "test-pack" in result

    def test_returns_none_on_unparseable_json(self):
        """Unparseable JSON from check_for_suggestion returns None (no crash)."""
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value="not json {{{"):
            result = guild_on_failure(context="still failing", failure_count=2)

        assert result is None

    def test_passes_tried_packs_to_check_for_suggestion(self):
        """tried_packs list is forwarded to check_for_suggestion."""
        mock_response = _mock_suggestion()
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response) as mock_check:
            guild_on_failure(
                context="still failing",
                failure_count=2,
                tried_packs=["already-tried-pack", "another-pack"],
            )

        _, kwargs = mock_check.call_args
        assert kwargs["tried_packs"] == ["already-tried-pack", "another-pack"]

    def test_frustration_signals_trigger_suggestion_even_with_low_failure_count(self):
        """Context with frustration signals triggers suggestion even when failure_count < 2."""
        mock_response = _mock_suggestion()
        with patch("guild.integrations.agent_hook.check_for_suggestion", return_value=mock_response) as mock_check:
            guild_on_failure(
                context="I've tried everything and it keeps failing",
                failure_count=1,
            )

        mock_check.assert_called_once()
        _, kwargs = mock_check.call_args
        assert kwargs["failure_count"] == 1


# -------------------------------------------------------------------------- -
# guild_on_task_start tests
# -------------------------------------------------------------------------- -

class TestGuildOnTaskStart:
    """Tests for guild_on_task_start()."""

    def test_returns_none_for_empty_task_description(self):
        """Empty task description returns None immediately."""
        result = guild_on_task_start("")
        assert result is None

        result = guild_on_task_start("   ")
        assert result is None

    def test_calls_classify_task_and_guild_search(self):
        """guild_on_task_start calls classify_task then guild_search for each term."""
        mock_matches = json.dumps({
            "success": True,
            "matches": [{
                "name": "test-driven-dev",
                "confidence": "inferred",
                "problem_class": "TDD workflow",
            }],
        })

        with patch("guild.integrations.agent_hook.classify_task", return_value=["test"]) as mock_classify:
            with patch("guild.integrations.agent_hook.guild_search", return_value=mock_matches) as mock_search:
                result = guild_on_task_start("I need to write unit tests for my function")

        mock_classify.assert_called_once_with("I need to write unit tests for my function")
        mock_search.assert_called_once_with("test")
        assert result is not None
        assert "test-driven-dev" in result

    def test_returns_none_when_classify_task_returns_empty(self):
        """If classify_task finds no terms, returns None without searching."""
        with patch("guild.integrations.agent_hook.classify_task", return_value=[]):
            result = guild_on_task_start("do something vague")

        assert result is None

    def test_returns_none_when_guild_search_returns_no_matches(self):
        """If guild_search finds nothing, returns None."""
        with patch("guild.integrations.agent_hook.classify_task", return_value=["debug"]):
            with patch("guild.integrations.agent_hook.guild_search", return_value=json.dumps({"success": True, "matches": []})):
                result = guild_on_task_start("my code has an error")

        assert result is None

    def test_deduplicates_packs_by_name(self):
        """Same pack matched by multiple terms appears only once."""
        single_match = json.dumps({
            "success": True,
            "matches": [{
                "name": "systematic-debugging",
                "confidence": "tested",
                "problem_class": "Debugging workflow",
            }],
        })

        with patch("guild.integrations.agent_hook.classify_task", return_value=["debug", "error"]):
            with patch("guild.integrations.agent_hook.guild_search", return_value=single_match):
                result = guild_on_task_start("debugging an error in my code")

        # Should mention systematic-debugging only once
        assert result is not None
        assert result.count("systematic-debugging") == 1

    def test_single_match_uses_singular_wording(self):
        """One match uses 'this useful' (singular)."""
        mock_matches = json.dumps({
            "success": True,
            "matches": [{
                "name": "deploy-pipeline",
                "confidence": "guessed",
                "problem_class": "CI/CD",
            }],
        })

        with patch("guild.integrations.agent_hook.classify_task", return_value=["deploy"]):
            with patch("guild.integrations.agent_hook.guild_search", return_value=mock_matches):
                result = guild_on_task_start("I need to set up deployment")

        assert result is not None
        assert "this useful" in result

    def test_multiple_matches_uses_plural_wording(self):
        """Multiple matches use 'these useful' (plural)."""
        mock_matches = json.dumps({
            "success": True,
            "matches": [
                {
                    "name": "deploy-pipeline",
                    "confidence": "guessed",
                    "problem_class": "CI/CD",
                },
                {
                    "name": "github-actions",
                    "confidence": "inferred",
                    "problem_class": "GitHub workflow",
                },
            ],
        })

        with patch("guild.integrations.agent_hook.classify_task", return_value=["deploy", "github"]):
            with patch("guild.integrations.agent_hook.guild_search", return_value=mock_matches):
                result = guild_on_task_start("I need CI and GitHub actions")

        assert result is not None
        assert "these useful" in result

    def test_handles_json_decode_error_gracefully(self):
        """guild_search returning bad JSON is skipped without crashing."""
        with patch("guild.integrations.agent_hook.classify_task", return_value=["debug"]):
            with patch("guild.integrations.agent_hook.guild_search", return_value="not json {{{"):
                result = guild_on_task_start("my code is broken")

        assert result is None


# -------------------------------------------------------------------------- -
# guild_format_pack_suggestion tests
# -------------------------------------------------------------------------- -

class TestGuildFormatPackSuggestion:
    """Tests for guild_format_pack_suggestion()."""

    def test_empty_pack_name_returns_empty_string(self):
        result = guild_format_pack_suggestion("", "tested", "Debugging", "matches debug")
        assert result == ""

    def test_full_args_returns_readable_string(self):
        result = guild_format_pack_suggestion(
            pack_name="systematic-debugging",
            confidence="tested",
            problem_class="Debugging workflow",
            why="matches your debug task",
        )

        assert "systematic-debugging" in result
        assert "[tested]" in result
        assert "Debugging workflow" in result
        assert "matches your debug task" in result

    def test_without_confidence_no_badge(self):
        """Confidence 'unknown' or empty does not add a badge."""
        result = guild_format_pack_suggestion(
            pack_name="my-pack",
            confidence="",
            problem_class="Some workflow",
            why="",
        )

        assert "my-pack" in result
        assert "[" not in result

    def test_without_confidence_unknown_no_badge(self):
        result = guild_format_pack_suggestion(
            pack_name="my-pack",
            confidence="unknown",
            problem_class="Some workflow",
            why="",
        )

        assert "my-pack" in result
        assert "[" not in result

    def test_without_why_suffix(self):
        """When 'why' is empty, no trailing explanation is appended."""
        result = guild_format_pack_suggestion(
            pack_name="simple-pack",
            confidence="guessed",
            problem_class="Simple workflow",
            why="",
        )

        assert "simple-pack" in result
        assert "[" not in result or "[guessed]" in result

    def test_short_result_gets_try_command(self):
        """When formatted result is short (name + maybe badge only),
        the guild:// URI is appended."""
        result = guild_format_pack_suggestion(
            pack_name="quick-pack",
            confidence="",
            problem_class="",
            why="",
        )

        assert "guild://hermes/quick-pack" in result

    def test_uri_is_appended_when_result_is_short(self):
        """URI is appended only when result is short (name ± badge ± single parenthetical)."""
        # Full args -> long enough, no URI appended
        long_result = guild_format_pack_suggestion(
            pack_name="my-pack-name",
            confidence="tested",
            problem_class="My problem",
            why="why it matches",
        )
        assert "guild://hermes/my-pack-name" not in long_result

        # Minimal args -> short, URI is appended
        short_result = guild_format_pack_suggestion(
            pack_name="my-pack-name",
            confidence="",
            problem_class="",
            why="",
        )
        assert "guild://hermes/my-pack-name" in short_result
