"""
Centralized Borg storage path resolution.

BORG_HOME is the product-level home (default: ~/.borg). It owns trace, V3,
atom, embedding, and failure-memory state. BORG_DIR is the workflow/pack
subdirectory used by older Guild/Borg code (default: BORG_HOME/guild).

All Borg code should import resolver helpers from this module rather than
hardcoding ~/.borg, ~/.hermes/borg, or ~/.hermes/guild paths.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _expand(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser()


_DEFAULT_BORG_HOME = Path.home() / ".borg"
_DEFAULT_BORG_DIR = _DEFAULT_BORG_HOME / "guild"

# Backward-compatible module constants. Call resolver functions for new code;
# tests may still patch BORG_DIR on importing modules.
BORG_HOME = _expand(os.environ["BORG_HOME"]) if "BORG_HOME" in os.environ else _DEFAULT_BORG_HOME
BORG_DIR = _expand(os.environ["BORG_DIR"]) if "BORG_DIR" in os.environ else BORG_HOME / "guild"


def get_borg_home() -> Path:
    """Return the Borg product home directory.

    Priority:
    1. BORG_HOME, when explicitly set.
    2. BORG_DIR, as a backwards-compatible isolation root for older callers/tests.
    3. ~/.borg.
    """
    if "BORG_HOME" in os.environ:
        return _expand(os.environ["BORG_HOME"])
    if "BORG_DIR" in os.environ:
        return _expand(os.environ["BORG_DIR"])
    # Use Path.home() dynamically so tests and embedded callers that monkeypatch
    # HOME/Path.home after module import still get isolated storage.  The
    # module-level BORG_HOME constant is kept only for legacy callers that patch
    # imported symbols directly.
    return Path.home() / ".borg"


def get_borg_dir() -> Path:
    """Return the workflow/pack store directory.

    BORG_DIR remains an explicit override. Without it, workflow packs live under
    BORG_HOME/guild so a single BORG_HOME isolates all Borg state for first users
    and MCP clients.

    When called from a module that has a module-level BORG_DIR constant, a test
    patch of that symbol still takes effect if it differs from this module's
    canonical BORG_DIR.
    """
    if "BORG_DIR" in os.environ:
        return _expand(os.environ["BORG_DIR"])

    frame = sys._getframe(1)
    try:
        caller_borg_dir = frame.f_globals.get("BORG_DIR")
        if caller_borg_dir is not None and Path(caller_borg_dir) != BORG_DIR:
            return Path(caller_borg_dir)
    finally:
        del frame

    return get_borg_home() / "guild"


def get_trace_db_path() -> Path:
    return get_borg_home() / "traces.db"


def get_v3_db_path() -> Path:
    return get_borg_home() / "borg_v3.db"


def get_atom_db_path() -> Path:
    return get_borg_home() / "atoms.db"


def get_embedding_cache_path() -> Path:
    return get_borg_home() / "embeddings.pkl"


def get_embedding_index_path() -> Path:
    return get_borg_home() / "embeddings_index.pkl"


def get_failure_memory_dir() -> Path:
    return get_borg_home() / "failures"


def safe_dir_exists(path: Path) -> bool:
    """Existence probe that treats unreadable as absent (D-018).

    On Python 3.12 ``Path.exists()``/``is_dir()`` RAISE PermissionError for
    paths under an untraversable directory (EACCES is not in pathlib's
    ignored-errno set). Maintainer-checkout fallback paths live under /root,
    which is 0700 on every normal machine — probing them crashed
    ``borg convert --all`` for every non-root user of the published wheel.
    An unreadable fallback dir must mean "not there", never a crash.
    """
    try:
        return path.exists()
    except OSError:
        return False


def get_feedback_db_path() -> Path:
    """Feedback signals share the trace DB for backwards-compatible schema use."""
    return get_trace_db_path()


def get_tenant_secret_path() -> Path:
    return get_borg_home() / "tenant_secret"


def get_paths_summary() -> dict[str, str]:
    """Machine-readable summary for doctor/runtime fingerprint/tests."""
    borg_home = get_borg_home()
    borg_dir = get_borg_dir()
    return {
        "borg_home": str(borg_home),
        "borg_dir": str(borg_dir),
        "trace_db_path": str(get_trace_db_path()),
        "v3_db_path": str(get_v3_db_path()),
        "guild_db_path": str(borg_dir / "guild.db"),
        "atom_db_path": str(get_atom_db_path()),
        "embedding_cache_path": str(get_embedding_cache_path()),
        "embedding_index_path": str(get_embedding_index_path()),
        "failure_memory_dir": str(get_failure_memory_dir()),
        "tenant_secret_path": str(get_tenant_secret_path()),
    }
