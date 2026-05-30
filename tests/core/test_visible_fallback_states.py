from __future__ import annotations

import json

from borg.core import search
from borg.core.rescue import rescue, render_rescue_text


def _codes_from_payload(payload: dict) -> set[str]:
    return {str(item.get("code")) for item in payload.get("fallback_states", []) if isinstance(item, dict)}


def _codes_from_result(result) -> set[str]:
    return {str(item.get("code")) for item in result.fallback_states if isinstance(item, dict)}


def test_rescue_no_confident_match_exposes_visible_fallback_state():
    result = rescue("proprietary blorple engine emitted qxz-991 impossible status", show_guidance=False)

    codes = _codes_from_result(result)
    assert result.status == "no_confident_match"
    assert "NO_CONFIDENT_MATCH" in codes
    assert "OUTCOME_NOT_RECORDED" in codes
    assert "do not blend weak retrieval" in result.agent_instruction.lower()
    rendered = render_rescue_text(result)
    assert "FALLBACK STATES" in rendered
    assert "NO_CONFIDENT_MATCH" in rendered


def test_rescue_matched_seed_result_exposes_local_seed_and_outcome_receipt_states():
    result = rescue("ModuleNotFoundError: No module named flask", show_guidance=False)

    codes = _codes_from_result(result)
    assert result.status == "matched"
    assert "LOCAL_SEED_NOT_COLLECTIVE_PROOF" in codes
    assert "OUTCOME_NOT_RECORDED" in codes
    assert result.value_receipt["evidence_source"] == "seed_pack"


def test_search_semantic_mode_reports_visible_lexical_fallback_and_seed_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "guild"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    (tmp_path / "guild").mkdir(parents=True)
    monkeypatch.setattr(search, "_fetch_index", lambda: {"packs": []})
    monkeypatch.setattr(search, "SemanticSearchEngine", None)

    payload = json.loads(search.borg_search("missing dependency", mode="semantic", include_seeds=True))

    assert payload["success"] is True
    assert payload["requested_mode"] == "semantic"
    assert payload["effective_mode"] in {"text", "semantic"}
    codes = _codes_from_payload(payload)
    assert "SEMANTIC_SEARCH_LEXICAL_FALLBACK" in codes
    assert "LOCAL_SEED_NOT_COLLECTIVE_PROOF" in codes
    assert payload["provenance_notice"]["claim_boundary"] == "Search hits are routing hints, not proof of measured Borg lift."


def test_search_semantic_text_only_side_path_still_merges_seed_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "guild"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    (tmp_path / "guild").mkdir(parents=True)
    monkeypatch.setattr(search, "_fetch_index", lambda: {"packs": []})

    class DummyStore:
        pass

    class TextOnlySemanticEngine:
        def __init__(self, store):
            self.store = store

        def search(self, query, top_k=50, mode="semantic"):
            return [
                {
                    "id": "local-text-missing-dependency",
                    "problem_class": "missing dependency",
                    "tier": "local",
                    "confidence": "unknown",
                    "match_type": "text",
                    "source": "local",
                }
            ]

    monkeypatch.setattr(search, "AgentStore", DummyStore)
    monkeypatch.setattr(search, "SemanticSearchEngine", TextOnlySemanticEngine)

    payload = json.loads(search.borg_search("missing dependency", mode="semantic", include_seeds=True))

    codes = _codes_from_payload(payload)
    assert payload["effective_mode"] == "text"
    assert "SEMANTIC_SEARCH_LEXICAL_FALLBACK" in codes
    assert payload["source_mix"].get("local", 0) == 1
    assert payload["source_mix"].get("seed", 0) >= 1
    assert "LOCAL_SEED_NOT_COLLECTIVE_PROOF" not in codes
    assert payload["provenance_notice"]["claim_boundary"] == "Search hits are routing hints, not proof of measured Borg lift."



def test_search_semantic_trace_hit_does_not_hide_primary_lexical_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "guild"))
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    (tmp_path / "guild").mkdir(parents=True)
    monkeypatch.setattr(search, "_fetch_index", lambda: {"packs": []})
    monkeypatch.setattr(search, "SemanticSearchEngine", None)

    from borg.core import embeddings

    def fake_semantic_trace(**kwargs):
        return [
            {
                "id": "trace-sem-1",
                "task_description": "missing dependency trace",
                "outcome": "success",
                "technology": "python",
                "similarity": 0.9,
            }
        ]

    monkeypatch.setattr(embeddings, "semantic_search", fake_semantic_trace)

    payload = json.loads(search.borg_search("missing dependency", mode="semantic", include_seeds=True))

    codes = _codes_from_payload(payload)
    assert payload["effective_mode"] == "text"
    assert "SEMANTIC_SEARCH_LEXICAL_FALLBACK" in codes
    assert payload["source_mix"].get("trace", 0) == 1
    assert payload["source_mix"].get("seed", 0) >= 1
    assert "LOCAL_SEED_NOT_COLLECTIVE_PROOF" not in codes



def test_search_legacy_remote_unknown_source_does_not_claim_seed_only(monkeypatch, tmp_path):
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "guild"))
    (tmp_path / "guild").mkdir(parents=True)
    monkeypatch.setattr(
        search,
        "_fetch_index",
        lambda: {"packs": [{"name": "legacy-missing-dependency", "id": "legacy-missing-dependency", "problem_class": "missing dependency"}]},
    )

    payload = json.loads(search.borg_search("missing dependency", mode="text", include_seeds=True))

    assert payload["success"] is True
    assert payload["source_mix"].get("unknown", 0) >= 1
    assert "LOCAL_SEED_NOT_COLLECTIVE_PROOF" not in _codes_from_payload(payload)


def test_search_empty_query_reports_source_mix_and_no_overclaim(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_DIR", str(tmp_path / "guild"))
    (tmp_path / "guild").mkdir(parents=True)

    payload = json.loads(search.borg_search("", mode="text", include_seeds=True))

    assert payload["success"] is True
    assert payload["requested_mode"] == "text"
    assert payload["effective_mode"] == "text"
    assert "source_mix" in payload
    assert payload["provenance_notice"]["global_promotion_allowed"] is False
    assert payload["provenance_notice"]["public_lift_claim"] is False
