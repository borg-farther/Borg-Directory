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

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REPO = os.environ.get('BORG_REPO', 'bensargotest-sys/guild-packs')
DEFAULT_BRANCH = "main"
BORG_DIR = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes")) / "guild"
INDEX_URL = f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}/index.json"

_CACHE_TTL = 300  # 5 minutes
_index_cache: Tuple[object, float] = (None, 0.0)

# ---------------------------------------------------------------------------
# URI resolution
# ---------------------------------------------------------------------------

def resolve_guild_uri(uri: str) -> str:
    """Resolve a guild URI to a fetchable URL or local path.

    Supported schemes:
      guild://domain/name  -> GitHub raw URL (https://raw.githubusercontent.com/...)
      https://... or http://... -> passthrough
      /local/path          -> passthrough (absolute path)

    Args:
        uri: A guild URI, HTTPS URL, or absolute local path.

    Returns:
        The resolved URL or path as a string.

    Raises:
        ValueError: If the URI is empty or has an unsupported scheme.
    """
    if not uri or not uri.strip():
        raise ValueError("URI cannot be empty")

    uri = uri.strip()

    if uri.startswith("borg://"):
        path_part = uri[len("borg://"):]
        if not path_part:
            raise ValueError(f"Invalid guild URI: {uri}")
        parts = path_part.split("/", 1)
        if len(parts) == 2:
            _domain, name = parts
        else:
            name = parts[0]  # guild://pack-name shorthand (no domain)
        # Try .workflow.yaml first, fall back to .yaml
        # Store both URLs so fetch_with_retry can try the fallback
        return (
            f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}"
            f"/packs/{name}.workflow.yaml"
        )

    if uri.startswith("https://") or uri.startswith("http://"):
        return uri

    if uri.startswith("/"):
        return uri

    # Bare pack name (no scheme) — try as borg://hermes/<name>
    if re.match(r'^[\w-]+$', uri):
        return resolve_guild_uri(f"borg://hermes/{uri}")

    raise ValueError(f"Unsupported URI scheme: {uri}. Use: borg://domain/pack-name or a bare pack name.")


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
        raise ValueError(f"Failed to fetch guild index: {e}")


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
    try:
        index = _fetch_index()
        for pack in index.get("packs", []):
            name = pack.get("name", "")
            if name:
                names.add(name)
    except Exception:
        pass

    # Fallback: gh CLI tree listing
    if not names:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{DEFAULT_REPO}/git/trees/{DEFAULT_BRANCH}",
                 "--jq", ".tree[].path"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line and not line.startswith(".") and line not in ("README.md", "LICENSE", "index.json"):
                        names.add(line)
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
    # Strip guild:// prefix if present
    if name.startswith("borg://"):
        parts = name[len("borg://"):].split("/", 1)
        if len(parts) >= 2:
            name = parts[1]

    available = get_available_pack_names()
    if not available:
        return []

    close = difflib.get_close_matches(name, available, n=5, cutoff=0.4)
    if close:
        return close
    return available
