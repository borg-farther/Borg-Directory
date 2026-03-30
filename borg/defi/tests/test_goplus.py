"""
Tests for GoPlus Security API client.

Run with:
    pytest borg/defi/tests/test_goplus.py -v --tb=short
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.api_clients.goplus import GoPlusClient


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name, "r") as f:
        return json.load(f)


@pytest.fixture
def goplus_token_security_fixture():
    """Load GoPlus token security fixture."""
    return load_fixture("goplus_token_security.json")


@pytest.fixture
def goplus_address_security_fixture():
    """Load GoPlus address security fixture."""
    return load_fixture("goplus_address_security.json")


@pytest.fixture
def goplus_approval_fixture():
    """Load GoPlus approval security fixture."""
    return load_fixture("goplus_approval_security.json")


@pytest.fixture
def goplus_nft_fixture():
    """Load GoPlus NFT security fixture."""
    return load_fixture("goplus_nft_security.json")


@pytest.fixture
def goplus_honeypot_fixture():
    """Load GoPlus honeypot token fixture."""
    return load_fixture("goplus_honeypot.json")


# ---------------------------------------------------------------------
# GoPlus Client Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_goplus_token_security_schema(goplus_token_security_fixture):
    """Test that GoPlus token security is correctly parsed."""
    client = GoPlusClient()

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"result": goplus_token_security_fixture}

        result = await client.token_security("eth", "0x1234567890123456789012345678901234567890")

        assert result is not None
        assert "is_honeypot" in result
        assert "token_symbol" in result
        assert "total_supply" in result

        print(f"✓ GoPlus token security schema test passed")


@pytest.mark.asyncio
async def test_goplus_address_security(goplus_address_security_fixture):
    """Test GoPlus address security check."""
    client = GoPlusClient()

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"result": goplus_address_security_fixture}

        result = await client.address_security("bsc", "0xABCDEF1234567890ABCDEF1234567890ABCDEF12")

        assert result is not None
        assert "is_malicious" in result or "result" in str(result)

        print(f"✓ GoPlus address security test passed")


@pytest.mark.asyncio
async def test_goplus_approval_security(goplus_approval_fixture):
    """Test GoPlus approval security check."""
    client = GoPlusClient()

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"result": goplus_approval_fixture}

        result = await client.approval_security("polygon", "0x9876543210987654321098765432109876543210")

        assert result is not None

        print(f"✓ GoPlus approval security test passed")


@pytest.mark.asyncio
async def test_goplus_nft_security(goplus_nft_fixture):
    """Test GoPlus NFT security check."""
    client = GoPlusClient()

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"result": goplus_nft_fixture}

        result = await client.nft_security("eth", "0xABC123DEF456ABC123DEF456ABC123DEF456ABC")

        assert result is not None

        print(f"✓ GoPlus NFT security test passed")


@pytest.mark.asyncio
async def test_goplus_multiple_token_security():
    """Test GoPlus multiple token security check."""
    client = GoPlusClient()

    mock_result = {
        "0x1234567890123456789012345678901234567890": {
            "is_honeypot": "false",
            "token_symbol": "TEST",
        },
        "0x0987654321098765432109876543210987654321": {
            "is_honeypot": "false",
            "token_symbol": "ANOTHER",
        },
    }

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"result": mock_result}

        result = await client.multiple_token_security(
            "eth",
            [
                "0x1234567890123456789012345678901234567890",
                "0x0987654321098765432109876543210987654321",
            ],
        )

        assert result is not None
        assert len(result) == 2

        print(f"✓ GoPlus multiple token security test passed")


@pytest.mark.asyncio
async def test_goplus_chain_id_mapping():
    """Test chain name to ID conversion."""
    client = GoPlusClient()

    assert client._get_chain_id("eth") == "1"
    assert client._get_chain_id("ethereum") == "1"
    assert client._get_chain_id("1") == "1"
    assert client._get_chain_id("bsc") == "56"
    assert client._get_chain_id("bnb") == "56"
    assert client._get_chain_id("polygon") == "137"
    assert client._get_chain_id("matic") == "137"
    assert client._get_chain_id("arb") == "42161"
    assert client._get_chain_id("arbitrum") == "42161"
    assert client._get_chain_id("opt") == "10"
    assert client._get_chain_id("optimism") == "10"
    assert client._get_chain_id("base") == "8453"

    print(f"✓ GoPlus chain ID mapping test passed")


# ---------------------------------------------------------------------
# Helper Method Tests
# ---------------------------------------------------------------------


def test_is_honeypot_false():
    """Test is_honeypot returns False for safe token."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "can_sell": "true",
        "trading_honeypot": "",
    }

    assert client.is_honeypot(result) is False


def test_is_honeypot_true():
    """Test is_honeypot returns True for honeypot token."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "true",
        "can_sell": "false",
        "trading_honeypot": "honeypot",
    }

    assert client.is_honeypot(result) is True


def test_is_honeypot_cannot_sell():
    """Test is_honeypot returns True if cannot sell."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "can_sell": "false",
    }

    assert client.is_honeypot(result) is True


def test_is_honeypot_empty():
    """Test is_honeypot returns False for empty result."""
    client = GoPlusClient()

    assert client.is_honeypot({}) is False
    assert client.is_honeypot(None) is False


def test_risk_score_safe_token():
    """Test risk_score returns low score for safe token."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "false",
        "is_mintable": "false",
        "sell_tax": "1",
        "transfer_tax": "0",
        "owner_address_balance_percent": "5",
        "lp_total_percent": "80",
    }

    score = client.risk_score(result)
    assert score < 30
    print(f"✓ Safe token risk score: {score}")


def test_risk_score_honeypot():
    """Test risk_score returns 100 for honeypot."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "true",
    }

    assert client.risk_score(result) == 100.0


def test_risk_score_proxy():
    """Test risk_score adds points for proxy contract."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "true",
        "is_mintable": "false",
        "sell_tax": "0",
        "transfer_tax": "0",
        "owner_address_balance_percent": "5",
        "lp_total_percent": "80",
    }

    score = client.risk_score(result)
    assert 20 <= score <= 30


def test_risk_score_high_tax():
    """Test risk_score adds points for high tax."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "false",
        "is_mintable": "false",
        "sell_tax": "20",
        "transfer_tax": "10",
        "owner_address_balance_percent": "5",
        "lp_total_percent": "80",
    }

    score = client.risk_score(result)
    # 20% sell tax * 2 = 40, 10% transfer tax * 2 = 20, capped at 50 for taxes
    assert score >= 40


def test_risk_score_high_owner():
    """Test risk_score adds points for high owner holdings."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "false",
        "is_mintable": "false",
        "sell_tax": "0",
        "transfer_tax": "0",
        "owner_address_balance_percent": "60",
        "lp_total_percent": "80",
    }

    score = client.risk_score(result)
    assert score >= 20


def test_risk_score_low_lp():
    """Test risk_score adds points for low LP lock."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "false",
        "is_mintable": "false",
        "sell_tax": "0",
        "transfer_tax": "0",
        "owner_address_balance_percent": "5",
        "lp_total_percent": "5",
    }

    score = client.risk_score(result)
    assert score >= 25


def test_risk_score_empty():
    """Test risk_score returns 100 for empty result (unknown = high risk)."""
    client = GoPlusClient()

    assert client.risk_score({}) == 100.0
    assert client.risk_score(None) == 100.0


def test_get_warnings():
    """Test get_warnings returns list of warnings."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "false",
        "is_proxy": "true",
        "is_mintable": "true",
        "sell_tax": "15",
        "transfer_tax": "0",
        "owner_address_balance_percent": "55",
        "lp_total_percent": "5",
    }

    warnings = client.get_warnings(result)

    assert len(warnings) >= 4
    assert any("proxy" in w.lower() for w in warnings)
    assert any("mintable" in w.lower() for w in warnings)
    assert any("sell tax" in w.lower() for w in warnings)
    assert any("owner" in w.lower() for w in warnings)
    assert any("LP" in w or "lp" in w.lower() for w in warnings)

    print(f"✓ Warnings: {warnings}")


def test_get_warnings_honeypot():
    """Test get_warnings includes honeypot warning."""
    client = GoPlusClient()

    result = {
        "is_honeypot": "true",
    }

    warnings = client.get_warnings(result)
    assert any("honeypot" in w.lower() for w in warnings)


def test_get_warnings_empty():
    """Test get_warnings returns error message for empty result."""
    client = GoPlusClient()

    warnings = client.get_warnings({})
    assert len(warnings) == 1
    assert "unable" in warnings[0].lower() or "data" in warnings[0].lower()


# ---------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_goplus_token_security_error():
    """Test GoPlus token security handles errors gracefully."""
    client = GoPlusClient()

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Network error")

        result = await client.token_security("eth", "0x1234567890123456789012345678901234567890")

        assert result is None

        print(f"✓ GoPlus token security error handling test passed")


@pytest.mark.asyncio
async def test_goplus_no_auth_required():
    """Test GoPlus works without API key (no auth required)."""
    client = GoPlusClient()

    # Should initialize without warning
    assert client._api_key is None
    assert client._base_url == "https://api.gopluslabs.com/api/v1"

    print(f"✓ GoPlus no auth required test passed")


# ---------------------------------------------------------------------
# Integration Tests (require network)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires network access to GoPlus API")
async def test_goplus_token_security_real():
    """Integration test: GoPlus real API call for USDC."""
    client = GoPlusClient()

    # USDC on Ethereum
    result = await client.token_security(
        "eth",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    )

    assert result is not None
    assert result.get("is_honeypot", "").lower() == "false"

    print(f"✓ GoPlus real API test passed: USDC is safe")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_goplus_chain_mapping_integration():
    """Integration test: Verify chain mapping works with real API."""
    client = GoPlusClient()

    # Test various chain formats
    chains = ["eth", "ethereum", "bsc", "polygon", "arbitrum", "base"]

    for chain in chains:
        chain_id = client._get_chain_id(chain)
        assert chain_id.isdigit(), f"Chain {chain} should map to numeric ID"
        print(f"  {chain} -> {chain_id}")

    print(f"✓ GoPlus chain mapping integration test passed")
