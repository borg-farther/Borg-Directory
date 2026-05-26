"""Remote federated learning registry proof tests.

These tests are intentionally stricter than local filesystem staging: a clean
client must sync only from a signed manifest served over an HTTP boundary, reject
replay/tampering, and converge revocations within the declared SLO.
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from borg.core.atom_registry import (
    ingest_atom_envelope,
    revoke_registry_atom,
    sync_signed_registry_to_store,
    write_signed_registry_manifest,
)
from borg.core.atom_store import AtomStore
from borg.core.atom_tenant import tenant_pseudonym
from borg.core.crypto import derive_verify_key, generate_signing_key
from borg.core.learning_atoms import compute_atom_id, learning_atom_key_id_from_verify_key, sign_learning_atom


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
            "tenant_pseudonym": tenant_pseudonym(tenant, b"test-secret"),
            "agent_reputation_at_submit": 0,
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


def _publish_one_global_atom(registry: Path, atom_signing_key, registry_signing_key, sequence: int = 1) -> dict:
    envelope = sign_learning_atom(_atom(), atom_signing_key)
    ingest_atom_envelope(envelope, registry, verified_tenant_count=3)
    return write_signed_registry_manifest(
        registry,
        registry_signing_key,
        sequence=sequence,
        channel="global",
        expires_in_seconds=120,
    )


def test_remote_signed_manifest_a_to_b_sync_then_tombstone_converges(tmp_path):
    registry = tmp_path / "registry"
    store_b = AtomStore(str(tmp_path / "client-b.db"))
    state_path = tmp_path / "client-b-sync-state.json"
    atom_signing_key = generate_signing_key()
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)

    manifest = _publish_one_global_atom(registry, atom_signing_key, registry_signing_key, sequence=1)
    atom_id = manifest["payload"]["atoms"][0]["atom_id"]

    with _serve_directory(registry) as base_url:
        first = sync_signed_registry_to_store(
            base_url,
            store_b,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=state_path,
            max_revocation_convergence_seconds=2.0,
        )
        assert first["remote"] is True
        assert first["manifest_sequence"] == 1
        assert first["imported"] == 1
        assert first["revoked"] == 0
        found = store_b.search_atoms("optional")
        assert found
        assert found[0]["trust"]["verified_tenant_count"] == 3
        assert found[0]["trust"]["independent_tenant_count"] == 999

        revoke_registry_atom(registry, atom_id, "bad guidance")
        write_signed_registry_manifest(
            registry,
            registry_signing_key,
            sequence=2,
            channel="global",
            expires_in_seconds=120,
        )
        second = sync_signed_registry_to_store(
            base_url,
            store_b,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=state_path,
            max_revocation_convergence_seconds=2.0,
        )

    assert second["manifest_sequence"] == 2
    assert second["revoked"] == 1
    assert second["revocation_convergence_seconds"] <= 2.0
    assert store_b.get_atom(atom_id) is None
    assert store_b.search_atoms("optional") == []


def test_remote_sync_rejects_unsigned_manifest(tmp_path):
    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "manifest.signed.json").write_text(json.dumps({"payload": {"sequence": 1}}), encoding="utf-8")
    store = AtomStore(str(tmp_path / "client.db"))

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="signature"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id="ed25519:missing",
            channel="global",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []


def test_remote_sync_rejects_manifest_hash_mismatch_without_partial_import(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=1)

    manifest_path = registry / "manifest.signed.json"
    signed = json.loads(manifest_path.read_text(encoding="utf-8"))
    signed["payload"]["atoms"][0]["sha256"] = "0" * 64
    # Re-sign the attacker-modified manifest to prove clients also verify file hashes,
    # not just the manifest signature.
    write_signed_registry_manifest(
        registry,
        registry_signing_key,
        sequence=1,
        channel="global",
        expires_in_seconds=120,
        manifest_payload_override=signed["payload"],
    )

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="hash mismatch"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []


def test_remote_sync_rejects_manifest_payload_tamper_without_resign(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=1)

    manifest_path = registry / "manifest.signed.json"
    signed = json.loads(manifest_path.read_text(encoding="utf-8"))
    signed["payload"]["sequence"] = 2
    manifest_path.write_text(json.dumps(signed), encoding="utf-8")

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="signature"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []


def test_remote_sync_rejects_channel_mismatch(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=1)

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="channel mismatch"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=trusted_key_id,
            channel="org",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []


def test_remote_sync_rejects_replayed_older_sequence(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    state_path = tmp_path / "state.json"
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=2)

    with _serve_directory(registry) as base_url:
        first = sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=state_path,
        )
        assert first["manifest_sequence"] == 2

        write_signed_registry_manifest(
            registry,
            registry_signing_key,
            sequence=1,
            channel="global",
            expires_in_seconds=120,
        )
        with pytest.raises(ValueError, match="replay"):
            sync_signed_registry_to_store(
                base_url,
                store,
                trusted_registry_key_id=trusted_key_id,
                channel="global",
                state_path=state_path,
            )


def test_remote_sync_rejects_expired_manifest(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    registry_signing_key = generate_signing_key()
    trusted_key_id = _registry_key_id(registry_signing_key)
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=1)
    write_signed_registry_manifest(
        registry,
        registry_signing_key,
        sequence=1,
        channel="global",
        expires_in_seconds=-1,
    )

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="expired"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=trusted_key_id,
            channel="global",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []


def test_remote_sync_rejects_untrusted_registry_key(tmp_path):
    registry = tmp_path / "registry"
    store = AtomStore(str(tmp_path / "client.db"))
    registry_signing_key = generate_signing_key()
    attacker_or_wrong_key = _registry_key_id(generate_signing_key())
    _publish_one_global_atom(registry, generate_signing_key(), registry_signing_key, sequence=1)

    with _serve_directory(registry) as base_url, pytest.raises(ValueError, match="untrusted registry key"):
        sync_signed_registry_to_store(
            base_url,
            store,
            trusted_registry_key_id=attacker_or_wrong_key,
            channel="global",
            state_path=tmp_path / "state.json",
        )

    assert store.search_atoms("optional") == []
