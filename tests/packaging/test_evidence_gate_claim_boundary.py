from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "eval" / "tasksets" / "evidence_gate_shadow_protocol_v1.json"
SNAPSHOT = ROOT / "eval" / "evidence_gate_shadow_snapshot.json"

CURRENT_CLAIM_SURFACES = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    ROOT / "docs" / "EPISTEMIC_GUARDRAIL.md",
    ROOT / "docs" / "README.md",
    ROOT / "examples" / "openclaw-skill" / "SKILL.md",
    ROOT / "examples" / "skills" / "borg" / "SKILL.md",
    ROOT / "borg" / "seeds_data" / "borg" / "SKILL.md",
)


def test_current_surfaces_do_not_claim_runtime_enforcement() -> None:
    forbidden = (
        "requires verification before action",
        "verification controls action",
        "stops unsafe tool calls",
        "proves that referenced evidence entails",
    )
    for path in CURRENT_CLAIM_SURFACES:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"runtime-enforcement overclaim in {path.relative_to(ROOT)}: {phrase}"


def test_public_boundaries_disclose_advisory_no_go_status() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guardrail_doc = (ROOT / "docs" / "EPISTEMIC_GUARDRAIL.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "NO-GO" in readme
    assert "not runtime interposition" in readme
    assert "`NO_GO_STOP`" in guardrail_doc
    assert "not a security permission system or runtime action guardrail" in guardrail_doc
    assert "does **not** establish semantic entailment or authorization" in agents


def test_snapshot_is_bound_to_the_preregistered_protocol_and_source() -> None:
    protocol_bytes = PROTOCOL.read_bytes()
    protocol = json.loads(protocol_bytes)
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert hashlib.sha256(protocol_bytes).hexdigest() == "3a80532445965ffa2df576d32c90c5997fe00f979c3436309a2b59ceb9db6ebd"
    assert snapshot["preregistration"]["sha256"] == hashlib.sha256(protocol_bytes).hexdigest()
    assert snapshot["source"]["sha256"] == protocol["source_corpus"]["sha256"]
    assert snapshot["source"]["rows"] == protocol["source_corpus"]["expected_rows"]
    assert snapshot["execution"]["prediction_fingerprint"] == "44eedc26b73ec397dea3eacb90d5acd888a4511eb3ad2122ecc95e74e5bfc55e"


def test_no_go_snapshot_and_audit_are_numerically_consistent() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    audit = (ROOT / "docs" / "EVIDENCE_GATE_SHADOW_AUDIT.md").read_text(encoding="utf-8")
    c2 = snapshot["condition_metrics"]["C2_relevant_memory"]
    c3 = snapshot["condition_metrics"]["C3_shuffled_memory"]

    assert snapshot["verdict"] == "NO_GO_STOP"
    assert c2["tp"] == 53
    assert c2["fn"] == 95
    assert c2["fp"] == 66
    assert c2["tn"] == 85
    assert c2["hard_block_recall"] == 0.0
    assert c2["unsafe_intervention_recall"] == c3["unsafe_intervention_recall"]
    assert c2["safe_false_intervention_rate"] == c3["safe_false_intervention_rate"]
    assert len(snapshot["critical_harm_false_negative_ids"]) == 59

    for exact_fact in (
        "53 | 95 | 66 | 85",
        "35.8%",
        "43.7%",
        "59 unsafe trajectories",
        "hard-blocked a single unsafe trajectory",
    ):
        assert exact_fact in audit
