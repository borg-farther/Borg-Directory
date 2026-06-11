"""Regression tests for D-015: privacy_redaction_count must reflect PII actually
redacted, not a re-scan of an already-redacted copy (which always finds zero)."""

from __future__ import annotations

from borg.core.collective_learning import CollectiveLearningStore, _privacy_prompt_summary

# AWS's documented example key + obviously-synthetic token/email/phone/path.
PII_PAYLOAD = {
    "error_pattern": (
        "PermissionError /home/jdoe/.aws/credentials "
        "AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE "
        "token ghp_aBcD1234567890aBcD1234567890aBcDeF "
        "contact jane.doe@acme-corp.com +1-415-555-0199"
    ),
}


def test_summary_counts_pii_in_raw_payload() -> None:
    # Before the fix this was 0 because the summary scanned an already-redacted
    # copy. The payload above carries >= 4 redactable spans (path/secret/email/phone).
    summary = _privacy_prompt_summary(PII_PAYLOAD)
    assert summary["privacy_redaction_count"] >= 4


def test_summary_zero_for_clean_payload() -> None:
    summary = _privacy_prompt_summary({"error_pattern": "TypeError: unsupported operand type(s)"})
    assert summary["privacy_redaction_count"] == 0


def test_recorded_event_carries_nonzero_redaction_count(tmp_path) -> None:
    """End-to-end: a contribution event recorded with PII in its payload must
    persist a non-zero privacy_redaction_count so operator privacy analytics are
    not blinded (gate #26)."""
    store = CollectiveLearningStore(db_path=str(tmp_path / "cl.db"))
    row = store.record_contribution_event(
        event_type="intervention",
        source_tool="borg_rescue",
        collective_stage="observed",
        payload=PII_PAYLOAD,
        task_text="PermissionError",
    )
    assert row["privacy_redaction_count"] >= 4
    # And the stored payload is still the redacted copy (no raw secret persisted).
    import json

    stored = json.dumps(row["payload"])
    assert "AKIAIOSFODNN7EXAMPLE" not in stored
    assert "jane.doe@acme-corp.com" not in stored
