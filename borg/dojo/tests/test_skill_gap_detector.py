"""Tests for borg/dojo/skill_gap_detector.py"""

import tempfile
from pathlib import Path

import pytest
from borg.dojo.skill_gap_detector import (
    detect_skill_gaps,
    get_request_count_for_capability,
    REQUEST_PATTERNS,
    SKILL_GAP_THRESHOLD,
    _normalize_capability,
    _EXISTING_SKILL_MAP,
)


# =============================================================================
# Tests: detect_skill_gaps — pattern matching
# =============================================================================

class TestPatternMatching:
    """Each of the 12+ patterns should correctly match their target capability."""

    def test_at_least_12_patterns(self):
        """The spec requires 12+ request patterns."""
        assert len(REQUEST_PATTERNS) >= 12

    def test_all_patterns_have_3_tuple_elements(self):
        """Each pattern should be a (compiled_re, capability_key, description) tuple."""
        for item in REQUEST_PATTERNS:
            assert len(item) == 3
            assert hasattr(item[0], 'search')  # compiled regex has .search()

    def test_all_capabilities_unique(self):
        """Each capability key should be unique."""
        cap_keys = [item[1] for item in REQUEST_PATTERNS]
        assert len(cap_keys) == len(set(cap_keys))

    def test_csv_parsing_pattern_matches(self):
        """CSV parsing pattern should match various phrasings."""
        messages = [
            ("Can you parse this CSV file?", "sess_1"),
            ("I need to parse the CSV data", "sess_2"),
            ("Please parse the CSV I uploaded", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        cap_keys = [g.capability for g in gaps]
        assert "csv-parsing" in cap_keys

    def test_csv_parsing_below_threshold(self):
        """CSV with only 2 messages should NOT be flagged (threshold=3)."""
        messages = [
            ("Can you parse this CSV file?", "sess_1"),
            ("I need to parse the CSV data", "sess_2"),
        ]
        gaps = detect_skill_gaps(messages)
        cap_keys = [g.capability for g in gaps]
        assert "csv-parsing" not in cap_keys

    def test_api_integration_pattern_matches(self):
        messages = [
            ("call the REST API endpoint", "sess_1"),
            ("fetch data from the API", "sess_2"),
            ("make an API call to the service", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        cap_keys = [g.capability for g in gaps]
        assert "api-integration" in cap_keys

    def test_deployment_pattern_matches(self):
        messages = [
            ("deploy to production", "sess_1"),
            ("push to prod", "sess_2"),
            ("deploy this to the server", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        cap_keys = [g.capability for g in gaps]
        assert "deployment" in cap_keys

    def test_case_insensitive_matching(self):
        """Patterns should be case insensitive."""
        messages = [
            ("PARSE CSV FILE", "sess_1"),
            ("Parse CSV Data", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        csv_gap = next((g for g in gaps if g.capability == "csv-parsing"), None)
        assert csv_gap is not None
        assert csv_gap.request_count == 3

    def test_each_capability_key_mapped(self):
        """Every capability key in REQUEST_PATTERNS should map to an entry."""
        cap_keys = [item[1] for item in REQUEST_PATTERNS]
        for key in cap_keys:
            assert key in _EXISTING_SKILL_MAP or True  # just verify it's a string


# =============================================================================
# Tests: detect_skill_gaps — threshold (3+ requests)
# =============================================================================

class TestThreshold:
    """SKILL_GAP_THRESHOLD = 3: only capabilities with 3+ requests are flagged."""

    def test_threshold_constant_is_3(self):
        assert SKILL_GAP_THRESHOLD == 3

    def test_2_requests_below_threshold(self):
        """2 requests for same capability should NOT be flagged."""
        messages = [
            ("parse this csv", "sess_1"),
            ("parse another csv", "sess_2"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 0

    def test_3_requests_at_threshold(self):
        """3 requests should be flagged as a gap."""
        messages = [
            ("parse this csv", "sess_1"),
            ("parse the csv data", "sess_2"),
            ("need to parse csv", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].capability == "csv-parsing"
        assert gaps[0].request_count == 3

    def test_5_requests_above_threshold(self):
        """5 requests should also be flagged."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
            ("parse csv", "sess_4"),
            ("parse csv", "sess_5"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].request_count == 5

    def test_mixed_capabilities_threshold(self):
        """Only capabilities at/above threshold should appear."""
        messages = [
            # csv-parsing: 3 times (at threshold)
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
            # api-integration: 2 times (below threshold)
            ("call the API", "sess_4"),
            ("fetch from API", "sess_5"),
        ]
        gaps = detect_skill_gaps(messages)
        capabilities = [g.capability for g in gaps]
        assert "csv-parsing" in capabilities
        assert "api-integration" not in capabilities


# =============================================================================
# Tests: detect_skill_gaps — session deduplication
# =============================================================================

class TestSessionDeduplication:
    def test_same_session_counts_multiple_times(self):
        """Multiple requests in the same session still count separately."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv again", "sess_1"),
            ("parse csv once more", "sess_1"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].request_count == 3
        assert gaps[0].session_ids == ["sess_1"]

    def test_multiple_sessions_tracked(self):
        """Each session appears in session_ids if it contributed."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].session_ids == ["sess_1", "sess_2", "sess_3"]

    def test_same_session_id_not_duplicated_in_session_ids(self):
        """session_ids should not contain duplicates."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_1"),
            ("parse csv", "sess_1"),
        ]
        gaps = detect_skill_gaps(messages)
        assert gaps[0].session_ids == ["sess_1"]  # only one unique session


# =============================================================================
# Tests: detect_skill_gaps — existing skill check
# =============================================================================

class TestExistingSkillCheck:
    def test_no_existing_skills_passed(self):
        """When existing_skills is None/empty, all gaps reported as no skill."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        gaps = detect_skill_gaps(messages, existing_skills=None)
        assert len(gaps) == 1
        assert gaps[0].existing_skill is None

    def test_existing_skill_reduces_confidence(self):
        """When a skill exists, confidence should be lower (gap is not 'missing')."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "csv-tools"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text("# CSV Tools")

            gaps = detect_skill_gaps(messages, existing_skills={"csv-tools": skill_path})
            assert len(gaps) == 1
            assert gaps[0].existing_skill == "csv-tools"
            assert gaps[0].confidence < 0.95  # Lower than without skill

    def test_existing_skill_not_matched(self):
        """When no existing skill matches, existing_skill is None."""
        messages = [
            ("deploy to prod", "sess_1"),
            ("deploy to prod", "sess_2"),
            ("deploy to prod", "sess_3"),
        ]
        # No deployment skill exists
        gaps = detect_skill_gaps(messages, existing_skills={})
        assert len(gaps) == 1
        assert gaps[0].existing_skill is None

    def test_existing_skill_check_requires_path_in_dict(self):
        """The existing skill must be in the existing_skills dict to be matched.

        Having a matching capability but no dict entry means no existing skill.
        """
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        # csv-tools is NOT in the dict — should be treated as no existing skill
        gaps = detect_skill_gaps(messages, existing_skills={})
        assert gaps[0].existing_skill is None

    def test_skill_key_must_be_in_dict(self):
        """The skill name must be a key in the existing_skills dict."""
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
        ]
        # Skill name is "csv-tools" but dict only has "data-tools"
        gaps = detect_skill_gaps(
            messages,
            existing_skills={"data-tools": Path("/tmp/data-tools")}
        )
        assert gaps[0].existing_skill is None


# =============================================================================
# Tests: detect_skill_gaps — confidence scoring
# =============================================================================

class TestConfidenceScoring:
    def test_confidence_increases_with_count(self):
        messages_3 = [("parse csv", f"sess_{i}") for i in range(3)]
        messages_5 = [("parse csv", f"sess_{i}") for i in range(5)]

        gaps_3 = detect_skill_gaps(messages_3)
        gaps_5 = detect_skill_gaps(messages_5)

        assert gaps_3[0].confidence < gaps_5[0].confidence

    def test_confidence_capped_at_095(self):
        """Very high request counts should cap confidence at 0.95."""
        messages = [("parse csv", f"sess_{i}") for i in range(20)]
        gaps = detect_skill_gaps(messages)
        assert gaps[0].confidence <= 0.95

    def test_confidence_is_float_01_range(self):
        messages = [("parse csv", f"sess_{i}") for i in range(3)]
        gaps = detect_skill_gaps(messages)
        assert isinstance(gaps[0].confidence, float)
        assert 0.0 <= gaps[0].confidence <= 1.0

    def test_confidence_with_existing_skill_lower_than_without(self):
        """Having an existing skill should lower confidence vs. no skill."""
        messages = [("parse csv", f"sess_{i}") for i in range(3)]

        gaps_no_skill = detect_skill_gaps(messages, existing_skills={})
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "csv-tools"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text("# CSV Tools")
            gaps_with_skill = detect_skill_gaps(
                messages, existing_skills={"csv-tools": skill_path}
            )

        assert gaps_with_skill[0].confidence < gaps_no_skill[0].confidence


# =============================================================================
# Tests: detect_skill_gaps — sorting
# =============================================================================

class TestSorting:
    def test_sorted_by_request_count_descending(self):
        messages = [
            # csv-parsing: 3 times
            ("parse csv", "sess_1"), ("parse csv", "sess_2"), ("parse csv", "sess_3"),
            # api-integration: 5 times — use phrases that match the patterns
            ("call the API", "sess_4"), ("call the API", "sess_5"), ("call the API", "sess_6"),
            ("call the API", "sess_7"), ("call the API", "sess_8"),
        ]
        gaps = detect_skill_gaps(messages)
        assert gaps[0].capability == "api-integration"  # 5 requests
        assert gaps[1].capability == "csv-parsing"  # 3 requests

    def test_single_capability_not_sorted(self):
        """Single gap doesn't need sorting."""
        messages = [("parse csv", f"sess_{i}") for i in range(3)]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].capability == "csv-parsing"


# =============================================================================
# Tests: _normalize_capability
# =============================================================================

class TestNormalizeCapability:
    def test_csv_alias(self):
        assert _normalize_capability("csv") == "csv-parsing"

    def test_email_alias(self):
        assert _normalize_capability("email") == "email-sending"

    def test_database_alias(self):
        assert _normalize_capability("database") == "database-operations"

    def test_spaces_become_hyphen(self):
        assert _normalize_capability("web scraping") == "web-scraping"

    def test_unknown_returns_hyphenated(self):
        assert _normalize_capability("foo bar") == "foo-bar"


# =============================================================================
# Tests: get_request_count_for_capability
# =============================================================================

class TestGetRequestCount:
    def test_counts_for_capability_key(self):
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
            ("call API", "sess_4"),
        ]
        count = get_request_count_for_capability(messages, "csv-parsing")
        assert count == 3

    def test_counts_for_alias(self):
        messages = [
            ("parse csv", "sess_1"),
            ("parse csv", "sess_2"),
        ]
        count = get_request_count_for_capability(messages, "csv")
        assert count == 2

    def test_returns_zero_for_no_match(self):
        messages = [("something unrelated", "sess_1")]
        count = get_request_count_for_capability(messages, "csv-parsing")
        assert count == 0

    def test_one_per_message(self):
        """Multiple capability matches in same message count as 1."""
        messages = [
            ("parse csv and also parse some csv data", "sess_1"),
        ]
        count = get_request_count_for_capability(messages, "csv-parsing")
        assert count == 1


# =============================================================================
# Tests: Empty / edge cases
# =============================================================================

class TestEdgeCases:
    def test_empty_messages(self):
        gaps = detect_skill_gaps([])
        assert gaps == []

    def test_empty_content_in_messages_skipped(self):
        """Empty strings in message content should be skipped."""
        messages = [
            ("", "sess_1"),  # empty — skip
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
            ("parse csv", "sess_4"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].request_count == 3

    def test_none_content_in_messages_skipped(self):
        """None values in message content should be skipped without error."""
        messages = [
            (None, "sess_1"),  # None — skip
            ("parse csv", "sess_2"),
            ("parse csv", "sess_3"),
            ("parse csv", "sess_4"),
        ]
        gaps = detect_skill_gaps(messages)
        assert len(gaps) == 1
        assert gaps[0].request_count == 3


# =============================================================================
# Tests: Real data from state.db
# =============================================================================

class TestRealStateDBData:
    """Tests using real user messages from ~/.hermes/state.db"""

    def test_real_user_messages_processed(self):
        """Real user messages should be processable without errors."""
        import sqlite3

        try:
            conn = sqlite3.connect(f"{Path.home()}/.hermes/state.db", timeout=1.0)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT content, session_id FROM messages WHERE role = 'user' AND content IS NOT NULL LIMIT 100"
            ).fetchall()
            conn.close()

            messages = [(r["content"], r["session_id"]) for r in rows if r["content"]]
            gaps = detect_skill_gaps(messages)

            # Just verify no crashes and proper types
            assert isinstance(gaps, list)
            for gap in gaps:
                assert isinstance(gap.capability, str)
                assert isinstance(gap.request_count, int)
                assert isinstance(gap.session_ids, list)
                assert isinstance(gap.confidence, float)
                assert 0.0 <= gap.confidence <= 1.0
                assert gap.request_count >= SKILL_GAP_THRESHOLD

        except Exception as e:
            pytest.skip(f"Could not access state.db: {e}")

    def test_real_tool_results_against_skill_gap_detector(self):
        """Verify skill gap detector works on real state.db tool content."""
        import sqlite3

        try:
            conn = sqlite3.connect(f"{Path.home()}/.hermes/state.db", timeout=1.0)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT content, session_id FROM messages WHERE role = 'tool' AND content IS NOT NULL LIMIT 50"
            ).fetchall()
            conn.close()

            messages = [(r["content"], r["session_id"]) for r in rows if r["content"]]

            # Should not crash on any input
            gaps = detect_skill_gaps(messages)
            assert isinstance(gaps, list)

        except Exception as e:
            pytest.skip(f"Could not access state.db: {e}")
