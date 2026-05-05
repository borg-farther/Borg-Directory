"""Regression tests for the import-level Borg first-user API."""

from __future__ import annotations

import json

import borg


def test_check_delegates_to_real_search(monkeypatch) -> None:
    calls = {}

    def fake_search(query: str, mode: str = "text", requesting_agent_id=None, **_kwargs):
        calls["query"] = query
        calls["mode"] = mode
        calls["agent_id"] = requesting_agent_id
        return json.dumps({
            "success": True,
            "matches": [
                {"name": "systematic-debugging", "tier": "CORE"},
                {"name": "test-driven-development", "tier": "VALIDATED"},
            ],
        })

    monkeypatch.setattr("borg.core.search.borg_search", fake_search)

    result = borg.check(
        "TypeError: unsupported operand type(s)",
        constraints={"mode": "text", "agent_id": "agent://test"},
        top_k=1,
    )

    assert calls == {
        "query": "TypeError: unsupported operand type(s)",
        "mode": "text",
        "agent_id": "agent://test",
    }
    assert result == [{"name": "systematic-debugging", "tier": "CORE"}]


def test_check_empty_context_is_empty() -> None:
    assert borg.check("") == []


def test_check_fails_closed_on_search_error(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("search unavailable")

    monkeypatch.setattr("borg.core.search.borg_search", boom)

    assert borg.check("anything") == []
