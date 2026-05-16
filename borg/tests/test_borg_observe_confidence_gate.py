import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.integrations import mcp_server


BASH_PERMISSION_MATCH = {
    "name": "bash-permission-denied",
    "id": "bash-permission-denied",
    "type": "pack",
    "source": "seed",
    "problem_class": "permission_denied",
    "solution": "Use chmod +x for scripts you own; avoid sudo/chmod 777.",
    "search_text": "bash permission denied chmod operation not permitted eacces",
}


def _stub_borg_observe_deps(monkeypatch, *, search_matches):
    monkeypatch.setattr(mcp_server, "_maybe_rebuild_index", lambda: None)
    monkeypatch.setattr(mcp_server, "_build_confidence_header", lambda tech, task: (
        "BORG [SYNTHETIC ONLY]\n"
        "Real traces: 0 | Synthetic: 0 | \n"
        "No real agent sessions -- guidance is from seed packs, unverified\n"
        "--------------------------------------------------"
    ))

    import borg.core.seed_loader as seed_loader
    import borg.core.trace_matcher as trace_matcher
    import borg.core.negative_traces as negative_traces
    import borg.core.search as search

    monkeypatch.setattr(seed_loader, "ensure_seeded", lambda: None)

    class EmptyTraceMatcher:
        def find_relevant(self, *args, **kwargs):
            return []

        def record_shown(self, *args, **kwargs):
            raise AssertionError("record_shown must not run without trace matches")

    monkeypatch.setattr(trace_matcher, "TraceMatcher", EmptyTraceMatcher)
    monkeypatch.setattr(negative_traces, "get_dead_end_patterns", lambda **kwargs: {"dead_ends": []})
    monkeypatch.setattr(search, "borg_search", lambda query: json.dumps({
        "success": True,
        "matches": search_matches,
        "query": query,
        "total": len(search_matches),
    }))

    try:
        import borg.core.embeddings as embeddings
        monkeypatch.setattr(embeddings, "semantic_search", lambda *args, **kwargs: [])
    except Exception:
        pass

    try:
        import borg.core.bm25_index as bm25_index

        class EmptyBM25:
            def search(self, *args, **kwargs):
                return []

        monkeypatch.setattr(bm25_index, "get_bm25_index", lambda *args, **kwargs: EmptyBM25())
    except Exception:
        pass


def test_unrelated_proof_dashboard_fails_closed_without_bash_permission_pack(monkeypatch):
    _stub_borg_observe_deps(monkeypatch, search_matches=[BASH_PERMISSION_MATCH])

    result = mcp_server._borg_observe_orig(
        task="Build a proof dashboard for investor readiness",
        context="",
        short=False,
    )

    assert "NO_CONFIDENT_MATCH" in result or "No confident Borg match" in result
    assert "PACK GUIDANCE (bash-permission-denied)" not in result
    assert "CONFIDENCE: Real traces: 0 | Synthetic: 0" not in result


def test_unrelated_adoption_truth_audit_fails_closed_without_bash_permission_pack(monkeypatch):
    _stub_borg_observe_deps(monkeypatch, search_matches=[BASH_PERMISSION_MATCH])

    result = mcp_server._borg_observe_orig(
        task="Audit all repos for adoption truth",
        context="",
        short=False,
    )

    assert "NO_CONFIDENT_MATCH" in result or "No confident Borg match" in result
    assert "PACK GUIDANCE (bash-permission-denied)" not in result


def test_concrete_permission_denied_can_still_return_bash_permission_guidance(monkeypatch):
    _stub_borg_observe_deps(monkeypatch, search_matches=[BASH_PERMISSION_MATCH])

    result = mcp_server._borg_observe_orig(
        task="Fix bash script permission denied when running ./deploy.sh",
        context="bash: ./deploy.sh: Permission denied",
        short=False,
    )

    assert "PACK GUIDANCE (bash-permission-denied)" in result
    assert "Use chmod +x" in result
    assert "NO_CONFIDENT_MATCH" not in result


def test_guidance_safety_suppresses_no_confident_match():
    guidance = """
ACTION: proceed with normal debugging.
CONFIDENCE: BORG [NO CONFIDENT MATCH]
NO_CONFIDENT_MATCH: No confident Borg match for this task.
"""
    assert mcp_server._guidance_is_safe_to_inject(guidance, "Audit docs", "") is False


def test_guidance_safety_suppresses_synthetic_pack_guidance():
    guidance = """
CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]
PACK GUIDANCE (git-merge-conflict)
Resolve conflict markers.
"""
    assert mcp_server._guidance_is_safe_to_inject(
        guidance,
        "Complete Borg supervised first-user beta proof package",
        "",
    ) is False


def test_embedded_borg_guidance_does_not_create_permission_signal():
    pasted_task = """whats next. Do the whole thing.

=== BORG GUIDANCE ===
CONFIDENCE: Real traces: 22 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (bash-permission-denied)
1. Check file permissions
"""
    assert "PACK GUIDANCE" not in mcp_server._strip_embedded_borg_guidance(pasted_task)
    assert mcp_server._permission_guidance_matches_task(pasted_task, "") is False


def test_guidance_safety_suppresses_real_traces_zero_pack_guidance():
    guidance = """
ACTION: Open conflicting files.
CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [LOW CONFIDENCE]
PACK GUIDANCE (git-merge-conflict)
Resolve conflict markers.
"""
    assert mcp_server._guidance_is_safe_to_inject(
        guidance,
        "Do the whole thing with tests and docs",
        "",
    ) is False


def test_guidance_safety_allows_real_permission_task():
    guidance = """
CONFIDENCE: Real traces: 3 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (bash-permission-denied)
Run chmod +x deploy.sh.
"""
    assert mcp_server._guidance_is_safe_to_inject(
        guidance,
        "Fix bash script permission denied when running ./deploy.sh",
        "bash: ./deploy.sh: Permission denied",
    ) is True
