"""Borg DeFi V2 — Circuit breaker for recommendation safety.

Circuit breaker states:
  CLOSED → recommendations flowing normally
  OPEN   → pack disabled, no recommendations allowed
  HALF   → limited recommendations with warnings

Trip conditions:
  - 2+ consecutive losses → OPEN
  - reputation < 0.3 with >= 4 outcomes → OPEN
  - any single loss > 20% → HALF + alert

State is persisted to a single JSON file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BreakerState(str):
    """Circuit breaker states (for backward compatibility)."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF = "HALF"


# For backward compatibility with tests
@dataclass
class PackBreakerStatus:
    """Breaker state for a single pack (for backward compatibility)."""
    status: BreakerState = BreakerState.CLOSED
    consecutive_losses: int = 0
    total_losses: int = 0
    total_outcomes: int = 0
    tripped_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class BreakerAlert:
    """An alert generated when a circuit breaker trips (for backward compatibility)."""
    pack_id: str
    new_state: BreakerState
    reason: str
    return_pct: float
    timestamp: datetime

# Default path for circuit breaker state
DEFAULT_STATE_PATH = Path.home() / ".hermes" / "borg" / "defi" / "circuit_breaker.json"


class CircuitBreaker:
    """
    Monitors recommendation outcomes and disables packs that are hurting users.

    This is the safety net that prevents borg from repeatedly recommending
    strategies that have been losing money.

    States:
      CLOSED → recommendations flowing normally
      OPEN   → pack disabled, no recommendations
      HALF   → limited recommendations with warnings
    """

    # Thresholds
    MAX_CONSECUTIVE_LOSSES: int = 2      # 2 losses in a row → OPEN
    MAX_SINGLE_LOSS_PCT: float = 20.0     # any single loss > 20% → HALF + alert
    MIN_OUTCOMES_FOR_REP: int = 4         # need >= 4 outcomes to check reputation
    MIN_REPUTATION: float = 0.3           # reputation < 0.3 with >= 4 outcomes → OPEN
    RECOVERY_PERIOD_HOURS: int = 72       # auto-recover to HALF after 72h

    # State format: {pack_id: {consecutive_losses: int, tripped: bool, tripped_at: str, reason: str, max_single_loss: float}}

    def __init__(self, state_path: Optional[Path] = None, state_dir: Optional[Path] = None):
        """
        Initialize the circuit breaker.

        Args:
            state_path: Path to JSON file for persistence.
            state_dir: Deprecated, use state_path instead. If provided, sets state_path
                      to state_dir / "circuit_breaker.json" for backward compatibility.
        """
        if state_dir is not None:
            # Backward compatibility: treat state_dir as a directory for multiple YAML files
            # but we use JSON, so convert to a single file path
            state_dir = Path(state_dir)
            if state_dir.suffix == '.json':
                # If it ends in .json, treat as a direct file path
                state_path = state_dir
            else:
                # Otherwise treat as directory and append our filename
                state_path = state_dir / "circuit_breaker.json"
        
        if state_path is None:
            state_path = DEFAULT_STATE_PATH
        self.state_path = Path(state_path)
        
        # In-memory cache of pack states: pack_id -> dict with keys:
        # consecutive_losses, tripped, tripped_at, reason, max_single_loss
        self._states: Dict[str, Dict] = {}
        
        # Pending alerts (cleared after get_and_clear_alerts)
        self._pending_alerts: List[Dict] = []

        # Load persisted state
        self._load()

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        """Load persisted state from JSON file."""
        if not self.state_path.exists():
            return

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return

            # Validate and load each pack's state
            for pack_id, state in data.items():
                if not isinstance(state, dict):
                    continue
                self._states[pack_id] = {
                    "consecutive_losses": state.get("consecutive_losses", 0),
                    "tripped": state.get("tripped", False),
                    "tripped_at": state.get("tripped_at"),
                    "reason": state.get("reason", ""),
                    "max_single_loss": state.get("max_single_loss", 0.0),
                }
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load circuit breaker state from {self.state_path}: {e}")
            self._states = {}

    def _save(self) -> None:
        """Persist all pack states to JSON file."""
        # Ensure parent directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize states
        data = {}
        for pack_id, state in self._states.items():
            # Don't save CLOSED states with no history
            if not state["tripped"] and state["consecutive_losses"] == 0 and state["max_single_loss"] == 0:
                continue
            data[pack_id] = state
        
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save circuit breaker state: {e}")

    # -------------------------------------------------------------------------
    # Core API
    # -------------------------------------------------------------------------

    def check_before_recommend(self, pack_id: str, pack) -> Tuple[bool, Optional[str]]:
        """
        Check if a pack can be recommended.

        Args:
            pack_id: Pack identifier.
            pack: The DeFiStrategyPack object (used to check reputation and warnings).

        Returns:
            Tuple of (allowed: bool, warning: str).
            - (True, None) → fully allowed
            - (True, "⚠️ WARNING: ...") → allowed with warning (HALF state)
            - (False, "Circuit OPEN: ...") → not allowed (OPEN state)
        """
        state = self._states.get(pack_id, {
            "consecutive_losses": 0,
            "tripped": False,
            "tripped_at": None,
            "reason": "",
            "max_single_loss": 0.0,
        })

        # If tripped, check for auto-recovery
        if state["tripped"]:
            tripped_at = state.get("tripped_at")
            if tripped_at:
                try:
                    tripped_time = datetime.fromisoformat(tripped_at)
                    hours_elapsed = (datetime.now() - tripped_time).total_seconds() / 3600
                    if hours_elapsed >= self.RECOVERY_PERIOD_HOURS:
                        # Auto-recover to HALF
                        state["tripped"] = False
                        state["reason"] = f"Auto-recovered after {self.RECOVERY_PERIOD_HOURS}h"
                        self._states[pack_id] = state
                        self._save()
                        return True, f"⚠️ WARNING: {state['reason']}. Recommend smaller position."
                except (ValueError, TypeError):
                    pass
            
            # Still blocked
            return False, f"Circuit OPEN: {state['reason']}"

        return True, None

    def record_outcome(self, pack_id: str, profitable: bool, loss_pct: float = 0.0) -> Optional[str]:
        """
        Record an execution outcome and check if circuit breaker trips.

        Args:
            pack_id: Pack identifier.
            profitable: Whether the outcome was profitable.
            loss_pct: The loss percentage (positive number, e.g., 25.0 for 25% loss).
                     Only used when profitable=False.

        Returns:
            Alert message if circuit breaker trips, None otherwise.
        """
        if pack_id not in self._states:
            self._states[pack_id] = {
                "consecutive_losses": 0,
                "tripped": False,
                "tripped_at": None,
                "reason": "",
                "max_single_loss": 0.0,
            }

        state = self._states[pack_id]
        alert_msg = None

        if not profitable:
            # It's a loss
            state["consecutive_losses"] += 1
            
            # Track max single loss
            if loss_pct > state["max_single_loss"]:
                state["max_single_loss"] = loss_pct

            # Check single catastrophic loss → HALF
            if loss_pct > self.MAX_SINGLE_LOSS_PCT:
                state["tripped"] = True
                state["tripped_at"] = datetime.now().isoformat()
                state["reason"] = f"Single loss of {loss_pct:.1f}% exceeds {self.MAX_SINGLE_LOSS_PCT:.0f}% threshold"
                alert_msg = f"⚠️ CIRCUIT BREAKER: {pack_id} tripped to HALF - {state['reason']}"
                self._save()
                return alert_msg

            # Check consecutive losses → OPEN
            if state["consecutive_losses"] >= self.MAX_CONSECUTIVE_LOSSES:
                state["tripped"] = True
                state["tripped_at"] = datetime.now().isoformat()
                state["reason"] = f"{state['consecutive_losses']} consecutive losses"
                alert_msg = f"⚠️ CIRCUIT BREAKER: {pack_id} tripped to OPEN - {state['reason']}"
                self._save()
                return alert_msg

        else:
            # It's a win — reset consecutive loss counter
            state["consecutive_losses"] = 0

        # Persist state
        self._save()
        return None

    def check_outcome_from_pack(self, pack_id: str, pack) -> None:
        """
        Check outcome using pack's collective stats for reputation-based trip.
        
        This is called after pack stats are updated and can trip based on
        reputation < 0.3 with >= 4 outcomes.

        Args:
            pack_id: Pack identifier.
            pack: The DeFiStrategyPack with updated collective stats.
        """
        if not pack or not pack.collective:
            return
            
        state = self._states.get(pack_id, {
            "consecutive_losses": 0,
            "tripped": False,
            "tripped_at": None,
            "reason": "",
            "max_single_loss": 0.0,
        })
        
        # Check reputation threshold (only with sufficient samples)
        total_outcomes = pack.collective.total_outcomes
        if total_outcomes >= self.MIN_OUTCOMES_FOR_REP:
            reputation = pack.collective.reputation
            if reputation < self.MIN_REPUTATION:
                state["tripped"] = True
                state["tripped_at"] = datetime.now().isoformat()
                state["reason"] = f"Reputation {reputation:.2f} < {self.MIN_REPUTATION} with {total_outcomes} outcomes"
                self._states[pack_id] = state
                self._save()
                logger.warning(f"Circuit breaker tripped for {pack_id}: {state['reason']}")

    def get_tripped_packs(self) -> List[str]:
        """
        Get all packs that are currently tripped (OPEN or HALF).

        Returns:
            List of pack IDs that are tripped.
        """
        return [
            pack_id for pack_id, state in self._states.items()
            if state.get("tripped", False)
        ]

    def reset(self, pack_id: str) -> None:
        """
        Manual override to clear breaker state and restore CLOSED.

        Args:
            pack_id: Pack identifier to reset.
        """
        self._states[pack_id] = {
            "consecutive_losses": 0,
            "tripped": False,
            "tripped_at": None,
            "reason": "",
            "max_single_loss": 0.0,
        }
        self._save()
        logger.info(f"Circuit breaker reset for {pack_id}")

    def get_state(self, pack_id: str) -> Dict:
        """
        Get the current breaker state for a pack.

        Args:
            pack_id: Pack identifier.

        Returns:
            Dict with state info (consecutive_losses, tripped, tripped_at, reason, max_single_loss).
        """
        if pack_id not in self._states:
            return {
                "consecutive_losses": 0,
                "tripped": False,
                "tripped_at": None,
                "reason": "",
                "max_single_loss": 0.0,
            }
        return self._states[pack_id]

    def trip(self, pack_id: str, reason: str) -> None:
        """
        Manually trip (or set) the breaker for a pack to OPEN.

        Args:
            pack_id: Pack identifier.
            reason: Why it was tripped.
        """
        self._states[pack_id] = {
            "consecutive_losses": 0,
            "tripped": True,
            "tripped_at": datetime.now().isoformat(),
            "reason": reason,
            "max_single_loss": 0.0,
        }
        self._save()
        logger.warning(f"Circuit breaker manually tripped for {pack_id}: {reason}")

    def get_and_clear_alerts(self) -> List[Dict]:
        """
        Get all pending alerts and clear them.

        Returns:
            List of alert dicts that were pending.
        """
        alerts = self._pending_alerts
        self._pending_alerts = []
        return alerts
