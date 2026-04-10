"""
Guild Ed25519 Signing Module — pack authenticity via Ed25519 signatures.

Provides:
    - Key generation (random or from seed)
    - Pack signing (canonical YAML → Ed25519 signature)
    - Signature verification
    - Key encoding/decoding (URL-safe base64)

Install: pip install agent-borg[crypto]  # installs pynacl

Schema addition (optional, backwards-compatible):
    provenance:
        signature: "<base64>"      # Ed25519 signature of canonical YAML
        signer: "<agent-id>"       # e.g. "agent://hermes/core"
        verify_key: "<base64>"     # Ed25519 verify key (shareable)

Integration points:
    - borg_pull  : verify signature if present in provenance
    - borg_publish: sign pack before publishing
    - action_start: verify signature if present
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Optional

import yaml

try:
    import nacl.signing
    import nacl.encoding
    import nacl.exceptions
    _NACL_AVAILABLE = True
except ImportError:
    _NACL_AVAILABLE = False
    nacl = None  # type: ignore


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """Return True if PyNaCl is installed and usable."""
    return _NACL_AVAILABLE


def _require_nacl() -> None:
    """Raise RuntimeError if PyNaCl is not installed."""
    if not _NACL_AVAILABLE:
        raise RuntimeError(
            "Ed25519 signing requires PyNaCl. "
            "Install with: pip install agent-borg[crypto]"
        )


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def generate_signing_key(seed: Optional[bytes] = None) -> "nacl.signing.SigningKey":
    """Generate a new Ed25519 signing key.

    Args:
        seed: Optional 32-byte seed for deterministic key generation.
              If None, a random key is generated using os.urandom.

    Returns:
        A nacl.signing.SigningKey instance.

    Raises:
        ValueError: If seed is not exactly 32 bytes.
        RuntimeError: If PyNaCl is not installed.
    """
    _require_nacl()
    if seed is None:
        seed = os.urandom(32)
    if len(seed) != 32:
        raise ValueError(f"Seed must be exactly 32 bytes, got {len(seed)}")
    # nacl.signing.SigningKey expects raw 32-byte seed
    return nacl.signing.SigningKey(seed)


def derive_verify_key(signing_key: "nacl.signing.SigningKey") -> "nacl.signing.VerifyKey":
    """Derive the verify key from a signing key.

    The verify key can be safely shared (it cannot be used to sign).
    """
    _require_nacl()
    return signing_key.verify_key


# ---------------------------------------------------------------------------
# Key encoding / decoding (URL-safe base64)
# ---------------------------------------------------------------------------

def encode_key(key: bytes) -> str:
    """Encode raw bytes as a URL-safe base64 string (no padding)."""
    import base64
    return base64.urlsafe_b64encode(key).rstrip(b"=").decode("ascii")


def decode_key(encoded: str, key_type: str = "signing") -> bytes:
    """Decode a URL-safe base64 string (no padding) to raw bytes.

    Args:
        encoded: Base64-encoded key string.
        key_type: For error messages only ("signing" or "verify").

    Returns:
        Raw key bytes (32 for Ed25519).

    Raises:
        ValueError: If the encoded string is invalid base64.
    """
    import base64
    # Re-add padding
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded += "=" * padding
    try:
        return base64.urlsafe_b64decode(encoded)
    except Exception as e:
        raise ValueError(f"Invalid {key_type} key encoding: {e}")


# ---------------------------------------------------------------------------
# Canonical YAML for signing
# ---------------------------------------------------------------------------

def canonical_yaml(yaml_text: str) -> bytes:
    """Produce canonical YAML bytes for signing.

    Normalises pack YAML to a reproducible form:
      - yaml.safe_load + yaml.safe_dump with fixed settings
      - Sort keys: False (document order preserved)
      - default_flow_style: False (block style)
      - No aliases (yaml.resolver.BasicResolver behaviour)

    Returns UTF-8 encoded bytes of the canonical form.
    """
    data = yaml.safe_load(yaml_text)
    # yaml.safe_dump produces clean, consistent YAML
    canonical = yaml.safe_dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return canonical.encode("utf-8")


def canonical_pack_bytes(pack: dict) -> bytes:
    """Serialize a pack dict to canonical YAML bytes for signing."""
    canonical = yaml.safe_dump(
        pack,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return canonical.encode("utf-8")


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign_pack(pack_yaml: str, signing_key: "nacl.signing.SigningKey") -> str:
    """Sign pack YAML content with an Ed25519 signing key.

    Args:
        pack_yaml: Raw YAML string of the pack (as stored in .yaml file).
        signing_key: nacl.signing.SigningKey instance.

    Returns:
        URL-safe base64-encoded Ed25519 signature (no padding).

    Raises:
        RuntimeError: If PyNaCl is not installed.
    """
    _require_nacl()
    canonical = canonical_yaml(pack_yaml)
    signed = signing_key.sign(canonical, encoder=nacl.encoding.RawEncoder)
    # signed.signature is the 64-byte Ed25519 signature
    return encode_key(bytes(signed.signature))


def sign_pack_dict(pack: dict, signing_key: "nacl.signing.SigningKey") -> str:
    """Sign a pack dict (already parsed) with an Ed25519 signing key.

    Returns URL-safe base64-encoded signature.
    """
    _require_nacl()
    canonical = canonical_pack_bytes(pack)
    signed = signing_key.sign(canonical, encoder=nacl.encoding.RawEncoder)
    return encode_key(bytes(signed.signature))


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_pack_signature(
    pack_yaml: str,
    signature: str,
    verify_key: "nacl.signing.VerifyKey",
) -> bool:
    """Verify an Ed25519 signature over pack YAML content.

    Args:
        pack_yaml: Raw YAML string of the pack.
        signature: URL-safe base64-encoded Ed25519 signature (from sign_pack).
        verify_key: nacl.signing.VerifyKey to use for verification.

    Returns:
        True if signature is valid, False otherwise.
        Returns False if PyNaCl is not installed.

    Raises:
        ValueError: If signature encoding is invalid.
    """
    if not _NACL_AVAILABLE:
        return False
    try:
        canonical = canonical_yaml(pack_yaml)
        sig_bytes = decode_key(signature, "signature")
        verify_key.verify(canonical, sig_bytes, encoder=nacl.encoding.RawEncoder)
        return True
    except (nacl.exceptions.BadSignatureError, ValueError):
        return False


def verify_pack_signature_dict(
    pack: dict,
    signature: str,
    verify_key: "nacl.signing.VerifyKey",
) -> bool:
    """Verify an Ed25519 signature over a pack dict."""
    if not _NACL_AVAILABLE:
        return False
    try:
        canonical = canonical_pack_bytes(pack)
        sig_bytes = decode_key(signature, "signature")
        verify_key.verify(canonical, sig_bytes, encoder=nacl.encoding.RawEncoder)
        return True
    except (nacl.exceptions.BadSignatureError, ValueError):
        return False


# ---------------------------------------------------------------------------
# VerifyKey from string
# ---------------------------------------------------------------------------

def verify_key_from_string(encoded: str) -> "nacl.signing.VerifyKey":
    """Decode a URL-safe base64-encoded verify key string."""
    _require_nacl()
    raw = decode_key(encoded, "verify")
    if len(raw) != 32:
        raise ValueError(f"Verify key must be 32 bytes, got {len(raw)}")
    return nacl.signing.VerifyKey(raw)


# ---------------------------------------------------------------------------
# SigningKey from string (for loading stored keys)
# ---------------------------------------------------------------------------

def signing_key_from_string(encoded: str) -> "nacl.signing.SigningKey":
    """Decode a URL-safe base64-encoded signing key string."""
    _require_nacl()
    raw = decode_key(encoded, "signing")
    if len(raw) != 32:
        raise ValueError(f"Signing key must be 32 bytes, got {len(raw)}")
    return nacl.signing.SigningKey(raw)


# ---------------------------------------------------------------------------
# Key storage
# ---------------------------------------------------------------------------

DEFAULT_KEYS_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild" / "keys"


def store_signing_key(
    signing_key: "nacl.signing.SigningKey",
    agent_id: str,
    keys_dir: Optional[Path] = None,
) -> Path:
    """Store a signing key to disk (mode 0o600).

    Key is stored at ``keys_dir/{safe_agent_id}.key`` where safe_agent_id
    is the agent_id with ``://`` replaced by ``_`` and non-alphanumeric
    characters replaced by ``_``.

    Args:
        signing_key: nacl.signing.SigningKey to store.
        agent_id: Agent identifier (used for filename).
        keys_dir: Directory to store keys. Defaults to ~/.hermes/guild/keys/.

    Returns:
        Path to the stored key file.
    """
    _require_nacl()
    if keys_dir is None:
        keys_dir = DEFAULT_KEYS_DIR
    keys_dir = Path(keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)

    safe_id = re.sub(r"[^a-zA-Z0-9]", "_", agent_id.replace("://", "_"))
    key_file = keys_dir / f"{safe_id}.key"

    raw_bytes = bytes(signing_key)
    key_file.write_text(encode_key(raw_bytes), encoding="utf-8")
    key_file.chmod(0o600)
    return key_file


def load_signing_key(
    agent_id: str,
    keys_dir: Optional[Path] = None,
) -> Optional["nacl.signing.SigningKey"]:
    """Load a signing key from disk.

    Args:
        agent_id: Agent identifier (used for filename).
        keys_dir: Directory to store keys. Defaults to ~/.hermes/guild/keys/.

    Returns:
        The signing key, or None if the key file does not exist.
    """
    if keys_dir is None:
        keys_dir = DEFAULT_KEYS_DIR
    keys_dir = Path(keys_dir)

    safe_id = re.sub(r"[^a-zA-Z0-9]", "_", agent_id.replace("://", "_"))
    key_file = keys_dir / f"{safe_id}.key"

    if not key_file.exists():
        return None

    encoded = key_file.read_text(encoding="utf-8").strip()
    return signing_key_from_string(encoded)


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------

def pack_has_signature(pack: dict) -> bool:
    """Return True if the pack has a non-empty signature in provenance."""
    provenance = pack.get("provenance", {})
    sig = provenance.get("signature", "")
    return bool(sig and isinstance(sig, str))


def pack_has_verify_key(pack: dict) -> bool:
    """Return True if the pack has a non-empty verify_key in provenance."""
    provenance = pack.get("provenance", {})
    vk = provenance.get("verify_key", "")
    return bool(vk and isinstance(vk, str))


def check_pack_signature(pack: dict, pack_yaml: str) -> dict:
    """Full signature check result dict.

    Returns:
        {
            "signed": bool,       # pack has a signature field
            "has_key": bool,      # pack has a verify_key field
            "valid": bool | None, # True=valid, False=invalid, None=can't verify
            "signer": str,        # signer field or ""
            "error": str,         # error message if any
        }
    """
    provenance = pack.get("provenance", {})
    signature = provenance.get("signature", "")
    signer = provenance.get("signer", "")
    verify_key_str = provenance.get("verify_key", "")

    if not signature:
        return {"signed": False, "has_key": bool(verify_key_str), "valid": None, "signer": signer, "error": ""}

    if not verify_key_str:
        return {"signed": True, "has_key": False, "valid": None, "signer": signer, "error": "No verify_key in provenance"}

    if not _NACL_AVAILABLE:
        return {"signed": True, "has_key": True, "valid": None, "signer": signer, "error": "PyNaCl not installed"}

    try:
        vk = verify_key_from_string(verify_key_str)
        valid = verify_pack_signature(pack_yaml, signature, vk)
        return {"signed": True, "has_key": True, "valid": valid, "signer": signer, "error": "" if valid else "Signature mismatch"}
    except Exception as e:
        return {"signed": True, "has_key": True, "valid": False, "signer": signer, "error": str(e)}
