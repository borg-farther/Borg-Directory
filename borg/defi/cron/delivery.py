"""
Telegram Delivery — Cron alert delivery via Telegram Bot API.

Provides async delivery of formatted alert strings to Telegram,
with support for chunking long messages and markdown formatting.

Usage:
    from borg.defi.cron.delivery import deliver_alerts

    # Simple delivery
    count = await deliver_alerts(["Alert 1", "Alert 2"])

    # With custom chat_id
    count = await deliver_alerts(["Alert 1"], chat_id="custom_chat_id")
"""

import asyncio
import logging
import os
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# Configuration from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Telegram API constants
TELEGRAM_API_BASE = "https://api.telegram.org/bot"
TELEGRAM_MESSAGE_LIMIT = 4096  # Telegram message length limit


async def deliver_alerts(
    alerts: List[str],
    platform: str = "telegram",
    chat_id: Optional[str] = None,
) -> int:
    """
    Deliver formatted alerts to a messaging platform.

    Currently supports Telegram Bot API. Messages are chunked if they
    exceed Telegram's 4096 character limit.

    Args:
        alerts: List of formatted alert strings to deliver.
        platform: Delivery platform (only 'telegram' currently supported).
        chat_id: Optional override for Telegram chat ID. If not provided,
                 uses TELEGRAM_CHAT_ID from environment.

    Returns:
        Number of messages actually sent. Returns 0 if:
        - alerts list is empty
        - TELEGRAM_BOT_TOKEN is not configured
        - platform is not supported
    """
    if not alerts:
        return 0

    if platform.lower() != "telegram":
        logger.warning(f"Unsupported delivery platform: {platform}")
        return 0

    token = TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("TELEGRAM_BOT_TOKEN not configured, skipping delivery")
        return 0

    target_chat = chat_id or TELEGRAM_CHAT_ID
    if not target_chat:
        logger.debug("No chat_id provided and TELEGRAM_CHAT_ID not set")
        return 0

    sent_count = 0
    for alert in alerts:
        # Chunk if message is too long
        chunks = _chunk_message(alert, TELEGRAM_MESSAGE_LIMIT)

        for chunk in chunks:
            success = await _send_telegram_message(
                token=token,
                chat_id=target_chat,
                text=chunk,
            )
            if success:
                sent_count += 1
            # Small delay to avoid hitting rate limits
            await asyncio.sleep(0.1)

    logger.info(f"Delivered {sent_count}/{len(alerts)} alert messages to Telegram")
    return sent_count


def _chunk_message(message: str, limit: int) -> List[str]:
    """
    Split a message into chunks that fit within the Telegram limit.

    Handles newlines and tries to break at reasonable points.

    Args:
        message: The message to chunk.
        limit: Maximum characters per chunk.

    Returns:
        List of message chunks.
    """
    if len(message) <= limit:
        return [message]

    chunks = []
    lines = message.split("\n")
    current_chunk = ""

    for line in lines:
        if not line:
            # Preserve empty lines
            if current_chunk:
                current_chunk += "\n"
            continue

        test_chunk = current_chunk + ("\n" if current_chunk else "") + line

        if len(test_chunk) <= limit:
            current_chunk = test_chunk
        else:
            # Current chunk is full
            if current_chunk:
                chunks.append(current_chunk)

            # If single line exceeds limit, split it forcibly
            if len(line) > limit:
                # Split line into smaller pieces
                while len(line) > limit:
                    chunks.append(line[:limit])
                    line = line[limit:]
                current_chunk = line
            else:
                current_chunk = line

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [message[:limit]]


async def _send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    parse_mode: str = "MarkdownV2",
) -> bool:
    """
    Send a single message via Telegram Bot API.

    Args:
        token: Telegram bot token.
        chat_id: Target chat ID.
        text: Message text.
        parse_mode: Parse mode for formatting (MarkdownV2 or HTML).

    Returns:
        True if message sent successfully, False otherwise.
    """
    url = f"{TELEGRAM_API_BASE}{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    logger.debug(f"Telegram message sent successfully to chat {chat_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.warning(f"Telegram API error {response.status}: {error_text}")
                    return False
    except asyncio.TimeoutError:
        logger.warning(f"Telegram request timed out for chat {chat_id}")
        return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


async def send_telegram(
    message: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "MarkdownV2",
) -> bool:
    """
    Convenience function to send a single message to Telegram.

    Args:
        message: Message text to send.
        chat_id: Optional override for chat ID.
        parse_mode: Parse mode for formatting.

    Returns:
        True if message sent successfully.
    """
    token = TELEGRAM_BOT_TOKEN
    if not token:
        return False

    target = chat_id or TELEGRAM_CHAT_ID
    if not target:
        return False

    return await _send_telegram_message(token, target, message, parse_mode)