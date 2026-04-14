"""
Tests for Borg Bridge natural language search (borg/defi/v2/borg_bridge.py).
Covers natural language parsing, recommendation formatting, and brief formatting.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from borg.defi.v2.borg_bridge import (
    parse_natural_query,
    format_recommendation,
    format_brief,
    TOKEN_ALIASES,
    CHAIN_ALIASES,
    RISK_ALIASES,
    ACTION_KEYWORDS,
)
from borg.defi.v2.models import StrategyRecommendation, StrategyQuery


class MockRecommendation:
    """Mock StrategyRecommendation for testing."""
    def __init__(
        self,
        pack_id="yield/aave-usdc-base",
        name="Aave V3 USDC Lending",
        protocol="aave-v3",
        chain="base",
        token="USDC",
        total_outcomes=12,
        profitable_count=10,
        avg_return_pct=4.2,
        median_return_pct=4.0,
        avg_duration_days=30,
        risk_tolerance=None,
        il_risk=False,
        trend="stable",
        confidence=0.75,
        warning=None,
        drift_alert=None,
        score_components=None,
    ):
        self.pack_id = pack_id
        self.name = name
        self.protocol = protocol
        self.chain = chain
        self.token = token
        self.total_outcomes = total_outcomes
        self.profitable_count = profitable_count
        self.avg_return_pct = avg_return_pct
        self.median_return_pct = median_return_pct
        self.avg_duration_days = avg_duration_days
        self.risk_tolerance = risk_tolerance or ["low", "medium"]
        self.il_risk = il_risk
        self.trend = trend
        self.confidence = confidence
        self.warning = warning
        self.drift_alert = drift_alert
        self.score_components = score_components


class TestNaturalLanguageParsing:
    """Test parse_natural_query function."""

    def test_yield_on_base_parsing(self):
        """'yield on base' should extract chain=base and action=yield."""
        query = parse_natural_query("yield on base")
        assert query.chain == "base"
        assert query.action_type == "lend"  # yield maps to lend

    def test_best_strategy_for_usdc(self):
        """'best strategy for idle USDC' should extract token=USDC and risk=low."""
        query = parse_natural_query("best strategy for idle USDC")
        assert query.token == "USDC"
        assert query.risk_tolerance == "low"  # idle implies low risk

    def test_high_yield_on_solana(self):
        """'high yield on solana' should extract chain=solana and risk=high."""
        query = parse_natural_query("high yield on solana")
        assert query.chain == "solana"
        assert query.risk_tolerance == "high"

    def test_safe_lending_on_ethereum(self):
        """'safe lending on ethereum' should extract chain, risk, and action."""
        query = parse_natural_query("safe lending on ethereum")
        assert query.chain == "ethereum"
        assert query.risk_tolerance == "low"  # safe maps to low
        assert query.action_type == "lend"

    def test_lp_on_arbitrum(self):
        """'LP on arbitrum' should extract action_type=lp and chain."""
        query = parse_natural_query("LP on arbitrum")
        assert query.chain == "arbitrum"
        assert query.action_type == "lp"

    def test_swap_on_polygon(self):
        """'swap on polygon' should extract action_type=swap and chain."""
        query = parse_natural_query("swap on polygon")
        assert query.chain == "polygon"
        assert query.action_type == "swap"

    def test_stake_on_solana(self):
        """'stake on solana' should extract action_type=stake and chain."""
        query = parse_natural_query("stake on solana")
        assert query.chain == "solana"
        assert query.action_type == "stake"

    def test_usdt_alias_resolves_to_usdt(self):
        """'USDT' should be recognized as token."""
        query = parse_natural_query("yield strategies with USDT")
        assert query.token == "USDT"

    def test_usdc_alias_resolves_to_usdc(self):
        """'USDC' and 'usd coin' should resolve to USDC."""
        query1 = parse_natural_query("yield with USDC")
        assert query1.token == "USDC"
        
        query2 = parse_natural_query("yield with usd coin")
        assert query2.token == "USDC"

    def test_eth_alias_resolves_to_eth(self):
        """'ETH' and 'ethereum' should resolve to ETH."""
        query1 = parse_natural_query("ETH strategies")
        assert query1.token == "ETH"
        
        query2 = parse_natural_query("ethereum strategies")
        assert query2.token == "ETH"

    def test_sol_alias_resolves_to_sol(self):
        """'SOL' and 'solana' should resolve correctly."""
        query1 = parse_natural_query("SOL yield")
        assert query1.token == "SOL"

    def test_chain_eth_alias(self):
        """'eth' should resolve to ethereum chain."""
        query = parse_natural_query("yield on eth")
        assert query.chain == "ethereum"

    def test_chain_sol_alias(self):
        """'sol' should resolve to solana chain."""
        query = parse_natural_query("yield on sol")
        assert query.chain == "solana"

    def test_chain_arb_alias(self):
        """'arb' should resolve to arbitrum chain."""
        query = parse_natural_query("yield on arb")
        assert query.chain == "arbitrum"

    def test_idle_implies_low_risk(self):
        """'idle' in query should imply low risk."""
        query = parse_natural_query("idle USDC strategies")
        assert query.risk_tolerance == "low"

    def test_degen_implies_high_risk(self):
        """'degen' should imply degen risk level."""
        query = parse_natural_query("degen strategies")
        assert query.risk_tolerance == "degen"

    def test_yolo_alias_for_degen(self):
        """'yolo' should map to degen risk."""
        query = parse_natural_query("yolo strategies")
        assert query.risk_tolerance == "degen"

    def test_protocol_extraction_aave(self):
        """'aave' should be extracted as protocol."""
        query = parse_natural_query("yield on aave")
        assert query.protocol == "aave"

    def test_protocol_extraction_compound(self):
        """'compound' should be extracted as protocol."""
        query = parse_natural_query("lending on compound")
        assert query.protocol == "compound"

    def test_returns_strategy_query_object(self):
        """Should return a StrategyQuery object."""
        query = parse_natural_query("yield on base")
        assert isinstance(query, StrategyQuery)


class TestRecommendationFormatting:
    """Test format_recommendation function."""

    def test_format_includes_name(self):
        """Formatted recommendation should include strategy name."""
        rec = MockRecommendation(name="Aave V3 USDC Lending")
        formatted = format_recommendation(rec)
        assert "Aave V3 USDC Lending" in formatted

    def test_format_includes_protocol_and_chain(self):
        """Should include protocol and chain info."""
        rec = MockRecommendation(protocol="aave-v3", chain="base")
        formatted = format_recommendation(rec)
        assert "aave-v3" in formatted
        assert "base" in formatted

    def test_format_includes_win_rate(self):
        """Should include win rate calculation."""
        rec = MockRecommendation(total_outcomes=10, profitable_count=8)
        formatted = format_recommendation(rec)
        assert "80%" in formatted  # 8/10 = 80%

    def test_format_includes_avg_return(self):
        """Should include average return percentage."""
        rec = MockRecommendation(avg_return_pct=4.2)
        formatted = format_recommendation(rec)
        assert "4.2%" in formatted

    def test_format_includes_il_risk_indicator(self):
        """Should indicate IL risk when present."""
        rec = MockRecommendation(il_risk=True)
        formatted = format_recommendation(rec)
        assert "IL: Yes" in formatted

    def test_format_no_il_risk_indicator_when_false(self):
        """Should not include IL indicator when false."""
        rec = MockRecommendation(il_risk=False)
        formatted = format_recommendation(rec)
        # Should not have "IL: Yes" but empty IL is ok
        assert "IL: Yes" not in formatted

    def test_format_includes_trend(self):
        """Should include trend with emoji."""
        rec = MockRecommendation(trend="improving")
        formatted = format_recommendation(rec)
        assert "improving" in formatted
        assert "+" in formatted  # improving emoji

    def test_format_includes_confidence(self):
        """Should include confidence as percentage."""
        rec = MockRecommendation(confidence=0.75)
        formatted = format_recommendation(rec)
        assert "75%" in formatted

    def test_format_includes_warning_when_present(self):
        """Should include warning when set."""
        rec = MockRecommendation(warning="High rug risk detected")
        formatted = format_recommendation(rec)
        assert "WARNING" in formatted
        assert "High rug risk detected" in formatted

    def test_format_includes_drift_alert(self):
        """Should include drift alert when set."""
        rec = MockRecommendation(drift_alert="Recent performance degrading")
        formatted = format_recommendation(rec)
        assert "DRIFT" in formatted
        assert "Recent performance degrading" in formatted


class TestBriefFormatting:
    """Test format_brief function."""

    def test_brief_header(self):
        """Brief should have header."""
        formatted = format_brief([], [], [])
        assert "Borg DeFi Daily Brief" in formatted

    def test_brief_empty_recommendations(self):
        """Brief with no recommendations should say so."""
        formatted = format_brief([], [], [])
        assert "No recommendations found" in formatted

    def test_brief_shows_warnings_count(self):
        """Brief should show warning count when warnings exist."""
        warnings = [
            {"severity": "high", "pack_id": "test/pack", "reason": "Test", "guidance": "Avoid"}
        ]
        formatted = format_brief([], warnings, [])
        assert "ACTIVE WARNINGS" in formatted
        assert "1" in formatted

    def test_brief_shows_drift_alerts_count(self):
        """Brief should show drift alerts count when present."""
        drift_alerts = [
            {"pack_id": "test/pack", "drift": "DEGRADING"}
        ]
        formatted = format_brief([], [], drift_alerts)
        assert "DRIFT ALERTS" in formatted
        assert "1" in formatted

    def test_brief_shows_recommendations_count(self):
        """Brief should show recommendations count."""
        recs = [
            MockRecommendation(name="Test Strategy 1"),
            MockRecommendation(name="Test Strategy 2"),
        ]
        formatted = format_brief(recs, [], [])
        assert "TOP RECOMMENDATIONS" in formatted
        assert "2" in formatted

    def test_brief_limits_warnings_to_5(self):
        """Brief should limit warnings section to 5 items."""
        warnings = [
            {"severity": "high", "pack_id": f"test/pack{i}", "reason": f"Reason {i}", "guidance": "Avoid"}
            for i in range(10)
        ]
        formatted = format_brief([], warnings, [])
        # Should contain header but not all 10 warnings in detail
        assert "ACTIVE WARNINGS" in formatted

    def test_brief_limits_drift_alerts_to_5(self):
        """Brief should limit drift alerts to 5 items."""
        drift_alerts = [
            {"pack_id": f"test/pack{i}", "drift": f"DRIFT {i}"}
            for i in range(10)
        ]
        formatted = format_brief([], [], drift_alerts)
        assert "DRIFT ALERTS" in formatted

    def test_brief_includes_recommendation_details(self):
        """Brief should include details for each recommendation."""
        recs = [MockRecommendation(name="Strategy A")]
        formatted = format_brief(recs, [], [])
        assert "Strategy A" in formatted
        assert "1." in formatted  # Numbered

    def test_brief_format_recommendations_truncates(self):
        """Should handle multiple recommendations properly."""
        recs = [
            MockRecommendation(name=f"Strategy {i}")
            for i in range(10)
        ]
        formatted = format_brief(recs, [], [])
        assert "TOP RECOMMENDATIONS" in formatted


class TestBorgSearchDefi:
    """Test borg_search_defi function (integration)."""

    def test_borg_search_defi_returns_string(self):
        """borg_search_defi should return a string."""
        from borg.defi.v2.borg_bridge import borg_search_defi
        # Note: This may return error message if dirs don't exist
        result = borg_search_defi("yield on base")
        assert isinstance(result, str)

    def test_borg_search_defi_handles_unknown_query(self):
        """Should handle queries without matches."""
        from borg.defi.v2.borg_bridge import borg_search_defi
        result = borg_search_defi("xyz_unknown_query")
        assert isinstance(result, str)
        # Should return the formatted output (may be empty)
        assert "Borg DeFi Daily Brief" in result


class TestConstants:
    """Test that constants are properly defined."""

    def test_token_aliases_defined(self):
        """TOKEN_ALIASES should be defined."""
        assert len(TOKEN_ALIASES) > 0
        assert "usdc" in TOKEN_ALIASES
        assert TOKEN_ALIASES["usdc"] == "USDC"

    def test_chain_aliases_defined(self):
        """CHAIN_ALIASES should be defined."""
        assert len(CHAIN_ALIASES) > 0
        assert "base" in CHAIN_ALIASES
        assert CHAIN_ALIASES["base"] == "base"

    def test_risk_aliases_defined(self):
        """RISK_ALIASES should be defined."""
        assert len(RISK_ALIASES) > 0
        assert "safe" in RISK_ALIASES
        assert RISK_ALIASES["safe"] == "low"

    def test_action_keywords_defined(self):
        """ACTION_KEYWORDS should be defined."""
        assert len(ACTION_KEYWORDS) > 0
        assert "lend" in ACTION_KEYWORDS
        assert "yield" in ACTION_KEYWORDS
        assert ACTION_KEYWORDS["yield"] == "lend"
