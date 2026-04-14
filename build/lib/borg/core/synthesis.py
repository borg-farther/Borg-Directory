"""
On-demand LLM synthesis for Borg trace retrieval results.
Caches synthesis results by content hash for 24 hours.
Uses claude-haiku-4-5 via the Anthropic API.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SYNTHESIS_CACHE_TTL = 86400   # 24 hours
SYNTHESIS_MODEL = "claude-haiku-4-5-20251001"
SYNTHESIS_MAX_TOKENS = 300

SYNTHESIS_PROMPT = """You are a senior engineer giving advice to a junior agent.
Below are traces from real agent sessions that handled the same type of problem.

TRACES:
{traces}

Write a 2-3 sentence mentor paragraph that:
1. Names the most common root cause (if consistent across traces)
2. States what approach actually worked (most frequently successful action)
3. Warns about one specific dead end that agents should avoid

Be concrete and specific. Use the exact commands/patterns from the traces.
Do not use bullet points. Do not use headers. Write in second person ("You should...").
If the traces show conflicting outcomes, say so honestly.
Maximum 3 sentences."""


def _get_cache_db() -> sqlite3.Connection:
    borg_home = Path(os.environ.get('BORG_HOME', '~/.borg')).expanduser()
    borg_home.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(borg_home / 'synthesis_cache.db'))
    db.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_cache (
            content_hash TEXT PRIMARY KEY,
            synthesis TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    db.commit()
    return db


def _hash_content(raw_traces_text: str) -> str:
    return hashlib.sha256(raw_traces_text.encode()).hexdigest()[:16]


def _get_cached(content_hash: str) -> Optional[str]:
    try:
        db = _get_cache_db()
        row = db.execute(
            "SELECT synthesis, created_at FROM synthesis_cache WHERE content_hash = ?",
            (content_hash,)
        ).fetchone()
        db.close()
        if row and (time.time() - row[1]) < SYNTHESIS_CACHE_TTL:
            return row[0]
    except Exception as e:
        logger.debug("synthesis cache read error: %s", e)
    return None


def _store_cached(content_hash: str, synthesis: str) -> None:
    try:
        db = _get_cache_db()
        db.execute(
            "INSERT OR REPLACE INTO synthesis_cache VALUES (?, ?, ?)",
            (content_hash, synthesis, time.time())
        )
        db.commit()
        db.close()
    except Exception as e:
        logger.debug("synthesis cache write error: %s", e)


def synthesise(raw_traces_text: str) -> Optional[str]:
    """
    Given raw trace content, call claude-haiku-4-5 to synthesise a mentor paragraph.
    Returns None if synthesis fails — caller should fall back to raw text.
    """
    if not raw_traces_text or len(raw_traces_text) < 50:
        return None

    content_hash = _hash_content(raw_traces_text)

    # Check cache first
    cached = _get_cached(content_hash)
    if cached:
        logger.debug("synthesis: cache hit for %s", content_hash)
        return cached

    # Call the API
    try:
        import anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            logger.debug("synthesis: ANTHROPIC_API_KEY not set")
            return None

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=SYNTHESIS_MODEL,
            max_tokens=SYNTHESIS_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": SYNTHESIS_PROMPT.format(traces=raw_traces_text[:2000])
            }]
        )

        synthesis = response.content[0].text.strip()

        if synthesis and len(synthesis) > 20:
            _store_cached(content_hash, synthesis)
            logger.info("synthesis: generated %d chars, cached as %s", len(synthesis), content_hash)
            return synthesis

    except ImportError:
        logger.debug("synthesis: anthropic package not available")
    except Exception as e:
        logger.debug("synthesis: API call failed: %s", e)

    return None
