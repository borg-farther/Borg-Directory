from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_collective_intelligence_loop_gate_proves_internal_loop_without_external_lift(tmp_path):
    output = tmp_path / "collective-gate.json"
    proc = subprocess.run(
        [sys.executable, "eval/run_collective_intelligence_loop_gate.py", "--output", str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["verdict"] == "GO"
    assert data["scope"] == "max_value_collective_intelligence_loop_primitives"
    assert data["public_external_lift"].startswith("NO-GO")
    assert all(data["checks"].values())
    assert data["registry_quorum"]["computed_from_outcome_receipts"] == 3
    assert data["registry_quorum"]["payload_hint"] == 99
    assert data["registry_quorum"]["receipt_verified_tenant_count"] == 3
    assert data["registry_quorum"]["promoted_direct_recompute"] == 0
    assert data["registry_quorum"]["promoted_explicit_rebind_recompute"] == 3
    assert data["checks"]["cluster_promotion_direct_recompute_strict"] is True
    assert data["checks"]["cluster_promotion_rebind_requires_supporting_receipts"] is True
    assert data["retrieval_top"]["source"] == "learning_atom"
    assert data["contribution_summary"]["by_type"]["intervention"] == 4
    assert data["contribution_summary"]["by_type"]["outcome_receipt"] == 4
    assert data["atom_candidate"]["promotable"] is True
    assert data["atom_candidate"]["helpful_verified_tenants"] == 3
    assert data["registry_promotion"]["decision"] == "global_candidate"
    assert data["registry_promotion"]["reason"] == "accepted"
    assert data["registry_promotion"]["verified_tenant_count"] == 3
    assert data["retrieval_top"]["atom_id"] == data["registry_promotion"]["atom_id"]
    assert "verified_quorum" in data["retrieval_top"]["score_reasons"]
    assert "helpful_outcomes" in data["retrieval_top"]["score_reasons"]
    assert "negative_evidence_present" in data["retrieval_top"]["score_reasons"]
    assert data["first10_counts"].get("real_users", 0) == 0
