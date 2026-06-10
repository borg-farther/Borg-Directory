"""Regression tests for the import-level Borg first-user API."""

from __future__ import annotations

import json

import borg


def test_check_delegates_to_real_search(monkeypatch) -> None:
    """check() plumbs query/mode/agent_id to borg_search, respects top_k, and
    passes through matches that are lexically confident for the query."""
    calls = {}

    def fake_search(query: str, mode: str = "text", requesting_agent_id=None, **_kwargs):
        calls["query"] = query
        calls["mode"] = mode
        calls["agent_id"] = requesting_agent_id
        return json.dumps({
            "success": True,
            "matches": [
                {
                    "name": "typeerror-operand-mismatch",
                    "problem_class": "type_mismatch",
                    "search_text": "TypeError unsupported operand type mismatch",
                    "tier": "CORE",
                },
                {
                    "name": "second-operand-typeerror",
                    "problem_class": "type_mismatch",
                    "search_text": "TypeError operand unsupported",
                    "tier": "VALIDATED",
                },
            ],
        })

    monkeypatch.setattr("borg.core.search.borg_search", fake_search)

    result = borg.check(
        "TypeError: unsupported operand type(s) for int and str",
        constraints={"mode": "text", "agent_id": "agent://test"},
        top_k=1,
    )

    assert calls == {
        "query": "TypeError: unsupported operand type(s) for int and str",
        "mode": "text",
        "agent_id": "agent://test",
    }
    # top_k=1 + both fixtures confident -> just the first.
    assert [r["name"] for r in result] == ["typeerror-operand-mismatch"]


def test_check_drops_confident_but_irrelevant_matches(monkeypatch) -> None:
    """D-006 regression (mocked): borg_search ranks weakly and can return packs
    that do not lexically match the query (Django/Docker packs for a `requests`
    ModuleNotFoundError). check() must gate these out, never surface them as a
    confident answer. Fails-before: the old pass-through returned both packs."""

    def fake_search(query: str, mode: str = "text", requesting_agent_id=None, **_kwargs):
        return json.dumps({
            "success": True,
            "matches": [
                {
                    "name": "django-circular-dependency",
                    "problem_class": "import_cycle",
                    "search_text": "django models circular import foreign key",
                    "tier": "seed",
                },
                {
                    "name": "docker-no-space",
                    "problem_class": "docker_no_space",
                    "search_text": "docker no space left on device prune images",
                    "tier": "seed",
                },
            ],
        })

    monkeypatch.setattr("borg.core.search.borg_search", fake_search)

    assert borg.check("ModuleNotFoundError: No module named 'requests'") == []


def test_check_real_search_no_confident_irrelevant_for_verbatim_stderr() -> None:
    """D-006 regression (end-to-end, no mock): against the bundled seed/pack
    index, the documented Python API must never return a confident-but-
    irrelevant pack for verbatim stderr. Before the fix, this query returned
    django-circular-dependency / django-schema-drift / docker-no-space."""
    known_irrelevant = {
        "django-circular-dependency",
        "django-schema-drift",
        "docker-no-space",
        "bash-permission-denied",
        "django-migration-state",
        "django-null-pointer",
    }
    result = borg.check("ModuleNotFoundError: No module named 'requests'", top_k=3)
    names = {str(r.get("name")) for r in result}
    leaked = names & known_irrelevant
    assert not leaked, f"confident-but-irrelevant packs leaked from check(): {leaked}"


def test_check_empty_context_is_empty() -> None:
    assert borg.check("") == []


def test_check_fails_closed_on_search_error(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("search unavailable")

    monkeypatch.setattr("borg.core.search.borg_search", boom)

    assert borg.check("anything") == []
