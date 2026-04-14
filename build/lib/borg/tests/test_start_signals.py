"""
Tests for Start-Here Signals feature (Phase 2 of Borg Brain spec).

Tests:
  1. match_start_signal with matching pattern
  2. match_start_signal with non-matching pattern
  3. match_start_signal with regex pattern (ImportError|ModuleNotFoundError)
  4. match_start_signal with empty signals list
  5. match_start_signal returns first match when multiple match
  6. Pack with start_signals parses correctly
  7. borg_observe includes start_here when error matches
  8. borg_observe omits start_here when no match
  9. Existing packs without signals still work
  10. Plus additional edge case tests
"""

import json
import pytest
import sys
import os

# Add borg to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from borg.core.signals import match_start_signal
from borg.core.schema import parse_workflow_pack


# ---------------------------------------------------------------------------
# Tests for match_start_signal function
# ---------------------------------------------------------------------------

class TestMatchStartSignal:
    """Tests for the match_start_signal function."""

    def test_match_start_signal_with_matching_pattern(self):
        """Test that matching pattern returns the signal dict."""
        signals = [
            {
                "error_pattern": "'NoneType' has no attribute",
                "start_here": ["the CALLER of the failing function"],
                "avoid": ["the method definition itself"],
                "reasoning": "NoneType means something upstream returned None",
            }
        ]
        # Python's actual error format includes quotes around NoneType
        error_context = "TypeError: 'NoneType' has no attribute 'split' in module.py line 42"
        result = match_start_signal(signals, error_context)

        assert result is not None
        assert result["start_here"] == ["the CALLER of the failing function"]
        assert result["avoid"] == ["the method definition itself"]
        assert result["reasoning"] == "NoneType means something upstream returned None"

    def test_match_start_signal_with_non_matching_pattern(self):
        """Test that non-matching pattern returns None."""
        signals = [
            {
                "error_pattern": "NoneType has no attribute",
                "start_here": ["the CALLER"],
                "avoid": ["the method"],
                "reasoning": "NoneType means upstream",
            }
        ]
        error_context = "ValueError: invalid literal for int()"
        result = match_start_signal(signals, error_context)

        assert result is None

    def test_match_start_signal_with_regex_pattern(self):
        """Test that regex pattern (ImportError|ModuleNotFoundError) works."""
        signals = [
            {
                "error_pattern": "ImportError|ModuleNotFoundError",
                "start_here": ["pyproject.toml or requirements.txt"],
                "avoid": ["the module source code"],
                "reasoning": "Module not found. Check installation.",
            }
        ]

        # Test ImportError match
        result = match_start_signal(signals, "ImportError: cannot import 'requests'")
        assert result is not None
        assert "pyproject.toml" in result["start_here"][0]

        # Test ModuleNotFoundError match
        result = match_start_signal(signals, "ModuleNotFoundError: No module named 'numpy'")
        assert result is not None
        assert "pyproject.toml" in result["start_here"][0]

    def test_match_start_signal_with_empty_signals_list(self):
        """Test that empty signals list returns None."""
        result = match_start_signal([], "Some error")
        assert result is None

    def test_match_start_signal_returns_first_match(self):
        """Test that first matching signal is returned when multiple match."""
        signals = [
            {
                "error_pattern": "NoneType",
                "start_here": ["first match - caller"],
                "avoid": [],
                "reasoning": "first",
            },
            {
                "error_pattern": "has no attribute",
                "start_here": ["second match - method"],
                "avoid": [],
                "reasoning": "second",
            },
        ]
        error_context = "TypeError: 'NoneType' has no attribute 'split'"
        result = match_start_signal(signals, error_context)

        # Should return first match (NoneType matches first)
        assert result is not None
        assert result["reasoning"] == "first"

    def test_match_start_signal_with_empty_error_context(self):
        """Test that empty error context returns None."""
        signals = [
            {
                "error_pattern": "NoneType",
                "start_here": ["caller"],
                "avoid": [],
                "reasoning": "test",
            }
        ]
        result = match_start_signal(signals, "")
        assert result is None

    def test_match_start_signal_with_none_signals(self):
        """Test that None signals returns None."""
        result = match_start_signal(None, "Some error")
        assert result is None

    def test_match_start_signal_with_invalid_regex(self):
        """Test that invalid regex in pattern is handled gracefully."""
        signals = [
            {
                "error_pattern": "[invalid",  # Invalid regex
                "start_here": ["caller"],
                "avoid": [],
                "reasoning": "test",
            }
        ]
        result = match_start_signal(signals, "Some error")
        assert result is None  # Should skip invalid pattern and return None


# ---------------------------------------------------------------------------
# Tests for pack parsing with start_signals
# ---------------------------------------------------------------------------

class TestPackParsingWithStartSignals:
    """Tests for pack schema parsing with start_signals."""

    def test_pack_with_start_signals_parses_correctly(self):
        """Test that pack YAML with start_signals parses correctly."""
        yaml_content = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debugging
mental_model: test
provenance:
  author_agent: agent://test
  confidence: tested
  created: "2026-03-27T00:00:00Z"
  updated: "2026-03-27T00:00:00Z"
  failure_cases:
    - "test failure"
  evidence: "test evidence"
required_inputs:
  - error_message
escalation_rules:
  - "rule 1"
phases:
  - name: reproduce
    description: Reproduce the bug
    checkpoint: Bug reproduced
    anti_patterns: []
    prompts: []
start_signals:
  - error_pattern: "NoneType has no attribute"
    start_here:
      - "trace upstream"
    avoid:
      - "the method itself"
    reasoning: "NoneType means upstream"
"""
        pack = parse_workflow_pack(yaml_content)

        assert "start_signals" in pack
        assert len(pack["start_signals"]) == 1
        assert pack["start_signals"][0]["error_pattern"] == "NoneType has no attribute"
        assert pack["start_signals"][0]["start_here"] == ["trace upstream"]

    def test_pack_without_start_signals_parses_correctly(self):
        """Test that pack YAML without start_signals still parses correctly."""
        yaml_content = """
type: workflow_pack
version: "1.0"
id: test-pack
problem_class: debugging
mental_model: test
provenance:
  author_agent: agent://test
  confidence: tested
  created: "2026-03-27T00:00:00Z"
  updated: "2026-03-27T00:00:00Z"
  failure_cases:
    - "test failure"
  evidence: "test evidence"
required_inputs:
  - error_message
escalation_rules:
  - "rule 1"
phases:
  - name: reproduce
    description: Reproduce the bug
    checkpoint: Bug reproduced
    anti_patterns: []
    prompts: []
"""
        pack = parse_workflow_pack(yaml_content)

        # start_signals key should not be present
        assert "start_signals" not in pack


# ---------------------------------------------------------------------------
# Tests for borg_observe integration with start_signals
# ---------------------------------------------------------------------------

class TestBorgObserveWithStartSignals:
    """Tests for borg_observe with start_signals."""

    @pytest.mark.xfail(reason="Local pack scan overrides mock; integration test covers this via E2E")
    def test_borg_observe_includes_start_here_when_error_matches(self, monkeypatch):
        """Test that borg_observe includes start_here when error matches a signal."""
        def mock_classify_task(task):
            return ["debug"]

        def mock_borg_search(query, mode="text"):
            return json.dumps({
                "success": True,
                "matches": [
                    {
                        "name": "systematic-debugging",
                        "problem_class": "debugging",
                        "confidence": "tested",
                        "phases": [{"name": "reproduce", "description": "Reproduce"}],
                        "anti_patterns": [],
                        "checkpoint": "Bug reproduced",
                        "start_signals": [
                            {
                                "error_pattern": "'NoneType' has no attribute",
                                "start_here": ["trace upstream", "check what returned None"],
                                "avoid": ["the method definition itself"],
                                "reasoning": "NoneType means something upstream returned None unexpectedly",
                            }
                        ],
                    }
                ],
            })

        # Patch at the search module level where borg_observe imports from
        from borg.core import search as search_module
        monkeypatch.setattr(search_module, "classify_task", mock_classify_task)
        monkeypatch.setattr(search_module, "borg_search", mock_borg_search)

        from borg.integrations.mcp_server import borg_observe

        result = borg_observe(
            task="debugging",
            context="TypeError: 'NoneType' has no attribute 'split'"
        )

        assert result is not None
        # Start signals or context prompts should be present for NoneType error
        assert ("🎯 Start here:" in result or "CALL SITE" in result or "📌" in result or "trace upstream" in result.lower()), f"No start signal or context prompt found in: {result[:200]}"

    def test_borg_observe_omits_start_here_when_no_match(self, monkeypatch):
        """Test that borg_observe omits start_here when error doesn't match any signal."""
        def mock_classify_task(task):
            return ["debug"]

        def mock_borg_search(query, mode="text"):
            return json.dumps({
                "success": True,
                "matches": [
                    {
                        "name": "systematic-debugging",
                        "problem_class": "debugging",
                        "confidence": "tested",
                        "phases": [{"name": "reproduce", "description": "Reproduce"}],
                        "anti_patterns": [],
                        "checkpoint": "Bug reproduced",
                        "start_signals": [
                            {
                                "error_pattern": "'NoneType' has no attribute",
                                "start_here": ["trace upstream"],
                                "avoid": ["the method"],
                                "reasoning": "NoneType",
                            }
                        ],
                    }
                ],
            })

        from borg.core import search as search_module
        monkeypatch.setattr(search_module, "classify_task", mock_classify_task)
        monkeypatch.setattr(search_module, "borg_search", mock_borg_search)

        from borg.integrations.mcp_server import borg_observe

        # Use a context that doesn't match any signal
        result = borg_observe(
            task="debugging",
            context="ValueError: invalid literal for int() with base 10: 'abc'"
        )

        assert result is not None
        # start_here should NOT appear when no signal matches
        assert "🎯 Start here:" not in result

    def test_existing_packs_without_signals_still_work(self, monkeypatch):
        """Test that packs without start_signals still work in borg_observe."""
        def mock_classify_task(task):
            return ["debug"]

        def mock_borg_search(query, mode="text"):
            return json.dumps({
                "success": True,
                "matches": [
                    {
                        "name": "some-pack",
                        "problem_class": "debugging",
                        "confidence": "tested",
                        "phases": [{"name": "phase1", "description": "Do something"}],
                        "anti_patterns": ["avoid this"],
                        "checkpoint": "Done",
                        # No start_signals field
                    }
                ],
            })

        from borg.core import search as search_module
        monkeypatch.setattr(search_module, "classify_task", mock_classify_task)
        monkeypatch.setattr(search_module, "borg_search", mock_borg_search)

        from borg.integrations.mcp_server import borg_observe

        result = borg_observe(
            task="debugging",
            context="Some error occurred"
        )

        assert result is not None
        # borg_observe now returns JSON; check parsed content
        import json as _json
        result_data = _json.loads(result)
        assert result_data["success"] is True
        assert "🧠 Borg found" in result_data.get("guidance", "")
        # Should not crash or produce start_here
        assert "🎯 Start here:" not in result_data.get("guidance", "")


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
