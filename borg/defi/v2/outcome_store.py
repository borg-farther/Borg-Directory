"""Borg DeFi V2 — Outcome storage layer."""

import yaml
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from borg.defi.v2.models import ExecutionOutcome

logger = logging.getLogger(__name__)


class OutcomeStore:
    """Manages execution outcomes on disk.

    Default directory: ~/.hermes/borg/defi/outcomes/
    Outcomes are stored in monthly subdirectories: outcomes/2026-03/outcome-001.yaml
    """

    def __init__(self, outcomes_dir: Optional[Path] = None):
        if outcomes_dir is None:
            outcomes_dir = Path.home() / ".hermes" / "borg" / "defi" / "outcomes"
        self.outcomes_dir = Path(outcomes_dir)
        # Ensure directory exists
        self.outcomes_dir.mkdir(parents=True, exist_ok=True)

    def _outcome_path(self, outcome: ExecutionOutcome) -> Path:
        """Get the file path for an outcome based on its date.

        Uses the entered_at timestamp to organize into monthly folders.
        """
        dt = outcome.entered_at or datetime.now()
        year_month = dt.strftime("%Y-%m")
        # Create safe filename from outcome_id
        safe_id = outcome.outcome_id.replace("/", "-").replace(":", "-")
        filename = f"{safe_id}.yaml"
        return self.outcomes_dir / year_month / filename

    def _current_month_dir(self) -> Path:
        """Get the directory for the current month."""
        year_month = datetime.now().strftime("%Y-%m")
        return self.outcomes_dir / year_month

    def save_outcome(self, outcome: ExecutionOutcome) -> None:
        """Save an outcome to disk.

        Args:
            outcome: ExecutionOutcome to save.
        """
        path = self._outcome_path(outcome)
        # Ensure subdirectory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.safe_dump(outcome.to_dict(), f, default_flow_style=False, sort_keys=False)

    def load_outcomes_for_pack(self, pack_id: str) -> List[ExecutionOutcome]:
        """Load all outcomes for a specific pack.

        Args:
            pack_id: Pack identifier.

        Returns:
            List of ExecutionOutcome objects for the pack.
        """
        outcomes = []
        for yaml_file in self.outcomes_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if data is None:
                    continue
                outcome = ExecutionOutcome.from_dict(data)
                if outcome.pack_id == pack_id:
                    outcomes.append(outcome)
            except Exception as e:
                logger.warning(f"Error loading outcome {yaml_file}: {e}")
                continue
        # Sort by entered_at
        outcomes.sort(key=lambda o: o.entered_at or datetime.min)
        return outcomes

    def load_all_outcomes(self, since_days: Optional[int] = None) -> List[ExecutionOutcome]:
        """Load all outcomes, optionally filtered by age.

        Args:
            since_days: If set, only return outcomes from the last N days.

        Returns:
            List of ExecutionOutcome objects.
        """
        outcomes = []
        cutoff = None
        if since_days is not None:
            cutoff = datetime.now() - timedelta(days=since_days)

        for yaml_file in self.outcomes_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if data is None:
                    continue
                outcome = ExecutionOutcome.from_dict(data)

                # Filter by age if requested
                if cutoff and outcome.entered_at:
                    if outcome.entered_at < cutoff:
                        continue

                outcomes.append(outcome)
            except Exception as e:
                logger.warning(f"Error loading outcome {yaml_file}: {e}")
                continue

        # Sort by entered_at
        outcomes.sort(key=lambda o: o.entered_at or datetime.min)
        return outcomes

    def outcome_exists(self, outcome_id: str) -> bool:
        """Check if an outcome exists.

        Searches all outcome files for the given outcome_id.

        Args:
            outcome_id: Outcome identifier to check.

        Returns:
            True if outcome exists, False otherwise.
        """
        # Try to find by searching all files (outcome_id is in the file content)
        for yaml_file in self.outcomes_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if data and data.get("outcome_id") == outcome_id:
                    return True
            except Exception:
                continue
        return False

    def get_outcome_count(self) -> int:
        """Get total count of stored outcomes.

        Returns:
            Total number of outcome files.
        """
        return len(list(self.outcomes_dir.rglob("*.yaml")))

    def delete_outcome(self, outcome_id: str) -> bool:
        """Delete an outcome by ID.

        Args:
            outcome_id: Outcome identifier to delete.

        Returns:
            True if deleted, False if not found.
        """
        for yaml_file in self.outcomes_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if data and data.get("outcome_id") == outcome_id:
                    yaml_file.unlink()
                    return True
            except Exception:
                continue
        return False
