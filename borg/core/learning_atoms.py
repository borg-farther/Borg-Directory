"""Learning atom schema, distillation, canonicalization, and signing."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from borg.core.crypto import derive_verify_key, encode_key, decode_key, verify_key_from_string
from borg.core.privacy import privacy_risk_score, privacy_scan_structured
from borg.core.prompt_injection import neutralize_for_retrieval, scan_prompt_injection
from borg.core.atom_tenant import is_valid_tenant_pseudonym, tenant_pseudonym


ALLOWED_TOP_FIELDS = {
    "schema_version", "atom_id", "scope", "task", "learning", "evidence",
    "privacy", "safety", "trust", "lifecycle",
    # Future-proof OPTIONAL fields (S0/B4) — validated when present, absent in
    # v1 atoms, and part of the signed canonical payload when set. Semantics in
    # docs/FEDERATION_DESIGN.md; adding them later would have re-signed the world.
    "applicability", "outcome", "signature_class", "embedding_ref",
}
ALLOWED_SCOPES = {"local", "org", "global_candidate", "global"}
ALLOWED_TASK_TYPES = {"debug", "test", "install", "deploy", "review", "config", "other"}
ALLOWED_STATUSES = {"draft", "quarantined", "local_safe", "org_safe", "global_candidate", "published", "revoked"}
ALLOWED_OUTCOME_STATUSES = {"unknown", "confirmed_helpful", "confirmed_unhelpful", "mixed"}
ALLOWED_SIGNATURE_CLASSES = {"ed25519", "ed25519_pq_hybrid_reserved"}
_APPLICABILITY_LIST_KEYS = {"languages", "frameworks", "os", "tool_versions"}


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: List[str]


@dataclass(frozen=True)
class SignatureCheck:
    valid: bool
    error: str = ""


def canonical_atom_json(atom: Dict[str, Any], include_atom_id: bool = False) -> bytes:
    """Return deterministic JSON bytes for atom IDs/signatures."""
    payload = copy.deepcopy(atom)
    if not include_atom_id:
        payload.pop("atom_id", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_atom_id(atom: Dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_atom_json(atom, include_atom_id=False)).hexdigest()


def learning_atom_key_id_from_verify_key(verify_key: Any) -> str:
    """Return the canonical key id for a learning-atom Ed25519 verify key.

    The key id is derived from the verify key bytes. Submitters cannot choose it
    by writing arbitrary `trust.submitter_key_id` or `signature.key_id` values.
    """
    return "ed25519:" + hashlib.sha256(bytes(verify_key)).hexdigest()[:16]


def validate_learning_atom(atom: Dict[str, Any]) -> ValidationResult:
    errors: List[str] = []
    if not isinstance(atom, dict):
        return ValidationResult(False, ["atom must be a dict"])

    unknown = set(atom) - ALLOWED_TOP_FIELDS
    if unknown:
        errors.append(f"unknown field(s): {', '.join(sorted(unknown))}")

    if atom.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if atom.get("scope") not in ALLOWED_SCOPES:
        errors.append("scope is invalid")

    task = atom.get("task") or {}
    if task.get("type") not in ALLOWED_TASK_TYPES:
        errors.append("task.type is invalid")

    lifecycle = atom.get("lifecycle") or {}
    if lifecycle.get("status") not in ALLOWED_STATUSES:
        errors.append("lifecycle.status is invalid")

    trust = atom.get("trust") or {}
    raw_tenant = str(trust.get("tenant_pseudonym", ""))
    if raw_tenant and not is_valid_tenant_pseudonym(raw_tenant):
        errors.append("trust.tenant_pseudonym must be tenant HMAC pseudonym, not raw tenant data")
    if re.search(r"@|https?://|/|\\\\", raw_tenant):
        errors.append("trust.tenant_pseudonym cannot contain raw tenant identifiers")

    # Future-proof optional fields (S0/B4): absent => v1-compatible; present =>
    # shape-checked here so federation peers can rely on them.
    if "applicability" in atom:
        applicability = atom.get("applicability")
        if not isinstance(applicability, dict):
            errors.append("applicability must be a dict")
        else:
            unknown_keys = set(applicability) - _APPLICABILITY_LIST_KEYS
            if unknown_keys:
                errors.append(f"applicability unknown key(s): {', '.join(sorted(unknown_keys))}")
            for key, value in applicability.items():
                if key in _APPLICABILITY_LIST_KEYS and (
                    not isinstance(value, list) or not all(isinstance(v, str) for v in value)
                ):
                    errors.append(f"applicability.{key} must be a list of strings")
    if "outcome" in atom:
        outcome = atom.get("outcome")
        if not isinstance(outcome, dict):
            errors.append("outcome must be a dict")
        elif outcome.get("status", "unknown") not in ALLOWED_OUTCOME_STATUSES:
            errors.append("outcome.status is invalid")
    if "signature_class" in atom and atom.get("signature_class") not in ALLOWED_SIGNATURE_CLASSES:
        errors.append("signature_class is invalid")
    if "embedding_ref" in atom:
        embedding_ref = atom.get("embedding_ref")
        if (
            not isinstance(embedding_ref, str)
            or not embedding_ref
            or len(embedding_ref) > 256
            or any(ch.isspace() for ch in embedding_ref)
        ):
            errors.append("embedding_ref must be a non-empty string (max 256 chars, no whitespace)")

    expected_id = compute_atom_id(atom)
    if atom.get("atom_id") and atom.get("atom_id") != expected_id:
        errors.append("atom_id does not match canonical payload")

    scan = privacy_risk_score(atom)
    if scan.blocked:
        errors.append("privacy risk blocks shared atom")
    # S0/B6: scan EVERY string in the payload, not just learning.* — crafted
    # atoms can carry injection in task/applicability/embedding_ref fields too.
    from borg.core.privacy import collect_strings

    if scan_prompt_injection(" ".join(collect_strings(atom))).blocked:
        errors.append("prompt injection risk blocks atom")

    if atom.get("scope") in {"global", "global_candidate"}:
        text = json.dumps(atom, ensure_ascii=False)
        if re.search(r"/home/|/root/|C:\\|https?://|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.", text):
            errors.append("global scope cannot contain raw path/url/email privacy material")

    return ValidationResult(not errors, errors)


def _safe_day() -> str:
    return time.strftime("%Y-%m-%d")


def _classify_error(error_text: str) -> str:
    text = (error_text or "").lower()
    if "migration" in text or "table already exists" in text or "operationalerror" in text:
        return "db-migration-error"
    if "typeerror" in text:
        return "type-error"
    if "importerror" in text or "modulenotfound" in text:
        return "python-import-error"
    return "generic-error"


def _as_list_from_json(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except Exception:
            return [value]
    return []


def distill_trace_to_atom(
    trace: Dict[str, Any],
    scope: str = "local",
    tenant_identifier: str = "",
    tenant_secret: bytes | str | None = None,
) -> Dict[str, Any]:
    """Convert a local raw trace into a schema-minimized learning atom.

    Raw tenant identifiers are accepted only as local inputs and are converted to
    HMAC pseudonyms before entering the atom payload.
    """
    errors = _as_list_from_json(trace.get("errors_encountered", []))
    dead_ends = _as_list_from_json(trace.get("dead_ends", []))
    technology = trace.get("technology") or "unknown"
    worked_raw = trace.get("approach_summary") or trace.get("root_cause") or trace.get("task_description", "")
    why_raw = trace.get("root_cause") or ""

    worked_scan = privacy_scan_structured(neutralize_for_retrieval(worked_raw))
    why_scan = privacy_scan_structured(neutralize_for_retrieval(why_raw))
    safe_avoid = []
    for item in dead_ends[:5]:
        cleaned = privacy_scan_structured(neutralize_for_retrieval(item)).sanitized
        if cleaned:
            safe_avoid.append(cleaned)
    if not safe_avoid:
        safe_avoid = ["Repeat previously failed approach without validating root cause."]

    error_joined = " ".join(errors + [trace.get("error_patterns", ""), trace.get("task_description", "")])
    privacy_scan = privacy_risk_score({"worked": worked_scan.sanitized, "why": why_scan.sanitized, "avoid": safe_avoid})
    injection_scan = scan_prompt_injection(" ".join([str(worked_scan.sanitized), str(why_scan.sanitized), " ".join(safe_avoid)]))

    tenant_pseudo = tenant_pseudonym(tenant_identifier, tenant_secret) if scope != "local" or tenant_identifier else ""
    atom = {
        "schema_version": "1.0",
        "scope": scope,
        "task": {
            "type": "debug",
            "technology": [technology] if isinstance(technology, str) else list(technology),
            "error_class": _classify_error(error_joined),
            "error_pattern": _classify_error(error_joined),
            "difficulty": "unknown",
        },
        "learning": {
            "root_cause_class": _classify_error(error_joined),
            "worked": worked_scan.sanitized,
            "avoid": safe_avoid,
            "why": why_scan.sanitized or "Root cause captured in sanitized local trace.",
        },
        "evidence": {"type": "test_passed" if trace.get("outcome") == "success" else "agent_reported", "strength": "medium", "support_count": 1},
        "privacy": {
            "risk_score": privacy_scan.risk_score,
            "scanner_version": "privacy-v1",
            "finding_classes": sorted({f.kind for f in privacy_scan.findings}),
            "redaction_count": len(privacy_scan.findings),
            "raw_trace_retained": False,
        },
        "safety": {
            "prompt_injection_score": injection_scan.score,
            "injection_classes": sorted({f.kind for f in injection_scan.findings}),
            "imperative_text_removed": True,
            "retrieval_treatment": "untrusted_advisory",
        },
        "trust": {"submitter_key_id": "", "tenant_pseudonym": tenant_pseudo, "agent_reputation_at_submit": 0, "independent_tenant_count": 1, "promotion_score": 0},
        "lifecycle": {"status": "local_safe", "created_at_day": _safe_day(), "expires_at_day": None, "revoked_at": None, "revocation_reason": None},
    }
    atom["atom_id"] = compute_atom_id(atom)
    return atom


def sign_learning_atom(atom: Dict[str, Any], signing_key: Any) -> Dict[str, Any]:
    """Sign an atom payload using existing Borg Ed25519 primitives."""
    from nacl import encoding

    payload = copy.deepcopy(atom)
    verify_key = derive_verify_key(signing_key)
    verify_key_str = encode_key(bytes(verify_key))
    key_id = learning_atom_key_id_from_verify_key(verify_key)
    payload.setdefault("trust", {})["submitter_key_id"] = key_id
    payload["atom_id"] = compute_atom_id(payload)
    signed = signing_key.sign(canonical_atom_json(payload, include_atom_id=True), encoder=encoding.RawEncoder)
    signature = encode_key(bytes(signed.signature))
    envelope = {
        "type": "learning_atom",
        "id": payload["atom_id"],
        "envelope_version": "1.0",
        "payload": payload,
        "signature": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "verify_key": verify_key_str,
            "signature_b64url": signature,
            "signed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }
    return envelope


def verify_signed_atom(envelope: Dict[str, Any]) -> SignatureCheck:
    try:
        from nacl import encoding, exceptions

        if envelope.get("type") != "learning_atom":
            return SignatureCheck(False, "envelope type must be learning_atom")
        payload = envelope["payload"]
        signature = envelope["signature"]
        if envelope.get("id") != payload.get("atom_id"):
            return SignatureCheck(False, "envelope id does not match payload atom_id")
        expected_atom_id = compute_atom_id(payload)
        if payload.get("atom_id") != expected_atom_id:
            return SignatureCheck(False, "payload atom_id does not match canonical payload")
        sig = signature["signature_b64url"]
        verify_key = verify_key_from_string(signature["verify_key"])
        derived_key_id = learning_atom_key_id_from_verify_key(verify_key)
        if signature.get("key_id") != derived_key_id:
            return SignatureCheck(False, "signature key_id does not match verify key")
        payload_key_id = (payload.get("trust") or {}).get("submitter_key_id")
        if payload_key_id != derived_key_id:
            return SignatureCheck(False, "payload submitter_key_id does not match verify key")
        try:
            verify_key.verify(
                canonical_atom_json(payload, include_atom_id=True),
                decode_key(sig, "signature"),
                encoder=encoding.RawEncoder,
            )
        except (exceptions.BadSignatureError, ValueError):
            return SignatureCheck(False, "signature mismatch")
        if validate_learning_atom(payload).valid is False:
            return SignatureCheck(False, "payload validation failed")
        return SignatureCheck(True, "")
    except Exception as e:
        return SignatureCheck(False, str(e))
