"""Outcome-grounded collective intelligence loop for Borg.

This module is intentionally small and boring: signed transport proves that safe
atoms can move; this store proves whether guidance actually helped.  The core
contract is:

    intervention shown -> verified outcome receipt -> dedupe/generalize ->
    registry quorum -> unified scored retrieval

Nothing here claims public launch or external-user lift.  First-10 measured lift
still comes only from consented row-level evidence in eval/first_10_*.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from borg.core.atom_store import AtomStore
from borg.core.atom_tenant import is_valid_tenant_pseudonym, tenant_pseudonym as derive_tenant_pseudonym
from borg.core.crypto import decode_key, derive_verify_key, encode_key, generate_signing_key, signing_key_from_string, verify_key_from_string
from borg.core.dirs import get_borg_home
from borg.core.learning_atoms import compute_atom_id, learning_atom_key_id_from_verify_key, sign_learning_atom, validate_learning_atom
from borg.core.privacy import privacy_risk_score, privacy_scan_structured
from borg.core.prompt_injection import neutralize_for_retrieval, scan_prompt_injection

_WORD_RE = re.compile(r"[a-z0-9_\.:-]+", re.I)
_SECRETISH_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{16,}|xox[baprs]-[a-z0-9-]{16,}|"
    r"akia[0-9a-z]{16}|password\s*=\s*\S+|api[_-]?key\s*=\s*\S+|token\s*=\s*\S+)"
)


def get_collective_learning_db_path() -> Path:
    return get_borg_home() / "collective_learning.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _canonical_json_bytes(value: Any) -> bytes:
    return _canonical_json(value).encode("utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "ignore")).hexdigest()


def _receipt_id(material: Dict[str, Any]) -> str:
    return "outcome-sha256:" + _sha256_text(_canonical_json(material))


def _intervention_id(material: Dict[str, Any]) -> str:
    return "intervention-sha256:" + _sha256_text(_canonical_json(material))


def _safe_text(value: Any, max_chars: int = 1600) -> str:
    text = str(value or "")
    text = _SECRETISH_RE.sub("[REDACTED]", text)
    try:
        text = privacy_scan_structured(text).sanitized
    except Exception:
        # Privacy scanner is best-effort here; the regex above catches common
        # credential classes so outcome recording never depends on optional deps.
        pass
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _redact_json_value(value: Any, *, max_text_chars: int = 1200, depth: int = 0) -> Any:
    """Return a JSON-safe, privacy-redacted copy of a contribution payload."""
    if depth > 6:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {str(_safe_text(key, max_chars=120)): _redact_json_value(val, max_text_chars=max_text_chars, depth=depth + 1) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_redact_json_value(item, max_text_chars=max_text_chars, depth=depth + 1) for item in list(value)[:50]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _safe_text(value, max_chars=max_text_chars)


def _privacy_prompt_summary(value: Any) -> Dict[str, Any]:
    text = _canonical_json(_redact_json_value(value, max_text_chars=1600))
    try:
        privacy = privacy_scan_structured(text)
        redaction_count = len(privacy.findings)
    except Exception:
        redaction_count = 0
    try:
        injection = scan_prompt_injection(text)
        injection_score = float(injection.score)
        injection_classes = sorted({finding.kind for finding in injection.findings})
    except Exception:
        injection_score = 0.0
        injection_classes = []
    return {
        "privacy_redaction_count": int(redaction_count),
        "prompt_injection_score": injection_score,
        "prompt_injection_classes": injection_classes,
    }


def _event_id(material: Dict[str, Any]) -> str:
    return "contribution-sha256:" + _sha256_text(_canonical_json(material))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "success", "helpful"}


def _normalize_tenant_pseudonym(value: Any) -> str:
    """Return the only tenant identifier format allowed in receipts.

    Raw names are accepted only as local input convenience and immediately
    converted to the installation's HMAC pseudonym.  Exported/shared receipts
    always contain `hmac-sha256:<64 hex>`.
    """
    text = _safe_text(value or "local", max_chars=160)
    if is_valid_tenant_pseudonym(text):
        return text
    return derive_tenant_pseudonym(text or "local")


def _outcome_key_path(db_path: str | Path | None = None) -> Path:
    if db_path:
        return Path(db_path).with_suffix(Path(db_path).suffix + ".outcome-signing-key")
    return get_borg_home() / "outcome_receipt_signing_key"


def _load_or_create_outcome_signing_key(path: str | Path | None = None) -> Any:
    key_path = Path(path) if path else _outcome_key_path()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return signing_key_from_string(key_path.read_text(encoding="utf-8").strip())
    signing_key = generate_signing_key()
    seed = signing_key.encode()
    key_path.write_text(encode_key(bytes(seed)), encoding="utf-8")
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return signing_key


def _outcome_receipt_material(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intervention_id": payload.get("intervention_id"),
        "created_at": payload.get("created_at"),
        "receipt_nonce": payload.get("receipt_nonce"),
        "outcome": str(payload.get("outcome") or "").lower(),
        "helpful": _as_bool(payload.get("helpful")),
        "verified": _as_bool(payload.get("verified")),
        "tenant_pseudonym": payload.get("tenant_pseudonym"),
        "atom_id": payload.get("atom_id"),
        "cluster_id": payload.get("cluster_id"),
    }


def sign_outcome_receipt_payload(payload: Dict[str, Any], signing_key: Any) -> Dict[str, Any]:
    """Return a signed outcome-receipt envelope.

    The signature is an integrity/authenticity check for exported registry files;
    it does not by itself prove external-user lift or Sybil-resistant identity.
    """
    from nacl import encoding

    receipt_payload = dict(payload)
    receipt_payload["receipt_id"] = _receipt_id(_outcome_receipt_material(receipt_payload))
    verify_key = derive_verify_key(signing_key)
    key_id = learning_atom_key_id_from_verify_key(verify_key)
    signed = signing_key.sign(_canonical_json_bytes(receipt_payload), encoder=encoding.RawEncoder)
    return {
        "type": "borg_outcome_receipt",
        "envelope_version": "1.0",
        "id": receipt_payload["receipt_id"],
        "payload": receipt_payload,
        "signature": {
            "algorithm": "ed25519",
            "key_id": key_id,
            "verify_key": encode_key(bytes(verify_key)),
            "signature_b64url": encode_key(bytes(signed.signature)),
            "signed_at": _utc_now(),
        },
    }


def verify_outcome_receipt_envelope(
    envelope: Dict[str, Any],
    *,
    trusted_receipt_signer_key_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Verify a signed outcome receipt and return its payload.

    Raises ValueError on unsigned, tampered, malformed, or non-pseudonymous
    receipts so registry quorum cannot be inflated by hand-written JSON files.
    """
    try:
        from nacl import encoding, exceptions

        if envelope.get("type") != "borg_outcome_receipt":
            raise ValueError("outcome receipt envelope type must be borg_outcome_receipt")
        if envelope.get("envelope_version") != "1.0":
            raise ValueError("outcome receipt envelope_version must be 1.0")
        payload = envelope.get("payload")
        signature = envelope.get("signature")
        if not isinstance(payload, dict) or not isinstance(signature, dict):
            raise ValueError("outcome receipt payload and signature are required")
        if envelope.get("id") != payload.get("receipt_id"):
            raise ValueError("outcome receipt envelope id does not match payload receipt_id")
        expected_receipt_id = _receipt_id(_outcome_receipt_material(payload))
        if payload.get("receipt_id") != expected_receipt_id:
            raise ValueError("outcome receipt_id does not match canonical payload")
        verify_key = verify_key_from_string(str(signature.get("verify_key", "")))
        derived_key_id = learning_atom_key_id_from_verify_key(verify_key)
        if signature.get("algorithm") != "ed25519":
            raise ValueError("outcome receipt signature algorithm must be ed25519")
        if signature.get("key_id") != derived_key_id:
            raise ValueError("outcome receipt signature key_id does not match verify key")
        trusted_signers = (
            {str(key_id) for key_id in trusted_receipt_signer_key_ids if str(key_id).strip()}
            if trusted_receipt_signer_key_ids is not None
            else None
        )
        if trusted_signers is not None and str(signature.get("key_id") or "") not in trusted_signers:
            raise ValueError("outcome receipt signer key is not trusted")
        try:
            verify_key.verify(
                _canonical_json_bytes(payload),
                decode_key(str(signature.get("signature_b64url", "")), "signature"),
                encoder=encoding.RawEncoder,
            )
        except exceptions.BadSignatureError as exc:
            raise ValueError("outcome receipt signature mismatch") from exc
        tenant = str(payload.get("tenant_pseudonym") or "")
        if not is_valid_tenant_pseudonym(tenant):
            raise ValueError("outcome receipt tenant_pseudonym must be an HMAC pseudonym")
        if _as_bool(payload.get("verified")) and not _safe_text(payload.get("verification_command_redacted"), max_chars=800):
            raise ValueError("verified outcome receipt requires verification evidence")
        return payload
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"outcome receipt verification failed: {exc}") from exc


def _words(value: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(value or "") if len(w) > 1]


def _normalize_error_pattern(error_pattern: str) -> str:
    text = (error_pattern or "").lower()
    text = re.sub(r"['\"]", "", text)
    text = re.sub(r"\bno module named\b", "module_missing", text)
    text = re.sub(r"\bmodulenotfounderror\b", "modulenotfounderror", text)
    text = re.sub(r"[^a-z0-9_\.:-]+", " ", text)
    text = text.replace(":", " ")
    words = _words(text)
    stop = {"the", "and", "for", "with", "this", "that", "error", "exception"}
    useful = [w for w in words if w not in stop]
    return " ".join(useful[:12]) or "unknown"


def normalize_problem_signature(
    task_type: str = "",
    technology: Sequence[str] | str | None = None,
    error_class: str = "",
    error_pattern: str = "",
) -> str:
    """Return a stable dedupe/generalization key for a problem family.

    This is deliberately coarse enough to merge spelling/casing/punctuation
    duplicates, but still includes task type + tech + error class to avoid unsafe
    cross-domain generalization.
    """
    if isinstance(technology, str):
        tech_values = [technology]
    else:
        tech_values = list(technology or [])
    tech = "+".join(sorted({re.sub(r"[^a-z0-9_.-]+", "", str(t).lower()) for t in tech_values if str(t).strip()})) or "unknown"
    task = re.sub(r"[^a-z0-9_.-]+", "", str(task_type or "other").lower()) or "other"
    err_cls = re.sub(r"[^a-z0-9_.-]+", "", str(error_class or "unknown").lower()) or "unknown"
    pattern = _normalize_error_pattern(error_pattern)
    return "cluster-sha256:" + _sha256_text(f"{task}\n{tech}\n{err_cls}\n{pattern}")[:24]


def _task_fields_from_text(task_text: str, context: str = "") -> Dict[str, Any]:
    text = f"{task_text} {context}".lower()
    tech: List[str] = []
    for name in ["python", "node", "typescript", "rust", "docker", "django", "fastapi", "github-actions"]:
        if name in text:
            tech.append(name)
    error_class = "unknown"
    pattern_text = task_text or ""
    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)|ModuleNotFoundError|ImportError|SyntaxError)\b", task_text or "", re.I)
    if m:
        raw = m.group(1)
        canonical = {
            "modulenotfounderror": "ModuleNotFoundError",
            "importerror": "ImportError",
            "syntaxerror": "SyntaxError",
        }.get(raw.lower(), raw)
        error_class = canonical
        pattern_text = (task_text or "")[:m.start()] + " " + (task_text or "")[m.end():]
    return {
        "task_type": "debug" if error_class != "unknown" or "error" in text or "failed" in text else "general",
        "technology": tech or ["unknown"],
        "error_class": error_class,
        "error_pattern": _safe_text(pattern_text, max_chars=300),
    }


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else get_collective_learning_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interventions (
            intervention_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source_tool TEXT NOT NULL,
            task_text_redacted TEXT NOT NULL,
            context_redacted TEXT NOT NULL,
            task_type TEXT NOT NULL,
            technology_json TEXT NOT NULL,
            error_class TEXT NOT NULL,
            error_pattern TEXT NOT NULL,
            cluster_id TEXT NOT NULL,
            guidance_hash TEXT NOT NULL,
            guidance_redacted TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            tenant_pseudonym TEXT NOT NULL,
            session_id TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_interventions_cluster ON interventions(cluster_id);
        CREATE INDEX IF NOT EXISTS idx_interventions_source ON interventions(source_tool);

        CREATE TABLE IF NOT EXISTS outcome_receipts (
            receipt_id TEXT PRIMARY KEY,
            intervention_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            outcome TEXT NOT NULL,
            helpful INTEGER NOT NULL,
            verified INTEGER NOT NULL,
            verification_command_redacted TEXT NOT NULL,
            tenant_pseudonym TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            atom_id TEXT,
            cluster_id TEXT NOT NULL,
            time_saved_minutes REAL NOT NULL DEFAULT 0,
            tokens_saved INTEGER NOT NULL DEFAULT 0,
            dead_ends_avoided INTEGER NOT NULL DEFAULT 0,
            notes_redacted TEXT NOT NULL,
            receipt_nonce TEXT NOT NULL DEFAULT '',
            receipt_envelope_json TEXT NOT NULL DEFAULT '{}',
            receipt_signer_key_id TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(intervention_id) REFERENCES interventions(intervention_id)
        );
        CREATE INDEX IF NOT EXISTS idx_outcomes_intervention ON outcome_receipts(intervention_id);
        CREATE INDEX IF NOT EXISTS idx_outcomes_atom ON outcome_receipts(atom_id);
        CREATE INDEX IF NOT EXISTS idx_outcomes_cluster ON outcome_receipts(cluster_id);
        CREATE INDEX IF NOT EXISTS idx_outcomes_value ON outcome_receipts(verified, helpful, outcome);

        CREATE TABLE IF NOT EXISTS contribution_events (
            event_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            collective_stage TEXT NOT NULL,
            status TEXT NOT NULL,
            source_tool TEXT NOT NULL,
            intervention_id TEXT,
            receipt_id TEXT,
            atom_id TEXT,
            cluster_id TEXT,
            agent_id TEXT NOT NULL,
            tenant_pseudonym TEXT NOT NULL,
            session_id TEXT NOT NULL,
            task_text_redacted TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL,
            privacy_redaction_count INTEGER NOT NULL DEFAULT 0,
            prompt_injection_score REAL NOT NULL DEFAULT 0,
            prompt_injection_classes_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_contribution_events_type ON contribution_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_contribution_events_cluster ON contribution_events(cluster_id);
        CREATE INDEX IF NOT EXISTS idx_contribution_events_intervention ON contribution_events(intervention_id);
        CREATE INDEX IF NOT EXISTS idx_contribution_events_stage_status ON contribution_events(collective_stage, status);
        """
    )
    existing = {row[1] for row in conn.execute("PRAGMA table_info(outcome_receipts)").fetchall()}
    for column, ddl in {
        "receipt_nonce": "ALTER TABLE outcome_receipts ADD COLUMN receipt_nonce TEXT NOT NULL DEFAULT ''",
        "receipt_envelope_json": "ALTER TABLE outcome_receipts ADD COLUMN receipt_envelope_json TEXT NOT NULL DEFAULT '{}'",
        "receipt_signer_key_id": "ALTER TABLE outcome_receipts ADD COLUMN receipt_signer_key_id TEXT NOT NULL DEFAULT ''",
    }.items():
        if column not in existing:
            conn.execute(ddl)
    conn.commit()


class CollectiveLearningStore:
    """SQLite-backed intervention/outcome receipt store."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or get_collective_learning_db_path())
        self.signing_key_path = _outcome_key_path(self.db_path)

    def record_contribution_event(
        self,
        *,
        event_type: str,
        source_tool: str,
        collective_stage: str,
        status: str = "accepted",
        payload: Dict[str, Any] | None = None,
        intervention_id: str = "",
        receipt_id: str = "",
        atom_id: str = "",
        cluster_id: str = "",
        agent_id: str = "default",
        tenant_pseudonym: str = "local",
        session_id: str = "",
        task_text: str = "",
    ) -> Dict[str, Any]:
        """Append a privacy-safe event to the contribution ledger.

        This is the broad "every meaningful contribution" substrate.  Events are
        evidence plumbing only: promotion still requires signed verified outcome
        receipts, sanitization, quorum, registry policy, and revocation support.
        """
        created_at = _utc_now()
        redacted_payload = _redact_json_value(payload or {})
        summary = _privacy_prompt_summary(redacted_payload)
        tenant_id = _normalize_tenant_pseudonym(tenant_pseudonym)
        safe_event_type = _safe_text(event_type or "unknown", max_chars=120) or "unknown"
        safe_stage = _safe_text(collective_stage or "observed", max_chars=120) or "observed"
        safe_status = _safe_text(status or "accepted", max_chars=120) or "accepted"
        safe_source = _safe_text(source_tool or "unknown", max_chars=120) or "unknown"
        material = {
            "created_at": created_at,
            "event_nonce": secrets.token_hex(16),
            "event_type": safe_event_type,
            "source_tool": safe_source,
            "intervention_id": intervention_id,
            "receipt_id": receipt_id,
            "atom_id": atom_id,
            "cluster_id": cluster_id,
            "tenant_pseudonym": tenant_id,
        }
        row = {
            "event_id": _event_id(material),
            "created_at": created_at,
            "event_type": safe_event_type,
            "collective_stage": safe_stage,
            "status": safe_status,
            "source_tool": safe_source,
            "intervention_id": _safe_text(intervention_id, max_chars=160),
            "receipt_id": _safe_text(receipt_id, max_chars=160),
            "atom_id": _safe_text(atom_id, max_chars=160),
            "cluster_id": _safe_text(cluster_id, max_chars=160),
            "agent_id": _safe_text(agent_id, max_chars=160),
            "tenant_pseudonym": tenant_id,
            "session_id": _safe_text(session_id, max_chars=160),
            "task_text_redacted": _safe_text(task_text, max_chars=1000),
            "payload": redacted_payload,
            "privacy_redaction_count": int(summary["privacy_redaction_count"]),
            "prompt_injection_score": float(summary["prompt_injection_score"]),
            "prompt_injection_classes": list(summary["prompt_injection_classes"]),
        }
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contribution_events
                (event_id, created_at, event_type, collective_stage, status, source_tool,
                 intervention_id, receipt_id, atom_id, cluster_id, agent_id, tenant_pseudonym,
                 session_id, task_text_redacted, payload_json, privacy_redaction_count,
                 prompt_injection_score, prompt_injection_classes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["event_id"], row["created_at"], row["event_type"], row["collective_stage"], row["status"], row["source_tool"],
                    row["intervention_id"], row["receipt_id"], row["atom_id"], row["cluster_id"], row["agent_id"], row["tenant_pseudonym"],
                    row["session_id"], row["task_text_redacted"], _canonical_json(row["payload"]), row["privacy_redaction_count"],
                    row["prompt_injection_score"], _canonical_json(row["prompt_injection_classes"]),
                ),
            )
            conn.commit()
        return row

    def recent_contribution_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 50), 500))
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM contribution_events ORDER BY created_at DESC, event_id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        events: List[Dict[str, Any]] = []
        for row in rows:
            item = {key: row[key] for key in row.keys() if key not in {"payload_json", "prompt_injection_classes_json"}}
            try:
                item["payload"] = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                item["payload"] = {}
            try:
                item["prompt_injection_classes"] = json.loads(row["prompt_injection_classes_json"] or "[]")
            except json.JSONDecodeError:
                item["prompt_injection_classes"] = []
            events.append(item)
        return events

    def contribution_summary(self) -> Dict[str, Any]:
        with _connect(self.db_path) as conn:
            total = int(conn.execute("SELECT COUNT(*) FROM contribution_events").fetchone()[0] or 0)
            by_type = {str(row["event_type"]): int(row["count"] or 0) for row in conn.execute("SELECT event_type, COUNT(*) AS count FROM contribution_events GROUP BY event_type")}
            by_stage = {str(row["collective_stage"]): int(row["count"] or 0) for row in conn.execute("SELECT collective_stage, COUNT(*) AS count FROM contribution_events GROUP BY collective_stage")}
            promotion_ready = conn.execute(
                """
                SELECT cluster_id, COUNT(DISTINCT tenant_pseudonym) AS tenants
                FROM outcome_receipts
                WHERE verified = 1 AND helpful = 1 AND outcome IN ('success','partial')
                GROUP BY cluster_id
                HAVING tenants >= 3
                ORDER BY tenants DESC, cluster_id
                """
            ).fetchall()
        return {
            "schema_version": 1,
            "total_events": total,
            "by_type": by_type,
            "by_stage": by_stage,
            "promotion_ready_clusters": [
                {"cluster_id": str(row["cluster_id"]), "helpful_verified_tenants": int(row["tenants"] or 0)}
                for row in promotion_ready
            ],
            "external_lift_status": "NO-GO_REAL_FIRST_10_ROWS_REQUIRED",
        }

    def record_intervention(
        self,
        *,
        source_tool: str,
        task_text: str,
        context: str = "",
        guidance: Any = "",
        agent_id: str = "default",
        tenant_pseudonym: str = "local",
        session_id: str = "",
        source_refs: Sequence[str] | None = None,
        task_type: str | None = None,
        technology: Sequence[str] | str | None = None,
        error_class: str | None = None,
        error_pattern: str | None = None,
    ) -> Dict[str, Any]:
        fields = _task_fields_from_text(task_text, context)
        task_type = task_type or fields["task_type"]
        technology = technology if technology is not None else fields["technology"]
        if isinstance(technology, str):
            technology_values = [technology]
        else:
            technology_values = list(technology or [])
        error_class = error_class or fields["error_class"]
        error_pattern = error_pattern or fields["error_pattern"]
        cluster_id = normalize_problem_signature(str(task_type or "other"), technology_values, str(error_class or "unknown"), str(error_pattern or ""))
        guidance_redacted = _safe_text(guidance if isinstance(guidance, str) else _canonical_json(guidance), max_chars=2200)
        source_refs_values = [str(ref) for ref in (source_refs or []) if str(ref).strip()]
        tenant_id = _normalize_tenant_pseudonym(tenant_pseudonym)
        created_at = _utc_now()
        material = {
            "created_at": created_at,
            "event_nonce": secrets.token_hex(16),
            "source_tool": source_tool,
            "cluster_id": cluster_id,
            "guidance_hash": _sha256_text(guidance_redacted),
            "agent_id": agent_id,
            "tenant_pseudonym": tenant_id,
            "session_id": session_id,
        }
        intervention_id = _intervention_id(material)
        row = {
            "intervention_id": intervention_id,
            "created_at": created_at,
            "source_tool": source_tool,
            "task_text_redacted": _safe_text(task_text, max_chars=1000),
            "context_redacted": _safe_text(context, max_chars=500),
            "task_type": task_type,
            "technology": technology_values,
            "error_class": error_class,
            "error_pattern": _safe_text(error_pattern, max_chars=500),
            "cluster_id": cluster_id,
            "guidance_hash": _sha256_text(guidance_redacted),
            "guidance_redacted": guidance_redacted,
            "source_refs": source_refs_values,
            "agent_id": _safe_text(agent_id, max_chars=160),
            "tenant_pseudonym": tenant_id,
            "session_id": _safe_text(session_id, max_chars=160),
        }
        with _connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO interventions
                (intervention_id, created_at, source_tool, task_text_redacted, context_redacted,
                 task_type, technology_json, error_class, error_pattern, cluster_id, guidance_hash,
                 guidance_redacted, source_refs_json, agent_id, tenant_pseudonym, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["intervention_id"], row["created_at"], row["source_tool"], row["task_text_redacted"], row["context_redacted"],
                    row["task_type"], _canonical_json(row["technology"]), row["error_class"], row["error_pattern"], row["cluster_id"], row["guidance_hash"],
                    row["guidance_redacted"], _canonical_json(row["source_refs"]), row["agent_id"], row["tenant_pseudonym"], row["session_id"],
                ),
            )
            conn.commit()
        event = self.record_contribution_event(
            event_type="intervention",
            source_tool=str(source_tool or "unknown"),
            collective_stage="observed",
            status="accepted",
            intervention_id=row["intervention_id"],
            cluster_id=row["cluster_id"],
            agent_id=row["agent_id"],
            tenant_pseudonym=row["tenant_pseudonym"],
            session_id=row["session_id"],
            task_text=row["task_text_redacted"],
            payload={
                "intervention_id": row["intervention_id"],
                "task_type": row["task_type"],
                "technology": row["technology"],
                "error_class": row["error_class"],
                "error_pattern": row["error_pattern"],
                "guidance_hash": row["guidance_hash"],
                "source_refs": row["source_refs"],
            },
        )
        row["contribution_event_id"] = event["event_id"]
        return row

    def record_outcome(
        self,
        *,
        intervention_id: str,
        outcome: str,
        helpful: Any,
        verified: Any,
        verification_command: str = "",
        tenant_pseudonym: str = "local",
        agent_id: str = "default",
        atom_id: str | None = None,
        cluster_id: str | None = None,
        time_saved_minutes: float = 0.0,
        tokens_saved: int = 0,
        dead_ends_avoided: int = 0,
        notes: str = "",
    ) -> Dict[str, Any]:
        outcome_norm = str(outcome or "unknown").strip().lower()
        if outcome_norm not in {"success", "failure", "partial", "unknown"}:
            raise ValueError("outcome must be success/failure/partial/unknown")
        helpful_bool = _as_bool(helpful)
        verified_bool = _as_bool(verified)
        verification_redacted = _safe_text(verification_command, max_chars=800)
        if verified_bool and not verification_redacted:
            raise ValueError("verification_command is required when verified=True")
        with _connect(self.db_path) as conn:
            intervention = conn.execute(
                "SELECT cluster_id, tenant_pseudonym, agent_id, source_refs_json FROM interventions WHERE intervention_id = ?",
                (intervention_id,),
            ).fetchone()
            if intervention is None:
                raise ValueError("intervention_id not found")
            intervention_cluster = str(intervention["cluster_id"])
            requested_cluster = str(cluster_id or "")
            if requested_cluster and requested_cluster != intervention_cluster:
                raise ValueError("outcome cluster must match intervention cluster")
            resolved_cluster = intervention_cluster
            intervention_tenant = str(intervention["tenant_pseudonym"])
            requested_tenant = _normalize_tenant_pseudonym(tenant_pseudonym or intervention_tenant)
            if requested_tenant != intervention_tenant:
                raise ValueError("outcome tenant must match intervention tenant")
            resolved_tenant = intervention_tenant
            resolved_agent = _safe_text(agent_id or intervention["agent_id"], max_chars=160)
            resolved_atom_id = _safe_text(atom_id, max_chars=160) if atom_id else ""
            if resolved_atom_id:
                try:
                    source_refs_raw = json.loads(str(intervention["source_refs_json"] or "[]"))
                except (TypeError, json.JSONDecodeError):
                    source_refs_raw = []
                allowed_atom_ids = {str(ref) for ref in source_refs_raw if str(ref).strip()}
                if resolved_atom_id not in allowed_atom_ids:
                    raise ValueError("outcome atom_id must match intervention source_refs")
            created_at = _utc_now()
            receipt_nonce = secrets.token_hex(16)
            row = {
                "receipt_id": "",
                "intervention_id": intervention_id,
                "created_at": created_at,
                "receipt_nonce": receipt_nonce,
                "outcome": outcome_norm,
                "helpful": helpful_bool,
                "verified": verified_bool,
                "verification_command_redacted": verification_redacted,
                "tenant_pseudonym": resolved_tenant,
                "agent_id": resolved_agent,
                "atom_id": resolved_atom_id or None,
                "cluster_id": resolved_cluster,
                "time_saved_minutes": float(time_saved_minutes or 0.0),
                "tokens_saved": int(tokens_saved or 0),
                "dead_ends_avoided": int(dead_ends_avoided or 0),
                "notes_redacted": _safe_text(notes, max_chars=1000),
            }
            row["receipt_id"] = _receipt_id(_outcome_receipt_material(row))
            envelope = sign_outcome_receipt_payload(row, _load_or_create_outcome_signing_key(self.signing_key_path))
            row["receipt_id"] = envelope["payload"]["receipt_id"]
            row["receipt_envelope"] = envelope
            row["receipt_signer_key_id"] = envelope["signature"]["key_id"]
            conn.execute(
                """
                INSERT OR REPLACE INTO outcome_receipts
                (receipt_id, intervention_id, created_at, outcome, helpful, verified,
                 verification_command_redacted, tenant_pseudonym, agent_id, atom_id, cluster_id,
                 time_saved_minutes, tokens_saved, dead_ends_avoided, notes_redacted,
                 receipt_nonce, receipt_envelope_json, receipt_signer_key_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["receipt_id"], row["intervention_id"], row["created_at"], row["outcome"], int(row["helpful"]), int(row["verified"]),
                    row["verification_command_redacted"], row["tenant_pseudonym"], row["agent_id"], row["atom_id"], row["cluster_id"],
                    row["time_saved_minutes"], row["tokens_saved"], row["dead_ends_avoided"], row["notes_redacted"],
                    row["receipt_nonce"], _canonical_json(envelope), row["receipt_signer_key_id"],
                ),
            )
            conn.commit()
        event = self.record_contribution_event(
            event_type="outcome_receipt",
            source_tool="borg_record_outcome",
            collective_stage="verified_outcome" if row["verified"] else "unverified_outcome",
            status="accepted" if row["verified"] else "telemetry_only",
            intervention_id=row["intervention_id"],
            receipt_id=row["receipt_id"],
            atom_id=row["atom_id"] or "",
            cluster_id=row["cluster_id"],
            agent_id=row["agent_id"],
            tenant_pseudonym=row["tenant_pseudonym"],
            task_text=row["notes_redacted"],
            payload={
                "receipt_id": row["receipt_id"],
                "outcome": row["outcome"],
                "helpful": row["helpful"],
                "verified": row["verified"],
                "verification_command_redacted": row["verification_command_redacted"],
                "time_saved_minutes": row["time_saved_minutes"],
                "tokens_saved": row["tokens_saved"],
                "dead_ends_avoided": row["dead_ends_avoided"],
                "receipt_signer_key_id": row["receipt_signer_key_id"],
            },
        )
        row["contribution_event_id"] = event["event_id"]
        return row

    def cluster_stats(self, cluster_id: str) -> Dict[str, Any]:
        with _connect(self.db_path) as conn:
            interventions = conn.execute("SELECT COUNT(*) FROM interventions WHERE cluster_id = ?", (cluster_id,)).fetchone()[0]
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS outcomes,
                    SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified_outcomes,
                    SUM(CASE WHEN verified = 1 AND helpful = 1 AND outcome IN ('success','partial') THEN 1 ELSE 0 END) AS helpful_outcomes,
                    SUM(CASE WHEN verified = 1 AND (helpful = 0 OR outcome = 'failure') THEN 1 ELSE 0 END) AS unhelpful_outcomes,
                    COUNT(DISTINCT CASE WHEN verified = 1 THEN tenant_pseudonym END) AS distinct_tenants,
                    SUM(time_saved_minutes) AS total_minutes_saved,
                    SUM(tokens_saved) AS total_tokens_saved,
                    SUM(dead_ends_avoided) AS dead_ends_avoided
                FROM outcome_receipts WHERE cluster_id = ?
                """,
                (cluster_id,),
            ).fetchone()
        verified = int(row["verified_outcomes"] or 0)
        helpful = int(row["helpful_outcomes"] or 0)
        unhelpful = int(row["unhelpful_outcomes"] or 0)
        # Conservative Beta(1,1) posterior mean. One success is promising, not proof.
        helpfulness_score = (helpful + 1.0) / (helpful + unhelpful + 2.0)
        return {
            "cluster_id": cluster_id,
            "dedupe_key": cluster_id,
            "interventions": int(interventions or 0),
            "outcomes": int(row["outcomes"] or 0),
            "verified_outcomes": verified,
            "helpful_outcomes": helpful,
            "unhelpful_outcomes": unhelpful,
            "distinct_tenants": int(row["distinct_tenants"] or 0),
            "total_minutes_saved": float(row["total_minutes_saved"] or 0.0),
            "total_tokens_saved": int(row["total_tokens_saved"] or 0),
            "dead_ends_avoided": int(row["dead_ends_avoided"] or 0),
            "helpfulness_score": round(helpfulness_score, 6),
        }

    def atom_outcome_stats(self, atom_id: str) -> Dict[str, Any]:
        with _connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS outcomes,
                    SUM(CASE WHEN verified = 1 THEN 1 ELSE 0 END) AS verified_outcomes,
                    SUM(CASE WHEN verified = 1 AND helpful = 1 AND outcome IN ('success','partial') THEN 1 ELSE 0 END) AS helpful_outcomes,
                    SUM(CASE WHEN verified = 1 AND (helpful = 0 OR outcome = 'failure') THEN 1 ELSE 0 END) AS unhelpful_outcomes,
                    COUNT(DISTINCT CASE WHEN verified = 1 AND helpful = 1 AND outcome IN ('success','partial') THEN tenant_pseudonym END) AS helpful_tenants
                FROM outcome_receipts WHERE atom_id = ?
                """,
                (atom_id,),
            ).fetchone()
        helpful = int(row["helpful_outcomes"] or 0)
        unhelpful = int(row["unhelpful_outcomes"] or 0)
        return {
            "atom_id": atom_id,
            "outcomes": int(row["outcomes"] or 0),
            "verified_outcomes": int(row["verified_outcomes"] or 0),
            "helpful_outcomes": helpful,
            "unhelpful_outcomes": unhelpful,
            "helpful_tenants": int(row["helpful_tenants"] or 0),
            "helpfulness_score": round((helpful + 1.0) / (helpful + unhelpful + 2.0), 6),
        }

    def export_verified_outcomes(self, registry_dir: str | Path) -> Dict[str, Any]:
        root = Path(registry_dir)
        out_dir = root / "outcomes"
        out_dir.mkdir(parents=True, exist_ok=True)
        exported = 0
        signer_key_ids: set[str] = set()
        with _connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM outcome_receipts WHERE verified = 1 ORDER BY created_at, receipt_id").fetchall()
        for row in rows:
            try:
                envelope = json.loads(str(row["receipt_envelope_json"] or "{}"))
                verify_outcome_receipt_envelope(envelope)
            except (KeyError, TypeError, json.JSONDecodeError, ValueError):
                # Unsigned legacy rows are intentionally not shareable evidence.
                continue
            signer_key_id = str((envelope.get("signature") or {}).get("key_id") or "")
            if signer_key_id:
                signer_key_ids.add(signer_key_id)
            path = out_dir / (str(row["receipt_id"]).replace(":", "_") + ".json")
            tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
            tmp.write_text(json.dumps(envelope, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            tmp.replace(path)
            exported += 1
        return {
            "exported": exported,
            "path": str(out_dir),
            # Trust anchors are returned by the local exporting store and must be
            # passed explicitly to registry-quorum computation.  Receipt files are
            # self-signed integrity envelopes; the registry must not infer signer
            # trust from files an attacker can place in `outcomes/`.
            "trusted_receipt_signer_key_ids": sorted(signer_key_ids),
        }

    def recent_value_summary(self) -> Dict[str, Any]:
        with _connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS interventions,
                    (SELECT COUNT(*) FROM outcome_receipts) AS outcomes,
                    (SELECT COUNT(*) FROM outcome_receipts WHERE verified = 1) AS verified_outcomes,
                    (SELECT COUNT(*) FROM outcome_receipts WHERE verified = 1 AND helpful = 1 AND outcome IN ('success','partial')) AS helpful_outcomes,
                    (SELECT COUNT(DISTINCT tenant_pseudonym) FROM outcome_receipts WHERE verified = 1 AND helpful = 1 AND outcome IN ('success','partial')) AS helpful_tenants,
                    (SELECT COALESCE(SUM(time_saved_minutes), 0) FROM outcome_receipts WHERE verified = 1 AND helpful = 1) AS minutes_saved,
                    (SELECT COALESCE(SUM(tokens_saved), 0) FROM outcome_receipts WHERE verified = 1 AND helpful = 1) AS tokens_saved
                FROM interventions
                """
            ).fetchone()
        return {key: row[key] for key in row.keys()}

    def build_learning_atom_candidate(
        self,
        cluster_id: str,
        *,
        scope: str = "global_candidate",
        min_helpful_tenants: int = 3,
    ) -> Dict[str, Any]:
        """Distill verified outcome receipts in one cluster into a sanitized atom.

        The candidate is allowed to be blocked.  Blocked candidates still enter
        the contribution ledger as evidence of why the cluster is not shareable.
        """
        scope_norm = scope if scope in {"org", "global_candidate", "global"} else "global_candidate"
        min_tenants = max(1, int(min_helpful_tenants or 1))
        with _connect(self.db_path) as conn:
            interventions = conn.execute(
                "SELECT * FROM interventions WHERE cluster_id = ? ORDER BY created_at, intervention_id",
                (cluster_id,),
            ).fetchall()
            outcomes = conn.execute(
                """
                SELECT o.*, i.guidance_redacted, i.task_type, i.technology_json, i.error_class, i.error_pattern, i.task_text_redacted
                FROM outcome_receipts o
                JOIN interventions i ON i.intervention_id = o.intervention_id
                WHERE o.cluster_id = ?
                ORDER BY o.created_at, o.receipt_id
                """,
                (cluster_id,),
            ).fetchall()
        if not interventions:
            raise ValueError("cluster_id not found")

        helpful_rows = [row for row in outcomes if int(row["verified"] or 0) == 1 and int(row["helpful"] or 0) == 1 and str(row["outcome"]).lower() in {"success", "partial"}]
        unhelpful_rows = [row for row in outcomes if int(row["verified"] or 0) == 1 and (int(row["helpful"] or 0) == 0 or str(row["outcome"]).lower() == "failure")]
        helpful_tenants = sorted({str(row["tenant_pseudonym"]) for row in helpful_rows if is_valid_tenant_pseudonym(str(row["tenant_pseudonym"]))})
        blockers: List[str] = []
        if not helpful_rows:
            blockers.append("no verified helpful outcomes")
        if len(helpful_tenants) < min_tenants:
            blockers.append(f"verified helpful tenant quorum {len(helpful_tenants)}/{min_tenants}")

        tech_counter: Counter[str] = Counter()
        error_classes: Counter[str] = Counter()
        error_patterns: Counter[str] = Counter()
        task_types: Counter[str] = Counter()
        for row in interventions:
            try:
                tech_values = json.loads(str(row["technology_json"] or "[]"))
            except json.JSONDecodeError:
                tech_values = []
            for tech in tech_values or ["unknown"]:
                tech_counter[_safe_text(tech, max_chars=80).lower() or "unknown"] += 1
            error_classes[_safe_text(row["error_class"], max_chars=120) or "unknown"] += 1
            error_patterns[_safe_text(row["error_pattern"], max_chars=300) or "unknown"] += 1
            task_types[_safe_text(row["task_type"], max_chars=80) or "debug"] += 1

        exemplar = helpful_rows[0] if helpful_rows else outcomes[0] if outcomes else interventions[0]
        raw_worked = str(exemplar["guidance_redacted"] if "guidance_redacted" in exemplar.keys() else exemplar["task_text_redacted"])
        worked = neutralize_for_retrieval(_safe_text(raw_worked, max_chars=900))
        if not worked:
            worked = "Use the verified cluster approach only after reproducing the failure and running the verification command."
        avoid_values: List[str] = []
        for row in unhelpful_rows[:5]:
            cleaned = neutralize_for_retrieval(_safe_text(row["guidance_redacted"], max_chars=350))
            if cleaned and cleaned not in avoid_values:
                avoid_values.append(cleaned)
        if not avoid_values:
            avoid_values = ["Do not repeat an unverified fix without rerunning the smallest failing command or regression test."]
        why = (
            f"Derived from {len(helpful_rows)} verified helpful outcome receipt(s) "
            f"across {len(helpful_tenants)} tenant pseudonym(s); "
            f"{len(unhelpful_rows)} verified negative receipt(s) retained for scoring."
        )
        technology = [item for item, _ in tech_counter.most_common(5)] or ["unknown"]
        error_class = error_classes.most_common(1)[0][0]
        error_pattern = error_patterns.most_common(1)[0][0]
        task_type = task_types.most_common(1)[0][0]
        privacy_input = {"worked": worked, "avoid": avoid_values, "why": why, "error_pattern": error_pattern}
        privacy = privacy_risk_score(privacy_input)
        injection = scan_prompt_injection(" ".join([worked, why, " ".join(avoid_values)]))
        if getattr(privacy, "blocked", False):
            blockers.append("privacy risk blocks atom candidate")
        if injection.blocked:
            blockers.append("prompt injection risk blocks atom candidate")
        promotable = not blockers
        atom = {
            "schema_version": "1.0",
            "scope": scope_norm,
            "task": {
                "type": task_type if task_type in {"debug", "test", "install", "deploy", "review", "config", "other"} else "debug",
                "technology": technology,
                "error_class": error_class,
                "error_pattern": error_pattern,
                "difficulty": "unknown",
            },
            "learning": {
                "root_cause_class": error_class,
                "worked": worked,
                "avoid": avoid_values,
                "why": why,
            },
            "evidence": {
                "type": "outcome_receipt",
                "strength": "verified_quorum" if promotable else "insufficient_quorum",
                "support_count": len(helpful_rows),
                "negative_count": len(unhelpful_rows),
                "cluster_id": cluster_id,
                "supporting_receipt_ids": [str(row["receipt_id"]) for row in helpful_rows[:20]],
            },
            "privacy": {
                "risk_score": getattr(privacy, "risk_score", 0),
                "scanner_version": "privacy-v1",
                "finding_classes": sorted({finding.kind for finding in getattr(privacy, "findings", [])}),
                "redaction_count": len(getattr(privacy, "findings", [])),
                "raw_trace_retained": False,
            },
            "safety": {
                "prompt_injection_score": injection.score,
                "injection_classes": sorted({finding.kind for finding in injection.findings}),
                "imperative_text_removed": True,
                "retrieval_treatment": "untrusted_advisory",
            },
            "trust": {
                "submitter_key_id": "",
                "tenant_pseudonym": helpful_tenants[0] if helpful_tenants else str(interventions[0]["tenant_pseudonym"]),
                "agent_reputation_at_submit": 0,
                "independent_tenant_count": len(helpful_tenants),
                "verified_tenant_count": len(helpful_tenants),
                "promotion_score": round(min(len(helpful_tenants) / max(min_tenants, 1), 1.0), 6),
            },
            "lifecycle": {
                "status": ("global_candidate" if scope_norm == "global_candidate" else "org_safe" if scope_norm == "org" else "published") if promotable else "draft",
                "created_at_day": _utc_now()[:10],
                "expires_at_day": None,
                "revoked_at": None,
                "revocation_reason": None,
            },
        }
        atom["atom_id"] = compute_atom_id(atom)
        validation = validate_learning_atom(atom)
        if not validation.valid:
            blockers.extend(validation.errors)
            promotable = False
        event = self.record_contribution_event(
            event_type="learning_atom_candidate",
            source_tool="collective_learning.build_learning_atom_candidate",
            collective_stage="sanitized_candidate",
            status="promotable" if promotable else "blocked",
            atom_id=atom["atom_id"],
            cluster_id=cluster_id,
            tenant_pseudonym=(helpful_tenants[0] if helpful_tenants else str(interventions[0]["tenant_pseudonym"])),
            payload={"atom_id": atom["atom_id"], "promotable": promotable, "blockers": blockers, "support_count": len(helpful_rows), "helpful_tenants": len(helpful_tenants)},
        )
        return {
            "success": True,
            "promotable": promotable,
            "blockers": sorted(set(blockers)),
            "atom": atom,
            "atom_id": atom["atom_id"],
            "cluster_id": cluster_id,
            "helpful_verified_tenants": len(helpful_tenants),
            "supporting_receipt_ids": [str(row["receipt_id"]) for row in helpful_rows],
            "negative_receipt_ids": [str(row["receipt_id"]) for row in unhelpful_rows],
            "validation_errors": validation.errors,
            "contribution_event_id": event["event_id"],
            "external_lift_status": "NO-GO_REAL_FIRST_10_ROWS_REQUIRED",
        }

    def promote_cluster_to_registry(
        self,
        cluster_id: str,
        registry_dir: str | Path,
        signing_key: Any,
        *,
        scope: str = "global_candidate",
        min_helpful_tenants: int = 3,
    ) -> Dict[str, Any]:
        """Build, sign, and stage a cluster-derived atom in a registry."""
        candidate = self.build_learning_atom_candidate(cluster_id, scope=scope, min_helpful_tenants=min_helpful_tenants)
        if not candidate["promotable"]:
            raise ValueError("cluster is not promotable: " + "; ".join(candidate["blockers"]))
        exported = self.export_verified_outcomes(registry_dir)
        envelope = sign_learning_atom(candidate["atom"], signing_key)
        from borg.core.atom_registry import ingest_atom_envelope, rebuild_manifest

        receipt = ingest_atom_envelope(
            envelope,
            registry_dir,
            trusted_receipt_signer_key_ids=exported.get("trusted_receipt_signer_key_ids", []),
            allow_cluster_receipt_rebind=True,
            trusted_cluster_rebind_atom_id=envelope["payload"]["atom_id"],
        )
        manifest = rebuild_manifest(registry_dir)
        event = self.record_contribution_event(
            event_type="registry_promotion",
            source_tool="collective_learning.promote_cluster_to_registry",
            collective_stage="registry_staged",
            status=receipt.decision,
            receipt_id=receipt.receipt_id,
            atom_id=receipt.atom_id,
            cluster_id=cluster_id,
            tenant_pseudonym=(candidate["atom"].get("trust") or {}).get("tenant_pseudonym", "local"),
            payload={
                "registry_receipt_id": receipt.receipt_id,
                "decision": receipt.decision,
                "verified_tenant_count": receipt.verified_tenant_count,
                "exported_outcome_receipts": exported["exported"],
                "manifest_atoms": manifest.get("atoms", []),
            },
        )
        return {
            "success": True,
            "candidate": candidate,
            "envelope": envelope,
            "registry_receipt": {
                "receipt_id": receipt.receipt_id,
                "atom_id": receipt.atom_id,
                "decision": receipt.decision,
                "reason": receipt.reason,
                "verified_tenant_count": receipt.verified_tenant_count,
                "path": receipt.path,
            },
            "exported_outcomes": exported,
            "manifest": manifest,
            "contribution_event_id": event["event_id"],
            "external_lift_status": "NO-GO_REAL_FIRST_10_ROWS_REQUIRED",
        }


def _iter_outcome_files(
    registry_dir: str | Path,
    *,
    trusted_receipt_signer_key_ids: Sequence[str],
) -> Iterable[Dict[str, Any]]:
    for path in sorted((Path(registry_dir) / "outcomes").glob("*.json")):
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            yield verify_outcome_receipt_envelope(
                envelope,
                trusted_receipt_signer_key_ids=trusted_receipt_signer_key_ids,
            )
        except (OSError, json.JSONDecodeError, ValueError):
            continue


def compute_verified_tenant_count_from_outcomes(
    registry_dir: str | Path,
    *,
    atom_id: str | None = None,
    cluster_id: str | None = None,
    supporting_receipt_ids: Sequence[str] | None = None,
    allow_supported_receipt_rebind: bool = False,
    trusted_receipt_signer_key_ids: Sequence[str] | None = None,
) -> int:
    """Compute independent helpful tenant quorum from signed outcome receipts.

    The default path is intentionally strict: receipt files are self-signed
    integrity envelopes, not trust anchors.  Callers must pass trusted receipt
    signer key IDs obtained from trusted local/operator state; otherwise quorum
    computes to zero.  If an exported receipt carries an atom_id, it only
    supports that exact atom.  Cluster-derived atoms are minted after the
    underlying outcomes exist, so a trusted promotion path may enable
    `allow_supported_receipt_rebind` with an explicit receipt-id allowlist.  Even
    then, the count is still registry-computed from verified receipt envelopes;
    caller-supplied tenant counts and unlisted same-cluster receipts are ignored.
    """
    tenants: set[str] = set()
    trusted_signers = {str(key_id) for key_id in (trusted_receipt_signer_key_ids or []) if str(key_id).strip()}
    if not trusted_signers:
        return 0
    supporting_ids: set[str] | None = None
    if supporting_receipt_ids is not None:
        supporting_ids = {str(rid) for rid in supporting_receipt_ids if str(rid).strip()}
    for receipt in _iter_outcome_files(registry_dir, trusted_receipt_signer_key_ids=sorted(trusted_signers)):
        receipt_id = str(receipt.get("receipt_id") or "")
        if supporting_ids is not None and receipt_id not in supporting_ids:
            continue
        receipt_atom_id = str(receipt.get("atom_id") or "")
        # Direct candidate promotion is strict: receipts must target the exact
        # candidate atom. Cluster-level or source-atom receipts can support a new
        # distilled atom only when the trusted local promotion path supplies their
        # explicit signed receipt IDs as lineage evidence.
        if atom_id:
            exact_atom_receipt = receipt_atom_id == atom_id
            supported_rebind = bool(
                allow_supported_receipt_rebind
                and supporting_ids is not None
                and receipt_id in supporting_ids
            )
            if not exact_atom_receipt and not supported_rebind:
                continue
        if cluster_id and receipt.get("cluster_id") != cluster_id:
            continue
        if not _as_bool(receipt.get("verified")):
            continue
        if not _as_bool(receipt.get("helpful")):
            continue
        if str(receipt.get("outcome") or "").lower() not in {"success", "partial"}:
            continue
        tenant = _safe_text(receipt.get("tenant_pseudonym"), max_chars=160)
        if tenant and is_valid_tenant_pseudonym(tenant):
            tenants.add(tenant)
    return len(tenants)


def _query_terms(query: str) -> set[str]:
    return {w for w in _words(query) if w not in {"error", "exception", "failed", "failure", "with", "the", "and"}}


def _text_score(query: str, atom: Dict[str, Any]) -> float:
    terms = _query_terms(query)
    if not terms:
        return 0.0
    task = atom.get("task") or {}
    learning = atom.get("learning") or {}
    haystack = " ".join([
        str(task.get("error_class", "")),
        str(task.get("error_pattern", "")),
        str(learning.get("root_cause_class", "")),
        str(learning.get("worked", "")),
        " ".join(str(t) for t in task.get("technology", [])),
    ]).lower()
    hay = set(_words(haystack))
    return len(terms & hay) / max(len(terms), 1)


def _verified_tenant_count_from_trust(trust: Dict[str, Any]) -> int:
    """Return registry/store-verified tenant count without trusting payload hints.

    `independent_tenant_count` inside an atom payload is advisory metadata.  Only
    `verified_tenant_count` injected by the store/registry path may contribute to
    unified retrieval quorum scoring, and a legitimate zero must stay zero.
    """
    raw = trust.get("verified_tenant_count")
    if raw is None:
        return 0
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        return 0


def unified_collective_retrieve(
    query: str,
    *,
    atom_store: AtomStore | None = None,
    outcome_store: CollectiveLearningStore | None = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return one scored ranking across atom memory plus outcome receipts.

    Today this unifies learning atoms and outcome receipts.  It is intentionally
    extensible: packs/traces/failure-memory can be added as additional sources
    behind the same score contract without changing callers.
    """
    atom_store = atom_store or AtomStore()
    outcome_store = outcome_store or CollectiveLearningStore()
    candidates_by_id: Dict[str, Dict[str, Any]] = {}
    for probe in [query, *_query_terms(query)]:
        if not str(probe).strip():
            continue
        for atom in atom_store.search_atoms(str(probe), limit=max(limit * 4, 20)):
            atom_id_key = str(atom.get("atom_id") or _sha256_text(_canonical_json(atom)))
            candidates_by_id[atom_id_key] = atom
    candidates = list(candidates_by_id.values())
    ranked: List[Dict[str, Any]] = []
    for atom in candidates:
        atom_id = atom.get("atom_id", "")
        task = atom.get("task") or {}
        trust = atom.get("trust") or {}
        cluster_id = normalize_problem_signature(
            task.get("type", "other"),
            task.get("technology", []),
            task.get("error_class", ""),
            task.get("error_pattern", ""),
        )
        text = _text_score(query, atom)
        verified_tenant_count = _verified_tenant_count_from_trust(trust)
        stats = outcome_store.atom_outcome_stats(atom_id) if atom_id else {
            "helpfulness_score": 0.5,
            "helpful_outcomes": 0,
            "unhelpful_outcomes": 0,
        }
        if int(stats.get("helpful_outcomes", 0) or 0) == 0 and int(stats.get("unhelpful_outcomes", 0) or 0) == 0:
            evidence = atom.get("evidence") or {}
            can_use_cluster_evidence = (
                verified_tenant_count > 0
                and evidence.get("type") == "outcome_receipt"
                and str(evidence.get("cluster_id") or "") == cluster_id
            )
            if can_use_cluster_evidence:
                cluster_stats = outcome_store.cluster_stats(cluster_id)
                if int(cluster_stats.get("interventions", 0) or 0) > 0:
                    stats = cluster_stats
        quorum = min(float(verified_tenant_count), 5.0) / 5.0
        helpfulness = float(stats.get("helpfulness_score", 0.5))
        score = (0.45 * text) + (0.30 * helpfulness) + (0.20 * quorum) + (0.05 if atom_id else 0.0)
        reasons = []
        if text > 0:
            reasons.append("text_match")
        if quorum >= 0.6:
            reasons.append("verified_quorum")
        if int(stats.get("helpful_outcomes", 0) or 0) > 0:
            reasons.append("helpful_outcomes")
        if int(stats.get("unhelpful_outcomes", 0) or 0) > 0:
            reasons.append("negative_evidence_present")
        ranked.append({
            "source": "learning_atom",
            "atom_id": atom_id,
            "cluster_id": cluster_id,
            "score": round(score, 6),
            "score_reasons": reasons,
            "verified_tenant_count": verified_tenant_count,
            "helpfulness_score": helpfulness,
            "helpful_outcomes": int(stats.get("helpful_outcomes", 0) or 0),
            "unhelpful_outcomes": int(stats.get("unhelpful_outcomes", 0) or 0),
            "atom": atom,
        })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]
