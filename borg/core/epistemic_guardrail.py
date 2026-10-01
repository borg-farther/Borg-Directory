"""Evidence-first guardrail and selective deep-deliberation contract.

Borg does not replace the host model's reasoning.  This module returns a bounded,
machine-readable packet that separates memory from proof, exposes conflicts and
unsupported claims, and requires independent verification for consequential work.
It intentionally contains no model/API calls and never requests chain-of-thought.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from borg.core.prompt_injection import neutralize_for_retrieval, scan_prompt_injection

SCHEMA_VERSION = "1.0"
VALID_MODES = {"auto", "standard", "deep"}
VALID_STAGES = {"preflight", "review"}
VALID_RISKS = {"", "low", "medium", "high", "critical"}
VALID_DECISIONS = {
    "proceed",
    "proceed_with_caution",
    "block_pending_verification",
    "invalid_input",
}
VALID_MEMORY_STATUSES = {
    "no_confident_match",
    "retrieval_degraded",
    "advisory_only",
    "verified_collective",
    "conflicted",
}

_TOKEN_RE = re.compile(r"[a-z0-9_+.-]{3,}", re.I)
_STOPWORDS = {
    "and", "are", "but", "can", "for", "from", "have", "into", "not", "the",
    "this", "that", "then", "they", "use", "using", "with", "without", "your",
    "task", "work", "agent", "borg", "guidance", "memory", "approach", "issue",
    "problem", "should", "must", "could", "would", "will", "was", "were", "has",
}
_HIGH_STAKES_PATTERNS = (
    re.compile(r"\bultra[ -]?deep\b", re.I),
    re.compile(r"\bdeep (?:think|thinking|review|analysis)\b", re.I),
    re.compile(r"\badversarial(?:ly)?\b", re.I),
    re.compile(r"\bproduction(?:-ready| readiness| release| deploy| migration)?\b", re.I),
    re.compile(r"\b(?:security|privacy|credential|secret|authentication|authorization)\b", re.I),
    re.compile(r"\b(?:irreversible|destructive|delete|purge|rotate keys?)\b", re.I),
    re.compile(r"\b(?:release|publish|deploy|cutover|mainnet|financial|legal|medical)\b", re.I),
    re.compile(r"\b(?:architecture|root cause|incident|postmortem|migration)\b", re.I),
    re.compile(r"\b(?:prove|verification|triple[- ]check|complete(?:ness)?)\b", re.I),
)
_VERIFICATION_CATEGORIES = (
    "scope",
    "independent_evidence",
    "decisive_test",
    "disconfirm",
)


def _clean_text(value: Any, limit: int = 4000) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _safe_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        parsed = float(value or 0.0)
        return round(parsed, 6) if math.isfinite(parsed) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _tokens(value: Any) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(_clean_text(value).lower())
        if token.lower() not in _STOPWORDS
    }


def _material_overlap(left: Any, right: Any) -> Tuple[bool, List[str]]:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    overlap = sorted(left_tokens & right_tokens)
    if len(overlap) < 2:
        return False, overlap
    denominator = max(min(len(left_tokens), len(right_tokens)), 1)
    return (len(overlap) / denominator) >= 0.5, overlap


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _stable_id(prefix: str, payload: Any) -> str:
    body = json.dumps(_jsonable(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _coerce_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_clean_text(value)] if _clean_text(value) else []
    if isinstance(value, Sequence):
        return [_clean_text(item) for item in value if _clean_text(item)]
    return [_clean_text(value)] if _clean_text(value) else []


@dataclass(frozen=True)
class MemoryItem:
    source_type: str
    source_id: str
    summary: str = ""
    worked: str = ""
    avoid: Tuple[str, ...] = field(default_factory=tuple)
    evidence_tier: str = "unverified"
    retrieval_treatment: str = "advisory"
    helpful_outcomes: int = 0
    unhelpful_outcomes: int = 0
    verified_tenant_count: int = 0
    score: float = 0.0
    provenance_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class EpistemicPacket:
    schema_version: str
    packet_id: str
    status: str
    stage: str
    mode_requested: str
    mode_selected: str
    decision: str
    activation_reasons: Tuple[str, ...]
    task: Dict[str, str]
    memory_status: str
    memory_items: Tuple[Dict[str, Any], ...]
    claims: Tuple[Dict[str, Any], ...]
    unsupported_claims: Tuple[str, ...]
    unverified_support_claims: Tuple[str, ...]
    invalid_evidence_refs: Tuple[Dict[str, Any], ...]
    assumptions: Tuple[Dict[str, Any], ...]
    evidence: Tuple[Dict[str, Any], ...]
    contradictions: Tuple[Dict[str, Any], ...]
    uncertainties: Tuple[str, ...]
    challenges: Tuple[str, ...]
    stop_conditions: Tuple[str, ...]
    verification_plan: Tuple[Dict[str, Any], ...]
    safety_findings: Tuple[Dict[str, Any], ...]
    provenance: Dict[str, Any]
    claim_boundaries: Tuple[str, ...]
    outcome_capture: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        data = _jsonable(asdict(self))
        if data.get("decision") not in VALID_DECISIONS:  # defensive contract guard
            data["decision"] = "invalid_input"
        return data


MemoryProvider = Callable[[str, str, int], Sequence[Mapping[str, Any]]]


def _activation(task: str, context: str, mode: str, risk_level: str, failure_count: int) -> Tuple[str, List[str]]:
    if mode == "deep":
        return "deep", ["explicit_deep_mode"]
    if mode == "standard":
        return "standard", ["explicit_standard_mode"]

    reasons: List[str] = []
    if failure_count >= 2:
        reasons.append("repeated_failures")
    if risk_level in {"high", "critical"}:
        reasons.append(f"{risk_level}_risk")
    combined = f"{task} {context}"
    if any(pattern.search(combined) for pattern in _HIGH_STAKES_PATTERNS):
        reasons.append("high_stakes_language")
    if reasons:
        return "deep", sorted(set(reasons))
    return "standard", ["no_deep_activation_signal"]


def _default_memory_provider(task: str, context: str, limit: int) -> Sequence[Mapping[str, Any]]:
    """Best-effort retrieval from existing stores; failures never block deliberation."""
    query = _clean_text(f"{task} {context}")
    if not query:
        return []
    raw: List[Mapping[str, Any]] = []

    try:
        from borg.core.collective_learning import unified_collective_retrieve

        for item in unified_collective_retrieve(query, limit=max(limit, 1)):
            atom = item.get("atom") or {}
            atom_task = atom.get("task") or {}
            learning = atom.get("learning") or {}
            atom_text = " ".join(
                [
                    str(atom_task.get("type", "")),
                    str(atom_task.get("error_pattern", "")),
                    " ".join(str(value) for value in atom_task.get("technology", []) or []),
                    str(learning.get("root_cause_class", "")),
                    str(learning.get("worked", "")),
                    " ".join(str(value) for value in learning.get("avoid", []) or []),
                ]
            )
            relevant, _ = _material_overlap(query, atom_text)
            if not relevant:
                continue
            raw.append(
                {
                    "source_type": "learning_atom",
                    "source_id": item.get("atom_id", ""),
                    "summary": learning.get("root_cause_class", ""),
                    "worked": learning.get("worked", ""),
                    "avoid": learning.get("avoid", []),
                    "helpful_outcomes": item.get("helpful_outcomes", 0),
                    "unhelpful_outcomes": item.get("unhelpful_outcomes", 0),
                    "verified_tenant_count": item.get("verified_tenant_count", 0),
                    "score": item.get("score", 0.0),
                    "provenance_verified": True,
                }
            )
    except Exception as exc:
        raw.append(
            {
                "_retrieval_error": True,
                "lane": "collective",
                "error_type": type(exc).__name__,
            }
        )

    try:
        from borg.core.confidence_gate import trace_match_is_confident
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher()
        for trace in matcher.find_relevant(task=task, error=context, top_k=max(limit, 1)):
            if not trace_match_is_confident(trace, query=query):
                continue
            raw.append(
                {
                    "source_type": "local_trace",
                    "source_id": trace.get("id") or trace.get("trace_id") or "",
                    "summary": trace.get("root_cause") or trace.get("task_description") or "",
                    "worked": trace.get("causal_intervention") or trace.get("approach_summary") or "",
                    "avoid": trace.get("dead_ends") or [],
                    "helpful_outcomes": trace.get("times_helped", 0),
                    "unhelpful_outcomes": max(
                        _safe_int(trace.get("times_shown")) - _safe_int(trace.get("times_helped")),
                        0,
                    ),
                    "score": trace.get("match_score", 0.0),
                    "provenance_verified": True,
                }
            )
    except Exception as exc:
        raw.append(
            {
                "_retrieval_error": True,
                "lane": "local_trace",
                "error_type": type(exc).__name__,
            }
        )

    try:
        from borg.core.failure_memory import FailureMemory

        recalled = FailureMemory().recall_across_agents(query)
        if recalled:
            correct = recalled.get("correct_approaches") or []
            wrong = recalled.get("wrong_approaches") or []
            raw.append(
                {
                    "source_type": "failure_memory",
                    "source_id": _stable_id("failure", recalled.get("error_pattern", query)),
                    "summary": recalled.get("error_pattern", ""),
                    "worked": "; ".join(
                        str(item.get("approach", "")) for item in correct[:3] if item.get("approach")
                    ),
                    "avoid": [
                        str(item.get("approach", "")) for item in wrong[:3] if item.get("approach")
                    ],
                    "helpful_outcomes": sum(_safe_int(item.get("success_count")) for item in correct),
                    "unhelpful_outcomes": sum(_safe_int(item.get("failure_count")) for item in wrong),
                    "provenance_verified": True,
                }
            )
    except Exception as exc:
        raw.append(
            {
                "_retrieval_error": True,
                "lane": "failure_memory",
                "error_type": type(exc).__name__,
            }
        )

    cap = max(limit * 2, limit)
    errors = [item for item in raw if item.get("_retrieval_error")]
    values = [item for item in raw if not item.get("_retrieval_error")]
    return (values[: max(cap - len(errors), 0)] + errors)[:cap]


def _normalize_memory(
    raw_items: Sequence[Mapping[str, Any]],
    limit: int,
) -> Tuple[List[MemoryItem], List[Dict[str, Any]]]:
    normalized: List[MemoryItem] = []
    findings: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for position, raw_value in enumerate(raw_items):
        if not isinstance(raw_value, Mapping):
            continue
        raw = dict(raw_value)
        if raw.get("_retrieval_error"):
            lane = _clean_text(raw.get("lane") or "unknown", 80)
            findings.append(
                {
                    "source_id": f"retrieval:{lane}",
                    "blocked": False,
                    "score": 0.0,
                    "kinds": ["retrieval_unavailable"],
                    "evidence_hashes": [],
                    "lane": lane,
                    "error_type": _clean_text(raw.get("error_type") or "Error", 80),
                }
            )
            continue
        atom = raw.get("atom") if isinstance(raw.get("atom"), Mapping) else {}
        learning = atom.get("learning") if isinstance(atom.get("learning"), Mapping) else {}
        source_type = _clean_text(raw.get("source_type") or raw.get("source") or "unverified", 80).lower()
        source_id = _clean_text(
            raw.get("source_id") or raw.get("atom_id") or raw.get("trace_id") or raw.get("id") or "",
            160,
        )
        if not source_id:
            source_id = _stable_id("memory", [source_type, position, raw])
        summary = _clean_text(raw.get("summary") or learning.get("root_cause_class") or raw.get("root_cause"))
        worked = _clean_text(raw.get("worked") or learning.get("worked") or raw.get("approach_summary"))
        avoid = _coerce_string_list(raw.get("avoid") or learning.get("avoid") or raw.get("dead_ends"))
        combined = " ".join([summary, worked, *avoid])
        try:
            scan = scan_prompt_injection(combined)
        except Exception as exc:
            findings.append(
                {
                    "source_id": source_id,
                    "blocked": True,
                    "score": 0.0,
                    "kinds": ["safety_scanner_unavailable"],
                    "evidence_hashes": [],
                    "error_type": type(exc).__name__,
                }
            )
            continue
        if scan.findings:
            findings.append(
                {
                    "source_id": source_id,
                    "blocked": bool(scan.blocked),
                    "score": scan.score,
                    "kinds": sorted({finding.kind for finding in scan.findings}),
                    "evidence_hashes": sorted({finding.evidence_hash for finding in scan.findings}),
                }
            )
        if scan.blocked:
            continue
        try:
            summary = _clean_text(neutralize_for_retrieval(summary))
            worked = _clean_text(neutralize_for_retrieval(worked))
            avoid = [_clean_text(neutralize_for_retrieval(item)) for item in avoid]
        except Exception as exc:
            findings.append(
                {
                    "source_id": source_id,
                    "blocked": True,
                    "score": 0.0,
                    "kinds": ["safety_scanner_unavailable"],
                    "evidence_hashes": [],
                    "error_type": type(exc).__name__,
                }
            )
            continue
        avoid = [item for item in avoid if item]
        if not (summary or worked or avoid):
            continue

        provenance_verified = _safe_bool(raw.get("provenance_verified"))
        helpful = _safe_int(raw.get("helpful_outcomes"))
        unhelpful = _safe_int(raw.get("unhelpful_outcomes"))
        tenants = _safe_int(raw.get("verified_tenant_count"))
        source_key = source_type.replace("-", "_")
        if source_key in {"seed", "seed_pack", "static", "bundled"}:
            tier = "seed_only"
        elif source_key in {"local_trace", "trace", "failure_memory", "local"}:
            tier = "observed_local"
        elif (
            source_key in {"learning_atom", "collective", "collective_atom"}
            and provenance_verified
            and tenants >= 3
            and helpful >= 3
            and helpful >= unhelpful
        ):
            tier = "verified_collective"
        else:
            tier = "unverified"

        key = (source_type, source_id)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            MemoryItem(
                source_type=source_type,
                source_id=source_id,
                summary=summary,
                worked=worked,
                avoid=tuple(avoid),
                evidence_tier=tier,
                retrieval_treatment="advisory",
                helpful_outcomes=helpful,
                unhelpful_outcomes=unhelpful,
                verified_tenant_count=tenants if provenance_verified else 0,
                score=_safe_float(raw.get("score")),
                provenance_verified=provenance_verified,
            )
        )

    tier_order = {"verified_collective": 0, "observed_local": 1, "seed_only": 2, "unverified": 3}
    normalized.sort(key=lambda item: (tier_order.get(item.evidence_tier, 9), -item.score, item.source_id))
    return normalized[: max(limit, 0)], sorted(findings, key=lambda item: item["source_id"])


def _detect_conflicts(items: Sequence[MemoryItem]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, Tuple[str, ...]]] = set()
    for positive in items:
        positive_text = " ".join(part for part in [positive.summary, positive.worked] if part)
        if not positive_text:
            continue
        for negative in items:
            if positive.source_id == negative.source_id or not negative.avoid:
                continue
            for avoid in negative.avoid:
                conflict, overlap = _material_overlap(positive_text, avoid)
                if not conflict:
                    continue
                key = (positive.source_id, negative.source_id, tuple(overlap))
                if key in seen:
                    continue
                seen.add(key)
                conflicts.append(
                    {
                        "kind": "worked_vs_avoid",
                        "positive_source_id": positive.source_id,
                        "negative_source_id": negative.source_id,
                        "overlap_terms": overlap,
                        "treatment": "do_not_select_between_memories_without_discriminating_evidence",
                    }
                )
    return sorted(conflicts, key=lambda item: (item["positive_source_id"], item["negative_source_id"]))


def _normalize_evidence(evidence: Optional[Sequence[Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    id_counts: Dict[str, int] = {}
    for index, raw in enumerate(evidence or []):
        if not isinstance(raw, Mapping):
            continue
        evidence_id = _clean_text(raw.get("id") or raw.get("evidence_id") or f"evidence-{index + 1}", 160)
        id_counts[evidence_id] = id_counts.get(evidence_id, 0) + 1
        normalized.append(
            {
                "id": evidence_id,
                "type": _clean_text(raw.get("type") or "unspecified", 80),
                "source": _clean_text(raw.get("source") or "caller_supplied", 160),
                "summary": _clean_text(raw.get("summary") or raw.get("result") or ""),
                "locator": _clean_text(raw.get("locator") or raw.get("path") or raw.get("url") or "", 500),
                "verified": _safe_bool(raw.get("verified")),
            }
        )
    duplicate_ids = {evidence_id for evidence_id, count in id_counts.items() if count > 1}
    for item in normalized:
        if item["id"] in duplicate_ids:
            item["verified"] = False
            item["duplicate_id"] = True
    normalized.sort(key=lambda item: item["id"])
    return normalized


def _audit_claims(
    claims: Optional[Sequence[Mapping[str, Any]]],
    evidence: Sequence[Dict[str, Any]],
    memories: Sequence[MemoryItem],
) -> Tuple[List[Dict[str, Any]], List[str], List[str], List[Dict[str, Any]]]:
    evidence_by_id = {item["id"]: item for item in evidence}
    memory_by_id = {item.source_id: item for item in memories}
    normalized: List[Dict[str, Any]] = []
    unsupported: List[str] = []
    unverified_support: List[str] = []
    invalid_refs: List[Dict[str, Any]] = []
    seen_claim_ids: Dict[str, int] = {}

    for index, raw in enumerate(claims or []):
        if not isinstance(raw, Mapping):
            continue
        original_claim_id = _clean_text(raw.get("id") or f"claim-{index + 1}", 160)
        seen_claim_ids[original_claim_id] = seen_claim_ids.get(original_claim_id, 0) + 1
        duplicate_claim = seen_claim_ids[original_claim_id] > 1
        claim_id = (
            f"{original_claim_id}#duplicate-{seen_claim_ids[original_claim_id]}"
            if duplicate_claim
            else original_claim_id
        )
        text = _clean_text(raw.get("text") or raw.get("claim"))
        refs = sorted(set(_coerce_string_list(raw.get("evidence_refs"))))
        dangling = [ref for ref in refs if ref not in evidence_by_id and ref not in memory_by_id]
        verified_refs = [ref for ref in refs if ref in evidence_by_id and evidence_by_id[ref]["verified"]]
        advisory_refs = [
            ref
            for ref in refs
            if ref in memory_by_id or (ref in evidence_by_id and not evidence_by_id[ref]["verified"])
        ]
        if not text or duplicate_claim or not refs or dangling:
            support_status = "unsupported"
            unsupported.append(claim_id)
        elif verified_refs:
            support_status = "verified_evidence_present"
        else:
            support_status = "advisory_only"
            unverified_support.append(claim_id)
        if dangling:
            invalid_refs.append({"claim_id": claim_id, "references": dangling})
        if duplicate_claim:
            invalid_refs.append({"claim_id": claim_id, "references": [], "reason": "duplicate_claim_id"})
        if not text:
            invalid_refs.append({"claim_id": claim_id, "references": [], "reason": "empty_claim_text"})
        normalized.append(
            {
                "id": claim_id,
                "text": text,
                "kind": _clean_text(raw.get("kind") or "material", 80),
                "material": _safe_bool(raw.get("material"), default=True),
                "evidence_refs": refs,
                "verified_evidence_refs": verified_refs,
                "advisory_evidence_refs": advisory_refs,
                "support_status": support_status,
            }
        )

    return (
        sorted(normalized, key=lambda item: item["id"]),
        sorted(set(unsupported)),
        sorted(set(unverified_support)),
        sorted(invalid_refs, key=lambda item: item["claim_id"]),
    )


def _verification_plan(
    supplied: Optional[Sequence[Mapping[str, Any]]],
    deep: bool,
) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    for index, raw in enumerate(supplied or []):
        if not isinstance(raw, Mapping):
            continue
        category = _clean_text(raw.get("category") or raw.get("type") or "caller_check", 80)
        plan.append(
            {
                "id": _clean_text(raw.get("id") or f"verify-{index + 1}", 160),
                "category": category,
                "objective": _clean_text(raw.get("objective") or raw.get("description") or raw.get("step")),
                "command": _clean_text(raw.get("command"), 1000),
                "required_evidence": _clean_text(raw.get("required_evidence") or raw.get("expected") or "recorded result"),
                "required": _safe_bool(raw.get("required"), default=True),
                "status": _clean_text(raw.get("status") or "pending", 40),
            }
        )

    generic = {
        "scope": (
            "Reproduce or bound the exact task state before acting.",
            "exact input, state, or failing output",
        ),
        "independent_evidence": (
            "Inspect an independent primary source or direct system artifact for each material claim.",
            "source locator plus directly observed result",
        ),
        "decisive_test": (
            "Run the smallest decisive check that can falsify the proposed action.",
            "test command or procedure, exit/result, and retained output",
        ),
        "disconfirm": (
            "Search explicitly for a counterexample, conflicting condition, or regression.",
            "disconfirming search result or documented absence within the stated scope",
        ),
    }
    required_categories = _VERIFICATION_CATEGORIES if deep else ("decisive_test",)
    existing = {item["category"] for item in plan}
    for category in required_categories:
        if category in existing:
            continue
        objective, required_evidence = generic[category]
        plan.append(
            {
                "id": f"verify-{category.replace('_', '-')}",
                "category": category,
                "objective": objective,
                "command": "",
                "required_evidence": required_evidence,
                "required": True,
                "status": "pending",
            }
        )
    return sorted(plan, key=lambda item: (list(_VERIFICATION_CATEGORIES).index(item["category"]) if item["category"] in _VERIFICATION_CATEGORIES else 99, item["id"]))


def _invalid_packet(task: str, context: str, mode: str, stage: str, reason: str) -> EpistemicPacket:
    packet_id = _stable_id("ep", [task, context, mode, stage, reason])
    return EpistemicPacket(
        schema_version=SCHEMA_VERSION,
        packet_id=packet_id,
        status="invalid_input",
        stage=stage if stage in VALID_STAGES else "preflight",
        mode_requested=mode,
        mode_selected="standard",
        decision="invalid_input",
        activation_reasons=(reason,),
        task={"text": _clean_text(task), "context": _clean_text(context)},
        memory_status="no_confident_match",
        memory_items=tuple(),
        claims=tuple(),
        unsupported_claims=tuple(),
        unverified_support_claims=tuple(),
        invalid_evidence_refs=tuple(),
        assumptions=tuple(),
        evidence=tuple(),
        contradictions=tuple(),
        uncertainties=(reason,),
        challenges=tuple(),
        stop_conditions=("Do not act on an invalid epistemic packet.",),
        verification_plan=tuple(),
        safety_findings=tuple(),
        provenance={"external_model_calls": False, "chain_of_thought_requested": False, "memory_retrieval": "not_run"},
        claim_boundaries=("No factual or operational guidance was produced.",),
        outcome_capture={"recordable": False},
    )


def deliberate(
    task: str,
    *,
    context: str = "",
    mode: str = "auto",
    stage: str = "preflight",
    draft: str = "",
    claims: Optional[Sequence[Mapping[str, Any]]] = None,
    assumptions: Optional[Sequence[str]] = None,
    evidence: Optional[Sequence[Mapping[str, Any]]] = None,
    verification_steps: Optional[Sequence[Mapping[str, Any]]] = None,
    failure_count: int = 0,
    risk_level: str = "",
    memory_items: Optional[Sequence[Mapping[str, Any]]] = None,
    memory_limit: int = 5,
    memory_provider: Optional[MemoryProvider] = None,
) -> EpistemicPacket:
    """Build a deterministic epistemic packet for a host reasoning agent.

    ``memory_items`` is primarily an adapter/testing seam.  Raw caller metadata
    cannot create collective proof unless the trusted adapter marks provenance as
    verified and existing conservative quorum requirements are also met.
    """
    task = _clean_text(task)
    context = _clean_text(context)
    draft = _clean_text(draft, 20000)
    mode = _clean_text(mode, 20).lower() or "auto"
    stage = _clean_text(stage, 20).lower() or "preflight"
    risk_level = _clean_text(risk_level, 20).lower()
    try:
        failure_count = max(int(failure_count), 0)
    except (TypeError, ValueError):
        failure_count = 0
    try:
        memory_limit = min(max(int(memory_limit), 0), 20)
    except (TypeError, ValueError):
        memory_limit = 5

    if not task:
        return _invalid_packet(task, context, mode, stage, "empty_task")
    if mode not in VALID_MODES:
        return _invalid_packet(task, context, mode, stage, "invalid_mode")
    if stage not in VALID_STAGES:
        return _invalid_packet(task, context, mode, stage, "invalid_stage")
    if risk_level not in VALID_RISKS:
        return _invalid_packet(task, context, mode, stage, "invalid_risk_level")

    selected_mode, activation_reasons = _activation(task, context, mode, risk_level, failure_count)
    provider_status = "caller_supplied"
    if memory_items is None:
        provider = memory_provider or _default_memory_provider
        provider_status = "default_stores" if memory_provider is None else "injected_provider"
        try:
            memory_items = provider(task, context, memory_limit)
        except Exception as exc:
            memory_items = [
                {
                    "_retrieval_error": True,
                    "lane": "provider",
                    "error_type": type(exc).__name__,
                }
            ]
            provider_status = "retrieval_error_fail_closed"
    memories, safety_findings = _normalize_memory(list(memory_items or []), memory_limit)
    conflicts = _detect_conflicts(memories)
    retrieval_degraded = any(
        bool({"retrieval_unavailable", "safety_scanner_unavailable"} & set(item.get("kinds", [])))
        for item in safety_findings
    )
    blocked_memory = any(
        bool(item.get("blocked"))
        and "safety_scanner_unavailable" not in item.get("kinds", [])
        for item in safety_findings
    )

    normalized_evidence = _normalize_evidence(evidence)
    normalized_claims, unsupported, unverified_support, invalid_refs = _audit_claims(
        claims, normalized_evidence, memories
    )
    normalized_assumptions = [
        {"id": f"assumption-{index + 1}", "text": _clean_text(value), "status": "unverified"}
        for index, value in enumerate(assumptions or [])
        if _clean_text(value)
    ]

    if conflicts:
        memory_status = "conflicted"
    elif any(item.evidence_tier == "verified_collective" for item in memories):
        memory_status = "verified_collective"
    elif memories:
        memory_status = "advisory_only"
    elif retrieval_degraded:
        memory_status = "retrieval_degraded"
    else:
        memory_status = "no_confident_match"

    material_claim_ids = {
        claim["id"]
        for claim in normalized_claims
        if claim.get("material", True) and claim.get("kind") != "preference"
    }
    risky_unsupported = bool(material_claim_ids & (set(unsupported) | set(unverified_support)))
    consequential = risk_level in {"high", "critical"} or "high_stakes_language" in activation_reasons
    review_without_claims = (
        stage == "review"
        and not normalized_claims
        and (bool(draft) or consequential)
    )

    if consequential and (risky_unsupported or review_without_claims):
        decision = "block_pending_verification"
    elif conflicts or unsupported or unverified_support or invalid_refs or safety_findings or review_without_claims:
        decision = "proceed_with_caution"
    else:
        decision = "proceed"

    uncertainties: List[str] = []
    if memory_status == "no_confident_match":
        uncertainties.append("No confident prior-memory match exists for this task.")
    if normalized_assumptions:
        uncertainties.append("Caller-supplied assumptions remain unverified.")
    if unsupported:
        uncertainties.append("One or more material claims lack resolvable evidence.")
    if unverified_support:
        uncertainties.append("One or more claims rely only on advisory evidence.")
    if review_without_claims:
        uncertainties.append("The consequential review was not accompanied by structured claims for its material assertions, so factual support was not auditable.")
    if conflicts:
        uncertainties.append("Retrieved memories conflict on a materially overlapping approach.")
    if retrieval_degraded:
        uncertainties.append("One or more memory lanes were unavailable; no absence-of-memory conclusion is valid for those lanes.")

    challenges: List[str] = []
    if selected_mode == "deep":
        challenges = [
            "What observation would falsify the leading conclusion?",
            "Which material claim has the weakest independent evidence?",
            "What changed since the remembered outcome, and could that reverse it?",
            "What is the smallest safe test that discriminates between competing explanations?",
        ]
    elif normalized_claims:
        challenges = ["What direct evidence would falsify the least-supported material claim?"]

    stops = [
        "Do not treat similarity, seed guidance, or a local trace as proof.",
        "Do not expose or persist private chain-of-thought; record only decision-relevant artifacts.",
    ]
    if memory_status == "no_confident_match":
        stops.append("Do not force unrelated memory onto this task; continue with normal reasoning and fresh evidence.")
    if conflicts:
        stops.append("Do not choose between conflicting memories without a discriminating check.")
    if blocked_memory:
        stops.append("Do not forward suppressed memory content; it triggered prompt-injection controls.")
    if retrieval_degraded:
        stops.append("Do not treat an unavailable memory lane as evidence that no prior result exists.")
    if decision == "block_pending_verification":
        stops.append("Do not execute the consequential action until material claims have verified evidence.")
    if review_without_claims:
        if draft:
            stops.append("Do not label an unstructured draft verified; submit its material claims and evidence references.")
        else:
            stops.append("Do not label an unstructured consequential review verified; submit its material claims and evidence references.")

    plan = _verification_plan(
        verification_steps,
        deep=selected_mode == "deep" or stage == "review" or risk_level in {"high", "critical"},
    )
    counts: Dict[str, int] = {}
    for item in memories:
        counts[item.evidence_tier] = counts.get(item.evidence_tier, 0) + 1

    claim_boundaries = [
        "The packet is a control artifact, not hidden reasoning or a factual oracle.",
        "All retrieved memory is advisory; only direct verification can close a material claim.",
        "Seed/static guidance and local traces are never represented as collective proof.",
        "No external performance lift is claimed by this packet.",
    ]
    if memory_status == "no_confident_match":
        claim_boundaries.append("NO_CONFIDENT_MATCH: Borg contributes no prior-memory evidence for this task.")

    id_payload = {
        "task": task,
        "context": context,
        "mode": mode,
        "stage": stage,
        "risk_level": risk_level,
        "failure_count": failure_count,
        "claims": normalized_claims,
        "evidence": normalized_evidence,
        "assumptions": normalized_assumptions,
        "draft_sha256": hashlib.sha256(draft.encode("utf-8")).hexdigest() if draft else "",
        "verification_plan": plan,
        "memories": [
            {"source_id": item.source_id, "content_ref": _stable_id("content", item.to_dict())}
            for item in memories
        ],
    }
    packet_id = _stable_id("ep", id_payload)
    return EpistemicPacket(
        schema_version=SCHEMA_VERSION,
        packet_id=packet_id,
        status="ok",
        stage=stage,
        mode_requested=mode,
        mode_selected=selected_mode,
        decision=decision,
        activation_reasons=tuple(activation_reasons),
        task={"text": task, "context": context},
        memory_status=memory_status,
        memory_items=tuple(item.to_dict() for item in memories),
        claims=tuple(normalized_claims),
        unsupported_claims=tuple(unsupported),
        unverified_support_claims=tuple(unverified_support),
        invalid_evidence_refs=tuple(invalid_refs),
        assumptions=tuple(normalized_assumptions),
        evidence=tuple(normalized_evidence),
        contradictions=tuple(conflicts),
        uncertainties=tuple(sorted(set(uncertainties))),
        challenges=tuple(challenges),
        stop_conditions=tuple(stops),
        verification_plan=tuple(plan),
        safety_findings=tuple(safety_findings),
        provenance={
            "external_model_calls": False,
            "chain_of_thought_requested": False,
            "memory_retrieval": provider_status,
            "memory_retrieval_degraded": retrieval_degraded,
            "memory_evidence_tier_counts": dict(sorted(counts.items())),
            "retrieval_authorizes_action": False,
        },
        claim_boundaries=tuple(claim_boundaries),
        outcome_capture={
            "recordable": True,
            "packet_id": packet_id,
            "required_binding": "intervention_id",
            "outcome_tool": "borg_record_outcome",
            "verified_success_requires": [
                "verification_command_or_procedure",
                "verification_result",
                "outcome_bound_to_this_intervention",
            ],
        },
    )


def render_epistemic_text(packet: EpistemicPacket) -> str:
    """Render a concise human view without adding facts absent from the packet."""
    data = packet.to_dict()
    lines = [
        f"BORG EPISTEMIC PACKET {data['packet_id']}",
        f"MODE: {data['mode_selected']} ({', '.join(data['activation_reasons'])})",
        f"DECISION: {data['decision']}",
        f"MEMORY: {data['memory_status']} ({len(data['memory_items'])} usable item(s))",
    ]
    if data["unsupported_claims"]:
        lines.append("UNSUPPORTED CLAIMS: " + ", ".join(data["unsupported_claims"]))
    if data["unverified_support_claims"]:
        lines.append("ADVISORY-ONLY CLAIMS: " + ", ".join(data["unverified_support_claims"]))
    if data["contradictions"]:
        lines.append(f"CONTRADICTIONS: {len(data['contradictions'])}; discriminate before acting")
    if data["safety_findings"]:
        blocked = sum(
            1
            for item in data["safety_findings"]
            if item.get("blocked")
            and "safety_scanner_unavailable" not in item.get("kinds", [])
        )
        degraded = sum(
            1
            for item in data["safety_findings"]
            if {"retrieval_unavailable", "safety_scanner_unavailable"} & set(item.get("kinds", []))
        )
        if blocked:
            lines.append(f"SAFETY: suppressed {blocked} unsafe memory item(s)")
        if degraded:
            lines.append(f"RETRIEVAL: {degraded} memory lane(s) unavailable; absence is not evidence")
    lines.append("STOP:")
    lines.extend(f"- {item}" for item in data["stop_conditions"])
    lines.append("VERIFY:")
    lines.extend(
        f"- [{item['category']}] {item['objective']}"
        for item in data["verification_plan"]
    )
    if data["memory_status"] == "no_confident_match":
        lines.append("NO_CONFIDENT_MATCH: proceed from fresh evidence, not recalled guidance.")
    return "\n".join(lines)


__all__ = [
    "EpistemicPacket",
    "MemoryItem",
    "SCHEMA_VERSION",
    "deliberate",
    "render_epistemic_text",
]
