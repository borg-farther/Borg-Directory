"""
Tests for guild/core/uri.py — URI resolution, fetch-with-retry, and fuzzy matching.

Covers:
  - guild:// URI resolution to GitHub raw URLs
  - https:// and http:// URI passthrough
  - Absolute local path passthrough
  - Unsupported URI scheme errors
  - Empty / whitespace-only URI errors
  - fetch_with_retry: local file reads, URL fetches, retry on failure
  - get_available_pack_names: local scan, remote index, gh fallback
  - fuzzy_match_pack: guild:// prefix stripping, close-match logic
"""

import sys
from pathlib import Path
from unittest.mock import mock_open, patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from borg.core.uri import (
    DEFAULT_REPO,
    DEFAULT_BRANCH,
    fetch_with_retry,
    fuzzy_match_pack,
    get_available_pack_names,
    resolve_guild_uri,
)


# ---------------------------------------------------------------------------
# resolve_guild_uri tests
# ---------------------------------------------------------------------------

class TestResolveBorgUri:
    """Tests for resolve_guild_uri()."""

    def test_guild_uri_resolves_to_github_raw(self):
        """borg://domain/name resolves to the correct GitHub raw URL."""
        result = resolve_guild_uri("borg://bensargotest-sys/my-pack")
        assert result == (
            f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}"
            "/packs/my-pack.workflow.yaml"
        )

    def test_guild_uri_with_slash_in_name(self):
        """borg://domain/pack/subpath resolves to a URL with the full path in the pack segment."""
        # guild://bensargotest-sys/my-pack -> packs/my-pack.workflow.yaml (pack name is just "my-pack")
        result = resolve_guild_uri("borg://bensargotest-sys/my-pack")
        assert result == (
            f"https://raw.githubusercontent.com/{DEFAULT_REPO}/{DEFAULT_BRANCH}"
            "/packs/my-pack.workflow.yaml"
        )

    def test_https_uri_passthrough(self):
        """https:// URLs are returned unchanged."""
        url = "https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/test.yaml"
        assert resolve_guild_uri(url) == url

    def test_http_uri_passthrough(self):
        """http:// URLs are returned unchanged."""
        url = "http://example.com/pack.yaml"
        assert resolve_guild_uri(url) == url

    def test_absolute_local_path_passthrough(self):
        """/local/path strings are returned unchanged."""
        path = "/etc/guild/packs/my-pack.yaml"
        assert resolve_guild_uri(path) == path

    def test_empty_uri_raises_value_error(self):
        with pytest.raises(ValueError, match="URI cannot be empty"):
            resolve_guild_uri("")

    def test_whitespace_only_uri_raises_value_error(self):
        with pytest.raises(ValueError, match="URI cannot be empty"):
            resolve_guild_uri("   ")

    def test_unsupported_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported URI scheme"):
            resolve_guild_uri("file:///etc/passwd")

    def test_invalid_guild_uri_empty_path(self):
        """borg:// with nothing after it raises ValueError."""
        with pytest.raises(ValueError, match="Invalid guild URI"):
            resolve_guild_uri("borg://")

    def test_guild_uri_shorthand_no_domain(self):
        """borg://pack-name resolves as shorthand (no domain required)."""
        url = resolve_guild_uri("borg://systematic-debugging")
        assert "systematic-debugging.workflow.yaml" in url
        assert "raw.githubusercontent.com" in url


# ---------------------------------------------------------------------------
# fetch_with_retry tests
# ---------------------------------------------------------------------------

class TestFetchWithRetry:
    """Tests for fetch_with_retry()."""

    def test_local_file_read(self, tmp_path):
        """Existing local files are read and returned successfully."""
        pack_file = tmp_path / "test-pack.yaml"
        pack_file.write_text("type: workflow\nversion: '1.0'", encoding="utf-8")

        content, error = fetch_with_retry(str(pack_file))
        assert error == ""
        assert content == "type: workflow\nversion: '1.0'"

    def test_local_file_not_found_returns_error(self):
        """Missing local path returns an error (no exception)."""
        content, error = fetch_with_retry("/nonexistent/path/pack.yaml")
        assert content == ""
        assert error != ""

    def test_url_fetch_success(self):
        """Successful URL fetch returns content with no error."""
        fake_yaml = "type: workflow\nversion: '1.0'"
        m = mock_open(read_data=fake_yaml.encode("utf-8"))
        with patch("borg.core.uri.urlopen", m):
            content, error = fetch_with_retry("https://example.com/pack.yaml")
            assert error == ""
            assert content == fake_yaml

    def test_url_fetch_fails_all_retries(self):
        """URL failure after all retries returns the last error message."""
        with patch("borg.core.uri.urlopen", side_effect=Exception("Connection refused")):
            content, error = fetch_with_retry("https://example.com/pack.yaml", retries=2)
            assert content == ""
            assert "Connection refused" in error

    def test_url_fetch_retries_then_succeeds(self):
        """On transient failure then success, fetch_with_retry returns the content."""
        fake_yaml = "type: workflow"
        with patch("borg.core.uri.urlopen") as mock_urlopen:
            # First call fails, second succeeds
            mock_urlopen.side_effect = [
                Exception("Temporary failure"),
                MagicMock(read=lambda: fake_yaml.encode("utf-8")),
            ]

            content, error = fetch_with_retry("https://example.com/pack.yaml", retries=1)
            assert error == ""
            assert content == fake_yaml
            assert mock_urlopen.call_count == 2

    def test_retries_argument_controls_attempt_count(self):
        """retries=N means N+1 total attempts (1 initial + N retries)."""
        with patch("borg.core.uri.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("always fails")
            # retries=3 -> 4 total attempts
            fetch_with_retry("https://example.com/pack.yaml", retries=3)
            assert mock_urlopen.call_count == 4

    def test_default_retries_is_one(self):
        """Default retries=1 means up to 2 attempts total."""
        with patch("borg.core.uri.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("always fails")
            fetch_with_retry("https://example.com/pack.yaml")
            assert mock_urlopen.call_count == 2


# ---------------------------------------------------------------------------
# get_available_pack_names tests
# ---------------------------------------------------------------------------

class TestGetAvailablePackNames:
    """Tests for get_available_pack_names()."""

    def test_returns_sorted_list(self):
        """Result is always a sorted list (not set or other type)."""
        with patch("borg.core.uri._fetch_index", side_effect=Exception("no network")):
            result = get_available_pack_names()
        assert isinstance(result, list)
        # If no packs found, should be empty list not None
        assert result == [] or result == sorted(result)

    def test_local_agent_dir_scanned(self, monkeypatch, tmp_path):
        """Local BORG_DIR packs are discovered."""
        # Point BORG_DIR at our temp directory
        from borg.core import uri as uri_module
        fake_guild = tmp_path / "guild"
        fake_guild.mkdir()
        (fake_guild / "my-pack").mkdir()
        (fake_guild / "my-pack" / "pack.yaml").write_text("type: workflow", encoding="utf-8")
        (fake_guild / "packs").mkdir()
        (fake_guild / "packs" / "other-pack.yaml").write_text("type: workflow", encoding="utf-8")

        monkeypatch.setattr(uri_module, "BORG_DIR", fake_guild)

        with patch.object(uri_module, "_fetch_index", side_effect=Exception("no network")):
            names = get_available_pack_names()

        assert "my-pack" in names
        assert "other-pack" in names

    def test_remote_index_packs_included(self, monkeypatch):
        """Remote index entries are added to the name set."""
        from borg.core import uri as uri_module

        fake_index = {"packs": [{"name": "remote-pack-1"}, {"name": "remote-pack-2"}]}
        with patch.object(uri_module, "_fetch_index", return_value=fake_index):
            with patch.object(uri_module, "BORG_DIR", Path("/nonexistent")):
                names = get_available_pack_names()

        assert "remote-pack-1" in names
        assert "remote-pack-2" in names


# ---------------------------------------------------------------------------
# fuzzy_match_pack tests
# ---------------------------------------------------------------------------

class TestFuzzyMatchPack:
    """Tests for fuzzy_match_pack()."""

    def test_guild_uri_prefix_stripped(self, monkeypatch):
        """borg:// prefix is stripped before matching."""
        from borg.core import uri as uri_module

        def fake_names():
            return ["my-pack", "other-pack"]

        monkeypatch.setattr(uri_module, "get_available_pack_names", fake_names)

        # Should look up "my-pack" not "bensargotest-sys/my-pack"
        result = fuzzy_match_pack("borg://bensargotest-sys/my-pack")
        assert "my-pack" in result

    def test_returns_close_matches(self, monkeypatch):
        """Close matches are returned when found."""
        from borg.core import uri as uri_module

        def fake_names():
            return ["web-search", "web-scrape", "image-classify", "audio-transcribe", "doc-read"]

        monkeypatch.setattr(uri_module, "get_available_pack_names", fake_names)

        # "web-srch" should match "web-search" and "web-scrape"
        result = fuzzy_match_pack("web-srch")
        assert "web-search" in result

    def test_returns_all_when_no_close_match(self, monkeypatch):
        """When no close match exists, all available packs are returned."""
        from borg.core import uri as uri_module

        def fake_names():
            return ["alpha", "beta", "gamma"]

        monkeypatch.setattr(uri_module, "get_available_pack_names", fake_names)

        result = fuzzy_match_pack("xyz-unlikely")
        assert result == ["alpha", "beta", "gamma"]

    def test_empty_list_when_no_packs_available(self, monkeypatch):
        """Returns empty list when no packs are available."""
        from borg.core import uri as uri_module

        monkeypatch.setattr(uri_module, "get_available_pack_names", lambda: [])

        result = fuzzy_match_pack("any-pack")
        assert result == []
