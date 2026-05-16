"""Tenant pseudonym helpers for privacy-safe learning atoms.

This module intentionally never persists raw tenant identifiers in atom payloads.
It derives stable HMAC pseudonyms so org/global policy can reason about tenant
provenance without leaking tenant names, domains, emails, or account IDs.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

from borg.core.dirs import get_tenant_secret_path


DEFAULT_TENANT_SECRET_FILE = get_tenant_secret_path()


def load_or_create_tenant_secret(path: str | None = None) -> bytes:
    """Load a local tenant HMAC secret, creating one with 0600 permissions if absent."""
    secret_path = Path(path) if path else DEFAULT_TENANT_SECRET_FILE
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if secret_path.exists():
        return secret_path.read_bytes().strip()
    secret = os.urandom(32).hex().encode("ascii")
    secret_path.write_bytes(secret)
    try:
        secret_path.chmod(0o600)
    except Exception:
        pass
    return secret


def tenant_pseudonym(tenant_identifier: str, secret: bytes | str | None = None) -> str:
    """Return a non-reversible tenant pseudonym: hmac-sha256:<hex>.

    `tenant_identifier` may be an org slug/email/domain locally, but callers must
    only store this returned value in atoms. Empty identifiers still produce a
    stable pseudonym for the local installation so M1 can stay zero-config.
    """
    if secret is None:
        secret_b = load_or_create_tenant_secret()
    elif isinstance(secret, str):
        secret_b = secret.encode("utf-8")
    else:
        secret_b = secret
    msg = (tenant_identifier or "local-default-tenant").encode("utf-8")
    digest = hmac.new(secret_b, msg, hashlib.sha256).hexdigest()
    return "hmac-sha256:" + digest


def is_valid_tenant_pseudonym(value: object) -> bool:
    """True when value has the only tenant identifier format allowed in atoms."""
    if not isinstance(value, str):
        return False
    if not value.startswith("hmac-sha256:"):
        return False
    suffix = value.split(":", 1)[1]
    return len(suffix) == 64 and all(c in "0123456789abcdef" for c in suffix)


def apply_tenant_pseudonym(atom: dict, tenant_identifier: str = "", secret: bytes | str | None = None) -> dict:
    """Return a copy of atom with only pseudonymous tenant provenance attached."""
    import copy

    updated = copy.deepcopy(atom)
    updated.setdefault("trust", {})["tenant_pseudonym"] = tenant_pseudonym(tenant_identifier, secret)
    return updated
