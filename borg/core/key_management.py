"""Root-key separation and key revocation for the federated registry (S0/B2).

Trust hierarchy (see docs/FEDERATION_DESIGN.md and docs/KEY_MANAGEMENT.md):

    root key (offline)  — signs ONLY the key directory below
      └── manifest keys (online, rotatable) — sign manifest.signed.json
            └── atom submitter keys (per tenant) — sign learning-atom envelopes

Before this module, clients pinned the manifest signing key directly
(`trusted_registry_key_id`), so rotating or revoking a compromised online key
meant re-configuring every client — catastrophic to retrofit after launch.
Now clients can pin the OFFLINE root key once; the registry serves a signed
``keys.signed.json`` key directory naming the currently-trusted manifest keys
and the revoked key ids. Compromising an online manifest key is then survivable:
the operator revokes it in the directory and signs a new one with the root key
that never touched the registry host.

Fail-closed rules:
  * the key directory must verify against the pinned root key id, match the
    channel, and be unexpired — otherwise NOTHING syncs;
  * revocation wins: a key id present in ``revoked_key_ids`` is untrusted even
    if it also appears in ``manifest_keys`` (and revoked atom-submitter keys
    cause their atoms to be skipped on sync);
  * the directory carries its own monotonic ``sequence`` so a replayed older
    directory cannot resurrect a revoked key (state persisted alongside the
    manifest sync state).
"""

from __future__ import annotations

import calendar
import copy
import hashlib
import json
import time
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

from borg.core.crypto import decode_key, derive_verify_key, encode_key, verify_key_from_string
from borg.core.learning_atoms import learning_atom_key_id_from_verify_key

KEY_DIRECTORY_TYPE = "borg_registry_key_directory"
KEY_DIRECTORY_PAYLOAD_TYPE = "borg_registry_key_directory_payload"
ENVELOPE_VERSION = "1.0"
SCHEMA_VERSION = "1.0"


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


def key_directory_hash(envelope: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(envelope)).hexdigest()


def build_key_directory_payload(
    *,
    channel: str,
    sequence: int,
    manifest_verify_keys: Sequence[str],
    revoked_key_ids: Sequence[str] = (),
    expires_in_seconds: int = 24 * 3600,
) -> Dict[str, Any]:
    """Build the unsigned key-directory payload.

    ``manifest_verify_keys`` are encoded Ed25519 verify keys (the same encoding
    `sign_learning_atom` uses); key ids are DERIVED from them here so a payload
    can never claim a key id that does not match its key material.
    """
    manifest_keys: List[Dict[str, str]] = []
    for encoded in manifest_verify_keys:
        verify_key = verify_key_from_string(str(encoded))
        manifest_keys.append(
            {
                "role": "manifest",
                "key_id": learning_atom_key_id_from_verify_key(verify_key),
                "verify_key": str(encoded),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "type": KEY_DIRECTORY_PAYLOAD_TYPE,
        "channel": str(channel),
        "sequence": int(sequence),
        "generated_at": _now(),
        "expires_at": _iso_from_epoch(_now_epoch() + int(expires_in_seconds)),
        "manifest_keys": manifest_keys,
        "revoked_key_ids": sorted({str(k) for k in revoked_key_ids}),
    }


def sign_key_directory(payload: Dict[str, Any], root_signing_key: Any) -> Dict[str, Any]:
    """Sign a key-directory payload with the OFFLINE root key."""
    from nacl import encoding

    payload = copy.deepcopy(payload)
    verify_key = derive_verify_key(root_signing_key)
    key_id = learning_atom_key_id_from_verify_key(verify_key)
    signed = root_signing_key.sign(_canonical_json_bytes(payload), encoder=encoding.RawEncoder)
    return {
        "type": KEY_DIRECTORY_TYPE,
        "envelope_version": ENVELOPE_VERSION,
        "payload": payload,
        "signature": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "verify_key": encode_key(bytes(verify_key)),
            "signature_b64url": encode_key(bytes(signed.signature)),
            "signed_at": _now(),
        },
    }


def verify_key_directory(
    envelope: Dict[str, Any],
    *,
    trusted_root_key_id: str,
    channel: str,
    now_epoch: float | None = None,
) -> Dict[str, Any]:
    """Verify a signed key directory against the pinned offline root key.

    Returns the verified payload; raises ValueError on ANY mismatch (fail closed).
    """
    if not isinstance(envelope, dict) or "signature" not in envelope:
        raise ValueError("key directory signature is required")
    if envelope.get("type") != KEY_DIRECTORY_TYPE:
        raise ValueError(f"key directory type must be {KEY_DIRECTORY_TYPE}")
    if envelope.get("envelope_version") != ENVELOPE_VERSION:
        raise ValueError("key directory envelope_version must be 1.0")
    payload = envelope.get("payload")
    signature = envelope.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        raise ValueError("key directory payload and signature are required")
    if payload.get("type") != KEY_DIRECTORY_PAYLOAD_TYPE:
        raise ValueError("key directory payload type mismatch")
    if signature.get("algorithm") != "ed25519":
        raise ValueError("key directory signature algorithm must be ed25519")

    verify_key = verify_key_from_string(str(signature.get("verify_key", "")))
    derived_key_id = learning_atom_key_id_from_verify_key(verify_key)
    if signature.get("key_id") != derived_key_id:
        raise ValueError("key directory signature key_id does not match verify key")
    if str(trusted_root_key_id) != derived_key_id:
        raise ValueError("key directory signed by untrusted root key")

    from nacl import encoding, exceptions

    try:
        verify_key.verify(
            _canonical_json_bytes(payload),
            decode_key(str(signature.get("signature_b64url", "")), "signature"),
            encoder=encoding.RawEncoder,
        )
    except exceptions.BadSignatureError as exc:
        raise ValueError("key directory signature mismatch") from exc
    except Exception as exc:
        raise ValueError(f"key directory signature verification failed: {exc}") from exc

    if payload.get("channel") != channel:
        raise ValueError("key directory channel mismatch")
    expires_at = payload.get("expires_at")
    if not expires_at:
        raise ValueError("key directory expires_at is required")
    now = _now_epoch() if now_epoch is None else now_epoch
    if _epoch_from_iso(str(expires_at)) < now:
        raise ValueError("key directory is expired")
    if not isinstance(payload.get("sequence"), int):
        raise ValueError("key directory sequence must be an integer")

    # Key ids must be derivable from their key material — a directory cannot
    # alias an arbitrary id onto different key bytes.
    for entry in payload.get("manifest_keys", []):
        entry_key = verify_key_from_string(str(entry.get("verify_key", "")))
        if entry.get("key_id") != learning_atom_key_id_from_verify_key(entry_key):
            raise ValueError("key directory entry key_id does not match its verify key")
    return payload


def resolve_trusted_manifest_key_ids(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    """Return (active manifest key ids, revoked key ids). Revocation wins."""
    revoked = {str(k) for k in payload.get("revoked_key_ids", [])}
    active = {
        str(entry.get("key_id"))
        for entry in payload.get("manifest_keys", [])
        if entry.get("role") == "manifest" and entry.get("key_id")
    }
    return active - revoked, revoked


def assert_key_not_revoked(key_id: str, revoked_key_ids: Iterable[str], *, what: str = "key") -> None:
    if str(key_id) in {str(k) for k in revoked_key_ids}:
        raise ValueError(f"{what} {key_id} is revoked")
