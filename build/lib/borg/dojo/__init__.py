"""
Borg Dojo — Session analysis for agent self-improvement.

Phase 1: Read-only analysis of Hermes session history.
"""

import os

# Feature flag — set BORG_DOJO_ENABLED=true to activate
BORG_DOJO_ENABLED = os.getenv("BORG_DOJO_ENABLED", "false").lower() == "true"

# Schema version for interface versioning (see BORG_DOJO_SPEC.md §5.2)
SCHEMA_VERSION = 1

__all__ = ["BORG_DOJO_ENABLED", "SCHEMA_VERSION"]
