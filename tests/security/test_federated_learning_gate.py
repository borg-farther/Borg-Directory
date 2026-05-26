"""Executable remote/federated learning GO gate tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_federated_learning_gate_writes_go_snapshot(tmp_path):
    output = tmp_path / "federated_learning_gate_snapshot.json"
    proc = subprocess.run(
        [sys.executable, "eval/run_federated_learning_gate.py", "--output", str(output)],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["success"] is True
    assert data["verdict"] == "GO"
    assert data["scope"] == "remote_global_federated_protocol"
    assert data["remote_http_signed_manifest"]["passed"] is True
    assert data["clean_client_sync"]["before_matches"] == 0
    assert data["clean_client_sync"]["after_matches"] == 1
    assert data["revocation_convergence"]["passed"] is True
    assert data["replay_protection"]["passed"] is True
    assert data["runtime_freshness"]["passed"] is True
    assert data["runtime_freshness"]["fingerprint"]["success"] is True
    assert data["broad_public_self_serve"] == "NO-GO"
    assert data["external_user_lift_claimed"] is False
    assert data["generated_at_utc"]
    assert data["proof_provenance"]["git"]["commit"]
    manifest = data["remote_http_signed_manifest"]
    for key in ["manifest_hash", "atom_id", "atom_envelope_hash", "receipt_id", "receipt_hash", "tombstone_hash"]:
        assert manifest[key]
    assert manifest["channel"] == "global"
    assert manifest["manifest_signature_key_id"] == manifest["registry_key_id"]
    assert data["revocation_convergence"]["post_revocation_get_atom_is_none"] is True
    assert data["revocation_convergence"]["reimport_suppressed"] is True
    assert "unsigned_manifest_rejected" in data["adversarial_coverage"]["in_tests"]
