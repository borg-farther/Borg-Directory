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


class ColdStartSeedError(RuntimeError):
    """The bundled seed corpus failed to load.

    This is a packaging/install breakage (e.g. a wheel built without
    ``seeds_data``), not a transient hiccup. It is raised — never swallowed — so
    an empty-corpus install fails LOUDLY instead of silently degrading every
    ``borg rescue`` to ``no_confident_match`` while looking healthy.
    """


def verify_seeds_loaded() -> int:
    """Load the bundled seed corpus and return its match count for ``"error"``.

    Deterministic and marker-independent, so tests and the wheel smoke can assert
    a freshly built package actually carries its seeds. Raises
    ``ColdStartSeedError`` if nothing loads.
    """
    from borg.core.seeds import get_seed_packs
    from borg.core.search import borg_search
    import json

    packs = get_seed_packs()
    result = json.loads(borg_search("error"))
    count = len(result.get("matches", []))
    if not packs or count == 0:
        raise ColdStartSeedError(
            f"seed corpus did not load: {len(packs)} seed packs, "
            f"{count} search matches for 'error' — the install is missing its "
            f"bundled seeds_data (broken wheel)."
        )
    return count


def run_if_needed() -> bool:
    """Run cold start setup if not already done. Returns True if it ran.

    A seed-corpus failure is LOUD (re-raised); all other cold-start hiccups
    (e.g. writing the done-marker) stay non-fatal. The done-marker is written
    only on success, so a broken install keeps re-checking until fixed.
    """
    if COLD_START_MARKER.exists():
        return False

    try:
        _run_cold_start()
    except ColdStartSeedError:
        logger.error(
            "Borg cold start FAILED: bundled seed corpus did not load. This "
            "install is broken (the wheel is missing seeds_data); `borg rescue` "
            "will match nothing until it is reinstalled."
        )
        raise
    except Exception as e:
        logger.warning(f"Cold start incomplete (non-fatal): {e}")
        return False

    try:
        COLD_START_MARKER.parent.mkdir(parents=True, exist_ok=True)
        COLD_START_MARKER.write_text("done")
    except Exception as e:
        logger.warning(f"Cold start marker not written (non-fatal): {e}")
    logger.info("Borg cold start complete")
    return True


def _run_cold_start():
    """Verify the seed corpus loads (loud on failure), then build the optional
    embedding index (genuinely optional — failure here is non-fatal)."""
    count = verify_seeds_loaded()
    logger.info(f"Cold start: search returns {count} results for 'error'")

    try:
        from borg.core.embeddings import build_index_from_db
        from borg.core.traces import TRACE_DB_PATH
        if os.path.exists(TRACE_DB_PATH):
            _, emb_count = build_index_from_db(TRACE_DB_PATH)
            logger.info(f"Cold start: embedded {emb_count} traces")
    except Exception as e:
        logger.warning(f"Cold start: embedding index failed (non-fatal): {e}")
