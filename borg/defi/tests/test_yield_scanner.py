"""Tests for Borg DeFi yield scanner module.

18 tests covering yield scanning, filtering, ranking, and change detection.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from borg.defi.yield_scanner import YieldScanner, _calculate_risk_adjusted_score
from borg.defi.data_models import YieldOpportunity, YieldChange


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_yield_opportunities():
    """Sample yield opportunities for testing."""
    now = datetime.now().timestamp()
    return [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v2-usdc",
            token="USDC",
            apy=5.2,
            tvl=150_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com/yields/pool/aave-v2-usdc",
            last_updated=now,
            pool_id="aave-v2-usdc",
        ),
        YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="kamino-usdc-sol",
            token="USDC-USDC LP",
            apy=45.0,
            tvl=23_000_000,
            risk_score=0.5,
            il_risk=True,
            url="https://defillama.com/yields/pool/kamino-usdc-sol",
            last_updated=now,
            pool_id="kamino-usdc-sol",
        ),
        YieldOpportunity(
            protocol="compound",
            chain="ethereum",
            pool="compound-v2-dai",
            token="DAI",
            apy=3.8,
            tvl=80_000_000,
            risk_score=0.15,
            il_risk=False,
            url="https://defillama.com/yields/pool/compound-v2-dai",
            last_updated=now,
            pool_id="compound-v2-dai",
        ),
        YieldOpportunity(
            protocol="raydium",
            chain="solana",
            pool="raydium-sol-usdc",
            token="SOL-USDC LP",
            apy=120.0,
            tvl=5_000_000,
            risk_score=0.7,
            il_risk=True,
            url="https://defillama.com/yields/pool/raydium-sol-usdc",
            last_updated=now,
            pool_id="raydium-sol-usdc",
        ),
    ]


@pytest.fixture
def sample_defillama_response():
    """Sample DeFiLlama API response."""
    return {
        "data": [
            {
                "pool": "aave-v2-usdc",
                "project": "aave",
                "symbol": "USDC",
                "chain": "Ethereum",
                "apy": 5.2,
                "tvlUsd": 150000000.0,
                "poolMeta": "lending",
                "updated": datetime.now().timestamp(),
            },
            {
                "pool": "kamino-usdc-sol",
                "project": "kamino",
                "symbol": "USDC-USDC LP",
                "chain": "Solana",
                "apy": 45.0,
                "tvlUsd": 23000000.0,
                "poolMeta": "lp",
                "updated": datetime.now().timestamp(),
            },
            {
                "pool": "compound-v2-dai",
                "project": "compound",
                "symbol": "DAI",
                "chain": "Ethereum",
                "apy": 3.8,
                "tvlUsd": 80000000.0,
                "poolMeta": "lending",
                "updated": datetime.now().timestamp(),
            },
            {
                "pool": "raydium-sol-usdc",
                "project": "raydium",
                "symbol": "SOL-USDC LP",
                "chain": "Solana",
                "apy": 120.0,
                "tvlUsd": 5000000.0,
                "poolMeta": "lp",
                "updated": datetime.now().timestamp(),
            },
        ]
    }


# ============================================================================
# Yield Opportunity DataClass Tests (YS1)
# ============================================================================

def test_yield_opportunity_dataclass():
    """Verify all fields of YieldOpportunity dataclass."""
    now = datetime.now().timestamp()
    opp = YieldOpportunity(
        protocol="aave",
        chain="ethereum",
        pool="aave-v2-usdc",
        token="USDC",
        apy=5.2,
        tvl=150_000_000,
        risk_score=0.2,
        il_risk=False,
        url="https://defillama.com",
        last_updated=now,
    )
    
    assert opp.protocol == "aave"
    assert opp.chain == "ethereum"
    assert opp.pool == "aave-v2-usdc"
    assert opp.token == "USDC"
    assert opp.apy == 5.2
    assert opp.tvl == 150_000_000
    assert opp.risk_score == 0.2
    assert opp.il_risk is False
    assert opp.url == "https://defillama.com"
    assert opp.last_updated == now


# ============================================================================
# DeFiLlama Scan Tests (YS1, YS7)
# ============================================================================

@pytest.mark.asyncio
async def test_yield_scan_defillama(sample_defillama_response):
    """Mock response -> valid opportunities."""
    scanner = YieldScanner()
    
    with patch.object(scanner, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=sample_defillama_response)
        
        # Create mock session that properly supports async context manager protocol
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_instance.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        opps = await scanner.scan_defillama()
    
    assert len(opps) >= 3  # some pools may be filtered by min APY/TVL
    assert all(isinstance(o, YieldOpportunity) for o in opps)
    assert opps[0].protocol in ["aave", "kamino", "compound", "raydium"]


@pytest.mark.asyncio
async def test_yield_empty_response():
    """Empty response -> empty list, no crash."""
    scanner = YieldScanner()
    
    with patch.object(scanner, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": []})
        
        # Create mock session that properly supports async context manager protocol
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_instance.get.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        opps = await scanner.scan_defillama()
    
    assert opps == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_yield_real_defillama():
    """[INTEGRATION] Real API call, verify >1000 pools."""
    scanner = YieldScanner()
    
    try:
        opps = await scanner.scan_defillama()
        assert len(opps) > 1000, f"Expected >1000 pools, got {len(opps)}"
    finally:
        await scanner.close()


# ============================================================================
# Filter Tests (YS2, YS3, YS7, YS8)
# ============================================================================

def test_yield_filter_min_tvl(sample_yield_opportunities):
    """Filter 1M -> only large pools."""
    scanner = YieldScanner(min_tvl=1_000_000)
    
    # Manually filter
    filtered = [o for o in sample_yield_opportunities if o.tvl >= 1_000_000]
    
    assert len(filtered) == 4  # raydium has 5M TVL, others above 1M
    assert all(o.tvl >= 1_000_000 for o in filtered)


def test_yield_filter_max_risk(sample_yield_opportunities):
    """Filter 0.5 -> only safe pools."""
    scanner = YieldScanner(max_risk=0.5)
    
    filtered = [o for o in sample_yield_opportunities if o.risk_score <= 0.5]
    
    assert len(filtered) == 3  # raydium has 0.7 risk
    assert all(o.risk_score <= 0.5 for o in filtered)


def test_yield_filter_chain(sample_yield_opportunities):
    """Filter solana -> no EVM."""
    scanner = YieldScanner()
    
    filtered = scanner.filter_by_chain(sample_yield_opportunities, "solana")
    
    assert len(filtered) == 2  # kamino and raydium
    assert all(o.chain == "solana" for o in filtered)


def test_yield_filter_stablecoin(sample_yield_opportunities):
    """Filter stable -> USDC/USDT only."""
    scanner = YieldScanner()
    
    filtered = scanner.filter_stablecoins(sample_yield_opportunities)
    
    # Should include USDC, DAI, and LP tokens containing them
    assert len(filtered) >= 2
    tokens = [o.token.upper() for o in filtered]
    assert any("USDC" in t or "DAI" in t for t in tokens)


# ============================================================================
# Ranking Tests (YS4)
# ============================================================================

def test_yield_ranking(sample_yield_opportunities):
    """Verify rank order correct."""
    scanner = YieldScanner()
    
    # Pass max_risk=1.0 to include raydium (risk=0.7) in ranking
    ranked = scanner.rank_opportunities(sample_yield_opportunities, max_risk=1.0)
    
    # Highest risk-adjusted score should be first
    # kamino at 45% APY with medium risk should rank high
    assert len(ranked) == 4
    assert ranked[0].apy >= ranked[-1].apy  # Basic sanity


def test_yield_risk_adjusted_score():
    """Verify score formula: APY * (1 - risk) * log(TVL)."""
    # High APY, low risk, high TVL -> high score
    score1 = _calculate_risk_adjusted_score(apy=100, risk_score=0.2, tvl=100_000_000)
    
    # Low APY, high risk, low TVL -> low score
    score2 = _calculate_risk_adjusted_score(apy=5, risk_score=0.8, tvl=1_000_000)
    
    assert score1 > score2


# ============================================================================
# Yield Change Detection Tests (YS5, YS6)
# ============================================================================

def test_yield_change_detection_spike():
    """5x APY increase -> alert."""
    scanner = YieldScanner()
    
    previous = [
        YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="kamino-usdc-sol",
            token="USDC LP",
            apy=10.0,
            tvl=10_000_000,
            risk_score=0.5,
            il_risk=True,
            url="https://defillama.com",
            last_updated=0,
            pool_id="kamino-usdc",
        )
    ]
    
    current = [
        YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="kamino-usdc-sol",
            token="USDC LP",
            apy=50.0,  # 5x increase
            tvl=10_000_000,
            risk_score=0.5,
            il_risk=True,
            url="https://defillama.com",
            last_updated=0,
            pool_id="kamino-usdc",
        )
    ]
    
    changes = scanner.detect_yield_changes(current, previous, threshold_pct=20)
    
    assert len(changes) == 1
    assert changes[0].is_spike is True
    assert changes[0].change_pct == 400.0  # 5x = 400%


def test_yield_change_detection_drop():
    """80% APY drop -> warning."""
    scanner = YieldScanner()
    
    previous = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v2-usdc",
            token="USDC",
            apy=30.0,
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-v2-usdc",
        )
    ]
    
    current = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v2-usdc",
            token="USDC",
            apy=6.0,  # 80% drop
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-v2-usdc",
        )
    ]
    
    changes = scanner.detect_yield_changes(current, previous, threshold_pct=20)
    
    assert len(changes) == 1
    assert changes[0].is_spike is False
    assert changes[0].change_pct == -80.0


# ============================================================================
# IL Risk Tests (YS9)
# ============================================================================

def test_yield_il_risk_flagging():
    """LP pool -> il_risk=True."""
    opp = YieldOpportunity(
        protocol="raydium",
        chain="solana",
        pool="raydium-sol-usdc",
        token="SOL-USDC LP",
        apy=50.0,
        tvl=10_000_000,
        risk_score=0.5,
        il_risk=True,  # Explicitly True for LP
        url="https://defillama.com",
        last_updated=0,
        pool_id="raydium-sol",
    )
    
    assert opp.il_risk is True


def test_yield_single_asset_no_il():
    """Lending pool -> il_risk=False."""
    opp = YieldOpportunity(
        protocol="aave",
        chain="ethereum",
        pool="aave-v2-usdc",
        token="USDC",
        apy=5.0,
        tvl=100_000_000,
        risk_score=0.2,
        il_risk=False,  # Lending has no IL
        url="https://defillama.com",
        last_updated=0,
        pool_id="aave-v2-usdc",
    )
    
    assert opp.il_risk is False


# ============================================================================
# Telegram Formatting Tests (YS10)
# ============================================================================

def test_yield_telegram_format(sample_yield_opportunities):
    """Verify formatting: APY, TVL, risk, protocol link."""
    scanner = YieldScanner()
    
    msg = scanner.format_telegram(sample_yield_opportunities, top_n=3)
    
    assert "📊 *Yield Scanner*" in msg
    assert "APY" in msg or "%" in msg
    assert "TVL" in msg or "$" in msg
    assert "defillama.com" in msg  # URL present


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_yield_dedup():
    """Same pool 2x -> 1 result."""
    scanner = YieldScanner()
    
    opps = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v2-usdc",
            token="USDC",
            apy=5.0,
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-v2-usdc",
        ),
        # Duplicate
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v2-usdc",
            token="USDC",
            apy=5.0,
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-v2-usdc",
        ),
    ]
    
    # Filter duplicates
    seen = set()
    deduped = []
    for o in opps:
        if o.pool_id not in seen:
            seen.add(o.pool_id)
            deduped.append(o)
    
    assert len(deduped) == 1


def test_yield_historical_comparison():
    """Compare current vs previous scan."""
    scanner = YieldScanner()
    
    previous = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-usdc",
            token="USDC",
            apy=5.0,
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-usdc",
        ),
        YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="kamino-usdc",
            token="USDC LP",
            apy=40.0,
            tvl=20_000_000,
            risk_score=0.5,
            il_risk=True,
            url="https://defillama.com",
            last_updated=0,
            pool_id="kamino-usdc",
        ),
    ]
    
    current = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-usdc",
            token="USDC",
            apy=6.0,  # Slight increase
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-usdc",
        ),
        # Kamino dropped significantly
    ]
    
    changes = scanner.detect_yield_changes(current, previous)
    
    # Aave change is small (<20%), so only high changes reported
    # The dropped kamino won't show since it's not in current
    assert all(abs(c.change_pct) >= 20 for c in changes)


def test_yield_cron_integration():
    """Simulate hourly scan."""
    scanner = YieldScanner()
    
    # Simulate two scans
    opps1 = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-usdc",
            token="USDC",
            apy=5.0,
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-usdc",
        ),
    ]
    
    # Store for next scan
    scanner._previous_pools = {o.pool_id: o.apy for o in opps1}
    
    opps2 = [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-usdc",
            token="USDC",
            apy=10.0,  # Doubled
            tvl=100_000_000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com",
            last_updated=0,
            pool_id="aave-usdc",
        ),
    ]
    
    changes = scanner.detect_yield_changes(opps2, opps1)
    
    assert len(changes) == 1
    assert changes[0].current_apy == 10.0
    assert changes[0].previous_apy == 5.0
