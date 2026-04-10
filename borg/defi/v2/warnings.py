"""
Warning propagation for Borg DeFi V2 — auto-generates warnings based on collective evidence.

Warnings are created when:
  - A pack's reputation drops below 0.4 AND
  - The pack has 4+ total outcomes (sufficient sample size)

Warnings expire after 30 days automatically.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from borg.defi.v2.models import Warning, DeFiStrategyPack, now_iso


# Default warning expiry in days
DEFAULT_EXPIRY_DAYS = 30


class WarningManager:
    """
    Manages warning propagation and lifecycle.

    Warnings are stored as YAML files in warnings_dir.
    """

    def __init__(self, warnings_dir: Path = None):
        if warnings_dir is None:
            warnings_dir = Path.home() / ".hermes" / "borg" / "defi" / "warnings"
        self.warnings_dir = Path(warnings_dir)
        self.warnings_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Warning] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load all warnings into memory on init."""
        if not self.warnings_dir.exists():
            return

        for path in self.warnings_dir.glob("*.yaml"):
            with open(path, "r", encoding="utf-8") as f:
                d = yaml.safe_load(f)
            if d:
                w = Warning.from_dict(d)
                self._cache[w.id] = w

    def _warning_path(self, warning_id: str) -> Path:
        """Get path for a warning ID."""
        safe_id = warning_id.replace("/", "_").replace(":", "_")
        return self.warnings_dir / f"{safe_id}.yaml"

    def check_and_propagate(self, pack: DeFiStrategyPack) -> Optional[Dict[str, Any]]:
        """
        Check if a pack needs a warning and auto-create one if so.

        Conditions:
          - reputation < 0.4 AND total_outcomes >= 4

        Returns the created warning dict, or None if no warning needed.
        """
        # Don't warn if already warned for this pack
        if self.is_warned(pack.id):
            return None

        # Check conditions
        if pack.reputation >= 0.4:
            return None
        if pack.total_outcomes < 4:
            return None

        # Create warning
        severity = "high" if pack.reputation < 0.3 else "medium"
        warning = Warning(
            id=f"warning/{pack.id}/{datetime.utcnow().strftime('%Y%m%d')}",
            type="collective_warning",
            severity=severity,
            pack_id=pack.id,
            reason=f"Low win rate with sufficient sample: reputation={pack.reputation:.2f}, "
                   f"outcomes={pack.total_outcomes}, losses={pack.total_outcomes - pack.profitable}",
            evidence={
                "total_outcomes": pack.total_outcomes,
                "losses": pack.total_outcomes - pack.profitable,
                "reputation": pack.reputation,
                "alpha": pack.alpha,
                "beta": pack.beta,
                "loss_patterns": [
                    {"pattern": lp.pattern, "count": lp.count}
                    for lp in pack.loss_patterns
                ],
            },
            guidance=f"Avoid {pack.name}. {pack.total_outcomes - pack.profitable} agents lost money "
                     f"across {pack.total_outcomes} attempts.",
            created_at=now_iso(),
            expires_at=(datetime.utcnow() + timedelta(days=DEFAULT_EXPIRY_DAYS)).isoformat() + "Z",
        )

        self._save(warning)
        return warning.to_dict()

    def get_active_warnings(
        self, chain: str = None, protocol: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get all currently active (non-expired) warnings.

        Optionally filter by chain or protocol (via pack_id parsing).
        """
        self.expire_old_warnings()  # Clean up first

        warnings = []
        for w in self._cache.values():
            if self._is_expired(w):
                continue

            # Filter by chain (pack_id format: category/protocol-token-chain or category/protocol-chain)
            if chain:
                pack_parts = w.pack_id.split("/")
                if len(pack_parts) >= 2:
                    # Chain is the last part of protocol-token-chain (e.g., "aave-usdc-base" -> "base")
                    protocol_part = pack_parts[-1]
                    chain_candidate = protocol_part.split("-")[-1]
                    if chain_candidate.lower() != chain.lower():
                        continue

            # Filter by protocol
            if protocol:
                pack_parts = w.pack_id.split("/")
                if len(pack_parts) >= 2:
                    pack_protocol = pack_parts[1]
                    if pack_protocol.lower() != protocol.lower():
                        continue

            warnings.append(w.to_dict())

        return warnings

    def is_warned(self, pack_id: str) -> bool:
        """Check if a pack currently has an active warning."""
        self.expire_old_warnings()

        for w in self._cache.values():
            if self._is_expired(w):
                continue
            if w.pack_id == pack_id:
                return True

        return False

    def get_warning_for_pack(self, pack_id: str) -> Optional[Warning]:
        """Get the active warning for a specific pack, if any."""
        self.expire_old_warnings()

        for w in self._cache.values():
            if self._is_expired(w):
                continue
            if w.pack_id == pack_id:
                return w

        return None

    def expire_old_warnings(self) -> int:
        """
        Remove warnings older than 30 days.

        Returns the number of warnings that were expired and removed.
        """
        expired_ids = []
        for wid, w in self._cache.items():
            if self._is_expired(w):
                expired_ids.append(wid)

        for wid in expired_ids:
            del self._cache[wid]
            path = self._warning_path(wid)
            if path.exists():
                path.unlink()

        return len(expired_ids)

    def _is_expired(self, warning: Warning) -> bool:
        """Check if a warning has expired."""
        if not warning.expires_at:
            return False

        try:
            expires = datetime.fromisoformat(warning.expires_at.replace("Z", ""))
            return datetime.utcnow() > expires
        except (ValueError, AttributeError):
            return False

    def _save(self, warning: Warning) -> None:
        """Save a warning to disk and update cache."""
        path = self._warning_path(warning.id)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(warning.to_dict(), f, sort_keys=False, allow_unicode=True)
        self._cache[warning.id] = warning

    def clear_warning(self, warning_id: str) -> bool:
        """Manually clear a warning (e.g., after pack improves)."""
        if warning_id in self._cache:
            del self._cache[warning_id]
            path = self._warning_path(warning_id)
            if path.exists():
                path.unlink()
            return True
        return False

    def list_all_warnings(self) -> List[Dict[str, Any]]:
        """List all warnings (including expired)."""
        return [w.to_dict() for w in self._cache.values()]
