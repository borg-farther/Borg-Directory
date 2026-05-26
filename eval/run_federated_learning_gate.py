#!/usr/bin/env python3
"""Executable GO gate for Borg remote/global/federated learning protocol.

This gate proves the code/protocol path, not broad public launch:

A clean client syncs a signed global atom from a hosted HTTP registry manifest,
retrieves it with registry-computed quorum evidence, then receives a tombstone
and stops retrieving it within the declared SLO. It also records runtime
freshness and replay protection checks in a machine-readable snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borg.core.atom_registry import (  # noqa: E402
    ingest_atom_envelope,
    revoke_registry_atom,
    sync_signed_registry_to_store,
    write_signed_registry_manifest,
)
from borg.core.atom_store import AtomStore  # noqa: E402
from borg.core.atom_tenant import tenant_pseudonym  # noqa: E402
from borg.core.crypto import derive_verify_key, generate_signing_key  # noqa: E402
from borg.core.learning_atoms import compute_atom_id, learning_atom_key_id_from_verify_key, sign_learning_atom  # noqa: E402
from borg.core.runtime_fingerprint import runtime_fingerprint  # noqa: E402


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _canonical_sha256(payload: Dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_git_context() -> Dict[str, Any]:
    def run(*args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
            return proc.stdout.strip() if proc.returncode == 0 else ""
        except Exception:
            return ""

    status = run("status", "--short")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status),
        "dirty_files": [line for line in status.splitlines() if line],
    }


@contextmanager
def _serve_directory(path: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(path))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def _atom(scope: str = "global_candidate", tenant: str = "tenant-a") -> dict:
    atom = {
        "schema_version": "1.0",
        "scope": scope,
        "task": {
            "type": "debug",
            "technology": ["python"],
            "error_class": "type-error",
            "error_pattern": "optional config none",
            "difficulty": "unknown",
        },
        "learning": {
            "root_cause_class": "missing_validation",
            "worked": "Validate optional value before split",
            "avoid": ["Blind reinstall"],
            "why": "Optional value was None",
        },
        "evidence": {"type": "test_passed", "strength": "medium", "support_count": 1},
        "privacy": {
            "risk_score": 0,
            "scanner_version": "privacy-v1",
            "finding_classes": [],
            "redaction_count": 0,
            "raw_trace_retained": False,
        },
        "safety": {
            "prompt_injection_score": 0,
            "injection_classes": [],
            "imperative_text_removed": True,
            "retrieval_treatment": "untrusted_advisory",
        },
        "trust": {
            "submitter_key_id": "",
            "tenant_pseudonym": tenant_pseudonym(tenant, b"federated-gate-test-secret"),
            "agent_reputation_at_submit": 0,
            # Deliberately inflated. The registry manifest must carry/display
            # verified_tenant_count=3 instead of trusting this payload hint.
            "independent_tenant_count": 999,
            "promotion_score": 0,
        },
        "lifecycle": {
            "status": "global_candidate",
            "created_at_day": "2026-05-26",
            "expires_at_day": "2026-08-26",
            "revoked_at": None,
            "revocation_reason": None,
        },
    }
    atom["atom_id"] = compute_atom_id(atom)
    return atom


def _registry_key_id(signing_key) -> str:
    return learning_atom_key_id_from_verify_key(derive_verify_key(signing_key))


def run_gate(max_revocation_convergence_seconds: float = 2.0) -> Dict[str, Any]:
    generated_at_utc = _utc_now()
    with tempfile.TemporaryDirectory(prefix="borg-federated-gate-") as td:
        tmp = Path(td)
        registry = tmp / "hosted-registry"
        store_b = AtomStore(str(tmp / "client-b.db"))
        state_path = tmp / "client-b-sync-state.json"
        atom_signing_key = generate_signing_key()
        registry_signing_key = generate_signing_key()
        trusted_registry_key_id = _registry_key_id(registry_signing_key)

        runtime = runtime_fingerprint()
        runtime_passed = bool(
            runtime.get("success")
            and runtime.get("version_matches_source")
            and runtime.get("confidence_gate_canary", {}).get("passed")
            and runtime.get("observe_behavior_canary", {}).get("passed")
        )

        envelope = sign_learning_atom(_atom(), atom_signing_key)
        receipt = ingest_atom_envelope(envelope, registry, verified_tenant_count=3)
        manifest_1 = write_signed_registry_manifest(
            registry,
            registry_signing_key,
            sequence=1,
            channel="global",
            expires_in_seconds=120,
        )
        atom_id = manifest_1["payload"]["atoms"][0]["atom_id"]
        atom_file = registry / "atoms" / (atom_id.replace(":", "_") + ".json")
        receipt_file = Path(receipt.path)
        manifest_1_hash = _canonical_sha256(manifest_1)
        atom_envelope_hash = _file_sha256(atom_file)
        receipt_hash = _file_sha256(receipt_file)
        before_matches = len(store_b.search_atoms("optional"))

        with _serve_directory(registry) as base_url:
            first_sync = sync_signed_registry_to_store(
                base_url,
                store_b,
                trusted_registry_key_id=trusted_registry_key_id,
                channel="global",
                state_path=state_path,
                max_revocation_convergence_seconds=max_revocation_convergence_seconds,
            )
            after_matches = len(store_b.search_atoms("optional"))

            revoke_registry_atom(registry, atom_id, "federated gate revocation canary")
            write_signed_registry_manifest(
                registry,
                registry_signing_key,
                sequence=2,
                channel="global",
                expires_in_seconds=120,
            )
            second_sync = sync_signed_registry_to_store(
                base_url,
                store_b,
                trusted_registry_key_id=trusted_registry_key_id,
                channel="global",
                state_path=state_path,
                max_revocation_convergence_seconds=max_revocation_convergence_seconds,
            )
            after_revocation_matches = len(store_b.search_atoms("optional"))
            post_revocation_get_atom_is_none = store_b.get_atom(atom_id) is None
            tombstone_file = registry / "tombstones" / (atom_id.replace(":", "_") + ".json")
            tombstone_hash = _file_sha256(tombstone_file)

            write_signed_registry_manifest(
                registry,
                registry_signing_key,
                sequence=1,
                channel="global",
                expires_in_seconds=120,
            )
            replay_blocked = False
            replay_error = ""
            try:
                sync_signed_registry_to_store(
                    base_url,
                    store_b,
                    trusted_registry_key_id=trusted_registry_key_id,
                    channel="global",
                    state_path=state_path,
                )
            except ValueError as exc:
                replay_blocked = "replay" in str(exc).lower()
                replay_error = str(exc)

        clean_sync_passed = before_matches == 0 and after_matches == 1 and first_sync["imported"] == 1
        revocation_passed = (
            second_sync["revoked"] >= 1
            and after_revocation_matches == 0
            and post_revocation_get_atom_is_none
            and second_sync["skipped"] >= 1
            and second_sync["revocation_convergence_seconds"] <= max_revocation_convergence_seconds
        )
        signed_manifest_passed = (
            manifest_1["signature"]["key_id"] == trusted_registry_key_id
            and manifest_1["payload"]["sequence"] == 1
            and manifest_1["payload"]["atoms"][0].get("verified_tenant_count") == 3
        )
        success = bool(runtime_passed and signed_manifest_passed and clean_sync_passed and revocation_passed and replay_blocked)
        return {
            "schema_version": 1,
            "generated_at_utc": generated_at_utc,
            "success": success,
            "verdict": "GO" if success else "NO-GO",
            "scope": "remote_global_federated_protocol",
            "broad_public_self_serve": "NO-GO",
            "external_user_lift_claimed": False,
            "external_user_lift_note": "This gate proves clean-client protocol lift, not row-derived real external-user usefulness.",
            "proof_provenance": {
                "command": "python eval/run_federated_learning_gate.py --output eval/federated_learning_gate_snapshot.json",
                "max_revocation_convergence_seconds": max_revocation_convergence_seconds,
                "git": _safe_git_context(),
            },
            "remote_http_signed_manifest": {
                "passed": signed_manifest_passed,
                "registry_key_id": trusted_registry_key_id,
                "sequence": manifest_1["payload"]["sequence"],
                "channel": manifest_1["payload"]["channel"],
                "expires_at": manifest_1["payload"]["expires_at"],
                "manifest_hash": manifest_1_hash,
                "manifest_signature_key_id": manifest_1["signature"]["key_id"],
                "atom_count": len(manifest_1["payload"].get("atoms", [])),
                "tombstone_count_after_revoke": second_sync["revoked"],
                "receipt_decision": receipt.decision,
                "receipt_id": receipt.receipt_id,
                "receipt_hash": receipt_hash,
                "atom_id": atom_id,
                "atom_envelope_hash": atom_envelope_hash,
                "tombstone_hash": tombstone_hash,
            },
            "runtime_freshness": {
                "passed": runtime_passed,
                "borg_version": runtime.get("borg_version"),
                "source_version": runtime.get("source_version"),
                "version_matches_source": runtime.get("version_matches_source"),
                "confidence_gate_canary": runtime.get("confidence_gate_canary", {}).get("passed"),
                "observe_behavior_canary": runtime.get("observe_behavior_canary", {}).get("passed"),
                "fingerprint": runtime,
            },
            "clean_client_sync": {
                "passed": clean_sync_passed,
                "before_matches": before_matches,
                "after_matches": after_matches,
                "first_sync": first_sync,
                "verified_tenant_count_source": "signed_registry_manifest",
            },
            "revocation_convergence": {
                "passed": revocation_passed,
                "slo_seconds": max_revocation_convergence_seconds,
                "observed_seconds": second_sync["revocation_convergence_seconds"],
                "after_revocation_matches": after_revocation_matches,
                "post_revocation_get_atom_is_none": post_revocation_get_atom_is_none,
                "reimport_suppressed": second_sync["skipped"] >= 1,
                "second_sync": second_sync,
            },
            "replay_protection": {
                "passed": replay_blocked,
                "error": replay_error,
            },
            "adversarial_coverage": {
                "in_gate": ["clean_client_http_sync", "tombstone_revocation_convergence", "manifest_replay_rejected"],
                "in_tests": [
                    "unsigned_manifest_rejected",
                    "manifest_payload_tamper_rejected",
                    "untrusted_registry_key_rejected",
                    "expired_manifest_rejected",
                    "channel_mismatch_rejected",
                    "hash_mismatch_no_partial_import",
                    "payload_inflated_tenant_count_ignored",
                    "revoked_atom_search_get_reimport_blocked",
                ],
            },
            "references": [
                "https://theupdateframework.github.io/specification/latest/",
                "https://docs.sigstore.dev/logging/overview/",
                "https://slsa.dev/attestation-model",
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Borg remote/federated learning protocol GO gate")
    parser.add_argument("--output", default=str(ROOT / "eval" / "federated_learning_gate_snapshot.json"))
    parser.add_argument("--max-revocation-convergence-seconds", type=float, default=2.0)
    args = parser.parse_args(argv)

    result = run_gate(args.max_revocation_convergence_seconds)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
