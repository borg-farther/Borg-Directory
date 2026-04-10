"""Borg DeFi V2 — Tests for pack_store."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from borg.defi.v2.pack_store import PackStore
from borg.defi.v2.models import (
    DeFiStrategyPack,
    EntryCriteria,
    ActionSpec,
    CollectiveStats,
    RiskAssessment,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def pack_store(temp_dir):
    """Create a PackStore with temporary directory."""
    return PackStore(packs_dir=temp_dir)


@pytest.fixture
def sample_pack():
    """Create a sample pack for testing."""
    return DeFiStrategyPack(
        id="yield/aave-usdc-base",
        name="Aave V3 USDC Lending on Base",
        version=1,
        entry=EntryCriteria(
            tokens=["USDC", "USDT"],
            chains=["base"],
            min_amount_usd=100,
            risk_tolerance=["low", "medium"],
        ),
        action=ActionSpec(
            type="lend",
            protocol="aave-v3",
            steps=["Supply USDC to Aave V3", "Monitor health factor"],
        ),
        exit_guidance="No lock period. Withdraw whenever needed.",
        collective=CollectiveStats(
            total_outcomes=12,
            profitable=11,
            alpha=12,
            beta=2,
            avg_return_pct=4.2,
            median_return_pct=4.0,
            std_dev=1.2,
            min_return_pct=-0.3,
            max_return_pct=5.8,
            avg_duration_days=30.0,
            last_5_returns=[4.1, 3.8, 5.2, 4.5, 3.9],
            trend="stable",
        ),
        risk=RiskAssessment(
            il_risk=False,
            rug_score=0.0,
            protocol_age_days=890,
            audit_status="multiple audits, no critical findings",
        ),
        updated_at=datetime(2026, 3, 30, 12, 0, 0),
        created_at=datetime(2026, 2, 15, 0, 0, 0),
    )


@pytest.fixture
def sample_pack_2():
    """Create a second sample pack for testing."""
    return DeFiStrategyPack(
        id="yield/kamino-usdc-sol",
        name="Kamino CLMM USDC-SOL",
        version=2,
        entry=EntryCriteria(
            tokens=["USDC", "SOL"],
            chains=["solana"],
            min_amount_usd=50,
            risk_tolerance=["medium", "high"],
        ),
        action=ActionSpec(
            type="lp",
            protocol="kamino",
            steps=["Add liquidity to USDC-SOL pool"],
        ),
        exit_guidance="Pull liquidity when APY drops below 5%",
        collective=CollectiveStats(
            total_outcomes=8,
            profitable=6,
            alpha=7,
            beta=3,
            avg_return_pct=8.5,
            median_return_pct=7.8,
            std_dev=3.2,
            min_return_pct=-2.1,
            max_return_pct=15.2,
            avg_duration_days=45.0,
            last_5_returns=[10.2, 8.5, 7.2, 6.8, 9.1],
            trend="improving",
        ),
        risk=RiskAssessment(
            il_risk=True,
            rug_score=0.15,
            protocol_age_days=365,
            audit_status="single audit",
        ),
        updated_at=datetime(2026, 3, 29, 10, 0, 0),
        created_at=datetime(2026, 1, 15, 0, 0, 0),
    )


class TestPackStoreInit:
    """Tests for PackStore initialization."""

    def test_default_init(self, temp_dir):
        """Test that PackStore creates default directory."""
        store = PackStore()  # Uses default path
        # Just verify it doesn't crash and has the right attribute
        assert store.packs_dir.name == "packs"

    def test_custom_dir(self, temp_dir):
        """Test initialization with custom directory."""
        custom = temp_dir / "custom_packs"
        store = PackStore(packs_dir=custom)
        assert store.packs_dir == custom
        assert custom.exists()

    def test_dir_created_if_missing(self, temp_dir):
        """Test that directory is created if it doesn't exist."""
        new_dir = temp_dir / "nonexistent" / "packs"
        store = PackStore(packs_dir=new_dir)
        assert new_dir.exists()


class TestPackStoreSaveLoad:
    """Tests for saving and loading packs."""

    def test_save_pack(self, pack_store, sample_pack):
        """Test saving a pack."""
        pack_store.save_pack(sample_pack)
        assert pack_store.pack_exists(sample_pack.id)

    def test_load_pack(self, pack_store, sample_pack):
        """Test loading a saved pack."""
        pack_store.save_pack(sample_pack)
        loaded = pack_store.load_pack(sample_pack.id)
        
        assert loaded is not None
        assert loaded.id == sample_pack.id
        assert loaded.name == sample_pack.name
        assert loaded.version == sample_pack.version

    def test_load_nonexistent(self, pack_store):
        """Test loading a pack that doesn't exist."""
        result = pack_store.load_pack("nonexistent/pack")
        assert result is None

    def test_save_and_load_preserves_data(self, pack_store, sample_pack):
        """Test that save/load roundtrip preserves all data."""
        pack_store.save_pack(sample_pack)
        loaded = pack_store.load_pack(sample_pack.id)

        assert loaded.name == sample_pack.name
        assert loaded.entry.tokens == sample_pack.entry.tokens
        assert loaded.action.protocol == sample_pack.action.protocol
        assert loaded.collective.total_outcomes == sample_pack.collective.total_outcomes
        assert loaded.collective.alpha == sample_pack.collective.alpha
        assert loaded.risk.il_risk == sample_pack.risk.il_risk

    def test_multiple_packs(self, pack_store, sample_pack, sample_pack_2):
        """Test saving multiple packs."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        assert pack_store.pack_exists(sample_pack.id)
        assert pack_store.pack_exists(sample_pack_2.id)

        loaded1 = pack_store.load_pack(sample_pack.id)
        loaded2 = pack_store.load_pack(sample_pack_2.id)

        assert loaded1.name == sample_pack.name
        assert loaded2.name == sample_pack_2.name

    def test_update_pack(self, pack_store, sample_pack):
        """Test updating an existing pack."""
        pack_store.save_pack(sample_pack)
        
        sample_pack.version = 2
        sample_pack.collective.total_outcomes = 13
        pack_store.save_pack(sample_pack)

        loaded = pack_store.load_pack(sample_pack.id)
        assert loaded.version == 2
        assert loaded.collective.total_outcomes == 13

    def test_delete_pack(self, pack_store, sample_pack):
        """Test deleting a pack."""
        pack_store.save_pack(sample_pack)
        assert pack_store.pack_exists(sample_pack.id)

        result = pack_store.delete_pack(sample_pack.id)
        assert result is True
        assert not pack_store.pack_exists(sample_pack.id)

    def test_delete_nonexistent(self, pack_store):
        """Test deleting a pack that doesn't exist."""
        result = pack_store.delete_pack("nonexistent/id")
        assert result is False


class TestPackStoreList:
    """Tests for listing packs."""

    def test_list_packs_empty(self, pack_store):
        """Test listing when no packs exist."""
        packs = pack_store.list_packs()
        assert packs == []

    def test_list_packs_all(self, pack_store, sample_pack, sample_pack_2):
        """Test listing all packs."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        packs = pack_store.list_packs()
        assert len(packs) == 2

    def test_list_packs_filter_token(self, pack_store, sample_pack, sample_pack_2):
        """Test filtering packs by token."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        # USDC is in both, SOL only in sample_pack_2
        packs = pack_store.list_packs(token="USDC")
        assert len(packs) == 2

        packs = pack_store.list_packs(token="SOL")
        assert len(packs) == 1
        assert packs[0].id == sample_pack_2.id

    def test_list_packs_filter_chain(self, pack_store, sample_pack, sample_pack_2):
        """Test filtering packs by chain."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        packs = pack_store.list_packs(chain="base")
        assert len(packs) == 1
        assert packs[0].id == sample_pack.id

        packs = pack_store.list_packs(chain="solana")
        assert len(packs) == 1
        assert packs[0].id == sample_pack_2.id

    def test_list_packs_filter_risk(self, pack_store, sample_pack, sample_pack_2):
        """Test filtering packs by risk tolerance."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        # sample_pack has low, sample_pack_2 has medium/high
        packs = pack_store.list_packs(risk="low")
        assert len(packs) == 1
        assert packs[0].id == sample_pack.id

        packs = pack_store.list_packs(risk="high")
        assert len(packs) == 1
        assert packs[0].id == sample_pack_2.id

    def test_list_packs_combined_filters(self, pack_store, sample_pack, sample_pack_2):
        """Test filtering with multiple criteria."""
        pack_store.save_pack(sample_pack)
        pack_store.save_pack(sample_pack_2)

        # USDC on base
        packs = pack_store.list_packs(token="USDC", chain="base")
        assert len(packs) == 1

        # USDC on solana (should be 0 since sample_pack_2 is SOL, not USDC)
        packs = pack_store.list_packs(token="SOL", chain="solana", risk="high")
        assert len(packs) == 1


class TestPackStoreWarnings:
    """Tests for warning management."""

    def test_save_and_load_warning(self, pack_store):
        """Test saving and loading a warning."""
        warning = {
            "id": "warning/test-pack/20260330",
            "type": "collective_warning",
            "severity": "high",
            "pack_id": "test/pack",
            "reason": "Multiple losses detected",
            "evidence": {
                "total_outcomes": 10,
                "losses": 5,
            },
            "guidance": "Avoid this pack",
            "created_at": "2026-03-30T10:00:00",
            "expires_at": "2026-04-29T10:00:00",
        }

        pack_store.save_warning(warning)
        warnings = pack_store.load_warnings()

        assert len(warnings) == 1
        assert warnings[0]["id"] == warning["id"]
        assert warnings[0]["pack_id"] == "test/pack"

    def test_load_warnings_empty(self, pack_store):
        """Test loading when no warnings exist."""
        warnings = pack_store.load_warnings()
        assert warnings == []

    def test_multiple_warnings(self, pack_store):
        """Test saving multiple warnings."""
        for i in range(3):
            warning = {
                "id": f"warning/pack-{i}/20260330",
                "type": "collective_warning",
                "severity": "medium",
                "pack_id": f"pack-{i}",
                "reason": f"Warning {i}",
                "guidance": f"Guidance {i}",
                "created_at": "2026-03-30T10:00:00",
                "expires_at": "2026-04-29T10:00:00",
            }
            pack_store.save_warning(warning)

        warnings = pack_store.load_warnings()
        assert len(warnings) == 3


class TestPackStoreEdgeCases:
    """Tests for edge cases and error handling."""

    def test_pack_with_no_entry(self, pack_store):
        """Test saving a pack with no entry criteria."""
        pack = DeFiStrategyPack(
            id="simple/pack",
            name="Simple Pack",
            entry=None,
        )
        pack_store.save_pack(pack)
        loaded = pack_store.load_pack(pack.id)
        assert loaded.entry is None

    def test_pack_with_no_collective(self, pack_store):
        """Test saving a pack with no collective stats."""
        pack = DeFiStrategyPack(
            id="new/pack",
            name="New Pack",
            collective=None,
        )
        pack_store.save_pack(pack)
        loaded = pack_store.load_pack(pack.id)
        assert loaded.collective is None

    def test_pack_path_generation(self, pack_store):
        """Test that pack paths are generated correctly."""
        path = pack_store._pack_path("yield/aave-usdc-base")
        assert "yield" in str(path)
        assert "aave-usdc-base.yaml" in str(path)

        path = pack_store._pack_path("simple-pack")
        assert path.name == "simple-pack.yaml"

    def test_subdirectory_creation(self, pack_store, sample_pack):
        """Test that subdirectories are created for nested pack IDs."""
        pack_store.save_pack(sample_pack)
        path = pack_store._pack_path(sample_pack.id)
        assert path.parent.exists()
