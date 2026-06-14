"""A seedless install must fail LOUDLY, never silently degrade to an empty corpus.

Before this, cold_start swallowed every exception as a warning, so a wheel built
without seeds_data would pass startup and answer every rescue with
no_confident_match while looking healthy. These tests lock the loud behavior in.
"""

from __future__ import annotations

import pytest

from borg.core import cold_start
from borg.core.cold_start import ColdStartSeedError, verify_seeds_loaded


def test_verify_seeds_loaded_passes_with_real_bundled_corpus():
    # The in-tree package carries seeds; this must load and report a positive count.
    assert verify_seeds_loaded() > 0


def test_verify_seeds_loaded_raises_when_corpus_is_empty(monkeypatch):
    monkeypatch.setattr("borg.core.seeds.get_seed_packs", lambda: [])
    monkeypatch.setattr("borg.core.search.borg_search", lambda *a, **k: '{"matches": []}')
    with pytest.raises(ColdStartSeedError):
        verify_seeds_loaded()


def test_run_if_needed_reraises_seed_error_loudly(monkeypatch, tmp_path, caplog):
    # No marker yet, and seeds "fail to load" -> must re-raise (not swallow).
    monkeypatch.setattr(cold_start, "COLD_START_MARKER", tmp_path / ".cold_start_done")
    def _boom():
        raise ColdStartSeedError("seed corpus did not load: 0 packs")
    monkeypatch.setattr(cold_start, "verify_seeds_loaded", _boom)
    with pytest.raises(ColdStartSeedError):
        cold_start.run_if_needed()
    # marker must NOT be written on failure (so it re-checks next start)
    assert not (tmp_path / ".cold_start_done").exists()


def test_run_if_needed_swallows_non_seed_errors(monkeypatch, tmp_path):
    # A non-seed hiccup (e.g. embedding/marker) stays non-fatal.
    monkeypatch.setattr(cold_start, "COLD_START_MARKER", tmp_path / ".cold_start_done")
    def _other_error():
        raise RuntimeError("some transient non-seed issue")
    monkeypatch.setattr(cold_start, "_run_cold_start", _other_error)
    assert cold_start.run_if_needed() is False  # non-fatal


def test_run_if_needed_succeeds_and_writes_marker(monkeypatch, tmp_path):
    marker = tmp_path / ".cold_start_done"
    monkeypatch.setattr(cold_start, "COLD_START_MARKER", marker)
    monkeypatch.setattr(cold_start, "_run_cold_start", lambda: None)
    assert cold_start.run_if_needed() is True
    assert marker.exists()
    # second call is a no-op (marker present)
    assert cold_start.run_if_needed() is False
