"""Federation kill-switch: a one-command global disable for all atom egress.

This is the pilot-safety panic button (PART 10 gate #27). It is a SECOND,
independent layer on top of the opt-in ``local_only`` default: even if a user has
opted into sharing, ``borg sharing off`` instantly halts every shareable-atom
egress path, and the guard fails closed.

State is a single sentinel file under ``BORG_HOME`` (``SHARING_DISABLED``).
A file is used deliberately: it is atomic to create/remove, needs no config
parser, and is trivial for an operator to inspect, back up, or drop in by hand
during an incident. Its mere existence engages the kill-switch; the JSON body is
advisory metadata (reason + timestamp).

Egress entry points (``borg publish``, ``borg atom publish``, non-local
``borg atom distill``, and the ``borg_publish`` MCP tool) call
``assert_sharing_allowed`` and refuse when the switch is engaged.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from borg.core.dirs import get_borg_home

SENTINEL_NAME = "SHARING_DISABLED"


class SharingDisabledError(RuntimeError):
    """Raised when an egress operation is attempted while the kill-switch is engaged."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sentinel_path(borg_home: Optional[Path | str] = None) -> Path:
    home = Path(borg_home) if borg_home is not None else get_borg_home()
    return home / SENTINEL_NAME


def is_sharing_disabled(borg_home: Optional[Path | str] = None) -> bool:
    """Return True when the federation kill-switch is engaged."""
    return _sentinel_path(borg_home).exists()


def disable_sharing(reason: str = "", *, borg_home: Optional[Path | str] = None) -> Dict[str, Any]:
    """Engage the kill-switch: block all atom egress. Idempotent."""
    path = _sentinel_path(borg_home)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "disabled": True,
        "reason": (reason or "manual kill-switch").strip()[:500],
        "disabled_at": _utc_now(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)  # atomic engage
    return record


def enable_sharing(*, borg_home: Optional[Path | str] = None) -> Dict[str, Any]:
    """Disengage the kill-switch: re-allow opt-in atom egress. Idempotent."""
    path = _sentinel_path(borg_home)
    was_disabled = path.exists()
    if was_disabled:
        path.unlink()
    return {"disabled": False, "was_disabled": was_disabled, "enabled_at": _utc_now()}


def sharing_status(borg_home: Optional[Path | str] = None) -> Dict[str, Any]:
    """Return the current kill-switch state (and its metadata if engaged)."""
    path = _sentinel_path(borg_home)
    if not path.exists():
        return {"disabled": False, "killswitch_engaged": False, "sentinel": str(path)}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            record = {}
    except Exception:
        record = {}
    return {"disabled": True, "killswitch_engaged": True, "sentinel": str(path), **record}


def assert_sharing_allowed(operation: str = "publish", *, borg_home: Optional[Path | str] = None) -> None:
    """Fail closed if the kill-switch is engaged.

    Raises:
        SharingDisabledError: when sharing is disabled, with a message that names
        the blocked operation and how to re-enable.
    """
    if is_sharing_disabled(borg_home):
        raise SharingDisabledError(
            f"federation kill-switch engaged: {operation} blocked. "
            f"No learning atoms will leave this machine. "
            f"Run `borg sharing on` to re-enable atom sharing, or `borg sharing status` for details."
        )
