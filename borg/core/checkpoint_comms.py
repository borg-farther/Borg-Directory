from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Phase(str, Enum):
    INVESTIGATE = "investigate"
    DECIDE = "decide"
    EXECUTE = "execute"
    VERIFY = "verify"


@dataclass(frozen=True)
class CostModel:
    """Simple blended model for conservative savings estimates."""

    avg_seconds_per_tool_call: float = 25.0
    usd_per_million_tokens_low: float = 3.0
    usd_per_million_tokens_high: float = 15.0


@dataclass(frozen=True)
class SavingsEstimate:
    tool_calls_avoided: int
    seconds_saved: float
    token_savings: int
    usd_low: float
    usd_high: float


@dataclass(frozen=True)
class CheckpointReceipt:
    phase: Phase
    borg_used: bool
    source: str
    confidence: Confidence
    what_changed: str
    next_step: str
    estimate: SavingsEstimate


_ALLOWED_SOURCES = {"borg", "guild", "none"}


def estimate_savings(
    *,
    tool_calls_avoided: int = 0,
    token_savings: int = 0,
    model: CostModel | None = None,
) -> SavingsEstimate:
    """Estimate time + USD savings using transparent, conservative defaults."""

    if tool_calls_avoided < 0:
        raise ValueError("tool_calls_avoided must be >= 0")
    if token_savings < 0:
        raise ValueError("token_savings must be >= 0")

    m = model or CostModel()
    seconds_saved = float(tool_calls_avoided) * m.avg_seconds_per_tool_call
    usd_low = (token_savings / 1_000_000.0) * m.usd_per_million_tokens_low
    usd_high = (token_savings / 1_000_000.0) * m.usd_per_million_tokens_high

    return SavingsEstimate(
        tool_calls_avoided=tool_calls_avoided,
        seconds_saved=seconds_saved,
        token_savings=token_savings,
        usd_low=usd_low,
        usd_high=usd_high,
    )


def build_checkpoint_receipt(
    *,
    phase: Phase,
    borg_used: bool,
    source: str,
    confidence: Confidence,
    what_changed: str,
    next_step: str,
    tool_calls_avoided: int = 0,
    token_savings: int = 0,
    model: CostModel | None = None,
) -> CheckpointReceipt:
    """Build structured checkpoint data suitable for Telegram rendering."""

    normalized_source = source.strip().lower()
    if normalized_source not in _ALLOWED_SOURCES:
        raise ValueError("source must be one of: borg, guild, none")
    if not what_changed.strip():
        raise ValueError("what_changed is required")
    if not next_step.strip():
        raise ValueError("next_step is required")

    estimate = estimate_savings(
        tool_calls_avoided=tool_calls_avoided,
        token_savings=token_savings,
        model=model,
    )

    return CheckpointReceipt(
        phase=phase,
        borg_used=borg_used,
        source=normalized_source,
        confidence=confidence,
        what_changed=what_changed.strip(),
        next_step=next_step.strip(),
        estimate=estimate,
    )


def render_telegram_checkpoint(receipt: CheckpointReceipt) -> str:
    """Render the canonical 5-line user-facing checkpoint block."""

    e = receipt.estimate
    return "\n".join(
        [
            "[borg checkpoint]",
            f"phase: {receipt.phase.value}",
            f"borg used: {'yes' if receipt.borg_used else 'no'} "
            f"(source: {receipt.source}, confidence: {receipt.confidence.value})",
            f"what changed: {receipt.what_changed}",
            f"estimated save: {e.tool_calls_avoided} calls | {int(e.seconds_saved)}s | "
            f"{e.token_savings} tokens | ${e.usd_low:.4f}-${e.usd_high:.4f}",
            f"next step: {receipt.next_step}",
        ]
    )


def mechanism_mode_for_risk_level(risk_level: str) -> int:
    """Select checkpoint count by risk level.

    low -> 1 checkpoint (final only)
    medium -> 2 checkpoints (decision + final)
    high -> 4 checkpoints (investigate, decide, execute, verify)
    """

    level = risk_level.strip().lower()
    if level == "low":
        return 1
    if level == "medium":
        return 2
    if level == "high":
        return 4
    raise ValueError("risk_level must be one of: low, medium, high")
