"""Schemas for Borg's local-only pack optimizer.

These dataclasses are intentionally JSON-simple.  The optimizer is an evidence
ledger and candidate-diff generator, not a runtime dependency on SkillOpt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OptimizerExample:
    """Privacy-safe training/selection example for pack optimization.

    This schema deliberately excludes raw chat, raw tool output, raw file
    contents, and raw tenant identity.  It stores only compact summaries and
    verification references that can be audited without exposing trajectories.
    """

    example_id: str
    pack_id: str
    task_class: str
    intervention_id: str
    action_summary: str
    stop_summary: str
    verify_summary: str
    outcome: str
    helpful: bool
    verified: bool
    verification_exit_code: int | None
    verification_output_sha256: str
    trusted_tenant_id: str
    receipt_id: str = ""
    dead_ends_avoided: int = 0

    def to_artifact(self) -> dict[str, Any]:
        return {
            "example_id": self.example_id,
            "pack_id": self.pack_id,
            "task_class": self.task_class,
            "intervention_id": self.intervention_id,
            "action_summary": self.action_summary,
            "stop_summary": self.stop_summary,
            "verify_summary": self.verify_summary,
            "outcome": self.outcome,
            "helpful": bool(self.helpful),
            "verified": bool(self.verified),
            "verification_exit_code": self.verification_exit_code,
            "verification_output_sha256": self.verification_output_sha256,
            "trusted_tenant_id": self.trusted_tenant_id,
            "receipt_id": self.receipt_id,
            "dead_ends_avoided": int(self.dead_ends_avoided or 0),
        }


@dataclass(frozen=True)
class CandidateEdit:
    """Bounded pack edit proposed by the local optimizer."""

    op: str
    anchor: str
    before_hash: str
    after_hash: str
    rationale: str
    supporting_receipt_ids: tuple[str, ...] = field(default_factory=tuple)
    risk: str = "low"
    expected_metric_impact: dict[str, float] = field(default_factory=dict)

    def to_artifact(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "anchor": self.anchor,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "rationale": self.rationale,
            "supporting_receipt_ids": list(self.supporting_receipt_ids),
            "risk": self.risk,
            "expected_metric_impact": dict(self.expected_metric_impact),
        }


@dataclass(frozen=True)
class SplitManifest:
    schema_version: str
    pack_id: str
    created_at: str
    source: str
    split_method: str
    seed_hash: str
    train_example_ids: tuple[str, ...]
    selection_example_ids: tuple[str, ...]
    hidden_example_ids: tuple[str, ...] = field(default_factory=tuple)
    privacy_policy: str = "no raw chat/tool output/file contents"
    first_10_claim: bool = False

    def to_artifact(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "created_at": self.created_at,
            "source": self.source,
            "split_method": self.split_method,
            "seed_hash": self.seed_hash,
            "train_example_ids": list(self.train_example_ids),
            "selection_example_ids": list(self.selection_example_ids),
            "hidden_example_ids": list(self.hidden_example_ids),
            "privacy_policy": self.privacy_policy,
            "first_10_claim": self.first_10_claim,
        }


@dataclass(frozen=True)
class SelectionScore:
    candidate_id: str
    baseline_score: float
    candidate_score: float
    score_delta: float
    primary_metric: str
    hard_failures: tuple[str, ...]
    recommendation: str

    @property
    def passed(self) -> bool:
        return self.recommendation == "eligible_for_manual_review"

    def to_artifact(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "candidate_id": self.candidate_id,
            "baseline_score": self.baseline_score,
            "candidate_score": self.candidate_score,
            "score_delta": self.score_delta,
            "primary_metric": self.primary_metric,
            "hard_failures": list(self.hard_failures),
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class OptimizerRunResult:
    success: bool
    candidate_id: str
    output_dir: str
    local_only: bool
    recommendation: str
    score_delta: float
    hard_failures: tuple[str, ...]

    def to_artifact(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "candidate_id": self.candidate_id,
            "output_dir": self.output_dir,
            "local_only": self.local_only,
            "recommendation": self.recommendation,
            "score_delta": self.score_delta,
            "hard_failures": list(self.hard_failures),
            "first_10_claim": False,
            "global_promotion_allowed": False,
        }
