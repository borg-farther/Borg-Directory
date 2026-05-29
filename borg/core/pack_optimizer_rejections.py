"""Persistent rejected-edit memory for Borg's local pack optimizer.

Rejected candidate edits are negative evidence.  Keeping them in a small local
JSONL ledger prevents the optimizer from re-proposing the same bad move across
runs without injecting hidden state into runtime prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

from borg.core.dirs import get_borg_home

_SECRETISH_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{16,}|xox[baprs]-[a-z0-9-]{16,}|"
    r"akia[0-9a-z]{16}|password\s*=\s*\S+|api[_-]?key\s*=\s*\S+|token\s*=\s*\S+)"
)
_SAFE_PACK_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,120}$", re.I)
_SAFE_OP_RE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,120}$", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256_ref(value: Any) -> str:
    return "rejected-edit-sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8", "ignore")).hexdigest()


def _safe_text(value: Any, max_chars: int = 400) -> str:
    text = _SECRETISH_RE.sub("[REDACTED]", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _safe_pack_id(pack_id: Any) -> str:
    text = _safe_text(pack_id, 140)
    if not _SAFE_PACK_RE.match(text):
        raise ValueError(f"invalid pack_id for rejected-edit memory: {pack_id!r}")
    return text


def _safe_op(value: Any, label: str) -> str:
    text = _safe_text(value, 140)
    if not _SAFE_OP_RE.match(text):
        raise ValueError(f"invalid {label} for rejected-edit memory: {value!r}")
    return text


def _safe_receipts(values: Iterable[Any]) -> list[str]:
    receipts = []
    for value in values:
        text = _safe_text(value, 180)
        if text:
            receipts.append(text)
        if len(receipts) >= 8:
            break
    return receipts


class RejectedEditMemory:
    """Tiny append-only JSONL ledger for optimizer negative evidence."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else get_borg_home() / "optimizer_rejected_edits.jsonl"

    def _ensure_writable_parent(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("rejected-edit memory path must not be a symlink")

    @staticmethod
    def prevent_repeat_key(*, pack_id: str, op: str, anchor: str) -> str:
        return _sha256_ref({"pack_id": pack_id, "op": op, "anchor": anchor})

    def record_rejection(
        self,
        *,
        pack_id: str,
        op: str,
        anchor: str,
        reason: str,
        candidate_id: str = "",
        supporting_receipt_ids: Sequence[Any] = (),
    ) -> dict[str, Any]:
        pack = _safe_pack_id(pack_id)
        safe_op = _safe_op(op, "op")
        safe_anchor = _safe_op(anchor, "anchor")
        record = {
            "schema_version": "1.0",
            "created_at": _utc_now(),
            "pack_id": pack,
            "op": safe_op,
            "anchor": safe_anchor,
            "reason": _safe_text(reason, 300) or "rejected",
            "candidate_id": _safe_text(candidate_id, 120),
            "supporting_receipt_ids": _safe_receipts(supporting_receipt_ids),
            "prevent_repeat_key": self.prevent_repeat_key(pack_id=pack, op=safe_op, anchor=safe_anchor),
        }
        self._ensure_writable_parent()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        return record

    def list_rejections(self, *, pack_id: str | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        if self.path.is_symlink():
            raise ValueError("rejected-edit memory path must not be a symlink")
        wanted = _safe_pack_id(pack_id) if pack_id else ""
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or data.get("schema_version") != "1.0":
                continue
            if wanted and data.get("pack_id") != wanted:
                continue
            rows.append(data)
        return rows

    def find_rejection(self, *, pack_id: str, op: str, anchor: str) -> dict[str, Any] | None:
        key = self.prevent_repeat_key(pack_id=_safe_pack_id(pack_id), op=_safe_op(op, "op"), anchor=_safe_op(anchor, "anchor"))
        matches = [row for row in self.list_rejections(pack_id=pack_id) if row.get("prevent_repeat_key") == key]
        return matches[-1] if matches else None

    def skipped_artifact(self, *, pack_id: str, op: str, anchor: str) -> dict[str, Any] | None:
        record = self.find_rejection(pack_id=pack_id, op=op, anchor=anchor)
        if not record:
            return None
        return {
            "op": record["op"],
            "anchor": record["anchor"],
            "reason": record.get("reason", "rejected"),
            "prevent_repeat_key": record["prevent_repeat_key"],
            "last_rejected_candidate_id": record.get("candidate_id", ""),
        }
