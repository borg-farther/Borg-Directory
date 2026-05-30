"""Maintainer review packets for local pack optimizer candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_REVIEW_ARTIFACTS = (
    "candidate_pack.patch",
    "candidate_pack.preview",
    "accepted_edits.json",
    "rejected_edits.json",
    "selection_score.json",
    "privacy_scan.json",
    "prompt_injection_scan.json",
    "candidate_integrity.json",
    "optimizer_run.json",
)
_CLAIM_KEYS = {"first_10_claim", "global_promotion_allowed", "public_lift_claim"}


def _sha256_ref(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"review artifact must not be a symlink: {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"review artifact must be a JSON object: {path.name}")
    return data


def _load_text(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"review artifact must not be a symlink: {path.name}")
    return path.read_text(encoding="utf-8")


def _has_truthy_claim(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in _CLAIM_KEYS and item not in (False, None, "", 0, "false", "False"):
                return True
            if _has_truthy_claim(item):
                return True
    if isinstance(value, list):
        return any(_has_truthy_claim(item) for item in value)
    return False


def build_review_packet(
    candidate_dir: str | Path,
    *,
    source_verified: bool = False,
    verified_inspection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact maintainer review packet from an optimizer artifact dir.

    Artifact-only review is inventory, not eligibility.  A review packet may only
    return `eligible_for_manual_review` after the caller has run source-bound
    verification with the original pack/taskset/examples.
    """
    root = Path(candidate_dir)
    if root.is_symlink():
        raise ValueError("candidate review directory must not be a symlink")
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"candidate review directory not found: {root}")
    missing = [name for name in REQUIRED_REVIEW_ARTIFACTS if not (root / name).exists()]
    if missing:
        raise ValueError("candidate review bundle incomplete: " + ", ".join(missing))

    patch_text = _load_text(root / "candidate_pack.patch")
    preview_text = _load_text(root / "candidate_pack.preview")
    accepted = _load_json(root / "accepted_edits.json")
    rejected = _load_json(root / "rejected_edits.json")
    score = _load_json(root / "selection_score.json")
    privacy = _load_json(root / "privacy_scan.json")
    injection = _load_json(root / "prompt_injection_scan.json")
    integrity = _load_json(root / "candidate_integrity.json")
    optimizer_run = _load_json(root / "optimizer_run.json")

    candidate_id = str(optimizer_run.get("candidate_id") or score.get("candidate_id") or integrity.get("candidate_id") or "")
    if verified_inspection is not None:
        verified_candidate_id = str(verified_inspection.get("candidate_id") or "")
        if verified_candidate_id and verified_candidate_id != candidate_id:
            raise ValueError("source-verified review candidate id mismatch")
        source_verified = bool(verified_inspection.get("source_verified", source_verified))
    overclaim_detected = any(_has_truthy_claim(item) for item in (accepted, rejected, score, privacy, injection, integrity, optimizer_run))
    hard_failures = list(score.get("hard_failures") or optimizer_run.get("hard_failures") or [])
    if overclaim_detected:
        hard_failures.append("artifact_overclaim_detected")
    accepted_raw = accepted.get("edits")
    rejected_raw = rejected.get("rejections")
    accepted_edits: list[Any] = accepted_raw if isinstance(accepted_raw, list) else []
    rejected_edits: list[Any] = rejected_raw if isinstance(rejected_raw, list) else []
    artifact_eligible = score.get("recommendation") == "eligible_for_manual_review" and not hard_failures and not privacy.get("blocked") and not injection.get("blocked") and bool(accepted_edits)
    eligible = bool(source_verified and artifact_eligible)
    if eligible:
        manual_review_eligibility = "eligible_for_manual_review"
        decision = "awaiting_maintainer_review"
    elif not source_verified and artifact_eligible:
        manual_review_eligibility = "source_verification_required"
        decision = "source_verification_required"
    else:
        manual_review_eligibility = "blocked"
        decision = "reject"

    packet = {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "pack_id": optimizer_run.get("pack_id", accepted.get("pack_id", rejected.get("pack_id", ""))),
        "source_verified": bool(source_verified),
        "decision": decision,
        "manual_review_eligibility": manual_review_eligibility,
        "score": {
            "recommendation": score.get("recommendation", ""),
            "score_delta": score.get("score_delta", 0),
            "baseline_score": score.get("baseline_score", 0),
            "candidate_score": score.get("candidate_score", 0),
            "hard_failures": hard_failures,
        },
        "diff": {
            "patch_sha256": _sha256_ref(patch_text),
            "preview_sha256": _sha256_ref(preview_text),
            "patch_line_count": len(patch_text.splitlines()),
        },
        "safety": {
            "privacy_blocked": bool(privacy.get("blocked")),
            "privacy_risk_score": privacy.get("risk_score", 0),
            "prompt_injection_blocked": bool(injection.get("blocked")),
            "prompt_injection_score": injection.get("score", 0),
            "scan_blocked_raw_artifacts_suppressed": bool(integrity.get("scan_blocked_raw_artifacts_suppressed")),
            "artifact_overclaim_detected": overclaim_detected,
        },
        "edits": {
            "accepted_count": len(accepted_edits),
            "rejected_count": len(rejected_edits),
            "accepted_ops": [edit.get("op", "") for edit in accepted_edits if isinstance(edit, dict)],
            "rejected_ops": [edit.get("op", "") for edit in rejected_edits if isinstance(edit, dict)],
        },
        "provenance": {
            "local_only": bool(optimizer_run.get("local_only")),
            "selection_evidence_sha256": optimizer_run.get("selection_evidence_sha256", ""),
            "baseline_pack_sha256": optimizer_run.get("baseline_pack_sha256", ""),
            "candidate_pack_sha256": optimizer_run.get("candidate_pack_sha256", ""),
        },
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
        "reviewer_checklist": [
            "Confirm source-bound inspect/apply was run",
            "Read ACTION / STOP / VERIFY diff for overclaiming or weak-match drift",
            "Confirm no raw trajectory, secret, prompt-injection, first-10, or public-lift claim is present",
            "Confirm accepted edits are backed by verified outcome receipts and rejected edits stay rejected",
            "Do not promote globally without separate trusted-tenant quorum and first-10 evidence",
        ],
        "next_actions": [
            f"Run source-bound inspect for {candidate_id} with --pack-file --taskset --examples-file",
            "If source verification passes, apply locally only and rerun focused/full gates",
            "Record maintainer decision and keep rejected edits as negative evidence",
        ],
    }
    return packet
