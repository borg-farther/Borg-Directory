from borg.core import confidence_gate


NO_MATCH_GUIDANCE = """
ACTION: proceed with normal debugging.
CONFIDENCE: BORG [NO CONFIDENT MATCH]
NO_CONFIDENT_MATCH: No confident Borg match for this task.
"""

SYNTHETIC_PACK_GUIDANCE = """
ACTION: Open conflicting files.
CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]
PACK GUIDANCE (git-merge-conflict)
Resolve conflict markers.
"""

ZERO_REAL_LOW_CONFIDENCE_GUIDANCE = """
ACTION: Open conflicting files.
CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [LOW CONFIDENCE]
PACK GUIDANCE (git-merge-conflict)
Resolve conflict markers.
"""

GOOD_REAL_GUIDANCE = """
ACTION: Pin the package version and rerun the failing import.
CONFIDENCE: Real traces: 4 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
WHAT WORKED (4 prior sessions)
Root cause: dependency drift
"""

PERMISSION_GUIDANCE = """
CONFIDENCE: Real traces: 3 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (bash-permission-denied)
Run chmod +x deploy.sh.
"""

PASTED_BORG_GUIDANCE_TASK = """OK, great. Keep going.

=== BORG GUIDANCE ===
CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]
PACK GUIDANCE (bash-permission-denied)
1. Check file permissions: ls -la
"""


def test_strip_embedded_borg_guidance_removes_stale_block():
    cleaned = confidence_gate.strip_embedded_borg_guidance(PASTED_BORG_GUIDANCE_TASK)
    assert "OK, great" in cleaned
    assert "PACK GUIDANCE" not in cleaned
    assert "bash-permission-denied" not in cleaned


def test_permission_guidance_requires_clean_permission_signal():
    assert confidence_gate.permission_guidance_matches_task(
        "Fix ./deploy.sh: Permission denied",
        "",
    ) is True
    assert confidence_gate.permission_guidance_matches_task(PASTED_BORG_GUIDANCE_TASK, "") is False


def test_guidance_safety_suppresses_no_confident_match():
    assert confidence_gate.guidance_is_safe_to_inject(NO_MATCH_GUIDANCE, "Audit docs", "") is False


def test_guidance_safety_suppresses_synthetic_pack_guidance():
    assert confidence_gate.guidance_is_safe_to_inject(
        SYNTHETIC_PACK_GUIDANCE,
        "Complete Borg supervised first-user beta proof package",
        "",
    ) is False


def test_guidance_safety_suppresses_zero_real_pack_guidance_even_without_synthetic_label():
    assert confidence_gate.guidance_is_safe_to_inject(
        ZERO_REAL_LOW_CONFIDENCE_GUIDANCE,
        "Do the whole thing with tests and docs",
        "",
    ) is False


def test_guidance_safety_allows_real_high_confidence_guidance_without_pack_leak():
    assert confidence_gate.guidance_is_safe_to_inject(
        GOOD_REAL_GUIDANCE,
        "Fix ModuleNotFoundError after package upgrade",
        "ModuleNotFoundError: No module named flask",
    ) is True


def test_guidance_safety_allows_permission_guidance_for_real_permission_task():
    assert confidence_gate.guidance_is_safe_to_inject(
        PERMISSION_GUIDANCE,
        "Fix bash script permission denied when running ./deploy.sh",
        "bash: ./deploy.sh: Permission denied",
    ) is True


def test_guidance_safety_suppresses_permission_guidance_if_only_stale_block_mentions_permission():
    assert confidence_gate.guidance_is_safe_to_inject(
        PERMISSION_GUIDANCE,
        PASTED_BORG_GUIDANCE_TASK,
        "",
    ) is False


def test_no_confident_match_response_has_required_action_stop_verify_contract():
    response = confidence_gate.no_confident_match_response("python")
    assert response.startswith("ACTION:")
    assert "STOP:" in response
    assert "VERIFY:" in response
    assert "CONFIDENCE: BORG [NO CONFIDENT MATCH]" in response
    assert "NO_CONFIDENT_MATCH" in response


def test_trace_confidence_rejects_medium_similarity_meta_overlap_only():
    trace = {
        "similarity": 0.48,
        "root_cause": "BORG_HOME was not set in the Hermes plugin service file.",
        "approach_summary": "Patch the real plugin runtime path and verify traces.db loading.",
    }

    assert confidence_gate.trace_match_is_confident(
        trace,
        query="continue Borg first-user readiness: fix borg_observe trace matching relevance bug",
    ) is False


def test_trace_confidence_allows_medium_similarity_with_concrete_error_overlap():
    trace = {
        "similarity": 0.52,
        "root_cause": "Flask was missing from the package environment.",
        "approach_summary": "Install the missing flask dependency and rerun the import smoke test.",
        "errors_encountered": "ModuleNotFoundError: No module named flask",
    }

    assert confidence_gate.trace_match_is_confident(
        trace,
        query="Fix ModuleNotFoundError: No module named flask after package upgrade",
    ) is True
