"""Filesystem staging registry for signed, sanitized learning atoms.

This is the M1 local/staging propagation primitive, not an internet federation
service. It proves the safe loop shape:

    signed atom -> registry receipt -> clean client sync -> tombstone sync

The registry never accepts raw traces and never trusts self-declared global
quorum from atom payloads.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from borg.core.atom_policy import AtomDecision, classify_atom_policy
from borg.core.atom_store import AtomStore
from borg.core.learning_atoms import verify_signed_atom


@dataclass(frozen=True)
class RegistryReceipt:
    receipt_id: str
    atom_id: str
    decision: str
    reason: str
    verified_tenant_count: int | None
    path: str


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_atom_filename(atom_id: str) -> str:
    if not atom_id.startswith("sha256:"):
        raise ValueError("atom_id must be sha256:<hex>")
    suffix = atom_id.split(":", 1)[1]
    if len(suffix) != 64 or any(ch not in "0123456789abcdef" for ch in suffix):
        raise ValueError("atom_id must be lowercase sha256 hex")
    return atom_id.replace(":", "_") + ".json"


def _ensure_registry_dirs(registry_dir: str | Path) -> Path:
    root = Path(registry_dir)
    for child in ("atoms", "tombstones", "receipts", "quarantine"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_name(f".{path.name}.{os_pid_time()}.tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def os_pid_time() -> str:
    import os

    return f"{os.getpid()}.{time.time_ns()}"


def rebuild_manifest(registry_dir: str | Path) -> Dict[str, Any]:
    root = _ensure_registry_dirs(registry_dir)
    atoms = sorted(path.name for path in (root / "atoms").glob("*.json"))
    tombstones = sorted(path.name for path in (root / "tombstones").glob("*.json"))
    receipts = sorted(path.name for path in (root / "receipts").glob("*.json"))
    manifest = {
        "schema_version": "1.0",
        "generated_at": _now(),
        "atoms": atoms,
        "tombstones": tombstones,
        "receipts": receipts,
    }
    _write_json(root / "manifest.json", manifest)
    return manifest


def _receipt_id(atom_id: str, decision: str, created_at: str) -> str:
    material = f"{atom_id}\n{decision}\n{created_at}".encode("utf-8")
    return "receipt-sha256:" + hashlib.sha256(material).hexdigest()


def _write_receipt(
    root: Path,
    atom_id: str,
    decision: str,
    reason: str,
    verified_tenant_count: int | None,
) -> RegistryReceipt:
    created_at = _now()
    receipt_id = _receipt_id(atom_id, decision, created_at)
    receipt = {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "atom_id": atom_id,
        "decision": decision,
        "reason": reason,
        "verified_tenant_count": verified_tenant_count,
        "created_at": created_at,
    }
    path = root / "receipts" / (receipt_id.replace(":", "_") + ".json")
    _write_json(path, receipt)
    return RegistryReceipt(receipt_id, atom_id, decision, reason, verified_tenant_count, str(path))


def _quarantine(root: Path, envelope: Dict[str, Any], reason: str) -> RegistryReceipt:
    payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
    atom_id = payload.get("atom_id", "sha256:" + hashlib.sha256(json.dumps(envelope, sort_keys=True, default=str).encode("utf-8")).hexdigest())
    created_at = _now()
    qid = "quarantine-sha256:" + hashlib.sha256(f"{atom_id}\n{reason}\n{created_at}".encode("utf-8")).hexdigest()
    quarantine = {
        "schema_version": "1.0",
        "quarantine_id": qid,
        "atom_id": atom_id,
        "reason": reason,
        "created_at": created_at,
    }
    _write_json(root / "quarantine" / (qid.replace(":", "_") + ".json"), quarantine)
    return _write_receipt(root, atom_id, "quarantine", reason, None)


def ingest_atom_envelope(
    envelope: Dict[str, Any],
    registry_dir: str | Path,
    verified_tenant_count: int | None = None,
) -> RegistryReceipt:
    """Validate and store a signed atom envelope in a local staging registry.

    Local-scope atoms are intentionally not accepted: callers must explicitly
    choose org/global_candidate scope before anything becomes shareable.
    """
    root = _ensure_registry_dirs(registry_dir)
    signature = verify_signed_atom(envelope)
    if not signature.valid:
        receipt = _quarantine(root, envelope, f"signature failed: {signature.error}")
        rebuild_manifest(root)
        raise ValueError(receipt.reason)

    payload = envelope["payload"]
    atom_id = payload["atom_id"]
    if payload.get("scope") == "local":
        receipt = _quarantine(root, envelope, "local-scope atoms are not shareable")
        rebuild_manifest(root)
        raise ValueError(receipt.reason)

    policy = classify_atom_policy(
        payload,
        has_valid_signature=True,
        verified_tenant_count=verified_tenant_count,
    )
    if policy.decision not in {AtomDecision.ORG_SAFE, AtomDecision.GLOBAL_CANDIDATE}:
        receipt = _quarantine(root, envelope, "; ".join(policy.reasons) or policy.decision.value)
        rebuild_manifest(root)
        raise ValueError(receipt.reason)

    _write_json(root / "atoms" / _safe_atom_filename(atom_id), envelope)
    receipt = _write_receipt(root, atom_id, policy.decision.value, "accepted", verified_tenant_count)
    rebuild_manifest(root)
    return receipt


def revoke_registry_atom(
    registry_dir: str | Path,
    atom_id: str,
    reason: str,
    issuer_key_id: str = "registry-local",
) -> RegistryReceipt:
    root = _ensure_registry_dirs(registry_dir)
    tombstone = {
        "schema_version": "1.0",
        "atom_id": atom_id,
        "revoked_at": _now(),
        "reason": reason,
        "issuer_key_id": issuer_key_id,
    }
    _write_json(root / "tombstones" / _safe_atom_filename(atom_id), tombstone)
    receipt = _write_receipt(root, atom_id, "revoked", reason, None)
    rebuild_manifest(root)
    return receipt


def _verified_count_for_atom(root: Path, atom_id: str) -> int | None:
    counts: List[int] = []
    for path in (root / "receipts").glob("*.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if receipt.get("atom_id") == atom_id and isinstance(receipt.get("verified_tenant_count"), int):
            counts.append(int(receipt["verified_tenant_count"]))
    return max(counts) if counts else None


def sync_registry_to_store(registry_dir: str | Path, store: AtomStore) -> Dict[str, int]:
    """Import registry tombstones first, then accepted atom envelopes."""
    root = _ensure_registry_dirs(registry_dir)
    imported = 0
    revoked = 0
    skipped = 0

    for path in sorted((root / "tombstones").glob("*.json")):
        tombstone = json.loads(path.read_text(encoding="utf-8"))
        atom_id = tombstone["atom_id"]
        if not store.is_revoked(atom_id):
            store.revoke(atom_id, tombstone.get("reason", "registry tombstone"), tombstone.get("issuer_key_id", ""))
            revoked += 1

    for path in sorted((root / "atoms").glob("*.json")):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        atom_id = envelope["payload"]["atom_id"]
        if store.is_revoked(atom_id):
            skipped += 1
            continue
        try:
            store.add_atom(envelope, verified_tenant_count=_verified_count_for_atom(root, atom_id))
            imported += 1
        except ValueError:
            skipped += 1

    return {"imported": imported, "revoked": revoked, "skipped": skipped}
