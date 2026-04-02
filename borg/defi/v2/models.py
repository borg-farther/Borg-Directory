"""Borg DeFi V2 — Data models."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import math


def now_iso() -> datetime:
    """Return current UTC time as datetime."""
    return datetime.utcnow()


def days_ago(n: int) -> datetime:
    """Return datetime N days ago."""
    return datetime.utcnow() - timedelta(days=n)


@dataclass
class LossPattern:
    """A pattern of losses observed in a strategy pack."""
    pattern: str
    count: int
    mitigation: str = ""


@dataclass
class Warning:
    """A warning about a DeFi strategy pack."""
    id: str
    type: str = "collective_warning"
    severity: str = "medium"
    pack_id: str = ""
    reason: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    guidance: str = ""
    created_at: Optional[str] = None
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "pack_id": self.pack_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "guidance": self.guidance,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Warning":
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "collective_warning"),
            severity=data.get("severity", "medium"),
            pack_id=data.get("pack_id", ""),
            reason=data.get("reason", ""),
            evidence=data.get("evidence", {}),
            guidance=data.get("guidance", ""),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
        )


@dataclass
class EntryCriteria:
    """Defines who a strategy pack is for."""
    tokens: List[str]                    # what token you need to hold
    chains: List[str]                    # supported chains
    min_amount_usd: float = 0            # minimum investment
    risk_tolerance: List[str] = field(default_factory=lambda: ["low", "medium"])  # who this is for


@dataclass
class ActionSpec:
    """Defines what action to take in a strategy."""
    type: str                            # lend | lp | stake | swap
    protocol: str                        # aave-v3, compound, kamino, etc.
    steps: List[str] = field(default_factory=list)  # human-readable steps


@dataclass
class RiskAssessment:
    """Risk assessment for a strategy pack."""
    il_risk: bool = False                # impermanent loss risk
    rug_score: float = 0.0              # 0=safe, 1=certain rug
    protocol_age_days: int = 0           # days since protocol launch
    audit_status: str = ""               # audit status description


@dataclass
class CollectiveStats:
    """Collective performance statistics for a strategy pack."""
    total_outcomes: int = 0
    profitable: int = 0
    alpha: float = 1.0                   # Beta-Binomial prior + wins
    beta: float = 1.0                    # Beta-Binomial prior + losses
    avg_return_pct: float = 0.0
    median_return_pct: float = 0.0
    std_dev: float = 0.0
    min_return_pct: float = 0.0
    max_return_pct: float = 0.0
    avg_duration_days: float = 0.0
    last_5_returns: List[float] = field(default_factory=list)
    trend: str = "stable"                # improving | stable | degrading
    loss_patterns: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def reputation(self) -> float:
        """Calculate reputation from Beta-Binomial posterior."""
        return self.alpha / (self.alpha + self.beta) if (self.alpha + self.beta) > 0 else 0.0


@dataclass
class DeFiStrategyPack:
    """A complete DeFi strategy pack."""
    id: str                              # unique pack identifier (e.g., "yield/aave-usdc-base")
    name: str                            # human-readable name
    version: int = 1                     # increments on every outcome
    entry: Optional[EntryCriteria] = None
    action: Optional[ActionSpec] = None
    exit_guidance: str = ""              # when to exit
    collective: Optional[CollectiveStats] = None
    risk: Optional[RiskAssessment] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML storage."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "entry": {
                "tokens": self.entry.tokens if self.entry else [],
                "chains": self.entry.chains if self.entry else [],
                "min_amount_usd": self.entry.min_amount_usd if self.entry else 0,
                "risk_tolerance": self.entry.risk_tolerance if self.entry else [],
            } if self.entry else {},
            "action": {
                "type": self.action.type if self.action else "",
                "protocol": self.action.protocol if self.action else "",
                "steps": self.action.steps if self.action else [],
            } if self.action else {},
            "exit": self.exit_guidance,
            "collective": {
                "total_outcomes": self.collective.total_outcomes if self.collective else 0,
                "profitable": self.collective.profitable if self.collective else 0,
                "alpha": self.collective.alpha if self.collective else 1.0,
                "beta": self.collective.beta if self.collective else 1.0,
                "avg_return_pct": self.collective.avg_return_pct if self.collective else 0.0,
                "median_return_pct": self.collective.median_return_pct if self.collective else 0.0,
                "std_dev": self.collective.std_dev if self.collective else 0.0,
                "min_return_pct": self.collective.min_return_pct if self.collective else 0.0,
                "max_return_pct": self.collective.max_return_pct if self.collective else 0.0,
                "avg_duration_days": self.collective.avg_duration_days if self.collective else 0.0,
                "last_5_returns": self.collective.last_5_returns if self.collective else [],
                "trend": self.collective.trend if self.collective else "stable",
                "loss_patterns": self.collective.loss_patterns if self.collective else [],
            } if self.collective else {},
            "risk": {
                "il_risk": self.risk.il_risk if self.risk else False,
                "rug_score": self.risk.rug_score if self.risk else 0.0,
                "protocol_age_days": self.risk.protocol_age_days if self.risk else 0,
                "audit_status": self.risk.audit_status if self.risk else "",
            } if self.risk else {},
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeFiStrategyPack":
        """Deserialize from dictionary (YAML parsing)."""
        entry_data = data.get("entry", {})
        entry = EntryCriteria(
            tokens=entry_data.get("tokens", []),
            chains=entry_data.get("chains", []),
            min_amount_usd=entry_data.get("min_amount_usd", 0),
            risk_tolerance=entry_data.get("risk_tolerance", ["low", "medium"]),
        ) if entry_data else None

        action_data = data.get("action", {})
        action = ActionSpec(
            type=action_data.get("type", ""),
            protocol=action_data.get("protocol", ""),
            steps=action_data.get("steps", []),
        ) if action_data else None

        collective_data = data.get("collective", {})
        collective = CollectiveStats(
            total_outcomes=collective_data.get("total_outcomes", 0),
            profitable=collective_data.get("profitable", 0),
            alpha=collective_data.get("alpha", 1.0),
            beta=collective_data.get("beta", 1.0),
            avg_return_pct=collective_data.get("avg_return_pct", 0.0),
            median_return_pct=collective_data.get("median_return_pct", 0.0),
            std_dev=collective_data.get("std_dev", 0.0),
            min_return_pct=collective_data.get("min_return_pct", 0.0),
            max_return_pct=collective_data.get("max_return_pct", 0.0),
            avg_duration_days=collective_data.get("avg_duration_days", 0.0),
            last_5_returns=collective_data.get("last_5_returns", []),
            trend=collective_data.get("trend", "stable"),
            loss_patterns=collective_data.get("loss_patterns", []),
        ) if collective_data else None

        risk_data = data.get("risk", {})
        risk = RiskAssessment(
            il_risk=risk_data.get("il_risk", False),
            rug_score=risk_data.get("rug_score", 0.0),
            protocol_age_days=risk_data.get("protocol_age_days", 0),
            audit_status=risk_data.get("audit_status", ""),
        ) if risk_data else None

        updated_at = data.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", 1),
            entry=entry,
            action=action,
            exit_guidance=data.get("exit", ""),
            collective=collective,
            risk=risk,
            updated_at=updated_at,
            created_at=created_at,
        )


@dataclass
class StrategyQuery:
    """A user's strategy query/request."""
    token: Optional[str] = None          # token symbol (USDC, ETH, SOL)
    chain: Optional[str] = None           # chain name (optional filter)
    amount_usd: float = 0                 # investment amount in USD
    risk_tolerance: str = "medium"        # low | medium | high | degen
    duration_days: Optional[int] = None  # expected duration (optional)
    action_type: Optional[str] = None   # lend | lp | stake | swap
    protocol: Optional[str] = None        # protocol name filter
    limit: int = 5                        # max recommendations


@dataclass
class StrategyRecommendation:
    """A recommended strategy with supporting evidence."""
    pack_id: str
    name: str = ""                        # human-readable strategy name
    chain: str = ""                       # blockchain (base, ethereum, etc)
    token: str = ""                       # target token (USDC, ETH, etc)
    rank: int = 0
    agent_count: int = 0                 # total agents who tried
    profitable_count: int = 0             # how many were profitable
    avg_return_pct: float = 0.0
    median_return_pct: float = 0.0
    avg_duration_days: float = 0.0
    protocol: str = ""                    # protocol name
    action_type: str = ""                 # lend | lp | stake | swap
    confidence: float = 0.0               # confidence score 0-1
    il_risk: bool = False
    exit_guidance: str = ""
    rug_warnings: List[str] = field(default_factory=list)
    trend: str = "stable"                 # improving | stable | degrading
    reputation: float = 0.0              # Beta-Binomial reputation
    confidence_interval: tuple = field(default_factory=lambda: (0.0, 1.0))  # 95% CI
    total_outcomes: int = 0               # total outcome count
    risk_tolerance: List[str] = field(default_factory=lambda: ["low", "medium"])  # risk tags
    score_components: Optional[dict] = None  # breakdown of scoring formula
    warning: str = ""                     # active warning message
    drift_alert: str = ""                 # drift detection alert


@dataclass
class ExecutionOutcome:
    """Result of executing a strategy."""
    outcome_id: str                      # unique outcome ID
    pack_id: str                         # which pack was used
    agent_id: str                         # agent identifier (hashed)
    entered_at: datetime                 # when position was entered
    exited_at: Optional[datetime] = None # when position was exited
    duration_days: float = 0.0           # holding period
    return_pct: float = 0.0              # return percentage
    profitable: bool = False              # was it profitable
    lessons: List[str] = field(default_factory=list)  # what was learned
    verification_tx_hash: Optional[str] = None  # on-chain proof
    chain: Optional[str] = None          # chain used

    @property
    def is_verified(self) -> bool:
        """Returns True if this outcome has on-chain verification."""
        return bool(self.verification_tx_hash)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML storage."""
        return {
            "outcome_id": self.outcome_id,
            "pack_id": self.pack_id,
            "agent_id": self.agent_id,
            "execution": {
                "entered_at": self.entered_at.isoformat() if self.entered_at else None,
                "exited_at": self.exited_at.isoformat() if self.exited_at else None,
                "duration_days": self.duration_days,
                "return_pct": self.return_pct,
                "profitable": self.profitable,
            },
            "lessons": self.lessons,
            "verification": {
                "tx_hash_enter": self.verification_tx_hash,
                "tx_hash_exit": None,
                "chain": self.chain,
            } if self.verification_tx_hash or self.chain else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionOutcome":
        """Deserialize from dictionary (YAML parsing)."""
        execution = data.get("execution", {})
        verification = data.get("verification", {})

        entered_at = execution.get("entered_at")
        if entered_at and isinstance(entered_at, str):
            entered_at = datetime.fromisoformat(entered_at.replace("Z", "+00:00"))

        exited_at = execution.get("exited_at")
        if exited_at and isinstance(exited_at, str):
            exited_at = datetime.fromisoformat(exited_at.replace("Z", "+00:00"))

        return cls(
            outcome_id=data.get("outcome_id", ""),
            pack_id=data.get("pack_id", ""),
            agent_id=data.get("agent_id", ""),
            entered_at=entered_at,
            exited_at=exited_at,
            duration_days=execution.get("duration_days", 0.0),
            return_pct=execution.get("return_pct", 0.0),
            profitable=execution.get("profitable", False),
            lessons=data.get("lessons", []),
            verification_tx_hash=verification.get("tx_hash_enter"),
            chain=verification.get("chain"),
        )


@dataclass
class AgentReputation:
    """Reputation and trust level for an agent."""
    agent_id: str
    outcomes_submitted: int = 0
    outcomes_verified: int = 0           # had tx_hash proof
    accuracy_score: float = 0.0          # how often they matched collective consensus
    trust_tier: str = "observer"         # observer | contributor | trusted | authority
    influence_weight: float = 1.0        # how much their outcomes count
    vouched_by: List[str] = field(default_factory=list)
    vouches_for: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML storage."""
        return {
            "agent_id": self.agent_id,
            "outcomes_submitted": self.outcomes_submitted,
            "outcomes_verified": self.outcomes_verified,
            "accuracy_score": self.accuracy_score,
            "trust_tier": self.trust_tier,
            "influence_weight": self.influence_weight,
            "vouched_by": self.vouched_by,
            "vouches_for": self.vouches_for,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentReputation":
        """Deserialize from dictionary (YAML parsing)."""
        return cls(
            agent_id=data.get("agent_id", ""),
            outcomes_submitted=data.get("outcomes_submitted", 0),
            outcomes_verified=data.get("outcomes_verified", 0),
            accuracy_score=data.get("accuracy_score", 0.0),
            trust_tier=data.get("trust_tier", "observer"),
            influence_weight=data.get("influence_weight", 1.0),
            vouched_by=data.get("vouched_by", []),
            vouches_for=data.get("vouches_for", []),
        )
