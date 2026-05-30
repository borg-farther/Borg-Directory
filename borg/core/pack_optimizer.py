"""Local-only Borg pack optimizer inspired by SkillOpt discipline.

This module intentionally does not vendor SkillOpt and does not mutate global
packs.  It turns privacy-safe verified outcome summaries into bounded candidate
pack diffs, evaluates them against a deterministic selection gate, and writes an
auditable artifact bundle for manual review.
"""

from __future__ import annotations

import difflib
import errno
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from borg.core.collective_learning import _connect, get_collective_learning_db_path
from borg.core.pack_optimizer_rejections import RejectedEditMemory
from borg.core.pack_optimizer_schemas import CandidateEdit, OptimizerExample, OptimizerRunResult, SelectionScore, SplitManifest
from borg.core.pack_optimizer_scoring import WEIGHTS, compare_baseline_candidate
from borg.core.privacy import privacy_scan_structured
from borg.core.prompt_injection import neutralize_for_retrieval, scan_prompt_injection
from borg.core.schema import parse_workflow_pack, validate_pack

_SECRETISH_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{16,}|xox[baprs]-[a-z0-9-]{16,}|"
    r"akia[0-9a-z]{16}|password\s*=\s*\S+|api[_-]?key\s*=\s*\S+|token\s*=\s*\S+)"
)
_RAW_TRAJECTORY_RE = re.compile(
    r"(?i)(RAW_USER_CHAT_SENTINEL|RAW_TOOL_OUTPUT_SENTINEL|RAW_USER_CHAT|RAW_TOOL_OUTPUT|BEGIN RAW|END RAW|\braw_user_chat\b|\braw_tool_output\b)"
)
_SHA256_REF_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$", re.I)
_TRUSTED_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_.:@/\\-]{2,240}$", re.I)
_CANDIDATE_ID_RE = re.compile(r"^packopt-sha256:[0-9a-f]{64}$")
_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,120}$", re.I)
_ALLOWED_EDIT_OPS = {
    "add_antipattern",
    "add_verification_step",
    "tighten_no_confident_match_rule",
    "tighten_stop_rule",
}

REQUIRED_ARTIFACTS = (
    "candidate_pack.patch",
    "candidate_pack.preview",
    "accepted_edits.json",
    "rejected_edits.json",
    "training_manifest.json",
    "selection_score.json",
    "privacy_scan.json",
    "prompt_injection_scan.json",
    "candidate_integrity.json",
    "optimizer_run.json",
)
_SUPPRESSED_PATCH_TEXT = "# candidate patch suppressed because privacy or prompt-injection scan failed\n"
_SUPPRESSED_PREVIEW_TEXT = "# candidate preview suppressed because privacy or prompt-injection scan failed\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()


def _sha256_ref(value: str) -> str:
    return "sha256:" + _sha256_text(value)


def _safe_text(value: Any, max_chars: int = 600) -> str:
    text = str(value or "")
    text = _RAW_TRAJECTORY_RE.sub("[REDACTED_RAW_TRAJECTORY]", text)
    text = _SECRETISH_RE.sub("[REDACTED]", text)
    try:
        text = str(privacy_scan_structured(text).sanitized)
    except Exception:
        text = _SECRETISH_RE.sub("[REDACTED]", text)
    text = _RAW_TRAJECTORY_RE.sub("[REDACTED_RAW_TRAJECTORY]", text)
    text = neutralize_for_retrieval(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _normalize_sha256_ref(value: Any) -> str:
    text = _safe_text(value, max_chars=96).lower()
    if not text or not _SHA256_REF_RE.match(text):
        return ""
    return text if text.startswith("sha256:") else f"sha256:{text}"


def _normalize_trusted_tenant_id(value: Any) -> str:
    text = _safe_text(value, max_chars=256)
    if not text or text.lower() in {"local", "default", "unknown", "anonymous"}:
        return ""
    if text.startswith("tenant-identity-sha256:") and _SHA256_REF_RE.match(text.removeprefix("tenant-identity-")):
        return text.lower()
    if not _TRUSTED_TENANT_RE.match(text):
        return ""
    return "tenant-identity-sha256:" + _sha256_text(text.lower())


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "success", "helpful"}


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_guidance_parts(guidance: Any) -> tuple[str, str, str]:
    if isinstance(guidance, dict):
        action = guidance.get("ACTION") or guidance.get("action") or guidance.get("worked") or ""
        stop = guidance.get("STOP") or guidance.get("stop") or guidance.get("avoid") or ""
        verify = guidance.get("VERIFY") or guidance.get("verify") or guidance.get("verification") or ""
        if isinstance(action, (list, tuple)):
            action = " ".join(str(x) for x in action)
        if isinstance(stop, (list, tuple)):
            stop = " ".join(str(x) for x in stop)
        if isinstance(verify, (list, tuple)):
            verify = " ".join(str(x) for x in verify)
        return _safe_text(action, 400), _safe_text(stop, 400), _safe_text(verify, 400)
    text = _safe_text(guidance, 900)
    return text[:400], "", ""


def _example_from_artifact(data: dict[str, Any]) -> OptimizerExample:
    action, stop, verify = _extract_guidance_parts(
        data.get("guidance")
        or {
            "ACTION": data.get("action_summary", ""),
            "STOP": data.get("stop_summary", ""),
            "VERIFY": data.get("verify_summary", ""),
        }
    )
    pack_id = _safe_text(data.get("pack_id") or "unknown", max_chars=120) or "unknown"
    task_class = _safe_text(data.get("task_class") or data.get("error_class") or data.get("task_type") or "unknown", max_chars=160) or "unknown"
    verification_hash = _normalize_sha256_ref(data.get("verification_output_sha256"))
    trusted_id = _normalize_trusted_tenant_id(data.get("trusted_tenant_id"))
    material = {
        "pack_id": pack_id,
        "task_class": task_class,
        "intervention_id": data.get("intervention_id", ""),
        "receipt_id": data.get("receipt_id", ""),
        "outcome": data.get("outcome", ""),
        "helpful": _bool(data.get("helpful")),
        "verified": _bool(data.get("verified")),
    }
    example_id = _safe_text(data.get("example_id"), max_chars=180) or "example-sha256:" + _sha256_text(_canonical_json(material))
    return OptimizerExample(
        example_id=example_id,
        pack_id=pack_id,
        task_class=task_class,
        intervention_id=_safe_text(data.get("intervention_id"), max_chars=180),
        action_summary=action,
        stop_summary=stop,
        verify_summary=verify,
        outcome=_safe_text(data.get("outcome") or "unknown", max_chars=80).lower() or "unknown",
        helpful=_bool(data.get("helpful")),
        verified=_bool(data.get("verified")),
        verification_exit_code=_int_or_none(data.get("verification_exit_code")),
        verification_output_sha256=verification_hash,
        trusted_tenant_id=trusted_id,
        receipt_id=_safe_text(data.get("receipt_id"), max_chars=180),
        dead_ends_avoided=max(0, int(data.get("dead_ends_avoided") or 0)),
    )


def sanitize_training_record(record: dict[str, Any]) -> OptimizerExample:
    """Return a privacy-safe optimizer example from a raw-ish local record.

    The function intentionally ignores raw trajectory keys such as raw_user_chat,
    raw_tool_output, observations, messages, and file contents.
    """
    allowed = {
        "example_id",
        "pack_id",
        "task_class",
        "error_class",
        "task_type",
        "intervention_id",
        "guidance",
        "action_summary",
        "stop_summary",
        "verify_summary",
        "outcome",
        "helpful",
        "verified",
        "verification_exit_code",
        "verification_output_sha256",
        "trusted_tenant_id",
        "receipt_id",
        "dead_ends_avoided",
    }
    return _example_from_artifact({key: record.get(key) for key in allowed if key in record})


def scan_candidate_text(text: str) -> dict[str, Any]:
    candidate_text = str(text or "")
    privacy = privacy_scan_structured(candidate_text)
    injection = scan_prompt_injection(candidate_text)
    raw_trajectory_blocked = bool(_RAW_TRAJECTORY_RE.search(candidate_text))
    secretish_blocked = bool(_SECRETISH_RE.search(candidate_text))
    blockers: list[str] = []
    if privacy.blocked or raw_trajectory_blocked or secretish_blocked:
        blockers.append("privacy")
    if injection.blocked:
        blockers.append("prompt_injection")
    if raw_trajectory_blocked:
        blockers.append("raw_trajectory")
    if secretish_blocked:
        blockers.append("secretish")
    finding_classes = sorted(
        {finding.kind for finding in privacy.findings}
        | ({"raw_trajectory"} if raw_trajectory_blocked else set())
        | ({"secretish"} if secretish_blocked else set())
    )
    return {
        "passed": not blockers,
        "blockers": blockers,
        "privacy_blocked": bool(privacy.blocked or raw_trajectory_blocked or secretish_blocked),
        "privacy_risk_score": float(privacy.risk_score),
        "privacy_finding_classes": finding_classes,
        "raw_trajectory_blocked": raw_trajectory_blocked,
        "secretish_blocked": secretish_blocked,
        "prompt_injection_blocked": bool(injection.blocked),
        "prompt_injection_score": float(injection.score),
        "prompt_injection_classes": sorted({finding.kind for finding in injection.findings}),
    }


def _artifact_leak_failures(name: str, text: str) -> list[str]:
    failures: list[str] = []
    if _RAW_TRAJECTORY_RE.search(text or ""):
        failures.append(f"{name}:raw_trajectory")
    if _SECRETISH_RE.search(text or ""):
        failures.append(f"{name}:secretish")
    injection = scan_prompt_injection(text or "")
    if injection.blocked:
        failures.append(f"{name}:prompt_injection")
    return failures


def _assert_no_artifact_leaks(artifacts: dict[str, str]) -> None:
    failures: list[str] = []
    for name, text in artifacts.items():
        failures.extend(_artifact_leak_failures(name, text))
    if failures:
        raise ValueError("candidate artifact leak detected: " + ", ".join(failures[:8]))


def _unified_diff(pack_id: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{pack_id}.baseline",
            tofile=f"{pack_id}.candidate",
        )
    )


def load_examples_file(path: str | Path) -> list[OptimizerExample]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("examples", [])
    else:
        raise ValueError("examples file must contain a list or {'examples': [...]} object")
    if not isinstance(records, list):
        raise ValueError("examples file must contain a list or {'examples': [...]} object")
    return [sanitize_training_record(item) for item in records if isinstance(item, dict)]


def _candidate_id_material(
    *,
    pack_id: str,
    pack_text: str,
    candidate_text: str,
    train_examples: Sequence[OptimizerExample],
    hidden_examples: Sequence[OptimizerExample],
    edits: Sequence[CandidateEdit],
    max_edits: int,
    selection_evidence: dict[str, Any],
    rejected_memory_skipped_edits: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    selection_evidence_sha256 = _sha256_ref(_canonical_json(selection_evidence))
    return {
        "algorithm": "borg-pack-optimizer-v1",
        "pack_id": pack_id,
        "baseline_pack_sha256": _sha256_ref(pack_text),
        "candidate_pack_sha256": _sha256_ref(candidate_text),
        "train_example_ids": [ex.example_id for ex in train_examples],
        "train_example_refs": [_example_ref(ex) for ex in train_examples],
        "selection_example_ids": list(selection_evidence.get("selection_example_ids", [])),
        "selection_example_refs": list(selection_evidence.get("selection_example_refs", [])),
        "hidden_example_ids": [ex.example_id for ex in hidden_examples],
        "hidden_example_refs": [_example_ref(ex) for ex in hidden_examples],
        "selection_taskset_sha256": selection_evidence.get("taskset_sha256", ""),
        "selection_evidence_sha256": selection_evidence_sha256,
        "edit_ops": [edit.op for edit in edits],
        "edit_artifacts_sha256": _edit_artifacts_sha256(edits),
        "rejected_memory_skipped_edits": [dict(item) for item in rejected_memory_skipped_edits],
        "max_edits": max_edits,
    }


def _candidate_id_from_material(material: dict[str, Any]) -> str:
    return "packopt-sha256:" + _sha256_text(_canonical_json(material))


def _strong_example_failures(example: OptimizerExample, *, pack_id: str) -> list[str]:
    failures: list[str] = []
    if example.pack_id != pack_id:
        failures.append("pack_id_mismatch")
    if not example.verified:
        failures.append("not_verified")
    if example.verification_exit_code is None:
        failures.append("missing_verification_exit_code")
    if not example.verification_output_sha256:
        failures.append("missing_verification_output_sha256")
    if not example.trusted_tenant_id:
        failures.append("missing_trusted_tenant_id")
    if not example.intervention_id:
        failures.append("missing_intervention_id")
    if not example.receipt_id:
        failures.append("missing_receipt_id")
    return failures


def _validated_examples(examples: Sequence[OptimizerExample], *, pack_id: str) -> list[OptimizerExample]:
    valid: list[OptimizerExample] = []
    failures: list[str] = []
    seen_example_ids: set[str] = set()
    seen_receipt_ids: set[str] = set()
    seen_intervention_ids: set[str] = set()
    for example in examples:
        reasons = _strong_example_failures(example, pack_id=pack_id)
        if example.example_id in seen_example_ids:
            reasons.append("duplicate_example_id")
        seen_example_ids.add(example.example_id)
        if example.receipt_id in seen_receipt_ids:
            reasons.append("duplicate_receipt_id")
        seen_receipt_ids.add(example.receipt_id)
        if example.intervention_id in seen_intervention_ids:
            reasons.append("duplicate_intervention_id")
        seen_intervention_ids.add(example.intervention_id)
        leak_reasons = _artifact_leak_failures(f"example:{example.example_id}", _canonical_json(example.to_artifact()))
        if leak_reasons:
            reasons.extend(leak_reasons)
        if reasons:
            failures.append(f"{example.example_id}:{','.join(reasons)}")
        else:
            valid.append(example)
    if failures:
        raise ValueError("optimizer examples must be verified, target-pack, shareable receipts: " + "; ".join(failures[:5]))
    return valid


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _safe_pack_id(pack_id: str) -> str:
    text = _safe_text(pack_id, 140)
    if not _PACK_ID_RE.match(text):
        raise ValueError(f"invalid pack id: {pack_id!r}")
    return text


def _slug_from_borg_uri(value: str) -> str:
    text = str(value or "").strip().strip("'\"")
    if not text.lower().startswith("borg://"):
        return ""
    text = text.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if not text or text.lower() == "borg://":
        return ""
    return _safe_pack_id(text.rsplit("/", 1)[-1])


def _pack_slug_from_ref(value: Any, *, allow_plain: bool = False) -> str:
    """Normalize explicit pack refs such as `pack:x` or `pack_uri:borg://.../x`.

    Generic URLs/paths and broad metadata like `problem_class:*` are not pack
    provenance. They deliberately return no match even if the final path segment
    happens to equal the target pack id.
    """
    text = str(value or "").strip().strip("'\"")
    text = re.sub(r"\s+#.*$", "", text).strip().strip("'\"")
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("pack_uri:", "borg-pack:", "pack_id:", "pack:", "seed_pack:"):
        if lowered.startswith(prefix):
            raw = text[len(prefix) :].strip()
            if raw.lower().startswith("borg://"):
                return _slug_from_borg_uri(raw)
            if "://" in raw or "/" in raw:
                return ""
            return _safe_pack_id(raw)
    if lowered.startswith("borg://"):
        return _slug_from_borg_uri(text)
    if ":" in text or "/" in text:
        return ""
    return _safe_pack_id(text) if allow_plain and text else ""


def _source_refs_include_pack(source_refs: Sequence[Any], pack_id: str) -> bool:
    wanted = _safe_pack_id(pack_id).lower()
    for ref in source_refs:
        try:
            if _pack_slug_from_ref(ref, allow_plain=False).lower() == wanted:
                return True
        except ValueError:
            continue
    return False


def _extract_pack_id_from_text(text: str) -> str:
    match = re.search(r"(?m)^\s*id:\s*([^\n#]+)\s*(?:#.*)?$", text or "")
    return _pack_slug_from_ref(match.group(1), allow_plain=True) if match else ""


def _pack_text_illegal_claim_failures(text: str) -> list[str]:
    failures: list[str] = []
    patterns = {
        "first-10": r"(?im)(^|[^A-Za-z0-9_-])first[_-]?10[_-]?claim\s*[:=]\s*(true|yes|1)",
        "global promotion": r"(?im)(^|[^A-Za-z0-9_-])global[_-]?promotion[_-]?allowed\s*[:=]\s*(true|yes|1)",
        "public lift": r"(?im)(^|[^A-Za-z0-9_-])public[_-]?lift[_-]?claim\s*[:=]\s*(true|yes|1)",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, text or ""):
            failures.append(label)
    return failures


def _validate_pack_text(text: str, *, expected_pack_id: str, label: str) -> None:
    expected_pack_id = _safe_pack_id(expected_pack_id)
    if not str(text or "").strip():
        raise ValueError(f"{label} is empty")
    text_claim_failures = _pack_text_illegal_claim_failures(text)
    if text_claim_failures:
        raise ValueError(f"{label} contains illegal claim text: {', '.join(text_claim_failures)}")
    try:
        pack = parse_workflow_pack(text)
    except ValueError as exc:
        raise ValueError(f"{label} failed workflow pack schema validation: {exc}") from exc
    if str(pack.get("type") or "") != "workflow_pack":
        raise ValueError(f"{label} is not a workflow_pack")
    validation_errors = validate_pack(pack)
    if validation_errors:
        raise ValueError(f"{label} failed workflow pack proof validation: {'; '.join(validation_errors)}")
    _assert_no_illegal_claims(pack, f"{label}.pack")
    found_pack_id = _pack_slug_from_ref(pack.get("id"), allow_plain=True)
    if not found_pack_id:
        raise ValueError(f"{label} is missing pack id")
    if found_pack_id != expected_pack_id:
        raise ValueError(f"{label} pack id mismatch: expected {expected_pack_id}, found {found_pack_id}")


def _edit_artifacts_sha256(edits: Sequence[CandidateEdit]) -> str:
    return _sha256_ref(_canonical_json([edit.to_artifact() for edit in edits]))


def _edit_core_from_artifact(edit: dict[str, Any]) -> dict[str, Any]:
    return {
        "op": edit.get("op", ""),
        "anchor": edit.get("anchor", ""),
        "before_hash": edit.get("before_hash", ""),
        "after_hash": edit.get("after_hash", ""),
        "rationale": edit.get("rationale", ""),
        "supporting_receipt_ids": list(edit.get("supporting_receipt_ids", [])),
        "risk": edit.get("risk", ""),
        "expected_metric_impact": dict(edit.get("expected_metric_impact", {})),
    }


_ACCEPTED_EDIT_KEYS = set(_edit_core_from_artifact({}))
_REJECTED_EDIT_KEYS = _ACCEPTED_EDIT_KEYS | {"candidate_id", "pack_id", "created_at", "reason", "score_delta", "safety_result", "prevent_repeat_key"}
_ACCEPTED_BUFFER_KEYS = {"schema_version", "candidate_id", "pack_id", "edits"}
_REJECTED_BUFFER_KEYS = {"schema_version", "candidate_id", "pack_id", "rejections"}
_OPTIMIZER_RUN_KEYS = {
    "success",
    "candidate_id",
    "output_dir",
    "local_only",
    "recommendation",
    "score_delta",
    "hard_failures",
    "first_10_claim",
    "global_promotion_allowed",
    "schema_version",
    "pack_id",
    "created_at",
    "required_artifacts",
    "train_examples",
    "selection_example_refs",
    "hidden_example_refs",
    "train_examples_used_for_candidate",
    "selection_examples_withheld_from_candidate",
    "hidden_examples_not_used",
    "selection_evidence_sha256",
    "baseline_pack_sha256",
    "candidate_pack_sha256",
    "stored_preview_sha256",
    "rejected_memory_consulted",
    "rejected_memory_skipped_edits",
}
_SELECTION_SCORE_KEYS = {"schema_version", "candidate_id", "baseline_score", "candidate_score", "score_delta", "primary_metric", "hard_failures", "recommendation"}
_TRAINING_MANIFEST_KEYS = {"schema_version", "pack_id", "created_at", "source", "split_method", "seed_hash", "train_example_ids", "selection_example_ids", "hidden_example_ids", "privacy_policy", "first_10_claim"}
_PRIVACY_SCAN_KEYS = {"schema_version", "candidate_id", "passed", "blocked", "risk_score", "finding_classes"}
_PROMPT_SCAN_KEYS = {"schema_version", "candidate_id", "passed", "blocked", "score", "finding_classes"}
_INTEGRITY_KEYS = {
    "schema_version",
    "candidate_id",
    "candidate_id_algorithm",
    "candidate_id_material",
    "baseline_pack_sha256",
    "candidate_pack_sha256",
    "stored_preview_sha256",
    "patch_sha256",
    "selection_evidence",
    "selection_evidence_sha256",
    "accepted_edits_sha256",
    "rejected_edits_sha256",
    "training_manifest_sha256",
    "scan_blocked_raw_artifacts_suppressed",
}


def _assert_edit_buffer_shape_and_metadata(
    *,
    pack_id: str,
    accepted_edits: Sequence[dict[str, Any]],
    rejected_edits: Sequence[dict[str, Any]],
    selection_score: dict[str, Any],
    privacy_scan: dict[str, Any],
    prompt_injection_scan: dict[str, Any],
) -> None:
    for edit in accepted_edits:
        if set(edit) != _ACCEPTED_EDIT_KEYS:
            raise ValueError("accepted edit artifact shape mismatch")
    expected_reason = ",".join(selection_score.get("hard_failures") or []) or "selection_score_not_strictly_better"
    expected_safety = "failed" if (privacy_scan.get("blocked") or prompt_injection_scan.get("blocked")) else "passed"
    expected_score_delta = selection_score.get("score_delta")
    for edit in rejected_edits:
        if set(edit) != _REJECTED_EDIT_KEYS:
            raise ValueError("rejected edit artifact shape mismatch")
        if edit.get("candidate_id") != selection_score.get("candidate_id") or edit.get("pack_id") != pack_id:
            raise ValueError("rejected edit candidate/pack metadata mismatch")
        if not str(edit.get("created_at", "")).endswith("Z"):
            raise ValueError("rejected edit timestamp metadata mismatch")
        if edit.get("reason") != expected_reason:
            raise ValueError("rejected edit reason metadata mismatch")
        if edit.get("score_delta") != expected_score_delta:
            raise ValueError("rejected edit score metadata mismatch")
        if edit.get("safety_result") != expected_safety:
            raise ValueError("rejected edit safety metadata mismatch")
        expected_key = _sha256_ref(
            _canonical_json(
                {
                    "pack_id": pack_id,
                    "op": edit.get("op", ""),
                    "anchor": edit.get("anchor", ""),
                    "reason": selection_score.get("hard_failures") or [],
                }
            )
        )
        if edit.get("prevent_repeat_key") != expected_key:
            raise ValueError("rejected edit prevent-repeat metadata mismatch")


def _assert_no_illegal_claims(value: Any, path: str = "artifact") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key == "first_10_claim" and item is not False:
                raise ValueError(f"candidate illegally claims first-10 proof in {child_path}")
            if key == "global_promotion_allowed" and item is not False:
                raise ValueError(f"candidate illegally allows global promotion in {child_path}")
            if key == "public_lift_claim" and item is not False:
                raise ValueError(f"candidate illegally claims public lift in {child_path}")
            _assert_no_illegal_claims(item, child_path)
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _assert_no_illegal_claims(item, f"{path}[{idx}]")


def _example_ref(example: OptimizerExample) -> dict[str, str]:
    artifact = example.to_artifact()
    return {"example_id": example.example_id, "artifact_sha256": _sha256_ref(_canonical_json(artifact))}


def _privacy_artifact_from_scan(candidate_id: str, scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "passed": not scan.get("privacy_blocked"),
        "blocked": bool(scan.get("privacy_blocked")),
        "risk_score": scan.get("privacy_risk_score", 0),
        "finding_classes": scan.get("privacy_finding_classes", []),
    }


def _prompt_artifact_from_scan(candidate_id: str, scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "passed": not scan.get("prompt_injection_blocked"),
        "blocked": bool(scan.get("prompt_injection_blocked")),
        "score": scan.get("prompt_injection_score", 0),
        "finding_classes": scan.get("prompt_injection_classes", []),
    }


def _safe_metric_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    metrics: dict[str, float] = {}
    for key, raw in value.items():
        safe_key = _safe_text(key, 120)
        if not safe_key:
            continue
        try:
            metrics[safe_key] = round(max(0.0, min(1.0, float(raw))), 6)
        except (TypeError, ValueError):
            metrics[safe_key] = 0.0
    return metrics


def _safe_controls_map(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {_safe_text(key, 120): bool(raw) for key, raw in value.items() if _safe_text(key, 120)}


def _safe_failure_list(value: Any) -> list[str]:
    failures: list[str] = []
    for item in value or []:
        safe = _safe_text(item, 180)
        if safe:
            failures.append(safe)
    return failures


def _write_text_no_symlink(path: Path, text: str) -> None:
    """Write text without following a preexisting symlink at the destination."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if path.is_symlink():
        raise ValueError(f"refusing to write symlink artifact path: {path.name}")
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"refusing to write symlink artifact path: {path.name}") from exc
        raise
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _portable_display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _selection_taskset_from_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline_metrics": _safe_metric_map(evidence.get("baseline_metrics") or {}),
        "candidate_metrics": _safe_metric_map(evidence.get("candidate_metrics") or {}),
        "controls": _safe_controls_map(evidence.get("controls") or {}),
        "hard_failures": _safe_failure_list(evidence.get("hard_failures") or []),
        "candidate_metric_source": _safe_text(evidence.get("candidate_metric_source", "deterministic_selection_evaluator_with_taskset_caps"), 180),
    }


_REQUIRED_TASKSET_CONTROL_KEYS = ("unrelated_task_regression", "no_confident_match_regression", "unsafe_command_regression")


def _validated_taskset(taskset: Any, *, taskset_path: str | Path) -> dict[str, Any]:
    if not isinstance(taskset, dict):
        raise ValueError("selection taskset must be a JSON object")
    _assert_no_illegal_claims(taskset, "selection_taskset")
    if _safe_text(taskset.get("schema_version"), 40) != "1.0":
        raise ValueError("selection taskset requires schema_version=1.0")
    taskset_id = _safe_text(taskset.get("taskset_id"), 180)
    if not taskset_id:
        raise ValueError("selection taskset requires taskset_id")
    baseline = _safe_metric_map(taskset.get("baseline_metrics") or {})
    candidate_caps = _safe_metric_map(taskset.get("candidate_metrics") or {})
    missing_baseline = [key for key in WEIGHTS if key not in baseline]
    missing_candidate = [key for key in WEIGHTS if key not in candidate_caps]
    if missing_baseline:
        raise ValueError(f"selection taskset missing baseline metrics: {', '.join(missing_baseline)}")
    if missing_candidate:
        raise ValueError(f"selection taskset missing candidate metric caps: {', '.join(missing_candidate)}")
    controls = _safe_controls_map(taskset.get("controls") or {})
    missing_controls = [key for key in _REQUIRED_TASKSET_CONTROL_KEYS if key not in controls]
    if missing_controls:
        raise ValueError(f"selection taskset missing controls: {', '.join(missing_controls)}")
    validated = dict(taskset)
    validated["schema_version"] = "1.0"
    validated["taskset_id"] = taskset_id
    validated["baseline_metrics"] = baseline
    validated["candidate_metrics"] = candidate_caps
    validated["controls"] = controls
    validated["hard_failures"] = _safe_failure_list(taskset.get("hard_failures", []))
    return validated


class PackOptimizer:
    """Local-only pack optimizer with deterministic artifacts and hard gates."""

    def __init__(
        self,
        *,
        collective_db_path: str | Path | None = None,
        output_root: str | Path | None = None,
        rejected_memory_path: str | Path | None = None,
    ) -> None:
        self.collective_db_path = Path(collective_db_path) if collective_db_path else get_collective_learning_db_path()
        self.output_root = Path(output_root or "eval/pack_optimizer")
        self.rejected_memory = RejectedEditMemory(rejected_memory_path or (self.output_root / "rejected_edits_memory.jsonl"))
        self._last_rejected_memory_skips: list[dict[str, Any]] = []

    def load_pack_text(self, pack_id: str, pack_path: str | Path | None = None) -> tuple[str, Path | None]:
        pack_id = _safe_pack_id(pack_id)
        if pack_path:
            path = Path(pack_path)
            text = path.read_text(encoding="utf-8")
            _validate_pack_text(text, expected_pack_id=pack_id, label="baseline pack")
            return text, path
        package_root = Path(__file__).resolve().parents[1]
        candidates = [
            package_root / "seeds_data" / "packs" / f"{pack_id}.workflow.yaml",
            package_root / "seeds_data" / f"{pack_id}.md",
        ]
        for candidate in candidates:
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8")
                _validate_pack_text(text, expected_pack_id=pack_id, label="baseline pack")
                return text, candidate
        raise FileNotFoundError(f"pack not found: {pack_id}")

    def build_examples_from_collective_store(self, *, pack_id: str, require_shareable: bool = True) -> list[OptimizerExample]:
        pack_id = _safe_pack_id(pack_id)
        if not self.collective_db_path.exists():
            return []
        query = """
            SELECT
              i.intervention_id AS intervention_id,
              i.task_type AS task_type,
              i.error_class AS error_class,
              i.error_pattern AS error_pattern,
              i.guidance_redacted AS guidance_redacted,
              i.source_refs_json AS source_refs_json,
              o.receipt_id AS receipt_id,
              o.outcome AS outcome,
              o.helpful AS helpful,
              o.verified AS verified,
              o.verification_command_redacted AS verification_command_redacted,
              o.verification_exit_code AS verification_exit_code,
              o.verification_output_sha256 AS verification_output_sha256,
              o.trusted_tenant_id AS trusted_tenant_id,
              o.dead_ends_avoided AS dead_ends_avoided
            FROM outcome_receipts o
            JOIN interventions i ON i.intervention_id = o.intervention_id
            ORDER BY o.created_at ASC, o.receipt_id ASC
        """
        examples: list[OptimizerExample] = []
        with _connect(self.collective_db_path) as conn:
            intervention_columns = {row[1] for row in conn.execute("PRAGMA table_info(interventions)").fetchall()}
            outcome_columns = {row[1] for row in conn.execute("PRAGMA table_info(outcome_receipts)").fetchall()}
            required_intervention_columns = {"intervention_id", "task_type", "error_class", "error_pattern", "guidance_redacted", "source_refs_json"}
            required_outcome_columns = {
                "receipt_id",
                "intervention_id",
                "created_at",
                "outcome",
                "helpful",
                "verified",
                "verification_command_redacted",
                "verification_exit_code",
                "verification_output_sha256",
                "trusted_tenant_id",
                "dead_ends_avoided",
            }
            if not required_intervention_columns.issubset(intervention_columns) or not required_outcome_columns.issubset(outcome_columns):
                return []
            rows = conn.execute(query).fetchall()
        for row in rows:
            source_refs = _json_list(row["source_refs_json"])
            if not _source_refs_include_pack(source_refs, pack_id):
                continue
            verification_hash = _normalize_sha256_ref(row["verification_output_sha256"])
            trusted_id = _normalize_trusted_tenant_id(row["trusted_tenant_id"])
            if require_shareable and not (
                _bool(row["verified"])
                and _safe_text(row["verification_command_redacted"], 500)
                and row["verification_exit_code"] is not None
                and verification_hash
                and trusted_id
            ):
                continue
            task_class = ":".join(part for part in [_safe_text(row["task_type"], 80), _safe_text(row["error_class"], 120)] if part) or "unknown"
            action, stop, verify = _extract_guidance_parts(row["guidance_redacted"])
            verify = verify or _safe_text(row["verification_command_redacted"], 300)
            example = OptimizerExample(
                example_id="example-sha256:" + _sha256_text(f"{row['receipt_id']}:{row['intervention_id']}"),
                pack_id=pack_id,
                task_class=task_class,
                intervention_id=_safe_text(row["intervention_id"], 180),
                action_summary=action,
                stop_summary=stop,
                verify_summary=verify,
                outcome=_safe_text(row["outcome"], 80).lower() or "unknown",
                helpful=_bool(row["helpful"]),
                verified=_bool(row["verified"]),
                verification_exit_code=_int_or_none(row["verification_exit_code"]),
                verification_output_sha256=verification_hash,
                trusted_tenant_id=trusted_id,
                receipt_id=_safe_text(row["receipt_id"], 180),
                dead_ends_avoided=max(0, int(row["dead_ends_avoided"] or 0)),
            )
            if not _strong_example_failures(example, pack_id=pack_id):
                examples.append(example)
        return examples

    def split_examples(self, examples: Sequence[OptimizerExample], *, pack_id: str, seed: str = "borg-pack-optimizer-v1") -> SplitManifest:
        if len(examples) < 2:
            raise ValueError("optimizer requires at least two privacy-safe examples for train/selection split")
        ordered = sorted(examples, key=lambda ex: _sha256_text(f"{seed}:{pack_id}:{ex.example_id}"))
        if len(ordered) >= 5:
            train_count = max(2, int(len(ordered) * 0.6))
            selection_count = max(1, int(len(ordered) * 0.2))
            if train_count + selection_count >= len(ordered):
                selection_count = 1
                train_count = len(ordered) - 2
            train_items = ordered[:train_count]
            selection_items = ordered[train_count : train_count + selection_count]
            hidden_items = ordered[train_count + selection_count :]
        else:
            train_items = ordered[:-1]
            selection_items = ordered[-1:]
            hidden_items = []
        return SplitManifest(
            schema_version="1.0",
            pack_id=pack_id,
            created_at=_utc_now(),
            source="local_collective_learning_store_or_examples_file",
            split_method="sha256(task_id + seed) deterministic train/selection/hidden split; selection withheld from proposal",
            seed_hash=_sha256_ref(seed),
            train_example_ids=tuple(ex.example_id for ex in train_items),
            selection_example_ids=tuple(ex.example_id for ex in selection_items),
            hidden_example_ids=tuple(ex.example_id for ex in hidden_items),
        )

    def propose_candidate(
        self,
        *,
        pack_id: str,
        pack_text: str,
        examples: Sequence[OptimizerExample],
        max_edits: int = 4,
        rejected_memory_skips: Sequence[dict[str, Any]] | None = None,
    ) -> tuple[str, list[CandidateEdit]]:
        if max_edits < 1 or max_edits > 12:
            raise ValueError("max_edits must be between 1 and 12")
        before_hash = _sha256_ref(pack_text)
        helpful = [ex for ex in examples if ex.helpful and ex.verified]
        negative = [ex for ex in examples if (not ex.helpful) or ex.outcome == "failure"]
        notes_by_key: dict[tuple[str, str], str] = {}
        edit_specs: list[tuple[str, str, str, tuple[str, ...], dict[str, float]]] = []
        if negative:
            receipts = tuple(ex.receipt_id for ex in negative if ex.receipt_id)[:5]
            note = "Tighten NO_CONFIDENT_MATCH: return no confident match instead of forcing weak or unrelated guidance."
            notes_by_key[("tighten_no_confident_match_rule", "NO_CONFIDENT_MATCH")] = note
            edit_specs.append(("tighten_no_confident_match_rule", "NO_CONFIDENT_MATCH", "reduce weak unrelated guidance", receipts, {"no_confident_match_precision": 0.15}))
        if helpful:
            receipts = tuple(ex.receipt_id for ex in helpful if ex.receipt_id)[:5]
            note = "Prefer ACTION / STOP / VERIFY guidance backed by verified command evidence and output hashes."
            notes_by_key[("add_verification_step", "VERIFY")] = note
            edit_specs.append(("add_verification_step", "VERIFY", "raise verification evidence quality", receipts, {"verification_quality": 0.10, "verified_success": 0.10}))
        if any(ex.dead_ends_avoided > 0 for ex in helpful):
            receipts = tuple(ex.receipt_id for ex in helpful if ex.dead_ends_avoided > 0 and ex.receipt_id)[:5]
            note = "Preserve STOP guidance that avoids repeated dead ends when outcome receipts verify it helped."
            notes_by_key[("tighten_stop_rule", "STOP")] = note
            edit_specs.append(("tighten_stop_rule", "STOP", "preserve verified dead-end avoidance", receipts, {"dead_ends_avoided": 0.15}))
        if not edit_specs:
            note = "Keep local optimizer candidate empty until verified examples support a bounded edit."
            notes_by_key[("add_antipattern", "LOCAL_ONLY")] = note
            edit_specs.append(("add_antipattern", "LOCAL_ONLY", "insufficient verified evidence placeholder", tuple(), {}))

        explicit_skip_keys = {
            (str(item.get("op", "")), str(item.get("anchor", ""))): dict(item)
            for item in (rejected_memory_skips or [])
            if isinstance(item, dict)
        }
        selected_specs: list[tuple[str, str, str, tuple[str, ...], dict[str, float]]] = []
        skipped: list[dict[str, Any]] = []
        for spec in edit_specs:
            op, anchor, _, _, _ = spec
            skip_record = explicit_skip_keys.get((op, anchor))
            if skip_record is None and rejected_memory_skips is None:
                skip_record = self.rejected_memory.skipped_artifact(pack_id=pack_id, op=op, anchor=anchor)
            if skip_record:
                skipped.append({
                    "op": _safe_text(skip_record.get("op") or op, 140),
                    "anchor": _safe_text(skip_record.get("anchor") or anchor, 140),
                    "reason": _safe_text(skip_record.get("reason") or "previously_rejected", 300),
                    "prevent_repeat_key": _safe_text(skip_record.get("prevent_repeat_key"), 120),
                    "last_rejected_candidate_id": _safe_text(skip_record.get("last_rejected_candidate_id"), 120),
                })
                continue
            selected_specs.append(spec)
            if len(selected_specs) >= max_edits:
                break
        self._last_rejected_memory_skips = skipped

        selected_notes = [notes_by_key[(op, anchor)] for op, anchor, _, _, _ in selected_specs if (op, anchor) in notes_by_key]
        if not selected_specs:
            return pack_text, []
        note_lines = "\n".join(f"  - \"{_safe_text(note, 220)}\"" for note in selected_notes[:max_edits])
        candidate_block = (
            "\n# Borg local pack optimizer candidate — local-only, not global promotion.\n"
            "# Generated from privacy-safe verified outcome summaries; first-10 claims remain false.\n"
            "optimizer_candidate_notes:\n"
            f"{note_lines}\n"
        )
        candidate_text = pack_text.rstrip() + "\n" + candidate_block
        after_hash = _sha256_ref(candidate_text)
        edits = [
            CandidateEdit(
                op=op,
                anchor=anchor,
                before_hash=before_hash,
                after_hash=after_hash,
                rationale=rationale,
                supporting_receipt_ids=receipts,
                expected_metric_impact=impact,
            )
            for op, anchor, rationale, receipts, impact in selected_specs
        ]
        return candidate_text, edits

    def _compute_candidate_metrics(self, *, candidate_text: str, edits: Sequence[CandidateEdit], selection_examples: Sequence[OptimizerExample], taskset: dict[str, Any]) -> dict[str, float]:
        text = candidate_text.upper()
        has_action_stop_verify = "ACTION" in text and "STOP" in text and "VERIFY" in text
        has_no_confident = "NO_CONFIDENT_MATCH" in text or "NO CONFIDENT MATCH" in text
        has_stop = "STOP" in text
        has_unsafe = any(token in text for token in ("SUDO PIP", "RM -RF", "CURL | SH", "CHMOD 777"))
        verified = [ex for ex in selection_examples if ex.verified]
        denominator = max(1, len(verified))
        matched = 0
        for example in verified:
            if example.helpful and has_action_stop_verify:
                matched += 1
            elif (not example.helpful or example.outcome == "failure") and has_no_confident:
                matched += 1
        candidate_metrics = {
            "verified_success": matched / denominator,
            "action_stop_verify_relevance": 1.0 if has_action_stop_verify else 0.0,
            "dead_ends_avoided": 1.0 if has_stop and any(ex.dead_ends_avoided > 0 for ex in selection_examples) else 0.6 if has_stop else 0.0,
            "no_confident_match_precision": 1.0 if (not any((not ex.helpful) or ex.outcome == "failure" for ex in selection_examples) or has_no_confident) else 0.0,
            "verification_quality": 1.0 if has_action_stop_verify and all(ex.verification_output_sha256 for ex in selection_examples) else 0.0,
            "token_or_tool_efficiency": 0.7 if 0 < len(edits) <= 4 else 0.4 if edits else 0.0,
        }
        if has_unsafe:
            candidate_metrics["verified_success"] = 0.0
            controls = dict(taskset.get("controls") or {})
            controls["unsafe_command_regression"] = True
            taskset["controls"] = controls
        declared = taskset.get("candidate_metrics") or {}
        for key in WEIGHTS:
            if key in declared:
                try:
                    candidate_metrics[key] = min(candidate_metrics[key], float(declared[key]))
                except (TypeError, ValueError):
                    candidate_metrics[key] = 0.0
        return {key: round(max(0.0, min(1.0, float(value))), 6) for key, value in candidate_metrics.items()}

    def build_selection_evidence(
        self,
        *,
        taskset_path: str | Path,
        scan: dict[str, Any],
        candidate_text: str,
        edits: Sequence[CandidateEdit],
        selection_examples: Sequence[OptimizerExample],
    ) -> dict[str, Any]:
        taskset_text = Path(taskset_path).read_text(encoding="utf-8")
        taskset = _validated_taskset(json.loads(taskset_text), taskset_path=taskset_path)
        failures = list(taskset.get("hard_failures", []))
        if scan.get("privacy_blocked"):
            failures.append("privacy_scan_failed")
        if scan.get("prompt_injection_blocked"):
            failures.append("prompt_injection_scan_failed")
        taskset["hard_failures"] = failures
        taskset["baseline_metrics"] = _safe_metric_map(taskset.get("baseline_metrics") or {})
        taskset["candidate_metrics"] = _safe_metric_map(taskset.get("candidate_metrics") or {})
        taskset["controls"] = _safe_controls_map(taskset.get("controls") or {})
        candidate_metrics = self._compute_candidate_metrics(candidate_text=candidate_text, edits=edits, selection_examples=selection_examples, taskset=taskset)
        selection_example_artifact_hashes = [_example_ref(example) for example in selection_examples]
        return {
            "schema_version": "1.0",
            "evaluator_version": "deterministic_selection_evaluator_with_taskset_caps/v1",
            "taskset_sha256": _sha256_ref(taskset_text),
            "taskset_id": _safe_text(taskset.get("taskset_id") or Path(taskset_path).name, 180),
            "baseline_metrics": dict(taskset.get("baseline_metrics") or {}),
            "candidate_metrics": candidate_metrics,
            "controls": dict(taskset.get("controls") or {}),
            "hard_failures": failures,
            "candidate_metric_source": "deterministic_selection_evaluator_with_taskset_caps",
            "selection_example_ids": [example.example_id for example in selection_examples],
            "selection_example_refs": selection_example_artifact_hashes,
        }

    def evaluate_candidate(self, *, candidate_id: str, selection_evidence: dict[str, Any]) -> SelectionScore:
        return compare_baseline_candidate(_selection_taskset_from_evidence(selection_evidence), candidate_id)

    def _candidate_dir(self, candidate_id: str) -> Path:
        if not _CANDIDATE_ID_RE.match(str(candidate_id)):
            raise ValueError("candidate_id must be packopt-sha256:<64 hex>")
        root = self.output_root.resolve()
        candidate_dirname = str(candidate_id).replace(":", "_")
        candidate_dir = root / candidate_dirname
        if candidate_dir.exists() and candidate_dir.is_symlink():
            raise ValueError("candidate artifact directory must not be a symlink")
        resolved = candidate_dir.resolve() if candidate_dir.exists() else candidate_dir.parent.resolve() / candidate_dir.name
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError("candidate_id resolves outside optimizer output root") from exc
        return candidate_dir

    def _candidate_display_dir(self, candidate_id: str) -> str:
        candidate_dirname = str(candidate_id).replace(":", "_")
        display_path = self.output_root / candidate_dirname
        return _portable_display_path(display_path)

    def write_artifacts(
        self,
        *,
        pack_id: str,
        pack_text: str,
        candidate_text: str,
        candidate_id: str,
        candidate_material: dict[str, Any],
        edits: Sequence[CandidateEdit],
        examples: Sequence[OptimizerExample],
        manifest: SplitManifest,
        scan: dict[str, Any],
        score: SelectionScore,
        selection_evidence: dict[str, Any],
        local_only: bool,
        rejected_memory_skipped_edits: Sequence[dict[str, Any]] = (),
    ) -> OptimizerRunResult:
        candidate_dir = self._candidate_dir(candidate_id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        scan_blocked = bool(scan.get("blockers"))
        if scan_blocked:
            patch = _SUPPRESSED_PATCH_TEXT
            preview = _SUPPRESSED_PREVIEW_TEXT
        else:
            patch = _unified_diff(pack_id, pack_text, candidate_text)
            preview = candidate_text
        accepted = [edit.to_artifact() for edit in edits] if score.passed and not scan_blocked else []
        rejected = [] if accepted else [
            {
                **edit.to_artifact(),
                "candidate_id": candidate_id,
                "pack_id": pack_id,
                "created_at": _utc_now(),
                "reason": ",".join(score.hard_failures) or "selection_score_not_strictly_better",
                "score_delta": score.score_delta,
                "safety_result": "failed" if scan.get("blockers") else "passed",
                "prevent_repeat_key": _sha256_ref(_canonical_json({"pack_id": pack_id, "op": edit.op, "anchor": edit.anchor, "reason": score.hard_failures})),
            }
            for edit in edits
        ]
        accepted_artifact = {"schema_version": "1.0", "candidate_id": candidate_id, "pack_id": pack_id, "edits": accepted}
        rejected_artifact = {"schema_version": "1.0", "candidate_id": candidate_id, "pack_id": pack_id, "rejections": rejected}
        if rejected:
            for rejection in rejected:
                reason = str(rejection.get("reason") or "selection_score_not_strictly_better")
                if "hidden" in reason.lower():
                    continue
                self.rejected_memory.record_rejection(
                    pack_id=pack_id,
                    op=str(rejection.get("op") or "add_antipattern"),
                    anchor=str(rejection.get("anchor") or "LOCAL_ONLY"),
                    reason=reason,
                    candidate_id=candidate_id,
                    supporting_receipt_ids=list(rejection.get("supporting_receipt_ids") or []),
                )
        manifest_artifact = manifest.to_artifact()
        score_artifact = score.to_artifact()
        privacy_artifact = _privacy_artifact_from_scan(candidate_id, scan)
        prompt_artifact = _prompt_artifact_from_scan(candidate_id, scan)
        selection_evidence_sha256 = _sha256_ref(_canonical_json(selection_evidence))
        integrity_artifact = {
            "schema_version": "1.0",
            "candidate_id": candidate_id,
            "candidate_id_algorithm": "sha256(canonical candidate_id_material)",
            "candidate_id_material": candidate_material,
            "baseline_pack_sha256": _sha256_ref(pack_text),
            "candidate_pack_sha256": _sha256_ref(candidate_text),
            "stored_preview_sha256": _sha256_ref(preview),
            "patch_sha256": _sha256_ref(patch),
            "selection_evidence": selection_evidence,
            "selection_evidence_sha256": selection_evidence_sha256,
            "accepted_edits_sha256": _sha256_ref(_canonical_json(accepted_artifact)),
            "rejected_edits_sha256": _sha256_ref(_canonical_json(rejected_artifact)),
            "training_manifest_sha256": _sha256_ref(_canonical_json(manifest_artifact)),
            "scan_blocked_raw_artifacts_suppressed": scan_blocked,
        }
        result = OptimizerRunResult(
            success=bool(score.passed and not scan_blocked),
            candidate_id=candidate_id,
            output_dir=self._candidate_display_dir(candidate_id),
            local_only=local_only,
            recommendation=score.recommendation if not scan_blocked else "reject",
            score_delta=score.score_delta,
            hard_failures=tuple(score.hard_failures) if not scan_blocked else tuple(sorted(set(score.hard_failures + tuple(scan.get("blockers", []))))),
        )
        examples_by_id = {example.example_id: example for example in examples}
        train_examples_for_artifact = [examples_by_id[example_id].to_artifact() for example_id in manifest.train_example_ids if example_id in examples_by_id]
        selection_example_refs = [_example_ref(examples_by_id[example_id]) for example_id in manifest.selection_example_ids if example_id in examples_by_id]
        hidden_example_refs = [_example_ref(examples_by_id[example_id]) for example_id in manifest.hidden_example_ids if example_id in examples_by_id]
        optimizer_run = {
            **result.to_artifact(),
            "schema_version": "1.0",
            "pack_id": pack_id,
            "created_at": _utc_now(),
            "required_artifacts": list(REQUIRED_ARTIFACTS),
            "train_examples": train_examples_for_artifact,
            "selection_example_refs": selection_example_refs,
            "hidden_example_refs": hidden_example_refs,
            "train_examples_used_for_candidate": list(manifest.train_example_ids),
            "selection_examples_withheld_from_candidate": list(manifest.selection_example_ids),
            "hidden_examples_not_used": list(manifest.hidden_example_ids),
            "selection_evidence_sha256": selection_evidence_sha256,
            "baseline_pack_sha256": _sha256_ref(pack_text),
            "candidate_pack_sha256": _sha256_ref(candidate_text),
            "stored_preview_sha256": _sha256_ref(preview),
            "rejected_memory_consulted": True,
            "rejected_memory_skipped_edits": [dict(item) for item in rejected_memory_skipped_edits],
        }
        artifacts = {
            "candidate_pack.patch": patch,
            "candidate_pack.preview": preview,
            "accepted_edits.json": accepted_artifact,
            "rejected_edits.json": rejected_artifact,
            "training_manifest.json": manifest_artifact,
            "selection_score.json": score_artifact,
            "privacy_scan.json": privacy_artifact,
            "prompt_injection_scan.json": prompt_artifact,
            "candidate_integrity.json": integrity_artifact,
            "optimizer_run.json": optimizer_run,
        }
        for name, value in artifacts.items():
            path = candidate_dir / name
            if isinstance(value, str):
                payload = value
            else:
                payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            _write_text_no_symlink(path, payload)
        return result

    def run(
        self,
        *,
        pack_id: str,
        taskset_path: str | Path,
        pack_path: str | Path | None = None,
        examples: Sequence[OptimizerExample | dict[str, Any]] | None = None,
        local_only: bool = True,
        max_edits: int = 4,
    ) -> OptimizerRunResult:
        pack_id = _safe_pack_id(pack_id)
        if not local_only:
            raise ValueError("pack optimizer is local-only in this release")
        if examples is None:
            safe_examples = self.build_examples_from_collective_store(pack_id=pack_id, require_shareable=True)
        else:
            safe_examples = [sanitize_training_record(ex.to_artifact() if isinstance(ex, OptimizerExample) else ex) for ex in examples]
        safe_examples = _validated_examples(safe_examples, pack_id=pack_id)
        manifest = self.split_examples(safe_examples, pack_id=pack_id)
        examples_by_id = {example.example_id: example for example in safe_examples}
        train_examples = [examples_by_id[example_id] for example_id in manifest.train_example_ids]
        selection_examples = [examples_by_id[example_id] for example_id in manifest.selection_example_ids]
        hidden_examples = [examples_by_id[example_id] for example_id in manifest.hidden_example_ids]
        pack_text, _ = self.load_pack_text(pack_id, pack_path)
        candidate_text, edits = self.propose_candidate(pack_id=pack_id, pack_text=pack_text, examples=train_examples, max_edits=max_edits)
        rejected_memory_skipped_edits = list(self._last_rejected_memory_skips)
        _validate_pack_text(candidate_text, expected_pack_id=pack_id, label="candidate preview")
        scan = scan_candidate_text(candidate_text)
        selection_evidence = self.build_selection_evidence(taskset_path=taskset_path, scan=scan, candidate_text=candidate_text, edits=edits, selection_examples=selection_examples)
        candidate_material = _candidate_id_material(
            pack_id=pack_id,
            pack_text=pack_text,
            candidate_text=candidate_text,
            train_examples=train_examples,
            hidden_examples=hidden_examples,
            edits=edits,
            max_edits=max_edits,
            selection_evidence=selection_evidence,
            rejected_memory_skipped_edits=rejected_memory_skipped_edits,
        )
        candidate_id = _candidate_id_from_material(candidate_material)
        score = self.evaluate_candidate(candidate_id=candidate_id, selection_evidence=selection_evidence)
        if not edits:
            score = SelectionScore(
                candidate_id=score.candidate_id,
                baseline_score=score.baseline_score,
                candidate_score=score.candidate_score,
                score_delta=score.score_delta,
                primary_metric=score.primary_metric,
                hard_failures=tuple(sorted(set(score.hard_failures + ("all_candidate_edits_previously_rejected",)))),
                recommendation="reject",
            )
        return self.write_artifacts(
            pack_id=pack_id,
            pack_text=pack_text,
            candidate_text=candidate_text,
            candidate_id=candidate_id,
            candidate_material=candidate_material,
            edits=edits,
            examples=safe_examples,
            manifest=manifest,
            scan=scan,
            score=score,
            selection_evidence=selection_evidence,
            local_only=local_only,
            rejected_memory_skipped_edits=rejected_memory_skipped_edits,
        )

    def _load_candidate_bundle(self, candidate_id: str) -> dict[str, Any]:
        candidate_dir = self._candidate_dir(candidate_id)
        if not candidate_dir.exists():
            raise FileNotFoundError(f"candidate not found: {candidate_id}")
        missing = [name for name in REQUIRED_ARTIFACTS if not (candidate_dir / name).exists()]
        if missing:
            raise ValueError("candidate artifact bundle incomplete: " + ", ".join(missing))

        def load_json(name: str) -> Any:
            return json.loads((candidate_dir / name).read_text(encoding="utf-8"))

        bundle = {
            "success": True,
            "candidate_id": candidate_id,
            "output_dir": str(candidate_dir),
            "optimizer_run": load_json("optimizer_run.json"),
            "selection_score": load_json("selection_score.json"),
            "accepted_edits": load_json("accepted_edits.json"),
            "rejected_edits": load_json("rejected_edits.json"),
            "training_manifest": load_json("training_manifest.json"),
            "privacy_scan": load_json("privacy_scan.json"),
            "prompt_injection_scan": load_json("prompt_injection_scan.json"),
            "candidate_integrity": load_json("candidate_integrity.json"),
        }
        self._verify_candidate_bundle(candidate_id, candidate_dir, bundle)
        return bundle

    def _verify_candidate_bundle(self, candidate_id: str, candidate_dir: Path, bundle: dict[str, Any]) -> None:
        id_fields = [
            bundle["optimizer_run"].get("candidate_id"),
            bundle["selection_score"].get("candidate_id"),
            bundle["accepted_edits"].get("candidate_id"),
            bundle["rejected_edits"].get("candidate_id"),
            bundle["privacy_scan"].get("candidate_id"),
            bundle["prompt_injection_scan"].get("candidate_id"),
            bundle["candidate_integrity"].get("candidate_id"),
        ]
        if any(value != candidate_id for value in id_fields):
            raise ValueError("candidate artifact bundle candidate_id mismatch")
        integrity = bundle["candidate_integrity"]
        material = integrity.get("candidate_id_material") or {}
        if _candidate_id_from_material(material) != candidate_id:
            raise ValueError("candidate integrity hash mismatch")
        pack_id = _safe_pack_id(material.get("pack_id") or "")
        shape_expectations = {
            "optimizer_run": _OPTIMIZER_RUN_KEYS,
            "selection_score": _SELECTION_SCORE_KEYS,
            "accepted_edits": _ACCEPTED_BUFFER_KEYS,
            "rejected_edits": _REJECTED_BUFFER_KEYS,
            "training_manifest": _TRAINING_MANIFEST_KEYS,
            "privacy_scan": _PRIVACY_SCAN_KEYS,
            "prompt_injection_scan": _PROMPT_SCAN_KEYS,
            "candidate_integrity": _INTEGRITY_KEYS,
        }
        for artifact_name, expected_keys in shape_expectations.items():
            if set(bundle[artifact_name]) != expected_keys:
                raise ValueError(f"{artifact_name} artifact shape mismatch")
        if bundle["optimizer_run"].get("pack_id") != pack_id or bundle["accepted_edits"].get("pack_id") != pack_id or bundle["rejected_edits"].get("pack_id") != pack_id:
            raise ValueError("candidate artifact bundle pack_id mismatch")
        _assert_no_illegal_claims(bundle)
        if _sha256_ref(_canonical_json(bundle["accepted_edits"])) != integrity.get("accepted_edits_sha256"):
            raise ValueError("accepted edits artifact hash mismatch")
        if _sha256_ref(_canonical_json(bundle["rejected_edits"])) != integrity.get("rejected_edits_sha256"):
            raise ValueError("rejected edits artifact hash mismatch")
        if _sha256_ref(_canonical_json(bundle["training_manifest"])) != integrity.get("training_manifest_sha256"):
            raise ValueError("training manifest artifact hash mismatch")
        manifest = bundle["training_manifest"]
        if list(manifest.get("train_example_ids", [])) != list(material.get("train_example_ids", [])):
            raise ValueError("candidate train split mismatch")
        if list(bundle["optimizer_run"].get("train_examples_used_for_candidate", [])) != list(material.get("train_example_ids", [])):
            raise ValueError("optimizer_run train split mismatch")
        actual_train_refs = [
            {"example_id": item.get("example_id", ""), "artifact_sha256": _sha256_ref(_canonical_json(item))}
            for item in bundle["optimizer_run"].get("train_examples", [])
            if isinstance(item, dict)
        ]
        if actual_train_refs != list(material.get("train_example_refs", [])):
            raise ValueError("candidate train example artifact hash mismatch")
        if list(manifest.get("selection_example_ids", [])) != list(material.get("selection_example_ids", [])):
            raise ValueError("candidate selection split mismatch")
        if list(manifest.get("hidden_example_ids", [])) != list(material.get("hidden_example_ids", [])):
            raise ValueError("candidate hidden split mismatch")
        if list(bundle["optimizer_run"].get("selection_examples_withheld_from_candidate", [])) != list(material.get("selection_example_ids", [])):
            raise ValueError("optimizer_run selection split mismatch")
        if list(bundle["optimizer_run"].get("hidden_examples_not_used", [])) != list(material.get("hidden_example_ids", [])):
            raise ValueError("optimizer_run hidden split mismatch")
        selection_refs = bundle["optimizer_run"].get("selection_example_refs", [])
        hidden_refs = bundle["optimizer_run"].get("hidden_example_refs", [])
        if any(set(ref) != {"example_id", "artifact_sha256"} for ref in selection_refs if isinstance(ref, dict)) or len(selection_refs) != len([ref for ref in selection_refs if isinstance(ref, dict)]):
            raise ValueError("selection example refs must be ref-only")
        if any(set(ref) != {"example_id", "artifact_sha256"} for ref in hidden_refs if isinstance(ref, dict)) or len(hidden_refs) != len([ref for ref in hidden_refs if isinstance(ref, dict)]):
            raise ValueError("hidden example refs must be ref-only")
        if list(selection_refs) != list(material.get("selection_example_refs", [])):
            raise ValueError("candidate selection example ref mismatch")
        if list(hidden_refs) != list(material.get("hidden_example_refs", [])):
            raise ValueError("candidate hidden example ref mismatch")
        accepted_edit_list = bundle["accepted_edits"].get("edits", [])
        rejected_edit_list = bundle["rejected_edits"].get("rejections", [])
        _assert_edit_buffer_shape_and_metadata(
            pack_id=pack_id,
            accepted_edits=[edit for edit in accepted_edit_list if isinstance(edit, dict)],
            rejected_edits=[edit for edit in rejected_edit_list if isinstance(edit, dict)],
            selection_score=bundle["selection_score"],
            privacy_scan=bundle["privacy_scan"],
            prompt_injection_scan=bundle["prompt_injection_scan"],
        )
        if len(accepted_edit_list) != len([edit for edit in accepted_edit_list if isinstance(edit, dict)]):
            raise ValueError("accepted edit artifact shape mismatch")
        if len(rejected_edit_list) != len([edit for edit in rejected_edit_list if isinstance(edit, dict)]):
            raise ValueError("rejected edit artifact shape mismatch")
        if bundle["selection_score"].get("recommendation") == "eligible_for_manual_review":
            if not accepted_edit_list:
                raise ValueError("eligible candidate must have accepted edits")
            if rejected_edit_list:
                raise ValueError("eligible candidate cannot move accepted edits into rejected buffer")
            edit_source = accepted_edit_list
        else:
            if accepted_edit_list:
                raise ValueError("rejected candidate cannot have accepted edits")
            edit_source = rejected_edit_list
        edit_artifact_hash = _sha256_ref(_canonical_json([_edit_core_from_artifact(edit) for edit in edit_source if isinstance(edit, dict)]))
        if edit_artifact_hash != material.get("edit_artifacts_sha256"):
            raise ValueError("candidate edit artifact hash mismatch")

        preview = (candidate_dir / "candidate_pack.preview").read_text(encoding="utf-8")
        patch = (candidate_dir / "candidate_pack.patch").read_text(encoding="utf-8")
        preview_hash = _sha256_ref(preview)
        patch_hash = _sha256_ref(patch)
        scan_blocked = bool(integrity.get("scan_blocked_raw_artifacts_suppressed"))
        _assert_no_artifact_leaks(
            {
                "candidate_pack.preview": preview,
                "candidate_pack.patch": patch,
                "optimizer_run.json": _canonical_json(bundle["optimizer_run"]),
                "accepted_edits.json": _canonical_json(bundle["accepted_edits"]),
                "rejected_edits.json": _canonical_json(bundle["rejected_edits"]),
                "training_manifest.json": _canonical_json(bundle["training_manifest"]),
                "selection_score.json": _canonical_json(bundle["selection_score"]),
                "privacy_scan.json": _canonical_json(bundle["privacy_scan"]),
                "prompt_injection_scan.json": _canonical_json(bundle["prompt_injection_scan"]),
                "candidate_integrity.json": _canonical_json(bundle["candidate_integrity"]),
            }
        )
        if integrity.get("baseline_pack_sha256") != material.get("baseline_pack_sha256") or bundle["optimizer_run"].get("baseline_pack_sha256") != material.get("baseline_pack_sha256"):
            raise ValueError("candidate baseline hash mismatch")
        if patch_hash != integrity.get("patch_sha256"):
            raise ValueError("candidate patch hash mismatch")
        if preview_hash != integrity.get("stored_preview_sha256") or bundle["optimizer_run"].get("stored_preview_sha256") != preview_hash:
            raise ValueError("candidate preview hash mismatch")

        if scan_blocked:
            if preview != _SUPPRESSED_PREVIEW_TEXT or patch != _SUPPRESSED_PATCH_TEXT:
                raise ValueError("scan-blocked candidate must suppress raw preview and patch")
            if not (bundle["privacy_scan"].get("blocked") or bundle["prompt_injection_scan"].get("blocked")):
                raise ValueError("suppressed candidate must record a blocking scan")
            if bundle["accepted_edits"].get("edits"):
                raise ValueError("scan-blocked candidate cannot have accepted edits")
            if bundle["optimizer_run"].get("success") is not False:
                raise ValueError("scan-blocked candidate must be unsuccessful")
        else:
            if preview_hash != material.get("candidate_pack_sha256") or preview_hash != integrity.get("candidate_pack_sha256"):
                raise ValueError("candidate preview hash mismatch")
            if bundle["optimizer_run"].get("candidate_pack_sha256") != preview_hash:
                raise ValueError("optimizer_run preview hash mismatch")
            _validate_pack_text(preview, expected_pack_id=pack_id, label="candidate preview")
            recomputed_scan = scan_candidate_text(preview)
            if _canonical_json(bundle["privacy_scan"]) != _canonical_json(_privacy_artifact_from_scan(candidate_id, recomputed_scan)):
                raise ValueError("privacy scan artifact mismatch")
            if _canonical_json(bundle["prompt_injection_scan"]) != _canonical_json(_prompt_artifact_from_scan(candidate_id, recomputed_scan)):
                raise ValueError("prompt-injection scan artifact mismatch")

        selection_evidence = integrity.get("selection_evidence") or {}
        selection_evidence_sha256 = _sha256_ref(_canonical_json(selection_evidence))
        if selection_evidence_sha256 != integrity.get("selection_evidence_sha256") or selection_evidence_sha256 != material.get("selection_evidence_sha256"):
            raise ValueError("selection evidence hash mismatch")
        if bundle["optimizer_run"].get("selection_evidence_sha256") != selection_evidence_sha256:
            raise ValueError("optimizer_run selection evidence hash mismatch")
        if list(selection_evidence.get("selection_example_ids", [])) != list(material.get("selection_example_ids", [])):
            raise ValueError("selection evidence split mismatch")
        if list(selection_evidence.get("selection_example_refs", [])) != list(material.get("selection_example_refs", [])):
            raise ValueError("selection evidence ref mismatch")
        expected_score = compare_baseline_candidate(_selection_taskset_from_evidence(selection_evidence), candidate_id).to_artifact()
        if _canonical_json(bundle["selection_score"]) != _canonical_json(expected_score):
            raise ValueError("selection score integrity mismatch")

        if not bundle["optimizer_run"].get("local_only"):
            raise ValueError("candidate was not generated as local-only")
        if bundle["optimizer_run"].get("first_10_claim") is not False:
            raise ValueError("candidate illegally claims first-10 proof")
        if bundle["optimizer_run"].get("global_promotion_allowed") is not False:
            raise ValueError("candidate illegally allows global promotion")
        if bundle["optimizer_run"].get("recommendation") != bundle["selection_score"].get("recommendation"):
            raise ValueError("optimizer_run recommendation mismatch")
        for edit in bundle["accepted_edits"].get("edits", []):
            if edit.get("op") not in _ALLOWED_EDIT_OPS:
                raise ValueError("candidate contains unsupported edit op")
            if edit.get("before_hash") != material.get("baseline_pack_sha256"):
                raise ValueError("accepted edit baseline hash mismatch")
            if edit.get("after_hash") != integrity.get("candidate_pack_sha256"):
                raise ValueError("accepted edit hash mismatch")

    def inspect_candidate(self, candidate_id: str) -> dict[str, Any]:
        data = self._load_candidate_bundle(candidate_id)
        data["source_verified"] = False
        data["manual_review_eligibility"] = "source_verification_required"
        return data

    def verify_candidate_against_sources(
        self,
        candidate_id: str,
        *,
        pack_path: str | Path,
        taskset_path: str | Path | None = None,
        examples: Sequence[OptimizerExample] | None = None,
        scope: str = "local",
    ) -> dict[str, Any]:
        bundle, _, path = self._verify_candidate_against_sources(
            candidate_id,
            pack_path=pack_path,
            taskset_path=taskset_path,
            examples=examples,
            scope=scope,
        )
        data = dict(bundle)
        data["source_verified"] = True
        data["source_pack_path"] = str(path)
        data["manual_review_eligibility"] = (
            "eligible_for_manual_review"
            if data["selection_score"].get("recommendation") == "eligible_for_manual_review"
            else "not_eligible"
        )
        return data

    def _verify_candidate_against_sources(
        self,
        candidate_id: str,
        *,
        pack_path: str | Path,
        taskset_path: str | Path | None = None,
        examples: Sequence[OptimizerExample] | None = None,
        scope: str = "local",
    ) -> tuple[dict[str, Any], str, Path]:
        self._candidate_dir(candidate_id)
        if scope != "local":
            raise ValueError("pack optimizer is local-only; global apply/promotion is blocked")
        if not pack_path:
            raise ValueError("candidate source verification requires --pack-file")
        if not taskset_path:
            raise ValueError("candidate source verification requires --taskset")
        if examples is None:
            raise ValueError("candidate source verification requires --examples-file")
        bundle = self._load_candidate_bundle(candidate_id)
        score = bundle["selection_score"]
        privacy = bundle["privacy_scan"]
        injection = bundle["prompt_injection_scan"]
        integrity = bundle["candidate_integrity"]
        material = integrity.get("candidate_id_material") or {}
        pack_id = _safe_pack_id(material.get("pack_id") or "")
        if score.get("recommendation") != "eligible_for_manual_review":
            raise ValueError("cannot apply rejected optimizer candidate; not eligible for manual review")
        if privacy.get("blocked") or not privacy.get("passed"):
            raise ValueError("candidate failed privacy scan")
        if injection.get("blocked") or not injection.get("passed"):
            raise ValueError("candidate failed prompt-injection scan")
        if integrity.get("scan_blocked_raw_artifacts_suppressed"):
            raise ValueError("candidate has suppressed raw artifacts")
        candidate_dir = self._candidate_dir(candidate_id)
        preview = (candidate_dir / "candidate_pack.preview").read_text(encoding="utf-8")
        if _sha256_ref(preview) != integrity.get("candidate_pack_sha256"):
            raise ValueError("candidate preview does not match candidate hash")
        path = Path(pack_path)
        if not path.exists():
            raise FileNotFoundError("pack file must already exist for source verification")
        current_text = path.read_text(encoding="utf-8")
        _validate_pack_text(current_text, expected_pack_id=pack_id, label="source pack")
        if _sha256_ref(current_text) != material.get("baseline_pack_sha256"):
            raise ValueError("source pack baseline hash mismatch; regenerate the candidate before review")
        source_examples = _validated_examples([sanitize_training_record(ex.to_artifact()) for ex in (examples or [])], pack_id=pack_id)
        source_manifest = self.split_examples(source_examples, pack_id=pack_id)
        if list(source_manifest.train_example_ids) != list(material.get("train_example_ids", [])):
            raise ValueError("source examples do not match candidate train split")
        if list(source_manifest.selection_example_ids) != list(material.get("selection_example_ids", [])):
            raise ValueError("source examples do not match candidate selection split")
        if list(source_manifest.hidden_example_ids) != list(material.get("hidden_example_ids", [])):
            raise ValueError("source examples do not match candidate hidden split")
        source_by_id = {example.example_id: example for example in source_examples}
        train_examples = [source_by_id[example_id] for example_id in source_manifest.train_example_ids]
        selection_examples = [source_by_id[example_id] for example_id in source_manifest.selection_example_ids]
        hidden_examples = [source_by_id[example_id] for example_id in source_manifest.hidden_example_ids]
        expected_preview, expected_edits = self.propose_candidate(
            pack_id=pack_id,
            pack_text=current_text,
            examples=train_examples,
            max_edits=int(material.get("max_edits") or 4),
            rejected_memory_skips=list(material.get("rejected_memory_skipped_edits", [])),
        )
        if preview != expected_preview:
            raise ValueError("candidate preview is not deterministic optimizer output for source baseline")
        expected_patch = _unified_diff(pack_id, current_text, preview)
        patch_text = (candidate_dir / "candidate_pack.patch").read_text(encoding="utf-8")
        if patch_text != expected_patch:
            raise ValueError("candidate patch does not match source baseline diff")
        selection_evidence = integrity.get("selection_evidence") or {}
        expected_scan = scan_candidate_text(preview)
        expected_selection_evidence = self.build_selection_evidence(
            taskset_path=taskset_path,
            scan=expected_scan,
            candidate_text=preview,
            edits=expected_edits,
            selection_examples=selection_examples,
        )
        if _canonical_json(expected_selection_evidence) != _canonical_json(selection_evidence):
            raise ValueError("candidate selection evidence does not match supplied taskset/examples")
        expected_material = _candidate_id_material(
            pack_id=pack_id,
            pack_text=current_text,
            candidate_text=preview,
            train_examples=train_examples,
            hidden_examples=hidden_examples,
            edits=expected_edits,
            max_edits=int(material.get("max_edits") or 4),
            selection_evidence=selection_evidence,
            rejected_memory_skipped_edits=list(material.get("rejected_memory_skipped_edits", [])),
        )
        if _candidate_id_from_material(expected_material) != candidate_id:
            raise ValueError("candidate identity is not reproducible from source baseline and bound examples")
        return bundle, preview, path

    def apply_candidate(
        self,
        candidate_id: str,
        *,
        pack_path: str | Path,
        taskset_path: str | Path | None = None,
        examples: Sequence[OptimizerExample] | None = None,
        scope: str = "local",
    ) -> dict[str, Any]:
        _, preview, path = self._verify_candidate_against_sources(
            candidate_id,
            pack_path=pack_path,
            taskset_path=taskset_path,
            examples=examples,
            scope=scope,
        )
        if path.is_symlink():
            raise ValueError("pack file must not be a symlink for local apply")
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.borg-optimize-pack.", suffix=".tmp", dir=str(path.parent), text=True)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(preview)
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return {"success": True, "candidate_id": candidate_id, "scope": scope, "pack_path": str(path)}


def run_pack_optimizer(
    *,
    pack_id: str,
    taskset_path: str | Path,
    pack_path: str | Path | None = None,
    output_root: str | Path | None = None,
    examples: Sequence[OptimizerExample | dict[str, Any]] | None = None,
    collective_db_path: str | Path | None = None,
    rejected_memory_path: str | Path | None = None,
    local_only: bool = True,
    max_edits: int = 4,
) -> OptimizerRunResult:
    optimizer = PackOptimizer(collective_db_path=collective_db_path, output_root=output_root, rejected_memory_path=rejected_memory_path)
    return optimizer.run(
        pack_id=pack_id,
        taskset_path=taskset_path,
        pack_path=pack_path,
        examples=examples,
        local_only=local_only,
        max_edits=max_edits,
    )
