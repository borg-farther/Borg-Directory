"""
Centralized BORG_DIR resolution.

All Guild v2 code should import get_borg_dir() from here rather than
hardcoding paths.  BORG_DIR is configurable via the BORG_DIR environment
variable, defaulting to ~/.hermes/guild.
"""

import inspect
import os
import sys
from pathlib import Path

#: Default path used when BORG_DIR env var is not set.
_DEFAULT_BORG_DIR = Path.home() / ".hermes" / "guild"

#: Module-level BORG_DIR.  Respects BORG_DIR env var if set.
#: Exposed as a module constant so that code that imports BORG_DIR from
#: here (e.g. "from borg.core.search import BORG_DIR") remains compatible
#: with existing tests that patch the symbol directly.
BORG_DIR = Path(os.environ["BORG_DIR"]) if "BORG_DIR" in os.environ else _DEFAULT_BORG_DIR


def get_borg_dir() -> Path:
    """
    Return the current BORG_DIR path.

    Respects the BORG_DIR environment variable.  If set, returns that path.
    Otherwise returns ~/.hermes/guild.

    When called from a module that has a module-level BORG_DIR constant
    (imported from this module), the caller's module-level constant is
    checked first so that tests patching that symbol take effect.
    """
    # Fast path: env var always wins (primary configuration mechanism)
    if "BORG_DIR" in os.environ:
        return Path(os.environ["BORG_DIR"])

    # Check the calling module's namespace for a patched BORG_DIR.
    # This allows tests to patch e.g. borg.core.search.BORG_DIR and have
    # those patches visible to search.py functions that call get_borg_dir().
    frame = sys._getframe(1)  # caller's frame
    try:
        caller_globals = frame.f_globals
        borg_dir = caller_globals.get("BORG_DIR")
        if borg_dir is not None:
            return borg_dir
    finally:
        del frame

    # Fall back to this module's constant
    return BORG_DIR
