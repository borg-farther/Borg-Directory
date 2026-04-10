"""
Tests for seed pack creation (borg/defi/v2/seed_packs.py).
Covers seed pack creation, collective data, and PackStore integration.
"""

import pytest
from pathlib import Path
import sys
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from borg.defi.v2.seed_packs import create_seed_packs, verify_seed_packs
from borg.defi.v2.pack_store import PackStore


class TestSeedPackCreation:
    """Test seed pack creation."""

    def test_create_seed_packs_returns_5_packs(self, tmp_path):
        """create_seed_packs should create exactly 5 packs."""
        packs = create_seed_packs(tmp_path)
        assert len(packs) == 5

    def test_seed_packs_have_expected_ids(self, tmp_path):
        """Created packs should have the expected IDs."""
        packs = create_seed_packs(tmp_path)
        pack_ids = [p.id for p in packs]
        
        expected_ids = [
            "yield/aave-usdc-base",
            "yield/aave-usdc-ethereum",
            "yield/compound-usdc-ethereum",
            "yield/kamino-usdc-sol",
            "yield/marinade-sol",
        ]
        
        for expected_id in expected_ids:
            assert expected_id in pack_ids, f"Missing pack: {expected_id}"

    def test_seed_packs_saved_to_disk(self, tmp_path):
        """Created packs should be saved to disk."""
        packs = create_seed_packs(tmp_path)
        
        # Check that pack files exist
        for pack in packs:
            # Convert pack_id to path
            parts = pack.id.split("/")
            filename = parts[-1] + ".yaml"
            subdir = "/".join(parts[:-1]) if len(parts) > 1 else ""
            
            if subdir:
                pack_file = tmp_path / subdir / filename
            else:
                pack_file = tmp_path / filename
            
            assert pack_file.exists(), f"Pack file not found: {pack_file}"

    def test_seed_pack_has_name(self, tmp_path):
        """Each seed pack should have a name."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.name is not None
            assert len(pack.name) > 0

    def test_seed_pack_has_tokens_via_entry(self, tmp_path):
        """Each seed pack should have tokens via entry."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.entry is not None
            assert pack.entry.tokens is not None
            assert len(pack.entry.tokens) > 0

    def test_seed_pack_has_chains_via_entry(self, tmp_path):
        """Each seed pack should have chains via entry."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.entry is not None
            assert pack.entry.chains is not None
            assert len(pack.entry.chains) > 0


class TestSeedPackCollectiveData:
    """Test that seed packs have proper collective statistics."""

    def test_seed_packs_have_outcomes(self, tmp_path):
        """Seed packs should have total_outcomes > 0."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.total_outcomes > 0, f"Pack {pack.id} has no outcomes"

    def test_seed_packs_have_alpha_beta(self, tmp_path):
        """Seed packs should have alpha and beta for Bayesian reputation."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.alpha > 0
            assert pack.collective.beta > 0

    def test_seed_packs_have_reputation(self, tmp_path):
        """Seed packs should have a valid reputation (0-1)."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert 0.0 <= pack.collective.reputation <= 1.0

    def test_seed_packs_have_avg_return(self, tmp_path):
        """Seed packs should have average return percentage."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.avg_return_pct is not None

    def test_seed_packs_have_std_dev(self, tmp_path):
        """Seed packs should have standard deviation."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.std_dev is not None
            assert pack.collective.std_dev >= 0.0

    def test_seed_packs_have_last_5_returns(self, tmp_path):
        """Seed packs should have last 5 returns recorded."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert len(pack.collective.last_5_returns) == 5

    def test_seed_packs_have_trend(self, tmp_path):
        """Seed packs should have a trend (improving/stable/degrading)."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.trend in ["improving", "stable", "degrading"]

    def test_seed_packs_have_profitable_count(self, tmp_path):
        """Seed packs should have profitable count."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.collective is not None
            assert pack.collective.profitable >= 0
            assert pack.collective.profitable <= pack.collective.total_outcomes

    def test_seed_packs_reputation_matches_alpha_beta_calculation(self, tmp_path):
        """Reputation should equal alpha / (alpha + beta)."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            expected_rep = pack.collective.alpha / (pack.collective.alpha + pack.collective.beta)
            assert abs(pack.collective.reputation - expected_rep) < 0.01


class TestSeedPackLoadableByPackStore:
    """Test that seed packs can be loaded by PackStore."""

    def test_seed_packs_loadable(self, tmp_path):
        """Seed packs should be loadable via create/verify cycle."""
        create_seed_packs(tmp_path)
        
        store = PackStore(tmp_path)
        
        for pack_id in [
            "yield/aave-usdc-base",
            "yield/aave-usdc-ethereum",
            "yield/compound-usdc-ethereum",
            "yield/kamino-usdc-sol",
            "yield/marinade-sol",
        ]:
            pack = store.load_pack(pack_id)
            assert pack is not None, f"Failed to load {pack_id}"
            assert pack.id == pack_id

    def test_seed_packs_roundtrip_serialization(self, tmp_path):
        """Seed packs should survive round-trip serialization."""
        create_seed_packs(tmp_path)
        store = PackStore(tmp_path)
        
        for pack_id in [
            "yield/aave-usdc-base",
            "yield/aave-usdc-ethereum",
            "yield/compound-usdc-ethereum",
            "yield/kamino-usdc-sol",
            "yield/marinade-sol",
        ]:
            loaded = store.load_pack(pack_id)
            assert loaded is not None
            # Core stats should match
            assert loaded.id == pack_id
            assert loaded.name is not None


class TestVerifySeedPacks:
    """Test verify_seed_packs function."""

    def test_verify_returns_true_for_valid_packs(self, tmp_path):
        """verify_seed_packs should return True for properly created packs."""
        create_seed_packs(tmp_path)
        result = verify_seed_packs(tmp_path)
        assert result == True

    def test_verify_returns_false_for_missing_pack(self, tmp_path):
        """verify_seed_packs should return False when a pack is missing."""
        create_seed_packs(tmp_path)
        
        # Delete a pack file
        pack_file = tmp_path / "yield" / "aave-usdc-base.yaml"
        if pack_file.exists():
            pack_file.unlink()
        
        result = verify_seed_packs(tmp_path)
        assert result == False


class TestSeedPackRiskAssessment:
    """Test seed pack risk assessments."""

    def test_aave_base_has_low_rug_score(self, tmp_path):
        """Aave USDC on Base should have low rug score."""
        packs = create_seed_packs(tmp_path)
        aave_base = next(p for p in packs if p.id == "yield/aave-usdc-base")
        assert aave_base.risk is not None
        assert aave_base.risk.rug_score < 0.1

    def test_kamino_has_il_risk(self, tmp_path):
        """Kamino CLMM should have IL risk flag."""
        packs = create_seed_packs(tmp_path)
        kamino = next(p for p in packs if p.id == "yield/kamino-usdc-sol")
        assert kamino.risk is not None
        assert kamino.risk.il_risk == True

    def test_kamino_has_higher_std_dev(self, tmp_path):
        """Kamino should have higher std_dev (more volatile)."""
        packs = create_seed_packs(tmp_path)
        kamino = next(p for p in packs if p.id == "yield/kamino-usdc-sol")
        aave = next(p for p in packs if p.id == "yield/aave-usdc-base")
        assert kamino.collective.std_dev > aave.collective.std_dev

    def test_aave_has_no_il_risk(self, tmp_path):
        """Aave lending should not have IL risk."""
        packs = create_seed_packs(tmp_path)
        aave_base = next(p for p in packs if p.id == "yield/aave-usdc-base")
        assert aave_base.risk is not None
        assert aave_base.risk.il_risk == False


class TestSeedPackVersions:
    """Test seed pack version tracking."""

    def test_seed_packs_have_version(self, tmp_path):
        """Each seed pack should have a version number."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.version >= 1

    def test_seed_packs_created_with_reasonable_version(self, tmp_path):
        """Seed packs should be created with reasonable version numbers."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            # Versions should be >= 1 and reflect some history
            assert pack.version >= 1


class TestSeedPackActions:
    """Test seed pack action specifications."""

    def test_seed_packs_have_action_type(self, tmp_path):
        """Each seed pack should have an action type."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.action is not None
            assert pack.action.type in ["lend", "lp", "stake", "swap"]

    def test_seed_packs_have_protocol(self, tmp_path):
        """Each seed pack should have a protocol."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.action is not None
            assert pack.action.protocol is not None
            assert len(pack.action.protocol) > 0

    def test_seed_packs_have_exit_guidance(self, tmp_path):
        """Each seed pack should have exit guidance."""
        packs = create_seed_packs(tmp_path)
        for pack in packs:
            assert pack.exit_guidance is not None
            assert len(pack.exit_guidance) > 0
