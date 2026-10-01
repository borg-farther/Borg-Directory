from __future__ import annotations

from borg.core import embeddings, negative_traces


def test_negative_trace_retrieval_rejects_unrelated_npm_permission_dead_end(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "traces.db"
    db_path.touch()

    monkeypatch.setattr(
        embeddings,
        "semantic_search",
        lambda **kwargs: [
            {
                "id": "npm-dead-end",
                "similarity": 0.91,
                "task_description": "npm global install EACCES",
                "technology": "nodejs",
                "approach_summary": "Ran sudo npm install -g to bypass global package permissions",
                "root_cause": "Created root-owned node_modules",
            },
            {
                "id": "script-dead-end",
                "similarity": 0.82,
                "task_description": "bash deploy.sh permission denied",
                "technology": "bash",
                "approach_summary": "Used chmod 777 on deploy.sh",
                "root_cause": "The script needed only its owner execute bit",
            },
        ],
    )

    matches = negative_traces.find_negative_traces(
        task="Fix bash ./deploy.sh permission denied",
        error="bash: ./deploy.sh: Permission denied",
        db_path=str(db_path),
    )

    assert [item["id"] for item in matches] == ["script-dead-end"]
    assert "npm" not in str(matches).lower()