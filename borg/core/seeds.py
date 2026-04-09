"""Seed corpus loader for cold-start fix.

Zero imports from tools.* or guild_mcp.* — uses stdlib only.

Provides:
    _load_seed_index()   — load seed packs from borg/seeds_data/packs/*.yaml
    SeedPack             — dataclass for a single seed pack
    SeedIndex            — dataclass for the full seed index
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

# The path to seeds within the package (read-only, shipped in wheel)
SEEDS_DIR = Path(__file__).parent.parent / "seeds_data" / "packs"


@dataclass
class SeedPack:
    """Minimal representation — just what borg_search needs."""
    name: str
    problem_class: str
    solution: str
    source_url: str
    tier: str = "SEED"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    @classmethod
    def from_yaml(cls, data: dict) -> "SeedPack":
        return cls(
            name=data.get("name", ""),
            problem_class=data.get("problem_class", ""),
            solution=data.get("solution", data.get("description", "")),
            source_url=data.get("source_url", ""),
            tier="SEED",
            tags=data.get("tags", []),
        )

    def to_search_dict(self) -> dict:
        """Convert to dict format used by borg_search()."""
        # Normalize hyphens to spaces for better text search matching
        normalized_name = self.name.replace("-", " ")
        return {
            "name": self.name,
            "problem_class": self.problem_class,
            "id": self.name,
            "phase_names": [normalized_name],  # Include normalized name for search
            "phases": 0,
            "confidence": "seed",
            "tier": "SEED",
            "source": "seed",
            "solution": self.solution,
            "source_url": self.source_url,
            "tags": self.tags,
        }


@dataclass
class SeedIndex:
    """Full seed index returned by _load_seed_index()."""
    version: str
    generated_at: str
    pack_count: int
    packs: List[SeedPack]


@functools.lru_cache(maxsize=1)
def _load_seed_index(force_reload: bool = False) -> dict:
    """Load seed packs from borg/seeds_data/packs/*.yaml.

    Memoized (maxsize=1). On any error, returns {"packs": []}.
    Never writes to user dir. Never makes network calls.

    Returns:
        dict with keys: version, generated_at, pack_count, packs
    """
    try:
        packs_dir = SEEDS_DIR
        if not packs_dir.exists():
            return {
                "version": "1.0",
                "generated_at": "2026-04-09",
                "pack_count": 0,
                "packs": [],
            }

        packs: List[SeedPack] = []
        for yaml_file in sorted(packs_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    packs.append(SeedPack.from_yaml(data))
            except Exception:
                # Fail silently per spec — one bad pack doesn't crash borg
                continue

        return {
            "version": "1.0",
            "generated_at": "2026-04-09",
            "pack_count": len(packs),
            "packs": packs,
        }
    except Exception:
        # Fail silently — cold-start break doesn't crash search
        return {
            "version": "1.0",
            "generated_at": "",
            "pack_count": 0,
            "packs": [],
        }


def get_seed_packs() -> List[SeedPack]:
    """Return all seed packs as SeedPack objects."""
    index = _load_seed_index()
    return index.get("packs", [])


def is_seeds_disabled() -> bool:
    """Check if seeds are disabled via environment variable."""
    return os.environ.get("BORG_DISABLE_SEEDS", "0") in ("1", "true", "True")
