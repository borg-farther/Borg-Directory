"""Minimum human-visible signal for hook/autopilot firings (E-014 channel e).

The agent-framework hook (`agent_hook.borg_on_failure`) returned its suggestion
string to the calling framework — i.e. a log. No human ever saw Borg fire.
This module pushes the one-line ``human_summary`` to the human over Telegram.

Rules:
  * OPT-IN only: silent no-op unless BOTH ``BORG_TELEGRAM_BOT_TOKEN`` and
    ``BORG_TELEGRAM_CHAT_ID`` are set by the user.
  * Push/pull rule: callers may push HITS and STUCK-CATCHES only. Misses are
    pull-only by design — ``push_human_summary`` refuses lines that look like
    misses as a second line of defense.
  * Best-effort and fail-silent: a notification must never break the loop
    that fired it. 5-second timeout, no retries, no exceptions out.
  * Privacy: only the human_summary line is sent — class-level words, no error
    text, no paths, no code (the line is built from redacted vocabulary).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_MISS_MARKERS = ("nothing reliable known", "won't guess")


def telegram_configured() -> bool:
    return bool(os.environ.get("BORG_TELEGRAM_BOT_TOKEN")) and bool(
        os.environ.get("BORG_TELEGRAM_CHAT_ID")
    )


def push_human_summary(human_summary: str) -> bool:
    """Push one moment-line to the configured Telegram chat. Returns True only
    when a push was actually attempted and accepted."""
    text = (human_summary or "").strip()
    if not text or not telegram_configured():
        return False
    if any(marker in text.lower() for marker in _MISS_MARKERS):
        # Misses are pull-only; never push them anywhere.
        return False
    token = os.environ["BORG_TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["BORG_TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{urllib.parse.quote(token)}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text[:400]}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # nosec B310 - fixed Telegram API host
            return 200 <= response.status < 300
    except Exception:
        logger.debug("borg notify: telegram push failed (ignored)")
        return False
