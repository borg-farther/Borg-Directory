import sqlite3

from borg.core import embeddings


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
