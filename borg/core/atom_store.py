"""Local SQLite store for signed, sanitized learning atoms."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from borg.core.atom_policy import AtomDecision, classify_atom_policy
from borg.core.dirs import get_atom_db_path
from borg.core.learning_atoms import verify_signed_atom

ATOM_DB_PATH = str(get_atom_db_path())


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or str(get_atom_db_path())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS atoms (
            atom_id TEXT PRIMARY KEY,
            scope TEXT NOT NULL,
            status TEXT NOT NULL,
            task_type TEXT NOT NULL,
            technology TEXT NOT NULL,
            error_class TEXT,
            error_pattern TEXT,
            root_cause_class TEXT,
            worked TEXT NOT NULL,
            avoid TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            signature_json TEXT,
            privacy_risk_score REAL NOT NULL,
            prompt_injection_score REAL NOT NULL,
            helpfulness_score REAL DEFAULT 0.5,
            times_shown INTEGER DEFAULT 0,
            times_helped INTEGER DEFAULT 0,
            support_count INTEGER DEFAULT 1,
            independent_tenant_count INTEGER DEFAULT 1,
            created_at_day TEXT NOT NULL,
            expires_at_day TEXT,
            revoked_at TEXT,
            revocation_reason TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_atoms_scope_status ON atoms(scope, status);
        CREATE INDEX IF NOT EXISTS idx_atoms_error_class ON atoms(error_class);
        CREATE INDEX IF NOT EXISTS idx_atoms_technology ON atoms(technology);

        CREATE TABLE IF NOT EXISTS atom_tombstones (
            atom_id TEXT PRIMARY KEY,
            revoked_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            issuer_key_id TEXT,
            signature_json TEXT
        );

        CREATE TABLE IF NOT EXISTS atom_quarantine (
            quarantine_id TEXT PRIMARY KEY,
            source_trace_id TEXT,
            reason TEXT NOT NULL,
            risk_json TEXT NOT NULL,
            sanitized_preview_json TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()


class AtomStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or ATOM_DB_PATH

    def add_atom(self, envelope: Dict[str, Any], verified_tenant_count: int | None = None) -> str:
        payload = envelope.get("payload", envelope)
        atom_id = payload.get("atom_id")
        if self.is_revoked(atom_id):
            raise ValueError("atom is tombstoned")
        signature_check = None
        if envelope.get("signature"):
            signature_check = verify_signed_atom(envelope)
            if not signature_check.valid:
                raise ValueError(f"atom rejected by signature verification: {signature_check.error}")
        has_valid_signature = bool(signature_check and signature_check.valid)
        if payload.get("scope") != "local" and not has_valid_signature:
            raise ValueError("shared atom must have a valid signed atom envelope")
        decision = classify_atom_policy(
            payload,
            has_valid_signature=has_valid_signature,
            verified_tenant_count=verified_tenant_count,
        )
        if decision.decision not in {AtomDecision.LOCAL_SAFE, AtomDecision.ORG_SAFE, AtomDecision.GLOBAL_CANDIDATE}:
            raise ValueError(f"atom rejected by policy: {decision.decision.value}")

        task = payload.get("task") or {}
        learning = payload.get("learning") or {}
        privacy = payload.get("privacy") or {}
        safety = payload.get("safety") or {}
        evidence = payload.get("evidence") or {}
        trust = payload.get("trust") or {}
        lifecycle = payload.get("lifecycle") or {}
        indexed_tenant_count = int(verified_tenant_count) if verified_tenant_count is not None else 0
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO atoms
                (atom_id, scope, status, task_type, technology, error_class, error_pattern,
                 root_cause_class, worked, avoid, payload_json, signature_json,
                 privacy_risk_score, prompt_injection_score, support_count,
                 independent_tenant_count, created_at_day, expires_at_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    atom_id,
                    payload.get("scope", "local"),
                    lifecycle.get("status", decision.decision.value),
                    task.get("type", "other"),
                    json.dumps(task.get("technology", [])),
                    task.get("error_class", ""),
                    task.get("error_pattern", ""),
                    learning.get("root_cause_class", ""),
                    learning.get("worked", ""),
                    json.dumps(learning.get("avoid", [])),
                    json.dumps(payload, sort_keys=True),
                    json.dumps(envelope.get("signature", {}), sort_keys=True),
                    float(privacy.get("risk_score", 0)),
                    float(safety.get("prompt_injection_score", 0)),
                    int(evidence.get("support_count", 1)),
                    indexed_tenant_count,
                    lifecycle.get("created_at_day", time.strftime("%Y-%m-%d")),
                    lifecycle.get("expires_at_day"),
                ),
            )
            conn.commit()
        return atom_id

    def get_atom(self, atom_id: str) -> Dict[str, Any] | None:
        if self.is_revoked(atom_id):
            return None
        with _connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT payload_json, independent_tenant_count FROM atoms WHERE atom_id = ? AND revoked_at IS NULL",
                (atom_id,),
            ).fetchone()
        if not row:
            return None
        atom = json.loads(row["payload_json"])
        trust = atom.setdefault("trust", {})
        # Return the same store/registry-computed quorum contract as search:
        # payload tenant hints remain advisory, including for direct get-by-id.
        trust["verified_tenant_count"] = int(row["independent_tenant_count"])
        return atom

    def is_revoked(self, atom_id: str | None) -> bool:
        if not atom_id:
            return False
        with _connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM atom_tombstones WHERE atom_id = ?", (atom_id,)).fetchone()
        return bool(row)

    def revoke(self, atom_id: str, reason: str, issuer_key_id: str = "") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with _connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO atom_tombstones (atom_id, revoked_at, reason, issuer_key_id, signature_json) VALUES (?, ?, ?, ?, ?)", (atom_id, now, reason, issuer_key_id, "{}"))
            conn.execute("UPDATE atoms SET revoked_at = ?, revocation_reason = ? WHERE atom_id = ?", (now, reason, atom_id))
            conn.commit()

    def search_atoms(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        q = f"%{query.lower()}%"
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json, independent_tenant_count FROM atoms
                WHERE revoked_at IS NULL
                  AND atom_id NOT IN (SELECT atom_id FROM atom_tombstones)
                  AND (LOWER(error_class) LIKE ? OR LOWER(error_pattern) LIKE ? OR LOWER(worked) LIKE ?)
                ORDER BY helpfulness_score DESC, independent_tenant_count DESC
                LIMIT ?
                """,
                (q, q, q, limit),
            ).fetchall()
        atoms = []
        for row in rows:
            atom = json.loads(row["payload_json"])
            trust = atom.setdefault("trust", {})
            # Retrieval must display the registry/store verified quorum, never a
            # submitter's self-declared tenant count from the signed payload.
            trust["verified_tenant_count"] = int(row["independent_tenant_count"])
            atoms.append(atom)
        return atoms
