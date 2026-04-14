"""
Borg cold start — runs once on first install to ensure immediate utility.
Installs extended seed packs and verifies borg_search works.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

COLD_START_MARKER = Path(os.path.expanduser("~/.borg/.cold_start_done"))


def run_if_needed() -> bool:
    """Run cold start setup if not already done. Returns True if ran."""
    if COLD_START_MARKER.exists():
        return False

    try:
        _run_cold_start()
        COLD_START_MARKER.parent.mkdir(parents=True, exist_ok=True)
        COLD_START_MARKER.write_text("done")
        logger.info("Borg cold start complete")
        return True
    except Exception as e:
        logger.warning(f"Cold start failed (non-fatal): {e}")
        return False


def _run_cold_start():
    """Install seed packs and verify search works."""
    from borg.core.seeds import get_seed_packs
    from borg.core.search import borg_search
    import json

    # Verify seeds load
    packs = get_seed_packs()
    logger.info(f"Cold start: {len(packs)} seed packs available")

    # Verify search works
    result = json.loads(borg_search("error"))
    count = len(result.get("matches", []))
    logger.info(f"Cold start: search returns {count} results for 'error'")

    if count == 0:
        raise ValueError("Cold start: search returned 0 results — seed packs not loading")

    # Build embedding index from existing traces
    try:
        from borg.core.embeddings import build_index_from_db
        from borg.core.traces import TRACE_DB_PATH
        if os.path.exists(TRACE_DB_PATH):
            _, emb_count = build_index_from_db(TRACE_DB_PATH)
            logger.info(f"Cold start: embedded {emb_count} traces")
    except Exception as e:
        logger.warning(f"Cold start: embedding index failed (non-fatal): {e}")
