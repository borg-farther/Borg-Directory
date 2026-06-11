"""Policy engine for learning atom promotion and sharing decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from borg.core.learning_atoms import validate_learning_atom
from borg.core.privacy import privacy_risk_score
from borg.core.prompt_injection import scan_prompt_injection
from borg.core.atom_tenant import is_valid_tenant_pseudonym


class AtomDecision(Enum):
    REJECT_PII = "reject_pii"
    REJECT_SECRET = "reject_secret"
    REJECT_PROMPT_INJECTION = "reject_prompt_injection"
    REJECT_UNSIGNED = "reject_unsigned"
    QUARANTINE = "quarantine"
    LOCAL_SAFE = "local_safe"
    ORG_SAFE = "org_safe"
    GLOBAL_CANDIDATE = "global_candidate"


@dataclass(frozen=True)
class AtomPolicyResult:
    decision: AtomDecision
    reasons: List[str]
    privacy: object
    injection: object


def classify_atom_policy(
    atom: dict,
    has_valid_signature: bool | None = None,
    min_tenant_quorum: int = 3,
    verified_tenant_count: int | None = None,
) -> AtomPolicyResult:
    """Classify an atom using fail-closed privacy, injection, signature, and quorum gates."""
    reasons: List[str] = []
    privacy = privacy_risk_score(atom)
    # Ingest-side injection scoring (S0/B6) covers EVERY string in the payload,
    # not just learning.worked/avoid/why — a crafted atom can carry injection in
    # task.error_pattern, technology, applicability, embedding_ref, ...
    from borg.core.privacy import collect_strings

    injection = scan_prompt_injection(" ".join(collect_strings(atom)))

    if injection.blocked:
        return AtomPolicyResult(AtomDecision.REJECT_PROMPT_INJECTION, ["prompt injection risk"], privacy, injection)

    if privacy.blocked:
        kinds = {f.kind for f in privacy.findings}
        if any(k in kinds for k in {"database_url", "bearer_token", "private_key", "jwt", "api_key", "high_entropy"}):
            return AtomPolicyResult(AtomDecision.REJECT_SECRET, ["secret risk"], privacy, injection)
        return AtomPolicyResult(AtomDecision.REJECT_PII, ["PII risk"], privacy, injection)

    validation = validate_learning_atom(atom)
    if not validation.valid:
        reasons.extend(validation.errors)
        return AtomPolicyResult(AtomDecision.QUARANTINE, reasons, privacy, injection)

    scope = atom.get("scope")
    trust = atom.get("trust") or {}
    signed_hint = bool(trust.get("submitter_key_id"))
    signed = signed_hint if has_valid_signature is None else bool(has_valid_signature)

    if scope == "local":
        return AtomPolicyResult(AtomDecision.LOCAL_SAFE, reasons, privacy, injection)

    if not signed:
        return AtomPolicyResult(AtomDecision.REJECT_UNSIGNED, ["shared atom must be signed"], privacy, injection)

    if scope == "org":
        if not is_valid_tenant_pseudonym(trust.get("tenant_pseudonym")):
            return AtomPolicyResult(AtomDecision.QUARANTINE, ["org atom requires tenant HMAC pseudonym"], privacy, injection)
        return AtomPolicyResult(AtomDecision.ORG_SAFE, reasons, privacy, injection)

    if scope in {"global_candidate", "global"}:
        if not is_valid_tenant_pseudonym(trust.get("tenant_pseudonym")):
            return AtomPolicyResult(AtomDecision.QUARANTINE, ["global atom requires tenant HMAC pseudonym"], privacy, injection)
        if verified_tenant_count is None:
            return AtomPolicyResult(
                AtomDecision.QUARANTINE,
                ["global promotion requires registry-computed independent tenant quorum"],
                privacy,
                injection,
            )
        tenant_count = int(verified_tenant_count or 0)
        if tenant_count < min_tenant_quorum:
            return AtomPolicyResult(AtomDecision.QUARANTINE, ["insufficient independent tenant quorum"], privacy, injection)
        return AtomPolicyResult(AtomDecision.GLOBAL_CANDIDATE, reasons, privacy, injection)

    return AtomPolicyResult(AtomDecision.QUARANTINE, ["unknown scope"], privacy, injection)
