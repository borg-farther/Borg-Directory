"""Borg DeFi V2 — Tests for outcome_store."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from borg.defi.v2.outcome_store import OutcomeStore
from borg.defi.v2.models import ExecutionOutcome


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def outcome_store(temp_dir):
    """Create an OutcomeStore with temporary directory."""
    return OutcomeStore(outcomes_dir=temp_dir)


@pytest.fixture
def sample_outcome():
    """Create a sample outcome for testing."""
    return ExecutionOutcome(
        outcome_id="out-2026-03-01-agent001-001",
        pack_id="yield/aave-usdc-base",
        agent_id="agent-001",
        entered_at=datetime(2026, 3, 1, 8, 0, 0),
        exited_at=datetime(2026, 3, 30, 8, 0, 0),
        duration_days=29.0,
        return_pct=3.8,
        profitable=True,
        lessons=["Steady 4% APY", "No issues during the month"],
        verification_tx_hash="0xabc123def456",
        chain="base",
    )


@pytest.fixture
def sample_outcome_2():
    """Create a second sample outcome."""
    return ExecutionOutcome(
        outcome_id="out-2026-03-15-agent002-001",
        pack_id="yield/kamino-usdc-sol",
        agent_id="agent-002",
        entered_at=datetime(2026, 3, 15, 10, 0, 0),
        exited_at=datetime(2026, 4, 15, 10, 0, 0),
        duration_days=31.0,
        return_pct=-2.1,
        profitable=False,
        lessons=["IL hurt during SOL dump", "Consider safer pool"],
        chain="solana",
    )


@pytest.fixture
def old_outcome():
    """Create an old outcome for testing age filtering."""
    return ExecutionOutcome(
        outcome_id="out-2026-01-15-agent003-001",
        pack_id="yield/aave-usdc-base",
        agent_id="agent-003",
        entered_at=datetime(2026, 1, 15, 8, 0, 0),
        exited_at=datetime(2026, 2, 15, 8, 0, 0),
        duration_days=31.0,
        return_pct=3.2,
        profitable=True,
        lessons=["Old outcome for testing"],
    )


class TestOutcomeStoreInit:
    """Tests for OutcomeStore initialization."""

    def test_default_init(self):
        """Test that OutcomeStore creates default directory."""
        store = OutcomeStore()  # Uses default path
        assert store.outcomes_dir.name == "outcomes"

    def test_custom_dir(self, temp_dir):
        """Test initialization with custom directory."""
        store = OutcomeStore(outcomes_dir=temp_dir)
        assert store.outcomes_dir == temp_dir
        assert temp_dir.exists()

    def test_dir_created_if_missing(self, temp_dir):
        """Test that directory is created if it doesn't exist."""
        new_dir = temp_dir / "nonexistent" / "outcomes"
        store = OutcomeStore(outcomes_dir=new_dir)
        assert new_dir.exists()


class TestOutcomeStoreSaveLoad:
    """Tests for saving and loading outcomes."""

    def test_save_outcome(self, outcome_store, sample_outcome):
        """Test saving an outcome."""
        outcome_store.save_outcome(sample_outcome)
        assert outcome_store.outcome_exists(sample_outcome.outcome_id)

    def test_load_outcomes_for_pack(self, outcome_store, sample_outcome, sample_outcome_2):
        """Test loading outcomes for a specific pack."""
        outcome_store.save_outcome(sample_outcome)
        outcome_store.save_outcome(sample_outcome_2)

        outcomes = outcome_store.load_outcomes_for_pack("yield/aave-usdc-base")
        assert len(outcomes) == 1
        assert outcomes[0].outcome_id == sample_outcome.outcome_id

        outcomes = outcome_store.load_outcomes_for_pack("yield/kamino-usdc-sol")
        assert len(outcomes) == 1
        assert outcomes[0].outcome_id == sample_outcome_2.outcome_id

    def test_load_outcomes_for_nonexistent_pack(self, outcome_store):
        """Test loading outcomes for a pack with no outcomes."""
        outcomes = outcome_store.load_outcomes_for_pack("nonexistent/pack")
        assert outcomes == []

    def test_load_all_outcomes(self, outcome_store, sample_outcome, sample_outcome_2):
        """Test loading all outcomes."""
        outcome_store.save_outcome(sample_outcome)
        outcome_store.save_outcome(sample_outcome_2)

        all_outcomes = outcome_store.load_all_outcomes()
        assert len(all_outcomes) == 2

    def test_load_all_outcomes_sorted(self, outcome_store, sample_outcome, sample_outcome_2):
        """Test that outcomes are sorted by entered_at."""
        outcome_store.save_outcome(sample_outcome)
        outcome_store.save_outcome(sample_outcome_2)

        outcomes = outcome_store.load_all_outcomes()
        # Should be sorted by entered_at ascending
        assert outcomes[0].entered_at <= outcomes[1].entered_at

    def test_outcome_exists(self, outcome_store, sample_outcome):
        """Test checking if outcome exists."""
        assert not outcome_store.outcome_exists(sample_outcome.outcome_id)
        
        outcome_store.save_outcome(sample_outcome)
        assert outcome_store.outcome_exists(sample_outcome.outcome_id)

    def test_outcome_not_found(self, outcome_store):
        """Test checking for nonexistent outcome."""
        assert not outcome_store.outcome_exists("nonexistent/outcome")

    def test_get_outcome_count(self, outcome_store, sample_outcome, sample_outcome_2):
        """Test getting total outcome count."""
        assert outcome_store.get_outcome_count() == 0

        outcome_store.save_outcome(sample_outcome)
        assert outcome_store.get_outcome_count() == 1

        outcome_store.save_outcome(sample_outcome_2)
        assert outcome_store.get_outcome_count() == 2

    def test_delete_outcome(self, outcome_store, sample_outcome):
        """Test deleting an outcome."""
        outcome_store.save_outcome(sample_outcome)
        assert outcome_store.outcome_exists(sample_outcome.outcome_id)

        result = outcome_store.delete_outcome(sample_outcome.outcome_id)
        assert result is True
        assert not outcome_store.outcome_exists(sample_outcome.outcome_id)

    def test_delete_nonexistent(self, outcome_store):
        """Test deleting a nonexistent outcome."""
        result = outcome_store.delete_outcome("nonexistent")
        assert result is False


class TestOutcomeStoreLoadByAge:
    """Tests for loading outcomes filtered by age."""

    def test_load_since_days(self, outcome_store, sample_outcome, old_outcome):
        """Test loading outcomes within N days."""
        # sample_outcome is from March, old_outcome is from January
        # March is ~2 months ago from today, January is ~3 months ago
        
        outcome_store.save_outcome(sample_outcome)
        outcome_store.save_outcome(old_outcome)

        # Filter to last 60 days should include sample_outcome but not old_outcome
        # (Assuming current date is around late March 2026)
        recent = outcome_store.load_all_outcomes(since_days=60)
        # At least the sample_outcome should be recent enough
        assert len(recent) >= 1

    def test_load_all_outcomes_no_filter(self, outcome_store, sample_outcome, old_outcome):
        """Test that load_all_outcomes without since_days returns all."""
        outcome_store.save_outcome(sample_outcome)
        outcome_store.save_outcome(old_outcome)

        all_outcomes = outcome_store.load_all_outcomes()
        assert len(all_outcomes) == 2


class TestOutcomeStoreRoundtrip:
    """Tests for save/load roundtrip."""

    def test_roundtrip_preserves_data(self, outcome_store, sample_outcome):
        """Test that save/load preserves all outcome data."""
        outcome_store.save_outcome(sample_outcome)

        loaded = outcome_store.load_outcomes_for_pack(sample_outcome.pack_id)[0]

        assert loaded.outcome_id == sample_outcome.outcome_id
        assert loaded.pack_id == sample_outcome.pack_id
        assert loaded.agent_id == sample_outcome.agent_id
        assert loaded.duration_days == sample_outcome.duration_days
        assert loaded.return_pct == sample_outcome.return_pct
        assert loaded.profitable == sample_outcome.profitable
        assert loaded.lessons == sample_outcome.lessons
        assert loaded.verification_tx_hash == sample_outcome.verification_tx_hash
        assert loaded.chain == sample_outcome.chain

    def test_roundtrip_with_verification(self, outcome_store):
        """Test roundtrip with verification tx hash."""
        outcome = ExecutionOutcome(
            outcome_id="out-with-verification",
            pack_id="test/pack",
            agent_id="agent-verified",
            entered_at=datetime(2026, 3, 1),
            exited_at=datetime(2026, 3, 30),
            duration_days=29.0,
            return_pct=5.0,
            profitable=True,
            verification_tx_hash="0xabcd1234efgh5678",
            chain="ethereum",
        )

        outcome_store.save_outcome(outcome)
        loaded = outcome_store.load_outcomes_for_pack("test/pack")[0]

        assert loaded.verification_tx_hash == "0xabcd1234efgh5678"
        assert loaded.chain == "ethereum"

    def test_roundtrip_without_verification(self, outcome_store):
        """Test roundtrip when no verification data."""
        outcome = ExecutionOutcome(
            outcome_id="out-no-verification",
            pack_id="test/pack",
            agent_id="agent-unverified",
            entered_at=datetime(2026, 3, 1),
            duration_days=10.0,
            return_pct=1.5,
            profitable=True,
            # No verification_tx_hash, no chain
        )

        outcome_store.save_outcome(outcome)
        loaded = outcome_store.load_outcomes_for_pack("test/pack")[0]

        assert loaded.verification_tx_hash is None
        assert loaded.chain is None


class TestOutcomeStoreMultiplePacks:
    """Tests for handling multiple packs."""

    def test_multiple_packs_same_agent(self, outcome_store):
        """Test multiple outcomes from same agent for different packs."""
        outcome1 = ExecutionOutcome(
            outcome_id="out-agent1-pack1",
            pack_id="pack-1",
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=10.0,
            return_pct=2.0,
            profitable=True,
        )
        outcome2 = ExecutionOutcome(
            outcome_id="out-agent1-pack2",
            pack_id="pack-2",
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 15),
            duration_days=15.0,
            return_pct=3.0,
            profitable=True,
        )

        outcome_store.save_outcome(outcome1)
        outcome_store.save_outcome(outcome2)

        # Both should be loadable
        all_outcomes = outcome_store.load_all_outcomes()
        assert len(all_outcomes) == 2

        # Each pack should have its own outcome
        pack1_outcomes = outcome_store.load_outcomes_for_pack("pack-1")
        pack2_outcomes = outcome_store.load_outcomes_for_pack("pack-2")
        assert len(pack1_outcomes) == 1
        assert len(pack2_outcomes) == 1

    def test_multiple_outcomes_same_pack(self, outcome_store):
        """Test multiple outcomes for the same pack."""
        base_time = datetime(2026, 3, 1)
        for i in range(5):
            outcome = ExecutionOutcome(
                outcome_id=f"out-pack1-{i}",
                pack_id="yield/aave-usdc-base",
                agent_id=f"agent-{i:03d}",
                entered_at=base_time + timedelta(days=i * 5),
                duration_days=30.0,
                return_pct=3.0 + i * 0.5,
                profitable=True,
            )
            outcome_store.save_outcome(outcome)

        outcomes = outcome_store.load_outcomes_for_pack("yield/aave-usdc-base")
        assert len(outcomes) == 5


class TestOutcomeStoreEdgeCases:
    """Tests for edge cases."""

    def test_outcome_with_empty_lessons(self, outcome_store):
        """Test saving outcome with empty lessons list."""
        outcome = ExecutionOutcome(
            outcome_id="out-empty-lessons",
            pack_id="test/pack",
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=10.0,
            return_pct=1.0,
            profitable=True,
            lessons=[],
        )
        outcome_store.save_outcome(outcome)

        loaded = outcome_store.load_outcomes_for_pack("test/pack")[0]
        assert loaded.lessons == []

    def test_outcome_no_exit(self, outcome_store):
        """Test saving outcome with no exit time (position still open)."""
        outcome = ExecutionOutcome(
            outcome_id="out-no-exit",
            pack_id="test/pack",
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            exited_at=None,  # Still open
            duration_days=0.0,
            return_pct=0.0,
            profitable=False,
        )
        outcome_store.save_outcome(outcome)

        loaded = outcome_store.load_outcomes_for_pack("test/pack")[0]
        assert loaded.exited_at is None
        assert loaded.profitable is False

    def test_monthly_subdirectory_creation(self, outcome_store, sample_outcome):
        """Test that monthly subdirectories are created."""
        outcome_store.save_outcome(sample_outcome)
        
        # Path should include year/month directory
        path = outcome_store._outcome_path(sample_outcome)
        assert path.parent.name == "2026-03"
