"""Borg DeFi V2 — Pack storage layer."""

import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from borg.defi.v2.models import DeFiStrategyPack

logger = logging.getLogger(__name__)


class PackStore:
    """Manages DeFi strategy packs on disk.

    Default directory: ~/.hermes/borg/defi/packs/
    """

    def __init__(self, packs_dir: Optional[Path] = None):
        if packs_dir is None:
            packs_dir = Path.home() / ".hermes" / "borg" / "defi" / "packs"
        self.packs_dir = Path(packs_dir)
        self._warnings_dir = self.packs_dir / "warnings"
        # Ensure directories exist
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self._warnings_dir.mkdir(parents=True, exist_ok=True)

    def _pack_path(self, pack_id: str) -> Path:
        """Get the file path for a pack ID.

        Example: yield/aave-usdc-base -> packs/yield/aave-usdc-base.yaml
        """
        # Convert pack_id to path: yield/aave-usdc-base -> yield/aave-usdc-base.yaml
        parts = pack_id.split("/")
        filename = parts[-1] + ".yaml"
        subdir = "/".join(parts[:-1]) if len(parts) > 1 else ""
        if subdir:
            return self.packs_dir / subdir / filename
        return self.packs_dir / filename

    def load_pack(self, pack_id: str) -> Optional[DeFiStrategyPack]:
        """Load a single pack by ID.

        Args:
            pack_id: Pack identifier (e.g., "yield/aave-usdc-base")

        Returns:
            DeFiStrategyPack if found, None otherwise.
        """
        path = self._pack_path(pack_id)
        if not path.exists():
            logger.debug(f"Pack not found: {pack_id} at {path}")
            return None

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
            if data is None:
                logger.warning(f"Empty pack file: {path}")
                return None
            return DeFiStrategyPack.from_dict(data)
        except yaml.YAMLError as e:
            logger.error(f"YAML error loading pack {pack_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading pack {pack_id}: {e}")
            return None

    def save_pack(self, pack: DeFiStrategyPack) -> None:
        """Save a pack to disk.

        Args:
            pack: DeFiStrategyPack to save.
        """
        path = self._pack_path(pack.id)
        # Ensure subdirectory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.safe_dump(pack.to_dict(), f, default_flow_style=False, sort_keys=False)

    def list_packs(
        self,
        token: Optional[str] = None,
        chain: Optional[str] = None,
        risk: Optional[str] = None,
    ) -> List[DeFiStrategyPack]:
        """List all packs, optionally filtered.

        Args:
            token: Filter by supported token (e.g., "USDC")
            chain: Filter by supported chain (e.g., "base")
            risk: Filter by risk tolerance (e.g., "low", "medium")

        Returns:
            List of matching DeFiStrategyPack objects.
        """
        packs = []
        for yaml_file in self.packs_dir.rglob("*.yaml"):
            # Skip warnings directory
            if "warnings" in yaml_file.parts:
                continue
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if data is None:
                    continue
                pack = DeFiStrategyPack.from_dict(data)

                # Apply filters
                if token and pack.entry and token not in pack.entry.tokens:
                    continue
                if chain and pack.entry and chain not in pack.entry.chains:
                    continue
                if risk and pack.entry and risk not in pack.entry.risk_tolerance:
                    continue

                packs.append(pack)
            except Exception as e:
                logger.warning(f"Error loading pack {yaml_file}: {e}")
                continue
        return packs

    def load_warnings(self) -> List[Dict[str, Any]]:
        """Load all active warnings.

        Returns:
            List of warning dictionaries.
        """
        warnings = []
        warning_files = self._warnings_dir.glob("*.yaml")
        for warning_file in warning_files:
            try:
                with open(warning_file, "r") as f:
                    data = yaml.safe_load(f)
                if data:
                    warnings.append(data)
            except Exception as e:
                logger.warning(f"Error loading warning {warning_file}: {e}")
        return warnings

    def save_warning(self, warning: Dict[str, Any]) -> None:
        """Save a warning to disk.

        Args:
            warning: Warning dictionary to save.
        """
        warning_id = warning.get("id", "unknown")
        # Convert warning id to filename: warning/yield-xxx/2026-03 -> yield-xxx-2026-03.yaml
        safe_name = warning_id.replace("/", "-").replace(":", "-")
        path = self._warnings_dir / f"{safe_name}.yaml"

        with open(path, "w") as f:
            yaml.safe_dump(warning, f, default_flow_style=False, sort_keys=False)

    def delete_pack(self, pack_id: str) -> bool:
        """Delete a pack from disk.

        Args:
            pack_id: Pack identifier to delete.

        Returns:
            True if deleted, False if not found.
        """
        path = self._pack_path(pack_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def pack_exists(self, pack_id: str) -> bool:
        """Check if a pack exists.

        Args:
            pack_id: Pack identifier.

        Returns:
            True if pack exists, False otherwise.
        """
        return self._pack_path(pack_id).exists()
