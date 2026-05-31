import pickle
import sqlite3
from pathlib import Path

import pytest

from borg.core import embeddings


def _use_temp_cache(monkeypatch, path):
    monkeypatch.setattr(embeddings, "EMBEDDING_CACHE_PATH", str(path))


def _pickle_side_effect(marker: str):
    Path(marker).write_text("executed", encoding="utf-8")
    return {}


class _MaliciousLegacyCache:
    def __init__(self, marker: str):
        self.marker = marker

    def __reduce__(self):
        return (_pickle_side_effect, (self.marker,))


def _create_legacy_trace_db(path):
    db = sqlite3.connect(path)
    db.execute(
        """
        CREATE TABLE traces (
            id TEXT PRIMARY KEY,
            task_description TEXT,
            outcome TEXT,
            root_cause TEXT,
            approach_summary TEXT,
            technology TEXT,
            keywords TEXT
        )
        """
    )
    db.execute(
        """
        INSERT INTO traces (id, task_description, outcome, root_cause, approach_summary, technology, keywords)
        VALUES ('t1', 'fix import bug', 'success', 'dependency drift', 'pin version', 'python', '["import"]')
        """
    )
    db.commit()
    db.close()


def test_build_index_from_legacy_db_without_causal_intervention_does_not_error(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_traces.db"
    _create_legacy_trace_db(db_path)

    monkeypatch.setattr(embeddings, "_get_model", lambda: None)
    embeddings._index_cache = None
    embeddings._index_cache_size = 0

    cache, count = embeddings.build_index_from_db(str(db_path), force_rebuild=True)

    assert cache == {}
    assert count == 0
    assert embeddings._index_cache == {}
    assert embeddings._index_cache_size == 0


def test_semantic_search_skips_model_load_when_legacy_db_has_no_cached_index(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_traces.db"
    _create_legacy_trace_db(db_path)

    calls = {"model": 0}

    def fake_get_model():
        calls["model"] += 1
        raise AssertionError("semantic_search should not load embedding model when no index exists")

    monkeypatch.setattr(embeddings, "_get_model", fake_get_model)
    embeddings._index_cache = None
    embeddings._index_cache_size = 0

    assert embeddings.semantic_search("fix import bug", str(db_path)) == []
    assert calls["model"] == 0


def test_embedding_cache_does_not_execute_legacy_pickle_payload(tmp_path, monkeypatch):
    cache_path = tmp_path / "embeddings.pkl"
    marker = tmp_path / "pickle_executed"
    cache_path.write_bytes(pickle.dumps(_MaliciousLegacyCache(str(marker))))
    _use_temp_cache(monkeypatch, cache_path)

    loaded = embeddings.load_embedding_cache()

    assert loaded == {}
    assert not marker.exists()


@pytest.mark.skipif(not embeddings._NUMPY_AVAILABLE, reason="numpy required for embedding cache vectors")
def test_embedding_cache_round_trips_safe_json_vectors(tmp_path, monkeypatch):
    cache_path = tmp_path / "embeddings.pkl"
    _use_temp_cache(monkeypatch, cache_path)
    vector = embeddings.np.arange(embeddings.EMBEDDING_DIM, dtype=embeddings.np.float32)

    embeddings.save_embedding_cache({"trace-1": vector})
    loaded = embeddings.load_embedding_cache()

    assert cache_path.read_text(encoding="utf-8").startswith("{")
    assert set(loaded) == {"trace-1"}
    assert loaded["trace-1"].dtype == embeddings.np.float32
    assert loaded["trace-1"].shape == (embeddings.EMBEDDING_DIM,)
    assert embeddings.np.allclose(loaded["trace-1"], vector)
    assert cache_path.stat().st_mode & 0o077 == 0


@pytest.mark.skipif(not embeddings._NUMPY_AVAILABLE, reason="numpy required for embedding cache vectors")
def test_embedding_cache_rejects_bad_vectors(tmp_path, monkeypatch):
    cache_path = tmp_path / "embeddings.pkl"
    _use_temp_cache(monkeypatch, cache_path)
    payload = {
        "schema_version": embeddings.EMBEDDING_CACHE_SCHEMA_VERSION,
        "embeddings": {
            "good": [0.0] * embeddings.EMBEDDING_DIM,
            "wrong-dim": [0.0] * (embeddings.EMBEDDING_DIM - 1),
            "nan": [float("nan")] * embeddings.EMBEDDING_DIM,
            "": [0.0] * embeddings.EMBEDDING_DIM,
            "x" * (embeddings.MAX_EMBEDDING_CACHE_KEY_BYTES + 1): [0.0] * embeddings.EMBEDDING_DIM,
        },
    }
    cache_path.write_text(embeddings.json.dumps(payload), encoding="utf-8")

    loaded = embeddings.load_embedding_cache()

    assert set(loaded) == {"good"}
