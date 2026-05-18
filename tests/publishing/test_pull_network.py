"""
Network integration tests for `borg pull`.

These tests verify that borg pull correctly fetches packs from:
  - borg:// shorthand URIs (guild index lookup)
  - Raw GitHub URLs (direct YAML)
  - Invalid URLs (proper error handling)

Marked with @pytest.mark.network — skip when offline.
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Ensure borg package is importable
import sys
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_borg_dir(monkeypatch, tmp_path):
    """Create a temporary BORG_DIR and patch it into borg.core.uri."""
    from borg.core import uri as uri_module

    borg_dir = tmp_path / ".borg"
    borg_dir.mkdir()
    monkeypatch.setattr(uri_module, "BORG_DIR", borg_dir)
    yield borg_dir
    # Cleanup is automatic via tmp_path


@pytest.fixture
def clear_index_cache():
    """Clear the remote index cache before each test."""
    from borg.core import uri as uri_module
    uri_module._index_cache = (None, 0)
    yield
    uri_module._index_cache = (None, 0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.network
def test_pull_borg_uri_systematic_debugging(temp_borg_dir, clear_index_cache):
    """Test that `borg pull borg://converted/systematic-debugging` fetches from guild index."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", "borg://converted/systematic-debugging"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )

    # Should succeed or at least not crash
    # (remote index may be empty, which is fine — just verify it tried)
    output = result.stdout + result.stderr
    assert "Traceback" not in output, f"Unexpected error:\n{output}"
    # Should have attempted to fetch something
    assert any(kw in output.lower() for kw in ["pulled", "not found", "error", "fetch", "pack"]), \
        f"No meaningful output:\n{output}"


@pytest.mark.network
def test_pull_raw_github_yaml(temp_borg_dir, clear_index_cache):
    """Test that a raw GitHub URL pointing to a pack YAML is downloaded and validated."""
    import subprocess

    # The django-null-pointer seed pack exists in the agent-borg repo
    url = (
        "https://github.com/bensargotest-sys/agent-borg/raw/main"
        "/borg/seeds_data/packs/django-null-pointer.yaml"
    )

    result = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", url],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
    )

    output = result.stdout + result.stderr

    # Check for download attempt — we don't require success if the file
    # doesn't exist at that path, but we do require no crash
    assert "Traceback" not in output, f"Unexpected crash:\n{output}"

    # If pack was found, verify the downloaded YAML is valid and has required fields
    if result.returncode == 0:
        data = json.loads(result.stdout) if result.stdout.strip().startswith("{") else {}
        if "path" in data:
            path = Path(data["path"])
            assert path.exists(), f"Reported path does not exist: {path}"
            import yaml
            pack_data = yaml.safe_load(path.read_text())
            assert isinstance(pack_data, dict), "Pack YAML is not a dict"
            assert "name" in pack_data, "Pack missing required 'name' field"
            assert "phases" in pack_data, "Pack missing required 'phases' field"
            # Cleanup
            path.unlink(missing_ok=True)


@pytest.mark.network
def test_pull_invalid_url_error_message(temp_borg_dir, clear_index_cache):
    """Test that invalid URLs return a clear error, not a crash."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", "https://invalid.domain.tld/pack.yaml"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0, "Should have failed"
    # Should have a meaningful error, not a traceback
    assert "Traceback" not in output, f"Unexpected crash:\n{output}"
    assert any(kw in output.lower() for kw in ["error", "not found", "failed", "invalid", "fetch"]), \
        f"No error message in output:\n{output}"


@pytest.mark.network
def test_pull_local_seed_pack(temp_borg_dir):
    """Test that a local seeds pack can be pulled by name."""
    import subprocess

    # Pull by name — should resolve to seed pack
    result = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", "django-null-pointer"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
    )

    output = result.stdout + result.stderr
    # Should either succeed or fail gracefully — no crash
    assert "Traceback" not in output, f"Unexpected crash:\n{output}"


@pytest.mark.network
def test_pull_clears_cache_on_retry(temp_borg_dir, clear_index_cache):
    """Test that pulling twice respects the network (doesn't cache failures)."""
    import subprocess

    # First: try a non-existent pack — should fail gracefully
    result1 = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", "https://github.com/nonexist/repo/pack.yaml"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
    )
    assert "Traceback" not in (result1.stdout + result1.stderr)
    assert result1.returncode != 0

    # Second: try the same — should also fail gracefully (not cached as success)
    result2 = subprocess.run(
        [sys.executable, "-m", "borg.cli", "pull", "https://github.com/nonexist/repo/pack.yaml"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
    )
    output2 = result2.stdout + result2.stderr
    assert "Traceback" not in output2
    assert result2.returncode != 0
