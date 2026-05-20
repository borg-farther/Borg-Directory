"""
Guild URI Resolution and Pack Fetch Module — T1.4 standalone extraction.

Zero imports from tools.* or guild_mcp.* — stdlib + yaml only (urllib is OK).

Provides:
  resolve_guild_uri()    — resolve guild:// URIs to GitHub raw URLs
  fetch_with_retry()     — fetch content from URL or local path with retry logic
  get_available_pack_names() — collect pack names from local dirs and remote index
  fuzzy_match_pack()      — fuzzy-match a pack name to available packs
"""

import difflib
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import List, Tuple
from urllib.request import urlopen

import yaml

from borg.core.dirs import get_borg_dir

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REPO = os.environ.get("BORG_PACK_REPO", "borg-farther/Borg-Directory")
DEFAULT_BRANCH = "main"
REMOTE_PACKS_PATH = "borg/seeds_data/packs"
BORG_DIR = get_borg_dir()
INDEX_URL = f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}/index.json"

_CACHE_TTL = 300  # 5 minutes
_index_cache: Tuple[object, float] = (None, 0.0)

# ---------------------------------------------------------------------------
# URI resolution
# ---------------------------------------------------------------------------

def normalize_pack_uri(uri: str, *, canonical_scheme: str = "borg") -> str:
    """Normalize pack identifiers to one canonical URI spelling.

    Borg historically used both ``guild://`` and ``borg://`` in docs, tests, and
    MCP payloads. First users should not pay for that history: all public entry
    points accept bare names, ``borg://...``, and ``guild://...``. Internally we
    normalize to ``borg://hermes/<pack>`` unless a caller explicitly requests the
    legacy ``guild`` scheme for display/back-compat.
    """
    if not uri or not str(uri).strip():
        raise ValueError("URI cannot be empty")

    raw = str(uri).strip()
    if raw.startswith(("https://", "http://", "/")):
        return raw

    scheme = f"{canonical_scheme}://"
    if raw.startswith(("borg://", "guild://")):
        scheme_end = raw.index("://") + 3
        path_part = raw[scheme_end:]
        if not path_part:
            raise ValueError(f"Invalid guild URI: {raw}")
        parts = path_part.split("/", 1)
        name = parts[1] if len(parts) == 2 else parts[0]
    elif re.match(r'^[\w-]+$', raw):
        name = raw
    else:
        raise ValueError(
            f"Unsupported URI scheme: {raw}. Use: borg://domain/pack-name, "
            "guild://domain/pack-name, or a bare pack name."
        )

    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError(f"Invalid guild URI: {raw}")
    return f"{scheme}hermes/{name}"


def _pack_name_from_uri(uri: str) -> str:
    """Return the sanitized pack name from any supported pack identifier."""
    normalized = normalize_pack_uri(uri)
    if normalized.startswith(("https://", "http://", "/")):
        return Path(normalized).stem.replace(".workflow", "")
    return normalized.rsplit("/", 1)[-1]


def resolve_guild_uri(uri: str) -> str:
    """Resolve a Borg/Guild URI to a fetchable URL or local path.

    Supported schemes:
      borg://domain/name   -> GitHub raw URL (preferred)
      guild://domain/name  -> GitHub raw URL (legacy alias)
      bare-pack-name       -> GitHub raw URL for borg://hermes/bare-pack-name
      https://... or http://... -> passthrough
      /local/path          -> passthrough (absolute path)
    """
    if not uri or not str(uri).strip():
        raise ValueError("URI cannot be empty")

    raw = str(uri).strip()
    if raw.startswith("https://") or raw.startswith("http://"):
        return raw
    if raw.startswith("/"):
        return raw

    name = _pack_name_from_uri(raw)

    # Prefer packaged seed packs. This keeps the day-one
    # `borg try systematic-debugging` path working in fresh installs even when
    # the remote GitHub index or raw URL is unavailable, without letting a
    # user's unrelated local BORG_DIR shadow explicit remote URI resolution.
    local_candidates = [
        Path(__file__).parent.parent / "seeds_data" / "packs" / f"{name}.workflow.yaml",
        Path(__file__).parent.parent / "seeds_data" / "packs" / f"{name}.yaml",
    ]
    for candidate in local_candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    return (
        f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}"
        f"/{REMOTE_PACKS_PATH}/{name}.workflow.yaml"
    )


# ---------------------------------------------------------------------------
# Content fetching with retry
# ---------------------------------------------------------------------------

def fetch_with_retry(url_or_path: str, retries: int = 1) -> Tuple[str, str]:
    """Fetch content from a URL or local path with optional retry.

    Attempts local file read first, then URL fetch with retry on failure.
    Sleeps exponentially between retries: 1s, 2s, ...

    Args:
        url_or_path: A local file path (absolute) or a http(s):// URL.
        retries: Number of retries on failure (default 1, meaning 2 attempts).

    Returns:
        A (content, error) tuple. On success content is the fetched text and
        error is empty. On failure content is empty and error describes the failure.
    """
    path = Path(url_or_path)
    if path.exists():
        try:
            return (path.read_text(encoding="utf-8"), "")
        except Exception as exc:
            return ("", str(exc))

    last_err = ""
    for attempt in range(retries + 1):
        try:
            req = urlopen(url_or_path, timeout=15)
            content = req.read().decode("utf-8")
            return (content, "")
        except Exception as exc:
            last_err = str(exc)
            if attempt < retries:
                time.sleep(1 * (attempt + 1))

    return ("", last_err)


# ---------------------------------------------------------------------------
# Index fetching (cached)
# ---------------------------------------------------------------------------

def _fetch_index() -> dict:
    """Fetch index.json from the guild-packs repo (cached, 5-minute TTL)."""
    global _index_cache
    now = time.time()
    if _index_cache[0] is not None and (now - _index_cache[1]) < _CACHE_TTL:
        return _index_cache[0]

    try:
        with urlopen(INDEX_URL, timeout=15) as resp:
            import json
            data = json.loads(resp.read().decode("utf-8"))
        _index_cache = (data, now)
        return data
    except Exception as e:
        if _index_cache[0] is not None:
            return _index_cache[0]
        # Don't fail search when remote index is unreachable — seeds still work.
        # Log at debug level so production users aren't affected by network issues.
        import logging
        logging.getLogger("borg.uri").debug("Index fetch failed, using empty index: %s", e)
        return {"packs": []}


# ---------------------------------------------------------------------------
# Pack name discovery and fuzzy matching
# ---------------------------------------------------------------------------

def get_available_pack_names() -> List[str]:
    """Collect available pack names from local guild dir and remote index.

    Local packs are found under BORG_DIR/*/pack.yaml and BORG_DIR/packs/*.yaml.
    Remote packs are read from index.json in the guild-packs repo.
    As a fallback when no packs are found, uses the GitHub tree API.

    Returns:
        A sorted list of unique pack name strings.
    """
    names: set = set()

    # Local packs
    if BORG_DIR.exists():
        for pack_yaml in BORG_DIR.glob("*/pack.yaml"):
            names.add(pack_yaml.parent.name)
        packs_dir = BORG_DIR / "packs"
        if packs_dir.exists():
            for pack_yaml in packs_dir.glob("*.yaml"):
                names.add(pack_yaml.stem)

    # Remote packs from index (best-effort)
    # Handle both index formats:
    # - Old format: {"packs": [...]}  (each pack has a "name" field)
    # - New format: {URI: pack_data, ...}  (pack names extracted from URI path)
    try:
        index = _fetch_index()
        if "packs" in index:
            for pack in index.get("packs", []):
                name = pack.get("name", "")
                if name:
                    names.add(name)
        else:
            # New format: top-level keys are URIs
            for uri in index.keys():
                pack_name = uri.split("/")[-1] if "/" in uri else uri
                names.add(pack_name)
    except Exception:
        pass

    # Fallback: gh CLI recursive tree listing of the packaged seed pack path.
    if not names:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{DEFAULT_REPO}/git/trees/{DEFAULT_BRANCH}?recursive=1",
                 "--jq", ".tree[].path"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                prefix = f"{REMOTE_PACKS_PATH}/"
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line.startswith(prefix) or not line.endswith((".yaml", ".yml")):
                        continue
                    filename = Path(line).name
                    if filename.endswith(".workflow.yaml"):
                        names.add(filename[:-len(".workflow.yaml")])
                    elif filename.endswith(".yaml"):
                        names.add(filename[:-len(".yaml")])
                    elif filename.endswith(".yml"):
                        names.add(filename[:-len(".yml")])
        except Exception:
            pass

    return sorted(names)


def fuzzy_match_pack(name: str) -> List[str]:
    """Return pack names similar to `name` using fuzzy matching.

    If ``name`` is a guild:// URI, extracts the pack name portion first.
    Uses difflib.get_close_matches with a cutoff of 0.4. Returns up to 5
    close matches, or all available pack names if no close matches exist.

    Args:
        name: A pack name or guild:// URI.

    Returns:
        A list of up to 5 similar pack names, or all available if none are close.
        Returns an empty list if no packs are available at all.
    """
    # Strip borg:// or guild:// prefix if present so suggestions use pack names.
    try:
        name = _pack_name_from_uri(name)
    except ValueError:
        pass

    available = get_available_pack_names()
    if not available:
        return []

    close = difflib.get_close_matches(name, available, n=5, cutoff=0.4)
    if close:
        return close
    return available
