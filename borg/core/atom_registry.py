"""Filesystem staging registry for signed, sanitized learning atoms.

This is the M1 local/staging propagation primitive, not an internet federation
service. It proves the safe loop shape:

    signed atom -> registry receipt -> clean client sync -> tombstone sync

The registry never accepts raw traces and never trusts self-declared global
quorum from atom payloads.
"""

from __future__ import annotations

import copy
import calendar
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin
from urllib.request import urlopen

from borg.core.atom_policy import AtomDecision, classify_atom_policy
from borg.core.atom_store import AtomStore
from borg.core.crypto import derive_verify_key, decode_key, encode_key, verify_key_from_string
from borg.core.learning_atoms import learning_atom_key_id_from_verify_key, verify_signed_atom


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


def _now_epoch() -> float:
    return time.time()


def _iso_from_epoch(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _epoch_from_iso(value: str) -> float:
    return float(calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ")))


def _canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _entry_for_file(root: Path, relative_path: str) -> Dict[str, Any]:
    path = root / relative_path
    entry: Dict[str, Any] = {
        "path": relative_path,
        "sha256": _sha256_file(path),
        "size": path.stat().st_size,
    }
    if relative_path.startswith("atoms/"):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope.get("payload", {})
            atom_id = payload.get("atom_id")
            entry["atom_id"] = atom_id
            verified = _verified_count_for_atom(root, atom_id) if atom_id else None
            if verified is not None:
                entry["verified_tenant_count"] = verified
        except Exception:
            pass
    elif relative_path.startswith("tombstones/"):
        try:
            tombstone = json.loads(path.read_text(encoding="utf-8"))
            entry["atom_id"] = tombstone.get("atom_id")
            entry["revoked_at"] = tombstone.get("revoked_at")
        except Exception:
            pass
    return entry


def _registry_entries(root: Path, child: str) -> List[Dict[str, Any]]:
    return [_entry_for_file(root, f"{child}/{path.name}") for path in sorted((root / child).glob("*.json"))]


def _sign_registry_payload(payload: Dict[str, Any], signing_key: Any) -> Dict[str, Any]:
    """Sign registry metadata with Ed25519 over canonical JSON payload bytes."""
    from nacl import encoding

    verify_key = derive_verify_key(signing_key)
    verify_key_str = encode_key(bytes(verify_key))
    key_id = learning_atom_key_id_from_verify_key(verify_key)
    signed = signing_key.sign(_canonical_json_bytes(payload), encoder=encoding.RawEncoder)
    return {
        "type": "borg_registry_manifest",
        "envelope_version": "1.0",
        "payload": payload,
        "signature": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "verify_key": verify_key_str,
            "signature_b64url": encode_key(bytes(signed.signature)),
            "signed_at": _now(),
        },
    }


def write_signed_registry_manifest(
    registry_dir: str | Path,
    signing_key: Any,
    *,
    sequence: int,
    channel: str = "global",
    expires_in_seconds: int = 300,
    previous_manifest_hash: str | None = None,
    manifest_payload_override: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Write a signed hosted-registry manifest and return its envelope.

    The signed manifest is the only authority remote clients trust. Directory
    listings, unsigned `manifest.json`, and atom payload hints are advisory only.
    """
    root = _ensure_registry_dirs(registry_dir)
    payload = copy.deepcopy(manifest_payload_override) if manifest_payload_override is not None else {
        "schema_version": "1.0",
        "type": "borg_registry_manifest_payload",
        "channel": channel,
        "sequence": int(sequence),
        "generated_at": _now(),
        "expires_at": _iso_from_epoch(_now_epoch() + expires_in_seconds),
        "previous_manifest_hash": previous_manifest_hash,
        "atoms": _registry_entries(root, "atoms"),
        "tombstones": _registry_entries(root, "tombstones"),
        "receipts": _registry_entries(root, "receipts"),
    }
    payload["channel"] = channel
    payload["sequence"] = int(sequence)
    signed = _sign_registry_payload(payload, signing_key)
    _write_json(root / "manifest.signed.json", signed)
    return signed


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


def _verify_registry_manifest_signature(
    signed_manifest: Dict[str, Any],
    *,
    trusted_registry_key_id: str,
    channel: str,
    now_epoch: float | None = None,
) -> Dict[str, Any]:
    if "signature" not in signed_manifest:
        raise ValueError("registry manifest signature is required")
    if signed_manifest.get("type") != "borg_registry_manifest":
        raise ValueError("registry manifest type must be borg_registry_manifest")
    if signed_manifest.get("envelope_version") != "1.0":
        raise ValueError("registry manifest envelope_version must be 1.0")
    payload = signed_manifest.get("payload")
    signature = signed_manifest.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        raise ValueError("registry manifest payload and signature are required")
    if signature.get("algorithm") != "ed25519":
        raise ValueError("registry manifest signature algorithm must be ed25519")
    verify_key = verify_key_from_string(str(signature.get("verify_key", "")))
    derived_key_id = learning_atom_key_id_from_verify_key(verify_key)
    if signature.get("key_id") != derived_key_id:
        raise ValueError("registry manifest signature key_id does not match verify key")
    if trusted_registry_key_id != derived_key_id:
        raise ValueError("registry manifest signed by untrusted registry key")
    from nacl import encoding, exceptions

    try:
        verify_key.verify(
            _canonical_json_bytes(payload),
            decode_key(str(signature.get("signature_b64url", "")), "signature"),
            encoder=encoding.RawEncoder,
        )
    except exceptions.BadSignatureError as exc:
        raise ValueError("registry manifest signature mismatch") from exc
    except Exception as exc:
        raise ValueError(f"registry manifest signature verification failed: {exc}") from exc
    if payload.get("channel") != channel:
        raise ValueError("registry manifest channel mismatch")
    expires_at = payload.get("expires_at")
    if not expires_at:
        raise ValueError("registry manifest expires_at is required")
    now = _now_epoch() if now_epoch is None else now_epoch
    if _epoch_from_iso(str(expires_at)) < now:
        raise ValueError("registry manifest is expired")
    return payload


def _fetch_registry_bytes(base_url: str | Path, relative_path: str, timeout: float = 10.0) -> bytes:
    rel = str(relative_path).replace("\\", "/")
    if rel.startswith("/") or ".." in rel.split("/"):
        raise ValueError("registry manifest contains unsafe relative path")
    base = str(base_url)
    if base.startswith("http://") or base.startswith("https://"):
        url = urljoin(base.rstrip("/") + "/", rel)
        with urlopen(url, timeout=timeout) as response:  # nosec B310 - trusted registry URL supplied by config/test.
            return response.read()
    return (Path(base_url) / rel).read_bytes()


def _validate_manifest_entry(base_url: str | Path, entry: Dict[str, Any]) -> Dict[str, Any]:
    path = str(entry.get("path", ""))
    if not path:
        raise ValueError("registry manifest entry missing path")
    body = _fetch_registry_bytes(base_url, path)
    expected_size = int(entry.get("size", -1))
    if expected_size != len(body):
        raise ValueError(f"registry file size mismatch for {path}")
    expected_hash = str(entry.get("sha256", ""))
    actual_hash = _sha256_bytes(body)
    if expected_hash != actual_hash:
        raise ValueError(f"registry file hash mismatch for {path}")
    return json.loads(body.decode("utf-8"))


def _load_sync_state(state_path: str | Path | None) -> Dict[str, Any]:
    if not state_path:
        return {}
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_sync_state(state_path: str | Path | None, state: Dict[str, Any]) -> None:
    if not state_path:
        return
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, state)


def sync_signed_registry_to_store(
    registry_url: str | Path,
    store: AtomStore,
    *,
    trusted_registry_key_id: str,
    channel: str = "global",
    state_path: str | Path | None = None,
    max_revocation_convergence_seconds: float | None = None,
    now_epoch: float | None = None,
) -> Dict[str, Any]:
    """Sync a hosted signed registry manifest into a clean local AtomStore.

    Clients trust only `manifest.signed.json`: the registry signature, monotonic
    sequence, expiry, and per-file hashes all have to pass before any atom is
    imported. Tombstones are applied first so revocation always wins.
    """
    manifest_bytes = _fetch_registry_bytes(registry_url, "manifest.signed.json")
    signed_manifest = json.loads(manifest_bytes.decode("utf-8"))
    payload = _verify_registry_manifest_signature(
        signed_manifest,
        trusted_registry_key_id=trusted_registry_key_id,
        channel=channel,
        now_epoch=now_epoch,
    )
    manifest_hash = _sha256_bytes(_canonical_json_bytes(signed_manifest))
    sequence = int(payload.get("sequence", 0))
    state = _load_sync_state(state_path)
    last_sequence = int(state.get("last_sequence", 0) or 0)
    last_hash = state.get("last_manifest_hash")
    if sequence < last_sequence or (sequence == last_sequence and last_hash and last_hash != manifest_hash):
        raise ValueError("registry manifest replay detected")

    # Validate all files before mutating the store. A hash mismatch or network
    # failure cannot leave a partial import without the corresponding tombstones.
    tombstones = [_validate_manifest_entry(registry_url, entry) for entry in payload.get("tombstones", [])]
    atom_pairs = [(_validate_manifest_entry(registry_url, entry), entry) for entry in payload.get("atoms", [])]

    revoked = 0
    max_convergence = 0.0
    now = _now_epoch() if now_epoch is None else now_epoch
    for tombstone in tombstones:
        atom_id = tombstone["atom_id"]
        if not store.is_revoked(atom_id):
            store.revoke(atom_id, tombstone.get("reason", "registry tombstone"), tombstone.get("issuer_key_id", ""))
            revoked += 1
        revoked_at = tombstone.get("revoked_at")
        if revoked_at:
            max_convergence = max(max_convergence, max(0.0, now - _epoch_from_iso(str(revoked_at))))

    imported = 0
    skipped = 0
    for envelope, entry in atom_pairs:
        atom_id = envelope["payload"]["atom_id"]
        if store.is_revoked(atom_id):
            skipped += 1
            continue
        try:
            store.add_atom(envelope, verified_tenant_count=entry.get("verified_tenant_count"))
            imported += 1
        except ValueError:
            skipped += 1

    if max_revocation_convergence_seconds is not None and max_convergence > max_revocation_convergence_seconds:
        raise ValueError("registry revocation convergence SLO exceeded")

    _write_sync_state(
        state_path,
        {
            "last_sequence": sequence,
            "last_manifest_hash": manifest_hash,
            "synced_at": _iso_from_epoch(now),
            "channel": channel,
        },
    )
    return {
        "remote": str(registry_url).startswith(("http://", "https://")),
        "manifest_sequence": sequence,
        "manifest_hash": manifest_hash,
        "imported": imported,
        "revoked": revoked,
        "skipped": skipped,
        "revocation_convergence_seconds": max_convergence,
    }
