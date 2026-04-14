"""
Comprehensive compatibility tests for all 23 guild packs.

Covers:
  - All 23 packs parse without error (parse_workflow_pack succeeds)
  - All 23 packs pass validate_pack (proof gates)
  - All 23 packs pass scan_pack_safety (no injection/credential threats)
  - borg_search finds each pack by name (network, @pytest.mark.network)
  - borg_try previews each pack without error (network, @pytest.mark.network)
  - Top-5 packs (systematic-debugging, code-review, test-driven-development,
    plan, quick-debug) can be pulled AND pass validate_pack + scan_pack_safety
    (network, @pytest.mark.network)

Run non-network tests only:
  pytest guild/tests/test_pack_compatibility.py -v --tb=short -m 'not network'
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core.schema import parse_workflow_pack, validate_pack
from borg.core.safety import scan_pack_safety
from borg.core.search import borg_search, borg_try, borg_pull

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKS_INDEX_PATH = Path("/root/hermes-workspace/guild-packs/index.json")
PACKS_DIR = Path("/root/hermes-workspace/guild-packs/packs")
TOP_5_PACKS = [
    "systematic-debugging",
    # "code-review",  # Removed in v3.0.0: d=-2.83, actively hurts performance
    "test-driven-development",
    "plan",
    "quick-debug",
]


# ---------------------------------------------------------------------------
# Load index
# ---------------------------------------------------------------------------

def _load_index() -> dict:
    with open(PACKS_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Build pack list directly from filesystem (all 23 YAML files)
#
# The index.json has 23 entries but only 20 unique names (3 names appear twice:
# systematic-debugging, code-review, test-driven-development). Some of those
# duplicate names map to files whose IDs already appear for other names, so we
# can't deduplicate cleanly via index. Instead we discover packs directly from
# the filesystem and match each to its best index entry by ID.
# ---------------------------------------------------------------------------

def _build_pack_list() -> List[tuple]:
    """Return [(pack_name, filename, uri)] for each of the 23 YAML files.

    Packs are discovered directly from PACKS_DIR/*.yaml (23 files).
    Each file's pack_name and uri come from the index via ID matching.
    Results are sorted by pack_name for stable ordering.
    """
    index = _load_index()

    # Build index lookup: id -> entry
    id_to_entry: Dict[str, dict] = {}
    for entry in index.get("packs", []):
        pid = entry.get("id", "")
        if pid:
            id_to_entry[pid] = entry

    # Build id -> filename for all YAML files
    id_to_fname: Dict[str, str] = {}
    fname_to_id: Dict[str, str] = {}
    for fname in sorted(PACKS_DIR.glob("*.yaml")):
        if not fname.name.endswith(".yaml"):
            continue
        with open(fname, encoding="utf-8") as f:
            import yaml
            data = yaml.safe_load(f.read())
        if data and isinstance(data, dict):
            pid = data.get("id", "")
            if pid:
                id_to_fname[pid] = fname.name
                fname_to_id[fname.name] = pid

    # Build (pack_name, filename, uri) for each file
    # For each file, find its index entry by ID
    seen_fnames: set = set()
    result: List[tuple] = []
    for fname in sorted(PACKS_DIR.glob("*.yaml")):
        if not fname.name.endswith(".yaml"):
            continue
        if fname.name in seen_fnames:
            continue
        seen_fnames.add(fname.name)

        pid = fname_to_id.get(fname.name, "")
        entry = id_to_entry.get(pid, {})
        fallback_name = fname.stem.replace(".workflow", "").replace(".rubric", "")
        pack_name = entry.get("name", fallback_name)  # fallback to filename stem sans suffix
        uri = pid or f"borg://hermes/{pack_name}"
        result.append((pack_name, fname.name, uri))

    result.sort(key=lambda x: x[0])
    return result


_PACK_LIST = _build_pack_list()
# {pack_name: (filename, uri)}  -- pack_name may have duplicates; key by filename instead
PACK_INFO: Dict[str, tuple] = {item[0]: (item[1], item[2]) for item in _PACK_LIST}
ALL_PACK_FILES: List[str] = [item[1] for item in _PACK_LIST]  # filenames
# Filter deprecated packs: code-review removed in v3.0.0 (d=-2.83, actively hurts)
_DEPRECATED_PACKS = {"code-review"}
ALL_PACK_NAMES: List[str] = [item[0] for item in _PACK_LIST if item[0] not in _DEPRECATED_PACKS]


def get_pack_file_path(pack_name: str) -> Path:
    """Return the local pack YAML path for a pack name."""
    fname = PACK_INFO[pack_name][0]
    return PACKS_DIR / fname


def get_pack_uri(pack_name: str) -> str:
    """Return the guild:// URI for a pack name."""
    return PACK_INFO[pack_name][1]


def read_pack_yaml(pack_name: str) -> str:
    """Read the raw YAML content for a pack."""
    path = get_pack_file_path(pack_name)
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test: all packs parse without error
# ---------------------------------------------------------------------------

class TestAllPacksParse:
    """Every pack file parses as valid YAML with required fields."""

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_parses(self, pack_name: str):
        content = read_pack_yaml(pack_name)
        pack = parse_workflow_pack(content)
        assert pack is not None
        assert isinstance(pack, dict)
        assert pack.get("id"), f"Pack '{pack_name}' is missing 'id' field"


# ---------------------------------------------------------------------------
# Test: all packs pass validate_pack
# ---------------------------------------------------------------------------

class TestAllPacksValidate:
    """Every pack file passes proof-gate validation."""

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_validates(self, pack_name: str):
        content = read_pack_yaml(pack_name)
        pack = parse_workflow_pack(content)
        errors = validate_pack(pack)
        assert errors == [], f"Pack '{pack_name}' failed validation: {errors}"


# ---------------------------------------------------------------------------
# Test: all packs pass scan_pack_safety
# ---------------------------------------------------------------------------

class TestAllPacksSafety:
    """Every pack file is free of injection/credential threats."""

    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_pack_safety(self, pack_name: str):
        content = read_pack_yaml(pack_name)
        pack = parse_workflow_pack(content)
        threats = scan_pack_safety(pack)
        # Filter out warnings (non-blocking) — only fail on actual threats
        blocking_threats = [t for t in threats if "warning" not in t.lower()]
        assert blocking_threats == [], (
            f"Pack '{pack_name}' has blocking safety threats: {blocking_threats}"
        )


# ---------------------------------------------------------------------------
# Test: borg_search finds each pack
# ---------------------------------------------------------------------------

class TestBorgSearchFindsPacks:
    """borg_search locates every pack by name (text search)."""

    @pytest.mark.network
    @pytest.mark.parametrize("pack_name", UNIQUE_PACK_NAMES)
    def test_search_finds_pack(self, pack_name: str):
        fake_index = _load_index()
        with patch("borg.core.search._fetch_index", return_value=fake_index):
            with patch("borg.core.uri.BORG_DIR", Path("/nonexistent")):
                result = json.loads(borg_search(pack_name))

        assert result["success"] is True, f"borg_search failed: {result.get('error')}"
        matched_names = [m.get("name") for m in result["matches"]]
        assert pack_name in matched_names, (
            f"Pack '{pack_name}' not found in search results: {matched_names}"
        )


# ---------------------------------------------------------------------------
# Test: borg_try previews each pack without error
# ---------------------------------------------------------------------------

class TestBorgTryPreviewsPacks:
    """borg_try fetches and previews every pack without raising an error."""

    @pytest.mark.network
    @pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
    def test_try_previews_pack(self, pack_name: str):
        uri = get_pack_uri(pack_name)
        content = read_pack_yaml(pack_name)
        fname = get_pack_file_path(pack_name).name
        resolved_url = (
            f"https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main"
            f"/packs/{fname}"
        )
        with patch("borg.core.search.resolve_guild_uri", return_value=resolved_url):
            with patch(
                "borg.core.search.fetch_with_retry",
                return_value=(content, ""),
            ):
                result = json.loads(borg_try(uri))

        assert result["success"] is True, (
            f"borg_try('{uri}') failed: {result.get('error')}"
        )
        assert result.get("id"), "borg_try response missing 'id' field"
        assert result.get("verdict") in ("safe", "blocked"), (
            f"Unexpected verdict: {result.get('verdict')}"
        )


# ---------------------------------------------------------------------------
# Test: top-5 packs — pull + validate + safety scan
# ---------------------------------------------------------------------------

class TestTop5PacksPullAndValidate:
    """Top-5 most important packs can be pulled and pass full validation."""

    @pytest.mark.network
    @pytest.mark.parametrize("pack_name", TOP_5_PACKS)
    def test_top5_pull_validates_and_is_safe(self, pack_name: str, tmp_path):
        uri = get_pack_uri(pack_name)
        content = read_pack_yaml(pack_name)
        fname = get_pack_file_path(pack_name).name
        resolved_url = (
            f"https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main"
            f"/packs/{fname}"
        )

        fake_guild = tmp_path / "guild"
        fake_guild.mkdir()

        import borg.core.search as search_module
        original_agent_dir = search_module.BORG_DIR
        search_module.BORG_DIR = fake_guild

        try:
            with patch("borg.core.search.resolve_guild_uri", return_value=resolved_url):
                with patch(
                    "borg.core.search.fetch_with_retry",
                    return_value=(content, ""),
                ):
                    pull_result = json.loads(borg_pull(uri))

            assert pull_result["success"] is True, (
                f"borg_pull('{uri}') failed: {pull_result.get('error')}"
            )

            # Load the saved pack and validate
            saved_path = Path(pull_result["path"])
            assert saved_path.exists(), f"Pack not saved to {saved_path}"
            saved_content = saved_path.read_text(encoding="utf-8")
            pack = parse_workflow_pack(saved_content)

            validation_errors = validate_pack(pack)
            assert validation_errors == [], (
                f"Pulled pack '{pack_name}' failed validation: {validation_errors}"
            )

            safety_threats = scan_pack_safety(pack)
            blocking_threats = [t for t in safety_threats if "warning" not in t.lower()]
            assert blocking_threats == [], (
                f"Pulled pack '{pack_name}' has blocking safety threats: {blocking_threats}"
            )

            assert pull_result["tier"] in ("CORE", "VALIDATED", "COMMUNITY"), (
                f"Invalid tier: {pull_result.get('tier')}"
            )

        finally:
            search_module.BORG_DIR = original_agent_dir


# ---------------------------------------------------------------------------
# Test: top-5 packs — borg_try returns safe verdict
# ---------------------------------------------------------------------------

class TestTop5PacksTryVerdict:
    """Top-5 packs return verdict='safe' on borg_try."""

    @pytest.mark.network
    @pytest.mark.parametrize("pack_name", TOP_5_PACKS)
    def test_top5_try_safe_verdict(self, pack_name: str):
        uri = get_pack_uri(pack_name)
        content = read_pack_yaml(pack_name)
        fname = get_pack_file_path(pack_name).name
        resolved_url = (
            f"https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main"
            f"/packs/{fname}"
        )
        with patch("borg.core.search.resolve_guild_uri", return_value=resolved_url):
            with patch(
                "borg.core.search.fetch_with_retry",
                return_value=(content, ""),
            ):
                result = json.loads(borg_try(uri))

        assert result["success"] is True
        assert result.get("verdict") == "safe", (
            f"Top-5 pack '{pack_name}' has verdict '{result.get('verdict')}' "
            f"with errors: {result.get('validation_errors', [])}"
        )


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

def test_file_count():
    """Sanity check: exactly 23 YAML files in the packs directory."""
    yaml_files = [f for f in PACKS_DIR.glob("*.yaml") if f.name.endswith(".yaml")]
    assert len(yaml_files) == 23, (
        f"Expected 23 YAML files, found {len(yaml_files)}"
    )


def test_top5_are_in_all_packs():
    """Sanity check: all top-5 packs are present in the pack list."""
    pack_names_set = set(ALL_PACK_NAMES)
    missing = [p for p in TOP_5_PACKS if p not in pack_names_set]
    assert not missing, f"Top-5 packs not found in pack list: {missing}"
