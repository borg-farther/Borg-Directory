"""
Agent reputation manager for Borg DeFi V2 — tracks outcomes, accuracy, and trust tiers.

Trust tiers:
  - observer:    <3 outcomes submitted
  - contributor: 3-19 outcomes
  - trusted:     20+ outcomes AND accuracy > 0.8
  - authority:   50+ outcomes AND 3+ vouches from trusted/authority agents

Influence weights:
  - observer:    0.1x
  - contributor: 1.0x
  - trusted:     1.5x
  - authority:   2.0x
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from borg.defi.v2.models import AgentReputation, ExecutionOutcome


# Trust tier thresholds
TRUST_TIER_THRESHOLDS = {
    "observer": {"min_outcomes": 0, "accuracy_threshold": 0.0, "vouches_required": 0},
    "contributor": {"min_outcomes": 3, "accuracy_threshold": 0.0, "vouches_required": 0},
    "trusted": {"min_outcomes": 20, "accuracy_threshold": 0.8, "vouches_required": 0},
    "authority": {"min_outcomes": 50, "accuracy_threshold": 0.0, "vouches_required": 3},
}

# Influence weights per tier
INFLUENCE_WEIGHTS = {
    "observer": 0.1,
    "contributor": 1.0,
    "trusted": 1.5,
    "authority": 2.0,
}


class AgentReputationManager:
    """
    Manages agent reputation, trust tiers, and vouching relationships.

    Each agent has a YAML file in agents_dir containing their reputation record.
    """

    def __init__(self, agents_dir: Path = None):
        if agents_dir is None:
            agents_dir = Path.home() / ".hermes" / "borg" / "defi" / "agents"
        self.agents_dir = Path(agents_dir)
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, AgentReputation] = {}

    def _agent_path(self, agent_id: str) -> Path:
        """Get the YAML file path for an agent."""
        return self.agents_dir / f"{agent_id}.yaml"

    def get_reputation(self, agent_id: str) -> AgentReputation:
        """
        Get agent reputation. Returns a new reputation record if agent doesn't exist.
        """
        if agent_id in self._cache:
            return self._cache[agent_id]

        path = self._agent_path(agent_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f)
            if d:
                rep = AgentReputation.from_dict(d)
                self._cache[agent_id] = rep
                return rep

        # New agent — return default reputation
        rep = AgentReputation(
            agent_id=agent_id,
            trust_tier="observer",
            influence_weight=0.1,
        )
        return rep

    def update_reputation(self, agent_id: str, outcome: ExecutionOutcome) -> None:
        """
        Update reputation after an outcome is submitted.

        Tracks:
        - outcomes_submitted: total outcomes reported
        - outcomes_verified: outcomes with on-chain proof (tx_hash)
        - accuracy_score: rolling accuracy vs collective consensus
        """
        rep = self.get_reputation(agent_id)

        # Increment submitted count
        rep.outcomes_submitted += 1

        # Increment verified if has on-chain proof
        if outcome.is_verified:
            rep.outcomes_verified += 1

        # Update accuracy score (exponential moving average)
        # For now: 1.0 if profitable matches expectation, 0.0 otherwise
        # A more sophisticated version would compare against pack's avg_return
        old_accuracy = rep.accuracy_score
        outcome_accuracy = 1.0 if outcome.profitable else 0.0
        # EMA with alpha=0.1: new = 0.9*old + 0.1*new
        rep.accuracy_score = 0.9 * old_accuracy + 0.1 * outcome_accuracy

        # Recalculate trust tier
        rep.trust_tier = self._compute_trust_tier(rep)
        rep.influence_weight = INFLUENCE_WEIGHTS[rep.trust_tier]

        # Save
        self._save(rep)

    def _compute_trust_tier(self, rep: AgentReputation) -> str:
        """Compute trust tier based on outcomes and vouches."""
        n = rep.outcomes_submitted

        if n < 3:
            return "observer"
        elif n < 20:
            return "contributor"
        elif rep.accuracy_score > 0.8:
            # Check if has enough vouches for authority
            trusted_vouches = sum(
                1 for v in rep.vouched_by
                if self.get_reputation(v).trust_tier in ("trusted", "authority")
            )
            if n >= 50 and trusted_vouches >= 3:
                return "authority"
            return "trusted"
        else:
            return "contributor"

    def get_trust_tier(self, agent_id: str) -> str:
        """
        Get the current trust tier for an agent.

        Tiers:
          observer    (<3 outcomes)
          contributor (3-19 outcomes)
          trusted     (20+ outcomes, accuracy > 0.8)
          authority   (50+ outcomes, 3+ vouches from trusted/authority)
        """
        rep = self.get_reputation(agent_id)
        return rep.trust_tier

    def get_influence_weight(self, agent_id: str) -> float:
        """
        Get the influence weight for an agent's outcomes.

        Weights:
          observer:    0.1
          contributor: 1.0
          trusted:     1.5
          authority:   2.0
        """
        tier = self.get_trust_tier(agent_id)
        return INFLUENCE_WEIGHTS.get(tier, 0.1)

    def vouch(self, voucher_id: str, target_id: str) -> bool:
        """
        Vouch for another agent. Only trusted/authority agents can vouch.

        Returns True if vouching succeeded, False if the voucher lacks permission.
        """
        voucher = self.get_reputation(voucher_id)
        target = self.get_reputation(target_id)

        # Only trusted or authority can vouch
        if voucher.trust_tier not in ("trusted", "authority"):
            return False

        # Can't vouch for self
        if voucher_id == target_id:
            return False

        # Can't vouch twice
        if target_id in voucher.vouches_for:
            return False

        # Add vouch
        voucher.vouches_for.append(target_id)
        target.vouched_by.append(voucher_id)

        # Recompute target's trust tier (may upgrade to authority)
        old_tier = target.trust_tier
        target.trust_tier = self._compute_trust_tier(target)
        target.influence_weight = INFLUENCE_WEIGHTS[target.trust_tier]

        # Save both
        self._save(voucher)
        self._save(target)

        return True

    def get_vouches(self, agent_id: str) -> tuple[List[str], List[str]]:
        """Return (vouched_by, vouches_for) for an agent."""
        rep = self.get_reputation(agent_id)
        return list(rep.vouched_by), list(rep.vouches_for)

    def _save(self, rep: AgentReputation) -> None:
        """Save reputation to disk and update cache."""
        with open(self._agent_path(rep.agent_id), "w", encoding="utf-8") as f:
            yaml.dump(rep.to_dict(), f, sort_keys=False, allow_unicode=True)
        self._cache[rep.agent_id] = rep

    def list_agents(self) -> List[str]:
        """List all agent IDs with reputation records."""
        if not self.agents_dir.exists():
            return []
        return [p.stem for p in self.agents_dir.glob("*.yaml")]
