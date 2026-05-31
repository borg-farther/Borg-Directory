from __future__ import annotations

import json

from eval import served_runtime_gate


def _passing_payload(version: str = "9.9.9") -> dict:
    return {
        "success": True,
        "borg_version": version,
        "source_version": version,
        "version_matches_source": True,
        "reload_status": "loaded_code_matches_source_behavior",
        "confidence_gate_canary": {"passed": True},
        "observe_behavior_canary": {"passed": True, "meta_prompt_failed_closed": True},
    }


def test_served_runtime_gate_passes_matching_fresh_fingerprint() -> None:
    result = served_runtime_gate.evaluate_snapshot(_passing_payload(), expected_version="9.9.9")

    assert result["passed"] is True
    assert result["blockers"] == []


def test_served_runtime_gate_fails_stale_served_runtime() -> None:
    payload = _passing_payload("3.3.14")
    payload["source_version"] = "3.3.15"
    payload["version_matches_source"] = False
    payload["reload_status"] = "reload_or_patch_required"

    result = served_runtime_gate.evaluate_snapshot(payload, expected_version="3.3.15")

    assert result["passed"] is False
    joined = "\n".join(result["blockers"])
    assert "3.3.14" in joined
    assert "version_matches_source" in joined
    assert "reload_status" in joined


def test_served_runtime_gate_reads_mcp_tool_result_wrapper(tmp_path) -> None:
    snapshot = tmp_path / "fingerprint.json"
    snapshot.write_text(json.dumps({"result": json.dumps(_passing_payload("1.2.3"))}), encoding="utf-8")

    payload, error = served_runtime_gate._read_payload(snapshot)

    assert error is None
    assert payload and payload["borg_version"] == "1.2.3"
